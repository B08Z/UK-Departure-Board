"""
Adapter that reuses Jonathan Foot's LondonUndergroundPy3.py.
Place that file alongside this one (or ensure it's importable).
"""

from __future__ import annotations
import datetime as dt
import typing as t

import LondonUndergroundPy3 as LU  # ensure this is in your repo / PYTHONPATH

class TubeLegacyAdapterError(Exception):
    pass

def tube_legacy_as_livetimes(*, stop_point_id: str, app_id: str, app_key: str, limit: int = 12) -> list[dict]:
    """
    Expect LondonUndergroundPy3.py to expose a callable that returns arrivals for a StopPoint.
    If your version is different, tweak this call accordingly.
    """
    try:
        # Adjust this line if your copy exposes a slightly different API.
        # Options to try if needed:
        #   LU.GetArrivals(stop_point_id, app_id, app_key)
        #   LU.getArrivals(stop_point_id, app_id, app_key)
        #   LU.fetch_arrivals(stop_point_id, app_id, app_key)
        raw = LU.GetArrivals(stop_point_id, app_id, app_key)
    except AttributeError as e:
        raise TubeLegacyAdapterError(
            "LondonUndergroundPy3.py must expose a function like "
            "GetArrivals(stop_point_id, app_id, app_key). Please open that file "
            "and extract/wire its core fetch routine into that function name."
        ) from e

    rows = []
    for idx, item in enumerate(raw, start=1):
        rows.append(_map_one(item, idx))
        if len(rows) >= limit:
            break
    return rows

def _map_one(item: t.Any, index: int) -> dict:
    """Map one item to the unified dict shape used by the board renderer."""
    destination = _get(item, "Destination", "destinationName", default="")
    expected_iso = _get(item, "Expected", "expectedArrival", default="")
    platform = _get(item, "Platform", "platformName", default="-")
    line = _get(item, "Line", "lineName", "lineId", default="Underground")
    direction = _get(item, "Direction", "direction", default="")
    expt_hhmm = _iso_to_hhmm(expected_iso)
    ident = _get(item, "Id", "id", "vehicleId", default=f"{line}-{index}")

    return {
        "Index": index,
        "ID": str(ident),
        "Operator": "London Underground",
        "Destination": destination,
        "SchArrival": "--:--",
        "ExptArrival": expt_hhmm,
        "CallingAt": "",
        "Platforms": platform,
        "IsCancelled": False,
        "DisruptionReason": "",
        "DisplayText": f"{line} {direction}".strip(),
    }

def _get(obj: t.Any, *names: str, default=None):
    for n in names:
        # attribute
        if hasattr(obj, n):
            v = getattr(obj, n)
            if v is not None:
                return v
        # dict-like
        if isinstance(obj, dict) and n in obj:
            v = obj.get(n)
            if v is not None:
                return v
    return default

def _iso_to_hhmm(s: str) -> str:
    if not s:
        return "--:--"
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().strftime("%H:%M")
    except Exception:
        return "--:--"