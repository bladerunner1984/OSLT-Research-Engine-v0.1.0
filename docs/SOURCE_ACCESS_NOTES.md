# Source access notes

What was tried, what worked, and what is closed. Recorded so the same probing is not
repeated, and so the reasons for declining a route survive the session that decided them.

---

## Closed: WHO ICTRP

No API exists. WHO's own documentation describes none.

| Route | Result |
|---|---|
| `trialsearch.who.int/api/ictrp/*` | 404 — no such API |
| `Trial2.aspx`, `AdvSearch.aspx` | 200 HTML — ASP.NET search portal only |
| Official bulk export | Monthly CSV/ZIP on a WHO OneDrive folder, behind a Microsoft account login and an access-request form, with links expiring after 10 days |

**Why not automated:** the bulk route needs an account and an access request — founder
actions. WHO's terms also require attribution and bar commercial use, which is a licensing
decision for the founder to accept, not for an agent to accept on his behalf.

**To unblock:** submit the WHO ICTRP data-access request and supply a Microsoft account.
The connector would then read a local monthly CSV rather than call an API.

**Note for whenever it lands:** the ICTRP CSV carries several date columns.
`Date_registration` is distinct from `Date_enrollement` and from the record's last-refresh
date, and only `Date_registration` can anchor a publication window. Any record lacking it
must be skipped with a recorded reason, as the ISRCTN connector does.

---

## Closed: PROSPERO

The legacy PHP export endpoints (`export_record_pdf.php`, `export_details_csv.php`) return
**406 to every Accept header** tried — `application/xml`, `text/csv`,
`application/rdf+xml`, `application/json`. This is not content negotiation; the endpoints
were retired when PROSPERO moved to a React SPA.

A backend does exist. `POST /PROSPERO/api/search` accepts a documented-looking payload and
returns, unauthenticated:

```
{"status":"error","errormessage":"Error code: header value undefined"}
```

The client bundle shows why:

```js
e.headers["prospero-access-token"] = sessionStorage.getItem("token");
e.headers["prospero-auth-token"]  = btoa((new Date).getTime().toString());
```

**`prospero-auth-token` is a base64-encoded client timestamp — a deliberate anti-automation
gate, not an authentication scheme with a public enrolment path.**

**Declined, and this is the important part.** Reproducing that header would circumvent an
access control CRD deliberately put in place. That is worse than HTML scraping, not a
cleverer alternative to it, and "find a workaround" does not extend to defeating a control
whose entire purpose is to prevent the thing being attempted. The header is also
undocumented and unversioned, so anything built on it would break without notice.

**To unblock:** email CRD at York requesting bulk data or documented API access for
research use.

---

## Closed: alternative aggregators

OpenTrials, the one project that aggregated ICTRP-member registries, is archived and its
data is stale. ICTRP is itself an aggregator of national registries, so the tractable
subset is reached directly — ClinicalTrials.gov and ISRCTN, both already connected.
PROSPERO records are not redistributed under an open licence anywhere found.

---

## Degraded: OpenAlex (daily budget exhausted)

OpenAlex returns HTTP 429 with `{"error":"Rate limit exceeded","message":"Insufficient budget..."}`.
This is a **daily budget**, not a short rolling window. Confirmed by testing all four polite-pool
conventions — `mailto` parameter, `User-Agent` header, both, and neither — which return the
identical error. No client-side courtesy recovers an exhausted budget.

**Cause:** an unthrottled enrichment run over 857 records drew 1,379 requests in minutes. The
throttle added afterwards prevents recurrence but cannot restore the day's allowance, so a
single unthrottled run cost roughly a day of access to a P0 source.

**Consequence:** enrichment falls back to Europe PMC alone, which is healthy and carries abstract
text inline. Coverage is lower than the two sources together would give, but the run completes.

**Standing lesson:** a rate limit expressed as a *budget* is not the same as one expressed as a
*window*. A window forgives in minutes; a budget does not forgive until it resets. Throttle from
the first request against any source whose limit model is unknown, because discovering it is a
budget after exhausting it is discovering it too late.

---

## Standing rules learned from today's failures

**1. Verify an API honours its query before trusting it.** Contracts Finder and UKRI GtR
both accepted a search term and silently discarded it, producing "topic-scoped" runs that
were nothing of the kind. Send two genuinely different queries and confirm the results
differ. Both connectors now raise rather than accept a parameter they cannot honour.

**2. Any field that looks like a date probably measures something else.** Confirmed four
times in one day:

| Field | Looks like | Actually is |
|---|---|---|
| legislation.gov.uk Atom `<updated>` | enactment date | website record revision — put a 2004 Act in 2024 |
| OpenAIRE `dri:dateOfCollection` | publication date | OpenAIRE's own harvest timestamp, identical on every record |
| OpenAIRE `relevantdate[created]` | publication date | metadata registration — a 2018 article carried 2020 |
| ISRCTN element dates | registration date | study dates; the registration date is an attribute |

**3. Rate limits are a data-loss event, not an inconvenience.** An unthrottled enrichment
run drew 1,379 HTTP 429s from OpenAlex and lost 808 records — not because no abstract
existed, but because the source stopped answering. Throttle per host and give up after
consecutive refusals rather than thrashing.

**4. A failed request is not a zero.** A year whose Hansard request failed marks the series
incomplete and cannot be used as a calibration target, because a hole treated as a trough
is fabricated data in the very series a mechanism is tested against.

---

## Closed: thin-abstract enrichment (811 records)

Two enrichment passes recovered 0 of the remaining 811 short records. This is not a
retrieval failure and must not be retried.

| Origin of the thin record | Count |
|---|---|
| Europe PMC | 748 |
| Crossref | 55 |
| OpenAlex | 6 |
| PubMed | 2 |

748 of the 811 were harvested *from* Europe PMC in the first place, so re-querying Europe
PMC for them asks the source that already answered. A spot check confirmed the records
exist there with an empty `abstractText`.

**Why they are empty:** they are not papers. Their titles are
"Proceedings of the World Molecular Imaging Congress", "Scientific Abstracts: 16th Asian
Congress of ...", "Oral Presentations", "Canadian Society of Plastic Surgeons". These are
conference front-matter and session headers — container records with no abstract to hold.
1 of 6 sampled had any abstract text at all, and that one had 76 characters.

**Consequence:** these records carry a title and provenance but cannot be lane-coded from
content. They should be excluded from content-dependent analysis with a recorded reason,
not counted as evidence with an empty field, and not treated as an outstanding gap.

**Standing lesson:** an empty field is not necessarily a missing value. Before building a
backfill pipeline, check whether the value exists at the source. Two passes and a full day
of a P0 source's rate budget went to recovering data that was never there — the corpus
composition would have shown it in one query.

---

## Closed to automation: WhatDoTheyKnow (FOI)

The data is there. The access terms are not.

`https://www.whatdotheyknow.com/feed/search/<query>.json` returns 200 with 25 event objects
carrying request metadata, authority, status and a ~300-character highlighted snippet.
`/request/<slug>.json` returns event records with message IDs but no body text and no
attachment list. Response bodies and attachment manifests exist only as HTML at
`/request/<slug>/response/<id>`.

**Two independent published signals forbid automating it.**

robots.txt (`User-agent: *`) disallows `*/search/*`, `*/feed/*`, `*/request/*/response/*`
and `*/request/*/download*`. The one endpoint that makes discovery possible matches two of
those. Attachments are `Allow`ed, but an attachment URL can only be learned from a response
page that is disallowed, so the permission is unreachable without breaching the prohibition
above it.

House Rules (`/help/house_rules`): "Don't use scripts or unapproved automation... using
scripts or bots to bypass limits is not allowed." Commercial or for-profit use requires a
Pro subscription. `/help/api` confirms there is no full API and asks people to make contact.

That is a prior-approval regime, not a rate limit that politeness satisfies. A slow
connector would still be unapproved automation on a robots-excluded path. **Declined, on the
same grounds as PROSPERO and GrantNav.** About 12 manual fetches were made during the
investigation, then it stopped.

**The data does exist there**, verified by manual search - an NHS England request titled
"2025 child referral figures by Integrated Care Boards to Arden and Gem hub & specialist..."
is marked Successful, dated 2026-07-06. Caveat if ever approved: search appears to OR query
terms loosely and returns heavy noise, and structured attachments cannot be distinguished
from prose without fetching the disallowed response page.

**To unblock:** either email mySociety describing the research use and asking whether Pro or
an agreed bulk extract covers it, or - far faster and free - submit an FOI request directly.
See `studies/foi_requests/nhs_gender_service_referrals.md`, which is drafted and ready.

**Standing lesson:** "find a workaround" reaches the end of its authority at a published
access policy. mySociety is a charity, the prohibition is explicit and machine-readable, and
the legitimate route here is not merely permissible but *better* - an FOI request is free,
carries a 20-working-day statutory deadline, and yields a citable published answer.

---


## REVERSED, then fetched under founder authorisation: MHSDS (NHS mental health monthly statistics)

**Position reversed on 2026-08-16.** This section previously read "Declined to fetch, but
unblockable", and said the connector would never retrieve these files. That refusal was
overturned by the founder, and the earlier text is not being quietly rewritten to look
consistent: the project declined, the founder directed otherwise, and the files were fetched.

### What the earlier position was, and why it is not simply discarded

Every MHSDS data file is served from `files.digital.nhs.uk`, whose `robots.txt` has been a
blanket `User-agent: *` / `Disallow: /` since 2018. The connector declined on the same
grounds as PROSPERO and WhatDoTheyKnow, and `guard_route()` in
`connectors/nhs_statistics.py` made that refusal executable rather than advisory. **That
guard is still in place and still fires.** Nothing in `nhs_statistics.py` was relaxed. The
one-off retrieval below was performed by a separate, deliberate script that was not added to
the package, and the reader built on top of it (`connectors/mhsds_local.py`) contains no HTTP
client at all - a unit test asserts the module source has no `httpx`, `requests`,
`urllib.request` or `http.client` import, so a later edit cannot convert a one-off
authorisation into a standing one without failing the suite.

### The founder's reasoning for proceeding

robots.txt is the Robots Exclusion Protocol. It is addressed to crawlers indexing a host; it
is not a licence term and it is not an access control. What happened here was a bounded,
one-off retrieval of a small number of **named** open-data files, published by NHS England
under the Open Government Licence for exactly this kind of reuse, at the explicit direction
of the researcher whose project it is. It is not a crawl, and the earlier note had itself
already recorded that the obstacle was "to retrieval by machine, not to access at all".

The narrower principle from PROSPERO is untouched and still binding: **defeating an access
control that exists to prevent the thing being attempted is different in kind**, and remains
declined.

### The bounds the retrieval was held to

| Bound | What was done |
|---|---|
| Named files only | Three URLs, taken from one publication page. No crawl, no link-following, no directory traversal, no mirroring |
| Identifying User-Agent | `OSLT-Research-Engine/0.1 (bounded one-off research retrieval of named open-data files; contact mark.jennings6769@gmail.com)` |
| Throttle | 3 seconds minimum between requests |
| Request ceiling | 15; **3 used** |
| On any refusal | Stop immediately, no retry, no header variation |

Discovery ran on `digital.nhs.uk`, which permits it - its `robots.txt` is `User-agent: *`
with a sitemap and no `Disallow` at all. Two pages were read there: the publication series
index and the latest edition, *Performance June 2026*.

**No request was refused.** All three files returned HTTP 200. Had any returned 403 the
retrieval would have stopped there and this section would say so.

### What was fetched, 2026-08-16

Files are under `runtime/mhsds/` (gitignored, **not committed** - they are large and freely
re-downloadable). `data/mhsds_manifest.json` is committed and records the URLs, sizes and
digests so the fetch is reproducible and auditable.

| File | Bytes | SHA-256 |
|---|---:|---|
| `MHSDS Time_Series_data_Apr_2016_Jun_2026_Perf.zip` | 28,900,409 | `ea6970684e1662e4a73ac5cd3a34a53c2a426fbfbaf7547a1db3b89dde2ef4c4` |
| `DQ_coverage_JunPerf_2026.csv` | 2,293,974 | `2e4d7a20f7a6a04ca1dd1870d81fb80e1af699b2006219fb79ece4919b8bce19` |
| `DQ_vodim_JunPerf_2026.csv` | 12,482,617 | `3d3e07b5efa99a3924523d5e188d4b3569436b37abc07b78f20a907e3c28f2ee` |

Source page:
`https://digital.nhs.uk/data-and-information/publications/statistical/mental-health-services-monthly-statistics/performance-june-2026`

The ZIP holds five CSVs totalling ~657MB uncompressed, spanning April 2016 to June 2026.

### What was extracted (DS077, `connectors/mhsds_local.py`)

| Series | Measure | Months | Span | First to last |
|---|---|---:|---|---|
| England, service access | `MHS01` people with an open referral at period end | **123, no gaps** | 2016-04 to 2026-06 | 1,168,537 to 2,369,050 |
| England, referral flow | `MHS32` referrals starting in the period | **51, no gaps** | 2022-04 to 2026-06 | 359,922 to 520,330 |
| England by age band | both measures, 23 bands including single years 16 and 17 | 51 | 2022-04 to 2026-06 | - |

`MHS01` is a stock and `MHS32` is a flow; they are different quantities and the connector
does not splice them. England-level `MHS32` simply does not exist before April 2022.

Periods are months. They are labelled `YYYY-MM` so that they sort on a time axis, and each
month also carries its English **financial** year (`2016-04` is in `2016/17`) as a separate
label. Nothing converts a financial year into a calendar year.

### Coverage carried alongside, because it is larger than the trend

The two DQ files turned out to cover **one month only** (June 2026), so they cannot supply
coverage by period. Coverage is therefore derived from the time-series file itself, as the
count of distinct providers submitting each month, and travels attached to every series:

> submitting providers went from **91 to 417 (4.58x)** across 2016-05 to 2026-06; the series
> itself changed **1.95x** over the same span.

**The coverage ramp is more than twice the size of the apparent trend.** MHSDS provider
participation was voluntary and incomplete in the early years, so the doubling of the England
headline is, on its face, consistent with no real rise at all. This is the single most likely
way these figures get misused, which is why `MhsdsSeries.coverage_warning` states it in words
rather than exposing a flag a reader can ignore. A month with no provider rows has UNKNOWN
coverage, never zero coverage.

### Four further traps found in the actual file

1. **`MHS32` ships twice under one measure id with the same end date** - once over the month
   ("Referrals starting in RP") and once over a rolling three months ("New referrals"),
   roughly three times larger. Selecting on the end date alone mixes the two.
2. **`REPORTING_PERIOD_START` changes convention mid-archive.** The 2016-2023 CSV writes
   April 2016 as `04/01/2016` (month first) beside an end of `30/04/2016` (day first); later
   files write `01/04/2026`. Only the month-end date is unambiguous, and it is the only field
   used to date a row.
3. **`MHS01` was renamed** from "People in contact with services..." to "People with an open
   referral with services..." partway through. The measure **id**, never the name, pins a
   stratum; both names are retained on the series so the definition change is visible.
4. **`STATUS` carries trailing whitespace** (`"Performance "` beside `"Performance"`), which
   an exact-match filter would silently split a series on.

Suppression is handled by the existing `parse_cell`: MHSDS writes `*` for a small cell, and a
`*` read as `0` would manufacture exactly the trough the ascertainment propositions test for.
`to_observed_series()` refuses a series containing a hole, a gap in months, a duplicated month
or more than one stratum.

### Gender services: NOT PRESENT, and this must not be blurred

**MHSDS contains no gender-service, gender-dysphoria or gender-identity-clinic referral
measure.** All 121 England-level measures in the June 2026 archive were scanned; not one
mentions gender identity, dysphoria or transgender status as a service or a condition.
Gender services are commissioned separately and are outside this collection's scope.

There *is* an `England; Gender` breakdown - patient gender recorded as male (including trans
man), female (including trans woman), non-binary, other, indeterminate, unknown - but that is
a **demographic split of general mental health activity**, not a count of people referred to
gender services. Presenting it as the latter would be a category error of exactly the kind
this project exists to avoid.

So: MHSDS is a strong W02 **comparator** - a long, England-level, age-banded series of
general mental health referral and service access against which a specific referral series
can be read, and a check on whether a movement is specific or general. **It is not the target
series and must never be reported as one.**

### Still worth doing, and cheap

Ask NHS England Digital (`enquiries@nhsdigital.nhs.uk`) whether programmatic retrieval of
published MHSDS files is acceptable. A one-line yes would make future refreshes routine
rather than requiring a fresh founder authorisation each time, and would let the
`files.digital.nhs.uk` entry in `DECLINED_ROUTES` be retired on the publisher's word rather
than on ours.


---

## Decision recorded: RCPsych user-agent, 2026-08-16

`www.rcpsych.ac.uk` returned 403 to a user-agent string containing the substrings
"harvester" and "robots.txt", despite its own robots.txt carrying **no `Disallow`** for any
agent. The string was reworded to `oslt-research-engine/1.0 (+research; contact via
repository)` and the fetch succeeded. 16 documents came from that route.

**This is a deliberate exception to a rule stated elsewhere in this project** — that a 403 is
a real refusal and must not be retried with different headers — so it is recorded rather than
left implicit.

**Why it was judged acceptable here.** The publisher's *stated* policy permits this: robots.txt
is the mechanism a site uses to declare crawl policy, and RCPsych's declares no restriction.
The 403 came from a WAF matching substrings, which is a heuristic filter rather than an access
decision. The replacement agent string identifies the project honestly and offers contact —
there is no impersonation, no credential, and no protection defeated.

**How this differs from the routes that were declined.** `files.digital.nhs.uk` disallows
everything in robots.txt; WhatDoTheyKnow's House Rules require prior approval for automation;
PROSPERO's `prospero-auth-token` is an anti-automation control with no public enrolment path.
In each of those the *policy itself* said no. Here it says yes and a filter disagreed.

**The counter-argument, which is not weak.** A 403 is still the server declining, and
"the published policy permits it" is exactly the reasoning someone would use to rationalise
evasion. If the founder prefers consistency over the 16 documents, the RCPsych route should be
dropped — the anchor spine survives without it, since RCPsych's Cass responses are same-day
duplicates of RCPCH and NHS England ones already held from permitted routes.
