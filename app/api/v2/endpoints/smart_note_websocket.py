"""
智能笔记WebSocket端点
提供实时的任务状态和结果推送
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState

from app.services.smart_note_service import smart_note_service
from app.utils.session_manager import session_manager
from app.crud import user as user_crud
from app.models.user import User
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# 存储WebSocket连接
class ConnectionManager:
    def __init__(self):
        # 按任务ID分组的连接
        self.task_connections: Dict[str, Set[WebSocket]] = {}
        # 所有活跃连接
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """连接WebSocket"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if task_id not in self.task_connections:
            self.task_connections[task_id] = set()
        self.task_connections[task_id].add(websocket)
        
        logger.info(f"WebSocket连接建立，任务ID: {task_id}")
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开WebSocket连接"""
        self.active_connections.discard(websocket)
        
        if task_id in self.task_connections:
            self.task_connections[task_id].discard(websocket)
            if not self.task_connections[task_id]:
                del self.task_connections[task_id]
        
        logger.info(f"WebSocket连接断开，任务ID: {task_id}")
    
    async def send_to_task(self, task_id: str, message: dict):
        """向特定任务的所有连接发送消息"""
        if task_id not in self.task_connections:
            return
        
        disconnected = set()
        for websocket in self.task_connections[task_id].copy():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                else:
                    disconnected.add(websocket)
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {e}")
                disconnected.add(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            self.disconnect(ws, task_id)
    
    async def send_to_all(self, message: dict):
        """向所有连接发送消息"""
        disconnected = set()
        for websocket in self.active_connections.copy():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                else:
                    disconnected.add(websocket)
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {e}")
                disconnected.add(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            self.active_connections.discard(ws)

# 全局连接管理器
manager = ConnectionManager()

def serialize_for_websocket(data):
    """序列化数据用于WebSocket传输"""
    if isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, dict):
        return {k: serialize_for_websocket(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_for_websocket(item) for item in data]
    elif hasattr(data, '__dict__'):
        return serialize_for_websocket(data.__dict__)
    else:
        return data

async def get_current_user_from_websocket(websocket: WebSocket) -> Optional[User]:
    """从WebSocket连接中获取当前用户"""
    try:
        # 从查询参数获取认证信息
        session_id = websocket.query_params.get("session_id")
        user_id = websocket.query_params.get("user_id")
        
        if not session_id or not user_id:
            # 尝试从cookies中获取（如果WebSocket支持）
            cookies = websocket.headers.get("cookie", "")
            if "session-id=" in cookies:
                for cookie in cookies.split(";"):
                    cookie = cookie.strip()
                    if cookie.startswith("session-id="):
                        session_id = cookie.split("=", 1)[1]
                    elif cookie.startswith("x-user-id="):
                        user_id = cookie.split("=", 1)[1]
        
        if not session_id or not user_id:
            return None
        
        # 验证session
        validated_user_id = session_manager.validate_session(session_id)
        if not validated_user_id or validated_user_id != user_id:
            return None
        
        # 获取用户信息
        db = next(get_db())
        db_user = user_crud.get(db, id=user_id)
        return db_user
        
    except Exception as e:
        logger.error(f"WebSocket认证失败: {e}")
        return None


@router.websocket("/task/{task_id}/ws")
async def websocket_task_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket端点，用于实时推送任务状态和结果"""
    try:
        # 验证用户身份（可选，根据需要启用）
        # user = await get_current_user_from_websocket(websocket)
        # if not user:
        #     await websocket.close(code=1008, reason="未授权")
        #     return
        
        await manager.connect(websocket, task_id)
        
        # 发送初始任务状态
        task = smart_note_service.get_task_status(task_id)
        if task:
            # 过滤掉不需要的字段
            safe_task = {k: v for k, v in task.items() if k not in ['image_data']}
            safe_task = serialize_for_websocket(safe_task)
            
            await websocket.send_text(json.dumps({
                "type": "initial_status",
                "data": safe_task
            }, ensure_ascii=False))
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": "任务不存在"}
            }, ensure_ascii=False))
            await websocket.close()
            return
        
        # 持续监控任务状态
        last_status = None
        last_progress = None
        last_step = None
        sent_intermediate_results = set()
        
        while True:
            try:
                current_task = smart_note_service.get_task_status(task_id)
                if not current_task:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {"message": "任务已被删除"}
                    }, ensure_ascii=False))
                    break
                
                # 检查并发送新的中间结果
                intermediate_results = current_task.get("intermediate_results", [])
                for i, result in enumerate(intermediate_results):
                    result_key = f"{result['type']}_{i}"
                    if result_key not in sent_intermediate_results:
                        # 序列化中间结果
                        safe_result = serialize_for_websocket(result)
                        await websocket.send_text(json.dumps({
                            "type": "intermediate_result",
                            "data": safe_result
                        }, ensure_ascii=False))
                        sent_intermediate_results.add(result_key)
                
                # 检查状态是否有变化
                status_changed = (
                    current_task["status"] != last_status or
                    current_task["progress"] != last_progress or
                    current_task["current_step"] != last_step
                )
                
                if status_changed:
                    # 发送状态更新
                    status_data = {
                        "task_id": current_task["task_id"],
                        "status": current_task["status"],
                        "progress": current_task["progress"],
                        "current_step": current_task["current_step"],
                        "error": current_task.get("error_message")
                    }
                    
                    await websocket.send_text(json.dumps({
                        "type": "status_update",
                        "data": status_data
                    }, ensure_ascii=False))
                    
                    last_status = current_task["status"]
                    last_progress = current_task["progress"]
                    last_step = current_task["current_step"]
                
                # 如果任务完成或失败，发送最终结果
                if current_task["status"] in ["completed", "failed"]:
                    if current_task["status"] == "completed":
                        result = current_task.get("result", {})
                        result_data = {
                            "task_id": current_task["task_id"],
                            "ocr_result": result.get("ocr_text"),
                            "corrected_result": result.get("corrected_text"),
                            "summary_result": result.get("summary"),
                            "content_id": result.get("content_id")
                        }
                        await websocket.send_text(json.dumps({
                            "type": "task_completed",
                            "data": result_data
                        }, ensure_ascii=False))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "task_failed",
                            "data": {"error": current_task.get("error_message", "处理失败")}
                        }, ensure_ascii=False))
                    
                    break
                
                # 等待0.5秒后继续检查
                await asyncio.sleep(0.5)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket监控过程中出错: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": f"监控错误: {str(e)}"}
                }, ensure_ascii=False))
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        manager.disconnect(websocket, task_id)

@router.websocket("/global/ws")
async def websocket_global_endpoint(websocket: WebSocket):
    """全局WebSocket端点，用于接收所有任务的更新"""
    try:
        await websocket.accept()
        manager.active_connections.add(websocket)
        
        await websocket.send_text(json.dumps({
            "type": "connected",
            "data": {"message": "已连接到全局WebSocket"}
        }, ensure_ascii=False))
        
        # 保持连接活跃
        while True:
            try:
                # 发送心跳
                await websocket.send_text(json.dumps({
                    "type": "heartbeat",
                    "data": {"timestamp": datetime.now().isoformat()}
                }, ensure_ascii=False))
                
                await asyncio.sleep(30)  # 每30秒发送一次心跳
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"全局WebSocket错误: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"全局WebSocket连接错误: {e}")
    finally:
        manager.active_connections.discard(websocket)

# 为智能笔记服务添加WebSocket推送功能
class WebSocketSmartNoteService:
    """扩展智能笔记服务，添加WebSocket推送功能"""
    
    @staticmethod
    async def push_status_update(task_id: str, status: str, current_step: str = None, progress: float = 0.0):
        """推送状态更新到WebSocket"""
        message = {
            "type": "status_update",
            "data": {
                "task_id": task_id,
                "status": status,
                "current_step": current_step,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            }
        }
        await manager.send_to_task(task_id, message)
    
    @staticmethod
    async def push_intermediate_result(task_id: str, result_type: str, data: dict):
        """推送中间结果到WebSocket"""
        message = {
            "type": "intermediate_result",
            "data": {
                "type": result_type,
                "data": serialize_for_websocket(data),
                "timestamp": datetime.now().isoformat()
            }
        }
        await manager.send_to_task(task_id, message)
    
    @staticmethod
    async def push_task_completed(task_id: str, result: dict):
        """推送任务完成到WebSocket"""
        message = {
            "type": "task_completed",
            "data": {
                "task_id": task_id,
                "result": serialize_for_websocket(result),
                "timestamp": datetime.now().isoformat()
            }
        }
        await manager.send_to_task(task_id, message)
    
    @staticmethod
    async def push_task_failed(task_id: str, error: str):
        """推送任务失败到WebSocket"""
        message = {
            "type": "task_failed",
            "data": {
                "task_id": task_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        }
        await manager.send_to_task(task_id, message)

# 导出WebSocket服务
websocket_service = WebSocketSmartNoteService()