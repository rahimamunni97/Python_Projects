"""
Dispatch UI Launcher
====================

This tiny module is the **entry point** for the Ride-Hailing Dispatch UI.

It provides a safe `__main__` block that either:
  1) launches the app with a provided *procedural backend* (a dict of plain
     functions), or
  2) falls back to the engine’s built-in default backend if no backend is
     available, available only to the teacher.

What is a "procedural backend"?
-------------------------------
A backend is a mapping (plain `dict`) with these callables:

- load_drivers(path: str) -> list[dict]
    Load driver entities from a CSV or similar source.

- load_requests(path: str) -> list[dict]
    Load request entities from a CSV or similar source.

- generate_drivers(n: int, width: int, height: int) -> list[dict]
    Generate `n` random drivers within the grid bounds.

- generate_requests(start_t: int, out_list: list[dict], req_rate: float,
                    width: int, height: int) -> None
    Append newly generated requests into `out_list`.

- init_state(drivers: list[dict], requests: list[dict], timeout: int,
             req_rate: float, width: int, height: int) -> dict
    Build the simulator state dictionary consumed by the UI/engine.

- simulate_step(state: dict) -> tuple[dict, dict]
    Advance the simulation one tick and return (new_state, metrics).

Usage
-----
Run directly:

    python -m gui.launch

or import and call `main()` with your backend:

    from gui.launch import main
    backend = {...}  # as specified above
    main(backend)

Notes
-----
- If you don’t pass a backend (or the optional import below fails),
  `run_app()` is called without arguments and is expected to construct
  a default backend internally, only for the teachers.
"""

from __future__ import annotations

from typing import Optional, Dict, Callable, Tuple, Any
from gui._engine import run_app


def main(backend: Optional[Dict[str, Callable[..., Any]]] = None) -> None:
    """
    Launch the Dispatch UI.

    Parameters
    ----------
    backend : dict[str, Callable] | None, optional
        Procedural backend mapping. If provided, it must include the six
        functions listed in the module docstring. If `None`, the engine’s
        default backend is used.

    Behavior
    --------
    - When `backend` is not None, forwards it to `run_app(backend)`.
    - Otherwise, calls `run_app()` with no arguments and relies on the engine
      to create a default backend.

    Raises
    ------
    Whatever `run_app` may raise if backend validation fails internally.
    """
    if backend is not None:
        run_app(backend)
    else:
        run_app()


if __name__ == "__main__":
    sim_mod = None
    try:
        from phase1 import io_mod, sim_mod  # type: ignore

        _backend = {
            "load_drivers": io_mod.load_drivers,
            "load_requests": io_mod.load_requests,
            "generate_drivers": io_mod.generate_drivers,
            "generate_requests": io_mod.generate_requests,
            "init_state": sim_mod.init_state,
            "simulate_step": sim_mod.simulate_step,
        }
    except Exception:
        _backend = None

    main(_backend)

    # --------------------------------------------------------------
    # POST-SIMULATION METRICS PLOTTING
    # --------------------------------------------------------------
    if sim_mod is not None:
        try:
            import matplotlib.pyplot as plt  # type: ignore
            
            served = list(getattr(sim_mod, "served_history", []))
            expired = list(getattr(sim_mod, "expired_history", []))
            avg_wait = list(getattr(sim_mod, "wait_history", []))
            
            if served:
                steps = list(range(1, len(served) + 1))
                plt.figure(figsize=(12, 6))
                plt.plot(steps, served, label="Served Requests", linewidth=2)
                plt.plot(steps, expired, label="Expired Requests", linewidth=2)
                plt.plot(steps, avg_wait, label="Average Wait Time", linewidth=2)
                plt.title("Simulation Metrics Over Time", fontsize=14, fontweight="bold")
                plt.xlabel("Simulation Step", fontsize=12)
                plt.ylabel("Count / Minutes", fontsize=12)
                plt.legend(loc="best", fontsize=10)
                plt.grid(True, linestyle="--", alpha=0.4)
                plt.tight_layout()
                plt.show()
            else:
                print("\n(No metric data recorded during the simulation.)\n")
        except ImportError:
            print("\n(Matplotlib not available - skipping metrics plot.)\n")
        except Exception as exc:
            print(f"\n(Error generating metrics plot: {exc})\n")