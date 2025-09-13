from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    SBP = "sbp"
    CARD = "card"
    YOOMONEY = "yoomoney"


class PaymentSystem(str, Enum):
    WATA = "wata"
    YOOKASSA = "yookassa"


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    plan_id = Column(BigInteger, ForeignKey("pricing_plans.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB")
    status = Column(String(20), default=PaymentStatus.PENDING)
    system = Column(String(20), nullable=False)
    external_id = Column(String(255), unique=True)
    payment_url = Column(Text)
    meta = Column("metadata", Text)  # JSON data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="payments")
    pricing_plan = relationship("PricingPlan", back_populates="payments")