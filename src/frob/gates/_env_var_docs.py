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
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["env_var_doc_gate"]

#: `NAME = "FROB_SOMETHING"` (or single-quoted) -- a `FROB_*` string
#: literal assigned to a constant. Deliberately matches ANY line shape
#: (module-level or indented, with or without a type annotation before
#: `=`), since the ticket's own enumeration ("every FROB_* string-literal
#: constant assigned") is not scoped to module top-level only.
_ENV_ASSIGNMENT_RE = re.compile(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=\s*["\'](FROB_[A-Z0-9_]+)["\']'
)


def _env_var_assignments(root: Path, tracked: tuple[str, ...]) -> tuple[
    tuple[str, str, str, int], ...
]:
    """Every `(rel_path, constant_name, env_var_value, line_no)` tuple for
    a `FROB_*` string-literal constant assignment found under
    `src/frob/**/*.py`, in file-then-line order."""
    found: list[tuple[str, str, str, int]] = []
    for rel in sorted(tracked):
        if not (rel.startswith("src/frob/") and rel.endswith(".py")):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = _ENV_ASSIGNMENT_RE.match(line)
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
    """ENV001: flag every `FROB_*` string-literal constant assignment
    under `src/frob/**/*.py` that is documented nowhere under `docs/` --
    neither by its literal env-var string nor by its owning Python
    constant name. WARN severity: a surfacing rule (matching ROOT001's
    own posture, T-1784) -- undocumented is a real gap, not a stop-the-
    world defect, and file-scoped `frob:waive ENV001` is the honest
    escape hatch for a genuinely internal/test-only/worker-internal
    flag."""
    tracked = _tracked_files(root, caller="env_var_docs")
    if not tracked:
        return ()
    assignments = _env_var_assignments(root, tracked)
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
