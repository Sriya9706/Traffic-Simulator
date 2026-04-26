"""
traffic_sim – Modular traffic simulation library.

Public API:
    Road             – directional road with capacity
    Junction         – 2/3/4-way junction with traffic lights
    Source           – vehicle generator (constant or Poisson rate)
    Sink             – vehicle absorber / destination
    SimulationEngine – runs the simulation and records history
    make_gif         – produce animated GIF output
    make_static_summary – produce static summary image
"""

from .road import Road
from .junction import Junction
from .source_sink import Source, Sink
from .vehicle import Vehicle
from .engine import SimulationEngine
from .visualizer import make_gif, make_static_summary

__all__ = [
    "Road",
    "Junction",
    "Source",
    "Sink",
    "Vehicle",
    "SimulationEngine",
    "make_gif",
    "make_static_summary",
]
