import asyncio
import json
import logging
import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from seed_data import DATACENTERS
import state

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("datasphere.api")

_HOSTNAME = socket.gethostname()


@asynccontextmanager
async def lifespan(app):
    """Seed state and register pod heartbeat while the app is running."""
    logger.info("Pod %s starting up", _HOSTNAME)
    state.init_state()
    logger.info("State initialized — %d datacenters seeded", len(DATACENTERS))
    stop = asyncio.Event()

    async def _heartbeat():
        while not stop.is_set():
            state.register_pod_heartbeat(_HOSTNAME)
            try:
                await asyncio.wait_for(stop.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass

    task = asyncio.create_task(_heartbeat())
    logger.info("Heartbeat started (every 5s, 15s TTL)")
    yield
    logger.info("Pod %s shutting down", _HOSTNAME)
    stop.set()
    await task


app = FastAPI(title="DataSphere API", version="1.4.4", lifespan=lifespan)

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


def _simulate_load() -> None:
    """Burn CPU based on combined simulated + offline-penalty load, divided by replicas."""
    simulated = state.get_simulated_load()
    offline_penalty = state.count_offline_majors() * 15
    total_load = simulated + offline_penalty
    if total_load == 0:
        return
    replica_count = state.get_replica_count()
    per_pod = total_load / replica_count
    iterations = int(per_pod * 50_000)
    logger.info(
        "Simulating load: total=%d%% (simulated=%d%% + dc_penalty=%d%%), "
        "pods=%d, per_pod=%.1f%%, iterations=%d",
        total_load, simulated, offline_penalty, replica_count, per_pod, iterations,
    )
    total = 0
    for i in range(iterations):
        total += i * i


# ── Models ────────────────────────────────────────────────────────────────────
class StatusUpdate(BaseModel):
    status: str  # online | degraded | offline


class LoadLevel(BaseModel):
    level: int  # 0-100


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
    logger.info("GET /api/datacenters — serving %d datacenters", len(DATACENTERS))
    _simulate_load()
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

    logger.info("Datacenter %s (%s) status → %s", dc_id, dc["display_name"], body.status)
    if body.status == "online":
        state.set_datacenter_fields(dc_id,
                                    status="online",
                                    capacity_pct=dc["base_capacity_pct"],
                                    workload_count=dc["base_workload_count"])
        _restore_load()
        logger.info("Load restored — all degraded hubs reset to baseline")
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
        logger.info("Load redistributed — offline hub workload spread to remaining majors")

    return state.get_datacenter(dc_id)


@app.post("/api/load")
def set_load(body: LoadLevel):
    """Set the simulated traffic load level (0-100)."""
    clamped = max(0, min(100, body.level))
    state.set_simulated_load(clamped)
    logger.info("Simulated traffic set to %d%%", clamped)
    return {"status": "ok", "level": clamped}


@app.get("/api/load")
def get_load():
    """Return current load breakdown."""
    simulated = state.get_simulated_load()
    offline_penalty = state.count_offline_majors() * 15
    total_load = simulated + offline_penalty
    replica_count = state.get_replica_count()
    per_pod = round(total_load / replica_count, 1)
    return {
        "simulated_load": simulated,
        "offline_penalty": offline_penalty,
        "total_load": total_load,
        "replica_count": replica_count,
        "per_pod_load": per_pod,
        "api_version": app.version,
    }


@app.post("/api/reset")
def reset_all():
    """Reset all datacenters and simulated load to defaults."""
    logger.info("Resetting all datacenters and simulated load to defaults")
    state.reset_state()
    return {"status": "reset", "datacenters": len(DATACENTERS)}


# ── Health check demo endpoints ───────────────────────────────────────────────
@app.post("/api/break")
def break_api():
    """Make the health endpoint return 500 — used in the health check lab."""
    global _api_broken
    _api_broken = True
    logger.warning("Health check BROKEN — pod %s will be restarted by liveness probe", _HOSTNAME)
    return {"status": "broken", "message": "Health check will now fail. OCP will restart this pod."}


@app.post("/api/restore")
def restore_api():
    """Restore health — reachable only if the pod hasn't been restarted yet."""
    global _api_broken
    _api_broken = False
    logger.info("Health check RESTORED on pod %s", _HOSTNAME)
    return {"status": "restored"}
