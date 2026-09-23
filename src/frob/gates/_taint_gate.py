"""SEC005 gate wiring (docs/modules/gates.md#rule-catalog, T-0781):
turns `frob.vet._taint.taint_findings` into repo-wide `Violation`s over
every git-tracked `.py` file, the same tracked-file-scan shape
`frob.gates._secrets`/`_opaque` already use.

T-5307 extends this SAME gate call site with a second, framework-scoped
source/sink family -- `frob.webapp._websec_sinks.websec_sink_findings`
(WEBSEC101-106, the DOM/template XSS sink corpus T-5141 names) -- rather
than standing up a parallel gate registration: both families are taint
passes with the same "source reaches a dangerous sink with no
validator/sanitizer hop" shape, and `websec_sink_findings` already
short-circuits to nothing for a repo `frob.webapp._detect.
detect_frameworks` reports no web framework in, so folding it into
`taint_gate` costs a no-framework repo nothing beyond one cheap detect
call. See docs/modules/webapp-websec-injection.md.

T-5311 folds in a THIRD framework-scoped family the same way --
`frob.webapp._websec_bounds.websec_bounds_findings` (WEBSEC123-125, the
resource-exhaustion input-bounds corpus items T-5141 names: unbounded
input length, XML/JSON bomb, unbounded recursion) -- same posture, same
short-circuit, no second gate registration. See
docs/modules/webapp-websec-bounds.md.

T-5308 replaces further ad-hoc hard-coded fold-ins with a DISCOVERY
mechanism (`_discover_websec_hook_modules`/`_discovered_websec_
violations`): every `frob.webapp._websec_*` submodule that exposes a
module-level `websec_findings(root: Path, frameworks:
frozenset[FrameworkKind]) -> tuple[Violation, ...]` callable is found via
`pkgutil.iter_modules` + `importlib.import_module` and called
automatically, so a NEW WEBSEC family (this leaf's own
`frob.webapp._websec_headers_log.websec_findings`, WEBSEC117-122, and any
future sibling) never needs its own `_taint_gate.py` edit -- only a new
`frob.webapp._websec_*` module with that one hook function. `frameworks`
is computed ONCE per `taint_gate(root)` call and threaded to every
discovered hook, so a repo with N discovered WEBSEC families still pays
for exactly one `detect_frameworks` call, not N. `_websec_sinks.py`
(T-5307) and `_websec_bounds.py` (T-5311) predate this discovery
mechanism and do not expose the hook -- both stay wired via their
existing direct calls below rather than a hand-edit to those modules'
own (out-of-this-leaf's-scope) files; a follow-up leaf can migrate them
onto the hook with zero `_taint_gate.py` changes once it does. See
docs/modules/webapp-websec-headers-log.md.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import frob.webapp
from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.vet._taint import taint_findings
from frob.webapp._detect import FrameworkKind, detect_frameworks
from frob.webapp._websec_bounds import websec_bounds_findings
from frob.webapp._websec_sinks import websec_sink_findings

_log = get_logger(__name__)

__all__ = ["taint_gate"]

#: Module-basename prefix `_discover_websec_hook_modules` scans
#: `frob.webapp` for -- every `frob.webapp._websec_*` submodule is a
#: candidate hook provider (T-5308).
# frob:ticket T-5308
_WEBSEC_MODULE_PREFIX = "_websec_"

#: Name of the module-level hook `_discover_websec_hook_modules` looks
#: for on each candidate module (T-5308's discovery contract, documented
#: on `frob.webapp._websec_headers_log.websec_findings`).
# frob:ticket T-5308
_WEBSEC_HOOK_NAME = "websec_findings"


# frob:ticket T-5308
# frob:waive ARCH104 reason="T-5308 dynamic plugin discovery over frob.webapp's own \
# package path -- see this function's own docstring for the full case."
# frob:waive OPAQUE001 reason="dotted name comes from pkgutil's own enumeration of \
# frob.webapp's real submodules, not attacker/config input -- see docstring."
def _discover_websec_hook_modules() -> tuple[object, ...]:
    """Every `frob.webapp._websec_*` submodule exposing a module-level
    `websec_findings(root, frameworks) -> tuple[Violation, ...]` callable
    (T-5308's discovery contract), imported via `importlib` and returned
    in sorted-name order for deterministic scan order. A submodule with
    no `websec_findings` attribute (T-5307's `_websec_sinks`, T-5311's
    `_websec_bounds` as of this leaf) is silently skipped -- discovery
    is additive, never a replacement for those modules' own existing
    direct calls below."""
    discovered: list[object] = []
    for module_info in sorted(
        pkgutil.iter_modules(frob.webapp.__path__), key=lambda m: m.name
    ):
        if not module_info.name.startswith(_WEBSEC_MODULE_PREFIX):
            continue
        dotted = f"{frob.webapp.__name__}.{module_info.name}"
        module = importlib.import_module(dotted)
        hook = getattr(module, _WEBSEC_HOOK_NAME, None)
        if not callable(hook):
            continue
        _log.debug("taint_gate: discovered websec hook module %s", dotted)
        discovered.append(module)
    return tuple(discovered)


# frob:ticket T-5308
# frob:waive OPAQUE001 reason="literal constant attribute name on a module this caller \
# already validated is callable -- see _discover_websec_hook_modules."
def _discovered_websec_violations(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """Call every discovered hook module's `websec_findings(root,
    frameworks)`, flattening the results into one `Violation` tuple
    (T-5308)."""
    violations: list[Violation] = []
    for module in _discover_websec_hook_modules():
        hook = getattr(module, _WEBSEC_HOOK_NAME)
        violations.extend(hook(root, frameworks))
    return tuple(violations)


def _tracked_python_files(root: Path) -> tuple[str, ...]:
    """`git ls-files -- '*.py'` under `root`, root-relative POSIX paths,
    `()` on any git failure -- mirrors `frob.gates._opaque`/`_secrets`'s
    own per-module copy of this exact shape."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", "*.py"))
    if spawned.is_err:
        _log.warning("taint_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("taint_gate: git ls-files exited %d", result.returncode)
        return ()
    files = tuple(line for line in result.stdout.splitlines() if line.strip())
    _log.debug("taint_gate: %d tracked .py file(s)", len(files))
    return files


# frob:doc docs/modules/gates.md#public-api
# frob:doc docs/modules/webapp-websec-injection.md#public-api
# frob:doc docs/modules/webapp-websec-bounds.md#public-api
# frob:doc docs/modules/webapp-websec-headers-log.md#public-api
# frob:ticket T-0781
# frob:ticket T-5307
# frob:ticket T-5311
# frob:ticket T-5308
# frob:enforces CHK-GATE-SEC005
# frob:enforces CWE-88
def taint_gate(root: Path) -> tuple[Violation, ...]:
    """SEC005: every git-tracked `.py` file scanned for
    `frob.vet._taint.taint_findings` (T-0781 -- a value parsed from
    `.git/`/`.frob/` repo-writable state reaching a subprocess argv
    position with no validator hop or `--` terminator). WARN-tier at
    first turn-on -- same T-0688/T-0973 promotion posture `opaque_gate`
    already follows: a brand-new structural rule needs a real fix-or-
    waive pass over its first measured hit set before ERROR is safe.

    T-5307: also folds in `frob.webapp._websec_sinks.websec_sink_findings`
    (WEBSEC101-106) -- see this module's own docstring for why that lives
    here instead of a second gate registration. Same WARN-tier posture.

    T-5308: also folds in every DISCOVERED `frob.webapp._websec_*`
    hook module's `websec_findings(root, frameworks)` (this leaf's own
    WEBSEC117-122 among them) -- see this module's own docstring for the
    discovery contract."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_python_files(root):
        abs_path = root / rel_path
        try:
            findings = taint_findings(abs_path)
        except OSError as exc:
            _log.debug("taint_gate: skipping unreadable %s: %s", rel_path, exc)
            continue
        scanned += 1
        for finding in findings:
            violations.append(
                Violation(
                    rule="SEC005",
                    severity=Severity.WARN,
                    file=rel_path,
                    line=finding.sink_line,
                    message=(
                        f"SEC005: {rel_path}:{finding.sink_line} "
                        f"{finding.sink_call}(...) argv includes "
                        f"{finding.var_name!r}, sourced from a repo-"
                        f"writable-state read at line {finding.source_line} "
                        f"(.git/.frob JSON or text another worktree/agent "
                        f"can write) with no validator call or a preceding "
                        f'`"--"` literal between source and sink -- pass '
                        f"the value through a `validate_*`/`sanitize_*` "
                        f'helper first, add a literal `"--"` terminator '
                        f"before it in the argv list, or "
                        f'`frob:waive SEC005 reason="..."` with a real '
                        f"justification"
                    ),
                )
            )

    websec_findings = websec_sink_findings(root)
    for finding in websec_findings:
        violations.append(
            Violation(
                rule=finding.rule,
                severity=Severity.WARN,
                file=finding.file,
                line=finding.line,
                message=finding.message,
            )
        )

    bounds_findings = websec_bounds_findings(root)
    for finding in bounds_findings:
        violations.append(
            Violation(
                rule=finding.rule,
                severity=Severity.WARN,
                file=finding.file,
                line=finding.line,
                message=finding.message,
            )
        )

    frameworks = detect_frameworks(root)
    discovered_violations = _discovered_websec_violations(root, frameworks)
    violations.extend(discovered_violations)

    _log.info(
        "taint_gate: scanned %d tracked .py file(s), %d SEC005 violation(s), "
        "%d WEBSEC10x violation(s), %d WEBSEC12x violation(s), "
        "%d discovered websec-hook violation(s)",
        scanned,
        len(violations)
        - len(websec_findings)
        - len(bounds_findings)
        - len(discovered_violations),
        len(websec_findings),
        len(bounds_findings),
        len(discovered_violations),
    )
    return tuple(violations)
