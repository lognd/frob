"""FORBID gate (T-4951): enforces `forbid call IDENTLIST` / `forbid import
IDENTLIST` policy rules (`_ast.py::ForbidCall`/`ForbidImport`) against the
real source bound to each rule's scoped nodes.

THE GAP THIS CLOSES. `forbid call`/`forbid import` are parsed
(strata-core/src/parse/grammar_policy.rs:129-140) and constructed by the
built-in `std.policy.analyzable` base pack (`_packs.py::ANALYZABLE`),
which the elaborator auto-injects onto every `trusted` component with a
WARNING log on every design load (`_packs.py::require_analyzable`). Until
this gate existed, nothing ever checked those rules against a node's
bound code: `_policy_weakening_gate.py` deliberately excludes both rule
kinds from WEAKENING detection (they are purely additive under
refinement, so that exclusion is correct), and no other gate read them at
all -- so the mandatory pack's warning was pure cost with zero
enforcement behind it. This module is TIER-2 execution of `ForbidCall`/
`ForbidImport` against actual source, the missing half.

GUARD DESIGN (memory/guard-design-lessons.md's three failure modes,
addressed explicitly):
  - EXEMPTING THE NORMAL CASE: a forbidden identifier reached through an
    alias or re-export is NOT resolved here (v0 scope cut, same as this
    module's sibling `_effects.py`'s needle-substring posture) -- this is
    a disclosed limitation, not a silent exemption: `docs/modules/
    gates.md` records it as a known gap, not a claim of soundness.
  - FAILING OPEN: a node in a forbidding policy's scope with NO bound
    code at all is reported as `Severity.UNRESOLVED` (`FORBID003`), never
    folded into a clean/empty result -- "uncheckable" is a distinguishable
    outcome, the same ceiling `_obligation_proof.py`'s REL2xx family
    already draws for its own proof-against-code checks.
  - CRYING WOLF: a needle match on a comment/docstring line
    (`non_executable_line_numbers`) or inside a same-line string literal
    (`_byte_offset_inside_string_literal`) is never reported -- reusing
    `frob.vet._capability`'s own false-positive guards rather than
    re-deriving them, so a docstring or log message that merely MENTIONS
    `eval(` is not a finding.

JOINS THE EXISTING CAPABILITY SCAN (acceptance clause 4, T-4669): this
module does not walk the source tree itself. `_forbid_rule_violations`
takes an already-computed `CodeBinding` (the same one `_effects.py::
check_capability_conformance` binds for its own tier-2 pass) and
`_obligation_proof.py::owner_index`'s inversion of it -- one `bind_code`
call per model, shared with capability conformance, never a second
full-tree walk of its own.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from frob.excludes import is_excluded, iter_files, load_exclude_globs
from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.vet._capability import (
    _byte_offset_inside_string_literal,
    language_for,
    non_executable_line_numbers,
)

if TYPE_CHECKING:
    from frob.strata._ast import Module
    from frob.strata._code_binding import CodeBinding
    from frob.strata._models import KernelModel

_log = get_logger(__name__)

#: `frob sys audit` rule id: a forbidden call (`forbid call IDENTLIST`)
#: was found in a node's bound code (T-4951). Private (no `frob:doc`
#: anchor) until `docs/modules/gates.md`'s T-4693 lease clears -- see
#: this ticket's Done report / T-4910's body for the doc-anchor +
#: registration follow-up.
_FORBID_CALL_VIOLATION = "FORBID001"

#: `frob sys audit` rule id: a forbidden import (`forbid import IDENTLIST`)
#: was found in a node's bound code (T-4951). Same T-4693 lease note as
#: `_FORBID_CALL_VIOLATION` above.
_FORBID_IMPORT_VIOLATION = "FORBID002"

#: `frob sys audit` rule id: a node named in a forbid-rule policy's scope
#: owns NO bound code at all -- UNCHECKABLE, never a silent clean pass
#: (T-4951, guard-design-lessons.md's fail-open ceiling). Same T-4693
#: lease note as `_FORBID_CALL_VIOLATION` above.
_FORBID_UNCHECKABLE = "FORBID003"

#: Mirrors `frob.gates._sys._design_dir`'s default (T-0135: no
#: cross-import into `frob.gates._sys`, which itself defers
#: `frob.strata`, just to read one toml key) -- same duplication posture
#: `_policy_weakening_gate.py::_DEFAULT_DESIGN_DIR` already documents.
_DEFAULT_DESIGN_DIR = "design"


class _ForbidSite(BaseModel):
    """One forbidden call/import site found in bound source (T-4951):
    which rule fired, at which file:line, on which identifier."""

    model_config = ConfigDict(frozen=True)

    rule: str
    file: str
    line: int
    ident: str


# frob:ticket T-4951
def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from frob.toml, defaulting to `_DEFAULT_DESIGN_DIR`
    -- duplicated from `_policy_weakening_gate.py::_design_dir` rather than
    imported, same T-0135 reasoning documented there."""
    import tomllib

    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return _DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("_forbid_rules_gate: frob.toml unreadable: %s", exc)
        return _DEFAULT_DESIGN_DIR
    strata_table = doc.get("strata", {})
    if not isinstance(strata_table, dict):
        return _DEFAULT_DESIGN_DIR
    value = strata_table.get("design_dir", _DEFAULT_DESIGN_DIR)
    return value if isinstance(value, str) else _DEFAULT_DESIGN_DIR


# frob:ticket T-4951
def _strata_files(root: Path, design_dir: Path) -> list[Path]:
    """Every `.strata` file under `design_dir`, minus `[graph].exclude`
    matches -- duplicated from `_policy_weakening_gate.py::_strata_files`
    (same T-0135 posture: no cross-import just for a file walk)."""
    if not design_dir.is_dir():
        return []
    exclude_globs = load_exclude_globs(root)
    found = []
    for path in sorted(iter_files(design_dir, suffix=".strata")):
        rel = path.relative_to(root).as_posix()
        if exclude_globs and is_excluded(rel, exclude_globs):
            continue
        found.append(path)
    return found


# frob:ticket T-4951
def _call_pattern(ident: str) -> re.Pattern[bytes]:
    """A call-shaped byte regex for `ident` (`ident` optionally followed by
    whitespace then `(`) -- e.g. `eval (x)` still matches, matching this
    module's textual-needle posture (same v0 scope cut as `_effects.py`'s
    own needle scan, not a real call-expression parse)."""
    return re.compile(re.escape(ident).encode() + rb"\s*\(")


# frob:ticket T-4951
def _import_pattern(ident: str) -> re.Pattern[bytes]:
    """An import-shaped byte regex for `ident`: `import IDENT` or
    `from IDENT import ...`, word-bounded so `import_module_helper` does
    not match a `forbid import module_helper` rule."""
    escaped = re.escape(ident).encode()
    return re.compile(
        rb"\b(?:import\s+" + escaped + rb"\b|from\s+" + escaped + rb"\s+import\b)"
    )


# frob:ticket T-4951
def _sites_in_file(
    path: Path,
    rel: str,
    call_idents: tuple[str, ...],
    import_idents: tuple[str, ...],
) -> list[_ForbidSite]:
    """Every forbidden call/import site in `path` (`rel`-relative to root),
    skipping comment/docstring lines (`non_executable_line_numbers`) and
    same-line string-literal mentions (`_byte_offset_inside_string_
    literal`) -- the crying-wolf guards this module's docstring commits
    to. Python-only (T-4951 v0 scope: the built-in `std.policy.analyzable`
    pack's own idents -- `eval`/`exec`/`getattr`/etc. -- are a Python
    vocabulary; `language_for` returning anything else skips the file
    entirely rather than false-matching an unrelated language's tokens)."""
    if language_for(path) != "python":
        return []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _log.warning("_forbid_rules_gate: could not read %s: %s", rel, exc)
        return []
    non_exec = non_executable_line_numbers(path)
    sites: list[_ForbidSite] = []
    for rule, idents, pattern_of in (
        (_FORBID_CALL_VIOLATION, call_idents, _call_pattern),
        (_FORBID_IMPORT_VIOLATION, import_idents, _import_pattern),
    ):
        for ident in idents:
            for match in pattern_of(ident).finditer(raw):
                idx = match.start()
                line = raw.count(b"\n", 0, idx) + 1
                if line in non_exec:
                    continue
                if _byte_offset_inside_string_literal(raw, idx):
                    continue
                sites.append(_ForbidSite(rule=rule, file=rel, line=line, ident=ident))
    return sites


# frob:ticket T-4951
def _rule_idents(rules: tuple, kind: str) -> tuple[str, ...]:
    """Every `idents` entry across `rules` whose `kind` matches (T-4951) --
    e.g. every `forbid call` target across a compiled policy's rules."""
    return tuple(ident for rule in rules if rule.kind == kind for ident in rule.idents)


# frob:ticket T-4951
def _uncheckable_violation(node_id: str, policy_id: str) -> Violation:
    """`FORBID003`/`Severity.UNRESOLVED` for `node_id`: it is in `policy_id`'s
    forbid-rule scope but owns no bound code at all (T-4951's fail-open
    ceiling -- see this module's docstring)."""
    return Violation(
        rule=_FORBID_UNCHECKABLE,
        severity=Severity.UNRESOLVED,
        file=policy_id,
        line=0,
        message=(
            f"FORBID003: node {node_id!r} is in policy {policy_id!r}'s "
            "forbid-rule scope but owns no bound code -- this obligation is "
            "UNCHECKABLE, not a clean pass (bind `code` glob(s) to it, or "
            "narrow the policy's scope)"
        ),
    )


# frob:ticket T-4951
def _site_violation(site: "_ForbidSite", node_id: str, policy_id: str) -> Violation:
    """One real forbidden call/import `site` turned into a `FORBID001`/
    `FORBID002` `Violation` (T-4951)."""
    verb = "call" if site.rule == _FORBID_CALL_VIOLATION else "import"
    return Violation(
        rule=site.rule,
        severity=Severity.ERROR,
        file=site.file,
        line=site.line,
        message=(
            f"{site.rule}: policy {policy_id!r} forbids {verb} of "
            f"{site.ident!r}, found in node {node_id!r}'s bound code -- "
            "std.policy.analyzable's extraction_soundness guarantee "
            "requires a closed, statically-visible call/import graph "
            "(docs/strata/evidence.md#the-enables-cascade)"
        ),
    )


# frob:ticket T-4951
def _node_forbid_violations(
    node_id: str,
    policy_id: str,
    files: list[str],
    call_idents: tuple[str, ...],
    import_idents: tuple[str, ...],
    root: Path,
) -> list[Violation]:
    """Every `FORBID001`/`FORBID002` finding for one `(node_id, policy_id)`
    pair, or a single `FORBID003` if `files` is empty (T-4951)."""
    if not files:
        _log.warning(
            "_forbid_rules_gate: node %s is in policy %s's forbid-rule "
            "scope but has no bound code -- UNCHECKABLE",
            node_id,
            policy_id,
        )
        return [_uncheckable_violation(node_id, policy_id)]
    violations: list[Violation] = []
    for rel in files:
        for site in _sites_in_file(root / rel, rel, call_idents, import_idents):
            _log.warning(
                "_forbid_rules_gate: %s: node %s forbidden site %r at %s:%d "
                "(policy %s)",
                site.rule,
                node_id,
                site.ident,
                rel,
                site.line,
                policy_id,
            )
            violations.append(_site_violation(site, node_id, policy_id))
    return violations


# frob:ticket T-4951
def _forbid_rule_violations(
    module: "Module",
    model: "KernelModel",
    binding: "CodeBinding",
    root: Path,
) -> tuple[Violation, ...]:
    """Every `ForbidCall`/`ForbidImport` policy rule in `module`, compiled
    against `model` and checked against `binding`'s already-bound source
    (T-4951): `FORBID001`/`FORBID002` for a real forbidden site, or
    `FORBID003` (`Severity.UNRESOLVED`) for a node in scope with no bound
    code at all. Deny-by-default and fail-closed the same way every other
    strata tier-2 conformance check in this package already is; a policy
    scope that fails to compile is logged and skipped (the malformed
    `.strata` file itself is SYS004's job to report, not this gate's)."""
    from frob.strata import compile_policies, require_analyzable
    from frob.strata._obligation_proof import owner_index

    # T-4951: `elaborate()` normalizes its OWN local copy of `module` with
    # `require_analyzable` (auto-injecting `std.policy.analyzable` onto a
    # trusted node lacking it) but returns only the resulting `KernelModel`,
    # never the amended `Module` -- so a caller's own `module.policies`
    # never carries the auto-injected pack unless it re-normalizes here too
    # (`_packs.py::require_analyzable` is itself idempotent: a module that
    # already declares the pack id is returned unchanged, so calling it
    # again after `elaborate()` already did is always safe).
    normalized = require_analyzable(module)
    if normalized.is_err:
        _log.warning(
            "_forbid_rules_gate: require_analyzable failed: %s", normalized.danger_err
        )
        return ()
    module = normalized.danger_ok

    compiled = compile_policies(module, model)
    if compiled.is_err:
        _log.warning(
            "_forbid_rules_gate: policy compilation failed: %s", compiled.danger_err
        )
        return ()

    owner_by_node = owner_index(binding.owner)
    violations: list[Violation] = []
    for policy in compiled.danger_ok.policies:
        call_idents = _rule_idents(policy.rules, "forbid_call")
        import_idents = _rule_idents(policy.rules, "forbid_import")
        if not call_idents and not import_idents:
            continue
        for node_id in policy.node_ids:
            violations.extend(
                _node_forbid_violations(
                    node_id,
                    policy.id,
                    owner_by_node.get(node_id, []),
                    call_idents,
                    import_idents,
                    root,
                )
            )
    return tuple(violations)


# frob:enforces CHK-GATE-FORBID001
# frob:enforces CHK-GATE-FORBID002
# frob:enforces CHK-GATE-FORBID003
# frob:ticket T-4951
def _forbid_rules_gate(root: Path) -> tuple[Violation, ...]:
    """T-4951: `forbid call`/`forbid import` (`_ast.py::ForbidCall`/
    `ForbidImport`) run for real over `root`'s actual `design/` policies,
    instead of being parsed, auto-injected by `std.policy.analyzable`, and
    never enforced. Opt-in behind a `design/` (or `[strata].design_dir`)
    directory existing, the same T-0135 posture `policy_weakening_gate`
    already uses. Each `.strata` file is parsed and elaborated on its own
    (not the merged multi-file `KernelModel`/`Module` `load_design_ids`
    builds for id-uniqueness checks): a forbid rule's `ScopeSpec` resolves
    against ITS OWN file's node namespace, and re-parsing here pays no new
    `frob.strata` import cost (`policy_weakening_gate.py::
    _policy_id_file_map`'s identical T-3460 precedent). A design load
    failure is left to SYS004 to report -- this gate silently contributes
    nothing for a file that fails to parse or elaborate rather than
    double-reporting a load failure under a second rule id. Private (no
    `frob:doc` anchor, not yet registered in `_ALL_GATES`) until
    `docs/modules/gates.md`'s T-4693 lease clears and T-3962's lease on
    `src/frob/gates/__init__.py` clears -- see T-4910's body."""
    design_dir = _design_dir(root)
    if not (root / design_dir).is_dir():
        _log.debug("_forbid_rules_gate: no %s/ directory, skipping", design_dir)
        return ()

    from frob.strata import bind_code, elaborate, parse_module

    violations: list[Violation] = []
    for path in _strata_files(root, root / design_dir):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("_forbid_rules_gate: could not read %s: %s", rel, exc)
            continue
        parsed = parse_module(text)
        if parsed.is_err:
            _log.debug(
                "_forbid_rules_gate: %s failed to parse (%s), skipping",
                rel,
                parsed.danger_err,
            )
            continue
        module = parsed.danger_ok
        if not module.policies:
            continue
        elaborated = elaborate(module)
        if elaborated.is_err:
            _log.debug(
                "_forbid_rules_gate: %s failed to elaborate (%s), skipping",
                rel,
                elaborated.danger_err,
            )
            continue
        model = elaborated.danger_ok
        binding = bind_code(model, root)
        if binding.is_err:
            _log.warning(
                "_forbid_rules_gate: %s: code binding failed: %s",
                rel,
                binding.danger_err,
            )
            continue
        violations.extend(
            _forbid_rule_violations(module, model, binding.danger_ok, root)
        )
    return tuple(violations)
