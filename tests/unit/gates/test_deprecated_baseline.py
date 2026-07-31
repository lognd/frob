"""Tests for `frob.gates._deprecated_baseline` (T-0639, redesigned T-1052):
the DEPR005 committed reference-set baseline -- load/save round trip and
the shrink-only/seed-only tighten idiom, on the line-insensitive
`(file, symbol)`-keyed `"file#count"` reference shape T-1052 introduced."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.gates import deprecated_current_references, deprecated_gate
from frob.gates._deprecated_baseline import (
    DeprecatedBaselineEntry,
    DeprecatedBaselineLock,
    file_reference_counts,
    load_deprecated_baseline,
    save_deprecated_baseline,
    tighten_deprecated_baseline,
)
from frob.graph import build_graph
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState


def _write(root: Path, rel: str, content: str) -> None:
    """Test helper: write `content` to `root/rel`, creating parent dirs."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _snapshot(root: Path):
    """Test helper: a fresh `GraphSnapshot` for `root`, mirroring
    `tests/test_gates.py::_snapshot`."""
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


def _open_ticket_queue(ticket_id: str = "T-0001") -> TicketQueue:
    """Test helper: a `TicketQueue` with a single open ticket bound to
    `ticket_id`, for exercising `deprecated_gate`'s DEPR005 branch."""
    return TicketQueue(
        tickets={
            ticket_id: Ticket(
                id=ticket_id,
                title="Sample",
                state=TicketState.QUEUED,
                kind=TicketKind.FEATURE,
                origin=Origin.HUMAN,
                created=date(2026, 1, 1),
                scope=(),
                evidence=(),
                body="## Description\nx\n\n## Done report\ndone\n",
            )
        }
    )


class TestDeprecatedCurrentReferencesImportGating:
    """`deprecated_current_references`'s import-gated call-shape resolution
    (T-1052): a call-shaped usage of a deprecated symbol's bare identifier
    only counts as a reference when its file also imports that exact
    name -- an unrelated same-named call in a non-importing file (e.g.
    `subprocess.run(` in a file that never imports a deprecated `run`)
    is not a caller."""

    def test_unrelated_same_name_call_in_non_importing_file_is_excluded(
        self, tmp_path: Path
    ) -> None:
        """T-1052 acceptance criterion 0: `subprocess.run(` in a new file
        that never imports the deprecated `run` is NOT reported as a
        reference -- only a file that actually imports `run` and calls it
        counts."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating.test_unrelated_same_name_call_in_non_importing_file_is_excluded  # noqa: E501
        _write(tmp_path, "src/runner.py", "def run(x):\n    return x\n")
        _write(
            tmp_path,
            "src/importer.py",
            "from runner import run\nrun(1)\n",
        )
        _write(
            tmp_path,
            "src/subprocess_caller.py",
            "import subprocess\nsubprocess.run(['ls'])\n",
        )
        refs = deprecated_current_references("run", tmp_path)
        assert any(r.startswith("src/importer.py:") for r in refs)
        assert not any(r.startswith("src/subprocess_caller.py:") for r in refs)


class TestFileReferenceCounts:
    """`file_reference_counts`: projects a `file:line` reference set down
    to per-file counts, dropping line numbers (T-1052)."""

    def test_buckets_by_file(self) -> None:
        """T-1052: two references in the same file bucket to one count of
        2; a lone reference in another file buckets to 1 -- line numbers
        never survive the projection."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestFileReferenceCounts.test_buckets_by_file  # noqa: E501
        refs = frozenset({"src/a.py:3", "src/a.py:40", "src/b.py:1"})
        counts = file_reference_counts(refs)
        assert counts == {"src/a.py": 2, "src/b.py": 1}


class TestDeprecatedBaselineEntry:
    """`DeprecatedBaselineEntry.file_counts`: decodes `"file#count"`
    entries back into a `{file: count}` mapping (T-1052)."""

    def test_file_counts_decodes_encoded_references(self) -> None:
        """T-1052: `"file#count"`-encoded references decode to their
        `(file, count)` pairs."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedBaselineEntry.test_file_counts_decodes_encoded_references  # noqa: E501
        entry = DeprecatedBaselineEntry(
            symbol="src/a.py::helper", references=("src/b.py#2", "src/c.py#1")
        )
        assert entry.file_counts() == {"src/b.py": 2, "src/c.py": 1}


class TestDeprecatedBaselineLock:
    """`DeprecatedBaselineLock.for_symbol`."""

    def test_for_symbol_missing_is_none(self) -> None:
        """T-0639: an un-baselined symbol resolves to `None`, not a crash."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedBaselineLock.test_for_symbol_missing_is_none  # noqa: E501
        lock = DeprecatedBaselineLock(
            entries=(DeprecatedBaselineEntry(symbol="a.py::foo", references=()),)
        )
        assert lock.for_symbol("b.py::bar") is None
        assert lock.for_symbol("a.py::foo") is not None


class TestLoadSave:
    """`load_deprecated_baseline`/`save_deprecated_baseline`."""

    def test_missing_file_is_empty(self, tmp_path: Path) -> None:
        """T-0639: no committed lock file yet is a valid, empty baseline."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestLoadSave.test_missing_file_is_empty  # noqa: E501
        lock = load_deprecated_baseline(tmp_path)
        assert lock.entries == ()

    def test_save_then_load_round_trips(self, tmp_path: Path) -> None:
        """T-0639: a saved lock loads back byte-identical in content, sorted
        deterministically."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestLoadSave.test_save_then_load_round_trips  # noqa: E501
        lock = DeprecatedBaselineLock(
            entries=(
                DeprecatedBaselineEntry(
                    symbol="src/a.py::helper", references=("src/b.py#1", "src/c.py#3")
                ),
            )
        )
        save_deprecated_baseline(tmp_path, lock)
        reloaded = load_deprecated_baseline(tmp_path)
        entry = reloaded.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.references == ("src/b.py#1", "src/c.py#3")

    def test_malformed_file_is_treated_as_empty(self, tmp_path: Path) -> None:
        """T-0639: unparseable JSON fails open to an empty baseline, never a
        crash -- mirrors `load_ratchet_lock`."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestLoadSave.test_malformed_file_is_treated_as_empty  # noqa: E501
        (tmp_path / "frob-deprecated-baseline.lock.json").write_text(
            "not json", encoding="utf-8"
        )
        assert load_deprecated_baseline(tmp_path).entries == ()


class TestTighten:
    """`tighten_deprecated_baseline`: seed-once, shrink-only, drop-if-gone
    -- now on the per-file-count key shape (T-1052)."""

    def test_first_seen_symbol_is_seeded_whole(self, tmp_path: Path) -> None:
        """T-0639: a symbol never baselined before is accepted whole, not
        flagged -- legacy callers at declaration time are not "new"."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_first_seen_symbol_is_seeded_whole  # noqa: E501
        current = {"src/a.py::helper": frozenset({"src/b.py:1", "src/c.py:2"})}
        tightened = tighten_deprecated_baseline(tmp_path, current)
        entry = tightened.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.file_counts() == {"src/b.py": 1, "src/c.py": 1}

    def test_line_shift_leaves_baseline_byte_identical(self, tmp_path: Path) -> None:
        """T-1052: a pure line-shift edit inside an already-referencing file
        (same file, different line, same count) tightens to an identical
        entry -- the whole point of dropping `file:line` for `(file,
        symbol)` keying."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_line_shift_leaves_baseline_byte_identical  # noqa: E501
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper", references=("src/b.py#1",)
                    ),
                )
            ),
        )
        shifted = {"src/a.py::helper": frozenset({"src/b.py:57"})}
        tightened = tighten_deprecated_baseline(tmp_path, shifted)
        entry = tightened.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.references == ("src/b.py#1",)

    def test_shrinkage_drops_stale_references(self, tmp_path: Path) -> None:
        """T-0639: a referencing file present in the baseline but no longer
        observed drops out -- the baseline auto-tightens."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_shrinkage_drops_stale_references  # noqa: E501
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper",
                        references=("src/b.py#1", "src/c.py#1"),
                    ),
                )
            ),
        )
        current = {"src/a.py::helper": frozenset({"src/b.py:1"})}
        tightened = tighten_deprecated_baseline(tmp_path, current)
        entry = tightened.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.references == ("src/b.py#1",)

    def test_shrinkage_keeps_lower_count_never_grows(self, tmp_path: Path) -> None:
        """T-1052: a file's observed count that FELL since baselining keeps
        only the lower (still-observed) count -- shrink-only applies
        per-file, not just per-file-presence."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_shrinkage_keeps_lower_count_never_grows  # noqa: E501
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper", references=("src/b.py#3",)
                    ),
                )
            ),
        )
        current = {"src/a.py::helper": frozenset({"src/b.py:1"})}
        tightened = tighten_deprecated_baseline(tmp_path, current)
        entry = tightened.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.file_counts() == {"src/b.py": 1}

    def test_never_absorbs_a_new_reference(self, tmp_path: Path) -> None:
        """T-0639: a new referencing file observed now but absent from the
        baseline is NOT silently absorbed -- tighten only ever shrinks an
        already-baselined entry, it never grows one."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_never_absorbs_a_new_reference  # noqa: E501
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper", references=("src/b.py#1",)
                    ),
                )
            ),
        )
        current = {"src/a.py::helper": frozenset({"src/b.py:1", "src/new.py:9"})}
        tightened = tighten_deprecated_baseline(tmp_path, current)
        entry = tightened.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.references == ("src/b.py#1",)
        assert "src/new.py" not in entry.file_counts()

    def test_never_absorbs_growth_inside_an_already_baselined_file(
        self, tmp_path: Path
    ) -> None:
        """T-1052: a file already baselined (count=1) that now shows MORE
        references (count=2) never silently grows -- the extra reference
        stays un-baselined until a human re-baselines deliberately."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_never_absorbs_growth_inside_an_already_baselined_file  # noqa: E501
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper", references=("src/b.py#1",)
                    ),
                )
            ),
        )
        current = {"src/a.py::helper": frozenset({"src/b.py:1", "src/b.py:99"})}
        tightened = tighten_deprecated_baseline(tmp_path, current)
        entry = tightened.for_symbol("src/a.py::helper")
        assert entry is not None
        assert entry.file_counts() == {"src/b.py": 1}

    def test_symbol_no_longer_deprecated_is_dropped(self, tmp_path: Path) -> None:
        """T-0639: a symbol baselined previously but absent from `current`
        (directive removed, or symbol deleted) drops out of the baseline
        entirely."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestTighten.test_symbol_no_longer_deprecated_is_dropped  # noqa: E501
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper", references=("src/b.py#1",)
                    ),
                )
            ),
        )
        tightened = tighten_deprecated_baseline(tmp_path, {})
        assert tightened.for_symbol("src/a.py::helper") is None


# frob:ticket T-1338
class TestDepr005ViolationsGrowth:
    """`deprecated_gate`'s DEPR005 branch (`_depr005_violations`, T-1052):
    fires on a per-file COUNT growth against the baseline, not a raw
    `file:line` diff -- exercises the `count > baseline_counts.get(file,
    0)` comparison and the grown-file line lookup directly, at gate level,
    to prove the comparison direction and per-file matching actually
    matter (a mutated `>`/`==` would silently pass a same-count or
    wrong-file case)."""

    def _deprecated_source(self) -> str:
        return (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )

    def test_same_count_as_baseline_does_not_fire(self, tmp_path: Path) -> None:
        """T-1052: a file whose CURRENT count equals its baselined count
        does not fire -- proves the comparison is a strict `>`, not `>=`
        or `==` (kills a Gt-swapped or Eq-swapped mutant that would fire,
        or fail to fire, on an unchanged count)."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth.test_same_count_as_baseline_does_not_fire  # noqa: E501
        _write(tmp_path, "src/a.py", self._deprecated_source())
        _write(tmp_path, "src/caller.py", "from a import helper\nhelper(1)\n")
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper", references=("src/caller.py#2",)
                    ),
                )
            ),
        )
        snap = _snapshot(tmp_path)
        queue = _open_ticket_queue()
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        assert not any(v.rule == "DEPR005" for v in violations)

    def test_growth_beyond_baseline_fires_at_the_right_file_and_line(
        self, tmp_path: Path
    ) -> None:
        """T-1052: a second file whose count grows beyond its baseline
        fires DEPR005 naming THAT file at its own (lowest) reference
        line, while an unrelated file at its baselined count stays silent
        -- proves the per-file `==` match used to compute the reported
        line actually discriminates between files (kills an Eq-swapped or
        And-swapped mutant that would report the wrong file/line or fire
        on the wrong file)."""
        # frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth.test_growth_beyond_baseline_fires_at_the_right_file_and_line  # noqa: E501
        _write(tmp_path, "src/a.py", self._deprecated_source())
        _write(tmp_path, "src/stable.py", "from a import helper\nhelper(1)\n")
        _write(
            tmp_path,
            "src/growing.py",
            "from a import helper\nhelper(1)\nhelper(2)\n",
        )
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper",
                        references=("src/stable.py#2", "src/growing.py#2"),
                    ),
                )
            ),
        )
        snap = _snapshot(tmp_path)
        queue = _open_ticket_queue()
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        depr005 = [v for v in violations if v.rule == "DEPR005"]
        assert len(depr005) == 1
        assert depr005[0].file.endswith("growing.py")
        assert depr005[0].line == 1

    def test_two_baselined_symbols_each_evaluated_independently(
        self, tmp_path: Path
    ) -> None:
        """T-1338: two DIFFERENT deprecated symbols, each with its own
        baseline entry, in one gate run -- proves the repo-wide
        `_DeprecatedRefIndex` built once and hoisted outside the eligible-
        edge loop (T-1338's PERF008 fix) still resolves each symbol's own
        reference set correctly and independently: one grows past its
        baseline and fires, the other stays at its baselined count and
        stays silent (kills a regression that shared state across symbols
        incorrectly, e.g. reusing one symbol's reference set for another)."""
        # frob:tests \
        # tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth.tes\
        # t_two_baselined_symbols_each_evaluated_independently
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n",
        )
        _write(
            tmp_path,
            "src/b.py",
            "def other(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n",
        )
        _write(tmp_path, "src/stable_caller.py", "from a import helper\nhelper(1)\n")
        _write(
            tmp_path,
            "src/growing_caller.py",
            "from b import other\nother(1)\nother(2)\n",
        )
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(
                        symbol="src/a.py::helper",
                        references=("src/stable_caller.py#2",),
                    ),
                    DeprecatedBaselineEntry(
                        symbol="src/b.py::other",
                        references=("src/growing_caller.py#2",),
                    ),
                )
            ),
        )
        snap = _snapshot(tmp_path)
        queue = _open_ticket_queue()
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        depr005 = [v for v in violations if v.rule == "DEPR005"]
        assert len(depr005) == 1
        assert depr005[0].file.endswith("growing_caller.py")
