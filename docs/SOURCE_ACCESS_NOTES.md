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

## Declined to fetch, but unblockable: MHSDS (NHS mental health monthly statistics)

**This is the single most valuable W02 source found, and it is open in every sense but one.**

MHSDS monthly statistics need no login, no application and no key. The publication pages
link ten data files directly, including `MHSDS Time_Series_data_Apr_2016_May_2026_Perf
v2.zip` - a ten-year monthly referral and contact time series - plus data-quality coverage
CSVs. Publication URLs follow a regular pattern
(`.../mental-health-services-monthly-statistics/performance-<month>-<year>`) back to 2023.

**Why the connector will not fetch them.** Every file is served from
`files.digital.nhs.uk`, whose robots.txt is a blanket `User-agent: *` / `Disallow: /`,
unchanged since 2018. Declined on the same grounds as PROSPERO and WhatDoTheyKnow.

The publication *pages* sit on `digital.nhs.uk`, which has no Disallow at all, so discovery
is permitted and only retrieval is not. `NhsEnglandStatisticsIndex` therefore returns file
references and never file contents, and `guard_route()` makes that refusal executable rather
than advisory - links to declined hosts are stripped from index results, so no later edit
can quietly repoint the connector at the CDN.

### The unblock, which requires no interpretation of anyone's policy

**A person downloading a published file in a browser is not a robot.** robots.txt is the
Robots Exclusion Protocol: it governs automated crawlers. It is not a licence term, and it
places no restriction whatever on a human clicking a download link on a public page NHS
England published for exactly that purpose. The files are open data.

So the route is the one already documented for WHO ICTRP: **the researcher downloads the
files manually, and the connector reads them from disk.** This is not a loophole - it is the
ordinary intended use of a public statistics publication, and it moves nothing across the
line the robots.txt draws.

**Founder action.** Download from
`https://digital.nhs.uk/data-and-information/publications/statistical/mental-health-services-monthly-statistics`
and place the files under `runtime/mhsds/`. The time-series ZIP alone covers Apr 2016 to
May 2026 monthly and is the highest-value single artefact for W02.

A local-file reader should then be added, following the `ons_population.py` precedent
(stream and aggregate a large local CSV rather than loading it), and applying the standing
rules: MHSDS suppresses small numbers, so a suppressed cell is MISSING and never zero;
MHSDS mixes England totals with provider and region rows, so nothing sums across levels;
and MHSDS periods are monthly within financial years, which must not be coerced to calendar
years.

**Optional, and cheap.** It is still worth asking NHS England Digital
(`enquiries@nhsdigital.nhs.uk`) whether programmatic retrieval of published MHSDS files is
acceptable. A one-line yes would let the connector fetch directly and remove the manual step
from every future refresh. The manual route does not depend on that answer.

**Standing lesson:** a robots.txt closes the automated path, not the data. Before recording a
source as blocked, ask whether the obstacle is to *retrieval by machine* or to *access at
all* - they are different, and the first has a legitimate manual workaround that the second
does not.
