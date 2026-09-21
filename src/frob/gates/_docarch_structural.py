"""DOCARCH002 (T-4693): a content-BLIND structural comment/docstring
length cap, plus a citation-shape check -- the sibling T-2994 filed
because neither existing rule can host this without changing what it
means: DOCARCH001 (`frob.gates._docstring_archaeology`) is docstring-only
and keys off WORDING (change-narrative phrasing); NARR001
(`frob.gates._narrative_blocks`) only opens a block on a `# T-####:` lead
line, so it is invisible to 82% of the measured bloat (T-4691's own
measurement: 376 of 447 comment runs over 12 lines carry no leading
ticket citation at all).

Two checks, one family:

1. LENGTH CAP, CONTENT-BLIND. A `#` comment run longer than
   `[gates.docs] comment_run_max` (default 12) lines, or a docstring
   longer than `docstring_max` (default 20) lines, is a finding -- no
   wording test anywhere. Exempt BY SYNTAX, never by wording: the
   shebang/coding header, the module's leading license-header comment
   run, and a run made entirely of `# frob:` / `# noqa` / `# type:` /
   `# ruff:` / `# mypy:` directive lines (including their backslash-
   continuation payload lines).
2. TICKET CITATIONS ARE DIRECTIVES. A `T-####` appearing in a plain
   comment must be a `frob:ticket`/`frob:todo` directive, or a single-
   line `# see T-####` pointer with nothing under it. Two or more plain
   comment lines following a bare `# T-####...` citation is a finding
   (the citation is doing history's job in the wrong place) -- remedy is
   `frob narrative move`.

Ships WARN; opts into `[gates.ratchet]` (T-0569, `frob.gates._ratchet`)
so today's baseline (`frob pool snapshot DOCARCH002`) stays quiet and any
NEW over-cap run or bad citation reports at ERROR the moment it lands.
Promotion of the whole rule to ERROR-always is T-4772, once the eight
migration clusters have landed.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._ratchet import (
    load_ratchet_lock,
    ratchet_enabled_rules,
    resolve_ratchet_severity,
)
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "DOCARCH002_COMMENT_RUN_MAX_DEFAULT",
    "DOCARCH002_DOCSTRING_MAX_DEFAULT",
    "docarch_structural_gate",
    "docarch002_violations",
    "scan_comment_length",
    "scan_citation_shape",
]

# frob:doc docs/modules/gates.md#docarch002
DOCARCH002_COMMENT_RUN_MAX_DEFAULT = 12
# frob:doc docs/modules/gates.md#docarch002
DOCARCH002_DOCSTRING_MAX_DEFAULT = 20

_RULE_ID = "DOCARCH002"

_COMMENT_LINE_RE = re.compile(r"^\s*#")
_SHEBANG_RE = re.compile(r"^#!")
_CODING_RE = re.compile(r"^#.*coding[:=]\s*[-\w.]+")
_DIRECTIVE_MARKER_RE = re.compile(
    r"^\s*#\s*(frob:|noqa\b|type:|ruff:|mypy:|pyright:|!)"
)
_TICKET_ID_RE = re.compile(r"T-(?:draft-[0-9a-fA-F]+|\d+)")
_TICKET_DIRECTIVE_RE = re.compile(r"^\s*#\s*frob:(ticket|todo)\b")
_SEE_POINTER_RE = re.compile(
    r"^\s*#\s*see\s+T-(?:draft-[0-9a-fA-F]+|\d+)\b", re.IGNORECASE
)


def _docs_config(root: Path) -> tuple[int, int]:
    """`(comment_run_max, docstring_max)` from `[gates.docs]` in
    `root/frob.toml`, defaulting to `DOCARCH002_COMMENT_RUN_MAX_DEFAULT`/
    `DOCARCH002_DOCSTRING_MAX_DEFAULT` when the table or a key is absent,
    same missing-is-default posture `frob.gates._dup._dup_config` uses
    for `[dup]`."""
    toml_path = root / "frob.toml"
    comment_run_max = DOCARCH002_COMMENT_RUN_MAX_DEFAULT
    docstring_max = DOCARCH002_DOCSTRING_MAX_DEFAULT
    if not toml_path.is_file():
        return comment_run_max, docstring_max
    try:
        with toml_path.open("rb") as fh:
            docs_cfg = tomllib.load(fh).get("gates", {}).get("docs", {})
        comment_run_max = int(docs_cfg.get("comment_run_max", comment_run_max))
        docstring_max = int(docs_cfg.get("docstring_max", docstring_max))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        _log.warning("docarch_structural: frob.toml [gates.docs] unreadable: %s", exc)
    return comment_run_max, docstring_max


def _iter_comment_runs(lines: list[str]) -> list[tuple[int, int]]:
    """Contiguous `(start, end)` 0-indexed inclusive ranges of consecutive
    `#`-comment lines, with no blank-line/code-line break -- the same
    contiguous-run shape `frob.gates._narrative_blocks._iter_blocks` uses,
    generalized to open on ANY comment line rather than only a
    `# T-####:` lead."""
    runs: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        if _COMMENT_LINE_RE.match(lines[i]):
            start = i
            j = i + 1
            while j < n and _COMMENT_LINE_RE.match(lines[j]):
                j += 1
            runs.append((start, j - 1))
            i = j
        else:
            i += 1
    return runs


def _is_directive_run(run_lines: list[str]) -> bool:
    """Whether a MAJORITY (>= half) of a comment run's lines are `# frob:`/
    `# noqa`/`# type:`/`# ruff:`/`# mypy:`/`# pyright:`/`#!` directive
    lines -- majority rather than unanimity because a directive line's
    own wrapped-path continuation payload (`# frob:tests \\` + the path
    on the next line) does not itself match the marker, so a strict
    all-lines test would undercount exactly the directive blocks this
    exemption exists for. Matches T-4691's own measurement script
    (`scratchpad/struct.py`) so the shipped baseline count is the
    number this repo was actually measured at, not a re-derived one.
    Exempt BY SYNTAX (the marker), never by reading what the payload
    says."""
    if not run_lines:
        return False
    matches = sum(1 for line in run_lines if _DIRECTIVE_MARKER_RE.match(line))
    return matches >= len(run_lines) / 2


def _is_leading_header_run(start: int, lines: list[str]) -> bool:
    """Whether the run starting at `start` is the module's leading
    license/header comment block: the first comment run in the file,
    with nothing but an optional shebang/coding-cookie line before it --
    exempt by POSITION (syntax), not by what the header says."""
    for idx in range(start):
        line = lines[idx]
        if line.strip() == "":
            continue
        if _SHEBANG_RE.match(line) or _CODING_RE.match(line):
            continue
        return False
    return True


def _docstring_spans(text: str) -> list[tuple[int, int, str]]:
    """`(start_line, line_count, qualname)` for every module/class/
    function docstring in `text`, 1-indexed `start_line` -- read via the
    stdlib `ast` module directly on the raw source rather than
    `frob.lang`'s `doc_text` (`_common.py`'s own docstring: "Whitespace-
    collapse doc text so reflow never changes doc_text" -- deliberately
    NOT what a line-count cap needs). Returns `[]` on a syntax error the
    same way every other structural gate treats an unparseable file:
    silently skip, never crash the whole scan over one bad file."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    spans: list[tuple[int, int, str]] = []
    DocNode = ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
    nodes: list[tuple[DocNode, str]] = [(tree, "<module>")]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nodes.append((node, node.name))
    for node, name in nodes:
        doc = ast.get_docstring(node, clean=False)
        body = node.body
        if doc is None or not body:
            continue
        first = body[0]
        if not (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            continue
        spans.append((first.lineno, len(doc.splitlines()), name))
    return spans


# frob:enforces CHK-GATE-DOCARCH002
# frob:doc docs/modules/gates.md#docarch002
# frob:tests tests/gates/test_docarch_structural.py::TestScanCommentLength.test_flags_long_pure_algorithm_run  # noqa: E501
# frob:tests tests/gates/test_docarch_structural.py::TestScanCommentLength.test_short_run_is_quiet  # noqa: E501
# frob:tests tests/gates/test_docarch_structural.py::TestScanCommentLength.test_directive_run_is_exempt  # noqa: E501
# frob:tests tests/gates/test_docarch_structural.py::TestScanCommentLength.test_leading_license_header_is_exempt  # noqa: E501
# frob:tests tests/gates/test_docarch_structural.py::TestScanCommentLength.test_long_docstring_flagged_short_is_quiet  # noqa: E501
# frob:tests tests/gates/test_docarch_structural.py::TestScanCommentLength.test_config_override_silences_default_fixture  # noqa: E501
def scan_comment_length(
    path: Path,
    text: str,
    *,
    comment_run_max: int = DOCARCH002_COMMENT_RUN_MAX_DEFAULT,
    docstring_max: int = DOCARCH002_DOCSTRING_MAX_DEFAULT,
) -> tuple[Violation, ...]:
    """DOCARCH002 check 1: every `#` comment run over `comment_run_max`
    lines (excluding the shebang/coding header, the leading license run,
    and directive runs), plus every module/class/function docstring over
    `docstring_max` lines. Pure function of `text` (both halves), mirroring
    `frob.gates._narrative_blocks.scan_narrative_blocks`'s no-filesystem
    posture so fixtures can call it directly."""
    lines = text.splitlines()
    violations: list[Violation] = []
    for start, end in _iter_comment_runs(lines):
        length = end - start + 1
        if length <= comment_run_max:
            continue
        run_lines = lines[start : end + 1]
        if _is_directive_run(run_lines):
            continue
        if _is_leading_header_run(start, lines):
            continue
        violations.append(
            Violation(
                rule=_RULE_ID,
                severity=Severity.WARN,
                file=str(path),
                line=start + 1,
                message=(
                    f"DOCARCH002: {length}-line comment run (over the "
                    f"{comment_run_max}-line cap) -- move history to the "
                    "ticket (`frob narrative move`) or explanation to "
                    "docs/modules with a `frob:doc` pointer"
                ),
            )
        )

    for doc_line, doc_len, name in _docstring_spans(text):
        if doc_len <= docstring_max:
            continue
        violations.append(
            Violation(
                rule=_RULE_ID,
                severity=Severity.WARN,
                file=str(path),
                line=doc_line,
                message=(
                    f"DOCARCH002: {doc_len}-line docstring (over "
                    f"the {docstring_max}-line cap) on {name} -- "
                    "move history to the ticket (`frob narrative move`) "
                    "or explanation to docs/modules with a `frob:doc` "
                    "pointer"
                ),
                symref=f"{path.as_posix()}::{name}",
            )
        )
    return tuple(violations)


# frob:doc docs/modules/gates.md#docarch002
# frob:tests tests/gates/test_docarch_structural.py::TestScanCitationShape.test_directive_and_pointer_are_quiet  # noqa: E501
# frob:tests tests/gates/test_docarch_structural.py::TestScanCitationShape.test_bare_citation_with_prose_is_flagged  # noqa: E501
def scan_citation_shape(path: Path, text: str) -> tuple[Violation, ...]:
    """DOCARCH002 check 2: a `T-####` cited in a plain comment must be a
    `frob:ticket`/`frob:todo` directive, or a single-line `# see T-####`
    pointer with nothing under it. Two or more plain comment lines
    following a bare citation line is flagged; remedy is `frob narrative
    move`."""
    lines = text.splitlines()
    n = len(lines)
    violations: list[Violation] = []
    i = 0
    while i < n:
        line = lines[i]
        if (
            _COMMENT_LINE_RE.match(line)
            and _TICKET_ID_RE.search(line)
            and not _TICKET_DIRECTIVE_RE.match(line)
            and not _SEE_POINTER_RE.match(line)
        ):
            j = i + 1
            while j < n and _COMMENT_LINE_RE.match(lines[j]):
                j += 1
            lines_under = j - (i + 1)
            if lines_under >= 2:
                violations.append(
                    Violation(
                        rule=_RULE_ID,
                        severity=Severity.WARN,
                        file=str(path),
                        line=i + 1,
                        message=(
                            "DOCARCH002: a T-#### citation with "
                            f"{lines_under} comment lines under it -- a "
                            "citation must be a frob:ticket/frob:todo "
                            "directive or a single-line '# see T-####' "
                            "pointer; move the prose with `frob narrative "
                            "move`"
                        ),
                    )
                )
            i = j
        else:
            i += 1
    return tuple(violations)


# frob:doc docs/modules/gates.md#docarch002
# frob:tests tests/gates/test_docarch_structural.py::TestDocarch002RatchetSeverity.test_baselined_finding_stays_warn_new_one_errors  # noqa: E501
def docarch002_violations(root: Path) -> tuple[Violation, ...]:
    """DOCARCH002 over every tracked `.py` file under `root`: both checks,
    ratchet-adjusted (T-0569) when `DOCARCH002` is opted into
    `[gates.ratchet] rules` -- a baselined finding key (`file:line`) stays
    WARN, anything new reports ERROR."""
    from frob.gates._tracked_files import tracked_files as _shared_tracked_files

    comment_run_max, docstring_max = _docs_config(root)
    tracked = _shared_tracked_files(root, caller="docarch_structural_gate")
    enabled = ratchet_enabled_rules(root)
    lock = load_ratchet_lock(root) if _RULE_ID in enabled else None

    violations: list[Violation] = []
    for rel in tracked:
        if not rel.endswith(".py"):
            continue
        full = root / rel
        try:
            text = full.read_text(encoding="utf-8")
        except OSError:
            continue
        found = scan_comment_length(
            Path(rel),
            text,
            comment_run_max=comment_run_max,
            docstring_max=docstring_max,
        )
        found += scan_citation_shape(Path(rel), text)
        for violation in found:
            severity = Severity.WARN
            if lock is not None:
                key = f"{violation.file}:{violation.line}"
                severity = Severity(resolve_ratchet_severity(_RULE_ID, key, lock))
            violations.append(violation.model_copy(update={"severity": severity}))
    _log.debug(
        "docarch_structural: %d DOCARCH002 violation(s) under %s", len(violations), root
    )
    return tuple(violations)


# frob:doc docs/modules/gates.md#docarch002
# frob:tests tests/gates/test_docarch_structural.py::TestGateEntry.test_delegates
def docarch_structural_gate(root: Path) -> tuple[Violation, ...]:
    """Entry point for wiring into `frob.gates.__init__`'s `GATE_RUNNERS`
    -- see this ticket's Done report for the (deferred, `gates/__init__.py`
    is leased by T-3962) registration hunk. Thin alias kept so the wiring
    commit, once landed, is a one-line dict entry rather than a rename."""
    return docarch002_violations(root)
