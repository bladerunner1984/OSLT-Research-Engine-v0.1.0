# Security Policy

## Never commit

- identifiable or pseudonymisable participant records;
- NHS/ONS/DfE/TRE microdata or unapproved outputs;
- private email, message, browsing or platform exports;
- API tokens, OAuth files, credentials, private keys or production endpoints;
- licensed corpora whose terms prohibit redistribution.

## Data-estate separation

`OPEN`, `LICENSED`, `PARTICIPANT_SECURE`, and `TRE_SDE` are separate stores with separate authority.
Git contains code, schemas, manifests, hashes, query definitions and permitted result objects only.

## Reporting

Report a suspected vulnerability privately to the repository owner. Do not open a public issue for a
security or privacy incident.
