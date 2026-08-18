"""DOC004 leaf shared state: `_ProjectNamespaces`, `_read_toml`, and
`_doc004_violation` (T-2231, gates/lang/graph import-cycle break).

Extracted out of `frob.gates._docblocks` -- both `_docblocks.py` and
`frob.gates._docblocks_refs` (itself split out of `_docblocks.py` by
T-1195) need these three names, and `_docblocks.py` importing back from
`_docblocks_refs.py` (for the bulk of DOC004's actual parsing/checking
logic) made the two modules mutually import each other: a real,
module-level cycle, not a lazy-import false positive. This module has no
dependency on either sibling, so both can depend on it without depending
on each other for these three names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.tomlio import read_toml_lenient


@dataclass(frozen=True)
class _ProjectNamespaces:
    """This project's own import/crate namespaces, derived from manifests."""

    python: frozenset[str] = field(default_factory=frozenset)
    rust: frozenset[str] = field(default_factory=frozenset)
    ts: frozenset[str] = field(default_factory=frozenset)
    # rust namespace -> crate source directory (repo-relative), used to
    # resolve a `use <crate>::path::Item` token to the .rs files that
    # could plausibly define `Item`.
    rust_crate_dirs: dict[str, str] = field(default_factory=dict)


def _read_toml(path: Path) -> dict | None:
    """Best-effort TOML load: `None` on any missing/unreadable/malformed file,
    never a crash -- a missing manifest just means that language contributes
    no namespaces, not a gate failure. Thin wrapper over `frob.tomlio.
    read_toml_lenient` (extracted T-0861) that fixes this module's own
    `log_prefix`."""
    return read_toml_lenient(path, log_prefix="doc004")


# frob:enforces CHK-GATE-DOC004
# frob:waive DUP001 reason="T-2231: DUP001 flags this against _decisions_compliance.py::_compliance005_violation and _refactor/_scan.py::_import_op purely on the shared 'build one Violation(...) from a tier/detail pair' boilerplate shape every gate module in this package repeats -- moving here (T-2231's import-cycle fix) surfaced it as a new DUP001 identity, not new duplication; each site constructs a DIFFERENT rule's Violation from a DIFFERENT source type, no shared logic to extract"  # noqa: E501
def _doc004_violation(doc_path: str, line: int, *, tier: str, detail: str) -> Violation:
    """Build one DOC004 `Violation` -- `tier` is `"stale"` (error, a named
    reference does not resolve) or `"unbound"` (warn, a valid reference has
    no nearby binding directive)."""
    severity = Severity.ERROR if tier == "stale" else Severity.WARN
    label = "stale" if tier == "stale" else "unbound"
    return Violation(
        rule="DOC004",
        severity=severity,
        file=doc_path,
        line=line,
        message=(
            f"DOC004: {label} code block in {doc_path}:{line} -- {detail}; "
            f"add a frob:doc/frob:describes/frob:tests anchor, fix the stale "
            f'reference, or `frob:waive DOC004 reason="..."` if this is an '
            f"intentional external/illustrative example"
        ),
    )


# frob:doc docs/modules/gates.md#flagcov001-t-2397
# frob:tests \
# tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate.test_unresolvable_parser_\
# is_unresolved_not_a_crash kind="unit"
# frob:ticket T-2397
def resolve_dotted_symbol(
    dotted: str, *, log_prefix: str = "resolve_dotted_symbol"
) -> object | None:
    """Resolve a `module:attribute` dotted path (the same declaration shape
    `[[docblocks.commands]]`'s own `parser` key already uses, T-1195) to the
    live object itself, or `None` on any import/lookup failure -- a
    malformed/stale config entry degrades to "cannot resolve this source",
    never a crash. Generic over WHAT is resolved (a zero-arg parser-factory
    callable, a pydantic config class, ...) so a second consumer (T-2397's
    FLAGCOV001, resolving both a `parser` AND a `config` entry off the same
    `[[docblocks.commands]]` declaration) reuses this exactly rather than
    hand-rolling a second `importlib.import_module`/`getattr` pair -- the
    NO DUPLICATION rule applied to DOC004's own `_load_parser_factory`,
    which now delegates here unchanged in behavior. `log_prefix` tags the
    warning with the calling gate's own rule family so a resolution failure
    in the log is traceable to which gate hit it."""
    import importlib

    from frob.logging import get_logger

    _log = get_logger(__name__)

    module_name, _, attr = dotted.partition(":")
    if not module_name or not attr:
        _log.warning(
            "%s: malformed dotted path %r (want 'module:attribute')",
            log_prefix,
            dotted,
        )
        return None
    try:
        # frob:waive OPAQUE001 reason="T-2397: dotted is a repo-owner-authored \
        # frob.toml [[docblocks.commands]].parser/.config config value, never \
        # externally/untrusted-input controlled -- same plugin-loading justification \
        # as _load_parser_factory's own OPAQUE001 waiver (T-1185), generalized to a \
        # second consumer of the identical declaration shape"
        module = importlib.import_module(module_name)
        # frob:waive OPAQUE001 reason="T-2397: attr is the same repo-owner-authored \
        # module:attribute config value as module_name above -- same plugin-loading \
        # justification, not a second independent opacity"
        return getattr(module, attr)
    except (ImportError, AttributeError) as exc:
        _log.warning("%s: could not resolve %r: %s", log_prefix, dotted, exc)
        return None


__all__ = [
    "_ProjectNamespaces",
    "_doc004_violation",
    "_read_toml",
    "resolve_dotted_symbol",
]
