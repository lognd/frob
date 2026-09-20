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
# see T-2224 for the history behind this
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

# frob:doc \
# docs/modules/gates.md#sys113-a-declaration-glob-matching-zero-files-is-its-own-finding-t-4110h3-10  # noqa: E501
# see T-4110 for the history behind this
SYS_ZERO_MATCH_DECLARATION = "SYS113"

# frob:doc docs/strata/surface.md#sys110-undeclared-intended-surface-t-1629
# see T-1629 for the history behind this
SYS_UNDECLARED_INTENDED_SURFACE = "SYS110"

# frob:doc docs/strata/surface.md#sys110-undeclared-intended-surface-t-1629
# see T-1629 for the history behind this
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

# see T-1636 for the history behind this
_LARGE_NODE_FILE_THRESHOLD = 20
