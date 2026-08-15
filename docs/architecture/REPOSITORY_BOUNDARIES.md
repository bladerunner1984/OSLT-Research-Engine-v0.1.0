# Repository and estate boundaries

| Estate | Purpose | May contain raw person-level data? |
|---|---|---:|
| GitHub | code, schemas, manifests, public metadata, approved results | No |
| Open object store | public/licensed evidence where terms permit | No identifiable data |
| Participant secure store | explicitly consented primary research | Yes, under approval |
| TRE/SDE | NHS/ONS/DfE and other controlled microdata | Yes; never exported raw |
| Film workspace | released claim cards, public sources, approved media | No unreleased sensitive data |

Serverity and OSLT must use separate repositories, credentials, databases, buckets, queues and audit
ledgers. Reuse occurs through documented patterns and deliberately versioned schema packages only.

## Byte-preservation boundary

`docs/reference/v2.4-rc1/**` and `registries/*.csv` are marked `-text` in `.gitattributes`.
This prevents Git line-ending conversion from changing hash-pinned source bytes on Windows.
Executable source/configuration remains normalised to LF; PowerShell scripts use CRLF.
