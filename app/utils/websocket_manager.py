import asyncio
import json
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储用户的WebSocket连接
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"用户 {user_id} 建立WebSocket连接")
        
        # 发送连接成功消息
        await self.send_message(user_id, {
            "type": "connection_established",
            "message": "WebSocket连接已建立",
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # 如果用户没有其他连接，删除用户记录
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"用户 {user_id} 断开WebSocket连接")
    
    async def send_message(self, user_id: str, message: Dict[str, Any]):
        """向指定用户发送消息"""
        if user_id not in self.active_connections:
            logger.warning(f"用户 {user_id} 没有活跃的WebSocket连接")
            return
        
        # 准备消息
        message_text = json.dumps(message, ensure_ascii=False)
        
        # 向用户的所有连接发送消息
        disconnected_connections = set()
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                disconnected_connections.add(websocket)
        
        # 清理断开的连接
        for websocket in disconnected_connections:
            self.active_connections[user_id].discard(websocket)
        
        # 如果用户没有其他连接，删除用户记录
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """向所有用户广播消息"""
        message_text = json.dumps(message, ensure_ascii=False)
        
        for user_id in list(self.active_connections.keys()):
            await self.send_message_to_user_connections(user_id, message_text)
    
    async def send_message_to_user_connections(self, user_id: str, message_text: str):
        """向用户的所有连接发送消息"""
        if user_id not in self.active_connections:
            return
        
        disconnected_connections = set()
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                disconnected_connections.add(websocket)
        
        # 清理断开的连接
        for websocket in disconnected_connections:
            self.active_connections[user_id].discard(websocket)
        
        # 如果用户没有其他连接，删除用户记录
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]
    
    def get_user_connection_count(self, user_id: str) -> int:
        """获取用户的连接数量"""
        return len(self.active_connections.get(user_id, set()))
    
    def get_total_connections(self) -> int:
        """获取总连接数"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_active_users(self) -> Set[str]:
        """获取活跃用户列表"""
        return set(self.active_connections.keys())

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()