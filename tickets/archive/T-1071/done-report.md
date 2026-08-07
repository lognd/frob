## Done report

Changed:
docs/guides/estate-capability-migration.md (new)
docs/index.md

Deliverable is frob-side machinery + docs, per this repo's own
constraint (this repo cannot edit the 8 sibling repos' source). The
actual "sibling repo declarations narrow to net.connect/net.listen"
edits are out of scope for a frob-repo worktree by construction and are
left to whichever agent picks up each sibling's own routed ticket,
following the per-repo recipe this doc records.

Machinery used (pre-existing, T-0573): `frob fleet route` filed one
ticket per sibling directly into that sibling's own ledger (not a code
edit in this repo, not a hand-edited sibling file) for the 5 siblings
whose design/*.strata actually has a bare `may "net"` or literal
fs-write/fs-read hit:
- lithos T-0076
- graphite T-0024
- aprog-public T-0062
- aprog-private T-0017
- logand.app T-0007

feldspar/typani/lograder had zero matching declarations (grepped their
design/*.strata) -- no ticket filed for them, recorded as such in the
guide rather than silently skipped.

Scope was widened twice from the ticket's originally declared
docs/design/registry/** (which does not cover this deliverable at all --
that directory is the unrelated design-knowledge corpus registry) to add
docs/guides/** (the recipe doc itself, matching where every other
agent-facing process doc lives) and docs/index.md (one line linking the
new guide, required by gate:DOC/DOC001's orphan-doc rule). Both changes
went through `frob ticket scope --add --reason-file`, reasons recorded
in the ticket's own scope_changes audit trail.

Evidence: this is a docs-only ticket with no code changed in this repo,
so there are no frob:tests-bound pytest node ids to bind (no code
symbol was added or changed). Evidence is the passing gate groups below,
run per T-1004/T-0627's foreground+timeout recipe (`frob test --base
main` falls back to a suite-wide pytest run for unknown-language .md
files' selection, ~900s -- not run; not applicable, since there is no
code-level touched-set to select tests against).

Gates: frob check --ticket T-1071 --only <group> clean for lint (ruff-
check/ty clean; ruff-format's one finding is in src/frob/gates/_waive.py,
a file this ticket never touched, pre-existing), static, gates-fast,
gates-native, gates-security -- 0 errors across every group after fixing
DOC001 (link the new guide from docs/index.md) and PRE001 (re-swept
after the scope widen).

### Changed
```
 docs/guides/estate-capability-migration.md | 100 +++++++++++++++++++++++++++++
 tickets.md                                 |  32 ++++++++-
 2 files changed, 130 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 700 warning(s), 419 waived
- error-findings: none (measured, zero errors)
