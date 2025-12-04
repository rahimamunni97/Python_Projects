"""Ride-Hailing Dispatch UI 

This module implements a lightweight visualization and control interface for a
ride-hailing dispatch simulation using **DearPyGui**. It is designed for the
students of DS830, DM857 for the phase1 of their projects.

Overview
========
The system simulates drivers and passenger requests inside a 2D grid. The UI
lets you initialize from CSVs or generate data, then step or run the
simulation continuously while visualizing:

- Driver locations (blue)
- Pickups waiting/assigned (red)
- Dropoffs after pickup (green)
- Direction arrows from each driver toward their current target

Architecture
============
1. State containers (dataclasses)
   - ``AppSimState`` wraps the dictionary the simulator expects.
   - ``RuntimeState`` holds GUI loop parameters (time, speed, horizon, running).
   - ``AppContext`` composes both into a single global ``APP``.

2. Procedural backend (no classes/objects)
   - A backend is a ``BackendFns`` mapping of required function names to
     callables: load/generate I/O, ``init_state`` and ``simulate_step``.
   - ``make_default_backend()`` wires to ``phase1.io_mod`` and
     ``phase1.sim_mod`` so students can run without writing their own backend.

3. Adapter layer
   - ``_adapter_*`` functions translate UI input into backend calls and collect
     data for plotting.

4. DearPyGui UI
   - Sliders, buttons, and a plot with three scatter series and arrow overlays.

Usage
=====
Run directly:
    python dispatch_ui.py

Or from Python:
    from dispatch_ui import run_app, make_default_backend
    run_app(make_default_backend())

To use your own procedural backend:
    backend = {
        "load_drivers": my_load_drivers,
        "load_requests": my_load_requests,
        "generate_drivers": my_generate_drivers,
        "generate_requests": my_generate_requests,
        "init_state": my_init_state,
        "simulate_step": my_simulate_step,
    }
    run_app(backend)

Notes
-----
* Coordinates default to a 50×30 grid; change ``GRID_WIDTH``/``GRID_HEIGHT``
  to match your data.
* The simulator is expected to accept and return a state ``dict`` compatible
  with the keys used here (``t``, ``drivers``, ``pending``, etc.).
* The Run button uses a blocking loop but remains visually
  responsive thanks to ``dpg.split_frame()`` each iteration (it took me ages to get this).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, TypedDict
import math
import time

import dearpygui.dearpygui as dpg

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GRID_WIDTH: int = 50
GRID_HEIGHT: int = 30
ARROW_LENGTH: float = 1.0  # visual length of direction arrows
EPS: float = 1e-9          # small epsilon for numeric stability


# ---------------------------------------------------------------------------
# Dataclasses for state
# ---------------------------------------------------------------------------
@dataclass
class AppSimState:
    """Container for the simulator state dictionary.

    The simulator itself works with plain dictionaries. We keep that contract
    but wrap it in a dataclass for safer, typed access from the UI.

    Keys used by the UI and adapter:
      - ``t`` (int): current simulation time
      - ``drivers`` (list[dict]): driver entities with at least ``x``, ``y``;
        optionally ``vx``, ``vy``, ``tx``, ``ty``, ``target_id``/``rid``
      - ``pending`` (list[dict]): request entities with pickup ``(px,py)``,
        dropoff ``(dx,dy)``, a ``status`` in {"waiting","assigned","picked"},
        and possibly an appearance time ``t``
      - ``served`` (int), ``expired`` (int): counters
    """

    sim: Dict = field(
        default_factory=lambda: {
            "t": 0,
            "drivers": [],
            "pending": [],
            "served": 0,
            "expired": 0,
        }
    )

    @property
    def t(self) -> int:
        """Current simulation time (int)."""
        return int(self.sim.get("t", 0))

    @t.setter
    def t(self, value: int) -> None:
        self.sim["t"] = int(value)

    @property
    def drivers(self) -> List[dict]:
        """Shallow copy of driver list to avoid accidental mutation."""
        return list(self.sim.get("drivers", []))

    @property
    def pending(self) -> List[dict]:
        """Shallow copy of pending request list."""
        return list(self.sim.get("pending", []))

    @property
    def served(self) -> int:
        """Number of served requests so far."""
        return int(self.sim.get("served", 0))

    @property
    def expired(self) -> int:
        """Number of expired requests so far."""
        return int(self.sim.get("expired", 0))


@dataclass
class RuntimeState:
    """UI runtime state (separate from the simulator state)."""

    running: bool = False
    speed: int = 30           # ms per sim step (UI pacing)
    clock: int = 0            # mirrors AppSimState.t for rendering
    horizon: int = 600        # max simulated time


@dataclass
class AppContext:
    """Composition root holding both app and runtime state."""

    state: AppSimState = field(default_factory=AppSimState)
    rt: RuntimeState = field(default_factory=RuntimeState)


# Global application context (single instance used by the UI)
APP = AppContext()


# ---------------------------------------------------------------------------
# Procedural backend interface
# ---------------------------------------------------------------------------
class BackendFns(TypedDict):
    """Typed mapping of required backend callables.

    Students can implement these as plain functions and pass them via a dict
    to ``run_app(backend)``.

    Required functions
    ------------------
    load_drivers(path) -> list[dict]
        Load driver entities from a CSV or similar source.

    load_requests(path) -> list[dict]
        Load request entities from a CSV or similar source.

    generate_drivers(n, width, height) -> list[dict]
        Generate ``n`` random drivers within the grid bounds.

    generate_requests(start_t, out_list, req_rate, width, height) -> None
        Append generated requests to ``out_list`` (Poisson-like rate allowed).

    init_state(drivers, requests, timeout, req_rate, width, height) -> dict
        Build the simulator state dictionary.

    simulate_step(state) -> (state, metrics)
        Advance the simulation by one step and return updated ``state`` and a
        ``metrics`` dict (e.g., ``{"served": int, "expired": int, "avg_wait": float}``).
    """

    load_drivers: Callable[[str], List[dict]]
    load_requests: Callable[[str], List[dict]]
    generate_drivers: Callable[[int, int, int], List[dict]]
    generate_requests: Callable[[int, List[dict], float, int, int], None]
    init_state: Callable[[List[dict], List[dict], int, float, int, int], Dict]
    simulate_step: Callable[[Dict], Tuple[Dict, Dict]]


def make_default_backend() -> BackendFns:
    """Return a backend mapping wired to ``phase1.io_mod``/``sim_mod``.

    The returned mapping exposes the procedural functions expected by this UI,
    allowing students to run the app without writing a custom backend.
    """
    from phase1 import io_mod
    from phase1 import sim_mod

    return BackendFns(
        load_drivers=io_mod.load_drivers,
        load_requests=io_mod.load_requests,
        generate_drivers=io_mod.generate_drivers,
        generate_requests=io_mod.generate_requests,
        init_state=sim_mod.init_state,
        simulate_step=sim_mod.simulate_step,
    )


# ---------------------------------------------------------------------------
# Helper functions for direction inference and vector math
# ---------------------------------------------------------------------------
def _find_request_by_id(req_id: Optional[int | str]) -> Optional[dict]:
    """Return the pending request whose id matches ``req_id``.

    Accepts ``id``, ``rid``, or ``req_id`` keys on request dictionaries. If the
    id is ``None`` or not found, returns ``None``.
    """
    if req_id is None:
        return None
    for r in APP.state.pending:
        if r.get("id", r.get("rid", r.get("req_id"))) == req_id:
            return r
    return None


def _infer_direction_from_driver(d: dict) -> Tuple[float, float]:
    """Infer an unscaled direction vector ``(ux, uy)`` for a driver ``d``.

    Priority order:
      1) use explicit velocity (``vx``, ``vy``) if present
      2) else use explicit target position (``tx``, ``ty``)
      3) else use ``target_id``/``rid`` to find a request and aim at its pickup
      4) else aim at the nearest pending request (if any)
      5) else return ``(0.0, 0.0)``
    """
    x, y = float(d.get("x", 0.0)), float(d.get("y", 0.0))

    # 1) explicit velocity
    if "vx" in d and "vy" in d:
        return float(d["vx"]), float(d["vy"])

    # 2) explicit target position
    tx, ty = d.get("tx"), d.get("ty")
    if tx is not None and ty is not None:
        return float(tx) - x, float(ty) - y

    # 3) pointer to a request
    tgt_id = d.get("target_id", d.get("rid"))
    req = _find_request_by_id(tgt_id)
    if req is not None:
        px, py = req.get("px"), req.get("py")
        if px is not None and py is not None:
            return float(px) - x, float(py) - y

    # 4) fallback: nearest pending request
    pend = APP.state.pending
    if pend:
        nearest = min(
            pend,
            key=lambda r: (float(r.get("px", 0.0)) - x) ** 2 + (float(r.get("py", 0.0)) - y) ** 2,
        )
        px, py = float(nearest.get("px", 0.0)), float(nearest.get("py", 0.0))
        return px - x, py - y

    # 5) no target
    return 0.0, 0.0


def _normalize_and_scale(vec: Tuple[float, float], length: float = ARROW_LENGTH) -> Tuple[float, float]:
    """Return ``vec`` normalized and scaled to a target ``length``.

    If ``vec`` is near zero, returns ``(0.0, 0.0)`` to avoid exploding arrows.
    """
    vx, vy = vec
    n = math.hypot(vx, vy)
    if n < EPS:
        return 0.0, 0.0
    s = length / n
    return vx * s, vy * s


# ---------------------------------------------------------------------------
# Adapter API (UI <-> Backend)
# ---------------------------------------------------------------------------
def _adapter_init(
    backend: BackendFns,
    drivers_path: Optional[str],
    requests_path: Optional[str],
    n_drivers: int,
    req_rate: float,
    horizon: int,
    timeout: int,
) -> bool:
    """Initialize the simulator state and runtime via the provided backend.

    Parameters
    ----------
    backend:
        Mapping of function names to callables (see ``BackendFns``).
    drivers_path, requests_path:
        File paths to CSVs; if ``None``, random data are generated.
    n_drivers:
        Number of drivers to generate when ``drivers_path`` is ``None``.
    req_rate:
        Average requests per minute used for generation when
        ``requests_path`` is ``None``.
    horizon:
        Max simulation time (integer minutes) used to stop auto-running.
    timeout:
        Request expiration threshold (minutes), passed to the simulator.
    """
    # drivers
    if drivers_path:
        drivers = backend["load_drivers"](drivers_path)
    else:
        drivers = backend["generate_drivers"](n_drivers, GRID_WIDTH, GRID_HEIGHT)

    # requests
    if requests_path:
        reqs = backend["load_requests"](requests_path)
    else:
        reqs: List[dict] = []
        backend["generate_requests"](0, reqs, req_rate, GRID_WIDTH, GRID_HEIGHT)

    # determinism: sort by appearance time if present
    reqs.sort(key=lambda r: r.get("t", 0))

    # initialize simulator state
    APP.state.sim = backend["init_state"](drivers, reqs, timeout, req_rate, GRID_WIDTH, GRID_HEIGHT)

    # runtime mirrors
    APP.rt.horizon = int(horizon)
    APP.rt.clock = 0
    return True


def _adapter_step(backend: BackendFns) -> Tuple[int, Dict]:
    """Advance the simulation by one step using the backend.

    Returns
    -------
    (t, metrics)
        Updated simulation time ``t`` and a metrics dictionary produced by the
        backend (e.g., ``{"served": int, "expired": int, "avg_wait": float}``).
    """
    APP.state.sim, metrics = backend["simulate_step"](APP.state.sim)
    return APP.state.sim["t"], metrics


def _adapter_reset() -> None:
    """Reset only the simulation clock (keeps positions/state)."""
    APP.state.t = 0


def _adapter_plot_data() -> Tuple[
    List[Tuple[float, float]],
    List[Tuple[float, float]],
    List[Tuple[float, float]],
    int,
    int,
    List[Tuple[float, float, float, float]],
]:
    """Collect pre-formatted data for plotting the current simulation state.

    Returns
    -------
    drivers_xy, pickup_xy, dropoff_xy, served, expired, dir_quiver
        - ``drivers_xy``: list of (x, y) driver coordinates
        - ``pickup_xy``: list of (x, y) pickup coordinates for "waiting"/"assigned"
        - ``dropoff_xy``: list of (x, y) dropoff coordinates for "picked"
        - ``served``/``expired``: integer counters
        - ``dir_quiver``: list of (x, y, u, v) for direction arrows per driver
    """
    drivers_xy: List[Tuple[float, float]] = []
    dir_quiver: List[Tuple[float, float, float, float]] = []

    # drivers and directions
    for d in APP.state.drivers:
        x, y = float(d.get("x", 0.0)), float(d.get("y", 0.0))
        drivers_xy.append((x, y))
        ux, uy = _infer_direction_from_driver(d)
        u, v = _normalize_and_scale((ux, uy), ARROW_LENGTH)
        dir_quiver.append((x, y, u, v))

    # requests: split into pickup vs dropoff based on status
    pickup_xy: List[Tuple[float, float]] = []
    dropoff_xy: List[Tuple[float, float]] = []
    for r in APP.state.pending:
        rs = r.get("status")
        if rs in ("waiting", "assigned"):
            pickup_xy.append((float(r["px"]), float(r["py"])))
        elif rs == "picked":
            dropoff_xy.append((float(r["dx"]), float(r["dy"])))

    served = APP.state.served
    expired = APP.state.expired
    return drivers_xy, pickup_xy, dropoff_xy, served, expired, dir_quiver


# ---------------------------------------------------------------------------
# DearPyGui UI callbacks
# ---------------------------------------------------------------------------
def _on_init(sender, app_data, user_data) -> None:
    """Seed the simulation from the UI controls and redraw the plot.

    Reads all relevant UI inputs, calls ``_adapter_init(...)`` with the
    provided backend, and refreshes the status labels and plot.
    """
    backend: BackendFns = user_data["backend"]

    use_files = bool(dpg.get_value("use_files"))
    drivers_path = dpg.get_value("drivers_path") if use_files else None
    requests_path = dpg.get_value("requests_path") if use_files else None
    n_drivers = int(dpg.get_value("n_drivers"))
    req_rate = float(dpg.get_value("req_rate"))
    horizon = int(dpg.get_value("horizon"))
    timeout = int(dpg.get_value("timeout"))

    _adapter_init(backend, drivers_path, requests_path, n_drivers, req_rate, horizon, timeout)
    _update_status()
    _redraw_plot()


def _on_step(sender=None, app_data=None, user_data=None) -> None:
    """Advance one simulation step and refresh the UI.

    If the runtime clock has reached the horizon, the run loop is stopped and
    the Run button label is reset.
    """
    backend: BackendFns = user_data["backend"]

    if APP.rt.clock >= APP.rt.horizon:
        APP.rt.running = False
        dpg.configure_item("run_btn", label="Run")
        return

    t, metrics = _adapter_step(backend)
    APP.rt.clock = t
    _update_status(metrics)
    _redraw_plot()
 
def _on_run_toggle(sender, app_data, user_data) -> None:
    if APP.rt.running:
        APP.rt.running = False
        dpg.configure_item("run_btn", label="Run")
    else:
        APP.rt.running = True
        dpg.configure_item("run_btn", label="Stop")

def _on_reset(sender, app_data, user_data) -> None:
    """Reset the simulation clock and refresh the UI."""
    APP.rt.running = False
    dpg.configure_item("run_btn", label="Run")
    _adapter_reset()
    APP.rt.clock = 0
    _update_status()
    _redraw_plot()


def _on_speed_change(sender, app_data, user_data) -> None:
    """Update the runtime step delay (ms per step) from the slider value."""
    APP.rt.speed = int(dpg.get_value("speed"))


def _update_status(metrics: Optional[Dict] = None) -> None:
    """Write a status line reflecting time and aggregated metrics to the UI."""
    served = 0 if metrics is None else int(metrics.get("served", 0))
    expired = 0 if metrics is None else int(metrics.get("expired", 0))
    avg_wait = 0.0 if metrics is None else float(metrics.get("avg_wait", 0.0))
    label = f"t = {APP.rt.clock} | served = {served} | expired = {expired} | avg_wait={avg_wait:.2f}"
    dpg.set_value("status_text", label)


def _redraw_plot() -> None:
    """Refresh scatter series and direction arrows from current simulation state."""
    drivers_xy, pickup_xy, dropoff_xy, served, expired, dir_quiver = _adapter_plot_data()

    dx = [x for x, _ in drivers_xy]
    dy = [y for _, y in drivers_xy]
    px = [x for x, _ in pickup_xy]
    py = [y for _, y in pickup_xy]
    gx = [x for x, _ in dropoff_xy]
    gy = [y for _, y in dropoff_xy]

    dpg.configure_item("drv_series", x=dx, y=dy)
    dpg.configure_item("pickup_series", x=px, y=py)
    dpg.configure_item("dropoff_series", x=gx, y=gy)

    # redraw arrows
    dpg.delete_item("dir_draw", children_only=True)
    for (x, y, u, v) in dir_quiver:
        dpg.draw_line((x, y), (x + u, y + v), color=(128, 128, 128, 160), thickness=0.5, parent="dir_draw")

    dpg.set_value(
        "legend_text",
        f"drivers: {len(dx)} | pickups: {len(px)} | dropoffs: {len(gx)} | served={served} | expired={expired}",
    )


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------
def run_app(backend: Optional[BackendFns] = None) -> None:
    """Launch the DearPyGui application with a single *procedural* backend.

    Parameters
    ----------
    backend:
        Mapping of function names → callables (see ``BackendFns``). If omitted,
        ``make_default_backend()`` will wire to ``phase1.io_mod`` and
        ``phase1.sim_mod`` Antonio's implementation automatically (not avialable to the students).
    """
    backend = backend or make_default_backend()

    dpg.create_context()
    dpg.create_viewport(title="Ride-Hailing Dispatch — Phase 1", width=1320, height=760)

    # Themes (minimal but distinct colors)
    with dpg.theme(tag="theme_pickup_red"):
        with dpg.theme_component(dpg.mvScatterSeries):
            dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, (230, 60, 60, 255), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, (230, 60, 60, 255), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 6.0, category=dpg.mvThemeCat_Plots)

    with dpg.theme(tag="theme_dropoff_green"):
        with dpg.theme_component(dpg.mvScatterSeries):
            dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, (50, 200, 70, 255), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, (50, 200, 70, 255), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 6.0, category=dpg.mvThemeCat_Plots)

    with dpg.theme(tag="theme_drivers_blue"):
        with dpg.theme_component(dpg.mvScatterSeries):
            dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, (50, 120, 230, 255), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, (50, 120, 230, 255), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 6.0, category=dpg.mvThemeCat_Plots)

    with dpg.window(label="City Dispatch (Phase 1)", width=1320, height=760):
        with dpg.group(horizontal=True):
            # Left panel: initialize & run controls
            with dpg.child_window(width=600, height=680, border=True):
                dpg.add_text("Setup")
                dpg.add_separator()
                dpg.add_checkbox(label="Use CSV files", default_value=False, tag="use_files")
                dpg.add_input_text(label="Drivers CSV", tag="drivers_path", hint="data/drivers.csv", width=360)
                dpg.add_input_text(label="Requests CSV", tag="requests_path", hint="data/requests.csv", width=360)
                dpg.add_slider_int(label="Horizon (min)", tag="horizon", default_value=600, min_value=60, max_value=1440)
                dpg.add_slider_int(label="Timeout (min)", tag="timeout", default_value=10, min_value=0, max_value=120)
                dpg.add_slider_int(label="# Drivers (random)", tag="n_drivers", default_value=10, min_value=1, max_value=50)
                dpg.add_slider_float(label="Avg requests per min", tag="req_rate", default_value=3.0, min_value=0.0, max_value=10.0)
                dpg.add_button(label="Initialize", callback=_on_init, user_data={"backend": backend}, width=120)

                dpg.add_separator()
                dpg.add_text("Run Controls")
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Run", tag="run_btn", callback=_on_run_toggle, user_data={"backend": backend}, width=100)
                    dpg.add_button(label="Step", callback=_on_step, user_data={"backend": backend}, width=100)
                    dpg.add_button(label="Reset", callback=_on_reset, user_data={"backend": backend}, width=100)

                dpg.add_slider_int(
                    label="Speed (ms/step)", tag="speed", width=360,
                    default_value=30, min_value=1, max_value=500, callback=_on_speed_change
                )
                dpg.add_text("", tag="status_text")
                dpg.add_text("", tag="legend_text")

            # Right panel: plot
            with dpg.child_window(width=-1, height=680, border=True):
                dpg.add_text("Visualize")
                dpg.add_separator()
                with dpg.plot(label="Grid", height=-1, width=-1, tag="plot"):
                    dpg.add_plot_legend()
                    xaxis = dpg.add_plot_axis(dpg.mvXAxis, label="x", tag="x_axis")
                    yaxis = dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="y_axis")
                    dpg.set_axis_limits(xaxis, 0, GRID_WIDTH)
                    dpg.set_axis_limits(yaxis, 0, GRID_HEIGHT)

                    # series
                    dpg.add_scatter_series([], [], label="drivers", parent="y_axis", tag="drv_series")
                    dpg.bind_item_theme("drv_series", "theme_drivers_blue")

                    dpg.add_scatter_series([], [], label="pickups", parent="y_axis", tag="pickup_series")
                    dpg.bind_item_theme("pickup_series", "theme_pickup_red")

                    dpg.add_scatter_series([], [], label="dropoffs", parent="y_axis", tag="dropoff_series")
                    dpg.bind_item_theme("dropoff_series", "theme_dropoff_green")

                # draw arrows on top of the plot (must be parented to the plot)
                dpg.add_draw_layer(parent="plot", tag="dir_draw")

    dpg.setup_dearpygui()
    dpg.show_viewport()
    last = time.perf_counter()
    while dpg.is_dearpygui_running():
    # run one step at the chosen speed only if running
        if APP.rt.running and APP.rt.clock < APP.rt.horizon:
            now = time.perf_counter()
            if (now - last) >= (APP.rt.speed / 1000.0):
               
                APP.state.sim, metrics = backend["simulate_step"](APP.state.sim)
                APP.rt.clock = APP.state.sim["t"]
                _update_status(metrics)
                _redraw_plot()
                last = now
        dpg.render_dearpygui_frame()

dpg.destroy_context()   


if __name__ == "__main__":
    run_app()
