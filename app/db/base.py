from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 创建数据库引擎，确保使用UTF-8编码
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    connect_args={
        "options": "-c client_encoding=utf8"
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
