"""
笔记总结任务管理器

负责管理总结任务的生命周期，包括任务创建、执行、状态跟踪等
"""

import asyncio
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from dataclasses import dataclass, field

from app.utils.text_processing import TextProcessor, ConfidenceCalculator
from app.crud.content import content
from app.db.session import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    TIMEOUT = "timeout"      # 超时


@dataclass
class SummaryTask:
    """总结任务数据类"""
    task_id: str
    user_id: str
    content_ids: List[str]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress: int = 0  # 进度百分比 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "content_ids": self.content_ids,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error_message": self.error_message,
            "progress": self.progress
        }


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        """初始化任务管理器"""
        self.tasks: Dict[str, SummaryTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = settings.NOTE_MAX_CONCURRENT_TASKS
        self.task_timeout = settings.NOTE_TASK_TIMEOUT
        self._cleanup_task = None
        self.text_processor = TextProcessor()
        self.confidence_calculator = ConfidenceCalculator()
        
    async def start_cleanup_task(self):
        """启动清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_tasks())
    
    async def create_task(self, user_id: str, content_ids: List[str], websocket_manager=None) -> str:
        """创建新的总结任务"""
        task_id = str(uuid.uuid4())
        
        # 验证内容数量
        if len(content_ids) < settings.NOTE_MIN_THRESHOLD:
            raise ValueError(f"内容数量不足，至少需要 {settings.NOTE_MIN_THRESHOLD} 个")
        
        # 检查并发任务数量
        running_count = len([t for t in self.tasks.values() 
                           if t.status in [TaskStatus.PENDING, TaskStatus.RUNNING]])
        
        if running_count >= self.max_concurrent_tasks:
            raise ValueError("当前任务过多，请稍后再试")
        
        # 创建任务
        task = SummaryTask(
            task_id=task_id,
            user_id=user_id,
            content_ids=content_ids
        )
        
        self.tasks[task_id] = task
        
        # 异步执行任务
        asyncio_task = asyncio.create_task(self._execute_task(task_id, websocket_manager))
        self.running_tasks[task_id] = asyncio_task
        
        logger.info(f"创建总结任务: {task_id}, 用户: {user_id}, 内容数量: {len(content_ids)}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return task.to_dict()
    
    async def get_user_tasks(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户的任务列表"""
        user_tasks = [
            task for task in self.tasks.values() 
            if task.user_id == user_id
        ]
        
        # 按创建时间倒序排列
        user_tasks.sort(key=lambda x: x.created_at, reverse=True)
        
        return [task.to_dict() for task in user_tasks[:limit]]
    
    async def cancel_task(self, task_id: str, user_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if not task or task.user_id != user_id:
            return False
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]:
            return False
        
        # 取消异步任务
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        # 更新任务状态
        task.status = TaskStatus.FAILED
        task.error_message = "任务已被用户取消"
        task.completed_at = datetime.now()
        
        logger.info(f"任务已取消: {task_id}")
        return True
    
    async def _execute_task(self, task_id: str, websocket_manager=None):
        """执行总结任务"""
        task = self.tasks[task_id]
        
        try:
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            task.progress = 10
            
            logger.info(f"开始执行任务: {task_id}")
            
            if websocket_manager:
                await websocket_manager.send_message(task.user_id, {
                    "type": "task_started",
                    "message": "总结任务已开始",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat()
                })
            
            # 设置超时
            result = await asyncio.wait_for(
                self._process_summary(task, websocket_manager),
                timeout=self.task_timeout
            )
            
            # 任务完成
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            task.progress = 100
            
            if websocket_manager:
                await websocket_manager.send_message(task.user_id, {
                    "type": "task_completed",
                    "message": "总结任务已完成",
                    "task_id": task_id,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
            
            logger.info(f"任务完成: {task_id}")
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error_message = "任务执行超时"
            task.completed_at = datetime.now()
            
            if websocket_manager:
                await websocket_manager.send_message(task.user_id, {
                    "type": "task_timeout",
                    "message": "任务执行超时",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat()
                })
            
            logger.error(f"任务超时: {task_id}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            
            if websocket_manager:
                await websocket_manager.send_message(task.user_id, {
                    "type": "task_failed",
                    "message": f"任务执行失败: {str(e)}",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat()
                })
            
            logger.error(f"任务执行失败: {task_id}, 错误: {e}")
            
        finally:
            # 清理运行中的任务
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _process_summary(self, task: SummaryTask, websocket_manager=None) -> Dict[str, Any]:
        """处理总结逻辑"""
        db = next(get_db())
        
        try:
            # 1. 获取用户内容
            task.progress = 20
            if websocket_manager:
                await websocket_manager.send_message(task.user_id, {
                    "type": "progress_update",
                    "message": "正在获取笔记内容...",
                    "progress": task.progress,
                    "timestamp": datetime.now().isoformat()
                })
            
            contents = []
            for content_id in task.content_ids:
                content_obj = content.get(db, id=content_id)
                if content_obj and content.check_user_access(db, content_id, task.user_id):
                    contents.append(content_obj)
            
            if not contents:
                raise ValueError("没有找到有效的内容")
            
            # 2. 检查缓存
            task.progress = 30
            if websocket_manager:
                await websocket_manager.send_message(task.user_id, {
                    "type": "progress_update",
                    "message": "检查缓存的总结...",
                    "progress": task.progress,
                    "timestamp": datetime.now().isoformat()
                })
            
            cached_summaries = await self._check_cache(contents)
            
            # 3. 根据内容数量选择处理逻辑
            if len(contents) == 1:
                # 单个内容：简化流程，直接生成知识点总结
                return await self._process_single_content(contents[0], cached_summaries, task, websocket_manager, db)
            else:
                # 多个内容：完整流程，包括置信度验证
                return await self._process_multiple_contents(contents, cached_summaries, task, websocket_manager, db)
            
        finally:
            db.close()
    
    async def _process_single_content(self, content_obj, cached_summaries, task, websocket_manager, db) -> Dict[str, Any]:
        """处理单个内容的总结"""
        content_id = str(content_obj.id)
        
        # 检查是否有缓存
        if cached_summaries.get(content_id):
            task.progress = 90
            if websocket_manager:
                await websocket_manager.send_message(task.user_id, {
                    "type": "progress_update",
                    "message": "使用缓存的总结",
                    "progress": task.progress,
                    "timestamp": datetime.now().isoformat()
                })
            
            return {
                "summary_title": content_obj.summary_title or "笔记总结",
                "summary_topic": content_obj.summary_topic or "知识整理", 
                "summary_content": content_obj.summary_content,
                "content_count": 1,
                "cached": True,
                "timestamp": datetime.now().isoformat()
            }
        
        # 生成新的总结
        task.progress = 50
        if websocket_manager:
            await websocket_manager.send_message(task.user_id, {
                "type": "progress_update",
                "message": "正在生成笔记总结...",
                "progress": task.progress,
                "timestamp": datetime.now().isoformat()
            })
        
        content_text = content_obj.text_data or ""
        summary = await self.text_processor.generate_single_summary(content_text)
        
        # 提取标题和主题
        lines = summary.split('\n')
        title = "笔记总结"
        topic = "知识整理"
        
        # 尝试从总结中提取标题
        for line in lines[:3]:
            if line.strip() and not line.startswith('#'):
                title = line.strip()[:50]
                break
        
        # 保存到数据库
        task.progress = 80
        content_hash = self._generate_content_hash(content_text)
        content.update_summary(
            db=db,
            content_id=content_obj.id,
            summary_title=title,
            summary_topic=topic,
            summary_content=summary,
            content_hash=content_hash
        )
        
        task.progress = 100
        if websocket_manager:
            await websocket_manager.send_message(task.user_id, {
                "type": "progress_update",
                "message": "单个笔记总结完成",
                "progress": task.progress,
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "summary_title": title,
            "summary_topic": topic,
            "summary_content": summary,
            "content_count": 1,
            "cached": False,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _process_multiple_contents(self, contents, cached_summaries, task, websocket_manager, db) -> Dict[str, Any]:
        """处理多个内容的总结（完整流程）"""
        # 3. 生成单笔记总结
        task.progress = 40
        individual_summaries = await self._generate_individual_summaries(
            contents, cached_summaries, task.user_id, websocket_manager, db
        )
        
        # 4. 生成综合总结
        task.progress = 70
        if websocket_manager:
            await websocket_manager.send_message(task.user_id, {
                "type": "progress_update",
                "message": "正在生成综合总结...",
                "progress": task.progress,
                "timestamp": datetime.now().isoformat()
            })
        
        comprehensive_summary = await self._generate_comprehensive_summary(individual_summaries)
        
        # 5. 计算置信度
        task.progress = 85
        if websocket_manager:
            await websocket_manager.send_message(task.user_id, {
                "type": "progress_update",
                "message": "计算置信度分数...",
                "progress": task.progress,
                "timestamp": datetime.now().isoformat()
            })
        
        confidence_scores = await self._calculate_confidence_scores(
            comprehensive_summary, individual_summaries
        )
        
        # 6. 修正总结（如果置信度低）
        task.progress = 90
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        if avg_confidence < settings.NOTE_CONFIDENCE_THRESHOLD:
            if websocket_manager:
                await websocket_manager.send_message(task.user_id, {
                    "type": "progress_update",
                    "message": "修正低置信度的总结...",
                    "progress": task.progress,
                    "timestamp": datetime.now().isoformat()
                })
            
            # 选择置信度最低的总结进行修正
            min_idx = confidence_scores.index(min(confidence_scores))
            corrected_summary = await self._correct_summary(
                individual_summaries[min_idx], comprehensive_summary
            )
            individual_summaries[min_idx] = corrected_summary
            
            # 重新计算置信度
            confidence_scores = await self._calculate_confidence_scores(
                comprehensive_summary, individual_summaries
            )
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # 7. 更新数据库
        await self._update_summaries(contents, individual_summaries, comprehensive_summary, db)
        
        # 8. 返回结果
        task.progress = 95
        
        return {
            "comprehensive_summary": comprehensive_summary,
            "individual_summaries": individual_summaries,
            "confidence_scores": confidence_scores,
            "average_confidence": round(avg_confidence, 1),
            "content_count": len(contents),
            "cached_count": len([s for s in cached_summaries.values() if s is not None])
        }
    
    async def _check_cache(self, contents: List[Any]) -> Dict[str, Optional[str]]:
        """检查内容是否已有缓存的总结"""
        cached_summaries = {}
        
        for content_obj in contents:
            content_id = str(content_obj.id)
            
            # 如果已有总结内容，直接使用
            if content_obj.summary_content:
                cached_summaries[content_id] = content_obj.summary_content
                logger.info(f"使用缓存总结: {content_id}")
            else:
                cached_summaries[content_id] = None
        
        return cached_summaries
    
    async def _generate_individual_summaries(
        self, 
        contents: List[Any], 
        cached_summaries: Dict[str, Optional[str]],
        user_id: str,
        websocket_manager=None,
        db=None
    ) -> List[str]:
        """生成各笔记的知识点总结"""
        summaries = []
        
        for i, content_obj in enumerate(contents):
            content_id = str(content_obj.id)
            
            # 使用缓存或生成新总结
            if cached_summaries.get(content_id):
                summary = cached_summaries[content_id]
                if websocket_manager:
                    await websocket_manager.send_message(user_id, {
                        "type": "using_cached_summary",
                        "message": f"使用第 {i+1} 份笔记的缓存总结",
                        "timestamp": datetime.now().isoformat(),
                        "progress": f"{i+1}/{len(contents)}"
                    })
            else:
                if websocket_manager:
                    await websocket_manager.send_message(user_id, {
                        "type": "generating_summary",
                        "message": f"正在生成第 {i+1} 份笔记的总结...",
                        "timestamp": datetime.now().isoformat(),
                        "progress": f"{i+1}/{len(contents)}"
                    })
                
                # 生成新总结
                content_text = content_obj.text_data or ""
                summary = await self.text_processor.generate_single_summary(content_text)
                
                # 提取标题和主题
                lines = summary.split('\n')
                title = "笔记总结"
                topic = "知识整理"
                
                # 尝试从总结中提取标题
                for line in lines[:3]:
                    if line.strip() and not line.startswith('#'):
                        title = line.strip()[:50]
                        break
                
                # 保存到数据库
                content_hash = self._generate_content_hash(content_text)
                content.update_summary(
                    db=db,
                    content_id=content_obj.id,
                    summary_title=title,
                    summary_topic=topic,
                    summary_content=summary,
                    content_hash=content_hash
                )
                
                if websocket_manager:
                    await websocket_manager.send_message(user_id, {
                        "type": "summary_generated",
                        "message": f"第 {i+1} 份笔记总结已生成",
                        "timestamp": datetime.now().isoformat(),
                        "progress": f"{i+1}/{len(contents)}"
                    })
            
            summaries.append(summary)
        
        return summaries
    
    async def _generate_comprehensive_summary(self, individual_summaries: List[str]) -> str:
        """生成综合总结"""
        return await self.text_processor.generate_comprehensive_summary(individual_summaries)
    
    async def _calculate_confidence_scores(
        self, 
        comprehensive_summary: str, 
        individual_summaries: List[str]
    ) -> List[float]:
        """计算置信度分数"""
        return self.confidence_calculator.calculate_confidence_scores(
            comprehensive_summary, individual_summaries
        )
    
    async def _calculate_single_confidence(
        self, 
        comprehensive_summary: str, 
        individual_summary: str
    ) -> float:
        """计算单个总结的置信度"""
        return self.confidence_calculator.calculate_similarity(
            comprehensive_summary, individual_summary
        )
    
    async def _correct_summary(self, original_summary: str, comprehensive_summary: str) -> str:
        """修正总结内容"""
        return await self.text_processor.correct_summary(original_summary, comprehensive_summary)
    
    async def _update_summaries(
        self, 
        contents: List[Any], 
        final_summaries: List[str], 
        comprehensive_summary: str,
        db=None
    ):
        """更新数据库中的总结信息"""
        for content_obj, summary in zip(contents, final_summaries):
            # 提取标题和主题（简单实现）
            lines = summary.split('\n')
            title = "笔记总结"
            topic = "知识整理"
            
            # 尝试从总结中提取标题
            for line in lines[:3]:  # 只检查前3行
                if line.strip() and not line.startswith('#'):
                    title = line.strip()[:50]  # 限制长度
                    break
            
            # 更新数据库
            content.update_summary(
                db=db,
                content_id=content_obj.id,
                summary_title=title,
                summary_topic=topic,
                summary_content=summary,
                content_hash=self._generate_content_hash(content_obj.text_data or "")
            )
    
    def _generate_content_hash(self, content_text: str) -> str:
        """生成内容哈希值"""
        return hashlib.md5(content_text.encode('utf-8')).hexdigest()
    
    async def _cleanup_old_tasks(self):
        """清理旧任务"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次
                
                cutoff_time = datetime.now() - timedelta(hours=24)
                old_task_ids = [
                    task_id for task_id, task in self.tasks.items()
                    if task.created_at < cutoff_time
                ]
                
                for task_id in old_task_ids:
                    del self.tasks[task_id]
                    if task_id in self.running_tasks:
                        self.running_tasks[task_id].cancel()
                        del self.running_tasks[task_id]
                
                if old_task_ids:
                    logger.info(f"清理了 {len(old_task_ids)} 个旧任务")
                    
            except Exception as e:
                logger.error(f"清理旧任务失败: {e}")


# 全局任务管理器实例
task_manager = TaskManager()