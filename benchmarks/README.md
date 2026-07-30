# Benchmarks

`compile_scaling.py` grows the fictional control-core example while preserving
the recipe graph. It records wall time, process CPU time and router telemetry.

```bash
python benchmarks/compile_scaling.py
python benchmarks/compile_scaling.py --rates 8,64,128 --repeats 3
python benchmarks/compile_scaling.py --rates 8 --format json
```

The benchmark has no pass/fail timing threshold because shared CI runners are
not stable performance environments. It is useful for comparing commits on the
same machine and for catching large changes in expanded A* states.

`core_equivalents` is process CPU time divided by wall time. Values near `1.0`
mean one logical core was active; values above `1.0` indicate effective
parallel execution. Runs shorter than 50 ms report `n/a`, because the Windows
process CPU clock is too coarse for a trustworthy ratio at that scale.
