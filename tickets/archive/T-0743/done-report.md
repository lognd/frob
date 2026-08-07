## Done report

T-0612's rust adapter flattened every enum variant onto NormalizedField
(bare name only), losing whether a variant was unit/tuple/struct-shaped
and its own payload field names/types. Adds two new model types to
_normalized.py (kept tree_sitter-free, per the ticket's explicit
constraint):

- NormalizedVariantPayload: one payload field of a variant (name --
  struct field name or tuple positional index as a string, reusing
  NormalizedField's existing tuple-index convention -- + optional type).
- NormalizedVariant: one variant's name, line, shape
  ("unit"/"tuple"/"struct"), and payload fields.

NormalizedClass gains a `variants: list[NormalizedVariant] = []` field,
populated only for enum-shaped types. RustAdapter maps it via two new
helpers (_rust_variant_payload, _rust_enum_variant_shapes), wired into
_rust_build_class_shell for enum_item nodes. The pre-existing bare-name
NormalizedField mapping (_rust_enum_variants) is left untouched and still
populated alongside variants -- additive, not a replacement, so no
existing consumer of NormalizedClass.fields regresses.

Coordination with T-0681 (TS phase 2, same model-extension class): out of
this ticket's scope (src/frob/arch/_typescript.py is not in T-0743's
declared scope) -- the model itself (NormalizedVariant/
NormalizedVariantPayload) is language-agnostic and ready for a TS/kotlin
adapter to map onto the same way, whenever that ticket lands.

Also fixed, within T-0632's still-open scope (not T-0743's): a fresh
gates-fast pass surfaced COV002 on four T-0632/T-0727 changed helpers in
src/frob/arch/_python.py that were missing frob:ticket edges -- added
those directives in a small follow-up commit under T-0632 before
continuing T-0743's own work, since it is a real compliance gap in this
worktree's own prior tickets, not a new discovery to file separately.

Known, same self-resolving SCOPE001 noise as T-0632's Done report:
tickets-archive.md (T-0727) and src/frob/arch/_python.py (T-0632) still
show as outside T-0743's declared scope in a fresh check -- both are
already-committed work from the other two tickets in this sequential
arch-cluster worktree, unrelated to any T-0743 edit. Resolves once the
coordinator lands T-0727/T-0632.

Also, unrelated to this ticket: main advanced again mid-session (now at
T-0679's land) and this ticket's deletion-filter check showed
docs/guides/worktree-pool.md, src/frob/scaffold/_pool.py, and
tests/system/test_scaffold_pool.py as deleted -- purely main moving
forward while this ticket was in progress (same class of transient as
T-0632's docs/design/language-adapter-tier-decision.md false positive);
resolved by merging main again before this commit, verified clean below.

Post-commit `git merge main` (main had advanced further, to T-0679's
land) picked up more unrelated upstream churn (dup/_pipeline, testing/
_stability, vet/_capability, scaffold/_pool, exports/__init__); `git diff
main --diff-filter=D --stat` is empty after the merge. `make core`
rebuilt native extensions post-merge; `tests/unit/test_arch.py` +
`tests/unit/test_arch_srp.py` re-run clean afterward: 172 passed, 0
failed (`uv run pytest tests/unit/test_arch.py tests/unit/test_arch_srp.py
-p no:cacheprovider -n0`).

### Changed
```
 src/frob/arch/_normalized.py | 74 ++++++++++++++++++++++++++++++---
 src/frob/arch/_rust.py       | 99 ++++++++++++++++++++++++++++++++++++++------
 tests/unit/test_arch.py      | 91 ++++++++++++++++++++++++++++++----------
 3 files changed, 223 insertions(+), 41 deletions(-)
```
(the done-report tool's auto-filled stat above reused T-0632's stale
diffstat again -- corrected here to `git diff main --stat` scoped to
this ticket's own three files, run and observed directly.)

### Evidence
- `tests/unit/test_arch.py::TestRustAdapter::test_adapt_enum_variant_payload_shapes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s), plus the full
  `tests/unit/test_arch.py` file: 149 passed, 0 failed, observed via
  `uv run pytest tests/unit/test_arch.py -p no:cacheprovider -n0`)
- gates: `uv run frob check --ticket T-0743 --only <stage>` chunked loop
  -- lint/static: 0 errors; gates-fast: 0 errors introduced by this
  ticket's own edits (the only errors present are the pre-existing
  `src/frob/exports/__init__.py` COV001/DOC002 debt already filed as
  T-0878, and the self-resolving T-0727/T-0632 SCOPE001
  inheritance documented above); a bare `frob check --ticket T-0743`
  refuses under FROB_AGENT (expected), which is why the CLI's own
  done-report step reported gates as unmeasured.
