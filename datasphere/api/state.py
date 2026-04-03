"""Shared datacenter state — Redis-backed with in-memory fallback.

If REDIS_URL is set and reachable, all datacenter state lives in Redis
hashes (one per datacenter, keyed ``dc:<id>``).  If Redis is unavailable
the module falls back to a plain Python dict — identical to the original
single-pod behaviour.

The ``_api_broken`` health flag is intentionally kept per-pod (in-memory)
so the health-probe lab can break one pod without affecting others.
"""

import json
import logging
import os
from typing import Optional

import redis as redis_lib

from seed_data import DATACENTERS

logger = logging.getLogger("datasphere.state")

# ── Redis connection ────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "")
_redis: Optional[redis_lib.Redis] = None
_use_redis = False

if REDIS_URL:
    try:
        _redis = redis_lib.Redis.from_url(REDIS_URL, decode_responses=True)
        _redis.ping()
        _use_redis = True
        logger.info("Connected to Redis at %s", REDIS_URL)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — falling back to in-memory state", exc)
        _redis = None
        _use_redis = False

# ── In-memory fallback ──────────────────────────────────────────────────────
_state: dict[str, dict] = {}

# Fields stored in Redis hashes (all stored as strings)
_REDIS_FIELDS = ("status", "capacity_pct", "workload_count", "uptime_pct")
_SEED_SENTINEL = "datasphere:seeded"


def _dc_key(dc_id: str) -> str:
    return f"dc:{dc_id}"


def _seed_defaults() -> dict[str, dict]:
    """Build the default state dict from seed data."""
    result = {}
    for dc in DATACENTERS:
        result[dc["id"]] = {
            **dc,
            "status": "online",
            "capacity_pct": dc["base_capacity_pct"],
            "workload_count": dc["base_workload_count"],
            "uptime_pct": 99.97 if dc["tier"] == "major" else 99.5,
        }
    return result


# ── Public API ──────────────────────────────────────────────────────────────

def init_state() -> None:
    """Seed datacenters into Redis (or the in-memory dict) if not already done."""
    defaults = _seed_defaults()

    if _use_redis:
        if not _redis.exists(_SEED_SENTINEL):
            pipe = _redis.pipeline()
            for dc_id, dc in defaults.items():
                pipe.hset(_dc_key(dc_id), mapping={
                    "status": dc["status"],
                    "capacity_pct": str(dc["capacity_pct"]),
                    "workload_count": str(dc["workload_count"]),
                    "uptime_pct": str(dc["uptime_pct"]),
                })
            pipe.set(_SEED_SENTINEL, "1")
            pipe.execute()
            logger.info("Seeded %d datacenters into Redis", len(defaults))
        else:
            logger.info("Redis already seeded — skipping")
    else:
        _state.clear()
        _state.update(defaults)


def get_all_datacenters() -> list[dict]:
    """Return all datacenters with current state merged onto seed data."""
    if _use_redis:
        result = []
        for dc in DATACENTERS:
            dc_id = dc["id"]
            stored = _redis.hgetall(_dc_key(dc_id))
            if stored:
                merged = {**dc}
                merged["status"] = stored.get("status", "online")
                merged["capacity_pct"] = int(stored.get("capacity_pct", dc["base_capacity_pct"]))
                merged["workload_count"] = int(stored.get("workload_count", dc["base_workload_count"]))
                merged["uptime_pct"] = float(stored.get("uptime_pct", 99.5))
                result.append(merged)
            else:
                result.append({**dc, "status": "online",
                               "capacity_pct": dc["base_capacity_pct"],
                               "workload_count": dc["base_workload_count"],
                               "uptime_pct": 99.97 if dc["tier"] == "major" else 99.5})
        return result
    else:
        return list(_state.values())


def get_datacenter(dc_id: str) -> Optional[dict]:
    """Return a single datacenter or None if not found."""
    if _use_redis:
        stored = _redis.hgetall(_dc_key(dc_id))
        if not stored:
            return None
        # Find the seed entry for static fields
        seed = next((dc for dc in DATACENTERS if dc["id"] == dc_id), None)
        if not seed:
            return None
        return {
            **seed,
            "status": stored.get("status", "online"),
            "capacity_pct": int(stored.get("capacity_pct", seed["base_capacity_pct"])),
            "workload_count": int(stored.get("workload_count", seed["base_workload_count"])),
            "uptime_pct": float(stored.get("uptime_pct", 99.5)),
        }
    else:
        return _state.get(dc_id)


def set_datacenter_fields(dc_id: str, **fields) -> None:
    """Update specific fields for a datacenter."""
    if _use_redis:
        # Convert all values to strings for Redis hash storage
        str_fields = {k: str(v) for k, v in fields.items()}
        _redis.hset(_dc_key(dc_id), mapping=str_fields)
    else:
        if dc_id in _state:
            _state[dc_id].update(fields)


def get_datacenter_field(dc_id: str, field: str):
    """Read a single field from a datacenter."""
    if _use_redis:
        val = _redis.hget(_dc_key(dc_id), field)
        return val
    else:
        dc = _state.get(dc_id)
        return dc.get(field) if dc else None


def count_offline_majors() -> int:
    """Count major hubs that are offline — used for CPU burn calculation."""
    if _use_redis:
        count = 0
        for dc in DATACENTERS:
            if dc["tier"] == "major":
                status = _redis.hget(_dc_key(dc["id"]), "status")
                if status == "offline":
                    count += 1
        return count
    else:
        return sum(
            1 for dc in _state.values()
            if dc["tier"] == "major" and dc["status"] == "offline"
        )


def get_online_major_ids(exclude_id: str) -> list[str]:
    """Return IDs of online major hubs, excluding a given ID."""
    if _use_redis:
        result = []
        for dc in DATACENTERS:
            if dc["tier"] == "major" and dc["id"] != exclude_id:
                status = _redis.hget(_dc_key(dc["id"]), "status")
                if status != "offline":
                    result.append(dc["id"])
        return result
    else:
        return [
            dc_id for dc_id, dc in _state.items()
            if dc_id != exclude_id and dc["tier"] == "major" and dc["status"] != "offline"
        ]


def reset_state() -> None:
    """Reset all datacenters to defaults."""
    if _use_redis:
        pipe = _redis.pipeline()
        for dc in DATACENTERS:
            pipe.delete(_dc_key(dc["id"]))
        pipe.delete(_SEED_SENTINEL)
        pipe.execute()
        # Re-seed
        init_state()
    else:
        _state.clear()
        defaults = _seed_defaults()
        _state.update(defaults)
