# Quality Gates

The project is intentionally small, but changes should still pass checks that
match an EDA-style tool.

## Python

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests benchmarks
python benchmarks/compile_scaling.py --rates 8 --format json
python -m pip wheel --no-deps . --wheel-dir dist
```

## Rust

```bash
cargo fmt --check --all
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

The Rust route core is tested in CI but is not required to install the Python
package yet.

## Release Notes

Before tagging a release, regenerate the demo artifacts:

```bash
efc compile examples/control-core.json --out docs/assets/demo
efc compile examples/hc-valley-battery.json \
  --out docs/assets/hc-valley-battery \
  --min-area
```

Then confirm:

- the Python test suite passes;
- the wheel installs in a clean virtual environment;
- native CI is green when Rust code changes;
- `CHANGELOG.md` describes user-visible changes;
- `docs/PERFORMANCE.md` contains fresh measurements when hot paths change.
