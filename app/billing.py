from __future__ import annotations

import os
from typing import Optional

import requests
from sqlalchemy.orm import Session

from .models import Merchant, Plan, Usage
from .utils import current_month_key, get_plan_limit, plan_price

APP_URL = os.getenv("APP_URL", "http://localhost:8000")


def ensure_recurring_charge(shop: str, token: str, plan: Plan) -> Optional[dict]:
    """Create a pending recurring application charge and return the payload."""

    url = f"https://{shop}/admin/api/2023-10/recurring_application_charges.json"
    payload = {
        "recurring_application_charge": {
            "name": f"{plan.value.capitalize()} Plan",
            "price": plan_price(plan),
            "return_url": f"{APP_URL}/billing/activated?shop={shop}",
            "test": True,
        }
    }
    response = requests.post(
        url,
        headers={"X-Shopify-Access-Token": token},
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("recurring_application_charge", {})


def activate_recurring_charge(shop: str, token: str, charge_id: int) -> dict:
    """Finalize a merchant's accepted recurring application charge."""

    url = (
        f"https://{shop}/admin/api/2023-10/recurring_application_charges/"
        f"{charge_id}/activate.json"
    )
    payload = {"recurring_application_charge": {"id": charge_id}}
    response = requests.post(
        url,
        headers={"X-Shopify-Access-Token": token},
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def create_usage_charge(shop: str, token: str, recurring_charge_id: int, description: str, price: float) -> dict:
    """Create a usage-based charge on top of the base recurring subscription."""

    url = (
        f"https://{shop}/admin/api/2023-10/recurring_application_charges/"
        f"{recurring_charge_id}/usage_charges.json"
    )
    payload = {"usage_charge": {"description": description, "price": price}}
    response = requests.post(
        url,
        headers={"X-Shopify-Access-Token": token},
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def issue_usage_charge_if_needed(db: Session, merchant: Merchant) -> None:
    """Bill merchants for usage that exceeds their plan allocation."""

    month = current_month_key()
    usage = (
        db.query(Usage)
        .filter(Usage.merchant_id == merchant.id, Usage.month_key == month)
        .first()
    )
    used = usage.processed_emails if usage else 0
    limit = get_plan_limit(merchant.plan)
    if used <= limit:
        return

    overage = used - limit
    if not merchant.recurring_charge_id:
        # Without an activated subscription we cannot issue usage-based charges yet.
        return

    price = round(overage * 0.02, 2)
    create_usage_charge(
        merchant.shop,
        merchant.access_token,
        merchant.recurring_charge_id,
        description=f"Overage: {overage} emails",
        price=price,
    )
    if usage:
        usage.billed = True
        db.commit()
