from sqlalchemy import Column, BigInteger, String, Text, DateTime, Boolean, Integer
from sqlalchemy.sql import func
from database.connection import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)  # JSON data
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FAQItem(Base):
    __tablename__ = "faq_items"
    
    id = Column(BigInteger, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100))
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BroadcastMessage(Base):
    __tablename__ = "broadcast_messages"
    
    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String(255))
    content = Column(Text, nullable=False)
    target_audience = Column(String(50))  # all, active, expired, trial
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_by = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    scheduled_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))