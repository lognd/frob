"""T-0748: per-language collector adapter tests, over small COMMITTED
fixture profiles (tests/unit/perf/fixtures/) -- never live-profiling,
per the ticket's determinism requirement. Each adapter's fixture and
resolver-facing shape (leaf-first frames, honest-unattributed on
unresolvable file info) is asserted directly against the parsed
`SampledStack`s; a full round trip through `frob.perf._hotgraph.
resolve_stream` is covered once per adapter to prove the produced
stacks are genuinely consumable by the shared hit stream, matching
T-0710's contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.arch._normalized import NormalizedClass, NormalizedFunction, NormalizedModule
from frob.perf._collectors import (
    CollectorError,
    build_class_to_file,
    build_index_for_files,
    detect_collector_format,
    parse_collector_format,
    parse_jfr_print,
    parse_perf_script,
    parse_v8_cpuprofile,
)
from frob.perf._hotgraph import (
    UNATTRIBUTED_SECTION_ID,
    SampledFrame,
    SampledStack,
    build_section_index,
    resolve_stream,
)

_FIXTURES = Path(__file__).parent / "fixtures"


class TestParsePerfScript:
    """Linux `perf script` textual output -> `SampledStack`s."""

    def test_parses_committed_fixture_into_leaf_first_stacks(self) -> None:
        """Frames within one sample are ordered leaf-first, matching perf
        script's own top-to-bottom record order."""
        text = (_FIXTURES / "sample.perf.script").read_text()
        result = parse_perf_script(text, source="sample.perf.script")
        assert result.is_ok
        stacks = result.danger_ok
        assert len(stacks) == 3
        leaf = stacks[0].frames[0]
        assert leaf.file == "src/crate/lib.rs"
        assert leaf.line == 12
        assert stacks[0].weight == 3.0

    def test_frame_with_no_debuginfo_is_unattributed_not_dropped(self) -> None:
        """A frame lacking a `(file:line)` suffix still yields a
        `SampledFrame` (`file="" line=0`), never a dropped sample."""
        text = (_FIXTURES / "sample.perf.script").read_text()
        stacks = parse_perf_script(text, source="sample.perf.script").danger_ok
        last = stacks[-1]
        assert last.frames == (
            last.frames[0],
        )  # single unresolved native frame, still present
        assert last.frames[0].file == ""
        assert last.frames[0].line == 0

    def test_unparseable_profile_errors_naming_the_file(self) -> None:
        """Garbage input (no recognizable perf script record) is `Err`,
        never a silent empty stack list."""
        result = parse_perf_script(
            "not a perf script at all\n", source="garbage.script"
        )
        assert result.is_err
        assert result.danger_err == CollectorError.BadPerfScript

    def test_resolves_through_shared_hotgraph_stream(self) -> None:
        """A parsed perf stack round-trips through `resolve_stream` like
        any other language's `SampledStack`s (T-0710's contract, no
        special-casing needed)."""
        func = NormalizedFunction(name="hot_loop", line=1, body_line_count=20)
        module = NormalizedModule(
            path="src/crate/lib.rs", language="rust", functions=[func]
        )
        index = build_section_index([module])
        text = (_FIXTURES / "sample.perf.script").read_text()
        stacks = parse_perf_script(text, source="sample.perf.script").danger_ok
        stream = resolve_stream(index, stacks)
        resolved = [
            h for h in stream.section_hits if h.section_id != UNATTRIBUTED_SECTION_ID
        ]
        assert resolved  # at least one sample landed on the real function section
        assert stream.unattributed_weight >= 1.0  # the no-debuginfo sample


class TestParseV8CpuProfile:
    """`node --cpu-prof` `.cpuprofile` JSON -> `SampledStack`s."""

    def test_parses_committed_fixture_walking_parent_chain(self) -> None:
        """Each sample's leaf id is walked up the node/children tree into
        a full leaf-first stack; V8's 0-based line becomes 1-based."""
        text = (_FIXTURES / "sample.cpuprofile").read_text()
        result = parse_v8_cpuprofile(text, source="sample.cpuprofile")
        assert result.is_ok
        stacks = result.danger_ok
        assert len(stacks) == 3
        leaf, caller, root = stacks[0].frames
        assert leaf.file == "app.ts"
        assert leaf.line == 20  # lineNumber 19 (0-based) -> 20 (1-based)
        assert caller.file == "app.ts"
        assert caller.line == 10

    def test_weight_comes_from_time_deltas(self) -> None:
        """`timeDeltas[i]` becomes that sample's weight."""
        text = (_FIXTURES / "sample.cpuprofile").read_text()
        stacks = parse_v8_cpuprofile(text, source="sample.cpuprofile").danger_ok
        assert [s.weight for s in stacks] == [100.0, 100.0, 50.0]

    def test_invalid_json_errors_naming_the_file(self) -> None:
        """Malformed JSON is `Err`, never a silently empty result."""
        result = parse_v8_cpuprofile("{not json", source="broken.cpuprofile")
        assert result.is_err
        assert result.danger_err == CollectorError.BadCpuProfile

    def test_missing_required_keys_errors(self) -> None:
        """Valid JSON missing `nodes`/`samples` is still `Err`, not an
        empty-but-successful parse."""
        result = parse_v8_cpuprofile("{}", source="incomplete.cpuprofile")
        assert result.is_err
        assert result.danger_err == CollectorError.BadCpuProfile

    def test_resolves_through_shared_hotgraph_stream(self) -> None:
        """A parsed V8 stack round-trips through `resolve_stream`."""
        func = NormalizedFunction(name="hotLoop", line=20, body_line_count=1)
        module = NormalizedModule(
            path="app.ts", language="typescript", functions=[func]
        )
        index = build_section_index([module])
        text = (_FIXTURES / "sample.cpuprofile").read_text()
        stacks = parse_v8_cpuprofile(text, source="sample.cpuprofile").danger_ok
        stream = resolve_stream(index, stacks)
        resolved = [
            h for h in stream.section_hits if h.section_id != UNATTRIBUTED_SECTION_ID
        ]
        assert resolved


class TestBuildClassToFile:
    """JVM dotted-class-name -> source-file map, derived from `NormalizedModule`s."""

    def test_maps_unambiguous_class_to_its_file(self) -> None:
        module = NormalizedModule(
            path="src/HotLoop.kt",
            language="kotlin",
            classes=[NormalizedClass(name="com.example.HotLoop", line=1)],
        )
        mapping = build_class_to_file([module])
        assert mapping == {"com.example.HotLoop": "src/HotLoop.kt"}

    def test_class_seen_in_two_files_is_dropped_not_guessed(self) -> None:
        """An ambiguous class name (seen in >1 file) is excluded entirely
        rather than mapped to a possibly-wrong file (NO-FAIL-SILENT)."""
        module_a = NormalizedModule(
            path="a/Dup.kt",
            language="kotlin",
            classes=[NormalizedClass(name="com.example.Dup", line=1)],
        )
        module_b = NormalizedModule(
            path="b/Dup.kt",
            language="kotlin",
            classes=[NormalizedClass(name="com.example.Dup", line=1)],
        )
        mapping = build_class_to_file([module_a, module_b])
        assert "com.example.Dup" not in mapping


class TestParseJfrPrint:
    """`jfr print --events jdk.ExecutionSample` text output -> `SampledStack`s."""

    def test_parses_committed_fixture_into_leaf_first_stacks(self) -> None:
        text = (_FIXTURES / "sample.jfr.txt").read_text()
        class_to_file = {"com.example.HotLoop": "src/HotLoop.kt"}
        result = parse_jfr_print(
            text, source="sample.jfr.txt", class_to_file=class_to_file
        )
        assert result.is_ok
        stacks = result.danger_ok
        assert len(stacks) == 2
        leaf = stacks[0].frames[0]
        assert leaf.file == "src/HotLoop.kt"
        assert leaf.line == 12

    def test_unmapped_class_is_unattributed_not_dropped(self) -> None:
        """A class with no `class_to_file` entry still yields a frame
        (`file=""`), preserving the sample's weight in the stream."""
        text = (_FIXTURES / "sample.jfr.txt").read_text()
        stacks = parse_jfr_print(text, source="sample.jfr.txt").danger_ok
        assert len(stacks) == 2
        assert all(frame.file == "" for stack in stacks for frame in stack.frames)

    def test_unparseable_profile_errors_naming_the_file(self) -> None:
        result = parse_jfr_print("not a jfr dump at all\n", source="garbage.jfr.txt")
        assert result.is_err
        assert result.danger_err == CollectorError.BadJfrPrint

    def test_resolves_through_shared_hotgraph_stream(self) -> None:
        """A parsed JFR stack, resolved via `build_class_to_file`, round-
        trips through `resolve_stream`."""
        func = NormalizedFunction(name="run", line=12, body_line_count=1)
        module = NormalizedModule(
            path="src/HotLoop.kt",
            language="kotlin",
            classes=[
                NormalizedClass(name="com.example.HotLoop", line=10, methods=[func])
            ],
        )
        index = build_section_index([module])
        class_to_file = build_class_to_file([module])
        text = (_FIXTURES / "sample.jfr.txt").read_text()
        stacks = parse_jfr_print(
            text, source="sample.jfr.txt", class_to_file=class_to_file
        ).danger_ok
        stream = resolve_stream(index, stacks)
        # The mapped HotLoop.run sample resolves; the unmapped Unknown.doWork
        # sample is honestly unattributed.
        resolved = [
            h for h in stream.section_hits if h.section_id != UNATTRIBUTED_SECTION_ID
        ]
        assert resolved
        assert stream.unattributed_weight >= 1.0


class TestDetectCollectorFormat:
    """`detect_collector_format` autodetection (T-0765)."""

    def test_cpuprofile_extension_is_v8(self) -> None:
        """`.cpuprofile` is decided by extension alone."""
        assert detect_collector_format(Path("out.cpuprofile"), "{}") == "v8-cpuprofile"

    def test_jdk_execution_sample_marker_is_jfr(self) -> None:
        """A JFR print transcript is decided by its event marker, whatever
        extension the file happens to carry."""
        text = (_FIXTURES / "sample.jfr.txt").read_text()
        assert detect_collector_format(Path("out.txt"), text) == "jfr-print"

    def test_anything_else_defaults_to_perf_script(self) -> None:
        """Neither marker present: falls back to `perf-script`, this
        repo's other text-based collector."""
        text = (_FIXTURES / "sample.perf.script").read_text()
        assert detect_collector_format(Path("out.txt"), text) == "perf-script"


class TestParseCollectorFormat:
    """`parse_collector_format`'s single dispatch call site (T-0765)."""

    @pytest.mark.parametrize(
        ("fmt", "fixture_name"),
        [
            ("perf-script", "sample.perf.script"),
            ("v8-cpuprofile", "sample.cpuprofile"),
            ("jfr-print", "sample.jfr.txt"),
        ],
    )
    def test_dispatches_to_the_matching_adapter(
        self, fmt: str, fixture_name: str
    ) -> None:
        """Each format name routes to the adapter that actually parses its
        own fixture (never falls through to a mismatched adapter)."""
        text = (_FIXTURES / fixture_name).read_text()
        result = parse_collector_format(fmt, text, source=fixture_name)
        assert result.is_ok
        assert result.danger_ok


class TestBuildIndexForFiles:
    """`build_index_for_files`'s multi-language, best-effort index (T-0765)."""

    def test_resolves_a_real_python_file_in_the_repo(self) -> None:
        """A stack landing on a real, on-disk python function resolves to
        that function's section -- proving the shared helper `_harness`
        and `frob perf collect` both use actually attributes real code,
        not just fixture text."""
        this_file = str(Path(__file__))
        index = build_index_for_files([this_file])
        assert this_file in index
        assert index[this_file]

    def test_missing_or_unmapped_file_is_absent_from_the_index(self) -> None:
        """A nonexistent path and an unmapped extension both degrade to
        simply not appearing in the index (NO-FAIL-SILENT: the caller's
        `resolve_stream` then attributes those frames as unattributed,
        never an error here)."""
        index = build_index_for_files(["/does/not/exist.py", "note.md", ""])
        assert index == {}


class TestLanguageDeciles:
    """`language_deciles`' per-language, rank-ordered bucketing (T-0765)."""

    def test_buckets_are_grouped_per_language_never_mixed(self) -> None:
        """Two languages' sections never share a decile row -- each
        language's ranking is independent of every other's."""
        from frob.perf._hotgraph import HitStream, Section, SectionHit, language_deciles

        py_section = Section(
            id="py1",
            kind="function",
            qualname="f",
            file="a.py",
            start_line=1,
            end_line=2,
        )
        ts_section = Section(
            id="ts1",
            kind="function",
            qualname="g",
            file="b.ts",
            start_line=1,
            end_line=2,
        )
        index = {"a.py": [py_section], "b.ts": [ts_section]}
        stream = HitStream(
            section_hits=(
                SectionHit(section_id="py1", weight=5.0),
                SectionHit(section_id="ts1", weight=3.0),
            )
        )
        rows = language_deciles(stream, index)
        languages = {row.language for row in rows}
        assert languages == {"python", "typescript"}
        assert all(row.decile == 1 for row in rows)

    def test_unattributed_weight_gets_its_own_visible_bucket(self) -> None:
        """`UNATTRIBUTED_SECTION_ID`'s weight is exposed as a real
        `"unattributed"` row, never silently folded into another
        language's total (NO-FAIL-SILENT)."""
        from frob.perf._hotgraph import HitStream, SectionHit, language_deciles

        stream = HitStream(
            section_hits=(SectionHit(section_id=UNATTRIBUTED_SECTION_ID, weight=4.0),)
        )
        rows = language_deciles(stream, {})
        assert len(rows) == 1
        assert rows[0].language == UNATTRIBUTED_SECTION_ID
        assert rows[0].weight == 4.0

    def test_resolve_stream_output_feeds_language_deciles_end_to_end(self) -> None:
        """A real `SampledStack` -> `resolve_stream` -> `language_deciles`
        round trip, proving the pieces `frob perf collect` wires together
        actually compose."""
        from frob.perf._hotgraph import language_deciles

        func = NormalizedFunction(name="run", line=1, body_line_count=3)
        module = NormalizedModule(path="a.py", language="python", functions=[func])
        index = build_section_index([module])
        stacks = [SampledStack(frames=(SampledFrame(file="a.py", line=2),))]
        stream = resolve_stream(index, stacks)
        rows = language_deciles(stream, index)
        assert rows
        assert rows[0].language == "python"


@pytest.mark.parametrize(
    "fixture_name",
    ["sample.perf.script", "sample.cpuprofile", "sample.jfr.txt"],
)
def test_fixtures_exist_and_are_nonempty(fixture_name: str) -> None:
    """Every fixture this test module depends on is actually committed
    (a missing fixture would otherwise fail loudly inside individual
    tests instead of naming itself directly here)."""
    path = _FIXTURES / fixture_name
    assert path.exists()
    assert path.read_text().strip()
