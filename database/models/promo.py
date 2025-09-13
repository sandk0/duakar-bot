from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Numeric, Integer, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from enum import Enum


class PromoType(str, Enum):
    PERCENT = "percent"
    FIXED = "fixed"
    DAYS = "days"


class PromoCode(Base):
    __tablename__ = "promo_codes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False)
    value = Column(Numeric(10, 2), nullable=False)
    max_uses = Column(Integer)
    current_uses = Column(Integer, default=0)
    valid_from = Column(DateTime(timezone=True))
    valid_until = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(BigInteger, ForeignKey("users.id"))
    
    # Relationships
    usages = relationship("PromoUsage", back_populates="promo_code")


class PromoUsage(Base):
    __tablename__ = "promo_usages"
    
    id = Column(BigInteger, primary_key=True, index=True)
    promo_code_id = Column(BigInteger, ForeignKey("promo_codes.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    payment_id = Column(BigInteger, ForeignKey("payments.id"))
    used_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    promo_code = relationship("PromoCode", back_populates="usages")
    user = relationship("User", back_populates="promo_usages")