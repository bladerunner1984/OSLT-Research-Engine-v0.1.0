"""Put this project's own published claims through the claim-release gate.

`governance/claim_release.py` had never executed. It is the control that stops a
`SIMULATION_ONLY` or descriptive result being narrated in language that implies an
established finding, and this project has produced exactly the material that invites that:
referral comparators, a feasibility census, an overturned coupling disposition.

So the first thing it is pointed at is the project's own prose. Every claim below is a
verbatim quotation from a committed document, with the source of its tier recorded. Where
a document declares no tier, that is refused as `CLAIM_TIER_NOT_DECLARED` rather than
having a tier assumed for it - an assumed tier would decide the verdict, which makes the
verdict about the assumption.

Usage::

    python scripts/assess_claim_release.py            # assess and print, write nothing
    python scripts/assess_claim_release.py --apply    # seal a run and persist every verdict
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from oslt_research.domain.enums import AuthorityLevel, ClaimTier, EvidenceLane
from oslt_research.governance.authority import NOT_PREREGISTERED
from oslt_research.governance.claim_release import (
    ClaimSubmission,
    assess_documented_claim,
    check_wording,
)
from oslt_research.persistence.sqlite import SQLiteStore
from oslt_research.pipelines.run_manifest import build_run_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

#: The four documents whose claims are under assessment, and where each one's tier comes
#: from. `None` means the document states no tier anywhere - checked by grep, not assumed.
DOCUMENTS: tuple[tuple[str, ClaimTier | None, str], ...] = (
    (
        "docs/REFERRAL_BASELINE.md",
        ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        'declared in the document header: "**Status:** descriptive, no mechanism calibrated."',
    ),
    (
        "docs/CENSUS_2021_GENDER_IDENTITY.md",
        None,
        "no tier stated anywhere in the document",
    ),
    (
        "docs/MX09_FALSIFICATION_RUN.md",
        None,
        (
            "no tier stated for the document itself; it quotes MD15 as capped at "
            "LIMITED_CAUSAL_EVIDENCE by the registry, which is a cap on a proposition, "
            "not a declaration of the tier this write-up claims at"
        ),
    ),
    (
        "docs/COUNTEREVIDENCE_RUN.md",
        None,
        "no tier stated anywhere in the document",
    ),
)

#: Tier used only for the advisory scan of tier-undeclared documents. It is the *lowest*
#: tier, which is the strictest wording regime, so an advisory pass is genuinely
#: informative and an advisory failure is not an artefact of a lenient choice.
ADVISORY_TIER = ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY

#: Individual headline sentences, quoted verbatim, assessed separately from the whole-file
#: scan so a failure can be attributed to a sentence rather than to a document.
HEADLINE_CLAIMS: tuple[tuple[str, str, str], ...] = (
    (
        "REFERRAL-BASELINE-HEADLINE",
        "docs/REFERRAL_BASELINE.md",
        "Referral volumes into a specialist clinical pathway rose roughly threefold in "
        "fifteen years while the proportion of referrals that found the condition nearly "
        "halved, monotonically.",
    ),
    (
        "REFERRAL-BASELINE-THRESHOLD",
        "docs/REFERRAL_BASELINE.md",
        "That is the arithmetic signature of a lowered referral threshold: more people "
        "referred, a smaller share of them having the thing referred for.",
    ),
    (
        "REFERRAL-BASELINE-NICE",
        "docs/REFERRAL_BASELINE.md",
        "This is not a claim about cancer policy, and it is not in dispute; it is the "
        "intended and documented effect of successive NICE guideline revisions and "
        "awareness campaigns.",
    ),
    (
        "REFERRAL-BASELINE-BALLOT",
        "docs/REFERRAL_BASELINE.md",
        "ASCERTAINMENT_SERVICE predicts referral growth accompanied by falling yield or "
        "threshold-consistent shifts, and predicts it should appear across domains.",
    ),
    (
        "REFERRAL-BASELINE-COMPARATOR",
        "docs/REFERRAL_BASELINE.md",
        "The same conjunction is present in general secondary mental health referrals "
        "over the same period, in a service with no relation to gender identity.",
    ),
)

#: Claims that DO have a persisted KernelResult behind them, so the full nine-gate
#: assess_release can run rather than stopping at NO_PERSISTED_RESULT_FOR_CLAIM.
RESULT_BACKED = ("KR-P1-20260815123808-MD11", "KR-P1-20260815123808-MX14")


def lanes_searched(database: Path, proposition_id: str) -> frozenset[EvidenceLane]:
    """Lanes with a completed search for one proposition, read from the store.

    Only `SEARCHED_COMPLETE` counts. A partial sweep is not a search for this purpose: the
    part that failed is exactly where the missing records would have been.
    """

    if not database.exists():
        return frozenset()
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT lane, status, proposition_ids FROM lane_search_records"
        ).fetchall()
    except sqlite3.OperationalError:
        return frozenset()
    finally:
        connection.close()
    found = set()
    for lane, status, proposition_ids in rows:
        if status == "SEARCHED_COMPLETE" and proposition_id in (proposition_ids or ""):
            found.add(EvidenceLane(lane))
    return frozenset(found)


def sentence_context(text: str, phrase: str) -> list[str]:
    """Every line containing a prohibited phrase, so a hit can be read in situ."""

    return [
        f"line {index}: {line.strip()}"
        for index, line in enumerate(text.splitlines(), 1)
        if re.search(rf"\b{re.escape(phrase)}", line, re.I)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(REPOSITORY_ROOT / "runtime" / "oslt.db"))
    parser.add_argument("--output", default=str(REPOSITORY_ROOT / "data" / "claim_release.json"))
    parser.add_argument("--apply", action="store_true", help="seal a run and persist verdicts")
    arguments = parser.parse_args()

    database = Path(arguments.database)
    store = SQLiteStore(database)
    assessed_at = datetime.now(timezone.utc).isoformat()
    run_id = f"REL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    submissions: list[ClaimSubmission] = []
    contexts: dict[str, dict[str, list[str]]] = {}

    for relative, tier, tier_source in DOCUMENTS:
        text = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
        submissions.append(
            ClaimSubmission(
                claim_ref=f"DOC:{relative}",
                source_document=relative,
                wording=text,
                declared_tier=tier,
                tier_source=tier_source,
            )
        )
        scan_tier = tier or ADVISORY_TIER
        contexts[f"DOC:{relative}"] = {
            phrase: sentence_context(text, phrase)
            for phrase in check_wording(text, scan_tier).prohibited_hits
        }

    referral_tier, referral_source = DOCUMENTS[0][1], DOCUMENTS[0][2]
    for claim_ref, relative, wording in HEADLINE_CLAIMS:
        submissions.append(
            ClaimSubmission(
                claim_ref=claim_ref,
                source_document=relative,
                wording=wording,
                declared_tier=referral_tier,
                tier_source=referral_source,
            )
        )

    results = {
        result.result_id: result
        for run in {"P1-20260815123808"}
        for result in store.list_kernel_results(run)
    }
    evidence_by_id = {item.evidence_id: item for item in store.list_evidence()}

    assessments = []
    for submission in submissions:
        assessments.append(assess_documented_claim(submission))

    for result_id in RESULT_BACKED:
        result = results.get(result_id)
        if result is None:
            continue
        submission = ClaimSubmission(
            claim_ref=f"RESULT:{result_id}",
            source_document="docs/COUNTEREVIDENCE_RUN.md",
            wording=result.narrative,
            declared_tier=result.claim_tier,
            tier_source=f"KernelResult.claim_tier persisted on {result_id}",
            result_id=result_id,
            lanes_searched=lanes_searched(database, result.proposition_id),
        )
        assessments.append(
            assess_documented_claim(
                submission,
                result=result,
                evidence=[
                    evidence_by_id[item]
                    for item in result.evidence_ids
                    if item in evidence_by_id
                ],
                human_review=None,
            )
        )

    report = {
        "assessed_at": assessed_at,
        "run_id": run_id if arguments.apply else "NOT_PERSISTED",
        "assessments": [item.as_record() for item in assessments],
        "prohibited_phrase_context": contexts,
        "released": [item.claim_ref for item in assessments if item.released],
        "refused": [item.claim_ref for item in assessments if not item.released],
    }

    Path(arguments.output).parent.mkdir(parents=True, exist_ok=True)
    Path(arguments.output).write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )

    for item in assessments:
        tier = item.declared_tier.value if item.declared_tier else "UNDECLARED"
        print(f"{'RELEASED' if item.released else 'REFUSED '} {item.claim_ref} [{tier}]")
        for failure in item.failures:
            print(f"    - {failure}")
        if item.advisory_prohibited_hits:
            print(f"    ~ advisory scan hits: {item.advisory_prohibited_hits}")

    if arguments.apply:
        store.initialise()
        manifest = build_run_manifest(
            run_id=run_id,
            objective="Claim release assessment over this project's published documents",
            proposition_ids=sorted({r.proposition_id for r in results.values()}),
            connectors=[],
            preregistration_ref=NOT_PREREGISTERED,
            root=REPOSITORY_ROOT,
        )
        store.save_run(manifest, authority=AuthorityLevel.A3_VERIFIED_EVIDENCE_COMPUTATION)
        for item in assessments:
            store.save_claim_assessment(item, run_id=run_id, assessed_at=assessed_at)
        print(f"persisted {len(assessments)} verdicts under run {run_id}")
    else:
        print("dry run: nothing written to the store (pass --apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
