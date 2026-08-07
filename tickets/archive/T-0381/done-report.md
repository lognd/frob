## Done report

Added a mandatory `caught_by` field (pydantic min_length=1, rejects
construction without it) to OutOfScopeEntry + BenignCapability (_threat.py)
and OutOfScopeRegulation (_compliance.py). Every construction site got an
honest value: the 16 CWE_TOP_25_OUT_OF_SCOPE, 10 DEFAULT_BENIGN_CAPABILITIES,
5 QUALITY_OUT_OF_SCOPE entries, and the [[strata.benign_capabilities]] TOML
loader now each NAME the real compensating control (e.g. CWE-78 for the exec
benign-capability) or an explicit "none -- ..." disclosure where none exists.
So an out-of-scope excuse can no longer silently omit "caught elsewhere?" --
it must state the compensating mechanism or admit there is none.

Evidence (3 tests): empty-caught_by-rejected, missing-caught_by-rejected,
missing-caught_by-is-malformed (TOML loader). Implemented by the easy-wins
sweeper; coordinator fixed the declared scope (tests/test_strata*.py matched
zero files -> tests/unit/strata/**; the zero-match-glob authoring hazard is
tracked) and landed via 3-way.
