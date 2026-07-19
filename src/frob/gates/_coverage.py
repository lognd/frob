"""coverage.xml parsing and the `.frob/coverage-stamp`
(docs/modules/gates.md TEST005/006).

`load_coverage` parses Cobertura-style `coverage.xml` (branch mode,
produced by `pytest-cov --cov-report=xml`) and maps line hits onto symbol
spans taken from the graph snapshot, producing per-symbol branch and
per-module line percentages. `stamp_coverage` is the only writer of
`.frob/coverage-stamp`; TEST006 (in `frob.gates`) compares that stamp
against live file hashes, so a stale or missing stamp is itself a
violation rather than a silently-passing gate.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import xml.etree.ElementTree as ET
from pathlib import Path

from typani import Err, Ok
from typani.result import Result
from typani.unit import Unit

from frob.gates._models import CoverageData, CoverageError, GateError
from frob.graph import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

_COVERAGE_XML = "coverage.xml"
_STAMP_REL = Path(".frob") / "coverage-stamp"
_SOURCE_EXTS = (".py", ".ts", ".tsx", ".rs", ".c", ".h", ".cpp")


def _sha_of(path: Path) -> str | None:
    """Sha256 hex of `path`'s bytes, `None` if unreadable."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _log.warning("_coverage: could not read %s: %s", path, exc)
        return None


def _parse_line_el(line_el: ET.Element) -> tuple[int, tuple[int, int]] | None:
    """One Cobertura `<line>` -> `(number, (hits, branch_pct))`, or None if junk."""
    try:
        number = int(line_el.get("number", "0"))
        hits = int(line_el.get("hits", "0"))
    except ValueError:
        return None
    is_branch = line_el.get("branch") == "true"
    cond_cov = line_el.get("condition-coverage", "")
    branch_pct = 100 if hits > 0 else 0
    if is_branch and cond_cov:
        try:
            branch_pct = int(cond_cov.split("(")[-1].split("%")[0].strip())
        except (ValueError, IndexError):
            branch_pct = 100 if hits > 0 else 0
    return number, (hits, branch_pct)


def _parse_class_lines(class_el: ET.Element) -> dict[int, tuple[int, int]]:
    """The per-line `{number: (hits, branch_pct)}` map for one `<class>`."""
    line_hits: dict[int, tuple[int, int]] = {}
    lines_el = class_el.find("lines")
    if lines_el is None:
        return line_hits
    for line_el in lines_el.findall("line"):
        parsed = _parse_line_el(line_el)
        if parsed is not None:
            line_hits[parsed[0]] = parsed[1]
    return line_hits


def _parse_sources(root_el: ET.Element) -> tuple[str, ...]:
    """The `<sources><source>...</source></sources>` roots Cobertura declared.

    `coverage.py`'s `--cov-report=xml` writer emits these precisely so a
    reader can re-root `<class filename="...">` (relative to whatever
    `--cov=` target was measured) back to real repo paths. Text is
    whitespace-stripped; empty entries are dropped.
    """
    sources_el = root_el.find("sources")
    if sources_el is None:
        return ()
    roots: list[str] = []
    for source_el in sources_el.findall("source"):
        text = (source_el.text or "").strip()
        if text:
            roots.append(text)
    return tuple(roots)


def _repo_relative_root(source: str, repo_root: Path) -> str | None:
    """A `<source>` entry made repo-relative and posix-normalized.

    `source` may be an absolute path (the common case -- coverage.py
    resolves `--cov=src/frob` to an absolute directory at run time) or
    already relative. An absolute source outside `repo_root` cannot be
    re-rooted (a different checkout, a CI-only path) and is dropped
    rather than guessed at.
    """
    source_path = Path(source)
    if source_path.is_absolute():
        try:
            rel = source_path.relative_to(repo_root.resolve())
        except ValueError:
            return None
        return rel.as_posix()
    return Path(source).as_posix().removeprefix("./")


def _join_candidate(root: str, raw_filename: str) -> str:
    """`root/raw_filename`, posix-joined and normalized (no `root=""` case)."""
    if not root:
        return raw_filename
    return posixpath.normpath(f"{root}/{raw_filename}")


def _score_root(
    classes: tuple[tuple[str, ET.Element], ...],
    root: str,
    known_paths: frozenset[str],
) -> int:
    """How many `<class>` filenames `root` joins onto a real, known path."""
    return sum(
        1
        for raw_filename, _el in classes
        if _join_candidate(root, raw_filename) in known_paths
    )


_ParsedClasses = tuple[
    dict[str, float], dict[str, dict[int, tuple[int, int]]], bool, tuple[str, ...]
]


def _parse_classes(
    root_el: ET.Element, repo_root: Path, known_paths: frozenset[str]
) -> _ParsedClasses:
    """`(module_line%, per-file line-hit maps, join_ok, roots_tried)`.

    Cobertura `<class filename="...">` attributes are relative to whatever
    `--cov=` target produced the report, NOT necessarily repo-relative
    (what every `frob:waive`/`frob:doc`/etc directive binds against, and
    what `_symbol_branch` below joins on). This gate ships in many sibling
    repos with different package roots, so a single hardcoded prefix would
    silently reproduce T-0148's zero-match bug everywhere but this one --
    see `_select_join_root` for the root-scoring strategy that replaces it.
    """
    classes = tuple(
        (class_el.get("filename", ""), class_el)
        for class_el in root_el.iter("class")
        if class_el.get("filename", "")
    )
    declared_roots = _parse_sources(root_el)
    candidate_roots = [
        rel
        for rel in (_repo_relative_root(src, repo_root) for src in declared_roots)
        if rel is not None
    ]
    # FALLBACK: bare filename, i.e. coverage.xml already repo-relative.
    candidate_roots.append("")

    winning_root, join_ok = _select_join_root(classes, candidate_roots, known_paths)
    module_line, hits_by_class_line = _build_class_maps(classes, winning_root)
    return module_line, hits_by_class_line, join_ok, tuple(candidate_roots)


def _select_join_root(
    classes: tuple[tuple[str, ET.Element], ...],
    candidate_roots: list[str],
    known_paths: frozenset[str],
) -> tuple[str, bool]:
    """The best-scoring candidate root and whether any root actually joined.

    Scores each candidate root (declared `<source>`s, PRIMARY, plus a bare-
    filename FALLBACK) by how many classes it resolves to a known repo
    path, and picks the highest scorer. `join_ok=False` when every root
    scores zero despite having classes/known paths to resolve against --
    `frob.gates`' TEST008 turns that into a loud violation rather than a
    silently empty map.
    """
    join_ok = True
    winning_root = candidate_roots[-1]  # bare filename until proven otherwise
    if classes and known_paths:
        scored = [
            (_score_root(classes, root, known_paths), root) for root in candidate_roots
        ]
        best_score, best_root = max(scored, key=lambda pair: pair[0])
        if best_score > 0:
            winning_root = best_root
        else:
            join_ok = False
            _log.error(
                "_parse_classes: 0/%d class(es) joined against any of %d "
                "candidate root(s) %r -- coverage data for this run will "
                "not attach to any symbol or module (TEST008)",
                len(classes),
                len(candidate_roots),
                candidate_roots,
            )
    return winning_root, join_ok


def _build_class_maps(
    classes: tuple[tuple[str, ET.Element], ...], winning_root: str
) -> tuple[dict[str, float], dict[str, dict[int, tuple[int, int]]]]:
    """`(module_line%, per-file line-hit maps)` keyed by `winning_root`-joined
    filename."""
    module_line: dict[str, float] = {}
    hits_by_class_line: dict[str, dict[int, tuple[int, int]]] = {}
    for raw_filename, class_el in classes:
        filename = _join_candidate(winning_root, raw_filename)
        line_rate = class_el.get("line-rate")
        if line_rate is not None:
            try:
                module_line[filename] = float(line_rate) * 100.0
            except ValueError:
                pass
        hits_by_class_line[filename] = _parse_class_lines(class_el)
    return module_line, hits_by_class_line


def _symbol_branch(
    snapshot: GraphSnapshot | None,
    hits_by_class_line: dict[str, dict[int, tuple[int, int]]],
) -> dict[str, float]:
    """Average per-symbol branch coverage by mapping line hits onto symbol spans."""
    symbol_branch: dict[str, float] = {}
    if snapshot is None:
        return symbol_branch
    for record in snapshot.symbols.values():
        sym_line_hits = hits_by_class_line.get(record.id.path)
        if sym_line_hits is None:
            continue
        start, end = record.span
        relevant = [
            pct for line, (hits, pct) in sym_line_hits.items() if start <= line <= end
        ]
        if relevant:
            symbol_branch[record.symref] = sum(relevant) / len(relevant)
    return symbol_branch


def _load_coverage_xml(
    xml_path: Path,
) -> Result[tuple[str, ET.ElementTree[ET.Element]], CoverageError]:
    """`(source_sha, parsed_tree)` for `xml_path`, or the load/parse error."""
    if not xml_path.exists():
        _log.warning("load_coverage: no coverage.xml at %s", xml_path)
        return Err(CoverageError.Missing)
    source_sha = _sha_of(xml_path)
    if source_sha is None:
        return Err(CoverageError.Missing)
    try:
        tree = ET.parse(xml_path)  # noqa: S314 - coverage.xml is a local build artifact
    except ET.ParseError as exc:
        _log.error("load_coverage: %s malformed: %s", xml_path, exc)
        return Err(CoverageError.Malformed)
    return Ok((source_sha, tree))


# frob:doc docs/modules/gates.md#public-api
def load_coverage(
    root: Path, snapshot: GraphSnapshot | None = None
) -> Result[CoverageData, CoverageError]:
    """Parse `coverage.xml` (Cobertura), mapping line hits onto symbol spans."""
    xml_path = root / _COVERAGE_XML
    loaded = _load_coverage_xml(xml_path)
    if loaded.is_err:
        return Err(loaded.danger_err)
    source_sha, tree = loaded.danger_ok

    known_paths = _known_repo_paths(root, snapshot)
    module_line, hits_by_class_line, join_ok, tried_roots = _parse_classes(
        tree.getroot(), root, known_paths
    )
    symbol_branch = _symbol_branch(snapshot, hits_by_class_line)

    _log.info(
        "load_coverage: %s -> %d module(s), %d symbol(s) mapped, join_ok=%s",
        xml_path,
        len(module_line),
        len(symbol_branch),
        join_ok,
    )
    return Ok(
        CoverageData(
            source_sha=source_sha,
            symbol_branch=symbol_branch,
            module_line=module_line,
            root_join_ok=join_ok,
            attempted_roots=tried_roots,
        )
    )


def _known_repo_paths(root: Path, snapshot: GraphSnapshot | None) -> frozenset[str]:
    """Repo-relative paths to validate a coverage-root join against.

    Prefers the graph snapshot's own symbol paths (exactly what
    `_symbol_branch`/downstream `frob:waive` joins need to match) since
    that is the real join target; falls back to a filesystem walk when no
    snapshot was supplied (e.g. `load_coverage` called standalone).
    """
    if snapshot is not None and snapshot.symbols:
        return frozenset(record.id.path for record in snapshot.symbols.values())
    return frozenset(_collect_file_hashes(root))


def _collect_file_hashes(root: Path) -> dict[str, str]:
    """Content-hash every tracked source file under `root` (excluded dirs pruned)."""
    file_hashes: dict[str, str] = {}
    for dirpath, _dirnames, filenames in _walk(root):
        for name in filenames:
            if not name.endswith(_SOURCE_EXTS):
                continue
            path = Path(dirpath) / name
            digest = _sha_of(path)
            if digest is not None:
                file_hashes[str(path.relative_to(root).as_posix())] = digest
    return file_hashes


# frob:doc docs/modules/gates.md#public-api
# frob:waive TEST005 reason="stamp_coverage 68.8% branch cover, debt T-0160"
def stamp_coverage(root: Path) -> Result[Unit, GateError]:
    """Record coverage.xml's sha plus current per-file content hashes as a stamp."""
    xml_path = root / _COVERAGE_XML
    source_sha = _sha_of(xml_path)
    if source_sha is None:
        _log.error("stamp_coverage: no readable coverage.xml at %s", xml_path)
        return Err(GateError.WriteFailed)

    file_hashes = _collect_file_hashes(root)
    stamp = {"source_sha": source_sha, "file_hashes": file_hashes}
    stamp_path = root / _STAMP_REL
    try:
        stamp_path.parent.mkdir(parents=True, exist_ok=True)
        stamp_path.write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        _log.error("stamp_coverage: could not write %s: %s", stamp_path, exc)
        return Err(GateError.WriteFailed)
    _log.info(
        "stamp_coverage: stamped %d file(s), source_sha=%s",
        len(file_hashes),
        source_sha[:8],
    )
    return Ok(Unit())


def _walk(root: Path):  # noqa: ANN202
    """Thin `os.walk` wrapper pruning the usual excluded directories."""
    import os

    excluded = {".git", ".venv", "node_modules", "target", "build", "dist", ".frob"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in excluded]
        yield dirpath, dirnames, filenames


# frob:doc docs/modules/gates.md#public-api
# frob:waive TEST005 reason="load_stamp 85.7% branch cover, debt T-0160"
def load_stamp(root: Path) -> dict | None:
    """The raw `.frob/coverage-stamp` document, or `None` if missing/unreadable."""
    stamp_path = root / _STAMP_REL
    if not stamp_path.exists():
        return None
    try:
        return json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("load_stamp: %s unreadable: %s", stamp_path, exc)
        return None


__all__ = ["load_coverage", "load_stamp", "stamp_coverage"]
