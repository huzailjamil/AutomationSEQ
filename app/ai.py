from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_DIR = BASE_DIR / "prompts"
INTENT_PROMPT_PATH = PROMPT_DIR / "intent_classifier_prompt.txt"
REPLY_PROMPT_PATH = PROMPT_DIR / "reply_generator_prompt.txt"

ALLOWED_INTENTS = {
    "tracking_request",
    "refund_request",
    "replacement_request",
    "wrong_item",
    "partial_order",
    "address_change",
    "not_received_but_delivered",
    "warranty_defect",
    "general_question",
    "spam",
}

_client = OpenAI()


def _load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt template missing: {path}")
    return path.read_text(encoding="utf-8")


def _format_prompt(template: str, **kwargs: Any) -> str:
    text = template
    for key, value in kwargs.items():
        placeholder = f"{{{{{key}}}}}"
        text = text.replace(placeholder, str(value))
    return text


def classify_intent(email_body: str) -> str:
    """Call OpenAI to classify the inbound email intent."""

    template = _load_prompt(INTENT_PROMPT_PATH)
    prompt = _format_prompt(template, EMAIL_BODY=email_body)
    response = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    label = response.choices[0].message.content.strip()
    return label if label in ALLOWED_INTENTS else "general_question"


def generate_reply(
    intent: str,
    merchant_name: str,
    customer_email: str,
    order: Optional[Dict[str, Any]],
    action_note: Optional[str],
    body: str,
    language: str = "en",
    policy_snippets: Optional[str] = None,
    customer_name: Optional[str] = None,
) -> str:
    """Generate a polished support reply tailored to the request."""

    template = _load_prompt(REPLY_PROMPT_PATH)
    order_ctx: Dict[str, Any] = {
        "id": order.get("id") if order else None,
        "name": order.get("name") if order else None,
        "fulfillment_status": order.get("fulfillment_status") if order else None,
        "tracking_numbers": [],
        "tracking_urls": [],
        "action_note": action_note,
    }
    if order:
        fulfillments = order.get("fulfillments") or []
        for fulfillment in fulfillments:
            if tracking_numbers := fulfillment.get("tracking_numbers"):
                order_ctx["tracking_numbers"].extend(tracking_numbers)
            if tracking_url := fulfillment.get("tracking_url"):
                order_ctx["tracking_urls"].append(tracking_url)

    formatted_prompt = _format_prompt(
        template,
        MERCHANT_NAME=merchant_name,
        INTENT=intent,
        CUSTOMER_EMAIL=customer_email,
        CUSTOMER_NAME=customer_name or "",
        ORDER_CONTEXT_JSON=json.dumps(order_ctx, ensure_ascii=False),
        POLICY_SNIPPETS=policy_snippets or "",
    )
    formatted_prompt = f"{formatted_prompt}\n\nCustomer email body:\n{body}\n\nPreferred language: {language}"

    response = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": formatted_prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()
