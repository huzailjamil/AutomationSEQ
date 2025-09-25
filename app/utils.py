import os
import datetime
from typing import Iterable, Optional

from .models import Plan


def current_month_key() -> str:
    """Return the YYYY-MM string used to bucket usage."""

    now = datetime.datetime.utcnow()
    return f"{now.year}-{now.month:02d}"


def get_plan_limit(plan: Plan) -> int:
    """Look up the monthly included email limit for the merchant's plan."""

    limits = {
        Plan.BASIC: int(os.getenv("PLAN_BASIC_LIMIT", 5000)),
        Plan.PRO: int(os.getenv("PLAN_PRO_LIMIT", 15000)),
        Plan.SCALE: int(os.getenv("PLAN_SCALE_LIMIT", 50000)),
    }
    return limits[plan]


def plan_price(plan: Plan) -> float:
    """Return the monthly subscription price for the selected plan."""

    prices = {
        Plan.BASIC: float(os.getenv("PLAN_BASIC_PRICE", 249)),
        Plan.PRO: float(os.getenv("PLAN_PRO_PRICE", 499)),
        Plan.SCALE: float(os.getenv("PLAN_SCALE_PRICE", 999)),
    }
    return prices[plan]


def safe_language(text: Optional[str]) -> str:
    """Very small helper that defaults to English but leaves room for future logic."""

    if not text:
        return "en"
    # Hook for language detection model/library.
    return "en"


def chunk(iterable: Iterable, size: int):
    """Yield successive chunks from an iterable; convenient for pagination helpers."""

    bucket = []
    for item in iterable:
        bucket.append(item)
        if len(bucket) == size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket
