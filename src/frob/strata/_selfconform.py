"""frob self-conformance: reconcile OUR OWN `src/frob/` capability surface
against the interfaces `design/frob.strata` declares (T-0150,
docs/strata/selfconform.md).

POST-REVIEW REWORK (T-0150 REJECT round): the first version of this
module invented a parallel `frob.toml` node<->path/node<->capability
mapping, on the mistaken belief that `code=`/`may` were not reachable
from `.strata` surface text. They ARE (T-0132, `strata-core/src/parse.rs`
`code STRING+` / `may STRING`, `_elaborate.py::_elaborate_node` maps them
straight onto `Node.attrs`'s `code=<glob>` convention and `Node.may`) --
`design/frob.strata`'s own header comment was simply stale and has been
corrected as part of this rework. This module is now a THIN layer: it
declares `code "..."`/`may "..."` directly on `design/frob.strata`'s
nodes (measured honestly from a real `scan_file_capabilities` sweep, same
numbers as the original version) and reuses the ALREADY-SHIPPED
`bind_code` (T-0078) + `check_capability_conformance`/THREAT004 (T-0079/
T-0113) machinery wherever it already expresses one of this ticket's three
rules. Only what that machinery genuinely cannot express gets new code
here, each with a written gap statement:

SYS100 undeclared interface -- a capability OBSERVED in a node's
`code=`-bound files but not DECLARED in that node's `may` atoms.
  - net/fs-write/exec: DELEGATED to `check_capability_conformance`
    (THREAT004) verbatim, just relabeled SYS100 -- that function already
    computes exactly this join at file:line granularity via `_effects.py`'s
    `_KIND_MAP`/`_line_effects`, zero new detection.
  - eval/env/ffi/install-hook: NEW code (`_extended_kind_violations`).
    GAP STATEMENT: `_effects.py::_KIND_MAP` is scoped (by its own
    docstring, T-0079) to net/fs-write/exec only -- "eval/env/ffi/
    install-hook are vet-specific dependency-vetting signals with no
    `may`-capability analog yet" -- so THREAT004 structurally cannot see
    these four kinds no matter what `may` declares. `scan_file_
    capabilities` (vet's own per-file scanner, already imported
    READ-ONLY by `_effects.py` for the other three kinds) is reused
    directly for these four, at file granularity, joined against
    `Node.may` via `_effects.py::_declared_kinds` (reused, not
    reimplemented).

SYS101 stale design -- a capability DECLARED in a node's `may` atoms with
zero observed sites anywhere in that node's `code=`-bound files. NEW code
for ALL kinds. GAP STATEMENT: neither `check_capability_conformance` nor
any other shipped join checks this direction -- THREAT004's `_effects.py`
module docstring is explicit that "an observed effect with no matching
`may` declaration is a violation... not a silent pass" is the ONLY
direction it discharges; a declared-but-unexercised capability is not a
concept the tier-2 machinery has ever computed. `check_effect_
completeness`'s own docstring (`_threat.py`) confirms this: THREAT004 is
"the code-level `undeclared capability in code is an error` kicker",
singular direction.

SYS102 unmodeled code -- a `src/frob/` top-level directory whose `.py`
files are ALL bound to `FOREIGN` (or entirely absent from `bind_code`'s
partition) -- i.e. no node's `code=` glob claims it at all. NEW code.
GAP STATEMENT: `bind_code` computes the FOREIGN bucket but nothing
downstream currently treats "this directory is entirely FOREIGN" as a
reportable finding; `check_import_conformance` explicitly SKIPS FOREIGN
files ("an unclassified file names no kernel node to attest the
crossing against") rather than flagging them, which is correct for ITS
rule (imports) but leaves "a whole directory has no owner" unraised
anywhere -- exactly the gap this ticket asked SYS102 to close.

SYS103 (SYS-COV, T-0667) coverage totality -- every file with an OBSERVED
capability effect (`scan_file_capabilities`, T-0328's import/binding-
aware resolver, not a bare substring guess) that is `FOREIGN` to the
`_capability_binding` partition. NEW code (`_coverage_totality_
violations`). GAP STATEMENT: SYS102 already flags every `FOREIGN` file
under `src/frob/` (capable or not), but it is HARDCODED to `_PACKAGE_ROOT`
("src/frob") -- module docstring's own T-0211 note: "every OTHER repo
running `frob sys audit` structurally lacks `src/frob/` by design", so
SYS102 is silent by construction on any tree that is not frob's own. The
T-0341 epic's coverage-totality acceptance criterion ("every deployable/
public module -- and every module the binding-aware scanner finds ANY
capability in -- must bind to exactly one strata node; unbound-but-
capable code is a hard failure") needs to hold for ANY audited repo, not
just frob's own -- `docs/design/structural-linter-adversarial-hardening.md`
draws the "like COV001 for docs" analogy: a capable module that escapes
the model is exactly as unacceptable as an undocumented public symbol.
SYS103 is that root-general form: it runs over the SAME `_capability_
binding` superset (any root, any repo layout) and fires ONLY for a
`FOREIGN` file the scanner observes at least one capability in -- a
`FOREIGN` file with zero observed capabilities (a pure-data module, an
`__init__.py` with nothing but re-exports) is not dangerous code escaping
an obligation, so SYS103 stays silent for it exactly as SYS-COV's own
acceptance criterion requires ("every module bound to a node" is silent;
narrower still, a capability-free FOREIGN file was never the threat this
rule exists to catch). SYS102 is UNCHANGED and still runs alongside
SYS103 for frob's own tree -- SYS103 does not replace it, it closes the
gap SYS102's `_PACKAGE_ROOT` scope leaves on every OTHER repo.

SYS104 (T-0668) exact interface conformance -- a node's declared
`interface=<symbol>` attrs (this ticket's convention, same "opaque attr
string" mechanism `code=`/`managed` already use, T-0078/T-0172; no
grammar change) must EQUAL the union of top-level public symbols
(`__all__` if the module declares one, else every non-underscore-prefixed
module-level `def`/`class`/assignment target) across the node's own
`code=`-bound `.py` files. Fires TWO ways: a declared symbol absent from
the real surface (`docs/design/structural-linter-adversarial-hardening.md`
"declared-but-absent declaration" row), and a real public symbol the node
never declared (the same doc's "undeclared public surface" row --
`secret_backdoor` example). MANDATORY as of T-1113 (closes the T-0668
disclosed opt-in scope cut): every node whose bound code has a non-empty
real public surface is now evaluated, whether or not it has declared any
`interface=` attr yet -- `design/frob.strata` itself now carries a real,
measured `interface=` declaration for every node with a non-empty surface
(one `attr interface=<symbol>;` per real public name, generated from the
same `_module_public_symbols`/`_node_real_public_surface` this check
uses, so declared and real agree by construction at the point they were
added). A node with an EMPTY real surface (no bound `.py` files, or files
with nothing public) stays exempt either way -- there is no obligation to
declare an interface for code that exports nothing. Python-only, same
boundary `bind_code` itself already draws (module docstring above).

SYS105 (T-0669) purpose contract -- a node's declared `purpose=<profile>`
attr (same opaque-attr convention, at most one per node) names a fixed,
closed vocabulary of allowed-effect profiles (`_PURPOSE_PROFILES`); any
observed effect kind (the SAME `_observed_raw_kinds_by_node`/
`_all_kinds_view` union SYS101 already computes) outside the declared
profile's allowed set fires. An unrecognized profile name is itself a
finding (a typo'd purpose is not silently permissive). Disclosed scope
cut, UNCHANGED by T-1113 (which flipped only SYS104 to mandatory, per its
own declared follow-up): only a node that HAS declared a `purpose=` attr
is checked; making every node declare one is a disclosed follow-up, not
forced here.

SYS106 (T-0670) binding totality / laundering -- code laundered into an
unbound (`FOREIGN`) file that is nonetheless *reachable* (via resolved
local python imports, `_code_binding.py::resolve_local_import`, followed
transitively) from a bound node's own files. SYS103 already flags any
`FOREIGN` file with an observed capability over its own scan (whole
root, unconditionally, as of T-1091 -- `_coverage_totality_scan_prefix`'s
own docstring has the T-0667-restricted-then-dropped history); SYS106
closes the specific evasion the design doc names ("binding need not be
total, so logic can be laundered into an unbound file") by following the
REACHABILITY edge itself, which stays independently useful even now that
SYS103 itself is unrestricted: SYS103 only fires when it actually WALKS
to a capable FOREIGN file, whereas SYS106 fires from the opposite
direction (starting at a bound node and following its real import
edges), so a file some future exclude-glob or walk boundary hides from
SYS103's own walk but that a bound node still imports at runtime is
still caught. Cycle-safe (visited-set BFS over resolved import targets).

SYS107 (T-1451) via-less-may-on-a-large-node advisory -- a node whose
`code=` glob(s) bind more than `_LARGE_NODE_FILE_THRESHOLD` real files but
declares at least one `may` atom with NO `via` (a T-1440 whole-node
grant) is an advisory (WARN by default) finding: the bigger a node's
bound surface, the less a whole-node grant actually tells a reviewer
about which files really need the capability, and the more valuable
narrowing it to `via` globs would be. Deliberately WARN, not ERROR, by
default (an advisory nudge toward scoping, not a new hard requirement on
every pre-existing declaration) -- `[strata] require_may_scope` in
`frob.toml` (`_scope_config.py`) escalates it to ERROR for a repo whose
owner is ready to commit. GAP STATEMENT: nothing else in this module (or
`_effects.py`) evaluates a node's OWN size against its grants' `via`
coverage -- SYS100/SYS101 both join declared-vs-observed per file or per
node, never asking whether a via-less grant's blast radius is large
enough to be worth narrowing at all.
"""

from __future__ import annotations

import ast
import fnmatch
import os
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs, walk_pruned
from frob.lang import resolve_local_import
from frob.logging import get_logger
from frob.vet._capability import (
    is_self_pattern_path,
    language_for,
    scan_file_capabilities,
)
from frob.vet._capability_modes import canonical_declared_kind, expand_declared_kind

from ._code_binding import (
    FOREIGN,
    CodeBinding,
    _node_code_globs,
    _python_imports_with_lines,
    bind_code,
)
from ._effects import (
    _KIND_MAP,
    _declared_kinds,
    _may_kind,
    _via_matches,
    check_capability_conformance,
)
from ._errors import StrataError
from ._models import KernelModel
from ._scope_config import load_strata_scope_config
from ._waive import (
    CONFORMANCE_WAIVER_EXPIRED_RULE,
    STALE_WAIVER_RULE,
    WaiverApplication,
    _split_waiver_rule,
    _stale_detail,
    apply_waivers,
    parse_waiver_expiry,
)

_log = get_logger(__name__)

# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS100 undeclared interface: a capability
#: observed in a node's `code=`-bound files but not declared in `may`.
SYS_UNDECLARED_INTERFACE = "SYS100"
# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS101 stale design: a `may` capability
#: declared for a node but never observed in its `code=`-bound files.
# invariant spec: [INV-026](invariants/INV-026.md)
SYS_STALE_DESIGN = "SYS101"
# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS102 unmodeled code: a `src/frob/`
#: directory whose files are all `FOREIGN` to `bind_code`'s partition.
SYS_UNMODELED_CODE = "SYS102"
# frob:doc docs/modules/strata.md#sys-cov-coverage-totality-sys103-t-0667
#: `frob sys audit` rule id for SYS103 (SYS-COV) coverage totality
#: (T-0667): a `FOREIGN` file the binding-aware scanner observes at
#: least one capability in, on ANY audited root -- the repo-general form
#: of SYS102's frob-own-tree-only unmodeled-code check.
SYS_COVERAGE_TOTALITY = "SYS103"
# frob:doc docs/modules/strata.md#sys104-interface-conformance-t-0668
#: `frob sys audit` rule id for SYS104 (T-0668) exact interface
#: conformance: a node's declared `interface=<symbol>` attrs must equal
#: its bound files' real public surface (module docstring's SYS104
#: section) -- fires for either direction of mismatch.
SYS_INTERFACE_CONFORMANCE = "SYS104"
# frob:doc docs/modules/strata.md#sys105-purpose-contract-t-0669
#: `frob sys audit` rule id for SYS105 (T-0669) purpose contract: a
#: node's declared `purpose=<profile>` attr bounds its allowed observed
#: effect kinds (module docstring's SYS105 section).
SYS_PURPOSE_CONTRACT = "SYS105"
# frob:doc docs/modules/strata.md#sys106-binding-totality-t-0670
#: `frob sys audit` rule id for SYS106 (T-0670) binding totality /
#: laundering: a `FOREIGN` file reachable via resolved local imports from
#: a bound node's own files, with an observed capability (module
#: docstring's SYS106 section).
SYS_BINDING_TOTALITY = "SYS106"
# frob:doc docs/strata/surface.md#may-scope
#: `frob sys audit` rule id for SYS107 (T-1451) via-less-may-on-a-large-
#: node advisory: a node bound to more than `_LARGE_NODE_FILE_THRESHOLD`
#: real files declaring at least one via-less `may` grant (module
#: docstring's SYS107 section). WARN by default; escalated to ERROR by
#: `[strata] require_may_scope` (`_scope_config.py`).
SYS_VIA_LESS_LARGE_NODE = "SYS107"

#: `src/` subtree self-conformance actually scans -- our own package root
#: (module docstring: `design/frob.strata` models exactly this one tree).
_PACKAGE_ROOT = "src/frob"

# frob:doc docs/strata/surface.md#may-scope
#: SYS107's default "large node" file-count threshold (T-1451) --
#: deliberately a round, generous number (LARGE001's own file-SIZE
#: threshold precedent, `frob.arch._check_large_file`, is the closest
#: existing analog in this repo for "a size past which a flat/unscoped
#: declaration stops being informative") rather than a data-derived one;
#: `[strata] require_may_scope_threshold` in `frob.toml` overrides it per
#: repo (`_scope_config.py::StrataScopeConfig`).
_LARGE_NODE_FILE_THRESHOLD = 20

#: The vet capability kinds THREAT004's `_effects.py::_KIND_MAP` has no
#: tier-2 analog for (module docstring's SYS100 gap statement) -- the ONLY
#: kinds this module's own file-level scan needs to cover, since net/fs-
#: write/exec are fully delegated to `check_capability_conformance`. T-0158
#: adds `sql`/`deserialize`/`html_render`/`fetch_url`/`client_storage`: new
#: `CAPABILITY_KINDS` the structured dangerous-operations registry patterns
#: that likewise have no `_KIND_MAP` tier-2 analog.
_EXTENDED_KINDS = frozenset(
    {
        "eval",
        #: T-1075: `env-read`/`env-write` are REMOVED from here (but bare
        #: `env` STAYS -- see below) -- `env-read`/`env-write` now have a
        #: real tier-2/THREAT004 analog (`_effects.py::_KIND_MAP`
        #: normalizes them to `env.read`/`env.write`, and `env` joined
        #: `WIRED_MODE_FAMILIES`), so `check_capability_conformance`
        #: (SYS100 core) covers those two precise kinds exactly like
        #: `fs-read`/`fs-write`/`net`/`exec` already do -- double-scanning
        #: them here too would be the same mistake `fs-read`'s own T-0717
        #: promotion comment warns against just above.
        "env",
        #: Bare `env` is UNRELATED to the env-read/env-write split just
        #: above despite the shared string: it is a handful of registry
        #: entries (`sys.exit`/`os._exit`, `signal.signal`) tagging
        #: process-lifecycle/signal-handling operations, never an actual
        #: environment-variable read or write -- `_capability_registry.py`
        #: never promoted these to `env-read`/`env-write` because they are
        #: not that. Removing bare `env` here (only `env-read`/`env-write`)
        #: would leave these registry entries with NO extended-kinds home
        #: at all, silently dropping SYS100 coverage for them -- confirmed
        #: by `TestDeployServeMutateNodeSplitConformance`'s own real-code
        #: fixture failing the drift-lock union check when this was tried.
        "ffi",
        "install-hook",
        "sql",
        "deserialize",
        "html_render",
        "fetch_url",
        "client_storage",
        #: T-0018 added `fs-read` here as a bespoke extended kind ahead of
        #: a real mode vocabulary; T-0717 promotes it into `_effects.py::
        #: _KIND_MAP` (as `fs.read`) instead, alongside `fs-write`'s new
        #: `fs.write` spelling -- it now has a real tier-2/THREAT004
        #: analog (this module's SYS100 gap statement no longer applies to
        #: it) and is REMOVED from here so it is not double-scanned by two
        #: independent, differently-normalized code paths.
    }
)


# frob:doc docs/strata/selfconform.md#the-three-rules
class SelfConformViolation(BaseModel):
    """One SYS100/SYS101/SYS102 finding: rule id, the node (or directory,
    for SYS102) it concerns, a human-readable detail string, and (SYS100/
    SYS101 only) the capability kind this specific instance fired for.
    `capability` is T-0174's multi-instance sub-target: SYS100/SYS101 can
    each fire more than once per node (once per capability kind), so a
    `waive` clause targeting one of them must name a sub-target
    (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`) and matching needs a
    structured field to compare against -- never parsed back out of
    `detail`'s free text."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    capability: str | None = None


# frob:doc docs/strata/selfconform.md#the-three-rules
class SelfConformReport(BaseModel):
    """Every UNWAIVED self-conformance violation, in rule-then-node order
    (module docstring), plus `waived` (T-0174: findings suppressed by a
    matching `waive` clause, kept here for report visibility -- never
    silently dropped, `_waive.py` module docstring). A stale waiver (its
    `(node, rule)` matched zero findings) is folded back INTO `violations`
    as a `SYSWAIVE002` entry rather than a separate field, so the existing
    `not selfconform.danger_ok.violations` gate condition (`sys_runner.py::
    _run_audit`) fails closed on drift without a second check to forget."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SelfConformViolation, ...] = ()
    waived: tuple[SelfConformViolation, ...] = ()


def _core_undeclared_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS100 for net/fs-write/exec, delegated verbatim to THREAT004's
    `check_capability_conformance` -- zero new detection (module
    docstring's SYS100 core case). REVIEWER-CAUGHT T-0169 CORRECTION: this
    function does no language filtering itself -- it only ever sees what
    `binding` puts in front of it. Earlier in this same ticket, the caller
    passed `bind_code`'s raw Python-only binding here on the mistaken
    belief that `check_capability_conformance` was Python-import-syntax-
    specific like `bind_code`'s OWN binding step is. It is not:
    `_effects.py::_line_effects`/`check_capability_conformance` call
    `language_for`/`_PATTERNS` directly, the SAME multi-language
    (python/typescript/rust/c-cpp) machinery `vet._capability` and this
    module's SYS100-extended/SYS101 already use -- there is no Python-
    specific parsing anywhere in this delegated path. So `check_self_
    conformance` now passes THIS function the same `_capability_binding`
    superset as the other two rules, and a `.ts`/`.rs`/`.c`/`.cpp` file's
    raw net/fs-write/exec effects reach SYS100 exactly like a `.py`
    file's do."""
    conformance = check_capability_conformance(model, binding, root)
    return [_core_undeclared_violation(v) for v in conformance.violations]


def _core_undeclared_violation(violation) -> SelfConformViolation:  # noqa: ANN001
    """Build the SYS100 finding for one THREAT004 conformance violation,
    split out of `_core_undeclared_violations` purely to keep its loop
    body short."""
    _log.warning(
        "selfconform: SYS100 (via THREAT004) %s:%d %s effect on %s",
        violation.file,
        violation.line,
        violation.kind,
        violation.component,
    )
    return SelfConformViolation(
        rule=SYS_UNDECLARED_INTERFACE,
        node=violation.component,
        detail=(
            f"capability {violation.kind!r} observed at "
            f"{violation.file}:{violation.line} but not declared"
        ),
        capability=violation.kind,
    )


def _sorted_owned_files(binding: CodeBinding) -> list[str]:
    """Every non-`FOREIGN` bound file path, in deterministic order
    (mirrors `_effects.py::_sorted_owned_files`)."""
    return sorted(rel for rel, owner in binding.owner.items() if owner != FOREIGN)


def _sorted_capability_files(root: Path) -> list[Path]:
    """Every file under `root` whose extension `vet._capability.language_for`
    recognizes (i.e. has a capability pattern table), skip-dir- AND
    `[graph].exclude`-filtered (T-0274), in deterministic path order
    (T-0169: the multi-language superset of `bind_code`'s `.py`-only walk
    -- `bind_code` itself stays Python-only since it also powers import-
    conformance, which is Python-syntax-specific; capability *observation*
    has no such constraint)."""
    exclude_globs = load_exclude_globs(root)
    found: list[Path] = []
    for path in sorted(walk_pruned(root, exclude_globs=exclude_globs)):
        if language_for(path) is None:
            continue
        found.append(path)
    return found


def _capability_binding(
    model: KernelModel, binding: CodeBinding, root: Path
) -> Result[CodeBinding, StrataError]:
    """`binding` (Python-only, from `bind_code`) extended with every OTHER
    capability-scannable-language file under `root`, bound by the SAME
    `code=` glob convention (T-0169 GAP STATEMENT: `bind_code` walks only
    `*.py` -- module docstring/T-0078 -- because it also backs import-
    conformance, which needs Python's import syntax specifically; that
    scope choice silently meant SYS100/SYS101 never saw a single TS/JS/
    Rust/C-C++ file either, even though `vet._capability` has scanned
    those languages since T-0079/T-0158. This function is the fix: it
    re-runs `bind_code`'s glob-match (via `_node_code_globs`, reused not
    reimplemented) over the non-`.py` capability-scannable file set, deny-
    by-default on ambiguity exactly like `bind_code`, and merges the
    result into `binding.owner` so every downstream SYS100/SYS101 join in
    this module sees every registry-covered language, not just Python)."""
    globs = [(node.id, glob) for node in model.nodes for glob in _node_code_globs(node)]
    owner = dict(binding.owner)
    for path in _sorted_capability_files(root):
        if path.suffix.lower() == ".py":
            continue  # already bound by `bind_code`
        rel = path.relative_to(root).as_posix()
        bound_id = _match_capability_owner(rel, globs)
        if bound_id.is_err:
            return Err(bound_id.danger_err)
        owner[rel] = bound_id.danger_ok
    bound = sum(1 for v in owner.values() if v != FOREIGN) - sum(
        1 for v in binding.owner.values() if v != FOREIGN
    )
    _log.info("capability binding: %d additional non-python file(s) bound", bound)
    return Ok(CodeBinding(owner=owner))


def _match_capability_owner(
    rel: str, globs: list[tuple[str, str]]
) -> Result[str, StrataError]:
    """The owning node id for `rel` against `globs` (`(node_id, glob)`
    pairs), `FOREIGN` if none match, deny-by-default on ambiguity -- split
    out of `_capability_binding` purely to keep its loop body short."""
    matched = {node_id for node_id, glob in globs if fnmatch.fnmatch(rel, glob)}
    if len(matched) > 1:
        _log.error(
            "capability binding: %s matched by multiple nodes %s",
            rel,
            tuple(sorted(matched)),
        )
        return Err(StrataError.AmbiguousCodeBinding)
    return Ok(next(iter(matched)) if matched else FOREIGN)


def _observed_raw_kinds_by_file(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every owned file (`rel` path) -> the RAW `scan_file_capabilities`
    output for that ONE file (no `_EXTENDED_KINDS` filter, no `_KIND_MAP`
    normalization) -- the SINGLE per-file scan pass every other observed-
    kinds view in this module (per-node aggregate via
    `_observed_raw_kinds_by_node`, and T-1450's per-via `_stale_design_
    violations` join) derives from, so `scan_file_capabilities` still
    only ever runs once per owned file (H5/T-0830's single-scan property,
    now anchored at file granularity instead of node granularity so a
    per-`via`-surface join has something to narrow). `binding` here is
    ALWAYS the T-0169 `_capability_binding` superset, never the raw
    `.py`-only `bind_code` output -- see that function's docstring. Skips
    `is_self_pattern_path` files (T-0201): a pattern-catalog data file's
    needle literals are not code exercising the capability, the same
    self-match class `frob.vet._capability`'s own aggregation excludes."""
    per_file: dict[str, frozenset[str]] = {}
    for rel in _sorted_owned_files(binding):
        path = root / rel
        if is_self_pattern_path(path, root):
            continue
        found = scan_file_capabilities(path)
        if found:
            per_file[rel] = frozenset(found)
    return per_file


def _aggregate_raw_kinds_by_node(
    binding: CodeBinding, raw_by_file: dict[str, frozenset[str]]
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of an already-scanned `raw_by_file`
    map's values across that node's owned files -- the per-node
    aggregation step split out of `_observed_raw_kinds_by_node` (T-1450)
    so a caller that also needs the per-file map (the per-via SYS101 join)
    can compute the file-level scan once and derive both views from it,
    instead of `_observed_raw_kinds_by_node` re-scanning independently."""
    per_node: dict[str, set[str]] = {}
    for rel, kinds in raw_by_file.items():
        owner = binding.owner[rel]
        per_node.setdefault(owner, set()).update(kinds)
    return {node_id: frozenset(kinds) for node_id, kinds in per_node.items()}


def _observed_raw_kinds_by_node(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of RAW `scan_file_capabilities` output
    (no `_EXTENDED_KINDS` filter, no `_KIND_MAP` normalization) across
    that node's `code=`-bound files -- the SINGLE per-file scan pass
    `_observed_extended_kinds_by_node` and `_observed_all_kinds_by_node`
    both derive their view from (H5/T-0830: each owned file used to be
    scanned TWICE, once per view, via two independent copies of this same
    loop; deriving both cheap set views from one raw scan halves the
    per-file resolution work `scan_file_capabilities` does). `binding`
    here is ALWAYS the T-0169 `_capability_binding` superset, never the
    raw `.py`-only `bind_code` output -- see that function's docstring.
    T-1450: now a thin wrapper over `_observed_raw_kinds_by_file` +
    `_aggregate_raw_kinds_by_node` for standalone callers -- the hot path
    (`_collect_sys_violations`) calls the file-level scan directly and
    aggregates itself so it can also hand the per-file map to the SYS101
    per-via join, without a second scan."""
    return _aggregate_raw_kinds_by_node(
        binding, _observed_raw_kinds_by_file(binding, root)
    )


def _extended_kinds_view(
    raw_by_node: dict[str, frozenset[str]],
) -> dict[str, frozenset[str]]:
    """`_EXTENDED_KINDS`-filtered view of an already-scanned raw per-node
    observed-kinds map (T-0830): derives SYS100-extended's vocabulary from
    `_observed_raw_kinds_by_node`'s single scan instead of re-scanning
    every owned file. Only includes a node when its filtered set is
    non-empty, matching the original per-file `if found:` guard. T-1075:
    no longer folds `env-read`/`env-write` through `_UNWIRED_ENV_MODE_
    ALIASES` (removed) -- `env` is no longer in `_EXTENDED_KINDS` at all
    (promoted to the tier-2 `_KIND_MAP` join, `_all_kinds_view` below), so
    this view naturally stops seeing it, same as `fs-read`'s own T-0717
    promotion."""
    return {
        node_id: extended
        for node_id, raw_kinds in raw_by_node.items()
        if (extended := raw_kinds & _EXTENDED_KINDS)
    }


def _all_kinds_view(
    raw_by_node: dict[str, frozenset[str]],
) -> dict[str, frozenset[str]]:
    """`_KIND_MAP`-normalized view of an already-scanned raw per-node
    observed-kinds map (T-0830): derives SYS101's full vocabulary
    (net/fs-write/fs-read/exec/env-read/env-write normalized to the
    precise, mode-qualified spelling `may` declarations resolve to,
    T-0717/T-1075) from `_observed_raw_kinds_by_node`'s single scan
    instead of re-scanning every owned file. Only includes a node with a
    non-empty raw set, matching the original per-file `if normalized:`
    guard (normalizing elementwise never turns a non-empty set empty).
    T-1075: no longer folds `env-read`/`env-write` through `_UNWIRED_ENV_
    MODE_ALIASES` (removed) -- both are now real `_KIND_MAP` keys, so
    `_KIND_MAP.get` alone normalizes them to `env.read`/`env.write`
    exactly like every other wired kind."""
    return {
        node_id: frozenset(_KIND_MAP.get(kind, kind) for kind in kinds)
        for node_id, kinds in raw_by_node.items()
        if kinds
    }


# frob:tests tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock.test_observed_extended_kinds_by_node_only_ever_yields_extended_kinds  # noqa: E501
def _observed_extended_kinds_by_node(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of `_EXTENDED_KINDS` capabilities
    `scan_file_capabilities` observes across that node's `code=`-bound
    files (module docstring's SYS100 extended case). `binding` here is
    ALWAYS the T-0169 `_capability_binding` superset, never the raw
    `.py`-only `bind_code` output -- see that function's docstring. Skips
    `is_self_pattern_path` files (T-0201): a pattern-catalog data file's
    needle literals are not code exercising the capability, the same
    self-match class `frob.vet._capability`'s own aggregation excludes.
    T-0830: a thin wrapper over `_observed_raw_kinds_by_node` +
    `_extended_kinds_view` for standalone callers -- the hot path
    (`_collect_sys_violations`) calls those two directly so this view and
    `_observed_all_kinds_by_node`'s share ONE scan of the owned-file set,
    not two."""
    return _extended_kinds_view(_observed_raw_kinds_by_node(binding, root))


# frob:tests tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock.test_observed_all_kinds_by_node_normalizes_through_kind_map  # noqa: E501
def _observed_all_kinds_by_node(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of ALL vet capability kinds observed
    across its bound files, net/fs-write/fs-read/exec normalized through
    `_effects.py::_KIND_MAP` to the SAME precise, mode-qualified spelling
    `may` declarations resolve to (`fs.write`/`fs.read`, T-0717) -- SYS101's
    observed side, which (unlike SYS100) needs the full vocabulary
    regardless of THREAT004's scope. `binding` here is the T-0169
    `_capability_binding` superset (see that function's docstring), so
    SYS101 stale-design also covers every registry-scanned language, not
    just Python. Skips `is_self_pattern_path` files (T-0201), same
    self-match exclusion as `_observed_extended_kinds_by_node` -- SYS101's
    declared-but-unobserved direction must not see a pattern catalog's own
    literals as "observed" either, or a real declaration gets masked by
    self-match noise on the OPPOSITE side of the join. T-0717: the old
    `_alias_legacy_fs_observations` bare-`fs`-aliasing hack is REMOVED --
    `_stale_design_violations` now judges staleness per DECLARED ATOM via
    `expand_declared_kind` (any of its modes observed discharges it), so no
    special-casing is needed on the observed side at all. T-0830: a thin
    wrapper over `_observed_raw_kinds_by_node` + `_all_kinds_view` for
    standalone callers -- see `_observed_extended_kinds_by_node`'s
    docstring for why the hot path bypasses both wrappers."""
    return _all_kinds_view(_observed_raw_kinds_by_node(binding, root))


def _extended_kind_violations(
    model: KernelModel, observed_by_node: dict[str, frozenset[str]]
) -> list[SelfConformViolation]:
    """SYS100 for eval/env/ffi/install-hook/sql/deserialize/html_render/
    fetch_url/client_storage -- the slice `check_capability_conformance`
    structurally cannot see (module docstring's SYS100 gap statement).
    T-0717: `fs-read` moved OUT of `_EXTENDED_KINDS` into `_effects.py::
    _KIND_MAP` (it now has a real tier-2/THREAT004 analog as `fs.read`),
    so this function no longer needs a bare-`fs`-covers-`fs-read` special
    case -- `_declared_kinds` already expands a coarse `may "fs"`
    declaration to `{fs.read, fs.write}` generically (`expand_declared_
    kind`), and `_dedupe_sys100_extended_against_core` keeps the core
    (THREAT004-delegated) pass as the single source of truth for it.
    T-0830: `observed_by_node` is precomputed by the caller (an
    `_extended_kinds_view` derivation) instead of this function scanning
    the owned-file set itself, so `_collect_sys_violations` can share ONE
    raw scan with `_stale_design_violations` instead of two independent
    passes."""
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        declared = _declared_kinds(node) & _EXTENDED_KINDS
        observed = observed_by_node.get(node.id, frozenset())
        # frob:waive PERF004 reason="distinct small per-node diff set, not repeated"
        for kind in sorted(observed - declared):
            _log.warning(
                "selfconform: SYS100 (extended) %s observed but undeclared on %s",
                kind,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_UNDECLARED_INTERFACE,
                    node=node.id,
                    detail=f"capability {kind!r} observed but not declared",
                    capability=kind,
                )
            )
    return found


# frob:ticket T-0361
def _repo_files_excluding_skip_dirs(root: Path) -> list[str]:
    """Every real file under `root`, as `root`-relative posix paths, with
    any path whose parts include a skip-dir (`is_skipped_dir`) omitted;
    split out of `_fully_excluded_node_ids`'s file-collection phase
    (T-0361)."""
    # Deliberately skip-dir-only pruning (no [graph].exclude): the SYS101
    # caller needs the pre-exclude file set to compare against is_excluded()
    # per-glob itself, so this cannot route through walk_pruned's
    # exclude_globs=() (which would fall back to loading frob.toml's
    # globs and collapse that distinction). Still prunes mid-descent via
    # os.walk's dirnames mutation, same as walk_pruned, just on a narrower
    # predicate.
    all_files: list[str] = []
    # frob:waive WALK001 reason="deliberately skip-dir-only, no [graph].exclude pruning -- the SYS101 caller needs the pre-exclude file set to compare against is_excluded() per-glob itself; walk_pruned's exclude_globs=() default would load frob.toml globs and collapse that distinction. Still prunes mid-descent via dirnames mutation, same shape as walk_pruned, just a narrower predicate"  # noqa: E501
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not is_skipped_dir(d)]
        current = Path(dirpath)
        for name in filenames:
            all_files.append((current / name).relative_to(root).as_posix())
    return sorted(all_files)


# frob:ticket T-0310
def _fully_excluded_node_ids(model: KernelModel, root: Path) -> frozenset[str]:
    """Node ids whose ENTIRE `code=` glob set resolves to `[graph].exclude`'d
    paths (T-0310, docs/strata/selfconform.md#sys101-fully-excluded-nodes):
    SYS101's 'declared but never observed' is a category error for such a
    node -- capability observation already skips excluded files (this
    module's `_sorted_capability_files`/`_capability_binding`, T-0274), so
    there is provably no file, excluded or not, observation could EVER see.
    A node qualifies only if its glob matches at least one REAL (skip-dir-
    filtered) file AND every such match is excluded -- a glob matching
    nothing at all is a different, pre-existing case (e.g. a typo'd glob)
    left to fire SYS101 unchanged, since that is genuine potential drift,
    not a structurally-unobservable node. Uses the SAME exclude source
    (`load_exclude_globs`/`is_excluded`) `_sorted_capability_files` already
    uses for observation, so observation and this skip cannot diverge."""
    exclude_globs = load_exclude_globs(root)
    if not exclude_globs:
        return frozenset()
    all_files = _repo_files_excluding_skip_dirs(root)
    fully_excluded: set[str] = set()
    for node in model.nodes:
        globs = _node_code_globs(node)
        if not globs:
            continue
        matched = [
            rel for rel in all_files if any(fnmatch.fnmatch(rel, g) for g in globs)
        ]
        if not matched:
            continue  # glob matches nothing at all -- unaffected, not this fix's target
        if all(is_excluded(rel, exclude_globs) for rel in matched):
            fully_excluded.add(node.id)
            _log.info(
                "selfconform: SYS101 skip: node %s code= glob resolves entirely "
                "to graph-excluded paths (%d file(s)); capability declarations "
                "unverifiable",
                node.id,
                len(matched),
            )
    return frozenset(fully_excluded)


def _raw_declared_kinds(node) -> frozenset[str]:  # noqa: ANN001
    """Every RAW (un-expanded, un-canonicalized) capability kind `node`'s
    `may` atoms name -- `_stale_design_violations`'s per-atom granularity
    needs the ORIGINAL spelling (`"fs"`, `"fs-read"`, `"fs.read"`, ...) so
    a waiver naming `SYS101:fs` still matches and a finding's `detail`
    still reads the declaration the author actually wrote, never a
    post-expansion synthetic id."""
    return frozenset(_may_kind(atom) for atom in node.may)


def _node_owned_files(binding: CodeBinding, node_id: str) -> list[str]:
    """Every owned file (`rel` path) `binding` binds to `node_id` -- T-1450's
    per-grant SYS101 join narrows this by a grant's own `via` globs, so it
    needs the node's owned-file set directly rather than the already-
    aggregated per-node kind union `observed_by_node` used to hand it."""
    return sorted(rel for rel, owner in binding.owner.items() if owner == node_id)


def _observed_kinds_for_files(
    files: list[str], all_kinds_by_file: dict[str, frozenset[str]]
) -> frozenset[str]:
    """The union of `all_kinds_by_file`'s (already `_KIND_MAP`-normalized,
    T-1450) values across `files` -- shared by a via-less grant's whole-
    node join and a `via`-scoped grant's narrowed join, the only
    difference between the two being which file list is passed in."""
    observed: set[str] = set()
    for rel in files:
        observed |= all_kinds_by_file.get(rel, frozenset())
    return frozenset(observed)


def _stale_grant_violation(
    node_id: str, raw_kind: str, via: tuple[str, ...]
) -> SelfConformViolation:
    """Build one SYS101 finding for a declared-but-unobserved atom, split
    out of `_stale_design_violations_for_node` (T-1450) purely to keep its
    loop body short. `via`, when present, is folded into `detail` so the
    finding names the specific surface that failed to discharge it -- not
    just the node, which per-via staleness (unlike the old whole-node
    join) can no longer imply on its own."""
    _log.warning(
        "selfconform: SYS101 %s declared but never observed on %s%s",
        raw_kind,
        node_id,
        f" via {list(via)}" if via else "",
    )
    detail = f"capability {raw_kind!r} declared but never observed"
    if via:
        detail += f" via {', '.join(via)}"
    return SelfConformViolation(
        rule=SYS_STALE_DESIGN,
        node=node_id,
        detail=detail,
        capability=raw_kind,
    )


def _stale_design_violations_for_node(
    node,  # noqa: ANN001
    binding: CodeBinding,
    all_kinds_by_file: dict[str, frozenset[str]],
) -> list[SelfConformViolation]:
    """One node's SYS101 findings (T-1450): iterates `node.may_grants`
    (populated for every parsed `may` clause, with or without `via` --
    `strata-core/src/parse/grammar_node.rs`) rather than the flat, kind-
    deduped `_raw_declared_kinds(node)` set the old whole-node join used,
    so a `via`-scoped grant is judged only against the files its own glob
    covers while a via-less grant on the SAME kind keeps the old whole-
    node join -- the exact "a dead grant on one file is flagged even
    while another file legitimately uses the same kind" acceptance clause
    this ticket exists for. `node.may_grants` empty entirely (a `Node`
    built directly, bypassing the parser -- most unit-test fixtures) falls
    back to the pre-T-1450 whole-node-only join over
    `_raw_declared_kinds`, an exact behavior-preserving path (mirrors
    `_effects.py::_declared_kinds_for_file`'s own legacy fallback)."""
    owned_files = _node_owned_files(binding, node.id)
    whole_node_observed = _observed_kinds_for_files(owned_files, all_kinds_by_file)
    found: list[SelfConformViolation] = []
    if not node.may_grants:
        # frob:waive PERF004 reason="distinct small per-node diff set, not repeated"
        for raw_kind in sorted(_raw_declared_kinds(node)):
            canonical = canonical_declared_kind(raw_kind)
            expanded = expand_declared_kind(canonical)
            if expanded & whole_node_observed:
                continue
            found.append(_stale_grant_violation(node.id, raw_kind, ()))
        return found
    seen: set[tuple[str, tuple[str, ...]]] = set()
    # frob:waive PERF004 reason="distinct small per-node grant list, not repeated"
    for grant in node.may_grants:
        raw_kind = _may_kind(grant.atom)
        key = (raw_kind, grant.via)
        if key in seen:
            continue  # duplicate (kind, via) grant -- already judged
        seen.add(key)
        if grant.via:
            matched_files = [rel for rel in owned_files if _via_matches(rel, grant.via)]
            observed = _observed_kinds_for_files(matched_files, all_kinds_by_file)
        else:
            observed = whole_node_observed
        canonical = canonical_declared_kind(raw_kind)
        expanded = expand_declared_kind(canonical)
        if expanded & observed:
            continue
        found.append(_stale_grant_violation(node.id, raw_kind, grant.via))
    return found


# frob:invariant INV-026
# frob:tests tests/unit/strata/test_selfconform.py::TestStaleDesign.test_stale_design_skips_node_fully_within_graph_exclude  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestStaleDesign.test_via_scoped_grant_stale_while_other_surface_uses_same_kind  # noqa: E501
def _stale_design_violations(
    model: KernelModel,
    root: Path,
    binding: CodeBinding,
    all_kinds_by_file: dict[str, frozenset[str]],
) -> list[SelfConformViolation]:
    """SYS101 over every kind (net/fs/exec included) -- new code, since no
    shipped join checks this direction (module docstring's SYS101 gap
    statement). T-0310: skips any node in `_fully_excluded_node_ids` --
    a node whose entire code-glob set is graph-excluded has nothing
    observable, so 'declared but never observed' is a category error, not
    real design drift (docs/strata/selfconform.md#sys101-fully-excluded-nodes).

    T-0717: judged PER RAW DECLARED ATOM, not over the flat expanded-kind
    set difference -- a declared atom is stale only if NONE of the precise
    modes it covers (`expand_declared_kind`) was ever observed. This is
    what makes a precise `may "fs.read"` declaration discharge NARROWLY
    (acceptance clause 1: only `fs.read` itself can satisfy it) while a
    coarse `may "fs"` declaration keeps discharging on EITHER mode being
    observed (mandate point 2/old `_alias_legacy_fs_observations`
    backward-compat behavior, now a natural consequence of this generic
    per-atom join rather than fs-specific code).

    T-1450: judged PER MAY-VIA SURFACE, not per whole-node kind -- delegated
    to `_stale_design_violations_for_node` per node (see its docstring for
    the per-grant join and the legacy whole-node fallback). `binding` is
    the T-0169 capability-binding superset (needed to resolve each node's
    owned-file set for the per-`via` narrowing); `all_kinds_by_file` is
    precomputed by the caller (an `_all_kinds_view` derivation over
    `_observed_raw_kinds_by_file`, T-0830's single-scan discipline
    extended to file granularity) instead of this function scanning the
    owned-file set itself -- see `_extended_kind_violations`'s docstring
    for why."""
    skip_nodes = _fully_excluded_node_ids(model, root)
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        if node.id in skip_nodes:
            continue
        found.extend(
            _stale_design_violations_for_node(node, binding, all_kinds_by_file)
        )
    return found


# frob:tests tests/unit/strata/test_selfconform.py::TestCoverageTotality.test_foreign_file_with_capability_fires_sys103  # noqa: E501
def _coverage_totality_scan_prefix(root: Path) -> str | None:
    """UNRESTRICTED as of T-1091: always returns `None` -- SYS103 scans
    `root` in full on every tree, frob's own included, with no
    `_PACKAGE_ROOT` carve-out. Kept as a named function (rather than
    inlining `None` at its one call site) so its docstring stays the
    single place this history lives, and so a future re-restriction (if
    one is ever needed) has an obvious hook to land on.

    HISTORY (why this used to restrict, and why that is now safe to
    drop): T-0667 shipped SYS103 scoped to `_PACKAGE_ROOT` ("src/frob")
    on frob's own tree specifically, because an unrestricted `root`-wide
    walk surfaced 264 real, then-unmodeled findings under `tests/**`,
    `scripts/**`, `frob-core/src/**`, `strata-core/src/**` --
    `design/frob.strata` only ever declared `code=`/`may` for `src/frob/`
    at that point (same T-0211 fact SYS102 already lived with), so
    wiring SYS103 unrestricted then would have regressed the live
    `SELFAUDIT001` gate from green to 264 errors. T-1079 closed that gap
    directly: `design/frob.strata` now models `tests/**` (`testsuite`),
    `scripts/**` (`scripts_ops`), `frob-core/src/**`
    (`frob_core_native`), and `strata-core/src/**` (`strata_core_native`)
    as real nodes with real `code=` bindings, so those 264 files are no
    longer `FOREIGN` at all -- `TestCoverageTotality::
    test_repo_unrestricted_scan_is_clean` (T-1079) already proved a
    prefix-bypassed scan against the live repo returns zero findings.
    T-1091 makes that the LIVE gate's own behavior, not just a test
    harness's: dropping the `_PACKAGE_ROOT` carve-out here means
    `SELFAUDIT001` now checks exactly what `design/frob.strata` claims to
    cover (the WHOLE repo), closing the gap for real. If a genuinely new,
    still-unmodeled tree is ever added back to this repo, SYS103 will
    correctly regress to non-zero on that tree -- that is the point of
    the rule, not a bug in this change."""
    return None


# frob:invariant INV-048
# invariant spec: [INV-048](invariants/INV-048.md)
# frob:tests tests/unit/strata/test_selfconform.py::TestCoverageTotality.test_foreign_file_with_capability_fires_sys103  # noqa: E501
def _coverage_totality_violations(
    capability_binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS103 (SYS-COV, T-0667, unrestricted as of T-1091): every
    `FOREIGN` file under `root` whose `root`-relative path starts with
    `_coverage_totality_scan_prefix(root)` (ALWAYS the whole root now --
    see that function's docstring for the T-0667-restricted-then-T-1091-
    dropped history) that `scan_file_capabilities` observes ANY
    capability in.
    `is_self_pattern_path` files are skipped
    (T-0201, same self-match exclusion every other observed-side join in
    this module already applies) -- a pattern-catalog data file's needle
    literals are not code exercising a capability. One finding per
    FOREIGN file, `capability` set to the sorted, comma-joined kind list
    observed there, folded into `detail` only -- `capability` (the
    `apply_waivers` sub-target field) is left `None`, exactly like
    SYS102's findings, since SYS103 has no per-kind waiver granularity of
    its own (the whole FILE is unbound, not one specific capability kind
    of it) and is NOT in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`;
    setting `capability` here would make a bare `waive "SYS103"` clause
    (sub_target=None) never match a finding whose computed sub_target is
    a non-None kind string -- `_apply_sys_waivers` below relies on this
    staying `None`.

    Deliberately walks `_sorted_capability_files(root)` directly rather
    than `capability_binding.owner.items()`: `bind_code` takes a fast
    path when NO node in the whole model declares any `code=` glob at
    all (`globs` empty) and returns an entirely EMPTY owner mapping -- no
    file gets a `FOREIGN` entry, not just no bound ones -- which would
    silently blind a dict-keyed join to every file in that degenerate-
    but-real state (a model with zero `code=` declarations, e.g. before
    anyone has written any, is exactly the un-modeled case SYS-COV exists
    to catch, not a state it can afford to go quiet in). Reading
    `capability_binding.owner.get(rel, FOREIGN)` per real file sidesteps
    that gap: a file absent from the mapping is treated identically to
    one explicitly marked `FOREIGN`, which is what its absence always
    means."""
    found: list[SelfConformViolation] = []
    prefix = _coverage_totality_scan_prefix(root)
    for path in _sorted_capability_files(root):
        rel = path.relative_to(root).as_posix()
        if prefix is not None and not rel.startswith(prefix):
            continue
        owner = capability_binding.owner.get(rel, FOREIGN)
        if owner != FOREIGN:
            continue
        if is_self_pattern_path(path, root):
            continue
        kinds = scan_file_capabilities(path)
        if not kinds:
            continue
        capability = ", ".join(sorted(kinds))
        _log.warning(
            "selfconform: SYS103 (SYS-COV) unbound-but-capable %s (%s)",
            rel,
            capability,
        )
        found.append(
            SelfConformViolation(
                rule=SYS_COVERAGE_TOTALITY,
                node=rel,
                detail=(
                    f"{rel} has an observed capability ({capability}) but no "
                    "node's code= glob binds it"
                ),
            )
        )
    return found


#: Node attr prefix for a SYS104 (T-0668) declared-interface entry (one
#: attr per declared public symbol name), mirroring `_code_binding.py`'s
#: `code=<glob>` attr-string convention (module docstring's SYS104
#: section).
_INTERFACE_PREFIX = "interface="

#: Node attr prefix for a SYS105 (T-0669) declared purpose profile (at
#: most one per node), same opaque-attr convention.
_PURPOSE_PREFIX = "purpose="

#: SYS105's fixed, closed allowed-effect-profile vocabulary (module
#: docstring's SYS105 section): profile name -> the set of observed effect
#: kinds (the SAME normalized vocabulary `_observed_all_kinds_by_node`
#: yields) that profile permits. `"full"` is the explicit opt-out --
#: still requires declaring a purpose (so a node cannot hide behind
#: silence), but permits every observed kind.
_PURPOSE_PROFILES: dict[str, frozenset[str] | None] = {
    "pure": frozenset(),
    "read-only": frozenset({"fs.read", "net.connect", "env.read"}),
    "logging": frozenset({"fs.write"}),
    "network": frozenset({"net.connect", "net.listen", "fetch_url"}),
    "full": None,  # None = no restriction (explicit opt-out)
}


def _node_attr_values(node, prefix: str) -> list[str]:  # noqa: ANN001
    """Every `node.attrs` entry's tail past `prefix`, in declaration order
    -- the same opaque-attr-string convention `_code_binding.py::
    _node_code_globs` reads for `code=`, generalized to `interface=`/
    `purpose=` so SYS104/SYS105 do not duplicate the split logic."""
    return [attr[len(prefix) :] for attr in node.attrs if attr.startswith(prefix)]


def _module_public_symbols(path: Path) -> frozenset[str] | None:
    """The real top-level public symbol set of one `.py` file: `__all__`'s
    string-literal entries if the module declares one, else every
    non-underscore-prefixed module-level `def`/`class`/plain-assignment
    target name. `None` on a parse failure (deny-by-default: the caller
    treats an unparseable file as contributing nothing rather than
    crashing the whole SYS104 pass, same posture `_parse_ast` establishes
    in `_code_binding.py`)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, OSError, UnicodeDecodeError) as exc:
        _log.warning("selfconform: SYS104 could not parse %s: %s", path, exc)
        return None
    all_literal = _module_all_literal(tree)
    if all_literal is not None:
        return all_literal
    names: set[str] = set()
    for stmt in tree.body:
        names |= _public_names_of_statement(stmt)
    return frozenset(names)


def _module_all_literal(tree: ast.Module) -> frozenset[str] | None:
    """`__all__`'s string-literal entries if `tree` assigns it a plain
    list/tuple of string constants at module level, else `None` (no
    `__all__`, or one this static pass cannot resolve -- falls back to
    name-based public-symbol collection, never crashes)."""
    for stmt in tree.body:
        if not (
            isinstance(stmt, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__all__" for t in stmt.targets)
        ):
            continue
        if not isinstance(stmt.value, (ast.List, ast.Tuple)):
            return None
        names: set[str] = set()
        for elt in stmt.value.elts:
            if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
                return None
            names.add(elt.value)
        return frozenset(names)
    return None


def _public_names_of_statement(stmt: ast.stmt) -> frozenset[str]:
    """The public (non-underscore-prefixed) top-level name(s) one module
    body statement introduces -- `def`/`class`/plain assignment targets --
    split out of `_module_public_symbols` purely to keep its loop body
    short."""
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return frozenset({stmt.name}) if not stmt.name.startswith("_") else frozenset()
    if isinstance(stmt, ast.Assign):
        return frozenset(
            t.id
            for t in stmt.targets
            if isinstance(t, ast.Name) and not t.id.startswith("_")
        )
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        name = stmt.target.id
        return frozenset({name}) if not name.startswith("_") else frozenset()
    return frozenset()


def _node_real_public_surface(
    binding: CodeBinding, root: Path, node_id: str
) -> frozenset[str]:
    """The union of `_module_public_symbols` across every `.py` file
    `binding` binds to `node_id` -- SYS104's real (ground-truth) side."""
    surface: set[str] = set()
    for rel in sorted(binding.owner):
        if binding.owner[rel] != node_id or not rel.endswith(".py"):
            continue
        found = _module_public_symbols(root / rel)
        if found is not None:
            surface |= found
    return frozenset(surface)


# frob:tests tests/unit/strata/test_selfconform.py::TestInterfaceConformance.test_undeclared_public_symbol_fires  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestInterfaceConformance.test_declared_but_absent_symbol_fires  # noqa: E501
def _interface_conformance_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS104 (T-0668, mandatory as of T-1113): for every node whose
    `code=`-bound `.py` files expose at least one real public symbol, the
    declared `interface=` set must equal that real public surface (module
    docstring's SYS104 section). T-1113 closes the original opt-in scope
    cut (T-0668's disclosed follow-up): a node is now evaluated whenever
    its REAL surface is non-empty, not only when it has already declared
    at least one `interface=` attr -- a node with zero declared attrs and
    a non-empty real surface now fires (every real symbol reports as
    missing), same as before for any node that already declares some but
    not all of its surface. A node with an empty real surface (no bound
    `.py` files, or files with nothing public) stays silent either way --
    there is no obligation to declare an interface for code that exports
    nothing."""
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        declared = frozenset(_node_attr_values(node, _INTERFACE_PREFIX))
        real = _node_real_public_surface(binding, root, node.id)
        if not declared and not real:
            continue  # nothing declared, nothing real to declare
        for missing in sorted(real - declared):
            _log.warning(
                "selfconform: SYS104 undeclared public symbol %s on %s",
                missing,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_INTERFACE_CONFORMANCE,
                    node=node.id,
                    detail=(
                        f"public symbol {missing!r} exported by code but not "
                        "declared in interface="
                    ),
                    capability=missing,
                )
            )
        for absent in sorted(declared - real):
            _log.warning(
                "selfconform: SYS104 declared-but-absent symbol %s on %s",
                absent,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_INTERFACE_CONFORMANCE,
                    node=node.id,
                    detail=(
                        f"interface= declares {absent!r} but no bound file exports it"
                    ),
                    capability=absent,
                )
            )
    return found


# frob:tests tests/unit/strata/test_selfconform.py::TestPurposeContract.test_effect_outside_profile_fires  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestPurposeContract.test_unrecognized_profile_fires  # noqa: E501
def _purpose_contract_violations(
    model: KernelModel, observed_by_node: dict[str, frozenset[str]]
) -> list[SelfConformViolation]:
    """SYS105 (T-0669): for every node declaring a `purpose=` attr, every
    observed effect kind must lie inside that profile's allowed set
    (`_PURPOSE_PROFILES`, module docstring's SYS105 section). An
    unrecognized profile name is itself a finding -- a typo must not read
    as a silently-permissive `"full"`."""
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        declared = _node_attr_values(node, _PURPOSE_PREFIX)
        if not declared:
            continue  # SYS105 scope cut: opt-in only, see module docstring
        profile = declared[0]
        allowed = _PURPOSE_PROFILES.get(profile)
        if profile not in _PURPOSE_PROFILES:
            _log.warning(
                "selfconform: SYS105 unrecognized purpose profile %r on %s",
                profile,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_PURPOSE_CONTRACT,
                    node=node.id,
                    detail=f"purpose={profile!r} is not a recognized profile",
                )
            )
            continue
        if allowed is None:
            continue  # "full" -- explicit opt-out, no restriction
        observed = observed_by_node.get(node.id, frozenset())
        for kind in sorted(observed - allowed):
            _log.warning(
                "selfconform: SYS105 %s effect outside purpose=%s on %s",
                kind,
                profile,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_PURPOSE_CONTRACT,
                    node=node.id,
                    detail=(
                        f"effect {kind!r} observed outside purpose={profile!r}'s "
                        "allowed profile"
                    ),
                    capability=kind,
                )
            )
    return found


def _reachable_local_files(start_files: list[str], root: Path) -> frozenset[str]:
    """BFS closure of every in-repo `.py` file reachable from `start_files`
    via resolved local python imports (`frob.lang.resolve_local_import`),
    visited-set guarded against import cycles -- SYS106's "reachable from
    a bound node" side (module docstring's SYS106 section).

    T-1208: calls `_code_binding._python_imports_with_lines` directly
    (memoized there via `_IMPORT_MEMO`) instead of parsing `path` itself
    and re-deriving imports with a local duplicate walk -- `check_import_
    conformance` (SYS003) parses this SAME ~800-file set in the SAME `frob
    sys` run, so sharing the one memo means the run parses each file once,
    not twice."""
    visited: set[str] = set(start_files)
    queue: list[str] = list(start_files)
    while queue:
        rel = queue.pop()
        path = root / rel
        for spec, _line in _python_imports_with_lines(path, root):
            dst = resolve_local_import(spec, "python", file_dir=path.parent, root=root)
            if dst is None or dst in visited:
                continue
            visited.add(dst)
            queue.append(dst)
    return frozenset(visited)


# frob:tests tests/unit/strata/test_selfconform.py::TestBindingTotality.test_laundered_capable_file_fires  # noqa: E501
def _binding_totality_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS106 (T-0670): a `FOREIGN` file reachable (via resolved local
    imports, `_reachable_local_files`) from ANY bound node's own files,
    that `scan_file_capabilities` observes a capability in -- "logic
    laundered into an unbound file" (module docstring's SYS106 section).
    One finding per such file (not per reaching node -- the file itself is
    the escaping unit, and could be reached from more than one node)."""
    bound_files = [
        rel
        for rel, owner in binding.owner.items()
        if owner != FOREIGN and rel.endswith(".py")
    ]
    if not bound_files:
        return []
    reachable = _reachable_local_files(bound_files, root)
    found: list[SelfConformViolation] = []
    for rel in sorted(reachable):
        if binding.owner.get(rel, FOREIGN) != FOREIGN:
            continue
        path = root / rel
        if is_self_pattern_path(path, root):
            continue
        kinds = scan_file_capabilities(path)
        if not kinds:
            continue
        capability = ", ".join(sorted(kinds))
        _log.warning(
            "selfconform: SYS106 laundered capable file %s (%s) reachable "
            "from bound code",
            rel,
            capability,
        )
        found.append(
            SelfConformViolation(
                rule=SYS_BINDING_TOTALITY,
                node=rel,
                detail=(
                    f"{rel} has an observed capability ({capability}), is "
                    "reachable from bound code via local imports, but no "
                    "node's code= glob binds it"
                ),
            )
        )
    return found


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1451
def _node_real_code_file_count(binding: CodeBinding, node_id: str) -> int:
    """The number of real (owned, non-`FOREIGN`) files `binding` binds to
    `node_id` -- SYS107's own "how large is this node's blast radius"
    measure, split out purely so `_via_less_large_node_violations`'s loop
    body stays short. Reuses `binding.owner` directly (already computed by
    the caller's `_capability_binding` pass) rather than re-walking
    `node.attrs`'s `code=` globs -- an owned-file count, not a glob count,
    is what actually determines how much a whole-node grant covers."""
    return sum(1 for owner in binding.owner.values() if owner == node_id)


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1451
# frob:tests tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory.test_via_less_grant_on_large_node_fires  # noqa: E501
# frob:tests tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory.test_via_less_grant_on_small_node_is_silent  # noqa: E501
# frob:tests tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory.test_via_scoped_grant_on_large_node_is_silent  # noqa: E501
def _via_less_large_node_violations(
    model: KernelModel, binding: CodeBinding, threshold: int
) -> list[SelfConformViolation]:
    """SYS107 (T-1451, module docstring's SYS107 section): a node bound to
    more than `threshold` real files that declares at least one via-less
    `may` grant is an advisory finding. Judged per NODE, not per grant (one
    finding per offending node, not one per via-less atom) -- the point is
    "this node is big enough that its whole-node grants are worth
    narrowing", a property of the node's size, not of any one atom.
    `node.may_grants` empty entirely (a `Node` built directly, bypassing
    the parser) is treated as "every declared `may` is via-less" (the
    pre-T-1440 meaning `MayGrant.via=()` formalizes), so this still fires
    correctly for a hand-built `Node` fixture with a flat `may` tuple and
    no `may_grants` at all."""
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        if not node.may:
            continue
        file_count = _node_real_code_file_count(binding, node.id)
        if file_count <= threshold:
            continue
        has_via_less = not node.may_grants or any(
            not grant.via for grant in node.may_grants
        )
        if not has_via_less:
            continue
        _log.warning(
            "selfconform: SYS107 via-less may grant on large node %s (%d files > "
            "threshold %d)",
            node.id,
            file_count,
            threshold,
        )
        found.append(
            SelfConformViolation(
                rule=SYS_VIA_LESS_LARGE_NODE,
                node=node.id,
                detail=(
                    f"node {node.id!r} binds {file_count} file(s) (> {threshold}) "
                    "and declares at least one via-less may grant -- consider "
                    "narrowing it with via"
                ),
            )
        )
    return found


def _top_level_dirs(root: Path) -> list[str]:
    """Every immediate, non-skipped subdirectory name of `root / _PACKAGE_ROOT`
    (module docstring's SYS102 unit of "unmodeled code"), in sorted order.
    T-0211: `_PACKAGE_ROOT` ("src/frob") is frob's OWN package layout, not a
    general convention -- SYS102 only makes sense when auditing frob's own
    repo (module docstring: `design/frob.strata` models exactly this one
    tree). Every OTHER repo running `frob sys audit` structurally lacks
    `src/frob/` by design, not by drift, so that absence is an expected,
    silent no-op (empty SYS102 finding set) here -- previously this logged
    at WARNING unconditionally, which fired in every non-frob repo on every
    audit run and read as "the self-conformance proof is vacuous" even
    though the other checks (SYS100/SYS101/exhaustiveness) genuinely ran
    (filed from sibling-repo pilot P2, tickets.md T-0211). DEBUG here (not
    silence outright) still leaves a trace for anyone diagnosing frob's own
    SYS102 detection, without alarming operators of unrelated repos."""
    package_root = root / _PACKAGE_ROOT
    if not package_root.is_dir():
        _log.debug(
            "selfconform: %s does not exist -- not the frob repo (or repo "
            "root mismatch); skipping SYS102 unmodeled-code check",
            package_root,
        )
        return []
    return sorted(
        entry.name
        for entry in package_root.iterdir()
        if entry.is_dir() and not is_skipped_dir(entry.name)
    )


def _package_relative(binding: CodeBinding) -> list[tuple[str, str, str]]:
    """`(rel, tail, owner)` for every `binding.owner` entry under
    `_PACKAGE_ROOT`, where `tail` is `rel` with the `src/frob/` prefix
    stripped -- the common slice `_unmodeled_violations`'s three passes
    (loose top-level files, fully-foreign directories, foreign files
    inside a partially-owned directory) all need, hoisted so each pass is
    a plain filter over the same precomputed list rather than
    re-deriving `tail` three times (charter: no duplication)."""
    out: list[tuple[str, str, str]] = []
    for rel, owner in binding.owner.items():
        if not rel.startswith(f"{_PACKAGE_ROOT}/"):
            continue
        out.append((rel, rel[len(_PACKAGE_ROOT) + 1 :], owner))
    return out


def _loose_foreign_file_violations(
    relative: list[tuple[str, str, str]],
) -> list[SelfConformViolation]:
    """G4 (docs/audits/strata.md): a `.py`/`.ts`/etc. file placed DIRECTLY
    under `src/frob/` (no subdirectory) that no node's `code=` glob
    claims. `_top_level_dirs` (below) only ever iterates DIRECTORIES
    (`entry.is_dir()`), so a loose top-level file was invisible to SYS102
    no matter what it did -- and, being `FOREIGN`, invisible to SYS100/
    SYS101 too (module docstring: those only reconcile bound files)."""
    found: list[SelfConformViolation] = []
    for rel, tail, owner in sorted(relative):
        if "/" in tail or owner != FOREIGN:
            continue
        _log.warning("selfconform: SYS102 unmodeled loose file %s", rel)
        found.append(
            SelfConformViolation(
                rule=SYS_UNMODELED_CODE,
                node=rel,
                detail=f"{rel} has no node's code= glob binding it",
            )
        )
    return found


def _fully_foreign_dir_violations(
    root: Path, owned_dirs: frozenset[str]
) -> list[SelfConformViolation]:
    """SYS102 original case: a whole top-level `src/frob/` directory with
    no file owned by any node's `code=` glob (module docstring's SYS102
    gap statement)."""
    found: list[SelfConformViolation] = []
    for name in _top_level_dirs(root):
        if name in owned_dirs:
            continue
        _log.warning("selfconform: SYS102 unmodeled code src/frob/%s", name)
        found.append(
            SelfConformViolation(
                rule=SYS_UNMODELED_CODE,
                node=name,
                detail=f"src/frob/{name} has no node's code= glob binding it",
            )
        )
    return found


def _foreign_file_in_owned_dir_violations(
    relative: list[tuple[str, str, str]], owned_dirs: frozenset[str]
) -> list[SelfConformViolation]:
    """G4 (docs/audits/strata.md): a file inside an OTHERWISE-owned
    top-level directory that no node's `code=` glob actually matches.
    Before this, `_unmodeled_violations` marked a whole directory "owned"
    the moment ANY file in it was non-`FOREIGN` (`prefix_owned`/
    `owned_dirs` below) -- so a stray unglobbed file dropped into an
    already-modeled directory was invisible to SYS102 (its directory is
    not fully foreign) AND invisible to SYS100/SYS101 (it is `FOREIGN`,
    so no node's capability set is ever joined against it). This fires
    per such file, at file granularity, so "the directory has an owner"
    can no longer hide "this ONE file does not"."""
    found: list[SelfConformViolation] = []
    for rel, tail, owner in sorted(relative):
        if "/" not in tail or owner != FOREIGN:
            continue
        top = tail.split("/", 1)[0]
        if top not in owned_dirs:
            continue  # the fully-foreign-directory pass already covers this file
        _log.warning(
            "selfconform: SYS102 unmodeled file %s in otherwise-modeled directory "
            "src/frob/%s",
            rel,
            top,
        )
        found.append(
            SelfConformViolation(
                rule=SYS_UNMODELED_CODE,
                node=rel,
                detail=(
                    f"{rel} has no node's code= glob binding it (directory "
                    f"src/frob/{top} is otherwise modeled)"
                ),
            )
        )
    return found


def _unmodeled_violations(
    root: Path, binding: CodeBinding
) -> list[SelfConformViolation]:
    """SYS102: every `src/frob/` file (loose top-level, or inside a
    directory) that no node's `code=` glob binds -- module docstring's
    SYS102 gap statement, tightened by G4 (docs/audits/strata.md) to fire
    per-FOREIGN-file rather than only per fully-FOREIGN top-level
    directory (`_fully_foreign_dir_violations`'s original grain missed
    both a stray file in an otherwise-modeled directory and a file placed
    directly under `src/frob/` with no subdirectory at all -- see
    `_foreign_file_in_owned_dir_violations`/`_loose_foreign_file_
    violations`'s docstrings for each gap). `binding` is the T-0169
    `_capability_binding` superset here, not `bind_code`'s raw `.py`-only
    output: a directory containing ONLY a `.ts`/`.rs`/etc. file that a
    node's `code=` glob genuinely claims used to misreport SYS102
    ("unmodeled") because the Python-only binding never bound that file
    at all -- a spurious finding on top of the missed SYS100/SYS101, now
    fixed by using the same superset every other rule in this module
    uses."""
    relative = _package_relative(binding)
    owned_dirs = frozenset(
        tail.split("/", 1)[0]
        for _, tail, owner in relative
        if "/" in tail and owner != FOREIGN
    )
    return [
        *_fully_foreign_dir_violations(root, owned_dirs),
        *_foreign_file_in_owned_dir_violations(relative, owned_dirs),
        *_loose_foreign_file_violations(relative),
    ]


# frob:doc docs/strata/selfconform.md#the-three-rules
# frob:enforces CHK-GATE-SYS100
# frob:enforces CHK-GATE-SYS101
# frob:enforces CHK-GATE-SYS102
# SYS103 edge added at T-0667's coordinator close-out, once the registry
# entry existed and SYS103 registered in the live rule set (the follow-up
# T-0667's Done report deferred).
# frob:enforces CHK-GATE-SYS103
# T-1113: CHK-GATE-SYS104/105/106 registry entries added alongside the
# SYS104 opt-in-to-mandatory flip, mirroring the CHK-GATE-SYS103
# precedent above.
# frob:enforces CHK-GATE-SYS104
# frob:enforces CHK-GATE-SYS105
# frob:enforces CHK-GATE-SYS106
# frob:enforces CHK-SUBSYS-STRATA
# T-0672: SLH-SYS-EVA-* edges bind this function directly to the
# structural-linter-adversarial-hardening.md denominator rows T-0668/
# T-0669/T-0670 close (docs/design/registry/arch-checks.yaml's
# `handled_by:SYS100`/`SYS104`/`SYS105`/`SYS106` dispositions).
# frob:enforces SLH-SYS-EVA-01-UNMODELED-MODULE
# frob:enforces SLH-SYS-EVA-02-UNDER-DECLARED-CAPABILITY
# frob:enforces SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE
# frob:enforces SLH-SYS-EVA-04-PURPOSE-DRIFT
# frob:enforces SLH-SYS-EVA-05-BINDING-LAUNDERING
def check_self_conformance(
    model: KernelModel, root: Path
) -> Result[SelfConformReport, StrataError]:
    """The `frob sys audit` self-conformance entrypoint (T-0150): `bind_code`
    (T-0078, reused verbatim) partitions `src/frob/` by each node's `code=`
    glob, then SYS100/SYS101/SYS102 reconcile that partition against
    `Node.may` (module docstring: SYS100's net/fs-write/exec slice
    delegates to THREAT004 outright; the rest is new code with a written
    gap statement each). ALL THREE rules run over `_capability_binding`'s
    superset (T-0169), not `bind_code`'s raw `.py`-only partition:
    `check_capability_conformance` (SYS100 core's delegate) is language-
    generic (`_effects.py::_line_effects` uses `language_for`/`_PATTERNS`,
    no Python-specific parsing), so restricting it to the Python-only
    binding was itself part of the same wiring bug this ticket fixes (see
    `_core_undeclared_violations`'s docstring). SYS102 also uses the
    superset for its ownership check, so a directory claimed only through
    a non-Python file no longer misreports as unmodeled (see
    `_unmodeled_violations`'s docstring). `bind_code`'s raw Python-only
    binding remains the ONLY input to `bind_code` itself (Python-import-
    syntax-specific by design) -- it is simply no longer handed to any
    SYS100/SYS101/SYS102 join. `Err` propagates `bind_code`'s (or
    `_capability_binding`'s) `AmbiguousCodeBinding` unchanged -- deny by
    default, never a silent partial scan."""
    bound_binding = _bind_conformance_inputs(model, root)
    if bound_binding.is_err:
        return Err(bound_binding.danger_err)
    capability_binding = bound_binding.danger_ok

    violations = _collect_sys_violations(model, capability_binding, root)
    applied = _apply_sys_waivers(model, violations)
    applied = _apply_conformance_waiver_staleness(applied)
    return Ok(_finalize_self_conform_report(applied, root))


#: SYS104/SYS105/SYS106 -- the conformance-obligation waiver families
#: T-0671's staleness gate applies to (module docstring's T-0671
#: section). SYS100-103 are UNCHANGED: their own bounded-escape-hatch
#: treatment is out of this ticket's scope (T-0341's acceptance
#: criterion [4] names "interface/purpose/binding waivers" specifically,
#: the three conformance checks T-0668/T-0669/T-0670 just built).
_CONFORMANCE_WAIVER_RULES: frozenset[str] = frozenset(
    {SYS_INTERFACE_CONFORMANCE, SYS_PURPOSE_CONTRACT, SYS_BINDING_TOTALITY}
)


# frob:enforces CHK-GATE-SYSWAIVE003
# frob:tests tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness.test_expired_waiver_refires_and_is_flagged  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness.test_missing_expiry_marker_treated_as_expired  # noqa: E501
def _apply_conformance_waiver_staleness(
    applied: WaiverApplication[SelfConformViolation],
    today: date | None = None,
) -> WaiverApplication[SelfConformViolation]:
    """T-0671 acceptance criterion [0]: a SYS104/SYS105/SYS106 waiver
    older than its `expires:YYYY-MM-DD` staleness bound (module
    docstring's T-0671 section, `_waive.py::parse_waiver_expiry`) is
    EXPIRED -- its finding moves back into `kept` (the underlying
    obligation re-fires, unchanged from what it would have been with no
    waiver at all) and a new `CONFORMANCE_WAIVER_EXPIRED_RULE`
    (SYSWAIVE003) finding names the expired waiver. A conformance waiver
    with NO `expires:` marker at all is treated identically to one whose
    date has passed (fail closed -- staleness-dating is mandatory for
    these three families, not optional). Every OTHER family's waiver
    (SYS100-103, THREAT002/003, LINT004, ...) passes through `waived`
    unchanged -- this gate is scoped to `_CONFORMANCE_WAIVER_RULES` only.
    `today` is injectable for deterministic tests; `None` (the production
    default) resolves to the real wall-clock date at call time."""
    today = today if today is not None else date.today()
    still_valid: list = []
    reopened: list[SelfConformViolation] = []
    for wf in applied.waived:
        family, _sub_target = _split_waiver_rule(wf.waiver.rule)
        if family not in _CONFORMANCE_WAIVER_RULES:
            still_valid.append(wf)
            continue
        expiry = parse_waiver_expiry(wf.waiver.reason)
        if expiry is not None and expiry >= today:
            still_valid.append(wf)
            continue
        _log.warning(
            "selfconform: SYSWAIVE003 expired conformance waiver %s on %s "
            "(expiry=%s) -- underlying obligation re-fires",
            wf.waiver.rule,
            wf.waiver.node,
            expiry,
        )
        reopened.append(wf.finding)
        reopened.append(
            SelfConformViolation(
                rule=CONFORMANCE_WAIVER_EXPIRED_RULE,
                node=wf.waiver.node,
                detail=(
                    f"waive {wf.waiver.rule!r} on node {wf.waiver.node} is "
                    f"expired (reason={wf.waiver.reason!r}, "
                    + (
                        f"declared expiry {expiry.isoformat()}"
                        if expiry is not None
                        else "no expires:YYYY-MM-DD marker"
                    )
                    + ") -- underlying obligation re-fires"
                ),
            )
        )
    return WaiverApplication(
        kept=tuple(applied.kept) + tuple(reopened),
        waived=tuple(still_valid),
        stale=applied.stale,
    )


def _finalize_self_conform_report(applied, root: Path) -> SelfConformReport:  # noqa: ANN001
    """Fold stale-waiver findings + waived-violation details and log the
    summary, split out of `check_self_conformance` purely to keep that
    function's body short."""
    kept = list(applied.kept)
    kept.extend(_stale_waiver_violations(applied))
    waived_violations = _fold_waived_violations(applied)
    _log.info(
        "selfconform: %d violation(s), %d waived, %d stale waiver(s) found under %s",
        len(kept),
        len(waived_violations),
        len(applied.stale),
        root,
    )
    return SelfConformReport(violations=tuple(kept), waived=waived_violations)


def _bind_conformance_inputs(
    model: KernelModel, root: Path
) -> Result[CodeBinding, StrataError]:
    """`bind_code` then `_capability_binding`, in order -- the two fallible
    binding steps `check_self_conformance` needs before any SYS rule can
    run, split out purely to keep that function's body short."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    capability_bound = _capability_binding(model, bound.danger_ok, root)
    if capability_bound.is_err:
        return Err(capability_bound.danger_err)
    return Ok(capability_bound.danger_ok)


def _dedupe_sys100_extended_against_core(
    core: list[SelfConformViolation], extended: list[SelfConformViolation]
) -> list[SelfConformViolation]:
    """T-0266: `_core_undeclared_violations` (THREAT004 delegate, real
    file:line evidence per observed site) and `_extended_kind_violations`
    (one coarse node-level finding per capability kind, module docstring's
    SYS100 gap statement) are two INDEPENDENT SYS100 producers joined
    against the same `(node, capability)` space -- today's `_KIND_MAP`
    (net/fs/exec) and `_EXTENDED_KINDS` (eval/env/ffi/install-hook/sql/
    deserialize/html_render/fetch_url/client_storage/fs-read) vocabularies
    happen not to overlap, but nothing enforces that split staying true as
    either registry grows (T-0158/T-0304 already moved capability strings
    between the two more than once), so a future/config-drift kind landing
    in both tables would silently double-report the SAME site under one
    rule id. Filters `extended` down to findings whose `(node, capability)`
    is NOT already present in `core` -- `core` is kept whole (it is the
    ONLY one of the two that can legitimately report multiple real sites
    for the same node+kind, one per observed file:line, and those must all
    survive), `extended` (one entry per node+kind by construction, module
    docstring's `_extended_kind_violations`) is the one filtered since it
    carries strictly less evidence than a matching core finding for the
    same `(node, capability)`."""
    core_keys = {(v.node, v.capability) for v in core}
    return [v for v in extended if (v.node, v.capability) not in core_keys]


def _collect_sys_violations(
    model: KernelModel, capability_binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """Every SYS100/SYS100-extended/SYS101/SYS102/SYS103 finding, in that
    order, for `check_self_conformance`. T-0266: the extended SYS100 pass is
    deduped against the core pass (`_dedupe_sys100_extended_against_core`)
    before being appended, so a `(node, capability)` observed by BOTH
    passes surfaces as ONE finding, not two. T-0830 (H5): the extended
    (SYS100) and all-kinds (SYS101) observed-kinds views used to be two
    independent full scans of every owned file (`_observed_extended_kinds_
    by_node` and `_observed_all_kinds_by_node` each calling
    `scan_file_capabilities` on the same files); `raw_by_node` is now
    scanned ONCE here and both cheap set views (`_extended_kinds_view`,
    `_all_kinds_view`) are derived from it before being handed to the two
    violation functions."""
    core_violations = _core_undeclared_violations(model, capability_binding, root)
    raw_by_file = _observed_raw_kinds_by_file(capability_binding, root)
    raw_by_node = _aggregate_raw_kinds_by_node(capability_binding, raw_by_file)
    extended_violations = _extended_kind_violations(
        model, _extended_kinds_view(raw_by_node)
    )
    violations = list(core_violations)
    violations.extend(
        _dedupe_sys100_extended_against_core(core_violations, extended_violations)
    )
    violations.extend(
        _stale_design_violations(
            model, root, capability_binding, _all_kinds_view(raw_by_file)
        )
    )
    violations.extend(_unmodeled_violations(root, capability_binding))
    violations.extend(_coverage_totality_violations(capability_binding, root))
    violations.extend(
        _interface_conformance_violations(model, capability_binding, root)
    )
    violations.extend(_purpose_contract_violations(model, _all_kinds_view(raw_by_node)))
    violations.extend(_binding_totality_violations(model, capability_binding, root))
    scope_config = load_strata_scope_config(root)
    threshold = scope_config.require_may_scope_threshold or _LARGE_NODE_FILE_THRESHOLD
    violations.extend(
        _via_less_large_node_violations(model, capability_binding, threshold)
    )
    return violations


def _apply_sys_waivers(model: KernelModel, violations: list[SelfConformViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174): a
    matched waiver moves its finding into `waived` (still visible, never
    dropped); a waiver that matched nothing is STALE and becomes a new
    SYSWAIVE002 violation so drift fails the audit rather than silently
    going stale forever (`_waive.py` module docstring). Split out of
    `check_self_conformance` purely to keep that function's body short."""
    sys_rules = frozenset(
        (
            SYS_UNDECLARED_INTERFACE,
            SYS_STALE_DESIGN,
            SYS_UNMODELED_CODE,
            SYS_COVERAGE_TOTALITY,
            SYS_INTERFACE_CONFORMANCE,
            SYS_PURPOSE_CONTRACT,
            SYS_BINDING_TOTALITY,
        )
    )
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        # T-0174 REJECT round: SYS100/SYS101 fire once per capability kind
        # per node, so the sub-target IS the capability kind
        # (`SelfConformViolation.capability`); SYS102/SYS103 have no
        # sub-target concept (one finding per unmodeled directory/file) and
        # leave `capability` `None`, so both accept only the bare-rule
        # waiver form (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` excludes
        # them -- see `_coverage_totality_violations`'s docstring for why
        # SYS103 must not populate `capability`).
        sub_target_of=lambda v: v.capability,
        # T-0174: this call only ever sees SYS100-102 findings -- a waiver
        # declared for any other rule (LINT004, THREAT002, ...) belongs to
        # `evaluate_exhaustiveness`'s pass, not this one (apply_waivers'
        # `in_scope` docstring: staleness must be judged only against
        # waivers this caller can actually match).
        in_scope=lambda rule: rule in sys_rules,
    )


def _stale_waiver_violations(applied) -> list[SelfConformViolation]:  # noqa: ANN001
    """One `STALE_WAIVER_RULE` finding per stale waiver in `applied`, for
    `check_self_conformance`."""
    return [
        SelfConformViolation(
            rule=STALE_WAIVER_RULE, node=stale.node, detail=_stale_detail(stale)
        )
        for stale in applied.stale
    ]


def _fold_waived_violations(applied) -> tuple[SelfConformViolation, ...]:  # noqa: ANN001
    """Fold each waiver's reason/ticket into its matched violation's
    `detail` -- `report.waived` must show WHY, never just THAT (module
    docstring's "loud in output" requirement, mirrors `frob.gates`'s
    `WaiverRef`-annotated `Violation.waived`). T-0174 REJECT round: folds
    `wf.waiver.rule` (the RAW declared string, e.g. "SYS100:fs-write")
    into the printed detail, not just `wf.finding.rule` (the bare family)
    -- a reader must see the exact sub-target a waiver named, never just
    that SOME waiver on this rule matched (module docstring's "no blanket
    waivers"). Split out of `check_self_conformance` purely to keep that
    function's body short."""
    return tuple(
        wf.finding.model_copy(
            update={
                "detail": (
                    f"{wf.finding.detail} -- WAIVED[{wf.waiver.rule}]: "
                    f"{wf.waiver.reason!r}"
                    + (f" (ticket {wf.waiver.ticket})" if wf.waiver.ticket else "")
                )
            }
        )
        for wf in applied.waived
    )


__all__ = [
    "SYS_BINDING_TOTALITY",
    "SYS_COVERAGE_TOTALITY",
    "SYS_INTERFACE_CONFORMANCE",
    "SYS_PURPOSE_CONTRACT",
    "SYS_STALE_DESIGN",
    "SYS_UNDECLARED_INTERFACE",
    "SYS_UNMODELED_CODE",
    "SelfConformReport",
    "SelfConformViolation",
    "check_self_conformance",
]
