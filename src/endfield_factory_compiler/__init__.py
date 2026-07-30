"""Endfield Factory Compiler public API."""

from .compiler import CompilationResult, compile_project
from .execution import (
    ExecutionOptions,
    PERFORMANCE_PROFILES,
    PerformanceProfile,
    resolve_performance_profile,
)
from .model import FloorplanSearchOptions, FloorplanSearchResult
from .pack import load_project, load_region_pack
from .routing import GridAStarRouter
from .routing_backend import RouterBackend, RoutingStats

__all__ = [
    "CompilationResult",
    "ExecutionOptions",
    "PERFORMANCE_PROFILES",
    "FloorplanSearchOptions",
    "FloorplanSearchResult",
    "GridAStarRouter",
    "PerformanceProfile",
    "RouterBackend",
    "RoutingStats",
    "compile_project",
    "load_project",
    "load_region_pack",
    "resolve_performance_profile",
]

__version__ = "0.4.4"
