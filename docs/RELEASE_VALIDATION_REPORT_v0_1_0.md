# OSLT GitHub Bootstrap v0.1.0 — release validation report

**Validation date:** 6 August 2026
**Repository target:** `bladerunner1984/oslt-research-engine`
**Lineage:** OSLT Research Engine v2.4 RC1

## Disposition

`LOCAL_BOOTSTRAP_PASS_REMOTE_PUBLICATION_PENDING`

The complete GitHub-ready repository has been implemented and validated locally. Remote repository
creation has not been represented as complete: this execution environment does not have GitHub CLI
and the connected GitHub application does not expose a create-repository operation.

## Verified controls

| Gate | Result |
|---|---:|
| Unit/integration tests | **62 / 62 passed** |
| Exact executable coverage | **85.21%** |
| OSLT preflight | **PASS** |
| Registry validation | **PASS** |
| Hypotheses | **64** |
| Variables | **640** |
| Sources | **65** |
| Methods | **100** |
| Workstreams | **13** |
| Exported JSON contracts | **10** |
| Immutable v2.4 reference files | **86** |
| Configuration/workflow YAML parse | **PASS** |
| Simulated Windows checkout (`core.autocrlf=true`) | **PASS** |
| Direct AI-provider boundary scan | **PASS** |
| Sensitive/raw-data filename and boundary scan | **PASS** |
| Python compileall | **PASS** |
| Wheel build | **PASS** |
| Wheel import smoke test | **PASS** |

## Built distribution

- File: `oslt_research_engine-0.1.0-py3-none-any.whl`
- SHA-256: `21356802204003b92d85b25956c544c7dc77d9b650c278f7e9c06795c390702f`
- Clean repository file count, excluding ignored runtime/test/build products: **259**

A clean simulated Windows checkout preserved the immutable v2.4 bytes, passed OSLT preflight and
passed all 62 tests.

The exact CI packaging path uses setuptools through:

`python -m pip wheel . --no-deps --no-build-isolation -w dist`

## CI architecture

The GitHub workflow separates:

1. validation-scope classification;
2. constitutional/provenance/source guards;
3. pure unit/governance tests;
4. conditional connector/persistence/vertical-slice integration tests;
5. full-suite coverage;
6. distributable build;
7. one fail-closed aggregate named `ci / check`.

The workflow uses a unique aggregate check name so branch protection can require one unambiguous
status context.

## Current implementation boundary

This release proves repository architecture and the public-evidence Pilot 1 execution path. It does
not claim that a live research corpus has been harvested or that any causal proposition has been
validated. Connector tests use mocked responses; live API acquisition remains a controlled future
run with a frozen protocol and manifest.

See `docs/IMPLEMENTATION_STATUS.md` and `docs/ROADMAP.md` for the exact implemented and deferred
scope.
