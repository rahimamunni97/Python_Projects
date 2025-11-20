from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Tuple

from .io_mod import generate_requests


Driver = Dict[str, object]
Request = Dict[str, object]
State = Dict[str, object]

served_history: List[int] = []
expired_history: List[int] = []
wait_history: List[float] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _reset_histories() -> None:
    served_history.clear()
    expired_history.clear()
    wait_history.clear()


def _normalise_driver(driver: Driver) -> Driver:
    driver.setdefault("vx", 0.0)
    driver.setdefault("vy", 0.0)
    driver.setdefault("speed", 1.0)
    driver["speed"] = max(float(driver["speed"]), 0.1)
    driver.setdefault("tx", None)
    driver.setdefault("ty", None)
    driver.setdefault("target_id", None)
    return driver


def _normalise_request(request: Request) -> Request:
    request.setdefault("t", 0)
    request.setdefault("t_wait", 0)
    request.setdefault("status", "waiting")
    request.setdefault("driver_id", None)
    return request


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def _step_towards(x: float, y: float, tx: float, ty: float, speed: float) -> Tuple[float, float, bool]:
    dist = _distance(x, y, tx, ty)
    if dist <= speed or dist < 1e-6:
        return tx, ty, True
    ratio = speed / dist
    nx = x + (tx - x) * ratio
    ny = y + (ty - y) * ratio
    return nx, ny, False


def _release_future_requests(state: State) -> None:
    current_time = state["t"]
    future: List[Request] = state["future"]  # type: ignore[assignment]
    ready, upcoming = [], []
    for req in future:
        if req.get("t", 0) <= current_time:
            req["status"] = "waiting"
            ready.append(req)
        else:
            upcoming.append(req)
    state["future"] = sorted(upcoming, key=lambda r: r.get("t", 0))
    state["pending"].extend(ready)  # type: ignore[arg-type]


def _update_waits_and_expire(state: State) -> None:
    timeout = state["timeout"]
    now = state["t"]
    pending: List[Request] = state["pending"]  # type: ignore[assignment]
    drivers: List[Driver] = state["drivers"]  # type: ignore[assignment]
    for req in pending:
        status = req.get("status", "waiting")
        if status in {"delivered", "expired"}:
            continue
        age = now - int(req.get("t", 0))
        req["t_wait"] = max(age, int(req.get("t_wait", 0)))
        if age >= timeout:
            req["status"] = "expired"
            state["expired"] += 1
            driver_id = req.get("driver_id")
            if driver_id is not None:
                for driver in drivers:
                    if driver.get("id") == driver_id and driver.get("target_id") == req.get("id"):
                        driver["target_id"] = None
                        driver["tx"] = None
                        driver["ty"] = None
                        break
            req["driver_id"] = None


def _assign_requests(state: State) -> None:
    drivers: List[Driver] = state["drivers"]  # type: ignore[assignment]
    pending: List[Request] = state["pending"]  # type: ignore[assignment]
    waiting_requests = [req for req in pending if req.get("status") == "waiting"]
    waiting_requests.sort(key=lambda r: (r.get("t", 0), r.get("id", 0)))
    idle_drivers = [drv for drv in drivers if drv.get("target_id") is None]

    for req in waiting_requests:
        if not idle_drivers:
            break
        target_point = (float(req["px"]), float(req["py"]))  # type: ignore[index]
        best_driver = min(
            idle_drivers,
            key=lambda d: _distance(float(d["x"]), float(d["y"]), target_point[0], target_point[1]),
        )
        req["status"] = "assigned"
        req["driver_id"] = best_driver.get("id")
        best_driver["target_id"] = req.get("id")
        best_driver["tx"], best_driver["ty"] = target_point
        idle_drivers.remove(best_driver)


def _request_by_id(pending: Iterable[Request], request_id) -> Optional[Request]:
    for req in pending:
        if req.get("id") == request_id:
            return req
    return None


def _move_drivers(state: State) -> None:
    drivers: List[Driver] = state["drivers"]  # type: ignore[assignment]
    pending: List[Request] = state["pending"]  # type: ignore[assignment]
    for driver in drivers:
        target_id = driver.get("target_id")
        if target_id is None:
            continue
        req = _request_by_id(pending, target_id)
        if req is None:
            driver["target_id"] = None
            continue

        tx = driver.get("tx")
        ty = driver.get("ty")
        if tx is None or ty is None:
            driver["target_id"] = None
            continue

        nx, ny, reached = _step_towards(
            float(driver["x"]),
            float(driver["y"]),
            float(tx),
            float(ty),
            float(driver.get("speed", 1.0)),
        )
        driver["x"], driver["y"] = nx, ny

        if req.get("status") == "assigned" and reached:
            req["status"] = "picked"
            driver["tx"], driver["ty"] = req.get("dx"), req.get("dy")
        elif req.get("status") == "picked" and reached:
            req["status"] = "delivered"
            state["served"] += 1
            state["served_waits"].append(req.get("t_wait", 0))  # type: ignore[arg-type]
            driver["target_id"] = None
            driver["tx"] = None
            driver["ty"] = None


def _cleanup_requests(state: State) -> None:
    pending: List[Request] = state["pending"]  # type: ignore[assignment]
    state["pending"] = [req for req in pending if req.get("status") not in {"delivered", "expired"}]


def _record_metrics(state: State) -> Dict[str, float]:
    served = state["served"]
    expired = state["expired"]
    waits: List[float] = state["served_waits"]  # type: ignore[assignment]
    avg_wait = sum(waits) / len(waits) if waits else 0.0
    served_history.append(served)
    expired_history.append(expired)
    wait_history.append(avg_wait)
    state.setdefault(
        "metrics_history",
        {"served": served_history, "expired": expired_history, "avg_wait": wait_history},
    )
    return {"served": served, "expired": expired, "avg_wait": avg_wait}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def init_state(
    drivers: List[Driver],
    requests: List[Request],
    timeout: int,
    req_rate: float,
    width: int,
    height: int,
) -> State:
    """
    Build the simulation state dictionary required by the GUI engine.
    """
    _reset_histories()
    normalised_drivers = [_normalise_driver(dict(driver)) for driver in drivers]
    normalised_requests = [_normalise_request(dict(req)) for req in requests]

    pending: List[Request] = []
    future: List[Request] = []
    for req in normalised_requests:
        if req.get("t", 0) <= 0:
            pending.append(req)
        else:
            future.append(req)
    future.sort(key=lambda r: r.get("t", 0))

    state: State = {
        "t": 0,
        "drivers": normalised_drivers,
        "pending": pending,
        "future": future,
        "served": 0,
        "expired": 0,
        "timeout": max(1, timeout),
        "served_waits": [],
        "req_rate": max(0.0, float(req_rate)),
        "width": width,
        "height": height,
        "history": {"served": served_history, "expired": expired_history, "avg_wait": wait_history},
    }
    return state


def simulate_step(state: State) -> Tuple[State, Dict[str, float]]:
    """
    Advance the simulation one time unit.
    """
    _release_future_requests(state)
    generate_requests(state["t"], state["pending"], state["req_rate"], state["width"], state["height"])  # type: ignore[arg-type]
    _update_waits_and_expire(state)
    _assign_requests(state)
    _move_drivers(state)
    _cleanup_requests(state)
    metrics = _record_metrics(state)
    state["t"] += 1
    return state, metrics


__all__ = [
    "init_state",
    "simulate_step",
    "served_history",
    "expired_history",
    "wait_history",
]

