from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Numeric, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from enum import Enum


class PlanType(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    TRIAL = "trial"
    PENDING = "pending"


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("pricing_plans.id"), nullable=False)
    status = Column(String(20), default="pending")
    start_date = Column(DateTime(timezone=False))
    end_date = Column(DateTime(timezone=False))
    auto_renew = Column(Boolean, default=False)
    payment_id = Column(Integer)
    created_at = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    updated_at = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("PricingPlan")


class PricingPlan(Base):
    __tablename__ = "pricing_plans"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB")
    duration_days = Column(Integer, nullable=False)
    plan_type = Column(String(20), default="regular")
    is_active = Column(Boolean, default=True)
    features = Column(Text)  # JSON data
    created_at = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    
    # Relationships
    payments = relationship("Payment", back_populates="pricing_plan")