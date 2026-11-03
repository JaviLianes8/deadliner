# deadliner 1.0.0 certification report

Preparation resumed from 1e7a670. Main is 8064ed4 (0.2.0). PyPI returned HTTP 200
on 2026-11-03: 0.2.0 was published on 2026-10-31. The earlier 404 is obsolete.

Progress:
- [x] Resume release branch without discarding the existing report commit
- [x] Baseline: four gates and strict tests typing; 1,312 tests passed
- [x] API, errors, typing, public examples (items 1 to 5)
- [x] Contracts, seeded properties, fetched references (items 6, 7, 9)
- [x] README, GUIDE, dated CHANGELOG and metadata (items 11 to 13)
- [ ] Built-wheel consumers, PyPI upgrade, distribution inspection (items 8, 14)
- [ ] Every installed supported interpreter (item 10)
- [ ] Mutation round and final gates (items 18, 15)
- [ ] PR and guard
- [ ] Independent reviewer and five QA lenses (items 16, 19): pending
- [ ] Merge and publish (item 17): pending

## API decisions

The six names and operation signatures remain. Callable aliases become structural
protocols, with their own runnable documentation. Functions remain compatible.
Errors omit caller labels and CLI input; attributes retain the requested label.
Finite weight sums no longer overflow, tiny suffixes remain usable, and final split
expiry is exact. Cancellation retrieves eventual errors on both cleanup paths.
All differences from 0.2.0 are listed in CHANGELOG and GUIDE. Callback contracts,
float precision, cooperative cancellation, sleep overshoot, subclass-state limits,
and direct-child CLI termination are explicit.

## Ground truth

Sources fetched on 2026-11-03 by `scripts/fetch_upstream.py` to an external scratch
directory. `UPSTREAM-MANIFEST.json` records URLs, pinned revisions where available,
byte counts, SHA-256 and licences. No downloaded text is committed or shipped.
`tests/test_upstream.py` verifies hashes before extracting GNU exit codes, checking
the Go parent-deadline branch, and exercising Python's monotonic clock contract.
The independent runtime oracle is local GNU coreutils timeout 8.32. The existing
real stdlib tests exercise queue, lock, subprocess, sockets and async timeouts.
The GNU web manual endpoint timed out; its official v9.7 source was fetched instead.

## Properties and contracts

Hand-generated cases are labelled separately from fetched evidence. Three seeds
produce 3,000 weighted splits checked with exact Fraction arithmetic; three seeds
produce 30,000 hostile duration strings; two seeds exercise 20,000 clock/child/cap
combinations. Long malformed numeric strings, huge labels, extreme finite weights,
exact expiry and cleanup cancellation have explicit regression contracts.
