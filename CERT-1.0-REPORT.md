# deadliner 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to deadliner. Nothing is on PyPI yet
(`https://pypi.org/pypi/deadliner/json` answered 404 on 2026-10-18), and 0.1.0 and 0.2.0
were never tagged or released anywhere, so 1.0.0 is the first release. Every change
against the 0.2.0 code on `main` (8064ed4) is still listed in the CHANGELOG.

Progress:
- [x] Branch `release/1.0.0` created from `main` (8064ed4, version 0.2.0)
- [ ] Baseline gates on 0.2.0
- [ ] API review and 1.0.0 changes (item 1)
- [ ] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Ground truth: fetched sources, GNU timeout and the standard library run live (item 7)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18)
- [ ] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and every Python (items 8, 10, 13, 14)
- [ ] Gates (item 15)
- [ ] PR and trace guard
