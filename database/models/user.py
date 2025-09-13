from sqlalchemy import Column, BigInteger, String, Boolean, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from database.connection import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    phone_number = Column(String(20))
    email = Column(String(255))
    language_code = Column(String(5), default="ru")
    status = Column(String(20), default="active")
    trial_used = Column(Boolean, default=False)
    referral_code = Column(String(50), unique=True)
    notifications_enabled = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=False)
    bonus_days = Column(Integer, default=0)
    referred_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    updated_at = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    last_activity = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    vpn_configs = relationship("VPNConfig", back_populates="user", cascade="all, delete-orphan")
    usage_stats = relationship("UsageStat", back_populates="user", cascade="all, delete-orphan")
    referrals = relationship("User", remote_side=[id], foreign_keys=[referred_by])
    referral_stats = relationship("ReferralStat", back_populates="user", uselist=False)
    action_logs = relationship("ActionLog", back_populates="user", cascade="all, delete-orphan")
    promo_usages = relationship("PromoUsage", back_populates="user", cascade="all, delete-orphan")


class ReferralStat(Base):
    __tablename__ = "referral_stats"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), unique=True)
    referral_count = Column(Integer, default=0)
    bonus_days_earned = Column(Integer, default=0)
    bonus_days_used = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="referral_stats")


class ActionLog(Base):
    __tablename__ = "action_logs"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    action_type = Column(String(100), nullable=False)
    action_data = Column(Text)  # JSON data
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="action_logs")