"""frob.gates._docstatus -- DOC009/DOC010/DOC011/DOC013 doc-freshness
gates (T-2843).

Split out of `frob.gates._doclink_docanchor` (T-2843, LARGE001 follow-up
to the T-2828 batch): that module's own docstring justifies only
DOC001/DOC002 (doclink_gate/docanchor_gate, a doc-tree-REACHABILITY
concern), but three more gates -- docstatus_gate (DOC009/DOC011),
docmake_gate (DOC010), docseverity_gate (DOC013) -- were bolted on later
without updating that docstring. All three share a different actual
characteristic: each is a docs/**/*.md CURRENCY/status check (a dated
status header, a Makefile target's freshness, a severity-table's
currency against `frob.toml`) rather than the reachability scan
DOC001/DOC002 share, so they get their own home here.

`docstatus_gate`/`docmake_gate`/`docseverity_gate` are re-exported from
`frob.gates` unchanged -- verified by a repo-wide grep before the move
that no code imports them directly from the old submodule path (only
`frob.gates`'s own re-export and `tests/test_gates.py`/
`tests/unit/gates/test_doc011.py`, both of which import from `frob.gates`
not this module). `docmake_gate`/`docseverity_gate` reuse
`_doclink_config`/`_obligated_docs`/`_linked_from_edges` from
`frob.gates._doclink_docanchor` -- a deliberate, pre-existing cross-module
seam (that module's own `__all__` already names `_doclink_config`/
`_obligated_docs` as consumed elsewhere, e.g. by `_sys.py`), not a new
coupling introduced by this split. `docmake_gate` also needs
`_line_index` (an offset->line helper DOC008, in the other module, needs
too) -- that name now lives in `_doclink_docanchor` and is imported here
rather than duplicated. Every other name defined here stays private to
this module."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from frob.gates._doclink_docanchor import (
    _doclink_config,
    _line_index,
    _linked_from_edges,
    _obligated_docs,
)
from frob.gates._markdown_scan import strip_code_spans as _strip_code_spans
from frob.gates._models import Severity, Violation
from frob.graph import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

# T-1232 (gate-gap class 6): a dated `Status: YYYY-MM-DD` (or
# `Status: SUPERSEDED (see <path>)`) header, checked within the first
# `_STATUS_HEADER_SCAN_LINES` lines of every docs/audits/*.md file -- audit
# docs describe a point-in-time snapshot and rot silently with no currency
# marker at all (docs/audits/docs-staleness-2026-07-29.md's own STATUS/
# CURRENCY gate-gap class).
# frob:ticket T-2843
_STATUS_HEADER_RE = re.compile(
    r"^[>\s]*\**Status:\**\s*"
    r"(?:(?P<date>\d{4}-\d{2}-\d{2})|SUPERSEDED\s*\(see\s+(?P<path>[^)]+)\))"
)
# frob:ticket T-2843
_STATUS_HEADER_SCAN_LINES = 15


# frob:ticket T-2843
def _audit_docs(root: Path) -> set[str]:
    """The docs/audits/*.md files obligated to carry a DOC009 status header."""
    return {p.relative_to(root).as_posix() for p in root.glob("docs/audits/*.md")}


# frob:ticket T-1486
# DOC011 (T-1486, gate-gap class 6 item 1, T-1232's own follow-up): a
# `T-####`/`T-draft-<hex>` id mentioned in doc PROSE must name a ticket
# that actually exists somewhere in the ledger (active or archived) --
# a typo'd or long-since-renumbered id in a doc citation reads as a real,
# followable reference but silently resolves to nothing. Deliberately
# narrower than the ticket's own "harder" stretch goal (flagging a
# mention whose STATE contradicts the prose, e.g. "tracked under T-0397"
# when T-0397 is closed): that needs NLP-grade parsing of the sentence
# around each mention to know what claim is even being made, which is a
# much larger, separately-scoped effort -- this closes the cheaper,
# unambiguous half (existence) first.
# frob:ticket T-2843
_DOC011_ID_MENTION_RE = re.compile(r"\bT-(?:\d{4}|draft-[0-9a-f]{8})\b")


# frob:waive DUP001 reason="sibling DOC010/DOC011 violation builders: same \
# Violation(...)-building shape, independently-evolving rule codes and messages \
# (DOC011 unresolved ticket-id mention vs DOC010 unresolved make-target citation)"
# frob:enforces CHK-GATE-DOC011
# frob:ticket T-2843
def _doc011_violation(doc_rel: str, line: int, ticket_id: str) -> Violation:
    """Build one DOC011 `Violation` -- a doc prose mention of a ticket id
    that does not resolve to any active or archived ticket.

    T-1486 shipped this at WARN, not ERROR, deliberately -- the first live
    run against this repo's own docs tree found 10 genuine pre-existing
    stale citations (mostly `T-draft-<hex>` ids that finalized to a real
    T-#### long ago, plus one true orphan and one illustrative example),
    entirely outside T-1486's own declared scope to fix. T-1542 closed
    that follow-up: all 10 were re-verified against the CURRENT tree --
    seven no longer contained the stale string at all (already fixed by
    unrelated intervening work), and the remaining three (two in
    docs/modules/gates.md, one in docs/strata/host.md) turned out to
    already be inside inline code spans illustrating the id SYNTAX itself
    (`_doc011_scan_doc`'s own code-span stripping already exempts these,
    matching DOC008's convention) -- not real dangling citations. With the
    count provably zero (`frob check --only docanchor`, unscoped, 0 DOC011
    findings), this promotes to ERROR: the soft landing T-1486 needed is
    no longer needed, and a real new dangling citation should fail a
    check, not just warn."""
    return Violation(
        rule="DOC011",
        severity=Severity.ERROR,
        file=doc_rel,
        line=line,
        message=(
            f"DOC011: {doc_rel}:{line} mentions {ticket_id!r}, which is not "
            f"a real ticket (not in tickets.md or tickets-archive.md) -- "
            f"typo, or the id was never finalized/was dropped without a "
            f"trace; fix the citation or drop it"
        ),
    )


# frob:ticket T-2843
def _doc011_known_ticket_ids(root: Path) -> set[str]:
    """Every ticket id that has ever existed in this repo's ledger, active
    OR archived (T-1486): late-imports `frob.tickets._store` to avoid a
    module-level `frob.gates` -> `frob.tickets` dependency this package
    does not otherwise carry. Best-effort -- a store that fails to parse
    (mid-conflict, genuinely malformed) degrades to an empty known-id set
    rather than raising, so a broken ledger never masquerades as every
    doc citation being a DOC011 finding; `gate:TICK`'s own ledger-parse
    checks are the right place for a malformed-ledger error, not this
    gate."""
    from frob.tickets._store import load_all, load_archive

    known: set[str] = set()
    active = load_all(root)
    if active.is_ok:
        known.update(active.danger_ok)
    archived = load_archive(root)
    if archived.is_ok:
        known.update(archived.danger_ok)
    return known


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _strip_code_spans/_line_index, module-local helpers the resolver cannot see through; \
# the one real raise path (file read) is caught below"
# frob:ticket T-2843
def _doc011_scan_doc(
    root: Path, doc_rel: str, known_ids: set[str]
) -> tuple[Violation, ...]:
    """Every DOC011 violation in `doc_rel`: each `T-####`/`T-draft-<hex>`
    mention in PROSE (fenced/inline code spans blanked first, same as
    DOC008's link scan, so a code example showing the id SYNTAX itself
    is never flagged) that is not in `known_ids`."""
    try:
        raw = (root / doc_rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ()
    text = _strip_code_spans(raw)
    line_index = _line_index(text)
    violations: list[Violation] = []
    seen_on_line: set[tuple[int, str]] = set()
    for match in _DOC011_ID_MENTION_RE.finditer(text):
        ticket_id = match.group(0)
        if ticket_id in known_ids:
            continue
        line = line_index(match.start())
        key = (line, ticket_id)
        if key in seen_on_line:
            continue
        seen_on_line.add(key)
        violations.append(_doc011_violation(doc_rel, line, ticket_id))
    return tuple(violations)


# frob:enforces CHK-GATE-DOC009
# frob:ticket T-2843
def _doc009_violation(doc_rel: str, message: str) -> Violation:
    """Build one DOC009 error `Violation` -- a missing or unresolvable
    status/superseded-by header on an audit doc."""
    return Violation(
        rule="DOC009", severity=Severity.ERROR, file=doc_rel, line=0, message=message
    )


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _STATUS_HEADER_RE.match, a compiled-regex match over an already-caught read_text() \
# output; a compiled pattern match cannot raise"
# frob:waive EXHAUST002 reason="T-1636: leaked KeyError traces to the resolver's \
# unconditional _SUBSCRIPT_RAISE default for text.splitlines()[:N], a list SLICE \
# (never raises KeyError, or any exception, regardless of N) that the resolver's \
# syntactic bracket scan cannot distinguish from a dict lookup"
# frob:ticket T-2843
def _doc009_check_doc(root: Path, doc_rel: str) -> Violation | None:
    """The DOC009 `Violation` for `doc_rel`, or None when a dated status
    header (or a superseded-by header whose target resolves) is found
    within its first `_STATUS_HEADER_SCAN_LINES` lines."""
    try:
        text = (root / doc_rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines()[:_STATUS_HEADER_SCAN_LINES]:
        match = _STATUS_HEADER_RE.match(line.strip())
        if match is None:
            continue
        path = match.group("path")
        if path is not None and not (root / path).exists():
            return _doc009_violation(
                doc_rel,
                f"DOC009: {doc_rel} superseded-by target {path!r} does not "
                f"resolve to a real file",
            )
        return None
    return _doc009_violation(
        doc_rel,
        f"DOC009: {doc_rel} is missing a dated status header in its first "
        f"{_STATUS_HEADER_SCAN_LINES} lines -- add 'Status: YYYY-MM-DD' or "
        f"'Status: SUPERSEDED (see <path>)'",
    )


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-3348
# frob:ticket T-2843
# frob:tests tests/test_gates.py::TestDocstatusGate.test_missing_status_header_fires_doc009  # noqa: E501
# frob:tests tests/test_gates.py::TestDocstatusGate.test_dated_status_header_passes  # noqa: E501
# frob:tests tests/test_gates.py::TestDocstatusGate.test_unresolvable_ticket_mention_fires_doc011  # noqa: E501
def docstatus_gate(root: Path) -> tuple[Violation, ...]:
    """DOC009: every `docs/audits/*.md` file needs a dated status (or
    superseded-by) header -- an audit is a point-in-time snapshot, and
    unlike code it carries no digest/hash the drift gate can compare
    against, so a currency claim has to be explicit and checkable.

    T-1486: also runs DOC011 (a `T-####`/`T-draft-<hex>` mention in ANY
    `docs/**/*.md` prose that does not resolve to a real ticket, active or
    archived) -- bundled into this same `--only docstatus` group rather
    than wired as a separate stage, since both checks are cheap, whole-
    docs-tree, repo_root-scoped scans with no shared state between them
    beyond "read every doc file once"."""
    root = Path(root)
    docs = _audit_docs(root)
    violations = [
        v
        for doc_rel in sorted(docs)
        for v in (_doc009_check_doc(root, doc_rel),)
        if v is not None
    ]
    doc011_docs = {p.relative_to(root).as_posix() for p in root.glob("docs/**/*.md")}
    known_ids = _doc011_known_ticket_ids(root)
    for doc_rel in sorted(doc011_docs):
        violations.extend(_doc011_scan_doc(root, doc_rel, known_ids))
    _log.info(
        "docstatus: %d audit doc(s), %d doc011 doc(s), %d violation(s)",
        len(docs),
        len(doc011_docs),
        len(violations),
    )
    return tuple(violations)


# T-1230 (gate-gap class 4, non-python doc targets): a `` `make <target>` ``
# citation in prose is invisible to every python-shaped pointer check
# (DOC006's kind 3 already resolves `[section]`/`[section.key]` against
# frob.toml/pyproject.toml/Cargo.toml -- this closes the sibling gap for
# Makefile recipe names specifically, the one non-python target class the
# docs-staleness sweep found rotting with no gate at all).
# frob:ticket T-2843
_MAKE_TARGET_CITATION_RE = re.compile(r"`make ([A-Za-z][\w.-]*)`")
# frob:ticket T-2843
_MAKEFILE_TARGET_RE = re.compile(r"^([A-Za-z][\w.-]*)\s*:(?!=)")


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _MAKEFILE_TARGET_RE.match, a compiled-regex match over an already-caught read_text() \
# output; a compiled pattern match cannot raise"
# frob:ticket T-2843
def _makefile_targets(makefile: Path) -> set[str]:
    """Every recipe name declared in `makefile` (`target:` lines,
    `.PHONY`/pattern/variable-assignment lines excluded)."""
    try:
        text = makefile.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    targets: set[str] = set()
    for line in text.splitlines():
        if line.startswith(("\t", "#", ".")):
            continue
        match = _MAKEFILE_TARGET_RE.match(line)
        if match:
            targets.add(match.group(1))
    return targets


# frob:ticket T-2843
def _makefiles_for_doc(root: Path, doc_rel: str) -> list[Path]:
    """T-2705: the ordered chain of Makefiles a `` `make <target>` ``
    citation in `doc_rel` resolves against -- the NEAREST `Makefile`
    walking up from the doc's own directory toward `root` (if any),
    THEN `root`'s own Makefile as a fallback (if it exists and differs
    from the nearest one already found). Consumer repos legitimately
    nest sub-projects, each with their own `Makefile` and their own docs
    describing it (e.g. `slidegen/Makefile`'s `preview:` target
    documented by `slidegen/docs/scripts.md`) -- resolving every
    citation repo-root-only made every nested project's own docs read as
    broken regardless of correctness. The root fallback keeps a nested
    doc that legitimately cites a ROOT-level target (present in root's
    Makefile but not the nested one) resolving correctly too."""
    chain: list[Path] = []
    current = (root / doc_rel).parent
    while True:
        candidate = current / "Makefile"
        if candidate.exists():
            chain.append(candidate)
            break
        if current == root or current.parent == current:
            break
        current = current.parent
    root_makefile = root / "Makefile"
    if root_makefile.exists() and root_makefile not in chain:
        chain.append(root_makefile)
    return chain


# frob:waive DUP001 reason="sibling DOC010/DOC011 violation builders: same \
# Violation(...)-building shape, independently-evolving rule codes and messages \
# (DOC011 unresolved ticket-id mention vs DOC010 unresolved make-target citation)"
# frob:ticket T-2843
def _doc010_violation(doc_rel: str, line: int, target: str) -> Violation:
    """Build one DOC010 error `Violation` -- a cited `make <target>` recipe
    that does not exist in the repo's Makefile."""
    return Violation(
        rule="DOC010",
        severity=Severity.ERROR,
        file=doc_rel,
        line=line,
        message=(
            f"DOC010: `make {target}` is not a real Makefile target "
            f"(no `{target}:` recipe)"
        ),
    )


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _line_index/_MAKE_TARGET_CITATION_RE.finditer, a module-local helper and a \
# compiled-regex scan over an already-caught read_text() output; neither can raise"
# frob:ticket T-2843
def _doc010_scan_doc(
    root: Path,
    doc_rel: str,
    target_cache: dict[Path, set[str]],
) -> list[Violation]:
    """DOC010 violations for every `` `make <target>` `` citation in
    `doc_rel` whose target does not resolve against ANY Makefile in
    `doc_rel`'s resolution chain (T-2705: nearest Makefile first, root
    Makefile as fallback -- `_makefiles_for_doc`). `target_cache` memoizes
    `_makefile_targets` per Makefile path across the whole doc scan (a
    repo-wide sweep would otherwise re-parse the same root Makefile once
    per doc)."""
    try:
        text = (root / doc_rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    makefiles = _makefiles_for_doc(root, doc_rel)
    if not makefiles:
        return []
    make_targets: set[str] = set()
    for makefile in makefiles:
        if makefile not in target_cache:
            target_cache[makefile] = _makefile_targets(makefile)
        make_targets |= target_cache[makefile]
    violations: list[Violation] = []
    line_of = _line_index(text)
    for match in _MAKE_TARGET_CITATION_RE.finditer(text):
        target = match.group(1)
        if target in make_targets:
            continue
        line = line_of(match.start())
        violations.append(_doc010_violation(doc_rel, line, target))
    return violations


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-2843
# frob:tests tests/test_gates.py::TestDocmakeGate.test_bogus_make_target_fires_doc010  # noqa: E501
# frob:tests tests/test_gates.py::TestDocmakeGate.test_real_make_target_passes  # noqa: E501
# frob:tests tests/test_gates.py::TestDocmakeGate.test_no_makefile_is_a_noop  # noqa: E501
def docmake_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC010: every `` `make <target>` `` citation in an obligated doc must
    name a real Makefile recipe -- the Makefile has no graph node of its
    own, so a renamed/removed target's doc citation was invisible to every
    other doc gate (gate-gap class 4). T-2705: resolves against the
    NEAREST Makefile to the citing doc (a nested sub-project's own
    Makefile), falling back to the repo-root Makefile -- see
    `_makefiles_for_doc`."""
    root = Path(root)
    if not (root / "Makefile").exists():
        return ()
    target_cache: dict[Path, set[str]] = {}
    include, exclude, roots = _doclink_config(root)
    docs = (
        _obligated_docs(root, include, exclude)
        | set(roots)
        | _linked_from_edges(snapshot)
    )
    violations = tuple(
        v
        for doc_rel in sorted(docs)
        for v in _doc010_scan_doc(root, doc_rel, target_cache)
    )
    _log.info("docmake: %d doc(s) scanned, %d violation(s)", len(docs), len(violations))
    return violations


# ---------------------------------------------------------------------------
# DOC013: SEVERITY TABLE (gate-gap class 4, T-2080) -- a markdown severity-
# table row's claimed severity word for a known gate code, checked against
# an explicit `[gates.severity]` override in this project's own frob.toml.
# DOC006's kind 3 (CONFIG REFERENCE) only resolves a `[section.key]`
# pointer's EXISTENCE, never a claimed VALUE against the real one (T-2080's
# own motivating example: docs/modules/arch.md's severity table called
# ARCH101 "warning" after T-0977 promoted it to `error` in frob.toml).
# ---------------------------------------------------------------------------

# frob:ticket T-2843
_SEVERITY_ROW_CODE_RE = re.compile(r"\(([A-Z]{2,10}\d{2,4})[,)]")

#: Doc-prose severity words this repo's own severity tables actually use
#: that unambiguously mean a specific `frob.toml` `[gates.severity]` value.
#: Deliberately narrow (T-2703-style closed-set hardening): a softer word
#: this repo also uses (`suggestion`, `report`) is a gate's class-coded
#: DEFAULT severity, which this check has no independent registry to
#: verify -- only the two words that map 1:1 onto a real override value
#: are compared, so an ambiguous vocabulary word is never flagged.
# frob:ticket T-2843
_SEVERITY_WORD_TO_TOML = {"error": "error", "warning": "warn", "warn": "warn"}


# frob:enforces CHK-GATE-DOC013
# frob:ticket T-2843
def _doc013_violation(
    doc_rel: str, line: int, code: str, doc_word: str, toml_value: str
) -> Violation:
    """Build one DOC013 violation -- `doc_rel`'s severity table lists
    `code` as `doc_word`, but this project's own `frob.toml` `[gates.
    severity]` explicitly overrides `code` to `toml_value`."""
    return Violation(
        rule="DOC013",
        severity=Severity.WARN,
        file=doc_rel,
        line=line,
        message=(
            f"DOC013: {doc_rel}:{line} lists {code} as `{doc_word}`, but "
            f'frob.toml [gates.severity] overrides {code} = "{toml_value}" '
            f"-- update the table or the override"
        ),
    )


# frob:ticket T-2843
def _gates_severity_overrides(root: Path) -> dict[str, str]:
    """This project's own `frob.toml` `[gates.severity]` table, or `{}` if
    absent/unreadable -- fail-open, same posture as `_load_frob_toml`."""
    path = root / "frob.toml"
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    except Exception:
        # Fail-open over a genuinely unresolvable manifest-load surprise
        # too, not just the two named cases (EXHAUST001, T-1371).
        return {}
    severity = data.get("gates", {})
    severity = severity.get("severity", {}) if isinstance(severity, dict) else {}
    return severity if isinstance(severity, dict) else {}


# frob:ticket T-2843
def _severity_table_violations(
    root: Path, doc_rel: str, severity_overrides: dict[str, str]
) -> list[Violation]:
    """DOC013 violations for every markdown table row shaped like
    `` | `name` (CODE, ...) | ... | SEVERITY_WORD | `` whose `CODE` has an
    explicit `frob.toml` `[gates.severity]` override contradicting the
    row's own claimed word (`_SEVERITY_WORD_TO_TOML`). Splits each
    candidate line on `|` rather than a single end-to-end regex -- robust
    to any number of middle cells, same posture as `_config_path_exists`
    walking structured data instead of pattern-matching prose."""
    try:
        text = (root / doc_rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    violations: list[Violation] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        code_match = _SEVERITY_ROW_CODE_RE.search(cells[0])
        if code_match is None:
            continue
        code = code_match.group(1)
        toml_value = severity_overrides.get(code)
        if toml_value is None:
            continue
        doc_word = cells[-1].lower()
        expected = _SEVERITY_WORD_TO_TOML.get(doc_word)
        if expected is None or expected == toml_value:
            continue
        violations.append(
            _doc013_violation(doc_rel, line_no, code, doc_word, toml_value)
        )
    return violations


# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/test_gates.py::TestDocseverityGate.test_mismatched_severity_row_fires_doc013  # noqa: E501
# frob:tests tests/test_gates.py::TestDocseverityGate.test_matching_severity_row_passes  # noqa: E501
# frob:tests tests/test_gates.py::TestDocseverityGate.test_no_override_is_a_noop  # noqa: E501
# frob:tests tests/test_gates.py::TestDocseverityGate.test_ambiguous_doc_word_is_never_flagged  # noqa: E501
# frob:ticket T-2843
def docseverity_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC013 (gate-gap class 4, T-2080): a markdown severity-table row's
    claimed severity word for a gate code must not contradict an explicit
    `frob.toml` `[gates.severity]` override for that same code -- closes
    the "ARCH101 is a report, not a gate" class of drift DOC006's kind 3
    (CONFIG REFERENCE) cannot see, since kind 3 only checks that a
    `[section.key]` path EXISTS, never a claimed VALUE against the real
    one. Ships at WARN (new-gate-at-WARN-first precedent, T-0688) pending
    a burn-down of any live findings, same posture DOC009/DOC012 shipped
    under before their own later promotion to ERROR."""
    root = Path(root)
    severity_overrides = _gates_severity_overrides(root)
    if not severity_overrides:
        return ()
    include, exclude, roots = _doclink_config(root)
    docs = (
        _obligated_docs(root, include, exclude)
        | set(roots)
        | _linked_from_edges(snapshot)
    )
    violations = tuple(
        v
        for doc_rel in sorted(docs)
        for v in _severity_table_violations(root, doc_rel, severity_overrides)
    )
    _log.info(
        "docseverity: %d doc(s) scanned, %d violation(s)", len(docs), len(violations)
    )
    return violations


__all__ = [
    "docstatus_gate",
    "docmake_gate",
    "docseverity_gate",
]
