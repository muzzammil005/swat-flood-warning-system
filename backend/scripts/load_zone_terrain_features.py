"""Populate zone_terrain_features from Swat_4Zones_Static_Features_MultiEvent.csv.

Reads ``backend/models/Swat_4Zones_Static_Features_MultiEvent.csv`` and populates
the 22 static columns in ``zone_terrain_features`` for each zone.

Zone name mapping (CSV name → zones.id):
    Kalam   → zone-kalam
    Bahrain → zone-bahrain
    Madyan  → zone-madyan
    Mingora → zone-mingora

Run this from the project root:
    python backend/scripts/load_zone_terrain_features.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "src"))

from infrastructure.db.session import get_session  # noqa: E402
from infrastructure.db.repositories import (  # noqa: E402
    ZoneRepositoryImpl,
    ZoneTerrainFeaturesRepositoryImpl,
)
from infrastructure.ml.artifacts import landcover_encoder  # noqa: E402

_CSV_PATH = _PROJECT_ROOT / "backend" / "models" / "Swat_4Zones_Static_Features_MultiEvent.csv"

_ZONE_NAME_TO_ID: dict[str, str] = {
    "Kalam": "zone-kalam",
    "Bahrain": "zone-bahrain",
    "Madyan": "zone-madyan",
    "Mingora": "zone-mingora",
}

_MONTH_COLS: tuple[str, ...] = (
    "rain_jan", "rain_feb", "rain_mar", "rain_apr", "rain_may", "rain_jun",
    "rain_jul", "rain_aug", "rain_sep", "rain_oct", "rain_nov", "rain_dec",
)


def _build_feature_dict(row: pd.Series) -> dict[str, float | int]:
    """Convert one CSV row into a 22-key static feature dict for the database."""
    monthly = {m: float(row[m]) for m in _MONTH_COLS}

    # Landcover: CSV numeric (e.g. 60.0) -> cast to int -> str ("60") -> encode with multiclass encoder.
    raw_landcover = row["landcover"]
    landcover_str = str(int(float(raw_landcover)))
    landcover_encoded = int(landcover_encoder.transform([landcover_str])[0])

    features: dict[str, float | int] = {
        "elevation": float(row["elevation"]),
        "slope": float(row["slope"]),
        "stream_proximity": float(row["stream_proximity"]),
        "drainage_density": float(row["drainage_density"]),
        "upstream_area": float(row["upstream_area"]),
        "hand": float(row["hand"]),
        "landcover_encoded": landcover_encoded,
        "ndvi": float(row["ndvi"]),
        **monthly,
        "longitude": float(row["longitude"]),
        "latitude": float(row["latitude"]),
    }
    return features


async def main() -> None:
    print("=" * 70)
    print("Load ZoneTerrainFeatures from Swat_4Zones_Static_Features_MultiEvent.csv")
    print("=" * 70)

    if not _CSV_PATH.exists():
        print(f"ERROR: CSV not found at {_CSV_PATH}")
        sys.exit(1)

    df = pd.read_csv(_CSV_PATH)
    print(f"\n1. Read CSV: {len(df)} rows, columns: {list(df.columns)}")

    name_col = df.columns[0]
    print(f"   Zone name column: '{name_col}'")

    async with get_session() as session:
        zone_repo = ZoneRepositoryImpl(session)
        terrain_repo = ZoneTerrainFeaturesRepositoryImpl(session)

        all_zones = await zone_repo.list_all()
        zone_ids_in_db = {z.id for z in all_zones}
        print(f"\n2. Zones in DB ({len(zone_ids_in_db)}): {sorted(zone_ids_in_db)}")

        for _, row in df.iterrows():
            csv_name = str(row[name_col]).strip()
            zone_id = _ZONE_NAME_TO_ID.get(csv_name)
            if zone_id is None:
                print(f"   ⚠  Skipping CSV row with unknown zone name: {csv_name!r}")
                continue
            if zone_ids_in_db and zone_id not in zone_ids_in_db:
                print(
                    f"   ⚠  Skipping {csv_name} (→ {zone_id}) — not present in zones table."
                )
                continue

            features = _build_feature_dict(row)
            persisted = await terrain_repo.upsert(zone_id, features)
            print(f"\n3. Upserted 22 static terrain features for {csv_name} (zone_id={zone_id}):")
            for k, v in persisted.items():
                print(f"     {k:<25} = {v:>12.6f}" if isinstance(v, float)
                      else f"     {k:<25} = {v:>12}")

        await session.commit()

    print("\n" + "=" * 70)
    print("Done — 22 static zone_terrain_features rows loaded / updated.")
    print("=" * 70)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
