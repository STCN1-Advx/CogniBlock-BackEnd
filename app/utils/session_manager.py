import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SessionInfo:
    """Session信息数据类"""
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    
    def is_expired(self) -> bool:
        """检查session是否已过期"""
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """检查session是否有效（未过期）"""
        return not self.is_expired()
    
    def refresh(self, extend_hours: int = 24) -> None:
        """刷新session过期时间"""
        self.last_accessed = datetime.now()
        self.expires_at = datetime.now() + timedelta(hours=extend_hours)


class SessionManager:
    """Session管理器
    
    在生产环境中应该使用Redis等持久化存储，
    这里使用内存存储仅用于开发和测试。
    """
    
    def __init__(self):
        self._sessions: Dict[str, SessionInfo] = {}
    
    def create_session(self, user_id: str, session_duration_hours: int = 24) -> str:
        """创建新的session
        
        Args:
            user_id: 用户ID
            session_duration_hours: session持续时间（小时）
            
        Returns:
            session_id: 生成的session ID
        """
        session_id = secrets.token_urlsafe(32)
        now = datetime.now()
        
        session_info = SessionInfo(
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(hours=session_duration_hours),
            last_accessed=now
        )
        
        self._sessions[session_id] = session_info
        
        # 清理过期的session
        self._cleanup_expired_sessions()
        
        print(f"🔑 [Session] 创建新session: {session_id[:8]}... for user: {user_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """获取session信息
        
        Args:
            session_id: session ID
            
        Returns:
            SessionInfo对象，如果session不存在或已过期则返回None
        """
        if not session_id or session_id not in self._sessions:
            return None
        
        session_info = self._sessions[session_id]
        
        # 检查是否过期
        if session_info.is_expired():
            print(f"⏰ [Session] Session已过期，删除: {session_id[:8]}...")
            del self._sessions[session_id]
            return None
        
        # 更新最后访问时间
        session_info.last_accessed = datetime.now()
        
        return session_info
    
    def validate_session(self, session_id: str) -> Optional[str]:
        """验证session并返回用户ID
        
        Args:
            session_id: session ID
            
        Returns:
            用户ID，如果session无效则返回None
        """
        session_info = self.get_session(session_id)
        if session_info and session_info.is_valid():
            return session_info.user_id
        return None
    
    def refresh_session(self, session_id: str, extend_hours: int = 24) -> bool:
        """刷新session过期时间
        
        Args:
            session_id: session ID
            extend_hours: 延长的小时数
            
        Returns:
            是否刷新成功
        """
        session_info = self.get_session(session_id)
        if session_info:
            session_info.refresh(extend_hours)
            print(f"🔄 [Session] Session已刷新: {session_id[:8]}...")
            return True
        return False
    
    def revoke_session(self, session_id: str) -> bool:
        """撤销session
        
        Args:
            session_id: session ID
            
        Returns:
            是否撤销成功
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            print(f"🗑️ [Session] Session已撤销: {session_id[:8]}...")
            return True
        return False
    
    def revoke_user_sessions(self, user_id: str) -> int:
        """撤销用户的所有session
        
        Args:
            user_id: 用户ID
            
        Returns:
            撤销的session数量
        """
        sessions_to_remove = [
            session_id for session_id, session_info in self._sessions.items()
            if session_info.user_id == user_id
        ]
        
        for session_id in sessions_to_remove:
            del self._sessions[session_id]
        
        print(f"🗑️ [Session] 撤销用户 {user_id} 的 {len(sessions_to_remove)} 个session")
        return len(sessions_to_remove)
    
    def _cleanup_expired_sessions(self) -> int:
        """清理过期的session
        
        Returns:
            清理的session数量
        """
        now = datetime.now()
        expired_sessions = [
            session_id for session_id, session_info in self._sessions.items()
            if session_info.expires_at < now
        ]
        
        for session_id in expired_sessions:
            del self._sessions[session_id]
        
        if expired_sessions:
            print(f"🧹 [Session] 清理了 {len(expired_sessions)} 个过期session")
        
        return len(expired_sessions)
    
    def get_session_count(self) -> int:
        """获取当前session数量"""
        return len(self._sessions)
    
    def get_user_session_count(self, user_id: str) -> int:
        """获取指定用户的session数量"""
        return sum(1 for session_info in self._sessions.values() 
                  if session_info.user_id == user_id)


# 全局session管理器实例
session_manager = SessionManager()