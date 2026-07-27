"""PERF012 (T-0919): duplicate-identical-subprocess-spawn-within-one-
call-path detector -- true-positive (two distinct helpers each spawning
the textually-identical subprocess from one caller, the real T-0919
`_check_gates_summary_fn`/`_check_gate_findings_fn` shape) and
false-positive (different argument shapes; only one helper called) cases.

# frob:ticket T-0919
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import parse_file
from frob.perf._dup_spawn import duplicate_spawn_violations


def _write(root: Path, name: str, src: str) -> Path:
    """Write `src` to `root/name`, returning the path -- shared test setup."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


class TestPerf012DuplicateSpawn:
    """T-0919's own acceptance: fires when one function's body calls two
    distinct helpers that each independently spawn a subprocess with the
    SAME argument shape (the before-fix `_done_report` shape), never when
    the two helpers' spawn arguments differ, and never for a single call."""

    def test_two_helpers_spawning_identical_subprocess_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """The real T-0919 shape, minimized: `caller` calls both
        `check_gates` and `check_gate_findings`, each independently
        spawning `subprocess.run(["frob", "check", "--ticket", ticket_id],
        cwd=root, timeout=600)` -- textually identical argument lists."""
        src = (
            "import subprocess\n\n\n"
            "def check_gates(root, ticket_id):\n"
            "    return subprocess.run(\n"
            '        ["frob", "check", "--ticket", ticket_id],\n'
            "        cwd=root,\n"
            "        timeout=600,\n"
            "    )\n\n\n"
            "def check_gate_findings(root, ticket_id):\n"
            "    return subprocess.run(\n"
            '        ["frob", "check", "--ticket", ticket_id],\n'
            "        cwd=root,\n"
            "        timeout=600,\n"
            "    )\n\n\n"
            "def caller(root, ticket_id):\n"
            "    gates = check_gates(root, ticket_id)\n"
            "    findings = check_gate_findings(root, ticket_id)\n"
            "    return gates, findings\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok

        violations = duplicate_spawn_violations([parsed])
        assert any(v.rule == "PERF012" for v in violations)

    def test_two_helpers_spawning_different_subprocess_args_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """Same two-helper caller shape, but the two spawn calls have
        genuinely DIFFERENT argument lists (one checks tickets, the other
        checks lint) -- not a duplicated cost, must not fire."""
        src = (
            "import subprocess\n\n\n"
            "def check_gates(root, ticket_id):\n"
            "    return subprocess.run(\n"
            '        ["frob", "check", "--ticket", ticket_id],\n'
            "        cwd=root,\n"
            "    )\n\n\n"
            "def check_lint(root):\n"
            "    return subprocess.run(\n"
            '        ["frob", "check", "--only", "lint"],\n'
            "        cwd=root,\n"
            "    )\n\n\n"
            "def caller(root, ticket_id):\n"
            "    gates = check_gates(root, ticket_id)\n"
            "    lint = check_lint(root)\n"
            "    return gates, lint\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok

        violations = duplicate_spawn_violations([parsed])
        assert not any(v.rule == "PERF012" for v in violations)

    def test_single_helper_call_is_not_flagged(self, tmp_path: Path) -> None:
        """Calling just ONE spawning helper once is the ordinary, non-
        duplicated case -- never a PERF012 finding on its own."""
        src = (
            "import subprocess\n\n\n"
            "def check_gates(root, ticket_id):\n"
            "    return subprocess.run(\n"
            '        ["frob", "check", "--ticket", ticket_id],\n'
            "        cwd=root,\n"
            "    )\n\n\n"
            "def caller(root, ticket_id):\n"
            "    return check_gates(root, ticket_id)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok

        violations = duplicate_spawn_violations([parsed])
        assert not any(v.rule == "PERF012" for v in violations)

    def test_multi_hop_duplicate_via_different_intermediate_callees_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """The INTERPROCEDURAL case the user directive specifically named:
        `caller` calls `path_a` and `path_b`; `path_a` calls `helper_a`
        which spawns; `path_b` calls `helper_b` which ALSO spawns the SAME
        argv -- two hops deep on each side, through four totally distinct
        named functions, the duplicate split across sibling callees at
        every level. Must still fire, proving the detector is NOT limited
        to same-function or single-hop scanning."""
        src = (
            "import subprocess\n\n\n"
            "def helper_a(root, ticket_id):\n"
            "    return subprocess.run(\n"
            '        ["frob", "check", "--ticket", ticket_id],\n'
            "        cwd=root,\n"
            "    )\n\n\n"
            "def helper_b(root, ticket_id):\n"
            "    return subprocess.run(\n"
            '        ["frob", "check", "--ticket", ticket_id],\n'
            "        cwd=root,\n"
            "    )\n\n\n"
            "def path_a(root, ticket_id):\n"
            "    return helper_a(root, ticket_id)\n\n\n"
            "def path_b(root, ticket_id):\n"
            "    return helper_b(root, ticket_id)\n\n\n"
            "def caller(root, ticket_id):\n"
            "    a = path_a(root, ticket_id)\n"
            "    b = path_b(root, ticket_id)\n"
            "    return a, b\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok

        violations = duplicate_spawn_violations([parsed])
        assert any(v.rule == "PERF012" and "caller" in v.message for v in violations)

    def test_call_site_varying_argument_is_not_flagged(self, tmp_path: Path) -> None:
        """Same multi-hop shape as the true positive, but each leaf spawn's
        argument is genuinely per-call-site distinct (a different
        `ticket_id` LITERAL baked into each helper, not a shared
        parameter) -- the two paths are NOT actually duplicated cost, must
        not fire."""
        src = (
            "import subprocess\n\n\n"
            "def helper_a(root):\n"
            "    return subprocess.run(\n"
            '        ["frob", "check", "--ticket", "T-0001"],\n'
            "        cwd=root,\n"
            "    )\n\n\n"
            "def helper_b(root):\n"
            "    return subprocess.run(\n"
            '        ["frob", "check", "--ticket", "T-0002"],\n'
            "        cwd=root,\n"
            "    )\n\n\n"
            "def path_a(root):\n"
            "    return helper_a(root)\n\n\n"
            "def path_b(root):\n"
            "    return helper_b(root)\n\n\n"
            "def caller(root):\n"
            "    a = path_a(root)\n"
            "    b = path_b(root)\n"
            "    return a, b\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok

        violations = duplicate_spawn_violations([parsed])
        assert not any(
            v.rule == "PERF012" and "caller" in v.message for v in violations
        )
