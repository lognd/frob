## Done report

Changed: docs/modules/gates.md ("Abandoned auto-fix journal detection (T-1348, T-3526)" subsection)

Added a new subsection under the "--fix Tier-A deterministic auto-fix
handlers (T-1138)" anchor covering write_autofix_manifest,
clear_autofix_manifest, read_abandoned_autofix_manifest,
AutofixManifest, and _abandoned_autofix_result / AUTOFIX001, including
T-3526's journal-before-first-mutation contract change.

Evidence: docs-kind change, closed via `frob ticket close --evidence-cmd` per docs-ticket convention (no code/tests touched).

Filed: none

Gates: scoped `frob check --ticket T-3534 --budget 300` run under
concurrent host load (7 other checks running); repo-wide FAIL lines
observed are pre-existing per the run's own note and unrelated to this
docs-only change; no gates.md-specific new finding (DOC/DOCENUM/COV)
surfaced against the added text.
