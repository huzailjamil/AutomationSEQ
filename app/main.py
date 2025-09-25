from __future__ import annotations

import os
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .ai import classify_intent, generate_reply
from .billing import (
    activate_recurring_charge,
    ensure_recurring_charge,
    issue_usage_charge_if_needed,
)
from .email_service import send_email_smtp
from .models import Base, Merchant, Plan, Ticket, Usage
from .shopify_api import (
    create_replacement,
    find_orders_by_email,
    refund_order,
    update_address_if_possible,
)
from .shopify_auth import build_install_url, exchange_token
from .utils import current_month_key, get_plan_limit, safe_language

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

app = FastAPI(title="Shopify AI Support (Public App)")


class EmailWebhookPayload(BaseModel):
    sender: str
    subject: Optional[str] = ""
    body: Optional[str] = ""


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def health() -> dict:
    return {"ok": True}


@app.get("/install")
def install(shop: str) -> RedirectResponse:
    return RedirectResponse(build_install_url(shop))


@app.get("/callback")
def callback(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    params = dict(request.query_params)
    shop = params.get("shop")
    token_payload = exchange_token(params)
    access_token = token_payload.get("access_token") if token_payload else None
    if not shop or not access_token:
        raise HTTPException(status_code=400, detail="OAuth exchange failed")

    merchant = db.query(Merchant).filter(Merchant.shop == shop).first()
    if not merchant:
        merchant = Merchant(shop=shop, access_token=access_token, plan=Plan.BASIC)
        db.add(merchant)
    else:
        merchant.access_token = access_token
    db.commit()

    charge = ensure_recurring_charge(shop, access_token, plan=merchant.plan)
    confirmation_url = None
    if charge:
        merchant.pending_recurring_charge_id = charge.get("id")
        db.commit()
        confirmation_url = charge.get("confirmation_url")

    redirect_target = confirmation_url or f"{APP_URL}/dashboard?shop={shop}"
    return RedirectResponse(redirect_target)


@app.get("/api/usage")
def get_usage(shop: str, db: Session = Depends(get_db)) -> dict:
    merchant = db.query(Merchant).filter(Merchant.shop == shop).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    usage = (
        db.query(Usage)
        .filter(Usage.merchant_id == merchant.id, Usage.month_key == current_month_key())
        .first()
    )
    used = usage.processed_emails if usage else 0
    return {"plan": merchant.plan.value, "limit": get_plan_limit(merchant.plan), "used": used}


@app.get("/api/tickets")
def list_tickets(shop: str, db: Session = Depends(get_db)) -> dict:
    merchant = db.query(Merchant).filter(Merchant.shop == shop).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    tickets = (
        db.query(Ticket)
        .filter(Ticket.merchant_id == merchant.id)
        .order_by(Ticket.created_at.desc())
        .limit(100)
        .all()
    )
    serialized = [
        {
            "id": ticket.id,
            "sender": ticket.sender,
            "subject": ticket.subject,
            "intent": ticket.intent,
            "order_id": ticket.order_id,
            "flagged": ticket.flagged,
            "auto_sent": ticket.auto_sent,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        }
        for ticket in tickets
    ]
    return {"tickets": serialized}


@app.post("/emails/webhook")
async def email_webhook(
    shop: str,
    payload: EmailWebhookPayload,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    merchant = db.query(Merchant).filter(Merchant.shop == shop).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    limit = get_plan_limit(merchant.plan)
    usage = (
        db.query(Usage)
        .filter(Usage.merchant_id == merchant.id, Usage.month_key == current_month_key())
        .first()
    )
    used = usage.processed_emails if usage else 0
    if used >= limit:
        message = (
            "You've reached your monthly automation quota. Please upgrade to continue "
            "automated support."
        )
        background.add_task(
            send_email_smtp,
            to=payload.sender,
            subject=f"Re: {payload.subject or 'Support'}",
            body=message,
        )
        ticket = Ticket(
            merchant_id=merchant.id,
            sender=payload.sender,
            subject=payload.subject,
            body=payload.body,
            intent="blocked_quota",
            auto_sent=True,
            result=message,
        )
        db.add(ticket)
        db.commit()
        return {"blocked": True, "reason": "quota_reached"}

    email_body = payload.body or ""
    intent = classify_intent(email_body)
    if intent == "spam":
        ticket = Ticket(
            merchant_id=merchant.id,
            sender=payload.sender,
            subject=payload.subject,
            body=email_body,
            intent="spam",
            auto_sent=False,
        )
        db.add(ticket)
        db.commit()
        return {"skipped": "spam"}

    orders = find_orders_by_email(shop=merchant.shop, token=merchant.access_token, email=payload.sender)
    order = orders[0] if orders else None

    flagged = False
    action_note: Optional[str] = None
    if intent == "refund_request" and order:
        action_note = refund_order(shop=merchant.shop, token=merchant.access_token, order_id=order.get("id"))
    elif intent == "replacement_request" and order:
        action_note = create_replacement(shop=merchant.shop, token=merchant.access_token, order=order)
    elif intent == "address_change" and order:
        action_note = update_address_if_possible(
            shop=merchant.shop,
            token=merchant.access_token,
            order=order,
            body=email_body,
        )
    elif intent == "not_received_but_delivered":
        flagged = True

    reply = generate_reply(
        intent=intent,
        merchant_name=merchant.shop,
        customer_email=payload.sender,
        order=order,
        action_note=action_note,
        body=email_body,
        language=safe_language(email_body),
    )

    background.add_task(
        send_email_smtp,
        to=payload.sender,
        subject=f"Re: {payload.subject or 'Support'}",
        body=reply,
    )

    ticket = Ticket(
        merchant_id=merchant.id,
        sender=payload.sender,
        subject=payload.subject,
        body=email_body,
        intent=intent,
        order_id=str(order.get("id")) if order and order.get("id") else None,
        flagged=flagged,
        auto_sent=True,
        result=reply,
    )
    db.add(ticket)

    if not usage:
        usage = Usage(merchant_id=merchant.id, month_key=current_month_key(), processed_emails=0)
        db.add(usage)
    usage.processed_emails += 1
    db.commit()

    return {"ok": True, "intent": intent, "flagged": flagged}


@app.post("/billing/run")
def run_billing(shop: str, db: Session = Depends(get_db)) -> dict:
    merchant = db.query(Merchant).filter(Merchant.shop == shop).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    issue_usage_charge_if_needed(db, merchant=merchant)
    return {"ok": True}


@app.get("/billing/activated")
def billing_activated(shop: str, charge_id: int, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.shop == shop).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    if merchant.pending_recurring_charge_id and merchant.pending_recurring_charge_id != charge_id:
        raise HTTPException(status_code=400, detail="Charge ID mismatch")

    activate_recurring_charge(shop=merchant.shop, token=merchant.access_token, charge_id=charge_id)

    merchant.recurring_charge_id = charge_id
    merchant.pending_recurring_charge_id = None
    db.commit()

    return RedirectResponse(f"{APP_URL}/dashboard?shop={shop}")
