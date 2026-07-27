"""PERF008 (T-0775): loop-invariant effectful call detector -- true-positive
(direct fs-walk, transitive spawn two hops deep, the real T-0773 ticket-row
shape) and false-positive (loop-varying argument) cases.

# frob:ticket T-0775
"""

from __future__ import annotations

from pathlib import Path

from frob.graph import build_graph
from frob.lang import parse_file
from frob.perf import loop_invariant_effect_violations
from frob.perf._rules import perf_rules


def _write(root: Path, name: str, src: str) -> Path:
    """Write `src` to `root/name`, returning the path -- shared test setup."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


class TestPerf008LoopInvariantEffect:
    """T-0775's own acceptance: fires on a loop-invariant transitively-
    effectful call (including the real pre-T-0773 ticket-row shape),
    never on a loop-varying one."""

    def test_fs_walk_direct_call_in_loop_is_flagged(self, tmp_path: Path) -> None:
        """`os.walk(fixed_root)` inside a loop with no per-iteration
        variation in its argument is a direct PERF008 hit."""
        src = (
            "import os\n\n\n"
            "def scan_all(items, fixed_root):\n"
            "    for _item in items:\n"
            "        for _dirpath, _dirs, _files in os.walk(fixed_root):\n"
            "            pass\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok

        violations = loop_invariant_effect_violations([parsed])
        assert any(v.rule == "PERF008" for v in violations)

    def test_loop_invariant_spawn_call_two_hops_deep_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """A loop calls a helper (in a DIFFERENT module) whose own body
        calls a second helper that finally spawns a subprocess -- the
        transitive, cross-module reachability case, with an argument that
        never varies across iterations."""
        _write(
            tmp_path,
            "gitio.py",
            "import subprocess\n\n\n"
            "def run_argv(argv):\n"
            "    return subprocess.run(argv, capture_output=True)\n",
        )
        _write(
            tmp_path,
            "helper.py",
            "from gitio import run_argv\n\n\n"
            "def common_dir(root):\n"
            "    return run_argv(['git', '-C', root, 'rev-parse', "
            "'--git-common-dir'])\n",
        )
        src = (
            "from helper import common_dir\n\n\n"
            "def read_all_leases(tickets, root):\n"
            "    for _ticket in tickets:\n"
            "        common_dir(root)\n"
        )
        path = _write(tmp_path, "leases.py", src)
        gitio_parsed = parse_file(tmp_path / "gitio.py").danger_ok
        helper_parsed = parse_file(tmp_path / "helper.py").danger_ok
        leases_parsed = parse_file(path).danger_ok

        violations = loop_invariant_effect_violations(
            [gitio_parsed, helper_parsed, leases_parsed]
        )
        assert any(v.rule == "PERF008" for v in violations)

    def test_ticket_row_rev_parse_shape_fires_on_real_repo_history_fixture(
        self, tmp_path: Path
    ) -> None:
        """The pre-T-0773 shape verbatim: a `read_all_leases`-style loop
        over ticket rows re-deriving the same repo root via a
        `git rev-parse --git-common-dir` spawn on every row -- fires, and
        is wired all the way through `perf_rules` (not just the standalone
        detector), matching PERF007's own precedent."""
        _write(
            tmp_path,
            "gitio.py",
            "import subprocess\n\n\n"
            "def run_argv(argv):\n"
            "    return subprocess.run(argv, capture_output=True)\n",
        )
        src = (
            "from gitio import run_argv\n\n\n"
            "def _git_common_dir(root):\n"
            "    return run_argv(['git', '-C', root, 'rev-parse', "
            "'--git-common-dir'])\n\n\n"
            "def read_all_leases(ticket_rows, root):\n"
            "    leases = []\n"
            "    for _row in ticket_rows:\n"
            "        leases.append(_git_common_dir(root))\n"
            "    return leases\n"
        )
        path = _write(tmp_path, "tickets.py", src)
        gitio_parsed = parse_file(tmp_path / "gitio.py").danger_ok
        tickets_parsed = parse_file(path).danger_ok
        cache = tmp_path / ".frob" / "cache.db"
        snapshot = build_graph(tmp_path, cache).danger_ok

        violations = loop_invariant_effect_violations([gitio_parsed, tickets_parsed])
        assert any(v.rule == "PERF008" for v in violations)
        assert any(
            v.rule == "PERF008"
            for v in perf_rules(snapshot, [gitio_parsed, tickets_parsed])
        )

    def test_loop_varying_argument_is_not_flagged(self, tmp_path: Path) -> None:
        """The exact same shape, but the call's argument is the loop's own
        bound variable (a genuinely per-iteration value) -- no finding."""
        _write(
            tmp_path,
            "gitio.py",
            "import subprocess\n\n\n"
            "def run_argv(argv):\n"
            "    return subprocess.run(argv, capture_output=True)\n",
        )
        src = (
            "from gitio import run_argv\n\n\n"
            "def _git_common_dir(root):\n"
            "    return run_argv(['git', '-C', root, 'rev-parse', "
            "'--git-common-dir'])\n\n\n"
            "def read_all_leases(ticket_rows):\n"
            "    leases = []\n"
            "    for _row in ticket_rows:\n"
            "        leases.append(_git_common_dir(_row.root))\n"
            "    return leases\n"
        )
        path = _write(tmp_path, "tickets.py", src)
        gitio_parsed = parse_file(tmp_path / "gitio.py").danger_ok
        tickets_parsed = parse_file(path).danger_ok

        violations = loop_invariant_effect_violations([gitio_parsed, tickets_parsed])
        assert not any(v.rule == "PERF008" for v in violations)

    # frob:waive DUP001 reason="parallel test methods within test_loop_effects.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_no_effectful_call_in_loop_is_not_flagged(self, tmp_path: Path) -> None:
        """A loop calling a harmless, non-effectful helper never fires,
        regardless of argument invariance."""
        src = (
            "def add_one(x):\n"
            "    return x + 1\n\n\n"
            "def run(items, fixed):\n"
            "    for _item in items:\n"
            "        add_one(fixed)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok

        violations = loop_invariant_effect_violations([parsed])
        assert violations == ()

    def test_loop_invariant_spawn_call_three_hops_deep_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """T-0922 acceptance (a): the substrate must fire IDENTICALLY
        regardless of how many hops separate the loop call site from the
        directly-effectful callee -- one hop deeper than the T-0775
        two-hop precedent above, through THREE distinct helper functions
        across THREE distinct modules."""
        _write(
            tmp_path,
            "gitio.py",
            "import subprocess\n\n\n"
            "def run_argv(argv):\n"
            "    return subprocess.run(argv, capture_output=True)\n",
        )
        _write(
            tmp_path,
            "inner_helper.py",
            "from gitio import run_argv\n\n\n"
            "def common_dir(root):\n"
            "    return run_argv(['git', '-C', root, 'rev-parse', "
            "'--git-common-dir'])\n",
        )
        _write(
            tmp_path,
            "outer_helper.py",
            "from inner_helper import common_dir\n\n\n"
            "def resolve_root(root):\n"
            "    return common_dir(root)\n",
        )
        src = (
            "from outer_helper import resolve_root\n\n\n"
            "def read_all_leases(tickets, root):\n"
            "    for _ticket in tickets:\n"
            "        resolve_root(root)\n"
        )
        path = _write(tmp_path, "leases.py", src)
        files = [
            parse_file(tmp_path / "gitio.py").danger_ok,
            parse_file(tmp_path / "inner_helper.py").danger_ok,
            parse_file(tmp_path / "outer_helper.py").danger_ok,
            parse_file(path).danger_ok,
        ]

        violations = loop_invariant_effect_violations(files)
        assert any(v.rule == "PERF008" for v in violations)

    # frob:waive DUP001 reason="parallel test methods within test_loop_effects.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_unresolvable_callee_does_not_crash_and_does_not_fire(
        self, tmp_path: Path
    ) -> None:
        """T-0922 acceptance (c), PERF008's Unknown policy: a loop calling a
        name this substrate cannot bind to any local definition (an
        external/stdlib-style boundary with no matching symbol anywhere in
        the parsed set) degrades to "no effect found via this name" --
        never a crash, never a finding manufactured from the unresolved
        edge."""
        src = (
            "def run(items, fixed):\n"
            "    for _item in items:\n"
            "        totally_unbound_external_call(fixed)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok

        violations = loop_invariant_effect_violations([parsed])
        assert violations == ()
