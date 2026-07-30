# Contributing

Thank you for helping turn this proof of concept into a community project.

## Good first contributions

- add tests for an existing stage;
- improve diagnostics or documentation;
- contribute a legally redistributable region pack;
- add a small placement or routing heuristic behind the current data model;
- report a reproducible bad layout.

For a larger feature, open a proposal issue first. The project has no promised
response time, so keep changes independently useful and easy to review.

## Development

```bash
python -m venv .venv
# activate the environment for your shell
python -m pip install -e .
python -m unittest discover -s tests -v
efc compile examples/control-core.json --out build/demo
```

See [quality gates](docs/QUALITY.md) for the full Python and Rust check list.

Pull requests should:

- preserve dependency-free operation unless a dependency is optional;
- include tests for behavior changes;
- keep output deterministic;
- avoid unrelated formatting changes;
- update schemas and documentation together;
- use [ADRs](docs/adr) for architecture, dependency or long-term performance
  decisions;
- not contain extracted game assets or unverifiable official claims.

## Region-pack contributions

Run `efc validate-pack path/to/region.json` and include the data source and game
version in the pull request. Fictional packs must say so in their name and
documentation.

## Commit messages

Short imperative messages are preferred, for example:

```text
Add congestion penalty to A* router
Document region-pack versioning
```

By contributing, you agree that your contribution is licensed under the MIT
License.
