from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Plan(str, enum.Enum):
    """Subscription tiers for merchants."""

    BASIC = "basic"
    PRO = "pro"
    SCALE = "scale"


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True)
    shop = Column(String, unique=True, index=True, nullable=False)
    access_token = Column(Text, nullable=False)
    plan = Column(Enum(Plan), default=Plan.BASIC, nullable=False)
    email_connected = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    usage = relationship("Usage", back_populates="merchant", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="merchant", cascade="all, delete-orphan")


class Usage(Base):
    __tablename__ = "usage"

    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), index=True, nullable=False)
    month_key = Column(String, index=True, nullable=False)
    processed_emails = Column(Integer, default=0)
    billed = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("merchant_id", "month_key", name="uniq_usage_month"),
    )

    merchant = relationship("Merchant", back_populates="usage")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), index=True, nullable=False)
    sender = Column(String, index=True, nullable=False)
    subject = Column(String)
    body = Column(Text)
    intent = Column(String, index=True)
    order_id = Column(String)
    flagged = Column(Boolean, default=False)
    auto_sent = Column(Boolean, default=False)
    result = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    merchant = relationship("Merchant", back_populates="tickets")
