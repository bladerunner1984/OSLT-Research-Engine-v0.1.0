# OSLT Global-100 Executable Assurance Overlay

**Result: 25/25 functional probes passed.**

This overlay complements the 100-item architecture audit. It tests selected load-bearing controls for executable fail-closed behaviour; it does not validate any substantive hypothesis.

- PASS A-01 - Default workflow graph validates: VALID
- PASS A-02 - Retrieval and analyst fan-out exist: {'retrieval': ('retrieve_support', 'retrieve_contradict', 'retrieve_rival', 'retrieve_null', 'retrieve_bias', 'retrieve_replication', 'retrieve_correction'), 'analysts': ('analyse_primary', 'analyse_rival', 'analyse_methods', 'analyse_source')}
- PASS A-03 - Model agreement cannot create evidential weight: FAIL_CLOSED
- PASS A-04 - Sensitive-data model policy fails closed: ('PRIMARY_MODEL_NOT_APPROVED_FOR_SENSITIVE_DATA', 'PRIMARY_MODEL_REQUIRES_DATA_RETENTION')
- PASS A-05 - Model qualification detects critical weakness: ('MODEL_BENCHMARK_CRITICAL_FAIL:CALIBRATION:0.300',)
- PASS A-06 - Context mismatch is not mislabelled substantive contradiction: TEMPORAL_MISMATCH
- PASS A-07 - Aligned opposing findings require contradiction adjudication: SUBSTANTIVE_CONTRADICTION
- PASS A-08 - Unfrozen causal specification is not release-ready: ('CAUSAL_SPEC_NOT_PREREGISTERED', 'CAUSAL_SPEC_NOT_FROZEN')
- PASS A-09 - Evidence completeness recognises saturated balanced discovery: ()
- PASS A-10 - Evidence completeness rejects missing counterevidence/saturation: ('EVIDENCE_LANE_EMPTY:CONTRADICT', 'INSUFFICIENT_INDEPENDENT_FAMILIES:CONTRADICT', 'EVIDENCE_LANE_EMPTY:RIVAL', 'INSUFFICIENT_INDEPENDENT_FAMILIES:RIVAL', 'DISCOVERY_SATURATION_NOT_REACHED')
- PASS A-11 - High-impact contradictory output escalates to multidisciplinary review: MULTIDISCIPLINARY_PANEL
- PASS A-12 - Execution budget detects runaway model calls: ('MODEL_CALL_BUDGET_EXCEEDED',)
- PASS A-13 - Final release readiness fails closed: ('RELEASE_GATE_FAILED:B',)
- PASS A-14 - Retrieved prompt-injection content is detected and isolated: ('ignore\\s+(all\\s+)?previous\\s+instructions', 'system\\s*prompt')
- PASS A-15 - All inherited research controls are reachable: controls=16
- PASS A-16 - 640 variable-method mappings retained: rows=640
- PASS A-17 - 640 variable-source mappings retained: rows=640
- PASS A-18 - 100 analytical method families retained: rows=100
- PASS A-19 - 65 source families retained: rows=65
- PASS A-20 - Global-100 source registry remains exactly 100 criteria: criteria=100
- PASS A-21 - Controlled-data raw export fails closed: ('TRE_RAW_EXPORT_PROHIBITED',)
- PASS A-22 - Participant harvest requires explicit consent reference: ('PVT:PARTICIPANT_CONSENT_REFERENCE_REQUIRED',)
- PASS A-23 - Insufficient sample information lowers inference tier: EXPLORATORY_OR_DESCRIPTIVE:('SMALL_COHORT', 'LOW_EVENTS_PER_EFFECTIVE_PARAMETER', 'LIMITED_TEMPORAL_DEPTH', 'NO_EXTERNAL_REPLICATION')
- PASS A-24 - Competing-model registry contains 64 falsifiable propositions: rows=64,families=5,falsifiers=True
- PASS A-25 - 640-variable harvest dictionary does not pretend field availability: rows=640,all_unverified=True
