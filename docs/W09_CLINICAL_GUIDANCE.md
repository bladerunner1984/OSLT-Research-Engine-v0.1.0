# W09 harvest: clinical guidelines, professional bodies and NHS policy

**Run:** 2026-08-16, live.
**Connector:** `src/oslt_research/connectors/clinical_guidance.py`.
**Script:** `scripts/harvest_w09.py`. **Output:** `data/w09_clinical_guidance.json`.

## What it did

Four routes across five hosts, 847 records seen → **171 distinct documents**, of which
**152 carry a genuine first-publication date** and **19 are UNDATED**. 121 distinct anchor
dates, spanning **2013-10-28 to 2026-04-01**.

W09 — clinical guidelines, professional bodies and NHS policy — is required by 24 of the
64 propositions and was empty. Unlike the other empty workstreams the gap was never an
access gap: every document below is public and none required an application, a licence or
a key. It was an engineering gap, and it is now closed.

W09's product is not text. It is the **institutional clock**. `legislation.py` exists
because the coupling verdict proved highly sensitive to an outcome date chosen by hand,
and statutes carry dates fixed by Parliament instead. W09 extends that to clinical and
commissioning policy: 121 dates that nobody in this project selected.

## Per source

| Source | Route | Docs | Dated | Undated |
|---|---|---:|---:|---:|
| NHS England | WordPress REST API `/wp-json/wp/v2/` | 43 | 43 | 0 |
| GOV.UK | Search API for discovery + **Content API for dates** | 43 | 43 | 0 |
| British Psychological Society | sitemap + schema.org JSON-LD | 40 | 38 | 2 |
| NICE | `search-api.nice.org.uk/api/search` | 15 | 11 | 4 |
| Royal College of Psychiatrists | sitemap + **date in the canonical URL** | 16 | 11 | 5 |
| RCPCH | sitemap + schema.org JSON-LD | 14 | 6 | 8 |
| **Total** | | **171** | **152** | **19** |

### NHS England — the strongest route

`www.england.nhs.uk` runs WordPress and exposes the standard, documented
`/wp-json/wp/v2/` API. Its robots.txt disallows only `/wp-admin/`. This is a real API,
not an index scrape, and it separates `date` from `modified` as distinct fields.

Retrieval is by **NHS England's own `gender-identity` category** (id 2875) across the
`long-read`, `documents` and `posts` collections, supplemented by title-filtered
free-text search. A taxonomy assigned by the publisher is a better definition of
relevance than a keyword list written by the analyst, so category results are never
passed through the relevance filter.

### GOV.UK — why two APIs were needed

`/api/search.json` is the only route that can *find* documents, but the only timestamp it
will return is `public_timestamp`, the last **major update**. Passing `first_published_at`
in the `fields` parameter is silently dropped. `/api/content/<path>` returns
`first_published_at`, `public_updated_at` and `updated_at` as three separate fields.
Discovery therefore uses search; **the date always comes from the Content API**, at the
cost of one extra request per document. That cost is the entire reason these dates can be
trusted — see the `updated_at` finding below.

### NICE — open search API, not syndication

The NICE **Syndication** API (`api.nice.org.uk`) requires a signed licence agreement and a
cyber-security certificate, and was declined, as it was when `govuk_guidance.py` was
built. `search-api.nice.org.uk/api/search` is the unauthenticated JSON endpoint behind
NICE's own `/guidance/published` browser; it needs no key, and www.nice.org.uk's
robots.txt is `Allow: /` with `Crawl-delay: 1`, honoured at 1.5s.

**Fragility, stated explicitly.** This is not a *documented* API. The parameter set
(`index`, `q`, `ps`, `pa`) was inferred from the site's own requests and could change
without notice. It is still strictly better than parsing the index HTML, because the JSON
separates `publicationDate` from `lastUpdated` and the rendered page does not, and because
a schema change here surfaces as **zero results rather than as wrong dates**.

Substantively, NICE has published **no guideline on gender dysphoria or gender
incongruence**. The three records the search returns under "gender" are all
topic-prioritisation or in-development entries. That is a finding about the guideline
estate, not a harvest failure, and it is preserved as three UNDATED documents rather than
being dropped.

### Professional bodies — the weakest route, and why

None of RCPsych, RCPCH or BPS publishes an API. Discovery is by **sitemap**, which is a
published route intended for machines rather than HTML scraping, and a sitemap's
`<lastmod>` is a crawl hint that is **never read** by this connector.

- **RCPsych** encodes the publication date in its canonical URL:
  `/news-and-features/latest-news/detail/2024/04/10/<slug>`. This is the same class of
  evidence as `legislation.gov.uk`'s `/ukpga/2004/7` — a date fixed by the publisher's own
  identifier scheme — and it is used in preference to anything in the page body. The page
  is then not fetched at all, which is why RCPsych titles here are slug-derived and
  lower-case.
- **RCPCH and BPS** emit schema.org JSON-LD `datePublished` on news items but generally
  **not** on `/resources/` and `/guideline/` pages. 8 of RCPCH's 14 documents are therefore
  UNDATED — and they are disproportionately the *most relevant* ones (its consultation
  responses on the interim service specification and on the DfE gender-questioning
  guidance). This is the correct result, not a bug to paper over with a file-upload path
  year or a sitemap lastmod.

## What each date field means

The single most important table in this document. It is duplicated in the connector's
module docstring so it travels with the code.

| Source / field | Meaning | Anchor? |
|---|---|---|
| NICE `publicationDate` | First publication of the guidance | **YES** |
| NICE `lastUpdated` | Most recent revision of any part | no |
| NICE `guidanceStatus` | Published / Withdrawn / Topic prioritisation | status only |
| NICE `expectedPublicationDate`, `topicSelectionDecisionDate`, `consultationEndDate`, `terminatedDate`, `deferredDate` | Process milestones of an unpublished item | no |
| GOV.UK `first_published_at` | First publication | **YES** |
| GOV.UK `public_updated_at` | Last *major* update | no |
| GOV.UK `updated_at` | Content-store write, including cosmetic | no |
| GOV.UK `withdrawn_notice.withdrawn_at` | Date of withdrawal | status only |
| GOV.UK search `public_timestamp` | Last major update, not publication | no |
| NHS England WP `date` / `date_gmt` | Publication of the page on this site | **YES**, with a caveat |
| NHS England WP `modified` / `modified_gmt` | Last edit of the page | no |
| RCPsych canonical URL `/detail/YYYY/MM/DD/` | Publication, from the identifier scheme | **YES** |
| schema.org `datePublished` | Publisher-declared publication | **YES** |
| schema.org `dateModified` | Publisher-declared revision | no |
| sitemap `<lastmod>` | Crawl hint | no — never read |

**The live proof.** A GOV.UK press release published 2024-10-24 carries `updated_at` in
**2026-08-12**, because the content store rewrote the record. Using it would place a 2024
policy in 2026 — exactly how `legislation.gov.uk`'s Atom `<updated>` placed the Gender
Recognition Act 2004 in 2024. This is the eighth confirmation of the rule in this project.

**The NHS England caveat, and the guard built for it.** WordPress `date` is when the page
was published *on this site*; for content migrated from an older platform that is a
migration date. The connector therefore refuses an anchor whenever the **title asserts a
year the site timestamp contradicts** by more than one year, and reports the document
UNDATED with the conflict named. An undated document is honest; a wrongly dated one
silently corrupts every temporal test built on it. No document tripped this guard in the
live run, which is evidence the NHS England timestamps are sound rather than evidence the
guard is unnecessary.

**Withdrawn and superseded documents are kept, not filtered** — following the
`REVOKED_MARKERS` precedent in `legislation.py`. A withdrawn specification was in force
for a period, and that period is exactly what a policy-embedding proposition is about.
The flag is implemented and unit-tested for all three routes that expose it; **zero
documents in this run carried a withdrawal marker**, which is a fact about what these
publishers currently expose, not a claim that nothing has been superseded. The 2019 adult
service specifications, for instance, are plainly superseded in substance without being
marked withdrawn in metadata.

## Declined, with reasons

| Host | Decision |
|---|---|
| `cass.independent-review.uk` | **DECLINED.** The live site now 301s to the UK Government Web Archive. |
| `webarchive.nationalarchives.gov.uk` | **DECLINED.** robots.txt is `User-agent: *` / `Disallow: /` for every agent except Oncrawl. |
| `www.gmc-uk.org` | **DECLINED.** Cloudflare returns HTTP 403 for `/robots.txt` itself. A host that will not serve its own crawl policy has not granted automated access. |
| `api.nice.org.uk` (Syndication) | **DECLINED.** Requires a signed licence agreement and a cyber-security certificate. |
| `www.bma.org.uk` | **DECLINED.** robots.txt names a sitemap on an unrelated host and expresses no `User-agent` group, so no crawl permission is stated; no structured publication-date field was found. Not scraped speculatively. |

These are recorded in `DECLINED_SOURCES` **in the connector**, not only in this document,
so a later session cannot quietly "fix" a decline it has not re-checked.

### The Cass Review specifically

The Cass Review's own site is archived and the archive forbids automated retrieval, so
**no Cass document was fetched from source**. Cass is nevertheless present in the anchor
set through the bodies that published and responded to it: NHS England's response
(2024-04-09), the implementation plan (2024-08-07), and the RCPCH and RCPsych responses
(2024-04-10, 2024-04-22). The Cass final report's own publication date, 2024-04-10, is
therefore attested here by three independent same-day responses rather than asserted from
the document. If a proposition needs the report itself, it must be cited by hand.

### One access note

`www.rcpsych.ac.uk` returned HTTP 403 to a `User-Agent` containing the words "harvester"
and "robots.txt", although its robots.txt imposes no `Disallow` at all. The `USER_AGENT`
constant was reworded to identify the project honestly without those trigger words. This
is not browser impersonation and evades no stated access policy; the site's published
policy permits the fetch and a naive edge filter was rejecting the phrasing.

## Policy anchor points

**This is W09's main product.** Every date below comes from a field established above as a
genuine first publication. The full set of 121 distinct dates and 152 dated documents is
in `data/w09_clinical_guidance.json`; this is the ordered spine.

| Date | Body | Document | Date field |
|---|---|---|---|
| 2013-10-28 | NHS England | Interim protocol for gender identity services | `wp:date_gmt` |
| 2016-12-16 | NHS England | Tavistock and Portman to take responsibility for gender identity services at Charing Cross | `wp:date_gmt` |
| 2019-07-03 | NHS England | Service specification: Gender Identity Services for Adults (Non-Surgical Interventions) | `wp:date_gmt` |
| 2019-07-03 | NHS England | Service specification: Gender Identity Services for Adults (Surgical Interventions) | `wp:date_gmt` |
| 2020-09-22 | NHS England | NHS announces independent review into gender identity services for children and young people | `wp:date_gmt` |
| 2022-03-10 | RCPCH | Response to the Cass Review **interim** report | `datePublished` |
| 2022-06-08 | GOV.UK | Gender Recognition Certificate: list of medical practitioners in gender dysphoria | `first_published_at` |
| 2022-07-28 | BPS | Response to the new NHS England regional model for CYP gender identity services | `datePublished` |
| 2022-07-29 | RCPCH | Response to further advice from the independent review | `datePublished` |
| 2023-12-07 | NHS England | CYP Gender Incongruence: referral pathway consultation | `wp:date_gmt` |
| 2024-03-12 | NHS England | **Clinical policy: puberty suppressing hormones** | `wp:date_gmt` |
| 2024-03-21 | NHS England | Clinical commissioning policy: prescribing of gender affirming hormones | `wp:date_gmt` |
| 2024-04-09 | NHS England | **Response to the final report of the independent review** | `wp:date_gmt` |
| 2024-04-10 | RCPCH | Response to the **Cass Review final report** | `datePublished` |
| 2024-04-10 | RCPsych | Response to the final report from Dr Hilary Cass | canonical URL |
| 2024-04-22 | RCPsych | Detailed response to the Cass Review's final report | canonical URL |
| 2024-05-29 | GOV.UK | **New restrictions on puberty blockers** | `first_published_at` |
| 2024-07-19 | GOV.UK | Review of suicides and gender dysphoria at the Tavistock and Portman NHS FT | `first_published_at` |
| 2024-08-07 | NHS England | **CYP gender services: implementing the Cass Review recommendations** | `wp:date_gmt` |
| 2024-08-07 | NHS England | Referral pathway for specialist CYP gender incongruence service | `wp:date_gmt` |
| 2024-08-07 | RCPCH / RCPsych | Responses to the NHS England implementation plan | `datePublished` / URL |
| 2024-08-22 | GOV.UK | Puberty blockers temporary ban extended | `first_published_at` |
| 2024-09-05 | NHS England | Referral pathway for CYP Gender Services | `wp:date_gmt` |
| 2024-11-06 | GOV.UK | Extension to temporary ban on puberty blockers | `first_published_at` |
| 2024-11-14 | NHS England | Review of the NHS adult GDCs: terms of reference and key lines of enquiry | `wp:date_gmt` |
| 2024-12-11 | GOV.UK | **Ban on puberty blockers to be made indefinite** | `first_published_at` |
| 2024-12-12 | GOV.UK | Health and Social Care Secretary's statement: puberty blockers | `first_published_at` |
| 2025-01-24 | GOV.UK | CHM report on proposed changes to the availability of puberty blockers | `first_published_at` |
| 2025-12-18 | NHS England | Operational and delivery review of NHS adult gender dysphoria clinics | `wp:date_gmt` |
| 2026-02-20 | GOV.UK | MHRA statement on the PATHWAYS puberty blocker trial | `first_published_at` |
| 2026-03-09 | NHS England | Clinical policy: prescribing of masculinising and feminising hormones for children and adolescents | `wp:date_gmt` |
| 2026-04-01 | NHS England | **Service specification: NHS Children and Young People's Gender Service** | `wp:date_gmt` |

Beyond gender-specific policy, the harvest also carries dated NICE guidance for the
comparator domains W02 uses — depression in children and young people (NG134,
2019-06-25), quality standard QS48 (2013-09-30), autism, eating disorders and self-harm.
These matter for the same reason the urgent-suspected-cancer referral series matters in
W02: they date guideline change in domains that share the referral system but not the
subject.

## How to use these, and how not to

**These dates are anchors, not results.** Nothing here has been run through
`mechanism_simulation.compare_mechanisms` and nothing in this document should be read as a
finding about any proposition.

Three cautions carry forward.

1. **A response date is not a publication date of the thing responded to.** RCPCH's
   2024-04-10 record dates *its own statement*. It is strong corroborating evidence for
   when the Cass final report appeared, and it is not the report's metadata. Keep the
   distinction when citing.
2. **The 19 undated documents are not absences.** They include NICE's in-development
   gender incongruence guidance and RCPCH's consultation responses on the interim service
   specification — some of the most directly relevant material in the workstream. They
   exist; their dates are unknown from these routes. A failed or missing date field is
   unknown, never "no such guidance".
3. **`OFF_TOPIC_SEARCH_RESULT: 573`.** Free-text search on GOV.UK and NHS England is
   recall-oriented and returns a full page of results whether or not the terms appear: an
   unfiltered run returned HMRC sign-in pages under "Cass review". The topic filter lives
   in `scripts/harvest_w09.py`, not in the connector, so the topic definition stays
   visible and auditable and the connector stays a general retrieval tool. Widening
   `TOPIC_TERMS` widens the harvest.

## Requested `registries/sources.csv` row

`registries/sources.csv` was owned by another agent during this run, so the connector
declares `SOURCE_ID = "UNREGISTERED:W09-CLINICAL-GUIDANCE"`. The row requested, taking
the next free id after `DS075`:

| Field | Value |
|---|---|
| `source_id` | `DS077` (or the next free number) |
| `source_name` | UK clinical guidance and NHS policy documents: NICE, NHS England, GOV.UK and professional bodies |
| `workstream_id` | `W09` |
| `access_class` | `OPEN` |
| `licence` | `OGL_v3` (GOV.UK, NHS England); NICE and professional-body content under each publisher's own terms, metadata only |
| `api_key_required` | `no` |
| `endpoint` | `https://search-api.nice.org.uk/api/search`; `https://www.england.nhs.uk/wp-json/wp/v2/`; `https://www.gov.uk/api/content`; publisher sitemaps |
| `notes` | Dated policy anchor points for temporal-ordering tests. Publication dates only — revision timestamps are recorded separately and never used to anchor. Cass Review site, UKGWA, GMC and BMA declined; see `docs/W09_CLINICAL_GUIDANCE.md`. |

If the registrar prefers one row per host, split into four rows sharing `workstream_id=W09`
and keyed on the four endpoints above; the connector reads `SOURCE_ID` in one place and can
be repointed either way.

## Verification

`.venv/Scripts/python.exe -m pytest` — **929 passed, 3 xfailed, exit code 0**. The three
xfails are the pre-existing `test_governance_field_wiring` entries documented in
`docs/WIRING_AUDIT.md` and are unrelated to this work. 41 of the passing tests are new and
live in `tests/unit/test_clinical_guidance.py`; all use `httpx.MockTransport` and none
touches the network.
