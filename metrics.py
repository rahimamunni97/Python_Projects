"""
After closing the graphical application window, the program should display a new window or generate
plots summarizing the evolution of the simulation metrics over time. This secondary output is intended
to allow inspection and analysis of how the system performed during the simulation — for example,
trends in served or expired requests, or the progression of average waiting times — and should make
it possible to distinguish the earnings achieved under different policies.
"""

import matplotlib as mp
import os
import dearpygui as dp


