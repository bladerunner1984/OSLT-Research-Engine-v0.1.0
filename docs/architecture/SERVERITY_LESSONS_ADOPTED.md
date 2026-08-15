# Serverity lessons adopted by OSLT

OSLT is a separate repository and data estate. It adopts cross-cutting engineering controls from
Serverity but not Serverity's legal matter schema, tenancy model, production credentials, or legal
rules on ultimate-issue probability.

## Adopted

1. **One controlled AI boundary.** Direct provider calls outside the gateway fail static checks.
2. **Fail-closed aggregate CI.** Branch protection should require the stable `ci / check` context.
3. **Source status separate from confidence.** VERIFIED, ASSERTED and UNVERIFIED answer a different
   question from evidential certainty.
4. **Evidence lanes.** SUPPORT, CONTRADICT, RIVAL, NULL, BIAS_CRITIQUE, REPLICATION and
   CORRECTION_RETRACTION must be searched explicitly.
5. **Authority precedence.** Model proposals cannot overwrite human decisions or the constitution.
6. **Continuity preflight.** Open issues, contradictions, rejected paths and state versions cannot be
   silently dropped between agents, calls or pipeline stages.
7. **Mutation-oriented guards.** Controls must fail when their protected invariant is deliberately
   removed, not merely exist as prose.
8. **Exact provenance.** Repository SHA, configuration hashes, data/evidence hashes and source
   versions are bound into every released run.
9. **No fake completeness.** A missing lane or unverified field is reported as missing, not inferred
   from absence.
10. **Separate pure and stateful tests.** Unit and registry guards run independently of persistence and
    connector integration tests.

## Adapted for research

- Serverity's document/matter authority becomes OSLT's evidence and research-decision authority.
- Legal counter-authority becomes scientific contradiction, rival, null and correction evidence.
- Matter context overlays become domain/workstream and estimand-specific analysis routing.
- Legal audit trails become tamper-evident research computation journals and run manifests.

## Explicitly not copied

- Legal-client tenancy and conflict-wall semantics.
- Legal win-probability or ultimate-issue modelling constraints.
- The Next.js/Prisma product architecture as the research compute core.
- Production secrets, AWS resources, databases or deployment coupling.
