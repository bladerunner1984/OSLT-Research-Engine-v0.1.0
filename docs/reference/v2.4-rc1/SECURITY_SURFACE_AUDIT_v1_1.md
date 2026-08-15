# Security Surface Audit — OSL Research Kernel v1.1

**Scope:** reference Python research-claim governance package only.  
**Date:** 25 July 2026  
**Status:** static release-surface check; not a penetration test, threat model, DSPT assessment, or production security certification.

## Static release findings

Release pre-flight scans `osl_research/*.py` for dynamic `eval`/`exec`, pickle deserialisation, `shell=True`, `os.system`, direct HTTP/socket clients and developer-local absolute paths.

**Result:** none detected in the product kernel.

The product kernel contains no live network clients, cloud SDK calls, database credentials, model-provider API keys, participant-data connectors or clinical-system adapters.

## Test-only subprocess use

The test and targeted-mutation harnesses invoke local pytest processes using argument-list `subprocess.run`. That code is release QA infrastructure and is not imported by the product kernel.

## Journal boundary

The optional JSONL research journal uses SHA-256 chaining to make alteration detectable. It is **tamper-evident, not immutable**. Production research would still require an appropriately governed environment with access controls, external immutable/auditable storage or signing, trusted identity, retention controls and incident procedures.

## Not established by this audit

This release has not undergone penetration testing, infrastructure threat modelling, secure-research-environment certification, independent code audit, SBOM/vulnerability assessment, or operational incident-response testing.
