# Remaining Research Gaps after Kernel v1.1

These are not hidden software defects. They are the evidence and governance work that a real research programme must complete.

## P0 — before participant-level data

1. **Sponsor / chief-investigator accountability and final protocol ownership.**
2. **HRA/REC and other applicable research approvals or determinations.**
3. **Documented UK GDPR/DPA 2018 lawful basis and Article 9 condition** determined by the accountable organisation; the kernel does not make this legal decision.
4. **DPIA, confidentiality route and secure research environment.**
5. **Purpose-specific authority** for private digital data, consultation recordings, genomic data and cross-person/network data.
6. **Participant information/consent or approved alternative route**, including withdrawal/objection handling where applicable.
7. **Final statistical analysis plan and simulation-based sample-size plan.**
8. **Independent ethics, causal-inference, psychometrics, statistics and lived-experience/PPI review.**

## P0 — before causal claims

1. Establish measurement properties and subgroup invariance for the actual instruments used.
2. Validate digital-exposure extraction against platform/raw-source ground truth.
3. Validate consultation NLP/linguistic coding against blinded dual-human coding.
4. Validate academic stance/dependency classifiers against a manually coded reference corpus.
5. Preregister estimands, DAGs, primary endpoints, time zero, adjustment sets, mediators, negative controls and falsifiers.
6. Demonstrate selection/attrition/missingness handling and reverse-causation sensitivity.
7. Complete designated rival analyses with evidence-bound provenance.
8. Replicate material findings in an independent cohort.

## P1 — platform hardening

- Replace local JSONL journal persistence with independently auditable/immutable infrastructure.
- Add signed release artefacts and dependency/SBOM management.
- Add study-specific schema validation for raw imports and feature derivation.
- Add independent code/security review before sensitive-data processing.
- Add controlled model/NLP registry with versioned performance cards.
- Add formal red-team test corpus for stigmatizing, discriminatory and over-causal language.

## Interpretive boundary

The research kernel can govern **how strong a claim may be**. It cannot make a weak study strong, make biased data representative, establish a lawful basis, or transform an association into causation by software rule.
