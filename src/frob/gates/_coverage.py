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


def _parse_classes(
    root_el: ET.Element,
) -> tuple[dict[str, float], dict[str, dict[int, tuple[int, int]]]]:
    """`(module_line%, per-file line-hit maps)` over every `<class>` element."""
    module_line: dict[str, float] = {}
    hits_by_class_line: dict[str, dict[int, tuple[int, int]]] = {}
    for class_el in root_el.iter("class"):
        filename = class_el.get("filename", "")
        if not filename:
            continue
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


# frob:doc docs/modules/gates.md#public-api
def load_coverage(
    root: Path, snapshot: GraphSnapshot | None = None
) -> Result[CoverageData, CoverageError]:
    """Parse `coverage.xml` (Cobertura), mapping line hits onto symbol spans."""
    xml_path = root / _COVERAGE_XML
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

    module_line, hits_by_class_line = _parse_classes(tree.getroot())
    symbol_branch = _symbol_branch(snapshot, hits_by_class_line)

    _log.info(
        "load_coverage: %s -> %d module(s), %d symbol(s) mapped",
        xml_path,
        len(module_line),
        len(symbol_branch),
    )
    return Ok(
        CoverageData(
            source_sha=source_sha, symbol_branch=symbol_branch, module_line=module_line
        )
    )


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
