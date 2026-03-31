import copy
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from seed_data import DATACENTERS

app = FastAPI(title="DataSphere API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory state (resets on pod restart — intentional for demo) ──────────
_state: dict[str, dict] = {}


def _init_state():
    for dc in DATACENTERS:
        _state[dc["id"]] = {
            **dc,
            "status": "online",
            "capacity_pct": dc["base_capacity_pct"],
            "workload_count": dc["base_workload_count"],
            "uptime_pct": 99.97 if dc["tier"] == "major" else 99.5,
        }


_init_state()

# ── Health break flag (for Lab 8 — health check demo) ───────────────────────
_api_broken = False


# ── Theme config ─────────────────────────────────────────────────────────────
CONFIG_FILE = Path(os.getenv("DATASPHERE_CONFIG_PATH", "/etc/datasphere/config.json"))
DEFAULT_THEME = os.getenv("DATASPHERE_THEME", "earth")

THEME_METADATA = {
    "earth": {
        "theme": "earth",
        "map_title": "DataSphere — Global Infrastructure",
        "dc_label": "Datacenter",
        "region_label": "Region",
        "status_labels": {"online": "Online", "degraded": "Degraded", "offline": "Offline"},
        "name_field": "display_name",
        "region_field": "region",
    },
    "mars": {
        "theme": "mars",
        "map_title": "DataSphere — Mars Operations",
        "dc_label": "Research Colony",
        "region_label": "Zone",
        "status_labels": {"online": "Operational", "degraded": "Limited", "offline": "Dark"},
        "name_field": "mars_name",
        "region_field": "mars_region",
    },
}


def _read_config() -> dict:
    """Read theme config from mounted ConfigMap file, falling back to env var."""
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text())
            theme = data.get("theme", DEFAULT_THEME)
            return THEME_METADATA.get(theme, THEME_METADATA["earth"])
    except Exception:
        pass
    return THEME_METADATA.get(DEFAULT_THEME, THEME_METADATA["earth"])


# ── Models ────────────────────────────────────────────────────────────────────
class StatusUpdate(BaseModel):
    status: str  # online | degraded | offline


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    if _api_broken:
        raise HTTPException(status_code=500, detail="API health check failed")
    return {"status": "ok"}


@app.get("/api/config")
def get_config():
    return _read_config()


@app.get("/api/datacenters")
def list_datacenters():
    return list(_state.values())


@app.get("/api/datacenters/{dc_id}")
def get_datacenter(dc_id: str):
    if dc_id not in _state:
        raise HTTPException(status_code=404, detail="Datacenter not found")
    return _state[dc_id]


@app.patch("/api/datacenters/{dc_id}/status")
def update_status(dc_id: str, body: StatusUpdate):
    if dc_id not in _state:
        raise HTTPException(status_code=404, detail="Datacenter not found")
    if body.status not in ("online", "degraded", "offline"):
        raise HTTPException(status_code=400, detail="status must be online, degraded, or offline")

    _state[dc_id]["status"] = body.status

    if body.status == "online":
        _state[dc_id]["capacity_pct"] = _state[dc_id]["base_capacity_pct"]
        _state[dc_id]["workload_count"] = _state[dc_id]["base_workload_count"]
    elif body.status == "degraded":
        _state[dc_id]["capacity_pct"] = min(95, _state[dc_id]["base_capacity_pct"] + 15)
    elif body.status == "offline":
        _state[dc_id]["capacity_pct"] = 0
        _state[dc_id]["workload_count"] = 0

    return _state[dc_id]


@app.post("/api/reset")
def reset_all():
    """Reset all datacenters to their default state."""
    _init_state()
    return {"status": "reset", "datacenters": len(_state)}


# ── Lab 8: Health check demo endpoints ───────────────────────────────────────
@app.post("/api/break")
def break_api():
    """Make the health endpoint return 500 — used in the health check lab."""
    global _api_broken
    _api_broken = True
    return {"status": "broken", "message": "Health check will now fail. OCP will restart this pod."}


@app.post("/api/restore")
def restore_api():
    """Restore health — reachable only if the pod hasn't been restarted yet."""
    global _api_broken
    _api_broken = False
    return {"status": "restored"}
