# Changelog

All notable changes to this project are documented here.

## 0.4.4

- add CLI resource profiles (`low-power`, `balanced`, `quality`) for
  low-end-friendly floorplan search budgets;
- expose the selected execution profile and floorplan candidate budget in JSON
  and Markdown reports;
- document the native-first architecture for future placement, routing, DRC and
  floorplan hot loops;
- add regression coverage for profile-driven minimum-area compilation.

## 0.4.3

- add `efc compile --min-area` for deterministic minimum-area floorplan search;
- add bounding-box dimensions, area and utilization to JSON, SVG and Markdown
  reports;
- make the router and DRC enforce aggregate same-item route-tile capacity on
  logistics trunk tiles;
- regenerate the HC Valley Battery artifact as a 41 x 17 routed floorplan;
- add floorplanning documentation and regression coverage for the compact HC
  Valley Battery acceptance target.

## 0.4.2

- add a Valley IV community-data research region pack;
- add an HC Valley Battery project that compiles into a clean placement and
  routed physical plan;
- add checked-in HC Valley Battery SVG/JSON/Markdown artifacts for easy
  repository inspection;
- document the current boundary between generated physical plans and official
  in-game blueprint-code export;
- add regression coverage for the HC Valley Battery recipe chain.

## 0.4.1

- apply Rust formatting required by the native CI quality gate.

## 0.4.0

- add a standalone Rust `native/route_core` crate for the future routing hot
  loop;
- add a root Cargo workspace, Rust toolchain file, ADR and quality-gate docs;
- implement deterministic native A* over compact integer cell/state arrays and
  per-cell occupancy bitsets;
- add native route-core tests to CI while keeping the Python package
  dependency-free.

## 0.3.1

- replace tuple/dictionary-heavy A* search state with compact integer-indexed
  arrays;
- rename the reference router telemetry to `serial-compact-grid-astar`;
- document the native-first performance direction for future hot-path work.

## 0.3.0

- add a shared `ExecutionOptions` contract for job budgets, deterministic seeds
  and soft routing time limits;
- extract a replaceable `RouterBackend` protocol and serial reference backend;
- add routing telemetry for effective jobs, A* state expansion, heap pressure,
  path length, elapsed/CPU time, observed core equivalents and timeouts;
- expose execution and routing statistics in JSON and Markdown reports;
- add a deterministic scaling benchmark and performance architecture guide;
- preserve the legacy `route_logistics` list-returning API.

## 0.2.1

- split consumer demand across multiple producer devices without overloading
  any individual machine;
- add device-level producer capacity and consumer input-rate DRC;
- add regression tests for physical flow conservation.

## 0.2.0

- add project-level power, device-count and route-tile constraints;
- add physical-design metrics to `plan.json` and SVG output;
- generate a deterministic Markdown compilation report;
- add congestion, crossing and bend costs to the A* router;
- add JSON Schema files for projects and region packs;
- add `efc validate-project`;
- expand regression coverage and normalize repository line endings.

## 0.1.0

- initial recipe synthesis, placement, routing, DRC and SVG prototype;
- add a fictional demo region pack and control-core example;
- add bilingual documentation and community contribution files.
