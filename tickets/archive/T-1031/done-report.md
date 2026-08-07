## Done report

Changed:
- docs/guides/estate-natives-build-rollout.md (new) -- the per-repo recipe
  for converting a sibling's hand-rolled `uv run maturin develop` Makefile
  step to the one-line `frob natives build` shim (mirrors
  docs/guides/estate-capability-migration.md's T-1071 shape exactly:
  why-this-migration, per-repo recipe, a dated fleet-sweep record table,
  and an explicit "not done here" scope-cut section).
- docs/index.md -- linked the new guide from the docs index (DOC001
  requires every guide be linked or carry its own frob:describes/frob:doc
  anchor).

Fleet survey (per this repo's own fleet.toml, 8 siblings + frob itself):
checked each sibling for a `Cargo.toml` building a Rust/pyo3 Python
native extension with a hand-rolled `maturin develop` call in its
Makefile.
- `graphite`, `typani`, `lograder`, `aprog-public`, `aprog-private`: no
  `Cargo.toml` at all -- no native extension, nothing to route.
- `logand.app`: one `Cargo.toml` (`wasm-ascii/`), but it targets
  `wasm-bindgen` (WebAssembly), a different toolchain entirely, not a
  Python native `frob natives build` builds -- nothing to route.
- `lithos`, `feldspar`: both hand-roll `uv run maturin develop [--uv]`
  directly inside `install`/`build`/`dev` Makefile targets and have no
  `[[native]]` entry in their own `frob.toml` -- routed via
  `frob fleet route` (T-0573), landing directly in each sibling's own
  ledger:
  - lithos: routed as lithos's own T-0077 (`fleet: routed T-0077 into
    lithos`), scope `Makefile`+`frob.toml`, kind `docs`.
  - feldspar: routed as feldspar's own T-0027 (`fleet: routed T-0027 into
    feldspar`), scope `Makefile`+`frob.toml`, kind `docs`.
  Both routed tickets' bodies embed the self-contained per-repo recipe
  (the sibling repo cannot see this repo's own docs/) and point back at
  this guide for the design precedent, mirroring T-1071's exact
  fleet-route shape.

This repo's own compliance was NOT re-verified from scratch (already
confirmed at T-0735's close per the ticket body); `git diff main -- Makefile`
shows no change here, consistent with that.

Evidence: docs-only ticket with no pytest surface of its own (mirrors
T-1071's own precedent and this playbook's T-0167 convention for
docs-only tickets) -- recording the existing CLI-dispatch integration
test as evidence:
`tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches`.

Filed: lithos T-0077, feldspar T-0027 (both routed sibling tickets, in
their OWN repos' numbering spaces, not this repo's tickets.md/
tickets-archive.md -- nothing to renumber here).

Gates: `uv run frob check --ticket T-1031 --only gates-fast` shows 26
errors, ALL pre-existing per `git diff main --stat` (zero touch) against
every flagged file -- the same 26 disclosed in T-1035/T-1112's Done
reports (23 COV003 archive-evidence residue tracked as T-1143, 1 COV001
on src/frob/gates/_tracked_files.py, 1 INV006 on
src/frob/app/ticket_runner/_mutate.py, 1 TICK006 on T-1114's phantom
draft). DOC001 (the new guide unlinked) is now clean after linking it
from docs/index.md -- 0 DOC errors.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 15 error(s), 541 warning(s), 424 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/ticket_runner/_mutate.py, SELFAUDIT001@design, TICK006@tickets.md
