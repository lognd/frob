"""PERF015/PERF016 (T-5136): loop-variant effectful call detectors --
positive-control (a real per-iteration spawn with a loop-variable
pathspec) and negative-control (loop-invariant, PERF008's own territory)
cases, plus PERF015's iteration-source-name threshold.

# frob:ticket T-5136
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import parse_file
from frob.perf._loop_variant import loop_variant_effect_violations


def _write(root: Path, name: str, src: str) -> Path:
    """Write `src` to `root/name`, returning the path -- shared test setup."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


class TestPerf016:
    """PERF016: git-spawn shape, unconditional -- exactly the T-5135 H3
    audit specimen (`git show base:<path>` once per loop-variant path)."""

    # frob:tests src/frob/perf/_loop_variant.py::loop_variant_effect_violations
    def test_git_spawn_with_loop_variable_pathspec_is_flagged(
        self, tmp_path: Path
    ) -> None:
        src = (
            "import subprocess\n\n\n"
            "def scan(paths, base):\n"
            "    for path in paths:\n"
            "        subprocess.run(['git', 'show', base + ':' + path])\n"
        )
        parsed = parse_file(_write(tmp_path, "mod.py", src)).danger_ok
        violations = loop_variant_effect_violations([parsed])
        assert any(v.rule == "PERF016" for v in violations)

    # frob:tests src/frob/perf/_loop_variant.py::loop_variant_effect_violations

    def test_loop_invariant_spawn_is_not_flagged_by_perf016(
        self, tmp_path: Path
    ) -> None:
        src = (
            "import subprocess\n\n\n"
            "def scan(items, fixed_ref):\n"
            "    for _item in items:\n"
            "        subprocess.run(['git', 'show', fixed_ref])\n"
        )
        parsed = parse_file(_write(tmp_path, "mod.py", src)).danger_ok
        violations = loop_variant_effect_violations([parsed])
        assert not any(v.rule == "PERF016" for v in violations)


class TestPerf015:
    """PERF015: the general negation of PERF008, gated by the
    iteration-source-name threshold so trivial loop-variant calls do not
    flood the report."""

    # frob:tests src/frob/perf/_loop_variant.py::loop_variant_effect_violations
    def test_loop_variant_ticket_id_spawn_is_flagged_advisory(
        self, tmp_path: Path
    ) -> None:
        src = (
            "import subprocess\n\n\n"
            "def scan(ticket_ids):\n"
            "    for ticket_id in ticket_ids:\n"
            "        subprocess.run(['git', 'show', ticket_id])\n"
        )
        parsed = parse_file(_write(tmp_path, "mod.py", src)).danger_ok
        violations = loop_variant_effect_violations([parsed])
        assert any(v.rule == "PERF015" for v in violations)

    # frob:tests src/frob/perf/_loop_variant.py::loop_variant_effect_violations
    def test_loop_variant_call_without_iteration_source_name_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        src = (
            "import subprocess\n\n\n"
            "def scan(widgets):\n"
            "    for widget in widgets:\n"
            "        subprocess.run(['git', 'show', widget])\n"
        )
        parsed = parse_file(_write(tmp_path, "mod.py", src)).danger_ok
        violations = loop_variant_effect_violations([parsed])
        assert not any(v.rule == "PERF015" for v in violations)
