"""Unit tests for `frob.render` -- color resolution, semantic palette,
element vocabulary, and the `Renderer` facade (T-0448)."""

from __future__ import annotations

import io

import pytest

from frob.render import Renderer, RenderError, resolve_color
from frob.render._elements import (
    count_deltas,
    count_summary,
    heading,
    kv_row,
    path_label,
    status_pill,
    subhead,
    table,
    ticket_id_label,
    tree,
)
from frob.render._palette import accent, critical, muted
from frob.render._renderer import Progress


class _FakeStream(io.StringIO):
    """A StringIO whose `isatty()` is controllable, unlike the real one."""

    def __init__(self, tty: bool) -> None:
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        """Report the controlled TTY-ness this fixture was built with."""
        return self._tty


class TestResolveColor:
    # frob:tests src/frob/render/_color.py::resolve_color
    def test_tty_stream_colors_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A TTY stream with no overrides colors."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FROB_NO_COLOR", raising=False)
        monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
        monkeypatch.delenv("TERM", raising=False)
        assert resolve_color(_FakeStream(tty=True)) is True

    # frob:tests src/frob/render/_color.py::resolve_color
    def test_non_tty_stream_never_colors_by_default(self) -> None:
        """A piped (non-TTY) stream never colors absent an override."""
        assert resolve_color(_FakeStream(tty=False)) is False

    # frob:tests src/frob/render/_color.py::resolve_color
    def test_no_color_flag_wins_over_everything(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`--no-color` beats even `--color=always` and `CLICOLOR_FORCE`."""
        monkeypatch.setenv("CLICOLOR_FORCE", "1")
        assert (
            resolve_color(
                _FakeStream(tty=True), color_flag="always", no_color_flag=True
            )
            is False
        )

    # frob:tests src/frob/render/_color.py::resolve_color
    def test_color_always_forces_color_when_piped(self) -> None:
        """`--color=always` colors even a non-TTY stream."""
        assert resolve_color(_FakeStream(tty=False), color_flag="always") is True

    # frob:tests src/frob/render/_color.py::resolve_color
    def test_color_never_disables_color_on_a_tty(self) -> None:
        """`--color=never` disables color even on a real TTY."""
        assert resolve_color(_FakeStream(tty=True), color_flag="never") is False

    # frob:tests src/frob/render/_color.py::resolve_color
    def test_no_color_env_disables_color_on_a_tty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`NO_COLOR` (any value) disables color on a TTY."""
        monkeypatch.setenv("NO_COLOR", "1")
        assert resolve_color(_FakeStream(tty=True)) is False

    # frob:tests src/frob/render/_color.py::resolve_color
    def test_frob_no_color_env_disables_color_on_a_tty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`FROB_NO_COLOR` (any value) disables color on a TTY."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FROB_NO_COLOR", "1")
        assert resolve_color(_FakeStream(tty=True)) is False

    # frob:tests src/frob/render/_color.py::resolve_color
    def test_clicolor_force_colors_a_non_tty_stream(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`CLICOLOR_FORCE=1` colors even a piped stream."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FROB_NO_COLOR", raising=False)
        monkeypatch.setenv("CLICOLOR_FORCE", "1")
        assert resolve_color(_FakeStream(tty=False)) is True

    # frob:tests src/frob/render/_color.py::resolve_color
    def test_clicolor_force_zero_does_not_force(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`CLICOLOR_FORCE=0` is treated as unset, per the de facto
        convention (only a non-empty, non-"0" value forces)."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FROB_NO_COLOR", raising=False)
        monkeypatch.setenv("CLICOLOR_FORCE", "0")
        assert resolve_color(_FakeStream(tty=False)) is False

    # frob:tests src/frob/render/_color.py::resolve_color
    def test_term_dumb_disables_color_on_a_tty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`TERM=dumb` disables color even when the stream is a TTY."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FROB_NO_COLOR", raising=False)
        monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
        monkeypatch.setenv("TERM", "dumb")
        assert resolve_color(_FakeStream(tty=True)) is False


class TestElements:
    # frob:tests src/frob/render/_elements.py::heading
    def test_heading_plain_has_no_ansi(self) -> None:
        """Plain-mode heading is bare text, byte-for-byte."""
        assert heading("frob doctor", color=False) == "frob doctor"

    # frob:tests src/frob/render/_elements.py::heading
    def test_heading_color_wraps_in_ansi(self) -> None:
        """Color-mode heading contains an ANSI escape and the same text."""
        out = heading("frob doctor", color=True)
        assert "\x1b[" in out
        assert "frob doctor" in out

    # frob:tests src/frob/render/_elements.py::subhead
    def test_subhead_shape_identical_across_modes(self) -> None:
        """The `-- ` marker shape is identical in both modes; only the
        ANSI bytes differ."""
        plain = subhead("extensions", color=False)
        colored = subhead("extensions", color=True)
        assert plain == "-- extensions"
        assert "-- extensions" in colored
        assert "\x1b[" in colored

    # frob:tests src/frob/render/_elements.py::kv_row
    def test_kv_row_plain_shape(self) -> None:
        """`kv_row` plain shape is `key: value`."""
        assert kv_row("frob version", "0.33.0", color=False) == "frob version: 0.33.0"

    # frob:tests src/frob/render/_elements.py::status_pill
    def test_status_pill_ok(self) -> None:
        """A known status renders `[OK]` in plain mode."""
        result = status_pill("ok", color=False)
        assert result.is_ok
        assert result.danger_ok == "[OK]"

    # frob:tests src/frob/render/_elements.py::status_pill
    def test_status_pill_unknown_is_err(self) -> None:
        """An unrecognized status value is `Err(InvalidStatus)`, not a
        silently-uncolored guess."""
        result = status_pill("bogus", color=False)
        assert result.is_err
        assert result.danger_err is RenderError.InvalidStatus

    # frob:tests src/frob/render/_elements.py::count_summary
    def test_count_summary_plain_shape(self) -> None:
        """`count_summary` renders `key=n, key=n` in insertion order."""
        out = count_summary({"ok": 3, "warn": 1}, color=False)
        assert out == "ok=3, warn=1"

    # frob:tests src/frob/render/_elements.py::path_label
    def test_path_label_plain_is_str_of_path(self) -> None:
        """`path_label` plain mode is exactly `str(path)`."""
        assert path_label("src/frob/render", color=False) == "src/frob/render"

    # frob:tests src/frob/render/_elements.py::ticket_id_label
    def test_ticket_id_label_valid(self) -> None:
        """A well-formed `T-####` id renders as itself in plain mode."""
        result = ticket_id_label("T-0448", color=False)
        assert result.is_ok
        assert result.danger_ok == "T-0448"

    # frob:tests src/frob/render/_elements.py::ticket_id_label
    def test_ticket_id_label_invalid_is_err(self) -> None:
        """A malformed ticket id is `Err(InvalidTicketId)`."""
        result = ticket_id_label("not-a-ticket", color=False)
        assert result.is_err
        assert result.danger_err is RenderError.InvalidTicketId


class TestPalette:
    # frob:tests src/frob/render/_palette.py::critical
    def test_critical_plain_has_no_ansi(self) -> None:
        """Plain-mode `critical` is bare text."""
        assert critical("boom", False) == "boom"

    # frob:tests src/frob/render/_palette.py::critical
    def test_critical_color_wraps_in_ansi(self) -> None:
        """Color-mode `critical` carries both bold and red SGR codes, per
        the colorblind-safety design (weight, not just hue)."""
        out = critical("boom", True)
        assert "\x1b[1;31m" in out

    # frob:tests src/frob/render/_palette.py::muted
    def test_muted_plain_has_no_ansi(self) -> None:
        """Plain-mode `muted` is bare text."""
        assert muted("src/frob/render", False) == "src/frob/render"

    # frob:tests src/frob/render/_palette.py::muted
    def test_muted_color_wraps_in_ansi(self) -> None:
        """Color-mode `muted` carries an ANSI escape."""
        assert "\x1b[" in muted("src/frob/render", True)

    # frob:tests src/frob/render/_palette.py::accent
    def test_accent_plain_has_no_ansi(self) -> None:
        """Plain-mode `accent` is bare text."""
        assert accent("frob doctor", False) == "frob doctor"

    # frob:tests src/frob/render/_palette.py::accent
    def test_accent_color_wraps_in_ansi(self) -> None:
        """Color-mode `accent` carries an ANSI escape."""
        assert "\x1b[" in accent("frob doctor", True)


class TestRenderer:
    # frob:tests src/frob/render/_renderer.py::Renderer
    # frob:tests src/frob/render/_renderer.py::RenderWriter.kv
    def test_write_methods_emit_one_line_each(self) -> None:
        """Every `Renderer.write.*` call appends exactly one line to the
        stream."""
        stream = _FakeStream(tty=False)
        r = Renderer(stream, color=False)
        r.write.heading("frob doctor")
        r.blank()
        r.write.kv("frob version", "0.33.0")
        r.write.good("all native extensions available")
        lines = stream.getvalue().splitlines()
        assert lines == [
            "frob doctor",
            "",
            "frob version: 0.33.0",
            "all native extensions available",
        ]

    # frob:tests src/frob/render/_renderer.py::Renderer
    def test_for_stream_resolves_color_once(self) -> None:
        """`Renderer.for_stream` resolves color via `resolve_color` and
        stores it, rather than re-deriving it per write call."""
        r = Renderer.for_stream(_FakeStream(tty=True))
        assert r.color is True
        r2 = Renderer.for_stream(_FakeStream(tty=True), no_color_flag=True)
        assert r2.color is False

    # frob:tests src/frob/render/_renderer.py::RenderWriter.status
    def test_write_status_propagates_invalid_status(self) -> None:
        """`write.status` surfaces `Err(InvalidStatus)` for a bad status
        rather than printing a malformed pill."""
        r = Renderer(_FakeStream(tty=False), color=False)
        result = r.write.status("bogus", "message")
        assert result.is_err

    # frob:tests src/frob/render/_renderer.py::RenderWriter.status
    def test_write_status_emits_pill_and_text(self) -> None:
        """A valid status emits `[STATUS] text` and returns `Ok(None)`."""
        stream = _FakeStream(tty=False)
        r = Renderer(stream, color=False)
        result = r.write.status("ok", "all clear")
        assert result.is_ok
        assert stream.getvalue().splitlines() == ["[OK] all clear"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.subhead
    def test_write_subhead(self) -> None:
        """`write.subhead` emits the `-- ` marker shape."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.subhead("extensions")
        assert stream.getvalue().splitlines() == ["-- extensions"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.count_summary
    def test_write_count_summary(self) -> None:
        """`write.count_summary` emits the `key=n, key=n` rollup shape."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.count_summary({"ok": 2, "warn": 1})
        assert stream.getvalue().splitlines() == ["ok=2, warn=1"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.path
    def test_write_path(self) -> None:
        """`write.path` emits `str(path)` verbatim in plain mode."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.path("src/frob/render")
        assert stream.getvalue().splitlines() == ["src/frob/render"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.ticket_id
    def test_write_ticket_id_valid(self) -> None:
        """A well-formed ticket id is emitted and returns `Ok(None)`."""
        stream = _FakeStream(tty=False)
        result = Renderer(stream, color=False).write.ticket_id("T-0448")
        assert result.is_ok
        assert stream.getvalue().splitlines() == ["T-0448"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.ticket_id
    def test_write_ticket_id_invalid(self) -> None:
        """A malformed ticket id propagates `Err(InvalidTicketId)` and
        emits nothing."""
        stream = _FakeStream(tty=False)
        result = Renderer(stream, color=False).write.ticket_id("nope")
        assert result.is_err
        assert stream.getvalue() == ""

    # frob:tests src/frob/render/_renderer.py::RenderWriter.good
    def test_write_good(self) -> None:
        """`write.good` emits the plain text (semantic color only, no
        markup in plain mode)."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.good("healthy")
        assert stream.getvalue().splitlines() == ["healthy"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.warn
    def test_write_warn(self) -> None:
        """`write.warn` emits the plain text."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.warn("degraded")
        assert stream.getvalue().splitlines() == ["degraded"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.critical
    def test_write_critical(self) -> None:
        """`write.critical` emits the plain text."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.critical("failed")
        assert stream.getvalue().splitlines() == ["failed"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.muted
    def test_write_muted(self) -> None:
        """`write.muted` emits the plain text."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.muted("src/frob/render")
        assert stream.getvalue().splitlines() == ["src/frob/render"]


class TestRenderIntegration:
    """One `kind="integration"` test exercising the render layer end to
    end (color resolution -> element vocabulary -> Renderer -> stream),
    rather than each piece in isolation -- clears TEST003 for the
    `src/frob/render` interface."""

    # frob:tests src/frob/render kind="integration"
    def test_renderer_end_to_end_report(self) -> None:
        """A small multi-element report renders correctly in both plain and
        color modes, and the color-mode output strips down to the exact
        same shape as plain mode."""
        import re

        plain_stream = _FakeStream(tty=False)
        plain = Renderer.for_stream(plain_stream)
        plain.write.heading("frob doctor")
        plain.blank()
        plain.write.kv("frob version", "0.33.0")
        status_result = plain.write.status("ok", "all native extensions available")
        assert status_result.is_ok

        colored_stream = _FakeStream(tty=True)
        colored = Renderer.for_stream(colored_stream, color_flag="always")
        colored.write.heading("frob doctor")
        colored.blank()
        colored.write.kv("frob version", "0.33.0")
        colored.write.status("ok", "all native extensions available")

        plain_text = plain_stream.getvalue()
        colored_text = colored_stream.getvalue()
        assert plain.color is False
        assert colored.color is True
        assert "\x1b[" not in plain_text
        assert "\x1b[" in colored_text
        stripped = re.sub(r"\x1b\[[0-9;]*m", "", colored_text)
        assert stripped == plain_text


class TestTableTreeCountDeltas:
    """Element-level tests for the T-0460 vocabulary follow-on: `table`,
    `tree`, `count_deltas`."""

    # frob:tests src/frob/render/_elements.py::table
    def test_table_plain_shape(self) -> None:
        """Plain-mode table: header, `-`-rule, then rows, columns padded to
        the widest cell in each column."""
        lines = table(
            ["ticket", "state"],
            [["T-0448", "done"], ["T-0460", "in-progress"]],
            color=False,
        )
        assert lines == [
            "ticket  state      ",
            "------  -----------",
            "T-0448  done       ",
            "T-0460  in-progress",
        ]

    # frob:tests src/frob/render/_elements.py::table
    def test_table_color_paints_header_and_rule_only(self) -> None:
        """Color mode paints the header and rule; data rows are identical
        to plain mode once ANSI is stripped."""
        import re

        plain = table(["a", "b"], [["1", "2"]], color=False)
        colored = table(["a", "b"], [["1", "2"]], color=True)
        assert "\x1b[" in colored[0]
        assert "\x1b[" in colored[1]
        assert "\x1b[" not in colored[2]
        stripped = [re.sub(r"\x1b\[[0-9;]*m", "", line) for line in colored]
        assert stripped == plain

    # frob:tests src/frob/render/_elements.py::tree
    def test_tree_plain_shape(self) -> None:
        """Plain-mode tree: two-space indent per depth level plus a
        `- ` marker."""
        lines = tree([(0, "src/frob"), (1, "render"), (2, "_elements.py")], color=False)
        assert lines == [
            "- src/frob",
            "  - render",
            "    - _elements.py",
        ]

    # frob:tests src/frob/render/_elements.py::tree
    def test_tree_color_paints_only_depth_zero(self) -> None:
        """Color mode paints only the depth-0 root label; deeper labels
        strip down to the identical plain shape."""
        import re

        plain = tree([(0, "root"), (1, "child")], color=False)
        colored = tree([(0, "root"), (1, "child")], color=True)
        assert "\x1b[" in colored[0]
        assert "\x1b[" not in colored[1]
        stripped = [re.sub(r"\x1b\[[0-9;]*m", "", line) for line in colored]
        assert stripped == plain

    # frob:tests src/frob/render/_elements.py::count_deltas
    def test_count_deltas_plain_shape(self) -> None:
        """Plain-mode `count_deltas` shows `key: old -> new (+n/-n)` per
        key, joined by `, `."""
        out = count_deltas({"errors": (5, 2), "warnings": (1, 1)}, color=False)
        assert out == "errors: 5 -> 2 (-3), warnings: 1 -> 1 (0)"

    # frob:tests src/frob/render/_elements.py::count_deltas
    def test_count_deltas_positive_delta_shape(self) -> None:
        """A regression (count went up) renders a `+n` delta."""
        out = count_deltas({"errors": (2, 5)}, color=False)
        assert out == "errors: 2 -> 5 (+3)"

    # frob:tests src/frob/render/_elements.py::count_deltas
    def test_count_deltas_color_has_no_ansi_in_plain(self) -> None:
        """Color mode wraps the segment in ANSI without changing the plain
        shape once stripped."""
        import re

        plain = count_deltas({"errors": (5, 2)}, color=False)
        colored = count_deltas({"errors": (5, 2)}, color=True)
        assert "\x1b[" in colored
        assert re.sub(r"\x1b\[[0-9;]*m", "", colored) == plain


class TestWriterTableTreeCountDeltas:
    # frob:tests src/frob/render/_renderer.py::RenderWriter.table
    def test_write_table(self) -> None:
        """`write.table` emits one line per table row via `_emit`."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.table(["a"], [["1"], ["22"]])
        assert stream.getvalue().splitlines() == ["a ", "--", "1 ", "22"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.tree
    def test_write_tree(self) -> None:
        """`write.tree` emits one line per `(depth, label)` entry."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.tree([(0, "root"), (1, "leaf")])
        assert stream.getvalue().splitlines() == ["- root", "  - leaf"]

    # frob:tests src/frob/render/_renderer.py::RenderWriter.count_deltas
    def test_write_count_deltas(self) -> None:
        """`write.count_deltas` emits the rollup as a single line."""
        stream = _FakeStream(tty=False)
        Renderer(stream, color=False).write.count_deltas({"errors": (3, 1)})
        assert stream.getvalue().splitlines() == ["errors: 3 -> 1 (-2)"]


class TestProgress:
    """`Progress` is TTY-only per the T-0419 contract: ephemeral in-place
    updates on a real TTY, a total no-op everywhere else."""

    # frob:tests src/frob/render/_renderer.py::RenderWriter.progress
    # frob:tests src/frob/render/_renderer.py::Progress.update
    def test_progress_updates_in_place_on_tty(self) -> None:
        """On a TTY stream, `update` writes a carriage-return-prefixed
        line containing the label and percent."""
        stream = _FakeStream(tty=True)
        r = Renderer(stream, color=False)
        p = r.write.progress("gates")
        p.update("gates", 1, 4)
        out = stream.getvalue()
        assert out.startswith("\r")
        assert "gates" in out
        assert "25%" in out

    # frob:tests src/frob/render/_renderer.py::Progress.update
    def test_progress_is_noop_on_non_tty(self) -> None:
        """On a non-TTY stream, `update` writes nothing at all -- no
        carriage return, no bar, no residue in a captured pipe."""
        stream = _FakeStream(tty=False)
        r = Renderer(stream, color=False)
        p = r.write.progress("gates")
        p.update("gates", 1, 4)
        assert stream.getvalue() == ""

    # frob:tests src/frob/render/_renderer.py::Progress.clear
    def test_progress_clear_erases_the_line_on_tty(self) -> None:
        """`clear` overwrites the drawn line with spaces and returns the
        cursor to column zero, leaving no residue."""
        stream = _FakeStream(tty=True)
        r = Renderer(stream, color=False)
        p = r.write.progress("gates")
        p.update("gates", 1, 4)
        drawn_len = len(stream.getvalue().split("\r")[-1])
        p.clear()
        segments = stream.getvalue().split("\r")
        assert segments[-2] == " " * drawn_len
        assert segments[-1] == ""

    # frob:tests src/frob/render/_renderer.py::Progress.clear
    def test_progress_clear_is_noop_on_non_tty(self) -> None:
        """`clear` on a non-TTY stream writes nothing."""
        stream = _FakeStream(tty=False)
        r = Renderer(stream, color=False)
        p = r.write.progress("gates")
        p.clear()
        assert stream.getvalue() == ""

    # frob:tests src/frob/render/_renderer.py::Progress.__exit__
    def test_progress_context_manager_clears_on_exit(self) -> None:
        """Using `Progress` as a context manager clears the drawn line on
        exit, even when the block raises."""
        stream = _FakeStream(tty=True)
        r = Renderer(stream, color=False)
        with r.write.progress("gates") as p:
            p.update("gates", 2, 4)
        final_segment = stream.getvalue().split("\r")[-1]
        assert final_segment.strip() == ""

    # frob:tests src/frob/render/_renderer.py::Progress.__exit__
    def test_progress_context_manager_clears_even_on_exception(self) -> None:
        """A raised exception inside the `with` block still clears the
        progress line before propagating."""
        stream = _FakeStream(tty=True)
        r = Renderer(stream, color=False)
        with pytest.raises(ValueError):
            with r.write.progress("gates") as p:
                p.update("gates", 1, 2)
                raise ValueError("boom")
        final_segment = stream.getvalue().split("\r")[-1]
        assert final_segment.strip() == ""

    # frob:tests src/frob/render/_renderer.py::Progress.update
    def test_progress_shorter_next_line_pads_over_stale_tail(self) -> None:
        """When a later `update` produces a shorter line than the previous
        one, the redraw pads with spaces so no stale tail survives."""
        stream = _FakeStream(tty=True)
        p = Progress(stream, tty=True)
        p.update("a very long stage name here", 1, 2)
        stream.seek(0)
        stream.truncate(0)
        p.update("x", 2, 2)
        out = stream.getvalue()
        assert out.startswith("\rx [")
        assert out.rstrip("\n") == out  # single redraw, no newline emitted
        assert len(out) - len("\r") >= len("a very long stage name here [")
