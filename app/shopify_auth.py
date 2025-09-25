import os
from typing import Dict
from urllib.parse import urlencode

import requests

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
SCOPES = "read_orders,write_orders"
REDIRECT_URI = f"{APP_URL}/callback"


def build_install_url(shop: str) -> str:
    """Return the Shopify OAuth consent screen URL for the merchant store."""

    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
    }
    return f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"


def exchange_token(params: Dict[str, str]) -> Dict[str, str]:
    """Exchange the OAuth code for a permanent access token."""

    shop = params.get("shop")
    code = params.get("code")
    if not shop or not code:
        return {}

    url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code,
    }
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()
