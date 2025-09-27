from __future__ import annotations
import os
import yaml
from pathlib import Path
from copy import deepcopy

from rtt import RTTClient, get_departures_as_livetimes
from tube_from_london_underground_py3 import tube_legacy_as_livetimes
from remote_config import RemoteConfig


# ---------- merge helpers ----------

def deep_merge(a: dict, b: dict) -> dict:
    """Deep merge dicts; values from b override a."""
    out = deepcopy(a)
    if not isinstance(b, dict):
        return out
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# ---------- config loaders ----------

def load_config(path: str | Path = "config.yml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def env_bool(s: str | None, default: bool) -> bool:
    if s is None or s == "":
        return default
    return str(s).strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(s: str | None, default: int) -> int:
    try:
        return int(s) if s not in (None, "") else default
    except Exception:
        return default


def read_env_overlay() -> dict:
    """
    Build a config overlay from environment variables (.env in Docker).
    Only sets keys when env exists; missing vars won't override file config.
    """
    overlay: dict = {}

    # RTT
    rtt = {}
    if os.getenv("RTT_BASE_URL"): rtt["base_url"] = os.getenv("RTT_BASE_URL")
    if os.getenv("RTT_USERNAME"): rtt["username"] = os.getenv("RTT_USERNAME")
    if os.getenv("RTT_PASSWORD"): rtt["password"] = os.getenv("RTT_PASSWORD")
    if rtt: overlay["rtt"] = rtt

    # TfL
    tfl = {}
    if os.getenv("TFL_APP_ID"): tfl["app_id"] = os.getenv("TFL_APP_ID")
    if os.getenv("TFL_APP_KEY"): tfl["app_key"] = os.getenv("TFL_APP_KEY")
    if tfl: overlay["tfl"] = tfl

    # Defaults / National Rail
    nr = {}
    if os.getenv("NR_CRS"): nr["crs"] = os.getenv("NR_CRS")
    # allow blank to mean null (remove destination filter)
    if "NR_TO_CRS" in os.environ:
        val = os.getenv("NR_TO_CRS")
        nr["to_crs"] = (val if val else None)
    if "NR_ARRIVALS" in os.environ:
        nr["arrivals"] = env_bool(os.getenv("NR_ARRIVALS"), False)
    if "NR_LIMIT" in os.environ:
        nr["limit"] = env_int(os.getenv("NR_LIMIT"), 6)

    # Defaults / Tube
    tube = {}
    if os.getenv("TUBE_STOPPOINT"): tube["stop_point_id"] = os.getenv("TUBE_STOPPOINT")
    if "TUBE_LIMIT" in os.environ:
        tube["limit"] = env_int(os.getenv("TUBE_LIMIT"), 6)

    if nr or tube:
        overlay.setdefault("defaults", {})
        if nr: overlay["defaults"]["national_rail"] = nr
        if tube: overlay["defaults"]["tube"] = tube

    # UI / Font
    ui = {}
    if os.getenv("FONT_PATH"): ui["font_path"] = os.getenv("FONT_PATH")
    if "FONT_BOLD_PATH" in os.environ:
        ui["font_bold_path"] = os.getenv("FONT_BOLD_PATH") or None
    if "FONT_SIZE" in os.environ:
        ui["font_size"] = env_int(os.getenv("FONT_SIZE"), 22)
    if "LINE_HEIGHT" in os.environ:
        ui["line_height"] = env_int(os.getenv("LINE_HEIGHT"), 24)
    if "LEFT_MARGIN" in os.environ:
        ui["left_margin"] = env_int(os.getenv("LEFT_MARGIN"), 4)
    if "INTERLEAVE" in os.environ:
        ui["interleave"] = env_bool(os.getenv("INTERLEAVE"), False)
    if ui: overlay["ui"] = ui

    # Remote config
    remote = {}
    if "REMOTE_ENABLED" in os.environ:
        remote["enabled"] = env_bool(os.getenv("REMOTE_ENABLED"), True)
    if os.getenv("REMOTE_URL"): remote["url"] = os.getenv("REMOTE_URL")
    if "REMOTE_TIMEOUT_SECONDS" in os.environ:
        remote["timeout_seconds"] = env_int(os.getenv("REMOTE_TIMEOUT_SECONDS"), 5)
    if "REMOTE_CACHE_TTL_SECONDS" in os.environ:
        remote["cache_ttl_seconds"] = env_int(os.getenv("REMOTE_CACHE_TTL_SECONDS"), 60)
    if remote: overlay["remote"] = remote

    # Optional: stash John-style options (if you later use them in rendering)
    john = {}
    for key, dst in [
        ("TIME_FORMAT", "time_format"),
        ("SPEED", "speed"),
        ("DELAY", "delay"),
        ("RECOVERY_TIME", "recovery_time"),
        ("NUMBER_OF_CARDS", "number_of_cards"),
        ("ROTATION", "rotation"),
        ("REQUEST_LIMIT", "request_limit"),
        ("STATIC_UPDATE_LIMIT", "static_update_limit"),
        ("ENERGY_SAVING_MODE", "energy_saving_mode"),
        ("INACTIVE_HOURS", "inactive_hours"),
        ("UPDATE_DAYS", "update_days"),
        ("EXCLUDED_PLATFORMS", "excluded_platforms"),
        ("HEADER", "header"),
        ("HEADER_ALIGNMENT", "header_alignment"),
        ("DESIGN", "design"),
        ("SHOW_CALLING_AT_FOR_DIRECT", "show_calling_at_for_direct"),
        ("HIDE_PLATFORM", "hide_platform"),
        ("SHOW_INDEX", "show_index"),
        ("REDUCED_ANIMATIONS", "reduced_animations"),
        ("FIX_NEXT_TO_ARRIVE", "fix_next_to_arrive"),
        ("NO_SPLASHSCREEN", "no_splashscreen"),
        ("EXCLUDE_LINES", "exclude_lines"),
        ("DIRECTION", "direction"),
        ("WARNING_TIME", "warning_time"),
        ("INCREASED_ANIMATIONS", "increased_animations"),
        ("DISPLAY", "display"),
        ("MAX_FRAMES", "max_frames"),
        ("NO_PIP_UPDATE", "no_pip_update"),
    ]:
        if key in os.environ:
            john[dst] = os.getenv(key)
    if john:
        overlay["john_options"] = john

    return overlay


def load_with_env_and_remote(path: str | Path = "config.yml"):
    """
    Final config = (config.yml) -> (env overlay) -> (remote overrides if enabled).
    Returns (merged_cfg, remote_config_or_none).
    """
    base = load_config(path)
    env_overlay = read_env_overlay()
    merged = deep_merge(base, env_overlay)

    r = merged.get("remote") or {}
    if not r.get("enabled"):
        return merged, None

    rc = RemoteConfig(url=r.get("url", ""), timeout=int(r.get("timeout_seconds", 5)))
    remote = rc.fetch(force=True)
    if remote:
        merged = deep_merge(merged, remote)
    return merged, rc


# ---------- data sources ----------

def make_clients(cfg: dict):
    return RTTClient(
        base_url=cfg["rtt"]["base_url"],
        username=cfg["rtt"]["username"],
        password=cfg["rtt"]["password"],
    )

def get_national_rail_board(cfg: dict, *, crs: str | None = None, to_crs: str | None = None,
                            arrivals: bool | None = None, limit: int | None = None,
                            include_calling_at: bool = True) -> list[dict]:
    rttc = make_clients(cfg)
    d = cfg["defaults"]["national_rail"]
    return get_departures_as_livetimes(
        client=rttc,
        crs=crs or d["crs"],
        to_crs=to_crs if to_crs is not None else d.get("to_crs"),
        arrivals=d.get("arrivals", False) if arrivals is None else arrivals,
        limit=d.get("limit", 6) if limit is None else limit,
        include_calling_at=include_calling_at,
    )

def get_tube_board(cfg: dict, *, stop_point_id: str | None = None, limit: int | None = None) -> list[dict]:
    d = cfg["defaults"]["tube"]
    return tube_legacy_as_livetimes(
        stop_point_id=stop_point_id or d["stop_point_id"],
        app_id=cfg["tfl"]["app_id"],
        app_key=cfg["tfl"]["app_key"],
        limit=d.get("limit", 6) if limit is None else limit,
    )

def interleave(a: list[dict], b: list[dict]) -> list[dict]:
    out = []
    for i in range(max(len(a), len(b))):
        if i < len(a): out.append(a[i])
        if i < len(b): out.append(b[i])
    for i, row in enumerate(out, start=1):
        row["Index"] = i
    return out