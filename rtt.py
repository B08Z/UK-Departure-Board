from __future__ import annotations
import datetime as _dt
import typing as _t
import requests

class RTTError(Exception):
    pass

class RTTClient:
    def __init__(self, base_url: str, username: str, password: str, session: _t.Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.auth = (username, password)

    def get_location_lineup(self, station: str, *, to_station: _t.Optional[str] = None,
                            date: _t.Optional[_dt.date] = None, time_hhmm: _t.Optional[str] = None,
                            arrivals: bool = False) -> dict:
        path = f"/json/search/{station}"
        if to_station:
            path += f"/to/{to_station}"
        if arrivals:
            path += "/arrivals"
        if date:
            path += f"/{date.year:04d}/{date.month:02d}/{date.day:02d}"
            if time_hhmm:
                if not _is_hhmm(time_hhmm):
                    raise ValueError("time_hhmm must be HHMM, e.g. '0810'")
                path += f"/{time_hhmm}"
        r = self.session.get(self.base_url + path, timeout=15)
        if r.status_code == 404:
            return {"location": None, "filter": None, "services": []}
        if r.status_code != 200:
            raise RTTError(f"RTT {r.status_code}: {r.text[:200]}")
        return r.json()

    def get_service_info(self, service_uid: str, run_date: _dt.date) -> dict:
        path = f"/json/service/{service_uid}/{run_date.year:04d}/{run_date.month:02d}/{run_date.day:02d}"
        r = self.session.get(self.base_url + path, timeout=15)
        if r.status_code == 404:
            return {}
        if r.status_code != 200:
            raise RTTError(f"RTT {r.status_code}: {r.text[:200]}")
        return r.json()

def get_departures_as_livetimes(*, client: RTTClient, crs: str, to_crs: _t.Optional[str] = None,
                                limit: int = 12, include_calling_at: bool = True, arrivals: bool = False,
                                date: _t.Optional[_dt.date] = None, time_hhmm: _t.Optional[str] = None,
                                passenger_only: bool = True) -> list[dict]:
    raw = client.get_location_lineup(crs, to_station=to_crs, date=date, time_hhmm=time_hhmm, arrivals=arrivals)
    services = raw.get("services") or []
    out: list[dict] = []
    for s in services:
        if passenger_only and not s.get("isPassenger", False):
            continue
        loc = s.get("locationDetail", {}) or {}
        dest = _first_desc(loc.get("destination")) or ""
        op = s.get("atocName") or "Unknown"
        platform = loc.get("platform") or "-"
        disp = (loc.get("displayAs") or "").upper()
        planned_cancel = bool(s.get("plannedCancel", False))
        if arrivals:
            gbtt = loc.get("gbttBookedArrival"); rt = loc.get("realtimeArrival")
        else:
            gbtt = loc.get("gbttBookedDeparture"); rt = loc.get("realtimeDeparture")
        sch = _fmt(gbtt) if gbtt else "--:--"
        expt = _fmt(rt) if rt else sch
        calling = ""
        if include_calling_at and s.get("serviceUid") and s.get("runDate"):
            try:
                sinfo = client.get_service_info(s["serviceUid"], _dt.date.fromisoformat(s["runDate"]))
                calling = _calling_for_station(sinfo, crs, arrivals)
            except Exception:
                calling = ""
        out.append({
            "Index": len(out) + 1,
            "ID": f"{s.get('serviceUid','')}-{s.get('runDate','')}",
            "Operator": op,
            "Destination": dest,
            "SchArrival": sch,
            "ExptArrival": expt,
            "CallingAt": calling,
            "Platforms": str(platform),
            "IsCancelled": planned_cancel or disp.startswith("CANCELLED"),
            "DisruptionReason": "",
            "DisplayText": s.get("runningIdentity") or s.get("trainIdentity") or "",
        })
        if len(out) >= limit:
            break
    return out

def _is_hhmm(s: str) -> bool:
    return isinstance(s, str) and len(s) == 4 and s.isdigit() and int(s[:2]) < 24 and int(s[2:]) < 60

def _fmt(s: _t.Optional[str]) -> str:
    return f"{s[:2]}:{s[2:]}" if s and len(s) == 4 and s.isdigit() else "--:--"

def _first_desc(pairs: _t.Optional[list]) -> _t.Optional[str]:
    try:
        if pairs and isinstance(pairs, list):
            return (pairs[0] or {}).get("description")
    except Exception:
        pass
    return None

def _calling_for_station(service_info: dict, station_crs: str, arrivals: bool) -> str:
    locs = service_info.get("locations") or []
    idx = next((i for i, l in enumerate(locs) if (l or {}).get("crs") == station_crs), None)
    if idx is None:
        return ""
    def _pub(l):
        return bool(l.get("isPublicCall") or l.get("isCallPublic"))
    seq = (l for l in (locs[:idx] if arrivals else locs[idx + 1:]) if _pub(l))
    names = [l.get("description") for l in seq if l.get("description")]
    return ", ".join(names[:20])