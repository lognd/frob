"""coverage.xml parsing and the `.frob/coverage-stamp`
(docs/modules/gates.md TEST005/006).

`load_coverage` parses Cobertura-style `coverage.xml` (branch mode,
produced by `pytest-cov --cov-report=xml`) and maps line hits onto symbol
spans taken from the graph snapshot, producing per-symbol branch and
per-module line percentages. `stamp_coverage` is the only writer of
`.frob/coverage-stamp`; TEST006 (in `frob.gates`) compares that stamp
against live file hashes, so a stale or missing stamp is itself a
violation rather than a silently-passing gate.

T-0545 (docs/audits/gates-accounting.md B5): `.frob/coverage-stamp` and
`coverage.xml` are both gitignored, so a fresh CI checkout (or a reviewer
reading a diff) has no committed artifact to verify a coverage claim
against -- the whole TEST005/006 story is locally-trusted-only.
`write_coverage_lock` addresses this narrowly: it writes a small, rounded,
deterministic SUMMARY (never the raw xml) to `frob-coverage.lock.json` at
the repo root, a path this module chose specifically because no existing
`.gitignore` rule matches it, so it is committed by default. `stamp_coverage`
calls it automatically, so any existing `--stamp-coverage` invocation now
also refreshes the committed lock with no new CLI wiring. `coverage_lock_diff`
lets a gate (TEST012, `frob.gates`) compare the lock's claimed numbers
against a freshly-loaded `CoverageData` and flag drift beyond tolerance --
e.g. a lock committed from a locally-inflated coverage.xml that a genuine
CI run cannot reproduce.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import json
import os
import posixpath
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from typani import Err, Ok
from typani.result import Result
from typani.unit import Unit

from frob.excludes import is_excluded, load_exclude_globs
from frob.gates._filehash import _collect_file_hashes, _sha_of
from frob.gates._models import CoverageData, CoverageError, GateError
from frob.graph import GraphSnapshot
from frob.logging import get_logger
from frob.tickets._worktree_guard import enforce_worktree_lease

_log = get_logger(__name__)

_COVERAGE_XML = "coverage.xml"
_STAMP_REL = Path(".frob") / "coverage-stamp"
# T-0545: deliberately NOT under `.frob/` or any other gitignored path --
# this is the one artifact in the coverage chain meant to be committed.
_LOCK_REL = Path("frob-coverage.lock.json")
# Percentage-point tolerance before `coverage_lock_diff` reports a module as
# drifted; coverage.xml's own line-rate float noise (rounding, differently
# ordered subprocess merges) is well under this in practice.
_LOCK_TOLERANCE = 2.0
# T-1375: a per-worktree, gitignored (under `.frob/`) append-only audit trail
# of every successful `write_coverage_lock` call -- a durable, on-disk record
# that survives independent of any one terminal's scrollback. A committed
# `frob-coverage.lock.json` changing with NO matching entry here (same
# `source_sha`, a write in this worktree's own history) means the write did
# NOT go through this module's own logged path -- an unattributed mutation,
# not proof the numbers are wrong, but proof the CLAIM "an explicit
# stamp_coverage call wrote this" cannot currently be verified for it.
_LOCK_AUDIT_REL = Path(".frob") / "coverage-lock-audit.log"


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
            # frob:ticket T-1376
            # The Cobertura value is "<pct>% (<covered>/<total>)", so the
            # percentage is the text BEFORE the '%'. Splitting on '(' first
            # (the pre-T-1376 form) yielded "1/2)", int() raised every time,
            # and the except branch below silently degraded every branch
            # line to hit/not-hit -- measured on this repo, the parser
            # emitted only 0 and 100 while 1324 lines were genuinely partial.
            branch_pct = int(cond_cov.split("%")[0].strip())
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
    module_line, hits_by_class_line = _build_class_maps(
        classes, winning_root, candidate_roots, known_paths
    )
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


def _resolve_class_root(
    raw_filename: str, candidate_roots: list[str], known_paths: frozenset[str]
) -> str | None:
    """The first `candidate_roots` entry `raw_filename` actually resolves
    under, or `None` if it matches no known repo path under any of them.

    T-0311: a package-relative `raw_filename` (e.g. `actgen/core.py`) can be
    ambiguous between multiple `--cov` roots when neither root's joined path
    disambiguates it on its own -- a single per-report "winning root" (as
    `_select_join_root` computes for TEST008 signaling) can then mislabel a
    file that actually lives under a DIFFERENT root than the one that won
    the aggregate vote. Resolving PER CLASS against `known_paths` (which is
    only ever populated with paths to files that genuinely exist -- graph
    symbols or a filesystem walk, see `_known_repo_paths`) picks the root
    this specific file truly exists under, independent of how other classes
    in the same report happened to score.
    """
    for root in candidate_roots:
        if _join_candidate(root, raw_filename) in known_paths:
            return root
    return None


def _build_class_maps(
    classes: tuple[tuple[str, ET.Element], ...],
    winning_root: str,
    candidate_roots: list[str],
    known_paths: frozenset[str],
) -> tuple[dict[str, float], dict[str, dict[int, tuple[int, int]]]]:
    """`(module_line%, per-file line-hit maps)` keyed by the per-class-resolved
    filename.

    Each class is joined against the specific candidate root it actually
    resolves under (`_resolve_class_root`); `winning_root` (the aggregate
    per-report scorer's pick) is only a fallback for classes that resolve
    under none of the candidates, matching the pre-T-0311 behavior for the
    join-failure case TEST008 already reports loudly.
    """
    module_line: dict[str, float] = {}
    hits_by_class_line: dict[str, dict[int, tuple[int, int]]] = {}
    for raw_filename, class_el in classes:
        class_root = _resolve_class_root(raw_filename, candidate_roots, known_paths)
        filename = _join_candidate(
            class_root if class_root is not None else winning_root, raw_filename
        )
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


# frob:ticket T-0464
def _newest_source_mtime(root: Path, snapshot: GraphSnapshot | None) -> float | None:
    """The most recent on-disk mtime among files the graph snapshot knows about,
    or `None` if there is no snapshot (freshness cannot be judged standalone).

    `CoverageData.source_sha` only hashes coverage.xml itself, not the
    source it measured, so nothing else in this module detects a
    coverage.xml older than the working tree it is supposed to describe.
    """
    if snapshot is None or not snapshot.symbols:
        return None
    newest: float | None = None
    for path in {record.id.path for record in snapshot.symbols.values()}:
        try:
            mtime = (root / path).stat().st_mtime
        except OSError:
            continue
        if newest is None or mtime > newest:
            newest = mtime
    return newest


# frob:ticket T-0464
# frob:ticket T-1406
def _module_join_fraction(
    module_line: dict[str, float], known_paths: frozenset[str]
) -> float:
    """Share of known `.py` modules that actually appear in `module_line`.

    A run that silently drops subprocess coverage (T-0464's root cause)
    only measures the main pytest process, so most modules never show up
    in coverage.xml at all even when `root_join_ok` is True (SOME data
    joined) -- this is the deflation fingerprint that `root_join_ok` alone
    misses. `1.0` (nothing to flag) when there are no known `.py` modules
    to compare against.

    T-1406: `known_paths` is expected to already be scoped to whatever
    root(s) coverage.xml's own `--cov=` target could ever report on
    (`_scope_known_paths_to_coverage_roots`, applied by `load_coverage`
    before calling this) -- this function itself does no scoping of its
    own, it just divides. Passing an unscoped, repo-wide `known_paths`
    (every `tests/**`/script `.py` file included, none of them ever
    instrumentable under a `--cov=src/frob` run) structurally deflates
    this fraction for reasons that have nothing to do with the run's
    actual health; that was T-1406's own finding (measured: 447/851=0.53,
    suspiciously close to `_DEFLATION_FLOOR` for a healthy run).
    """
    known_python_paths = frozenset(p for p in known_paths if p.endswith(".py"))
    if not known_python_paths:
        return 1.0
    return len(module_line.keys() & known_python_paths) / len(known_python_paths)


# frob:ticket T-1406
def _scope_known_paths_to_coverage_roots(
    known_paths: frozenset[str], declared_roots: tuple[str, ...]
) -> frozenset[str]:
    """`known_paths` filtered down to whatever `declared_roots` coverage.xml's
    own `<sources><source>` elements name (repo-relative, via
    `_repo_relative_root`) -- the set of paths a `--cov=<root>` run could
    EVER report on, structurally (T-1406).

    `_known_repo_paths` returns every `.py` (or graph-known) module in the
    repo, unconditionally -- `tests/**`, scripts, everything -- because it
    also serves the coverage-ROOT-JOIN heuristic (`_select_join_root`),
    which genuinely needs the full set to disambiguate which `--cov` root a
    given `<class filename=...>` resolves under. `module_join_fraction`'s
    DENOMINATOR has a narrower, different job: "how much of what this run
    COULD have measured did it actually measure" -- a module `--cov` could
    never touch in the first place is not something the run "dropped," and
    counting it against the run structurally deflates the fraction no
    matter how healthy the run is (T-1406's own measurement: `make coverage`
    runs `pytest --cov=src/frob`, so `tests/**` can never join, yet the
    unscoped denominator counted it anyway -- 447/851=0.53, next door to
    `_DEFLATION_FLOOR`, for a run with nothing wrong).

    `declared_roots` empty (no `<sources>` block, or every entry unresolvable
    against this checkout -- `_repo_relative_root` returning `None` for all
    of them) returns `known_paths` UNCHANGED: with no root information to
    scope against, the old repo-wide behavior is the only one available,
    and the `_DEFLATION_FLOOR` comparison degrades to that meaning again
    rather than dividing by an empty set.
    """
    if not declared_roots:
        return known_paths
    normalized_roots = tuple(r for r in declared_roots if r)
    if not normalized_roots:
        return known_paths
    return frozenset(
        p
        for p in known_paths
        if any(p == r or p.startswith(f"{r}/") or r == "" for r in normalized_roots)
    )


# T-1401: acceptance[2] -- a module that genuinely cannot be joined against
# coverage.xml must surface as an explicit, enumerated diagnostic, never a
# silent omission folded into a bare `module_join_fraction` float. A
# percentage alone tells a reader THAT something is missing, not WHICH
# modules -- exactly the gap that let a stale/carried-over lock value go
# unnoticed until directly diffed against the raw xml (this ticket).
_UNJOINED_LOG_THRESHOLD = 0.95


def _unjoined_python_modules(
    module_line: dict[str, float], known_paths: frozenset[str]
) -> tuple[str, ...]:
    """Known `.py` modules that do NOT appear in `module_line`, sorted.

    The explicit complement `_module_join_fraction`'s bare ratio omits --
    every module in this tuple failed to join against coverage.xml for
    this run.
    """
    known_python_paths = frozenset(p for p in known_paths if p.endswith(".py"))
    return tuple(sorted(known_python_paths - module_line.keys()))


# frob:doc docs/modules/gates.md#public-api
# frob:waive AFFECT001 reason="T-1401 added the unjoined-module enumeration log below \
# the 0.95 join-fraction threshold; docs/modules/gates.md#public-api needs a matching \
# update but docs/** was held by T-1235's concurrent in-progress lease for this \
# ticket's whole duration -- tracked as T-1405, land the doc update there"
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

    try:
        xml_mtime = xml_path.stat().st_mtime
    except OSError:
        xml_mtime = None
    newest_source_mtime = _newest_source_mtime(root, snapshot)
    stale_by_mtime = (
        xml_mtime is not None
        and newest_source_mtime is not None
        and xml_mtime < newest_source_mtime
    )
    # T-1406: scope the join-fraction denominator to whatever root(s)
    # coverage.xml's own <sources> declares -- NOT `known_paths` unscoped,
    # which counts every .py file in the repo (tests/**, scripts) even
    # though a --cov=<root> run can structurally never report on anything
    # outside that root. `_parse_classes` above still gets the UNSCOPED
    # `known_paths` (it needs the full set for root-join disambiguation);
    # only the deflation-floor denominator narrows.
    declared_roots = tuple(
        rel
        for rel in (
            _repo_relative_root(src, root) for src in _parse_sources(tree.getroot())
        )
        if rel is not None
    )
    scoped_known_paths = _scope_known_paths_to_coverage_roots(
        known_paths, declared_roots
    )
    join_fraction = _module_join_fraction(dict(module_line), scoped_known_paths)
    if join_fraction < _UNJOINED_LOG_THRESHOLD:
        unjoined = _unjoined_python_modules(dict(module_line), scoped_known_paths)
        _log.warning(
            "load_coverage: %s -> module_join_fraction=%.2f below %.2f -- "
            "%d known .py module(s) did not join against coverage.xml: %s",
            xml_path,
            join_fraction,
            _UNJOINED_LOG_THRESHOLD,
            len(unjoined),
            unjoined,
        )

    _log.info(
        "load_coverage: %s -> %d module(s), %d symbol(s) mapped, join_ok=%s, "
        "stale_by_mtime=%s, module_join_fraction=%.2f",
        xml_path,
        len(module_line),
        len(symbol_branch),
        join_ok,
        stale_by_mtime,
        join_fraction,
    )
    return Ok(
        CoverageData(
            source_sha=source_sha,
            symbol_branch=symbol_branch,
            module_line=module_line,
            root_join_ok=join_ok,
            attempted_roots=tried_roots,
            stale_by_mtime=stale_by_mtime,
            module_join_fraction=join_fraction,
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


# frob:ticket T-0997
# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/test_gates.py::TestCoverageLoad.test_stamp_coverage_lock_excludes_graph_excluded_modules  # noqa: E501
def exclude_filtered_coverage(
    data: CoverageData, snapshot: GraphSnapshot
) -> CoverageData:
    """Re-filter `data` against `[graph] exclude`.

    `coverage.xml` is produced straight from whatever `pytest --cov`
    walked, so it does not honor `[graph] exclude` (T-0148) the way
    `frob.graph`'s own walk does -- e.g. `src/frob/scaffold/data/**`
    (jinja templates rendered into OTHER repos, never imported/executed
    here) shows up as near-random "line coverage" of template source
    text. Re-filtering `data.module_line`/`.symbol_branch` here, against
    the same excludes every other file-walking surface already respects
    (`frob.excludes`), keeps TEST005 measuring only this package's own
    maintained modules.

    T-0997: lives here (not `frob.gates`) so `stamp_coverage` below can call
    the SAME filter the TEST012 gate check applies before writing the
    committed lock -- previously the lock was written from unfiltered data
    while the gate compared against filtered data, so every excluded path
    (e.g. 22 scaffold `.j2` templates) read as permanent, unfixable drift.
    `frob.gates` re-exports this under its old private name for the one
    external call site that still imports it from there.
    """
    exclude_globs = load_exclude_globs(Path(snapshot.root))
    if not exclude_globs:
        return data
    return CoverageData(
        source_sha=data.source_sha,
        symbol_branch={
            symref: pct
            for symref, pct in data.symbol_branch.items()
            if not is_excluded(symref.split("::", 1)[0], exclude_globs)
        },
        module_line={
            path: pct
            for path, pct in data.module_line.items()
            if not is_excluded(path, exclude_globs)
        },
        root_join_ok=data.root_join_ok,
        attempted_roots=data.attempted_roots,
        stale_by_mtime=data.stale_by_mtime,
        module_join_fraction=data.module_join_fraction,
    )


# T-1180: extends TEST011's `_TEST011_JOIN_FLOOR` (WARN-advisory, in
# `frob.gates`) into a hard, stamp-time refusal here -- three consecutive
# `make coverage` runs produced a coverage.xml that stamped clean despite
# deflated/dropped subprocess data, because TEST011 only warns AFTER the
# fact, once a bad stamp is already on disk and TEST005 is already trusting
# it. Same threshold as TEST011 by design (one floor, not two to keep in
# sync); duplicated as a constant here (not imported from `frob.gates`,
# which imports FROM this module) rather than risk a circular import.
#
# T-1406: the fraction this floor compares against is scoped to whatever
# root(s) coverage.xml's own <sources> block declares
# (`_scope_known_paths_to_coverage_roots`, applied in `load_coverage`
# before `module_join_fraction` is computed) -- NOT every `.py` file in
# the repo. Before T-1406, a healthy `--cov=src/frob` run's own denominator
# included `tests/**` and every other non-instrumentable path, permanently
# deflating the fraction toward this floor for reasons unrelated to run
# health (measured: 447/851=0.53, immediately above 0.5, purely from
# counting files `--cov` could never report on). When `<sources>` is
# missing or none of its entries resolve against this checkout, scoping
# falls back to the old repo-wide denominator (documented in
# `_scope_known_paths_to_coverage_roots`'s own docstring) -- this floor
# still holds in that degraded case, just against the wider, noisier
# fraction it always compared against pre-T-1406.
_DEFLATION_FLOOR = 0.5

# T-1180: a real, tiny repo (or the many test fixtures that build a
# one-or-two-file snapshot and call `stamp_coverage` against a deliberately
# minimal/empty `coverage.xml` to exercise unrelated behavior -- e.g.
# `tests/system/test_cli_check.py::test_only_gates_passes_once_bound_and_
# tested`) can legitimately have `module_join_fraction == 0.0` with no
# deflation involved: there is nothing to "drop" when there was only ever
# one module to begin with. The floor only means something once there are
# enough known modules that a near-zero join fraction can only plausibly
# come from a run that silently failed to merge, not from a small sample
# size -- below this count, skip the check entirely (pre-T-1180 behavior:
# still stamps, still refreshes the lock from whatever joined).
_DEFLATION_MIN_KNOWN_MODULES = 20

# frob:ticket T-1435
# T-1435 (T-1407 finding 2): a burn-down agent's own scoped `pytest --cov`
# run (section 6b of docs/guides/agent-playbook.md -- the sanctioned
# workaround for "don't run `make coverage` as a sub-agent") leaves a
# narrow coverage.xml on disk that measures only a handful of touched
# modules. `_DEFLATION_FLOOR` alone does not catch this: a locally-scoped
# run can join 100% of the FEW modules it measured (module_join_fraction
# reads clean) while still covering only a sliver of what the last full
# `make coverage` run covered -- the floor above compares a run against
# itself, never against history. This ratio instead compares the CURRENT
# run's joined module count against the last COMMITTED
# `frob-coverage.lock.json`'s module count: a full run replacing a full
# run keeps this ratio near 1.0; a scoped run masquerading as a full one
# collapses it. `0.5` mirrors `_DEFLATION_FLOOR`'s own threshold choice
# (one floor value repo-wide, not two independently-tuned numbers to keep
# in sync) -- deliberately conservative, since incremental `make
# coverage-fast` runs (T-0484) can legitimately measure a proper subset in
# between full runs and must not trip this on every ordinary use.
_PROVENANCE_MIN_MODULE_RATIO = 0.5


# frob:ticket T-1435
def _provenance_drop(root: Path, current_module_count: int) -> tuple[int, float] | None:
    """`(committed_count, ratio)` if the current coverage.xml's joined
    module count looks like a locally-scoped run being misread as a full
    one (T-1435), else `None`.

    Reads the last COMMITTED `frob-coverage.lock.json` (never the current,
    possibly-scoped run's own numbers) as the historical baseline. Returns
    `None` (nothing to flag) whenever there is no committed lock yet, the
    lock predates enough known modules to mean anything
    (`_DEFLATION_MIN_KNOWN_MODULES`, the same sample-size floor
    `_filtered_coverage_or_deflated` already applies), or the ratio is at
    or above `_PROVENANCE_MIN_MODULE_RATIO`.
    """
    lock = load_coverage_lock(root)
    if not lock:
        return None
    committed_line = lock.get("module_line") or {}
    committed_count = len(committed_line)
    if committed_count < _DEFLATION_MIN_KNOWN_MODULES:
        return None
    ratio = current_module_count / committed_count
    if ratio >= _PROVENANCE_MIN_MODULE_RATIO:
        return None
    return (committed_count, ratio)


# frob:ticket T-1435
# frob:tests tests/test_gates.py::TestCoverageLoad.test_stamp_coverage_refuses_below_deflation_floor  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageLoad.test_stamp_coverage_deflation_floor_skipped_below_min_known_modules  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageLoad.test_stamp_coverage_refuses_locally_scoped_run_via_provenance_drop  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageLoad.test_stamp_coverage_provenance_check_skipped_without_committed_lock  # noqa: E501
def _filtered_coverage_or_deflated(
    root: Path, snapshot: GraphSnapshot
) -> Result[CoverageData | None, GateError]:
    """`stamp_coverage`'s T-1180 pre-stamp check, split out to keep
    `stamp_coverage` itself under ARCH001's line threshold.

    Loads and `[graph] exclude`-filters `coverage.xml` against `snapshot`,
    then refuses (`Err(GateError.CoverageDeflated)`) when
    `module_join_fraction` falls below `_DEFLATION_FLOOR` -- the same
    signal TEST011 only warns about, promoted here to a hard refusal so a
    deflated coverage.xml can never produce a clean-looking stamp. Skipped
    entirely below `_DEFLATION_MIN_KNOWN_MODULES` known `.py` modules (see
    that constant's docstring -- a small repo/fixture's low join fraction
    is sample-size noise, not deflation). A `load_coverage` failure
    degrades to `Ok(None)` (stamp still proceeds, just without the lock
    refresh) rather than blocking the stamp on a parse problem unrelated
    to deflation.
    """
    loaded = load_coverage(root, snapshot)
    if loaded.is_err:
        _log.warning(
            "stamp_coverage: could not load coverage.xml to check the "
            "deflation floor (%s); stamping without the lock refresh",
            loaded.danger_err,
        )
        return Ok(None)
    # T-0997: filter through `[graph] exclude` (the same filter
    # `frob.gates`' TEST012 gate applies to the LIVE CoverageData it
    # diffs against) before writing the lock -- otherwise this write
    # path and the gate-time read path disagree about what counts
    # as a "module", and TEST012 permanently flags every excluded
    # path (e.g. `src/frob/scaffold/data/**`'s .j2 templates,
    # 22 of them observed) as drift no re-stamp can ever clear.
    filtered = exclude_filtered_coverage(loaded.danger_ok, snapshot)
    # T-1435: checked BEFORE the sample-size skip below -- this check has
    # its own independent gate (the committed lock's own module count,
    # `_DEFLATION_MIN_KNOWN_MODULES`-checked inside `_provenance_drop`
    # itself), not the CURRENT tree's known-module count. A locally-scoped
    # run's tree can legitimately look tiny (few known modules -> the
    # sample-size skip below would fire) while the committed lock it is
    # about to silently narrow was built from a real, large, full run --
    # exactly the shape this check exists to catch, so it must not be
    # skipped just because today's checkout looks small.
    drop = _provenance_drop(root, len(filtered.module_line))
    if drop is not None:
        committed_count, ratio = drop
        _log.error(
            "stamp_coverage: refusing to stamp -- coverage.xml joins only "
            "%d module(s), %.0f%% of the %d module(s) the last committed "
            "%s recorded (floor %.0f%%); this looks like a locally-scoped "
            "coverage.xml (e.g. a burn-down agent's own `pytest --cov` "
            "run, docs/guides/agent-playbook.md section 6b) being read as "
            "if it were a full run's data -- re-run: make coverage",
            len(filtered.module_line),
            ratio * 100,
            committed_count,
            _LOCK_REL,
            _PROVENANCE_MIN_MODULE_RATIO * 100,
        )
        return Err(GateError.CoverageDeflated)
    known_python_modules = sum(
        1 for p in _known_repo_paths(root, snapshot) if p.endswith(".py")
    )
    if known_python_modules < _DEFLATION_MIN_KNOWN_MODULES:
        _log.debug(
            "stamp_coverage: only %d known .py module(s) (< %d) -- "
            "skipping the T-1180 deflation floor as sample-size noise",
            known_python_modules,
            _DEFLATION_MIN_KNOWN_MODULES,
        )
        return Ok(filtered)
    if filtered.module_join_fraction < _DEFLATION_FLOOR:
        _log.error(
            "stamp_coverage: refusing to stamp -- coverage.xml only "
            "joins %.0f%% of known modules (floor %.0f%%), looks "
            "deflated (e.g. subprocess coverage not merged); "
            "re-run: make coverage",
            filtered.module_join_fraction * 100,
            _DEFLATION_FLOOR * 100,
        )
        return Err(GateError.CoverageDeflated)
    return Ok(filtered)


# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/test_gates.py::TestCoverageLoad.test_stamp_coverage_refuses_below_deflation_floor  # noqa: E501
def stamp_coverage(
    root: Path, snapshot: GraphSnapshot | None = None
) -> Result[Unit, GateError]:
    """Record coverage.xml's sha plus current per-file content hashes as a stamp.

    T-0545: also refreshes the committed `frob-coverage.lock.json` summary
    (`write_coverage_lock`) from the same `coverage.xml`, so every existing
    `--stamp-coverage` call keeps the attestable artifact current with zero
    new CLI wiring. `snapshot` is optional and only improves the lock's
    per-module numbers (`load_coverage` needs it to map line hits onto
    modules/symbols); a caller with no snapshot handy still gets a stamp,
    just without a lock refresh.

    T-1180: when a `snapshot` IS supplied, this also checks the same
    `module_join_fraction` deflation signal TEST011 warns about, but as a
    hard pre-stamp floor -- a coverage.xml that joined too small a share of
    known modules (the fingerprint of a run that silently dropped
    subprocess coverage) is refused outright (`Err(GateError.
    CoverageDeflated)`, no stamp/lock written at all) rather than stamped
    and only flagged after the fact. No snapshot means no floor check
    (same as the pre-existing lock-refresh skip) -- the caller opted out of
    graph-aware checks entirely.
    """
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(GateError.WorktreeLeaseViolation)
    xml_path = root / _COVERAGE_XML
    source_sha = _sha_of(xml_path)
    if source_sha is None:
        _log.error("stamp_coverage: no readable coverage.xml at %s", xml_path)
        return Err(GateError.WriteFailed)

    filtered: CoverageData | None = None
    if snapshot is not None:
        checked = _filtered_coverage_or_deflated(root, snapshot)
        if checked.is_err:
            return Err(checked.danger_err)
        filtered = checked.danger_ok

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
    if filtered is not None:
        write_coverage_lock(root, filtered)
    return Ok(Unit())


# T-1363: `frob-coverage.lock.json` holds committed coverage-ratchet FLOORS
# (docs/audits/gates-accounting.md B5) -- a failed/partial `make coverage`
# run rewrote these downward twice in one day (src/frob/app/__init__.py
# 76.5% -> 16.2%), which would have permanently lowered the repo's quality
# floor through a file nobody reviews had it been committed. A module
# dropping by more than `_LOCK_TOLERANCE` points in one `write_coverage_lock`
# call is clamped to its prior committed value (unless `allow_decrease=True`)
# rather than silently accepted -- a real, deliberate re-baseline still goes
# through via the explicit override, but an accidental one from a bad
# measurement cannot.
#
# T-1401: that clamp had no exception for a module whose real, freshly
# measured coverage.xml value is EXACTLY ZERO -- and fired on one anyway
# (src/frob/__main__.py: lock said 81.2%, coverage.xml recorded 0 of 133
# lines hit) from a clean, crash-free, fully-completed `make coverage` run
# (exit 0, no worker crash). A module coverage.xml genuinely recorded zero
# hits for is never "a bad/partial measurement noise floor" -- it is the
# most confident, unambiguous signal this module produces, and clamping it
# back up to a stale number is exactly the silent-divergence failure mode
# T-1363 itself was written to prevent, just aimed at the opposite case.
# That divergence misled a later investigation (T-1398, dropped). This is
# fixed narrowly: `new_pct == 0.0` is now excluded from the clamp
# unconditionally, regardless of `allow_decrease`, so a real zero always
# stamps as zero. Non-zero drops keep the pre-T-1401 clamp behavior
# unchanged (see T-1401's Done report for why the clamp itself was not
# removed more broadly: doing so would require updating this module's
# existing T-1363 regression tests in the same change, and those live in
# tests/test_gates.py, outside this ticket's touchable scope while T-1235
# holds a concurrent lease on tests/** -- filed as a follow-up).


def _apply_lock_ratchet(root: Path, rounded: dict[str, float]) -> None:
    """Clamp `rounded` in place against the prior committed lock (T-1363/T-1401).

    A module's new percentage is clamped back to the prior committed value
    whenever it drops by more than `_LOCK_TOLERANCE` points -- UNLESS the new
    value is exactly `0.0` (T-1401: a genuine zero-hit measurement is real
    signal, never partial-run noise, and must never be silently overwritten).
    Mutates `rounded` directly; logs a single loud warning naming how many
    modules were clamped, never silent.
    """
    existing_lock = load_coverage_lock(root) or {}
    existing_line: dict[str, float] = existing_lock.get("module_line", {})
    clamped = 0
    for module, existing_pct in existing_line.items():
        new_pct = rounded.get(module)
        if new_pct is None:
            continue
        if new_pct > 0.0 and existing_pct - new_pct > _LOCK_TOLERANCE:
            rounded[module] = existing_pct
            clamped += 1
    if clamped:
        _log.warning(
            "write_coverage_lock: refused a downward ratchet on %d "
            "module(s) (drop > %.1f points) -- kept the prior committed "
            "floor for each; pass allow_decrease=True for a deliberate "
            "re-baseline",
            clamped,
            _LOCK_TOLERANCE,
        )


# frob:doc docs/modules/gates.md#public-api
# frob:waive AFFECT001 reason="T-1401 added a zero-hit carve-out to the ratchet clamp \
# below; docs/modules/gates.md#public-api needs a matching update but docs/** was held \
# by T-1235's concurrent in-progress lease for this ticket's whole duration -- tracked \
# as T-1405, land the doc update there"
# frob:tests tests/test_gates.py::TestCoverageLoad.test_stamp_coverage_refreshes_committed_lock  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageLoad.test_write_coverage_lock_refuses_downward_ratchet  # noqa: E501
# frob:tests tests/test_gates.py::TestCoverageLoad.test_write_coverage_lock_allow_decrease_overrides_ratchet  # noqa: E501
def write_coverage_lock(
    root: Path, data: CoverageData, *, allow_decrease: bool = False
) -> Result[Unit, GateError]:
    """Write the committed `frob-coverage.lock.json` summary for `data` (T-0545).

    Deliberately rounds every percentage to 1 decimal and stores only
    `module_line` (never per-line hit data or the raw xml) -- small enough to
    diff sanely in a PR, and specific enough for `coverage_lock_diff` to
    catch a claim a real CI run cannot reproduce. Rounding also keeps the
    committed file's diffs quiet across re-stamps with only float-noise
    differences.

    T-1363: unless `allow_decrease=True` (an explicit, deliberate
    re-baseline -- never the default a `make coverage` run passes), a
    module already present in the committed lock can only ratchet UP: its
    new percentage is clamped to `max(existing, new)` whenever the drop
    exceeds `_LOCK_TOLERANCE` points, so a single bad/partial measurement
    cannot silently lower a committed quality floor. A module with no prior
    lock entry is written as-is (nothing to ratchet against yet).

    T-1401: a module whose new value is EXACTLY zero is NEVER clamped, even
    when `allow_decrease` is left `False` -- a real zero-hit measurement is
    never "noise", and silently reporting a stale non-zero floor for a
    module coverage.xml shows zero hits for is precisely the defect this
    ticket found and fixed. See `_apply_lock_ratchet` for the clamp itself.
    """
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(GateError.WorktreeLeaseViolation)
    rounded = {k: round(v, 1) for k, v in sorted(data.module_line.items())}
    if not allow_decrease:
        _apply_lock_ratchet(root, rounded)
    lock = {
        "source_sha": data.source_sha,
        "module_line": rounded,
    }
    lock_path = root / _LOCK_REL
    try:
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        _log.error("write_coverage_lock: could not write %s: %s", lock_path, exc)
        return Err(GateError.WriteFailed)
    _log.info(
        "write_coverage_lock: locked %d module(s), source_sha=%s",
        len(lock["module_line"]),
        data.source_sha[:8],
    )
    _append_lock_audit_entry(root, data.source_sha, len(lock["module_line"]))
    return Ok(Unit())


# frob:ticket T-1375
def _append_lock_audit_entry(root: Path, source_sha: str, module_count: int) -> None:
    """Best-effort append of one provenance line to `_LOCK_AUDIT_REL` after a
    successful `write_coverage_lock` write (T-1375).

    A durable, on-disk companion to the `_log.info` call above: log output
    is only as durable as whatever terminal/session captured it, but this
    file survives in the worktree across sessions, so `load_lock_audit_log`
    can later confirm (or fail to confirm) that a given committed lock's
    `source_sha` has a matching, logged write in THIS worktree's own
    history. A write failure here is logged but never fails the lock write
    itself -- the audit trail is a diagnostic aid, not a hard requirement
    of stamping."""
    audit_path = root / _LOCK_AUDIT_REL
    entry = {
        "written_at": datetime.now(UTC).isoformat(),
        "pid": os.getpid(),
        "source_sha": source_sha,
        "module_count": module_count,
    }
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError as exc:
        _log.warning(
            "_append_lock_audit_entry: could not append to %s: %s", audit_path, exc
        )


# frob:doc docs/modules/gates.md#public-api
def load_coverage_lock(root: Path) -> dict | None:
    """The raw `frob-coverage.lock.json` document, or `None` if missing/unreadable."""
    lock_path = root / _LOCK_REL
    if not lock_path.exists():
        return None
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("load_coverage_lock: %s unreadable: %s", lock_path, exc)
        return None


# frob:doc docs/modules/gates.md#public-api
def load_lock_audit_log(root: Path) -> tuple[dict, ...]:
    """Every entry `_append_lock_audit_entry` has recorded in this worktree
    (T-1375), oldest first; empty (never an error) if the file is missing,
    unreadable, or contains a malformed line -- a malformed/missing audit
    trail means "cannot confirm attribution", which callers should treat
    the same as "no matching entry found", not a crash.

    Use to check whether a given committed `frob-coverage.lock.json`'s
    `source_sha` has a matching entry: `any(e["source_sha"] == lock
    ["source_sha"] for e in load_lock_audit_log(root))` -- `False` means
    the current lock content has no attributable `write_coverage_lock`
    call logged in this worktree's own history.
    """
    audit_path = root / _LOCK_AUDIT_REL
    if not audit_path.exists():
        return ()
    entries: list[dict] = []
    try:
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except ValueError as exc:
                _log.warning(
                    "load_lock_audit_log: skipping malformed line in %s: %s",
                    audit_path,
                    exc,
                )
    except OSError as exc:
        _log.warning("load_lock_audit_log: %s unreadable: %s", audit_path, exc)
        return ()
    return tuple(entries)


# frob:doc docs/modules/gates.md#public-api
def coverage_lock_diff(
    lock: dict, data: CoverageData, tolerance: float = _LOCK_TOLERANCE
) -> tuple[str, ...]:
    """Modules whose live `data.module_line` % differs from `lock` by more
    than `tolerance` points, sorted for stable output (T-0545/TEST012).

    A module present in `lock` but absent from `data` (e.g. the file was
    deleted, or this run's coverage.xml simply didn't measure it) is also
    reported -- silently dropping a module from live data is exactly the
    "an author trims the measured set locally" evasion this check exists to
    catch, so absence must not fail open the same way B4's `pct is None`
    skip does for TEST005.
    """
    locked_line: dict[str, float] = lock.get("module_line", {})
    drifted: list[str] = []
    for module, locked_pct in locked_line.items():
        live_pct = data.module_line.get(module)
        if live_pct is None or abs(live_pct - locked_pct) > tolerance:
            drifted.append(module)
    return tuple(sorted(drifted))


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


__all__ = [
    "coverage_lock_diff",
    "exclude_filtered_coverage",
    "load_coverage",
    "load_coverage_lock",
    "load_lock_audit_log",
    "load_stamp",
    "stamp_coverage",
    "write_coverage_lock",
]
