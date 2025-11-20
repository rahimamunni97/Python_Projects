from __future__ import annotations

import csv
import io
import math
import random
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence, Union


DriverRow = Union[Dict[str, str], Sequence[str]]
RequestRow = Union[Dict[str, str], Sequence[str]]

_DRIVER_ID_COUNTER = 0
_REQUEST_ID_COUNTER = 0


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _collect_input_files(path: Union[str, Path], prefix: str) -> List[Path]:
    root = Path(path)
    if root.is_dir():
        files = sorted(root.glob(f"{prefix}*.csv"))
    else:
        files = [root]
    return [fp for fp in files if fp.exists()]


def _clean_lines(file_path: Path) -> List[str]:
    cleaned: List[str] = []
    with file_path.open("r", newline="") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            cleaned.append(line)
    return cleaned


def _looks_like_header(line: str) -> bool:
    for cell in line.split(","):
        token = cell.strip()
        if not token:
            continue
        if any(ch.isalpha() for ch in token):
            return True
    return False


def _parse_csv_lines(lines: List[str]) -> Iterator[Union[Dict[str, str], List[str]]]:
    if not lines:
        return iter(())

    buffer = io.StringIO("".join(lines))
    if _looks_like_header(lines[0]):
        reader = csv.DictReader(buffer)
        return (
            {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k is not None}
            for row in reader
            if any(row.values())
        )

    reader = csv.reader(buffer)
    return (
        [cell.strip() for cell in row if cell.strip()]
        for row in reader
        if any(cell.strip() for cell in row)
    )


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_id(raw, fallback: int) -> Union[int, str]:
    if raw is None or raw == "":
        return fallback
    try:
        return int(raw)
    except (TypeError, ValueError):
        return str(raw)


def _bump_driver_counter(candidate) -> None:
    global _DRIVER_ID_COUNTER
    if isinstance(candidate, int):
        _DRIVER_ID_COUNTER = max(_DRIVER_ID_COUNTER, candidate + 1)


def _bump_request_counter(candidate) -> None:
    global _REQUEST_ID_COUNTER
    if isinstance(candidate, int):
        _REQUEST_ID_COUNTER = max(_REQUEST_ID_COUNTER, candidate + 1)


def _next_driver_id() -> int:
    global _DRIVER_ID_COUNTER
    value = _DRIVER_ID_COUNTER
    _DRIVER_ID_COUNTER += 1
    return value


def _next_request_id() -> int:
    global _REQUEST_ID_COUNTER
    value = _REQUEST_ID_COUNTER
    _REQUEST_ID_COUNTER += 1
    return value


def _extract_from_dict(data: Dict[str, str], keys: Iterable[str], default: float = 0.0) -> float:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return _safe_float(data[key], default)
    return default


def _build_driver_from_row(row: DriverRow) -> Dict[str, Union[int, float, str, None]]:
    if isinstance(row, dict):
        driver_id = _normalize_id(row.get("id"), _next_driver_id())
        _bump_driver_counter(driver_id)
        driver = {
            "id": driver_id,
            "x": _extract_from_dict(row, ("x", "px"), 0.0),
            "y": _extract_from_dict(row, ("y", "py"), 0.0),
            "vx": _extract_from_dict(row, ("vx",), 0.0),
            "vy": _extract_from_dict(row, ("vy",), 0.0),
            "speed": max(_extract_from_dict(row, ("speed", "v"), 1.0), 0.1),
            "tx": row.get("tx"),
            "ty": row.get("ty"),
            "target_id": row.get("target_id"),
        }
        return driver

    values = list(row)
    if len(values) < 2:
        raise ValueError("Driver rows must define at least x and y coordinates.")

    driver_id = _next_driver_id()
    driver = {
        "id": driver_id,
        "x": _safe_float(values[0], 0.0),
        "y": _safe_float(values[1], 0.0),
        "vx": 0.0,
        "vy": 0.0,
        "speed": max(_safe_float(values[2], 1.0) if len(values) > 2 else 1.0, 0.1),
        "tx": None,
        "ty": None,
        "target_id": None,
    }
    return driver


def _build_request_from_row(row: RequestRow) -> Dict[str, Union[int, float, str, None]]:
    if isinstance(row, dict):
        request_id = _normalize_id(row.get("id"), _next_request_id())
        _bump_request_counter(request_id)
        request = {
            "id": request_id,
            "px": _extract_from_dict(row, ("px", "pickup_x", "x"), 0.0),
            "py": _extract_from_dict(row, ("py", "pickup_y", "y"), 0.0),
            "dx": _extract_from_dict(row, ("dx", "dropoff_x"), 0.0),
            "dy": _extract_from_dict(row, ("dy", "dropoff_y"), 0.0),
            "t": _safe_int(row.get("t") or row.get("time"), 0),
            "t_wait": _safe_int(row.get("t_wait"), 0),
            "status": (row.get("status") or "waiting").strip().lower(),
            "driver_id": row.get("driver_id"),
        }
        if request["status"] not in {"waiting", "assigned", "picked", "delivered", "expired"}:
            request["status"] = "waiting"
        return request

    values = list(row)
    if len(values) < 5:
        raise ValueError("Request rows must follow the format: time, px, py, dx, dy.")

    request_id = _next_request_id()
    request = {
        "id": request_id,
        "t": _safe_int(values[0], 0),
        "px": _safe_float(values[1], 0.0),
        "py": _safe_float(values[2], 0.0),
        "dx": _safe_float(values[3], 0.0),
        "dy": _safe_float(values[4], 0.0),
        "t_wait": 0,
        "status": "waiting",
        "driver_id": None,
    }
    return request


def _load_rows(path: Union[str, Path], prefix: str) -> List[Union[Dict[str, str], List[str]]]:
    records: List[Union[Dict[str, str], List[str]]] = []
    for file_path in _collect_input_files(path, prefix):
        lines = _clean_lines(file_path)
        records.extend(list(_parse_csv_lines(lines)))
    return records


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def load_drivers(path: Union[str, Path]) -> List[Dict[str, Union[int, float, str, None]]]:
    """Load driver dictionaries from a CSV file or directory containing CSVs."""
    drivers: List[Dict[str, Union[int, float, str, None]]] = []
    for row in _load_rows(path, "drivers"):
        drivers.append(_build_driver_from_row(row))
    return drivers


def load_requests(path: Union[str, Path]) -> List[Dict[str, Union[int, float, str, None]]]:
    """Load request dictionaries from a CSV file or directory containing CSVs."""
    requests: List[Dict[str, Union[int, float, str, None]]] = []
    for row in _load_rows(path, "requests"):
        requests.append(_build_request_from_row(row))
    requests.sort(key=lambda r: r["t"])  # type: ignore[index]
    return requests


def generate_drivers(n: int, width: int, height: int) -> List[Dict[str, Union[int, float, str, None]]]:
    """Generate `n` random drivers within a rectangular grid."""
    drivers: List[Dict[str, Union[int, float, str, None]]] = []
    for _ in range(max(0, n)):
        driver_id = _next_driver_id()
        driver = {
            "id": driver_id,
            "x": random.uniform(0, width),
            "y": random.uniform(0, height),
            "vx": 0.0,
            "vy": 0.0,
            "speed": random.uniform(0.8, 1.2),
            "tx": None,
            "ty": None,
            "target_id": None,
        }
        drivers.append(driver)
    return drivers


def _poisson_sample(lmbda: float) -> int:
    if lmbda <= 0:
        return 0
    L = math.exp(-lmbda)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return max(0, k - 1)


def generate_requests(
    start_t: int,
    out_list: List[Dict[str, Union[int, float, str, None]]],
    req_rate: float,
    width: int,
    height: int,
) -> None:
    """Append new random requests to `out_list` based on a Poisson arrival process."""
    num_new = _poisson_sample(max(req_rate, 0.0))
    for _ in range(num_new):
        request_id = _next_request_id()
        request = {
            "id": request_id,
            "px": random.uniform(0, width),
            "py": random.uniform(0, height),
            "dx": random.uniform(0, width),
            "dy": random.uniform(0, height),
            "t": start_t,
            "t_wait": 0,
            "status": "waiting",
            "driver_id": None,
        }
        out_list.append(request)


__all__ = [
    "load_drivers",
    "load_requests",
    "generate_drivers",
    "generate_requests",
]

