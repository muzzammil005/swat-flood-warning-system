"""Prompt 4 — refresh risk assessments from the real ML model + real weather.

Batch job that:
    1. Loops over all zones in the ``zones`` table.
    2. For each zone:
       a. Fetches *past 7 days* accumulated precipitation from Open-Meteo
          (``past_days=7`` on the forecast endpoint — same API, no separate
          historical endpoint needed).
       b. Fetches *next 72 hours* (3 days) forecast precipitation from the
          same Open-Meteo call.
       c. Loads the zone's ``ZoneTerrainFeatures`` row (must already exist —
          run ``load_zone_terrain_features.py`` first).
       d. Calls :func:`infrastructure.ml.predictor.predict` with the terrain
          dict + rain windows + current month.
       e. Appends a brand-new ``RiskAssessment`` row (append-only, never
          UPDATEs — matches the repository contract for historical facts).
    3. After every zone has a fresh base assessment, runs
       :class:`EscalationEngine.propagate()` *on top* of the raw model output
       so upstream→downstream escalation (including pushing HIGH → DANGER when
       an upstream neighbour is also elevated) still applies exactly as it
       did with the seed script's synthetic risks.

Usage (from project root, inside the backend container or a venv with deps)::

    python backend/scripts/refresh_risk_assessments.py

The existing HTTP routers (GET /api/zones, GET /api/zones/{id}) serve the
freshly-inserted rows with zero frontend changes required — this is the
proof that the "one backend, two clients" architecture works end-to-end.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "src"))

from datetime import timedelta  # noqa: E402

from domain.entities.alert import Alert  # noqa: E402
from domain.entities.risk_assessment import RiskAssessment  # noqa: E402
from domain.services.escalation_engine import EscalationEngine  # noqa: E402
from domain.value_objects.risk_tier import RiskTier  # noqa: E402
from infrastructure.db.session import get_session  # noqa: E402
from infrastructure.db.repositories import (  # noqa: E402
    AlertRepositoryImpl,
    RiskAssessmentRepositoryImpl,
    ZoneRepositoryImpl,
    ZoneTerrainFeaturesRepositoryImpl,
)
from infrastructure.ml.predictor import predict  # noqa: E402


# ---------------------------------------------------------------------------
# Open-Meteo helper — direct httpx call for past_7d + next_72h rain windows.
# We don't extend the WeatherProvider port because this 10-day split window
# is specific to the ML predictor's signature; the HTTP-level use cases only
# ever need the simpler 24h forecast window that fetch_forecast() provides.
# ---------------------------------------------------------------------------


_OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
_OPEN_METEO_TIMEOUT = 15.0
_OPEN_METEO_MAX_RETRIES = 2


class _OpenMeteoRainWindows:
    """Small typed container for the two rain windows the predictor needs."""

    def __init__(self, past_7d_mm: float, next_72h_mm: float) -> None:
        self.past_7d_mm = max(float(past_7d_mm), 0.0)
        self.next_72h_mm = max(float(next_72h_mm), 0.0)


async def _fetch_rain_windows(
    latitude: float, longitude: float, /, *, client: httpx.AsyncClient
) -> _OpenMeteoRainWindows:
    """Fetch past-7-day + next-72h accumulated precipitation from Open-Meteo.

    Uses a *single* API call with ``past_days=7`` + ``forecast_days=3`` so we
    get all 10 days of hourly data in one round trip (cheaper, less rate-limit
    pressure, fewer points of failure than two separate calls).
    """
    params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation",
        "past_days": 7,       # 7 days of *historical* hourly values
        "forecast_days": 3,   # 3 days of *future* hourly values
        "timezone": "auto",
    }

    last_exception: Exception | None = None
    for attempt in range(_OPEN_METEO_MAX_RETRIES + 1):
        try:
            response = await client.get(_OPEN_METEO_BASE, params=params)
            response.raise_for_status()
            data = response.json()
            hourly = data.get("hourly", {})
            precip_list = hourly.get("precipitation", [])
            if not isinstance(precip_list, list) or len(precip_list) < (7 + 3) * 24:
                raise ValueError(
                    f"Open-Meteo returned only {len(precip_list)} hourly rows; "
                    f"expected at least {(7+3)*24} for past_7d + forecast_3d."
                )
            # 7 days = 168 hours, 3 days = 72 hours. Order: past first, then forecast.
            past_values = [float(v or 0.0) for v in precip_list[: 7 * 24]]
            future_values = [float(v or 0.0) for v in precip_list[7 * 24 : (7 + 3) * 24]]
            past_7d_mm = sum(v for v in past_values if math.isfinite(v))
            next_72h_mm = sum(v for v in future_values if math.isfinite(v))
            return _OpenMeteoRainWindows(past_7d_mm, next_72h_mm)

        except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError, IndexError) as exc:
            last_exception = exc
            # Don't retry 4xx — only 5xx / network / transient.
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                break
            # Transient: continue to next attempt.
            continue
        except Exception as exc:
            last_exception = exc
            continue

    # All retries failed → surface the last error. Caller can decide to skip.
    raise RuntimeError(
        f"Open-Meteo rain fetch failed for ({latitude}, {longitude}): {last_exception!r}"
    )


# ---------------------------------------------------------------------------
# Explanation builder — human-readable dashboard text from a PredictionResult.
# ---------------------------------------------------------------------------


def _build_explanation(
    *,
    zone_name: str,
    combined_rain_mm: float,
    expected_rain_mm: float,
    rainfall_anomaly_ratio: float,
    tier_name: str,
    top_features: list[str],
) -> str:
    """Compose a RiskAssessment.explanation string for non-technical viewers.

    Prompt 5 enhancement: if ``top_features`` is non-empty (SHAP ran), weave
    the top contributing feature names into the sentence so the dashboard
    shows *why* the model picked its tier, not just a generic template.
    """
    ratio_pct = int(round(rainfall_anomaly_ratio * 100))
    base = (
        f"{zone_name}: {tier_name} risk. "
        f"10-day combined rain {combined_rain_mm:.1f} mm "
        f"(expected ~{expected_rain_mm:.1f} mm = {ratio_pct}% of baseline)."
    )
    if top_features:
        readable = _humanize_feature_names(top_features)
        base += f" Top drivers: {', '.join(readable)}."
    return base


_FEATURE_HUMAN_NAMES: dict[str, str] = {
    "elevation": "low elevation",
    "slope": "flat terrain slope",
    "stream_proximity": "proximity to rivers",
    "drainage_density": "high drainage density",
    "upstream_area": "large upstream catchment",
    "hand": "low height above river",
    "landcover_encoded": "land cover type",
    "ndvi": "low vegetation cover",
    "annual_rain_mean": "high annual rainfall",
    "rainfall_std": "variable monthly rainfall",
    "rainfall_max_anomaly": "extreme monthly rainfall anomaly",
    "terrain_ruggedness": "terrain ruggedness",
    "longitude": "downstream location",
    "latitude": "downstream latitude",
}


def _humanize_feature_names(cols: list[str]) -> list[str]:
    """Map raw ML feature names → plain English for the dashboard."""
    result: list[str] = []
    for c in cols:
        if c.startswith("rain_"):
            # rain_jun → heavy June rain
            month_name = c.split("_", 1)[1].title()
            result.append(f"heavy {month_name} rain")
        else:
            result.append(_FEATURE_HUMAN_NAMES.get(c, c))
    return result


# ---------------------------------------------------------------------------
# Alert sync — ensure public-facing alerts match the final post-escalation tier.
# ---------------------------------------------------------------------------


_CERTAINTY_URGENCY_BY_TIER: dict[RiskTier, tuple[str, str]] = {
    RiskTier.DANGER: ("Observed", "Immediate"),
    RiskTier.HIGH:   ("Likely",   "Expected"),
    RiskTier.MEDIUM: ("Possible", "Future"),
}


async def _sync_alerts(
    *,
    session,
    zones,
    final_assessments: dict[str, RiskAssessment],
    now: datetime,
) -> dict[str, Alert]:
    """Replace stale alerts so GET /api/alerts agrees with GET /api/zones.

    Strategy (mirrors seed_demo_data.generate_alerts + its DELETE-first step):
      1. Clear all existing alert rows (append-only contract applies to
         *repository insert* — raw DELETE via SQL is still the supported
         reset path as proven by seed_demo_data.clear_existing_data).
      2. For every zone whose *final post-escalation tier* is >= MEDIUM,
         emit a new CAP-inspired alert row using the same tier -> certainty/
         urgency mapping the seed script uses so the two scripts can't
         silently disagree on severity semantics.
      3. LOW-tier zones deliberately get NO alert (the threshold to warrant
         public broadcast is MEDIUM+, identical to seed_demo_data line 403).
    """
    from sqlalchemy import text

    alert_repo = AlertRepositoryImpl(session)
    created: dict[str, Alert] = {}

    await session.execute(text("DELETE FROM alerts WHERE TRUE"))

    for zone in zones:
        zone_id = zone.id
        if zone_id not in final_assessments:
            continue
        assessment = final_assessments[zone_id]
        if assessment.tier.value < RiskTier.MEDIUM.value:
            continue

        certainty, urgency = _CERTAINTY_URGENCY_BY_TIER[assessment.tier]
        alert = Alert(
            zone_id=zone_id,
            severity=assessment.tier,
            certainty=certainty,
            urgency=urgency,
            headline=f"{assessment.tier.name} risk alert for {zone.name}",
            description=assessment.explanation,
            sent_at=now + timedelta(minutes=10),
        )
        saved = await alert_repo.add(alert)
        created[zone_id] = saved

    return created


# ---------------------------------------------------------------------------
# Main batch loop
# ---------------------------------------------------------------------------


async def main() -> None:
    print("=" * 70)
    print("Prompt 4 — Refresh Risk Assessments (real ML model + real weather)")
    print("=" * 70)

    now = datetime.now(timezone.utc)
    current_month = now.month
    print("\nRun timestamp: {}  (month={})".format(now.isoformat(), current_month))

    try:
        from infrastructure.ml.artifacts import build_shap_explainer
        build_shap_explainer()
        print("SHAP explainer built successfully.")
    except Exception as e:
        print(f"Failed to build SHAP explainer: {e}")

    async with httpx.AsyncClient(
        timeout=_OPEN_METEO_TIMEOUT,
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    ) as http_client:
        async with get_session() as session:
            zone_repo = ZoneRepositoryImpl(session)
            terrain_repo = ZoneTerrainFeaturesRepositoryImpl(session)
            risk_repo = RiskAssessmentRepositoryImpl(session)

            zones = await zone_repo.list_all()
            print(f"\n1. Found {len(zones)} zones: {[z.name for z in zones]}")

            # Phase A — compute base (pre-escalation) assessments per zone.
            base_assessments: dict[str, RiskAssessment] = {}

            for zone in zones:
                print(f"\n--- {zone.name} (id={zone.id}) ---")

                # A1. Load terrain features. Script aborts if any *real SWAT*
                # zone is missing a terrain row (operator error — run
                # load_zone_terrain_features.py first).
                # For synthetic demo/test zones that don't have terrain data
                # (e.g. Override Detail/Summary test zones from the seed
                # script), skip gracefully with a warning rather than
                # aborting the whole batch for 3 lines of test data.
                terrain = await terrain_repo.get_by_zone_id(zone.id)
                if terrain is None:
                    if zone.id.startswith("zone-override-") or (
                        zone.id not in (
                            "zone-kalam", "zone-bahrain",
                            "zone-madyan", "zone-mingora",
                        )
                        and not zone.id.startswith("zone-")
                    ):
                        print(f"   ⚠  Skipping — no ZoneTerrainFeatures for "
                              f"test/non-SWAT zone {zone.id} ({zone.name}).")
                        continue
                    raise RuntimeError(
                        f"No ZoneTerrainFeatures for zone {zone.id} ({zone.name}). "
                        f"Run backend/scripts/load_zone_terrain_features.py first."
                    )
                print(f"   Terrain features loaded ({len(terrain)} static cols, elevation="
                      f"{float(terrain.get('elevation', 0.0)):.1f} m)")

                # A2. Fetch rain windows; on failure, fall back to 0 / baseline prediction
                # rather than killing the entire batch (one dead API call shouldn't
                # leave the other 3 zones stale).
                try:
                    rain = await _fetch_rain_windows(
                        zone.coordinates.latitude,
                        zone.coordinates.longitude,
                        client=http_client,
                    )
                    print(f"   Past-7d rain:  {rain.past_7d_mm:.1f} mm")
                    print(f"   Next-72h rain: {rain.next_72h_mm:.1f} mm")
                except RuntimeError as exc:
                    print(f"   ⚠  Rain fetch failed ({exc}); using 0 / baseline.")
                    rain = _OpenMeteoRainWindows(0.0, 0.0)

                # A3. ML predictor.
                prediction = predict(
                    terrain,
                    past_7day_rain=rain.past_7d_mm,
                    next_72hr_forecast_rain=rain.next_72h_mm,
                    current_month=current_month,
                    include_shap=True,  # opt-in; harmless if SHAP explainer isn't built
                )
                tier_name = prediction.risk_level.name
                explanation = _build_explanation(
                    zone_name=zone.name,
                    combined_rain_mm=prediction.combined_rain_mm,
                    expected_rain_mm=prediction.expected_rain_mm,
                    rainfall_anomaly_ratio=prediction.rainfall_anomaly_ratio,
                    tier_name=tier_name,
                    top_features=prediction.top_contributing_features,
                )
                assessment = RiskAssessment(
                    zone_id=zone.id,
                    tier=prediction.risk_level,
                    probability=prediction.flood_probability,
                    explanation=explanation,
                    computed_at=now,
                    combined_rain_mm=prediction.combined_rain_mm,
                    expected_rain_mm=prediction.expected_rain_mm,
                    rainfall_anomaly_ratio=prediction.rainfall_anomaly_ratio,
                    top_contributing_features=prediction.top_contributing_features,
                )
                print(f"   Model output: P(flood)={prediction.flood_probability:.4f} → {tier_name}")
                if prediction.top_contributing_features:
                    print(f"   Top SHAP features: {prediction.top_contributing_features}")
                base_assessments[zone.id] = assessment

            # Phase B — EscalationEngine propagates HIGH/DANGER downstream.
            print("\n" + "-" * 70)
            print("2. Running EscalationEngine across fresh base assessments...")
            escalation = EscalationEngine()
            escalation.build_graph(zones)
            final_assessments = escalation.propagate(base_assessments)

            # Phase C — persist every final assessment (append-only = INSERT per zone).
            print("\n3. Persisting final RiskAssessment rows (append-only)...")
            persisted_by_zone: dict[str, RiskAssessment] = {}
            for zone in zones:
                if zone.id not in final_assessments:
                    # Skipped earlier (no terrain — test zones). Don't re-crash.
                    continue
                final = final_assessments[zone.id]
                persisted = await risk_repo.add(final)
                persisted_by_zone[zone.id] = persisted
                base_tier = base_assessments[zone.id].tier if zone.id in base_assessments else final.tier
                escalated = " (ESCALATED)" if final.tier != base_tier else ""
                print(
                    f"   {zone.name:<8} → {final.tier.name:<7} "
                    f"P={final.probability:.4f}{escalated}"
                )

            # Phase D — sync public-facing alerts to the final post-escalation tiers.
            print("\n4. Syncing alerts table to match final tiers (MEDIUM+ only)...")
            new_alerts = await _sync_alerts(
                session=session,
                zones=zones,
                final_assessments=persisted_by_zone,
                now=now,
            )
            if new_alerts:
                for zid, alt in new_alerts.items():
                    print(f"   {alt.severity.name:<7} alert for zone {zid}")
            else:
                print("   No alerts created (all zones LOW after escalation).")
            await session.commit()

    print("\n" + "=" * 70)
    print(f"Done. {len(persisted_by_zone)} new risk assessments inserted.")
    print(f"      {len(new_alerts)} active alerts now in the alerts table.")
    print("Verify via:   GET /api/zones   and   GET /api/zones/{id}")
    print("              GET /api/alerts  (now matches zones' final tiers)")
    print("=" * 70)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
