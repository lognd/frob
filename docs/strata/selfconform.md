# Self-conformance: SYS100-102 vs `design/frob.strata` (T-0150)

`frob sys audit` runs a fourth check family, SYS100-102, alongside the
THREAT/COMPLIANCE exhaustiveness conjunction (`docs/strata/threat.md`):
does the capability surface OUR OWN `src/frob/` tree actually exhibits
match what `design/frob.strata` (the self-hosted architecture model,
T-0081) declares via `code`/`may`? This is the same "design constrains
code" posture `_code_binding.py` (T-0078, import conformance) and
`_effects.py`/THREAT004 (T-0079/T-0113, capability conformance) already
enforce -- SYS100-102 is a THIN layer over that existing machinery, not a
parallel detector.

## Mechanism: `code`/`may`, not a parallel config table

An earlier draft of this ticket believed `code=<glob>`/`may <capability>`
were not reachable from `.strata` SOURCE TEXT (citing a since-corrected
claim in `design/frob.strata`'s own header) and invented a `frob.toml`
mapping table instead. That belief was WRONG: T-0132 landed the
STRING-quoted `code STRING+` / `may STRING` surface grammar in
`strata-core/src/parse.rs::parse_node` well before this ticket's
merge-base (`docs/strata/surface.md#node-grammar-implemented-t-0132-
closes-the-code-may-gap-t-0136-adds-on-deploy`), and `_elaborate.py::
_elaborate_node` has mapped both straight onto `Node.attrs`'s
`code=<glob>` convention and `Node.may` since then. The corrected
mechanism is exactly the one `_code_binding.py`/`_effects.py` were built
for: declare `code "glob";`/`may "kind";` directly on `design/frob.strata`'s
nodes, then reuse `bind_code` + `check_capability_conformance` (THREAT004)
wherever they already express one of this ticket's three rules.

One real, narrow grammar gap DOES remain and is not fixed here: `store`
declarations (`strata-core/src/parse.rs::parse_store`) do not actually
accept `code`/`may`, despite `docs/strata/surface.md`'s `store_prop :=
node_prop | ...` line claiming otherwise. `design/frob.strata`'s
`tickets_ledger` store therefore declares neither; the CODE that writes to
it (`src/frob/tickets/**`) is folded into the `core` node's `code`/`may`
instead, consistent with `core`'s existing `f_core_tickets: core ->
tickets_ledger` flow. Fixing `parse_store` is a separately-filed,
narrowly-scoped `strata-core` grammar ticket, not part of T-0150.

## The three rules

Unit of "code" for all three rules is a `code=`-bound file, aggregated to
the node level. SYS100's net/fs-write/exec slice and SYS102 reuse
`bind_code`'s existing `FOREIGN` partition; nothing here duplicates
detection THREAT004 already runs.

- **SYS100 undeclared interface.** A capability observed in a node's
  `code=`-bound files but not declared in that node's `may`.
  - net/fs-write/exec: delegated VERBATIM to `check_capability_
    conformance` (THREAT004) -- `_selfconform.py::_core_undeclared_
    violations` just relabels its `CapabilityViolation`s as SYS100. Zero
    new detection for this slice.
  - eval/env/ffi/install-hook: NEW code
    (`_selfconform.py::_extended_kind_violations`). **Gap statement:**
    `_effects.py::_KIND_MAP` is scoped, by its own docstring (T-0079), to
    net/fs-write/exec only -- "eval/env/ffi/install-hook are vet-specific
    dependency-vetting signals with no `may`-capability analog yet" -- so
    THREAT004 structurally cannot see these four kinds no matter what
    `may` declares. `frob.vet._capability.scan_file_capabilities` (already
    imported READ-ONLY by `_effects.py` for the other three kinds) is
    reused directly for these four, joined against `Node.may` via
    `_effects.py::_declared_kinds` (reused, not reimplemented).
- **SYS101 stale design.** A `may` capability declared for a node with
  zero observed sites anywhere in that node's `code=`-bound files, over
  ALL seven kinds. Entirely NEW code (`_selfconform.py::_stale_design_
  violations`). **Gap statement:** no shipped join checks this direction.
  `_effects.py`'s own module docstring says THREAT004 catches "an observed
  effect with no matching `may` declaration" -- singular direction, never
  the reverse; `_threat.py::check_effect_completeness`'s docstring
  confirms THREAT004 is "the code-level `undeclared capability in code is
  an error` kicker", again one-directional.
- **SYS102 unmodeled code.** A `src/frob/` top-level directory whose files
  (if any) are ALL `FOREIGN` to `bind_code`'s partition -- no node's
  `code=` glob claims it at all. Entirely NEW code (`_selfconform.py::
  _unmodeled_violations`). **Gap statement:** `bind_code` computes the
  `FOREIGN` bucket, but `check_import_conformance` explicitly SKIPS
  `FOREIGN` files ("an unclassified file names no kernel node to attest
  the crossing against") rather than flagging them -- correct for ITS
  rule (imports), but it leaves "this whole directory has no owner"
  unraised anywhere. SYS102 is that missing raise.

## Kind-space drift-lock

The net/fs-write/exec vs. eval/env/ffi/install-hook split
(`_selfconform.py::_EXTENDED_KINDS`) is the one fact this module hardcodes
that could silently rot if `_effects.py::_KIND_MAP` ever grows a fourth
key. `tests/unit/strata/test_selfconform.py::
TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map`
asserts `_EXTENDED_KINDS` and `_KIND_MAP`'s keys are disjoint and their
union covers every kind `vet._capability._PATTERNS` actually defines --
if `_KIND_MAP` (THREAT004's scope) ever grows, or `_PATTERNS` grows an
eighth kind neither set accounts for, that test fails first, loudly, in
review.

## First honest run

Running `check_self_conformance` against a `design/frob.strata` with no
`code`/`may` on any node fails SYS102 for every `src/frob/` top-level
directory (nothing is bound, so the whole tree is `FOREIGN`), and both
SYS100 slices and SYS101 are vacuously silent only because there is
nothing to compare -- not proof of conformance. Declaring `code`/`may` on
every real node from a real `scan_file_capabilities` sweep (T-0150's Done
report has the exact measured numbers, corrected once during this
ticket's own rework when a capability the ORIGINAL detection code itself
introduced, `open(` in a since-deleted `frob.toml` reader, stopped being
observed) is what turns the gate green -- honestly, by declaring what the
code actually does, never by narrowing what gets scanned.
