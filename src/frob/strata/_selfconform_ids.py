"""SYS1xx rule-id constants shared across `_selfconform.py`'s split
modules (T-2729 layer 0): the leaf of the split's import graph so that
`_selfconform_kinds.py`, the per-rule-family modules, and `_selfconform.
py`'s own orchestration can all depend on the same rule ids without any
module importing back up into orchestration. See `_selfconform.py`'s
module docstring for what each rule actually checks."""

from __future__ import annotations

# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS100 undeclared interface: a capability
#: observed in a node's `code=`-bound files but not declared in `may`.
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS_UNDECLARED_INTERFACE = "SYS100"
# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS101 stale design: a `may` capability
#: declared for a node but never observed in its `code=`-bound files.
# invariant spec: [INV-026](invariants/INV-026.md)
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS_STALE_DESIGN = "SYS101"
# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS102 unmodeled code: a `src/frob/`
#: directory whose files are all `FOREIGN` to `bind_code`'s partition.
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS_UNMODELED_CODE = "SYS102"
# frob:doc docs/modules/strata.md#sys-cov-coverage-totality-sys103-t-0667
#: `frob sys audit` rule id for SYS103 (SYS-COV) coverage totality
#: (T-0667): a `FOREIGN` file the binding-aware scanner observes at
#: least one capability in, on ANY audited root -- the repo-general form
#: of SYS102's frob-own-tree-only unmodeled-code check.
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS_COVERAGE_TOTALITY = "SYS103"
# frob:doc docs/modules/strata.md#sys105-purpose-contract-t-0669
#: `frob sys audit` rule id for SYS105 (T-0669) purpose contract: a
#: node's declared `purpose=<profile>` attr bounds its allowed observed
#: effect kinds (module docstring's SYS105 section).
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS_PURPOSE_CONTRACT = "SYS105"
# frob:doc docs/modules/strata.md#sys106-binding-totality-t-0670
#: `frob sys audit` rule id for SYS106 (T-0670) binding totality /
#: laundering: a `FOREIGN` file reachable via resolved local imports from
#: a bound node's own files, with an observed capability (module
#: docstring's SYS106 section).
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS_BINDING_TOTALITY = "SYS106"
# frob:doc docs/strata/surface.md#may-scope
#: `frob sys audit` rule id for SYS107 (T-1451) via-less-may-on-a-large-
#: node advisory: a node bound to more than `_LARGE_NODE_FILE_THRESHOLD`
#: real files declaring at least one via-less `may` grant (module
#: docstring's SYS107 section). WARN by default; escalated to ERROR by
#: `[strata] require_may_scope` (`_scope_config.py`).
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS_VIA_LESS_LARGE_NODE = "SYS107"

# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-2224
#: T-2224: the capability atoms SYS107 treats as FAIL-CLOSED regardless
#: of `[strata] require_may_scope` -- a via-less grant on one of these,
#: on a large node, is ALWAYS `Severity.ERROR`
#: (`frob.gates._sys_selfaudit._selfaudit_severity`), never an opt-in
#: advisory. These four atoms let a node run attacker-influenced code
#: (`exec`/`eval`), persist beyond itself (`install-hook`), or cross the
#: language-runtime trust boundary (`ffi`) -- the shape T-1623's threat
#: model names as unacceptable to leave WARN-only indefinitely.
#: `net`/`fs.read`/`fs.write` are deliberately NOT in this set: they stay
#: WARN-appropriate at whole-node breadth per SYS107's existing
#: rationale (module docstring's SYS107 section) -- widening this set to
#: them would be mass unrelated churn across `design/frob.strata`'s
#: existing declarations, exactly what this ticket's own scope note
#: warns against.
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS107_FAIL_CLOSED_ATOMS: frozenset[str] = frozenset(
    {"exec", "eval", "install-hook", "ffi"}
)

# frob:doc docs/strata/surface.md#interface-conformance-mechanical-upkeep-sys104-t-1150
#: `frob sys audit` rule id for SYS108 (T-1624) duplicate interface
#: declaration: a node whose `interface=` attrs name the same symbol more
#: than once (module docstring's SYS108 section). Always ERROR.
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS_DUPLICATE_INTERFACE = "SYS108"

# frob:doc docs/strata/surface.md#sys110-undeclared-intended-surface-t-1629
#: `frob sys audit` rule id for SYS110 (T-1629) undeclared intended
#: surface: a node that has opted into hand-declared `interface=` intent
#: (at least one entry) whose REAL public surface contains a symbol not
#: named there (module docstring's SYS110 section). Always ERROR. SYS109
#: is retired as an id (T-1627, folded into SELFAUDIT001 directly rather
#: than through this module's own `_collect_sys_violations` aggregator);
#: SYS110 continues the sequence here since it IS collected by that
#: aggregator, same family as SYS100-108.
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS_UNDECLARED_INTENDED_SURFACE = "SYS110"

# frob:doc docs/strata/surface.md#sys110-undeclared-intended-surface-t-1629
#: T-1629's OWN migration boundary, hand-typed and disclosed here rather
#: than silently absorbed by the check: these `interface=` blocks predate
#: T-1629 (T-0668/T-1150-era generated MIRRORS, no longer kept in sync
#: since T-1870 deleted the writer) and have real drift against the
#: current tree today (measured directly against this repo's own
#: `design/frob.strata` at T-1629 time -- `frozenset(v.node for v in
#: check_self_conformance(...).danger_ok.violations if v.rule ==
#: SYS_UNDECLARED_INTENDED_SURFACE)`, 734 findings across these 15
#: nodes at T-1629 time). SYS110 is silent for exactly these node ids
#: until a human does the per-node hand-curation pass the module
#: docstring's phased-migration section describes -- shrink this set
#: (never add to it without the same audit) as each node's list is
#: brought current; SYS110 is now LIVE and enforced for every node NOT
#: named here, including the two nodes that already carried a non-empty
#: `interface=` and already conformed at T-1629 time (`checker`, `fleet`
#: -- deliberately not silenced, since enabling enforcement wherever it
#: is already green today is the correct default, not "exempt everything
#: with an interface= block") and `natives` (T-1981: hand-audited, 1
#: real finding -- `CARGO_CACHE_DIRNAME` was a genuine public export
#: (in the module's own `__all__`) missing from `interface=`; added by
#: hand, not regenerated, after confirming a real external consumer
#: (`tests/unit/test_natives_build.py`) actually imports it).
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
SYS110_UNAUDITED_NODES: frozenset[str] = frozenset(
    {
        "cli",
        "core",
        "deploy",
        "gates",
        "graphlang",
        "mutate",
        "refactor",
        "registry_model",
        "security",
        "serve",
        "stratamod",
        "tickets_ledger",
        "verify",
        "vet",
    }
)

#: `src/` subtree self-conformance actually scans -- our own package root
#: (module docstring: `design/frob.strata` models exactly this one tree).
# frob:ticket T-2729
_PACKAGE_ROOT = "src/frob"

# frob:doc docs/strata/surface.md#may-scope
# frob:waive COV007 reason="T-1636: docs/strata/surface.md's may-scope section \
# (T-1440/T-1451) documents the SYS107 via-less-large-node advisory this constant \
# configures -- same T-0524/T-0529 per-symbol architecture-doc precedent every other \
# COV007 waiver in this repo already carries, not accidental drift onto a private \
# symbol"
#: SYS107's default "large node" file-count threshold (T-1451) --
#: deliberately a round, generous number (LARGE001's own file-SIZE
#: threshold precedent, `frob.arch._check_large_file`, is the closest
#: existing analog in this repo for "a size past which a flat/unscoped
#: declaration stops being informative") rather than a data-derived one;
#: `[strata] require_may_scope_threshold` in `frob.toml` overrides it per
#: repo (`_scope_config.py::StrataScopeConfig`).
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
_LARGE_NODE_FILE_THRESHOLD = 20
