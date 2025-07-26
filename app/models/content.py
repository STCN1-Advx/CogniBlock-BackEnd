from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(50), nullable=False)  # 'image', 'text'
    image_data = Column(Text, nullable=True)  # Base64 编码的图片
    text_data = Column(Text, nullable=True)
    filename = Column(String(255), nullable=True)  # 文件名
    
    # 笔记总结相关字段
    summary_title = Column(String(255), nullable=True)  # 总结标题
    summary_content = Column(Text, nullable=True)  # 总结内容（Markdown格式）
    summary_status = Column(String(20), nullable=True)  # 总结状态：pending, processing, completed, failed
    content_hash = Column(String(64), nullable=True, index=True)  # 内容哈希，用于缓存查询
    
    # 知识库记录相关字段
    knowledge_title = Column(String(500), nullable=True)  # 知识库记录标题
    knowledge_date = Column(String(20), nullable=True)  # 知识库记录日期 (YYYY-MM-DD)
    knowledge_preview = Column(Text, nullable=True)  # 知识库记录预览内容（Markdown格式）
    
    # 文字模式相关字段
    original_text = Column(Text, nullable=True)  # 原始输入文字（用于文字模式）
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    cards = relationship("Card", back_populates="content")
    user_contents = relationship("UserContent", back_populates="content", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Content(id={self.id}, content_type='{self.content_type}')>"