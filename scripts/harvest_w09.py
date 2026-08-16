"""Live W09 harvest: clinical guidelines, professional bodies and NHS policy.

W09 is required by 24 of the 64 propositions and was empty. Unlike the other empty
workstreams its material is entirely public, so the gap was engineering, not access.

The product is a set of DATED policy anchor points. A document with no genuine
first-publication date is retained and reported as UNDATED rather than anchored on a
revision timestamp - see the module docstring of ``connectors/clinical_guidance.py``.

Usage:  .venv/Scripts/python.exe scripts/harvest_w09.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import httpx

sys.path.insert(0, "src")

from oslt_research.connectors.clinical_guidance import (  # noqa: E402
    DECLINED_SOURCES,
    NHS_ENGLAND_COLLECTIONS,
    PROFESSIONAL_BODIES,
    GovUkPolicyDocumentConnector,
    GuidanceHarvest,
    NhsEnglandPolicyConnector,
    NiceGuidanceConnector,
    ProfessionalBodyConnector,
    ThrottledClient,
)

OUT = Path("data/w09_clinical_guidance.json")

NICE_QUERIES = [
    "gender",
    "gender dysphoria",
    "transgender",
    "puberty",
    "depression children young people",
    "autism",
    "eating disorder",
    "self-harm",
    "mental wellbeing young people",
    "referral to specialist services",
]

NHS_ENGLAND_SEARCHES = [
    "gender dysphoria service specification",
    "gender incongruence children young people",
    "Cass review implementation",
    "specialised commissioning gender",
    "puberty suppressing hormones",
]

GOVUK_QUERIES = [
    "Cass review gender identity services",
    "gender identity services children",
    "puberty blockers",
    "gender questioning children schools guidance",
    "gender recognition",
]

BODY_KEYWORDS = ("gender", "cass", "transgender", "puberty", "gender-questioning")

#: Free-text search on GOV.UK and NHS England is recall-oriented: both return their full
#: page of results whether or not the terms appear in the document. A run without this
#: filter returned HMRC sign-in pages under "Cass review". Relevance is therefore decided
#: on the title, here in the script rather than in the connector, so the connector stays a
#: general retrieval tool and the topic definition stays visible and auditable.
TOPIC_TERMS = (
    "gender", "transgender", "trans ", "cass", "puberty", "gender identity",
    "gender dysphoria", "gender incongruence", "sex and gender", "gender questioning",
    "gender recognition",
)


def log(message: str) -> None:
    print(message, flush=True)


def only_on_topic(harvest: GuidanceHarvest) -> GuidanceHarvest:
    """Keep documents whose title carries a topic term; count the rest as off-topic.

    Applied only to free-text search results. Results reached through NHS England's own
    ``gender-identity`` category are never filtered: a taxonomy assigned by the publisher
    is a better definition of relevance than a keyword list written by the analyst.
    """

    kept = [
        doc for doc in harvest.documents
        if any(term in doc.title.lower() for term in TOPIC_TERMS)
    ]
    skips = dict(harvest.skip_reasons)
    dropped = len(harvest.documents) - len(kept)
    if dropped:
        skips["OFF_TOPIC_SEARCH_RESULT"] = skips.get("OFF_TOPIC_SEARCH_RESULT", 0) + dropped
    return GuidanceHarvest(
        documents=kept, records_seen=harvest.records_seen, skip_reasons=skips
    )


def run() -> GuidanceHarvest:
    shared = ThrottledClient(httpx.Client(timeout=90.0), enabled=True)
    total = GuidanceHarvest(declined=dict(DECLINED_SOURCES))

    # ---- NICE -------------------------------------------------------------------
    nice = NiceGuidanceConnector(client=shared)
    for query in NICE_QUERIES:
        try:
            result = nice.search(query, page_size=50)
        except httpx.HTTPError as error:
            # A failed request is not an absence.
            log(f"NICE   {query!r:46} REQUEST FAILED {type(error).__name__}")
            continue
        total = total.merged_with(result)
        log(
            f"NICE   {query!r:46} {len(result.documents):>3} docs "
            f"({len(result.dated())} dated)"
        )

    # ---- NHS England ------------------------------------------------------------
    nhse = NhsEnglandPolicyConnector(client=shared)
    try:
        category = nhse.category_id("gender-identity")
    except httpx.HTTPError as error:
        category = None
        log(f"NHSE   category lookup FAILED {type(error).__name__}")
    log(f"NHSE   gender-identity category id = {category}")

    for collection in NHS_ENGLAND_COLLECTIONS:
        if category is not None:
            try:
                result = nhse.collection(collection, category=category, per_page=100)
            except httpx.HTTPError as error:
                log(f"NHSE   {collection:<12} category REQUEST FAILED {type(error).__name__}")
            else:
                total = total.merged_with(result)
                log(
                    f"NHSE   {collection:<12} category      "
                    f"{len(result.documents):>3} docs ({len(result.dated())} dated)"
                )
        for search in NHS_ENGLAND_SEARCHES:
            try:
                result = nhse.collection(collection, search=search, per_page=50)
            except httpx.HTTPError as error:
                log(f"NHSE   {collection:<12} {search!r:46} FAILED {type(error).__name__}")
                continue
            result = only_on_topic(result)
            total = total.merged_with(result)
            log(
                f"NHSE   {collection:<12} {search[:40]!r:44} "
                f"{len(result.documents):>3} docs"
            )

    # ---- GOV.UK -----------------------------------------------------------------
    govuk = GovUkPolicyDocumentConnector(client=shared)
    for query in GOVUK_QUERIES:
        try:
            result = govuk.search(query, count=30)
        except httpx.HTTPError as error:
            log(f"GOVUK  {query!r:46} REQUEST FAILED {type(error).__name__}")
            continue
        result = only_on_topic(result)
        total = total.merged_with(result)
        log(
            f"GOVUK  {query!r:46} {len(result.documents):>3} docs "
            f"({len(result.dated())} dated)"
        )

    # ---- professional bodies ----------------------------------------------------
    bodies = ProfessionalBodyConnector(client=shared)
    for key, body in PROFESSIONAL_BODIES.items():
        try:
            result = bodies.harvest(body, keywords=BODY_KEYWORDS, limit=40)
        except httpx.HTTPError as error:
            log(f"BODY   {key:<8} REQUEST FAILED {type(error).__name__}")
            continue
        total = total.merged_with(result)
        log(
            f"BODY   {key:<8} {len(result.documents):>3} docs "
            f"({len(result.dated())} dated) of {result.records_seen} sitemap matches"
        )

    shared.close()
    return total


def main() -> int:
    harvest = run()
    dated = harvest.dated()
    undated = harvest.undated()

    payload = {
        "workstream": "W09",
        "source_id": "DS078",
        "documents_total": len(harvest.documents),
        "documents_with_genuine_anchor_date": len(dated),
        "documents_undated": len(undated),
        "withdrawn_or_superseded": sum(1 for doc in harvest.documents if doc.withdrawn),
        "distinct_anchor_dates": len(harvest.anchor_dates()),
        "records_seen": harvest.records_seen,
        "skip_reasons": dict(sorted(harvest.skip_reasons.items())),
        "declined_sources": harvest.declined,
        "anchor_dates": [d.isoformat() for d in harvest.anchor_dates()],
        "documents": [
            {
                **asdict(doc),
                "published_on": doc.published_on.isoformat() if doc.published_on else None,
                "last_updated": doc.last_updated.isoformat() if doc.last_updated else None,
            }
            for doc in sorted(
                harvest.documents,
                key=lambda d: (d.published_on is None, d.published_on or "", d.source),
            )
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    log("")
    log(f"=== {len(harvest.documents)} documents; {len(dated)} carry a genuine anchor "
        f"date, {len(undated)} are UNDATED ===")
    log(f"skip reasons: {payload['skip_reasons']}")
    log(f"written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
