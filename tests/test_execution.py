import unittest
from pathlib import Path

from endfield_factory_compiler.compiler import compile_project
from endfield_factory_compiler.execution import (
    ExecutionOptions,
    resolve_performance_profile,
)
from endfield_factory_compiler.pack import load_project, load_region_pack
from endfield_factory_compiler.routing import GridAStarRouter, route_logistics


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "control-core.json"


class _RecordingRouter:
    name = "recording-router"

    def __init__(self):
        self.called = False

    def route(self, problem, options):
        self.called = True
        result = GridAStarRouter().route(problem, options)
        result.stats.backend_name = self.name
        return result


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.project = load_project(PROJECT)
        self.pack = load_region_pack(self.project.region_pack_path)

    def test_execution_options_validate_resources(self):
        with self.assertRaises(ValueError):
            ExecutionOptions(profile="turbo-furnace")
        for jobs in (0, -1, 1.5, True):
            with self.subTest(jobs=jobs):
                with self.assertRaises(ValueError):
                    ExecutionOptions(jobs=jobs)
        for limit in (0, -1, True, "fast", float("nan"), float("inf")):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    ExecutionOptions(time_limit_seconds=limit)
        with self.assertRaises(ValueError):
            ExecutionOptions(seed=True)
        self.assertEqual(
            resolve_performance_profile("low-power").floorplan_max_candidates,
            300,
        )

    def test_compilation_exposes_router_telemetry(self):
        result = compile_project(
            self.project,
            self.pack,
            options=ExecutionOptions(jobs=4, seed=7),
        )
        stats = result.routing_stats
        self.assertEqual(stats.backend_name, "serial-compact-grid-astar")
        self.assertEqual(stats.requested_jobs, 4)
        self.assertEqual(stats.effective_jobs, 1)
        self.assertEqual(stats.routes_requested, len(result.layout.routes))
        self.assertEqual(
            stats.routes_completed + stats.routes_failed,
            stats.routes_requested,
        )
        self.assertGreater(stats.expanded_states, 0)
        self.assertGreater(stats.peak_frontier, 0)
        self.assertGreater(stats.elapsed_seconds, 0)
        self.assertGreaterEqual(stats.cpu_seconds, 0)
        self.assertIn(
            "ROUTER_SERIAL_FALLBACK",
            {diagnostic.code for diagnostic in result.diagnostics},
        )
        plan = result.to_dict()
        self.assertEqual(plan["execution"]["profile"], "balanced")
        self.assertEqual(plan["execution"]["jobs"], 4)
        self.assertEqual(plan["routing_stats"]["seed"], 7)

    def test_soft_time_limit_is_reported(self):
        result = compile_project(
            self.project,
            self.pack,
            options=ExecutionOptions(time_limit_seconds=1e-12),
        )
        self.assertTrue(result.routing_stats.timed_out)
        self.assertTrue(result.has_errors)
        self.assertIn(
            "ROUTING_TIME_LIMIT_EXCEEDED",
            {diagnostic.code for diagnostic in result.diagnostics},
        )

    def test_router_backend_is_injectable(self):
        router = _RecordingRouter()
        result = compile_project(self.project, self.pack, router=router)
        self.assertTrue(router.called)
        self.assertEqual(result.routing_stats.backend_name, "recording-router")
        self.assertFalse(result.has_errors)

    def test_legacy_route_wrapper_still_returns_routes(self):
        result = compile_project(self.project, self.pack)
        routes = route_logistics(
            self.pack,
            result.synthesis,
            result.layout.devices,
        )
        self.assertIsInstance(routes, list)
        self.assertTrue(routes)


if __name__ == "__main__":
    unittest.main()
