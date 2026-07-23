"""Per-language collector adapters (T-0748, sibling of T-0710's
`frob.perf._hotgraph` contract): bounded parsers converting each
ecosystem's NATIVE profile format into the language-neutral
`SampledStack`/`SampledFrame` hit stream `resolve_stream` already
consumes, with zero changes needed to that contract.

Three adapters, one per ecosystem this ticket covers:

- `parse_perf_script`: Linux `perf record`/`perf script` textual output
  (native/Rust/C/C++, incl. the pyo3 `strata_core`/`frob_core` crates
  in-process) -- frame-pointer or dwarf stacks.
- `parse_v8_cpuprofile`: `node --cpu-prof` V8 `.cpuprofile` JSON (TS/JS),
  the format the T-0587 vitest runner's own `--cpu-prof` flag produces.
- `parse_jfr_print`: `jfr print --events jdk.ExecutionSample <file>` text
  output (Kotlin/JVM).

Every adapter is tested only against small COMMITTED fixture profiles
(tests/unit/perf/fixtures/) -- never live-profiling in unit tests, per
the ticket's determinism requirement.

NO-FAIL-SILENT: a profile this module cannot parse AT ALL is an `Err`
naming the source file (never a silent empty result). A single malformed
SAMPLE or FRAME inside an otherwise-good profile is logged and skipped
(the rest of the profile is still real data) -- but where a frame's true
`(file, line)` cannot be determined from the source format at all (a
perf frame with no debuginfo, a JFR frame whose class has no known file),
the frame is given `SampledFrame(file="", line=0-or-n)` rather than a
guess: `resolve_stream` can never match `file=""` to a real section, so
that sample surfaces as visible `HitStream.unattributed_weight` instead
of a silently wrong section -- the same DEGRADE-TO-CORRECT discipline
`frob.perf._hotgraph._block_sections` documents.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from typani import Err, Ok
from typani.error_set import ErrorSet
from typani.result import Result

from frob.arch._normalized import NormalizedModule
from frob.logging import get_logger
from frob.perf._hotgraph import SampledFrame, SampledStack

_log = get_logger(__name__)

__all__ = [
    "CollectorError",
    "build_class_to_file",
    "parse_jfr_print",
    "parse_perf_script",
    "parse_v8_cpuprofile",
]


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
class CollectorError(ErrorSet):
    """Failure values every T-0748 collector adapter can return; every
    variant is raised only when a whole profile is unparseable -- the
    caller's log line names the offending source file (never a bare
    "parse failed")."""

    BadPerfScript = "perf script output could not be parsed"
    BadCpuProfile = "V8 .cpuprofile JSON could not be parsed"
    BadJfrPrint = "JFR print output could not be parsed"


# ---------------------------------------------------------------------------
# (a) native/Rust/C/C++: `perf script`
# ---------------------------------------------------------------------------

_PERF_FRAME_RE = re.compile(r"^\s+[0-9a-fA-F]+\s+(?P<sym>.+?)\s+\((?P<loc>[^)]*)\)\s*$")
_PERF_LOC_FILE_LINE_RE = re.compile(r"^(?P<file>.+):(?P<line>\d+)$")
_PERF_WEIGHT_RE = re.compile(r":\s*(?P<weight>\d+(?:\.\d+)?)\s+\S+:\s*$")


def _split_perf_blocks(text: str) -> list[tuple[str, list[str]]]:
    """Split `perf script` output into `(header, frame_lines)` blocks: a
    non-indented header line followed by indented frame lines, blocks
    separated by a blank line (perf script's own record format)."""
    blocks: list[tuple[str, list[str]]] = []
    header: str | None = None
    frame_lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            if header is not None:
                blocks.append((header, frame_lines))
            header, frame_lines = None, []
            continue
        if line[0] not in (" ", "\t"):
            if header is not None:
                blocks.append((header, frame_lines))
            header, frame_lines = line, []
        else:
            frame_lines.append(line)
    if header is not None:
        blocks.append((header, frame_lines))
    return blocks


def _parse_perf_frames(frame_lines: list[str]) -> list[SampledFrame]:
    """One sample's indented frame lines into `SampledFrame`s, leaf first
    (perf script's own ordering, matching `SampledStack`'s contract). A
    frame with no `(file:line)` suffix (missing debuginfo, or a foreign
    module frame) gets `file="" line=0` -- honestly unattributed rather
    than guessed."""
    frames: list[SampledFrame] = []
    for line in frame_lines:
        match = _PERF_FRAME_RE.match(line)
        if not match:
            continue
        loc_match = _PERF_LOC_FILE_LINE_RE.match(match.group("loc"))
        if loc_match:
            frames.append(
                SampledFrame(
                    file=loc_match.group("file"), line=int(loc_match.group("line"))
                )
            )
        else:
            frames.append(SampledFrame(file="", line=0))
    return frames


def _perf_weight(header: str) -> float:
    """The sample's weight from its header's period field (e.g. `... 3
    cycles:` -> `3.0`), or `1.0` when the header carries no numeric
    period (a tolerant default, not a parse error)."""
    match = _PERF_WEIGHT_RE.search(header)
    if not match:
        return 1.0
    try:
        return float(match.group("weight"))
    except ValueError:
        return 1.0


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
# frob:tests tests/unit/perf/test_collectors.py::TestParsePerfScript
def parse_perf_script(
    text: str, source: str
) -> Result[list[SampledStack], CollectorError]:
    """Parse Linux `perf record`/`perf script` textual output (frame-
    pointer or dwarf stacks) into `SampledStack`s for native/Rust/C/C++
    workloads, incl. the pyo3 `strata_core`/`frob_core` crates in-process
    -- one profile can carry mixed python+native frames on the same
    stack; this adapter only resolves the native side (`(file:line)`
    debuginfo frames), a python frame within the same stack still gets
    `file="" line=0` here since perf has no python-source-line insight of
    its own -- see the module docstring's mixed-mode note. `source` names
    the profile file in every error/log line so a caller can locate bad
    input. `Err(BadPerfScript)` only when NOTHING in `text` looks like a
    perf script record at all; a single malformed sample within an
    otherwise-good profile is logged and skipped."""
    blocks = _split_perf_blocks(text)
    if not blocks:
        _log.error("parse_perf_script: %s has no recognizable sample blocks", source)
        return Err(CollectorError.BadPerfScript)
    stacks: list[SampledStack] = []
    for header, frame_lines in blocks:
        frames = _parse_perf_frames(frame_lines)
        if not frames:
            _log.warning(
                "parse_perf_script: %s sample %r has no parsable frames, skipping",
                source,
                header,
            )
            continue
        stacks.append(SampledStack(frames=tuple(frames), weight=_perf_weight(header)))
    if not stacks:
        _log.error(
            "parse_perf_script: %s produced zero parsable stacks out of %d block(s)",
            source,
            len(blocks),
        )
        return Err(CollectorError.BadPerfScript)
    _log.info("parse_perf_script: %s -> %d stack(s)", source, len(stacks))
    return Ok(stacks)


# ---------------------------------------------------------------------------
# (b) V8/TS/JS: `node --cpu-prof` `.cpuprofile`
# ---------------------------------------------------------------------------


def _v8_stack(
    sample_id: int,
    nodes: dict[int, dict],
    parent_of: dict[int, int],
    source: str,
) -> list[SampledFrame] | None:
    """Walk `sample_id` up the cpuprofile's node/children tree (rebuilt
    once into `parent_of`) into a leaf-first `SampledFrame` list, or
    `None` if the sample references an unknown node or a cyclic parent
    chain (both logged, never silently fabricated)."""
    frames: list[SampledFrame] = []
    current: int | None = sample_id
    seen: set[int] = set()
    while current is not None:
        if current in seen:
            _log.error(
                "parse_v8_cpuprofile: %s cycle detected at node %s", source, current
            )
            return None
        seen.add(current)
        node = nodes.get(current)
        if node is None:
            _log.warning(
                "parse_v8_cpuprofile: %s sample references unknown node %s",
                source,
                current,
            )
            return None
        call_frame = node.get("callFrame", {}) or {}
        url = call_frame.get("url") or ""
        line_number = call_frame.get("lineNumber", -1)
        # V8 line numbers are 0-based; this repo's SampledFrame is 1-based.
        is_valid = isinstance(line_number, int) and line_number >= 0
        line = (line_number + 1) if is_valid else 0
        frames.append(SampledFrame(file=url, line=line))
        current = parent_of.get(current)
    return frames


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
# frob:tests tests/unit/perf/test_collectors.py::TestParseV8CpuProfile
def parse_v8_cpuprofile(
    text: str, source: str
) -> Result[list[SampledStack], CollectorError]:
    """Parse a `node --cpu-prof` V8 `.cpuprofile` JSON document (Chrome
    DevTools CPU profile format -- `nodes`/`samples`/`timeDeltas`) into
    `SampledStack`s for TS/JS. V8 only records child pointers per node;
    this rebuilds the parent chain once so each sample's leaf id can walk
    up to a full stack. Hooks into the same vitest runner invocation the
    T-0587 collector already discovers (`--cpu-prof` writes this file
    alongside vitest's own output). `source` names the profile file in
    every error/log line."""
    try:
        doc = json.loads(text)
    except (ValueError, TypeError) as exc:
        _log.error("parse_v8_cpuprofile: %s invalid JSON: %s", source, exc)
        return Err(CollectorError.BadCpuProfile)
    if not isinstance(doc, dict) or "nodes" not in doc or "samples" not in doc:
        _log.error("parse_v8_cpuprofile: %s missing nodes/samples", source)
        return Err(CollectorError.BadCpuProfile)

    nodes: dict[int, dict] = {}
    parent_of: dict[int, int] = {}
    for node in doc["nodes"]:
        if not isinstance(node, dict) or "id" not in node:
            _log.error("parse_v8_cpuprofile: %s node missing id", source)
            return Err(CollectorError.BadCpuProfile)
        node_id = node["id"]
        nodes[node_id] = node
        for child in node.get("children", ()) or ():
            parent_of[child] = node_id

    samples = doc["samples"]
    time_deltas = doc.get("timeDeltas")
    stacks: list[SampledStack] = []
    for i, sample_id in enumerate(samples):
        frames = _v8_stack(sample_id, nodes, parent_of, source)
        if frames is None:
            continue
        weight = 1.0
        if isinstance(time_deltas, list) and i < len(time_deltas):
            try:
                weight = max(float(time_deltas[i]), 0.0) or 1.0
            except (TypeError, ValueError):
                weight = 1.0
        stacks.append(SampledStack(frames=tuple(frames), weight=weight))
    _log.info("parse_v8_cpuprofile: %s -> %d stack(s)", source, len(stacks))
    return Ok(stacks)


# ---------------------------------------------------------------------------
# (c) JVM/Kotlin: `jfr print`
# ---------------------------------------------------------------------------

_JFR_FRAME_RE = re.compile(
    r"^\s*(?P<qualname>[\w.$]+)\([^)]*\)\s+line:\s*(?P<line>\d+)\s*$"
)


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
# frob:tests tests/unit/perf/test_collectors.py::TestBuildClassToFile
def build_class_to_file(modules: list[NormalizedModule]) -> dict[str, str]:
    """Map a JVM-style dotted class name to its source file, derived from
    the same `NormalizedModule`s `build_section_index` indexes -- the
    file JFR's `jdk.ExecutionSample` event never carries directly (only
    `class.method` + line). A class name seen in more than one module is
    AMBIGUOUS (which file's class does a JFR frame naming it belong to?)
    and is dropped from the map entirely rather than guessed, so an
    ambiguous class's frames resolve honestly to unattributed instead of
    a possibly-wrong file (NO-FAIL-SILENT, matching `_hotgraph`'s
    DEGRADE-TO-CORRECT precedent for ambiguous spans)."""
    seen: dict[str, str | None] = {}
    for module in modules:
        for cls in module.classes:
            if cls.name in seen and seen[cls.name] != module.path:
                seen[cls.name] = None
            elif cls.name not in seen:
                seen[cls.name] = module.path
    return {name: path for name, path in seen.items() if path is not None}


def _split_jfr_blocks(text: str) -> list[list[str]]:
    """Split `jfr print --events jdk.ExecutionSample` text output into one
    `stackTrace = [ ... ]` line list per event block (leaf frame first,
    JFR's own ordering)."""
    blocks: list[list[str]] = []
    in_event = False
    in_stack = False
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("jdk.ExecutionSample"):
            in_event, in_stack, current = True, False, []
            continue
        if not in_event:
            continue
        if stripped.startswith("stackTrace = ["):
            in_stack = True
            continue
        if in_stack and stripped == "]":
            in_stack = False
            blocks.append(current)
            continue
        if in_stack:
            current.append(line)
        if stripped == "}":
            in_event = False
    return blocks


def _parse_jfr_frames(
    lines: list[str], class_to_file: Mapping[str, str]
) -> list[SampledFrame]:
    """One event's `stackTrace` lines into `SampledFrame`s. A frame line
    not matching JFR's `Class.method(...) line: N` shape (a native frame
    with no line info, an unrecognized entry) is skipped, not fabricated;
    a frame whose class has no `class_to_file` entry still contributes
    its line number with `file=""`, honestly unattributed."""
    frames: list[SampledFrame] = []
    for line in lines:
        match = _JFR_FRAME_RE.match(line)
        if not match:
            continue
        qualname = match.group("qualname")
        cls_name = qualname.rsplit(".", 1)[0] if "." in qualname else qualname
        file = class_to_file.get(cls_name, "")
        frames.append(SampledFrame(file=file, line=int(match.group("line"))))
    return frames


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
# frob:tests tests/unit/perf/test_collectors.py::TestParseJfrPrint
def parse_jfr_print(
    text: str, source: str, class_to_file: Mapping[str, str] | None = None
) -> Result[list[SampledStack], CollectorError]:
    """Parse `jfr print --events jdk.ExecutionSample <file>` text output
    into `SampledStack`s for Kotlin/JVM workloads. `class_to_file`
    (build via `build_class_to_file` from the same `NormalizedModule`s
    `build_section_index` was given) resolves each frame's class prefix
    to a source file; omit it (or leave a class unmapped) and those
    frames still parse with `file=""`, which `resolve_stream` can never
    match to a section -- honestly unattributed rather than guessed.
    `source` names the profile file in every error/log line."""
    class_to_file = class_to_file or {}
    blocks = _split_jfr_blocks(text)
    if not blocks:
        _log.error("parse_jfr_print: %s has no jdk.ExecutionSample blocks", source)
        return Err(CollectorError.BadJfrPrint)
    stacks: list[SampledStack] = []
    for lines in blocks:
        frames = _parse_jfr_frames(lines, class_to_file)
        if not frames:
            _log.warning(
                "parse_jfr_print: %s sample has no parsable stackTrace "
                "frames, skipping",
                source,
            )
            continue
        stacks.append(SampledStack(frames=tuple(frames), weight=1.0))
    _log.info("parse_jfr_print: %s -> %d stack(s)", source, len(stacks))
    return Ok(stacks)
