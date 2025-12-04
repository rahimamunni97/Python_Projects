"""
5.2 Adapter Functions
As in Part I, the GUI will interact with your backend through a small set of functions. At a minimum,
you must provide functions (in a separate module) that create and manipulate a DeliverySimulation
instance:
• init_simulation(...params...) -> None,
• step_simulation() -> tuple[int, dict] (returns current time and metrics),
• get_plot_data() -> ... (returns positions needed for plotting).
The exact function signatures will be given in the project repository, and will mirror the Part I
interface as closely as possible. Your task is to construct and manage the DeliverySimulation
object behind these functions.

"""
