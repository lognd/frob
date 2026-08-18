"""ENV001: every `FROB_*` env var needs a doc anchor or an explicit waiver
(docs/modules/gates.md#env001-t-1782).

T-1611 classification history: T-1610's docs-completeness sweep found
`FROB_WORKER_STDOUT_LOG_LEVEL` (T-0806) undocumented anywhere in `docs/`
for roughly two weeks. `SEC110` (`frob.gates._secrets`) DOES fire on this
exact env-var read -- but it asks "is this env var a secret needing a
`std.secrets` registry mapping", a different question than "does this
operational env var have user-facing documentation"; it fired and was
correctly waived for its own question, and that waiver covers nothing
here. `COV001`/`COV007` also do not apply: the constant backing an
env-var name is normally a private symbol, and this repo's own
convention (COV007) is that private symbols do NOT carry a `frob:doc`
anchor by default -- so an operationally user-facing `FROB_*` env var
implemented as a private constant was structurally invisible to every
existing doc-coverage gate.

`env_var_doc_gate` enumerates every `FROB_*` string-literal constant
ASSIGNMENT in `src/frob/**/*.py` (`NAME = "FROB_..."`, the same
enumeration T-1610 did by hand) and requires each to either:

  (a) appear literally (the `FROB_...` string itself) or by its owning
      Python constant name (the `NAME` on the left of the `=`) in some
      tracked file under `docs/` -- matching the "documented by constant
      name, not literal string" allowance T-1610's own audit already
      established as adequate (the `FROB_PARSE_ARTIFACT_CACHE`
      precedent), or
  (b) carry a `frob:waive ENV001 reason="..."` directive ANYWHERE in the
      same source file -- file-scoped, not per-constant, the same
      granularity `_match_waiver`'s symref-less matching mode already
      gives every other file-scoped rule in this package. A file that
      groups several genuinely internal/test-only/worker-internal
      `FROB_*` constants together can waive them all with one directive;
      a file mixing a genuinely internal one with a real user-facing one
      should split the internal one into its own module if per-constant
      precision is ever needed -- not attempted here (disclosed, not
      silently dropped).
"""
# frob:ticket T-1782

from __future__ import annotations

import re
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._tracked_files import tracked_files as _tracked_files
from frob.lang import declared_project_package_name, declared_source_prefixes
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["env_var_doc_gate"]


def _env_assignment_pattern(env_prefix: str) -> re.Pattern[str]:
    """`NAME = "<ENV_PREFIX>SOMETHING"` (or single-quoted) -- a
    `<env_prefix>*` string literal assigned to a constant, `env_prefix`
    resolved from THIS project's own declared package name (T-2389,
    retargeted off a hardcoded `FROB_` literal -- the same
    catalogued-is-not-enforced class T-2384 exists to fix: a `lograder`
    checkout's own `LOGRADER_*` env vars were structurally invisible to
    the pre-fix hardcoded pattern). Deliberately matches ANY line shape
    (module-level or indented, with or without a type annotation before
    `=`), since the ticket's own enumeration ("every <PREFIX>* string-
    literal constant assigned") is not scoped to module top-level only."""
    return re.compile(
        r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=\s*"
        rf'["\']({re.escape(env_prefix)}[A-Z0-9_]+)["\']'
    )


def _env_var_assignments(
    root: Path,
    tracked: tuple[str, ...],
    *,
    source_prefixes: tuple[str, ...],
    env_prefix: str,
) -> tuple[tuple[str, str, str, int], ...]:
    """Every `(rel_path, constant_name, env_var_value, line_no)` tuple for
    an `<env_prefix>*` string-literal constant assignment found under any
    of `source_prefixes` (T-2389: was a hardcoded `"src/frob/"`, now this
    project's own declared source roots -- see
    `frob.lang.declared_source_prefixes`, T-2195/T-2384), in
    file-then-line order."""
    pattern = _env_assignment_pattern(env_prefix)
    found: list[tuple[str, str, str, int]] = []
    for rel in sorted(tracked):
        if not (rel.startswith(source_prefixes) and rel.endswith(".py")):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = pattern.match(line)
            if match:
                found.append((rel, match.group(1), match.group(2), lineno))
    return tuple(found)


def _docs_corpus(root: Path, tracked: tuple[str, ...]) -> str:
    """The concatenated text of every tracked file under `docs/` -- one
    read pass, reused across every candidate env var this run checks."""
    chunks: list[str] = []
    for rel in tracked:
        if not rel.startswith("docs/"):
            continue
        try:
            chunks.append((root / rel).read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(chunks)


# frob:doc docs/modules/gates.md#env001-t-1782
def env_var_doc_gate(root: Path) -> tuple[Violation, ...]:
    """ENV001: flag every `<PREFIX>*` string-literal constant assignment
    (`PREFIX` this project's own declared package name, uppercased --
    T-2389, was hardcoded `FROB_`) under this project's own declared
    source roots (T-2389, was hardcoded `src/frob/**/*.py`) that is
    documented nowhere under `docs/` -- neither by its literal env-var
    string nor by its owning Python constant name. UNRESOLVED (not a
    silent empty pass) if this project's own package name cannot be
    resolved from pyproject.toml (T-2391 fail-loudly doctrine -- no
    denominator to scan for is a different claim than "found nothing").
    WARN severity otherwise: a surfacing rule (matching ROOT001's own
    posture, T-1784) -- undocumented is a real gap, not a stop-the-world
    defect, and file-scoped `frob:waive ENV001` is the honest escape
    hatch for a genuinely internal/test-only/worker-internal flag."""
    pkg = declared_project_package_name(root)
    if pkg is None:
        _log.warning(
            "env_var_docs: %s/pyproject.toml [project].name unreadable -- "
            "ENV001 cannot resolve what env-var prefix to look for; "
            "reporting UNRESOLVED, not a clean pass",
            root,
        )
        return (
            Violation(
                rule="ENV001",
                severity=Severity.UNRESOLVED,
                file="pyproject.toml",
                line=0,
                message=(
                    "ENV001: could not resolve this project's own "
                    "declared package name from pyproject.toml "
                    "[project].name -- ENV001 has no env-var prefix to "
                    "scan for and cannot report a meaningful pass/fail; "
                    "fix pyproject.toml's [project] table"
                ),
            ),
        )
    source_prefixes = declared_source_prefixes(root)
    env_prefix = f"{pkg.upper().replace('-', '_')}_"

    tracked = _tracked_files(root, caller="env_var_docs")
    if not tracked:
        return ()
    assignments = _env_var_assignments(
        root, tracked, source_prefixes=source_prefixes, env_prefix=env_prefix
    )
    if not assignments:
        return ()
    docs_text = _docs_corpus(root, tracked)

    violations: list[Violation] = []
    for rel, name, value, lineno in assignments:
        if value in docs_text or name in docs_text:
            continue
        _log.debug("env_var_docs: %s (%s) has no doc anchor", value, name)
        violations.append(
            Violation(
                rule="ENV001",
                severity=Severity.WARN,
                file=rel,
                line=lineno,
                message=(
                    f"ENV001: {value} ({name}, {rel}:{lineno}) has no doc "
                    "anchor under docs/ -- neither the literal env-var "
                    "string nor its owning constant name appears in any "
                    "tracked docs/ file (T-1610/T-1782: this is exactly "
                    "how FROB_WORKER_STDOUT_LOG_LEVEL went undocumented "
                    "for two weeks). Document it under docs/, or if it is "
                    "genuinely internal/test-only/worker-internal, add "
                    f'`# frob:waive ENV001 reason="..."` anywhere in '
                    f"{rel} (file-scoped: covers every FROB_* constant in "
                    "that file)."
                ),
            )
        )
    return tuple(violations)
