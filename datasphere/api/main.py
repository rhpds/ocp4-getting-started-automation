import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from seed_data import DATACENTERS
import state

app = FastAPI(title="DataSphere API", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load redistribution constants ────────────────────────────────────────────
LOAD_PRESSURE = 25          # capacity % added per hub on failure
DEGRADED_THRESHOLD = 85     # capacity % that triggers degraded

# ── Per-pod health flag (intentionally NOT shared in Redis) ──────────────────
_api_broken = False

# ── Seed state on startup ───────────────────────────────────────────────────
state.init_state()

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
    """When a major hub fails, spread its workload to remaining online major hubs."""
    offline = state.get_datacenter(offline_dc_id)
    if not offline or offline["tier"] != "major":
        return

    online_major_ids = state.get_online_major_ids(offline_dc_id)
    if not online_major_ids:
        return

    extra_workload = offline["base_workload_count"] // len(online_major_ids)
    for hub_id in online_major_ids:
        hub = state.get_datacenter(hub_id)
        if not hub:
            continue
        new_workload = hub["workload_count"] + extra_workload
        new_capacity = min(99, hub["base_capacity_pct"] + LOAD_PRESSURE)
        new_status = "degraded" if new_capacity >= DEGRADED_THRESHOLD else hub["status"]
        state.set_datacenter_fields(hub_id,
                                    workload_count=new_workload,
                                    capacity_pct=new_capacity,
                                    status=new_status)


def _restore_load() -> None:
    """Reset all degraded hubs back to their base values."""
    all_dcs = state.get_all_datacenters()
    for dc in all_dcs:
        if dc["status"] == "degraded":
            state.set_datacenter_fields(dc["id"],
                                        status="online",
                                        capacity_pct=dc["base_capacity_pct"],
                                        workload_count=dc["base_workload_count"])


def _simulate_cascading_cpu_load() -> None:
    """Burn CPU proportional to the number of offline major hubs."""
    offline_majors = state.count_offline_majors()
    if offline_majors == 0:
        return
    iterations = offline_majors * 150_000
    total = 0
    for i in range(iterations):
        total += i * i


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
    _simulate_cascading_cpu_load()
    return state.get_all_datacenters()


@app.get("/api/datacenters/{dc_id}")
def get_datacenter(dc_id: str):
    dc = state.get_datacenter(dc_id)
    if dc is None:
        raise HTTPException(status_code=404, detail="Datacenter not found")
    return dc


@app.patch("/api/datacenters/{dc_id}/status")
def update_status(dc_id: str, body: StatusUpdate):
    dc = state.get_datacenter(dc_id)
    if dc is None:
        raise HTTPException(status_code=404, detail="Datacenter not found")
    if body.status not in ("online", "degraded", "offline"):
        raise HTTPException(status_code=400, detail="status must be online, degraded, or offline")

    if body.status == "online":
        state.set_datacenter_fields(dc_id,
                                    status="online",
                                    capacity_pct=dc["base_capacity_pct"],
                                    workload_count=dc["base_workload_count"])
        _restore_load()
    elif body.status == "degraded":
        state.set_datacenter_fields(dc_id,
                                    status="degraded",
                                    capacity_pct=min(95, dc["base_capacity_pct"] + 15))
    elif body.status == "offline":
        state.set_datacenter_fields(dc_id,
                                    status="offline",
                                    capacity_pct=0,
                                    workload_count=0)
        _distribute_load(dc_id)

    return state.get_datacenter(dc_id)


@app.post("/api/reset")
def reset_all():
    """Reset all datacenters to their default state."""
    state.reset_state()
    return {"status": "reset", "datacenters": len(DATACENTERS)}


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
