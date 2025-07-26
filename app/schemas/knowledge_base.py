from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class KnowledgeBaseStats(BaseModel):
    """
    知识库统计信息模型
    """
    knowledge_base_count: int  # 用户有权限的知识库数量
    total_content_count: int   # 用户有权限的总内容数
    last_updated_at: Optional[datetime]  # 最近一次更新任何资产的时间
    user_id: str  # 用户ID
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }