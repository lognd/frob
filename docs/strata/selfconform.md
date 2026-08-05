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
`strata-core/src/parse/grammar_node.rs::parse_node` well before this ticket's
merge-base
(`docs/strata/surface.md#node-grammar-implemented-t-0132-closes-the-codemay-gap-t-0136-adds-on-deploy-t-0154-adds-carries-t-0172-adds-managed-t-0174-adds-waive`),
and `_elaborate.py::
_elaborate_node` has mapped both straight onto `Node.attrs`'s
`code=<glob>` convention and `Node.may` since then. The corrected
mechanism is exactly the one `_code_binding.py`/`_effects.py` were built
for: declare `code "glob";`/`may "kind";` directly on `design/frob.strata`'s
nodes, then reuse `bind_code` + `check_capability_conformance` (THREAT004)
wherever they already express one of this ticket's three rules.

This grammar gap has since been fixed (T-0166): `store` declarations
(`strata-core/src/parse/grammar_infra.rs::parse_store`) now DO accept
`code`/`may`, matching `docs/strata/surface.md`'s `store_prop :=
node_prop | ...` line. Before T-0166, `design/frob.strata`'s
`tickets_ledger` store declared neither; the CODE that wrote to it
(`src/frob/tickets/**`) was folded into the `core` node's `code`/`may`
instead as a workaround, consistent with `core`'s existing
`f_core_tickets: core -> tickets_ledger` flow -- see
`docs/strata/surface.md`'s `code`/`may` on `store` section for the
current (post-T-0166) grammar.

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
    (`_selfconform.py::_extended_kind_violations`, `_EXTENDED_KINDS`).
    **Gap statement:** `_effects.py::_KIND_MAP` (7 entries: net-connect,
    net-listen, fs-write, fs-read, exec, env-read, env-write) covers
    net/fs-write/fs-read/exec/env-read/env-write -- `env-read`/`env-write`
    were promoted out of `_EXTENDED_KINDS` into `_KIND_MAP` by T-1075, but
    bare `env` (a handful of registry entries like `sys.exit`/`os._exit`/
    `signal.signal` with no tier-2 `may`-capability analog) stays extended
    -- so THREAT004 structurally cannot see eval/env/ffi/install-hook no
    matter what `may` declares. `frob.vet._capability.scan_file_capabilities` (already
    imported READ-ONLY by `_effects.py` for the other three kinds) is
    reused directly for these, joined against `Node.may` via
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
  <a id="sys101-fully-excluded-nodes"></a>
  **Fully-excluded-node skip (T-0310).** SYS101's "declared but never
  observed" join is a category error for a node whose ENTIRE `code=`
  glob set resolves to `[graph].exclude`'d paths (T-0274): capability
  *observation* already skips excluded files (module docstring above,
  `_sorted_capability_files`), so such a node has provably zero files
  observation could EVER see, excluded or not, forever -- there is
  nothing "stale" about a design that structurally cannot be checked.
  `_selfconform.py::_fully_excluded_node_ids` computes, once per audit,
  which node ids match this: every real (skip-dir-filtered) file the
  node's `code=` globs match is excluded, AND at least one such file
  exists (a glob matching NOTHING at all is a different, pre-existing
  case -- e.g. a typo'd glob or genuinely empty directory -- and still
  fires SYS101 as before, unchanged by this fix). `_stale_design_
  violations` skips any node in that set entirely (no SYS101 finding for
  ANY of its declared capabilities) and logs an INFO line naming the
  node and file count, so the skip is not silently invisible. A node
  with even one NON-excluded observable file is unaffected: SYS101
  still fires normally for any genuinely-unobserved declared capability
  on that node -- only the fully-excluded case is skipped.
  <!-- frob:invariant INV-026 -->
  This does not
  change SYS100 (observed-but-undeclared): the inverse graphite finding
  (`bind_code`/capability binding over-attributing bundled-JS effects to
  a server node by walking raw FS) was ALREADY reconciled by T-0274 --
  `_sorted_capability_files` and `_capability_binding` both honor
  `[graph].exclude`, the SAME exclude source `_fully_excluded_node_ids`
  reuses, so observation and the SYS101 skip are provably consistent
  with each other; there is no separate over-attribution path left to
  fix here.

- **SYS102 unmodeled code.** A `src/frob/` top-level directory whose files
  (if any) are ALL `FOREIGN` to `bind_code`'s partition -- no node's
  `code=` glob claims it at all. Entirely NEW code (`_selfconform.py::
  _unmodeled_violations`). **Gap statement:** `bind_code` computes the
  `FOREIGN` bucket, but `check_import_conformance` explicitly SKIPS
  `FOREIGN` files ("an unclassified file names no kernel node to attest
  the crossing against") rather than flagging them -- correct for ITS
  rule (imports), but it leaves "this whole directory has no owner"
  unraised anywhere. SYS102 is that missing raise.

`check_self_conformance` (the `frob sys audit` entrypoint all three rules
above run through) walks `_sorted_capability_files(root)` -- the
`[graph].exclude`-filtered tree scan every rule's observation is built
from -- exactly ONCE per audit (T-1449). It used to run twice (once
inside `_capability_binding`, again inside `_coverage_totality_
violations`), doubling the walk cost of every single-call audit,
including the two full-repo-scan tests
(`TestRealGateGreen`/`TestCoverageTotality`) whose back-to-back peak
memory/wall time motivated pinning them to one xdist worker
(`tests/unit/strata/test_selfconform.py`). The single walk's file list is
now threaded through both call sites instead of re-derived; no rule's
findings changed, only the redundant I/O.

## may-mutation audit (T-1203)

SYS100/SYS101 prove that today's `design/frob.strata` declarations are
CONSISTENT with today's code -- they say nothing about whether removing a
declaration would actually be CAUGHT. `src/frob/strata/_mutation_audit.py`
(`run_may_mutation_audit`) closes that gap: for every `may` atom on every
node in every loaded model, it checks a mutated in-memory copy of just
that one atom two ways:

- **Deletion** must trip SYS100 (core or extended, `DETECTABLE_KINDS` is
  the exact union of kinds either producer can ever see -- a kind outside
  it is reported as an `UndetectableCapabilityKind` finding rather than
  silently passing) plus, wherever `EXPORT_DETECTABLE_KINDS` claims
  coverage, an independent SECOND detector: `_export.py::
  node_allowed_syscalls`'s generated seccomp allowlist, which joins the
  same `Node.may` tuple through a completely different table
  (`_SECCOMP_KIND_MAP`, keyed on the raw `_may_kind` spelling) -- a
  semantic scanner and an artifact generator sharing no code path, so a
  gap in one cannot hide a matching gap in the other. Today that second
  detector only has real OS-syscall coverage for `exec`/`net`/`fs.read`/
  `fs.write`; every other declared kind (`eval`/`env`/`ffi`/
  `install-hook`/`sql`/`deserialize`/`fetch_url`) has no syscall analog
  and is reported instead as a disclosed `SecondDetectorGap` -- not
  silently claimed as double-detected. Building a real second detector
  for those app-level kinds is a follow-up, not faked here.
- **Substitution** (swapping the atom for an unrelated, detectable kind)
  must trip the SYS100+SYS101 pair -- the original kind now undeclared,
  the substituted kind now declared-but-unobserved.

The harness also asserts the baseline SYS101 count is zero (every `may`
already-observed BEFORE any mutation -- the precondition the whole
guarantee rests on) and is deliberately pre-waiver: it reuses the same
kind-level join functions `check_self_conformance` calls, but never
`_apply_sys_waivers`, so an existing `waive "SYS100:..."` clause on the
real design cannot mask a mutation finding here even though it would
suppress the corresponding live `frob sys audit` finding.

## Kind-space drift-lock

The net-connect/net-listen/fs-write/fs-read/exec vs. eval/env-read/
env-write/ffi/install-hook/sql/deserialize/html_render/fetch_url/
client_storage split (`_selfconform.py::_EXTENDED_KINDS`) is the one fact
this module hardcodes that could silently rot if `_effects.py::_KIND_MAP`
ever grows a new key. `tests/unit/strata/test_selfconform.py::
TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map`
asserts `_EXTENDED_KINDS` and `_KIND_MAP`'s keys are disjoint and their
union covers every kind `vet._capability._PATTERNS` actually defines --
if `_KIND_MAP` (THREAT004's scope) ever grows, or `_PATTERNS` grows a
kind neither set accounts for, that test fails first, loudly, in
review.

T-0771 gave `net` its own precise `net-connect`/`net-listen` scanner
split (the `fs-write`/`fs-read` shape below, applied to `net`) and moved
it OUT of `_EXTENDED_KINDS` into `_KIND_MAP` (`net-connect: net.connect`,
`net-listen: net.listen`) -- `net` is now THREAT004-delegated exactly
like `fs-write`/`fs-read`/`exec`, not a SYS100-extended kind any more.
The same ticket gave `env` a matching `env-read`/`env-write` scanner
split, but LEFT `env` in `_EXTENDED_KINDS` (env-read and env-write both
added there) rather than moving it to `_KIND_MAP` -- env has no tier-2
(THREAT004) `may`-declaration join at all yet, so there is nothing for a
`_KIND_MAP` entry to feed. T-1075 subsequently gave `env-read`/`env-write`
their own real tier-2/THREAT004 wiring (promoted into `_KIND_MAP`, see
above), which retired the transitional `_UNWIRED_ENV_MODE_ALIASES` shim
this section used to describe -- it no longer exists. `env` itself
(the bare, unqualified kind -- `sys.exit`/`os._exit`/`signal.signal`
registry entries with no read/write split) stays in `_EXTENDED_KINDS`,
separate from the env-read/env-write pair.

<a id="fs-read-fs-write"></a>
## `fs-read`/`fs-write`: the read-only filesystem signal (T-0018, graphite adoption)

Before T-0018 the vet scanner had exactly one filesystem kind: `fs`
(normalized from the scanner's `fs-write`, `_effects.py::_KIND_MAP`). A
node whose code only ever READS local files (config loads via `Path.
read_text()`/`json.load()`, no writes anywhere) could declare `may "fs"`
and SYS101 would still fire "declared but never observed" -- the scanner
never emitted the write-derived `fs` kind for a read-only site, forcing a
`waive "SYS101:fs"` naming a real capability the waiver reason had to
apologize for.

`fs-read` is a genuinely NEW, separate `CAPABILITY_KINDS` entry (`frob.
vet._capability_registry`), patterned for real in all four scanned
languages (Python `Path.read_text`/`read_bytes`/`json.load`; TypeScript
`fs.readFile`/`readFileSync`; Rust `fs::read_to_string`/`fs::read`; C/C++
`fread`/`fgets`). It was originally added to `_EXTENDED_KINDS`, but has
since been promoted into `_effects.py::_KIND_MAP` (`fs-read: fs.read`),
so it is now THREAT004-delegated like `fs-write`/`exec`, not a
SYS100-extended kind any more. `DEFAULT_BENIGN_
CAPABILITIES` gained a matching `fs-read` entry so THREAT002 does not
independently flag it (same "no CWE_CATALOG sink for local filesystem
access on its own" reasoning as the existing `fs` entry).

**Backward compatibility.** A pre-existing `may "fs"` declaration
predates the split and meant "any real filesystem access" -- it must not
go stale just because the only real access turns out to be reads. T-0717
retired the old `_alias_legacy_fs_observations` bare-`fs`-aliasing hack
that used to implement this (it no longer exists): `_stale_design_
violations` now judges staleness per DECLARED ATOM via
`expand_declared_kind` (any of the atom's modes observed discharges it) --
a coarse `may "fs"` declaration discharges on EITHER `fs.read`/`fs.write`
being observed, a natural consequence of the generic per-atom join rather
than fs-specific special-casing. This is still scoped to SYS101's
`declared - observed` side; SYS100's `observed - declared` side
(`_extended_kind_violations`/`_core_undeclared_violations`) would
undeclared for the SAME single read observation, a redundant duplicate
finding for one real capability. A node that declares `may "fs-read"`
specifically (the more honest, narrower signal for a genuinely read-only
component) is unaffected by the alias either way -- it already matches
the raw `fs-read` observation directly, and stays stale if only writes
are ever observed (the alias never runs in that direction).

## Waiving a SYS100-102 finding (T-0174)

A SYS100/SYS101/SYS102 finding can be waived like any other `frob sys
audit` finding. SYS100 and SYS101 fire once PER CAPABILITY KIND on a
node, so their `waive` clause MUST name that kind as a sub-target --
`waive "SYS100:net" reason "..." ticket "T-...";` -- a bare `waive
"SYS100"` is an elaborate-time error (T-0174 REJECT round: a bare rule
would blanket-suppress every current and future SYS100 finding on the
node). SYS102 fires once per unmodeled directory (not per node
capability) and keeps the bare-rule form: `waive "SYS102" reason "...";`.
See `docs/strata/waive.md` for the full mechanism (grammar, sub-target
requirement, WAIVED reporting, stale-waiver drift lock).

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
