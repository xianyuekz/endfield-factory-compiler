# Changelog

All notable changes to this project are documented here.

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
