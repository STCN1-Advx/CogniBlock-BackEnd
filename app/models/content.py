from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(50), nullable=False)  # 'image', 'text', 'ocr'
    image_data = Column(Text, nullable=True)  # Base64 编码的图片
    text_data = Column(Text, nullable=True)
    
    # OCR识别相关字段
    ocr_result = Column(Text, nullable=True)  # OCR识别的原始结果（Markdown格式）
    ocr_status = Column(String(20), nullable=True)  # OCR状态：pending, processing, completed, failed
    
    # 笔记总结相关字段
    summary_title = Column(String(500), nullable=True)  # 总结标题
    summary_topic = Column(String(200), nullable=True)  # 总结主题
    summary_content = Column(Text, nullable=True)  # 总结内容（Markdown格式）
    summary_status = Column(String(20), nullable=True)  # 总结状态：pending, processing, completed, failed
    content_hash = Column(String(64), nullable=True, index=True)  # 内容哈希，用于缓存查询
    
    # 文件信息
    filename = Column(String(255), nullable=True)  # 原始文件名
    file_size = Column(Integer, nullable=True)  # 文件大小（字节）
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    cards = relationship("Card", back_populates="content")
    user_contents = relationship("UserContent", back_populates="content", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Content(id={self.id}, content_type='{self.content_type}')>"