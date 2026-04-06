"""
Stage 1: Market Scanner — deterministic pre-filter + bias-opportunity scoring.

Fetches all active Polymarket markets via Gamma API, applies hard filters
(no LLM, zero cost), scores survivors on bias-opportunity signals, and
returns ranked top-N candidates for downstream evaluation.

Replaces the RAG-based event filtering in trade.py.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from dateutil import parser as dateutil_parser
from pydantic import BaseModel

from agents.polymarket.gamma import GammaMarketClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class MarketScores(BaseModel):
    price_extreme: float       # 0-1, deviation from 50/50 (favorite-longshot proxy)
    volume_momentum: float     # 0-1, 24hr volume concentration (overreaction proxy)
    volume_signal: float       # 0-1, retail activity ratio
    spread_quality: float      # 0-1, tighter spread = higher
    narrative_density: float   # 0-1, description richness
    composite: float           # weighted sum


class ScoredMarket(BaseModel):
    market_id: str
    question: str
    description: str
    end_date: str
    days_to_resolution: float
    liquidity: float
    volume_24hr: float
    volume_1wk: float
    spread: float
    outcome_prices: list[float]
    outcomes: list[str]
    clob_token_ids: list[str]
    category: str  # "sports", "crypto", "other"
    scores: MarketScores
    tags: list[str] = []
    raw: dict = {}


class ScanResult(BaseModel):
    timestamp: str
    total_fetched: int
    passed_prefilter: int
    returned: int
    markets: list[ScoredMarket]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ScannerError(Exception):
    pass


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class Scanner:
    DEFAULT_CONFIG = {
        "min_liquidity": 100_000.0,
        "min_hours_to_resolution": 6,
        "max_days_to_resolution": 2.0,
        "min_description_length": 50,
        "top_n": 0,  # 0 = return all passing markets
        "weights": {
            "price_extreme": 0.30,
            "volume_momentum": 0.25,
            "volume_signal": 0.20,
            "spread_quality": 0.15,
            "narrative_density": 0.10,
        },
    }

    def __init__(self, gamma: Optional[GammaMarketClient] = None, config: Optional[dict] = None):
        self.gamma = gamma or GammaMarketClient()
        self.cfg = {**self.DEFAULT_CONFIG, **(config or {})}

    # -------------------------------------------------------------------
    # Public
    # -------------------------------------------------------------------

    def scan(self) -> ScanResult:
        """Full scan: fetch → filter → score → rank → return top N."""
        raw_markets = self._fetch_all_markets()
        filtered = self._apply_prefilters(raw_markets)

        scored: list[ScoredMarket] = []
        for m in filtered:
            try:
                scored.append(self._score_market(m))
            except Exception as e:
                logger.warning("Skipping market %s: %s", m.get("id", "?"), e)

        scored.sort(key=lambda s: s.scores.composite, reverse=True)
        top_n = self.cfg["top_n"]
        top = scored if top_n <= 0 else scored[:top_n]

        return ScanResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_fetched=len(raw_markets),
            passed_prefilter=len(filtered),
            returned=len(top),
            markets=top,
        )

    # -------------------------------------------------------------------
    # Fetch
    # -------------------------------------------------------------------

    def _fetch_all_markets(self) -> list[dict]:
        """Fetch active markets within the resolution window using server-side date filtering."""
        now = datetime.now(timezone.utc)
        min_end = now + timedelta(hours=self.cfg["min_hours_to_resolution"])
        max_end = now + timedelta(days=self.cfg["max_days_to_resolution"])

        base_params = {
            "active": True,
            "closed": False,
            "archived": False,
            "end_date_min": min_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_date_max": max_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        page_size = 500  # Gamma API max
        offset = 0
        all_markets: list[dict] = []

        try:
            while True:
                params = {**base_params, "limit": page_size, "offset": offset}
                resp = httpx.get(
                    self.gamma.gamma_markets_endpoint, params=params, timeout=15
                )
                resp.raise_for_status()
                batch = resp.json()
                all_markets.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
        except Exception as e:
            raise ScannerError(f"Gamma API fetch failed: {e}") from e

        return all_markets

    # -------------------------------------------------------------------
    # Pre-filters
    # -------------------------------------------------------------------

    def _apply_prefilters(self, markets: list[dict]) -> list[dict]:
        passed = []
        for m in markets:
            if not self._passes_prefilter(m):
                continue
            passed.append(m)
        return passed

    def _passes_prefilter(self, m: dict) -> bool:
        # 1. Tradeable
        if not m.get("enableOrderBook"):
            return False
        if not m.get("acceptingOrders"):
            return False

        # 2. Liquidity
        liquidity = _safe_float(m.get("liquidity"))
        if liquidity < self.cfg["min_liquidity"]:
            return False

        # 3. Resolution window: 6h < remaining < 2d
        end_date = _parse_end_date(m.get("endDate"))
        if end_date is None:
            return False
        now = datetime.now(timezone.utc)
        remaining = end_date - now
        remaining_hours = remaining.total_seconds() / 3600
        min_hours = self.cfg["min_hours_to_resolution"]
        max_hours = self.cfg["max_days_to_resolution"] * 24
        if remaining_hours < min_hours or remaining_hours > max_hours:
            return False

        # 4. Valid prices
        prices = _parse_outcome_prices(m.get("outcomePrices"))
        if prices is None or len(prices) < 2:
            return False
        if not all(0 <= p <= 1 for p in prices):
            return False

        # 5. Has description
        desc = m.get("description") or ""
        if len(desc) < self.cfg["min_description_length"]:
            return False

        return True

    # -------------------------------------------------------------------
    # Scoring
    # -------------------------------------------------------------------

    def _score_market(self, m: dict) -> ScoredMarket:
        prices = _parse_outcome_prices(m.get("outcomePrices"))
        liquidity = _safe_float(m.get("liquidity"))
        volume_24hr = _safe_float(m.get("volume24hr"))
        volume_1wk = _safe_float(m.get("volume1wk"))
        spread = _safe_float(m.get("spread"))
        desc = m.get("description") or ""
        end_date = _parse_end_date(m.get("endDate"))
        category = _derive_category(m)

        now = datetime.now(timezone.utc)
        days_to_res = (end_date - now).total_seconds() / 86400 if end_date else 0.0

        outcomes_raw = m.get("outcomes")
        if isinstance(outcomes_raw, str):
            try:
                outcomes = json.loads(outcomes_raw)
            except (json.JSONDecodeError, TypeError):
                outcomes = [outcomes_raw]
        elif isinstance(outcomes_raw, list):
            outcomes = outcomes_raw
        else:
            outcomes = []

        clob_ids = _parse_list_field(m.get("clobTokenIds"))

        tags_raw = m.get("tags")
        if isinstance(tags_raw, list):
            tags = [t.get("label", str(t)) if isinstance(t, dict) else str(t) for t in tags_raw]
        else:
            tags = []

        w = self.cfg["weights"]
        pe = self._score_price_extreme(prices)
        vm = self._score_volume_momentum(volume_24hr, volume_1wk)
        vs = self._score_volume_signal(volume_24hr, liquidity)
        sq = self._score_spread_quality(spread)
        nd = self._score_narrative_density(desc)
        composite = (
            pe * w["price_extreme"]
            + vm * w["volume_momentum"]
            + vs * w["volume_signal"]
            + sq * w["spread_quality"]
            + nd * w["narrative_density"]
        )

        return ScoredMarket(
            market_id=str(m.get("id", "")),
            question=m.get("question", ""),
            description=desc,
            end_date=end_date.isoformat() if end_date else "",
            days_to_resolution=round(days_to_res, 3),
            liquidity=liquidity,
            volume_24hr=volume_24hr,
            volume_1wk=volume_1wk,
            spread=spread,
            outcome_prices=prices,
            outcomes=outcomes,
            clob_token_ids=clob_ids,
            category=category,
            scores=MarketScores(
                price_extreme=round(pe, 4),
                volume_momentum=round(vm, 4),
                volume_signal=round(vs, 4),
                spread_quality=round(sq, 4),
                narrative_density=round(nd, 4),
                composite=round(composite, 4),
            ),
            tags=tags,
            raw=m,
        )

    # --- Individual scoring functions ---

    @staticmethod
    def _score_narrative_density(description: str) -> float:
        return min(1.0, len(description) / 2000)

    @staticmethod
    def _score_price_extreme(prices: list[float]) -> float:
        """Score price deviation from 50/50.

        Sweet spot is 0.15–0.85 range (genuine bias opportunity).
        Near-certain outcomes (>0.92 or <0.08) are penalized — those
        aren't mispriced, they're just resolved.
        """
        max_dev = max(abs(p - 0.50) for p in prices)
        # Too close to 50/50 — no signal
        if max_dev < 0.15:
            return 0.0
        # Sweet spot: deviation 0.15–0.42 (prices in ~8-35% or 65-92% range)
        if max_dev <= 0.42:
            return min(1.0, (max_dev - 0.15) / 0.27)
        # Near-certain (>92% or <8%): penalize — outcome is effectively decided
        return max(0.0, 1.0 - (max_dev - 0.42) / 0.08)

    @staticmethod
    def _score_volume_signal(volume_24hr: float, liquidity: float) -> float:
        if liquidity <= 0:
            return 0.0
        ratio = volume_24hr / liquidity
        return min(1.0, ratio / 0.5)

    @staticmethod
    def _score_volume_momentum(volume_24hr: float, volume_1wk: float) -> float:
        """Score 24hr volume concentration within the week.

        High ratio = something just happened and retail is piling in.
        This is the availability bias / System 1 overreaction detector.
        """
        denominator = max(volume_1wk, volume_24hr)  # guard against 1wk < 24hr edge case
        if denominator <= 0:
            return 0.0
        ratio = volume_24hr / denominator
        return min(1.0, ratio / 0.5)

    @staticmethod
    def _score_spread_quality(spread: float) -> float:
        if spread <= 0:
            return 0.5  # unknown, neutral
        return max(0.0, 1.0 - (spread / 0.10))


# ---------------------------------------------------------------------------
# Helpers (module-level)
# ---------------------------------------------------------------------------

def _parse_outcome_prices(raw: Any) -> Optional[list[float]]:
    """Parse outcomePrices from either a JSON string or a list."""
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    elif isinstance(raw, list):
        parsed = raw
    else:
        return None
    try:
        return [float(p) for p in parsed]
    except (ValueError, TypeError):
        return None


def _parse_list_field(raw: Any) -> list[str]:
    """Parse a field that might be a JSON string or already a list."""
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return [str(x) for x in parsed]
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _parse_end_date(raw: Any) -> Optional[datetime]:
    """Parse an end date string into a timezone-aware datetime."""
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(str(raw))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _derive_category(m: dict) -> str:
    """Derive market category from feeType field."""
    fee_type = m.get("feeType", "")
    if fee_type == "crypto_fees_v2":
        return "crypto"
    if fee_type == "sports_fees_v2":
        return "sports"
    return "other"