import unittest

from benchmarks.compile_scaling import run_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_scaling_benchmark_emits_router_telemetry(self):
        rows = run_benchmark([8], repeats=1, jobs=1)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.target_rate, 8)
        self.assertEqual(row.devices, 13)
        self.assertEqual(row.routes, 25)
        self.assertGreater(row.expanded_states, 0)
        self.assertGreater(row.routing_ms, 0)
        self.assertEqual(row.effective_jobs, 1)


if __name__ == "__main__":
    unittest.main()
