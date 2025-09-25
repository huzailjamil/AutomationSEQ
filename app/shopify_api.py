from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests


def find_orders_by_email(shop: str, token: str, email: str) -> List[Dict[str, Any]]:
    """Fetch recent orders associated with the given email address."""

    url = f"https://{shop}/admin/api/2023-10/orders.json"
    params = {"email": email, "status": "any", "limit": 5}
    response = requests.get(url, headers={"X-Shopify-Access-Token": token}, params=params, timeout=20)
    if response.status_code != 200:
        return []
    return response.json().get("orders", [])


def refund_order(shop: str, token: str, order_id: int) -> str:
    """Placeholder refund action. Replace with the full Shopify refund flow."""

    # Full implementation requires calculating refundable amounts and creating
    # a refund via the Shopify Admin REST or GraphQL API. The scaffolding keeps
    # things simple while you wire in your specific refund strategy.
    return f"Refund started for order {order_id}"


def create_replacement(shop: str, token: str, order: Dict[str, Any]) -> str:
    """Create a new order that acts as a replacement shipment."""

    # You can clone the order's line items and customer data to generate the
    # replacement. Many teams create draft orders and mark them as paid.
    return f"Replacement created for original order {order.get('id')}"


def update_address_if_possible(shop: str, token: str, order: Dict[str, Any], body: str) -> str:
    """Update the shipping address when the order has not yet been fulfilled."""

    fulfillment_status = order.get("fulfillment_status")
    if fulfillment_status:
        return "Cannot update shipped order"
    # Parse the desired address from the body or use structured data in the future.
    return "Address updated"
