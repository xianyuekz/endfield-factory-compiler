"""Endfield Factory Compiler public API."""

from .compiler import CompilationResult, compile_project
from .execution import ExecutionOptions
from .pack import load_project, load_region_pack
from .routing import GridAStarRouter
from .routing_backend import RouterBackend, RoutingStats

__all__ = [
    "CompilationResult",
    "ExecutionOptions",
    "GridAStarRouter",
    "RouterBackend",
    "RoutingStats",
    "compile_project",
    "load_project",
    "load_region_pack",
]

__version__ = "0.3.1"
