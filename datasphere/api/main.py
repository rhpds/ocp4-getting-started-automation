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

# ── Load redistribution constants ────────────────────────────────────────────
# When a major hub goes offline, each remaining online hub absorbs this many
# extra percentage points of capacity.  Raise it to trigger more degraded sites.
LOAD_PRESSURE = 25          # capacity % added per hub on failure

# Hubs at or above this capacity percentage flip to "degraded" status.
DEGRADED_THRESHOLD = 85     # capacity % that triggers degraded

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

# ── Health break flag (for health check demo) ────────────────────────────────
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


# ── Load redistribution helpers ──────────────────────────────────────────────

def _distribute_load(offline_dc_id: str) -> None:
    """When a major hub fails, spread its workload to remaining online major hubs.

    Each surviving hub absorbs LOAD_PRESSURE extra capacity points.  Hubs that
    cross DEGRADED_THRESHOLD flip to 'degraded' so the map turns yellow.
    Regional sites are not cascaded — only major hub failures matter at scale.
    """
    offline = _state[offline_dc_id]
    if offline["tier"] != "major":
        return

    online_majors = [
        s for k, s in _state.items()
        if k != offline_dc_id and s["tier"] == "major" and s["status"] != "offline"
    ]
    if not online_majors:
        return

    extra_workload = offline["base_workload_count"] // len(online_majors)
    for hub in online_majors:
        hub["workload_count"] += extra_workload
        hub["capacity_pct"] = min(99, hub["base_capacity_pct"] + LOAD_PRESSURE)
        if hub["capacity_pct"] >= DEGRADED_THRESHOLD:
            hub["status"] = "degraded"


def _restore_load() -> None:
    """Reset all degraded hubs back to their base values.

    Called whenever any hub comes back online so the network stabilises.
    """
    for dc in _state.values():
        if dc["status"] == "degraded":
            dc["status"] = "online"
            dc["capacity_pct"] = dc["base_capacity_pct"]
            dc["workload_count"] = dc["base_workload_count"]


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
        _restore_load()          # stabilise any hubs that were absorbing extra load
    elif body.status == "degraded":
        _state[dc_id]["capacity_pct"] = min(95, _state[dc_id]["base_capacity_pct"] + 15)
    elif body.status == "offline":
        _state[dc_id]["capacity_pct"] = 0
        _state[dc_id]["workload_count"] = 0
        _distribute_load(dc_id)  # cascade load to remaining online major hubs

    return _state[dc_id]


@app.post("/api/reset")
def reset_all():
    """Reset all datacenters to their default state."""
    _init_state()
    return {"status": "reset", "datacenters": len(_state)}


# ── Health check demo endpoints ───────────────────────────────────────────────
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
