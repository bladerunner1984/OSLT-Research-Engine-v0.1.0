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
