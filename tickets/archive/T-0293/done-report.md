## Done report

Added normalize_evidence_separator in src/frob/tickets/__init__.py, called
from validate_evidence (the shared write-time entry point for both
new_ticket and add_evidence), so a `path::Class.method` (optionally with a
`[param]` suffix) is rewritten to the pytest-canonical
`path::Class::method` at record time. It rewrites ONLY the first dot after
the `path::` prefix: ids without `::`, ids already carrying a second `::`,
cmd: evidence, module-path dots BEFORE the `::`, and dotted filenames are
all left untouched (reviewer stress-tested the regex on each case).

Bonus fix found while wiring: add_evidence previously resolved/pass-checked/
stored the caller's RAW node_ids even though validation normalized a
separate copy; now resolution, pass-check, and persisted evidence all use
the normalized ids (normalize is idempotent on `::` form, so no double-
normalization risk).

Evidence (3 of 5 tests; all 5 pass): normalizes-dot-separator,
normalizes-dot-with-parametrized-suffix, and the add_evidence integration
test proving stored evidence uses the normalized form. Reviewer APPROVED.
Landed via 3-way patch onto current main.
