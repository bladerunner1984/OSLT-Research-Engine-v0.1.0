# OSLT Data Management Plan Template

## Data inventory
Source, access tier, controller/owner, sensitivity, fields, dates, location.

## Storage architecture
Separate OPEN store, LICENSED store, PARTICIPANT secure store and TRE/SDE projects. Never centralise raw controlled NHS/education person-level data.

## Identity separation
Direct identifiers -> linkage vault; research data -> pseudonymous study IDs; analysis outputs -> disclosure checked.

## Access
Role-based least privilege; MFA; audit logs; named researchers; review dates.

## Provenance
Every ingest has source/version/query/date/hash/licence/approval and transformation log.

## Retention/destruction
Define per source/consent/contract. Destroy or return when no longer permitted.

## Incident response
Named escalation route; access suspension; containment; notification under applicable institutional/legal rules.
