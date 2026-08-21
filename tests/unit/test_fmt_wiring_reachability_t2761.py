"""T-2761: T-1606 built `resolve_line_length` (per-language line-length
resolution: rustfmt.toml's `max_width`, prettier's `printWidth`,
.clang-format's `ColumnLimit`, nearest-config-wins) and wired it into
`format_paths` as the DEFAULT when no explicit `limit` override is
passed -- but four real callers outside T-1606's scope still pre-resolved
ONE ruff-derived limit via `read_line_length(root)` and passed it as an
explicit override, which defeats per-file resolution entirely (an
explicit `limit` short-circuits it by design). This file proves, through
each REAL entrypoint (not a unit call to `resolve_line_length` itself),
that a Rust file with its own `rustfmt.toml` now gets ITS declared width
-- not ruff's -- end to end.

Fixture shape shared by every test here: `pyproject.toml` sets ruff's
line-length to a narrow 20 columns; `rustfmt.toml` sets `max_width` to a
generous 200. A single-physical-line `frob:` directive comment in a `.rs`
file is deliberately longer than 20 columns but well under 200. Before
this ticket, every one of these four callers pre-resolved the ruff-
derived 20 and wrapped the Rust file's directive against it (a spurious
rewrite); after this ticket, each resolves the file's OWN 200-column
rustfmt width and leaves it untouched.
"""

from __future__ import annotations

from pathlib import Path

from frob.app.config import AppConfig


# frob:ticket T-2761
# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs -- shared fixture
    helper matching the repo-wide `tests/test_gates.py::_write` shape."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-2761
_LONG_REASON = "x" * 40  # pushes the directive comment past 20 cols, well under 200


# frob:ticket T-2761
# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _make_fixture(tmp_path: Path) -> tuple[Path, str]:
    """Build the shared ruff-narrow/rustfmt-wide fixture tree; returns
    `(root, rel_path)` for the planted `.rs` file."""
    _write(tmp_path, "pyproject.toml", "[tool.ruff]\nline-length = 20\n")
    _write(tmp_path, "rustfmt.toml", "max_width = 200\n")
    rel = "src/lib.rs"
    original = f'// frob:waive SCOPE001 reason="{_LONG_REASON}"\n'
    _write(tmp_path, rel, original)
    return tmp_path, rel


# frob:ticket T-2761
class TestFmtRunnerReachability:
    """`frob fmt` (T-2761 caller #1: `src/frob/app/fmt_runner.py`)."""

    # frob:ticket T-2761
    # frob:tests tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmtRunnerReachability.test_check_mode_reports_no_change_for_rust_file_under_its_own_width kind="unit"  # noqa: E501
    def test_check_mode_reports_no_change_for_rust_file_under_its_own_width(
        self, tmp_path: Path
    ) -> None:
        """`frob fmt --check` over the fixture must NOT flag `lib.rs` --
        its directive fits the rustfmt-declared 200-column width, even
        though it exceeds ruff's 20. Before T-2761, `run()` pre-resolved
        ruff's 20 and passed it as an explicit `limit=`, which DID flag
        (and would have rewrapped) this file."""
        from frob.app import fmt_runner

        root, rel = _make_fixture(tmp_path)
        before = (root / rel).read_text()
        cfg = AppConfig(fmt_path=root, fmt_check=True, fmt_json=True)
        fmt_runner.run(cfg)
        after = (root / rel).read_text()
        assert after == before, "check mode must never write"

    # frob:ticket T-2761
    # frob:tests tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmtRunnerReachability.test_write_mode_leaves_rust_directive_untouched kind="unit"  # noqa: E501
    def test_write_mode_leaves_rust_directive_untouched(
        self, tmp_path: Path
    ) -> None:
        """`frob fmt` (write mode) over the fixture leaves `lib.rs`
        byte-for-byte unchanged -- its own rustfmt width has room."""
        from frob.app import fmt_runner

        root, rel = _make_fixture(tmp_path)
        before = (root / rel).read_text()
        cfg = AppConfig(fmt_path=root, fmt_check=False, fmt_json=True)
        fmt_runner.run(cfg)
        after = (root / rel).read_text()
        assert after == before


# frob:ticket T-2761
class TestLandFmtStepReachability:
    """`frob ticket land`'s absorbed fmt step (T-2761 caller #2:
    `src/frob/app/ticket_runner/_land_cmd.py::_fmt_pre_land_step`)."""

    # frob:ticket T-2761
    # frob:tests tests/unit/test_fmt_wiring_reachability_t2761.py::TestLandFmtStepReachability.test_touched_scoped_step_leaves_rust_file_untouched kind="unit"  # noqa: E501
    def test_touched_scoped_step_leaves_rust_file_untouched(
        self, tmp_path: Path
    ) -> None:
        """`_fmt_pre_land_step`, called with `lib.rs` in the touched set,
        must not rewrite it -- its own 200-column rustfmt width has
        plenty of room, even though ruff's 20 would have flagged it."""
        from frob.app.ticket_runner._land_cmd import _fmt_pre_land_step

        root, rel = _make_fixture(tmp_path)
        before = (root / rel).read_text()
        _fmt_pre_land_step(root, "T-2761", frozenset({rel}))
        after = (root / rel).read_text()
        assert after == before

    # frob:ticket T-2761
    # frob:tests tests/unit/test_fmt_wiring_reachability_t2761.py::TestLandFmtStepReachability.test_whole_tree_fallback_leaves_rust_file_untouched kind="unit"  # noqa: E501
    def test_whole_tree_fallback_leaves_rust_file_untouched(
        self, tmp_path: Path
    ) -> None:
        """The `touched_paths is None` whole-tree fallback branch also
        must not rewrite `lib.rs`."""
        from frob.app.ticket_runner._land_cmd import _fmt_pre_land_step

        root, rel = _make_fixture(tmp_path)
        before = (root / rel).read_text()
        _fmt_pre_land_step(root, "T-2761", None)
        after = (root / rel).read_text()
        assert after == before


# frob:ticket T-2761
class TestTierAFixHandlerReachability:
    """The Tier-A auto-fix handler (T-2761 caller #3:
    `src/frob/gates/_fix_engine_text.py::fix_fmt001_directive_wrap`)."""

    # frob:ticket T-2761
    # frob:tests tests/unit/test_fmt_wiring_reachability_t2761.py::TestTierAFixHandlerReachability.test_scoped_fix_reports_no_applied_fix_for_rust_file kind="unit"  # noqa: E501
    def test_scoped_fix_reports_no_applied_fix_for_rust_file(
        self, tmp_path: Path
    ) -> None:
        """`fix_fmt001_directive_wrap(only_paths={rel})` must report no
        `FixApplied` for `lib.rs` and leave it unchanged."""
        from frob.gates._fix_engine_text import fix_fmt001_directive_wrap

        root, rel = _make_fixture(tmp_path)
        before = (root / rel).read_text()
        applied = fix_fmt001_directive_wrap(root, only_paths=frozenset({rel}))
        after = (root / rel).read_text()
        assert applied == []
        assert after == before

    # frob:ticket T-2761
    # frob:tests tests/unit/test_fmt_wiring_reachability_t2761.py::TestTierAFixHandlerReachability.test_whole_tree_fix_reports_no_applied_fix_for_rust_file kind="unit"  # noqa: E501
    def test_whole_tree_fix_reports_no_applied_fix_for_rust_file(
        self, tmp_path: Path
    ) -> None:
        """`fix_fmt001_directive_wrap(only_paths=None)` (whole-tree
        branch) also leaves `lib.rs` untouched."""
        from frob.gates._fix_engine_text import fix_fmt001_directive_wrap

        root, rel = _make_fixture(tmp_path)
        before = (root / rel).read_text()
        applied = fix_fmt001_directive_wrap(root, only_paths=None)
        after = (root / rel).read_text()
        assert not any(a.file == rel for a in applied)
        assert after == before


# frob:ticket T-2761
class TestFmt001GateReachability:
    """The FMT001 diff gate (T-2761 caller #4:
    `src/frob/gates/_todo_fmt.py::fmt_gate`)."""

    # frob:ticket T-2761
    # frob:tests tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmt001GateReachability.test_rust_file_over_ruff_width_but_under_rustfmt_width_not_flagged kind="unit"  # noqa: E501
    def test_rust_file_over_ruff_width_but_under_rustfmt_width_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """A diff-touched `.rs` directive line that exceeds ruff's
        20-column limit but fits rustfmt's declared 200 must NOT fire
        FMT001 -- before T-2761, `fmt_gate` resolved one project-wide
        `read_line_length(root)` for every language, so this exact
        fixture WOULD have fired against ruff's 20."""
        from frob.gates._todo_fmt import fmt_gate
        from frob.gitio import Diff, Hunk

        root, rel = _make_fixture(tmp_path)
        diff = Diff(base="x", hunks=(Hunk(file=rel, span=(1, 1)),))
        violations = fmt_gate(root, diff)
        assert not any(v.rule == "FMT001" for v in violations)

    # frob:ticket T-2761
    # frob:tests tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmt001GateReachability.test_rust_file_over_its_own_rustfmt_width_still_flagged kind="unit"  # noqa: E501
    def test_rust_file_over_its_own_rustfmt_width_still_flagged(
        self, tmp_path: Path
    ) -> None:
        """Positive control: the SAME gate still fires when the directive
        line genuinely exceeds the file's own (narrow) rustfmt width --
        proves this is real per-file resolution, not a detector that
        stopped firing altogether."""
        from frob.gates._todo_fmt import fmt_gate
        from frob.gitio import Diff, Hunk

        root, _rel = _make_fixture(tmp_path)
        # Override with a narrow rustfmt width so the SAME directive line
        # now genuinely exceeds its own language's configured width.
        _write(root, "rustfmt.toml", "max_width = 10\n")
        rel = "src/other.rs"
        _write(
            root, rel, f'// frob:waive SCOPE001 reason="{_LONG_REASON}"\n'
        )
        diff = Diff(base="x", hunks=(Hunk(file=rel, span=(1, 1)),))
        violations = fmt_gate(root, diff)
        hit = next((v for v in violations if v.rule == "FMT001"), None)
        assert hit is not None
        assert hit.file == rel
