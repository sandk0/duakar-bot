from sqlalchemy import Column, BigInteger, String, Boolean, Text, DateTime, ForeignKey, Date, Integer, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base


class VPNConfig(Base):
    __tablename__ = "vpn_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    marzban_user_id = Column(String(255), unique=True)
    config_data = Column(Text)
    qr_code_data = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    updated_at = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    
    # Relationships
    user = relationship("User", back_populates="vpn_configs")


class UsageStat(Base):
    __tablename__ = "usage_stats"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    bytes_uploaded = Column(BigInteger, default=0)
    bytes_downloaded = Column(BigInteger, default=0)
    connections_count = Column(Integer, default=0)
    unique_ips = Column(ARRAY(String))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="usage_stats")