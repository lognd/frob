## Done report

T-0494 legitimately removed test_no_clone_group_at_any_threshold (its
zero-groups assertion was inverted by T-0487's keyword fix). Commit
458244a already re-pointed T-0187/T-0198's dangling evidence ids in
tickets-archive.md at that landing, but T-0198's evidence list ended up
with the surviving replacement id
(test_both_languages_parse_into_the_snapshot) repeated 6 times where the
original had 6 separate now-stale entries, plus the Done report's own
evidence-recap list carried the same 6x repeat. Deduped both to a single
entry (plus the untouched test_both_symbols_are_individually_fingerprinted
line), and left a note in the Done report explaining the pre-dedup pass
count. T-0187's evidence list had no duplicates. Verified via
`uv run frob check --ticket T-0187` and `--ticket T-0198`: 0 COV003 hits in
either scoped run (grep -c COV003 on full check output -> 0); remaining
errors are pre-existing COV006/DOC/REG findings unrelated to this ticket's
scope (tickets.md/tickets-archive.md evidence only).

### Changed
(no changed files detected)

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
