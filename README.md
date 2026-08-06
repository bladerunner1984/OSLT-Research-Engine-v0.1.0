# OSLT Research Engine

OSLT is a governed, model-agnostic research platform for testing competing explanations of complex,
multicausal phenomena. It organises evidence, preserves provenance, retrieves counterevidence,
routes questions to specialist kernels, and limits conclusions to what the design and evidence can
support.

## What this repository is

This repository converts the OSLT v2.4 RC1 architecture and registers into an executable research
platform. The first vertical slice is **Pilot 1: Academic Knowledge Production**.

Initial live public-source adapters are provided for OpenAlex, Crossref, PubMed and
ClinicalTrials.gov. They preserve query, retrieval timestamp, upstream identifiers, response hash
and connector version; their outputs remain unclassified evidence until an explicit lane-coding step.

It is deliberately separate from Serverity. Serverity is a production legal platform; OSLT is an
experimental research system. OSLT adopts Serverity's strongest engineering controls without sharing
its data model, credentials, deployment estate, or legal-domain conclusions.

## Constitutional boundaries

OSLT is not:

- a diagnostic or clinical decision system;
- an identity-truth classifier;
- a system that infers individual causes from population associations;
- a machine for proving an investigator's preferred hypothesis;
- a repository for identifiable NHS, education, participant, email, message, or browsing data.

A preferred hypothesis is metadata. Counterevidence, rival explanations, null findings,
methodological criticism, replication evidence, and corrections/retractions are mandatory lanes.

## Architecture

```text
source connectors -> provenance admission -> evidence/dependency graph
                 -> specialist kernels -> contradiction resolver
                 -> certainty/claim gates -> master synthesis
                 -> human review -> released claims -> film evidence dossier
```

Controlled person-level data remain inside the approved TRE/SDE. OSLT exchanges versioned analysis
specifications and disclosure-checked result objects, not unrestricted raw microdata.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
python scripts/preflight.py
pytest
oslt registry-summary
oslt init-db
uvicorn oslt_research.api.app:app --reload
```

## Repository map

- `src/oslt_research/` — executable research kernel and API.
- `registries/` — 64 hypotheses, 640 variables, 65 sources, 100 methods, 13 workstreams.
- `config/` — scientific constitution, model boundary, data-boundary policy.
- `schemas/` — versioned JSON contracts crossing kernel and environment boundaries.
- `studies/pilot_01_academic_knowledge/` — first reproducible study vertical.
- `film/` — documentary-ready claim/scene dossier outputs, downstream of released evidence.
- `docs/reference/v2.4-rc1/` — immutable lineage package.
- `data/` — policy-only placeholders; raw/restricted data are gitignored.

## Security and scientific integrity

The default model gateway is disabled. No model provider SDK may be called outside the single gateway
module. CI fails closed on registry drift, sensitive-file risks, broken lineage hashes, dropped
continuity state, direct model-provider imports, and test failures.

See `GOVERNANCE.md`, `SECURITY.md`, and `docs/architecture/SERVERITY_LESSONS_ADOPTED.md`.

## Current implementation status

This bootstrap is a governed executable foundation, not a completed study or validated causal
system. See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md),
[`docs/ROADMAP.md`](docs/ROADMAP.md), and the
[`GitHub bootstrap runbook`](docs/runbooks/GITHUB_BOOTSTRAP.md).
