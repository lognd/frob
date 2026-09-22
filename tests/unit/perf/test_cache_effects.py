"""PERF017/PERF018 (T-5136): success-only cache writes and discarded
hoisted values -- positive-control specimens mirroring the T-5135 audit's
H2 and H4 shapes.

# frob:ticket T-5136
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import parse_file
from frob.perf._cache_effects import cache_effect_violations


def _write(root: Path, name: str, src: str) -> Path:
    """Write `src` to `root/name`, returning the path -- shared test setup."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


class TestPerf017:
    """PERF017: an if/else where only one returning branch writes to the
    cache -- the H2 audit shape (unmeasurable outcome never memoized)."""

    # frob:tests src/frob/perf/_cache_effects.py::cache_effect_violations  # noqa: E501
    def test_success_only_cache_write_is_flagged(self, tmp_path: Path) -> None:
        src = (
            "def recheck(root, pairs):\n"
            "    result = measure(root, pairs)\n"
            "    if result is not None:\n"
            "        write_cache(root, result)\n"
            "        return result\n"
            "    else:\n"
            "        return None\n"
        )
        parsed = parse_file(_write(tmp_path, "mod.py", src)).danger_ok
        violations = cache_effect_violations([parsed])
        assert any(v.rule == "PERF017" for v in violations)
# frob:tests src/frob/perf/_cache_effects.py::cache_effect_violations  # noqa: E501

    def test_both_branches_writing_cache_is_not_flagged(self, tmp_path: Path) -> None:
        src = (
            "def recheck(root, pairs):\n"
            "    result = measure(root, pairs)\n"
            "    if result is not None:\n"
            "        write_cache(root, result)\n"
            "        return result\n"
            "    else:\n"
            "        write_cache(root, None)\n"
            "        return None\n"
        )
        parsed = parse_file(_write(tmp_path, "mod.py", src)).danger_ok
        violations = cache_effect_violations([parsed])
        assert not any(v.rule == "PERF017" for v in violations)


class TestPerf018:
    """PERF018: a hoisted expensive value recomputed by a transitive
    callee inside the loop -- the H4 audit shape (`read_all_leases`
    hoisted, then re-scanned one frame below the loop)."""

    # frob:tests src/frob/perf/_cache_effects.py::cache_effect_violations  # noqa: E501
    def test_hoisted_value_recomputed_in_loop_is_flagged(self, tmp_path: Path) -> None:
        src = (
            "def find_leaked(root, others):\n"
            "    leases = read_all_leases(root)\n"
            "    for other_id in others:\n"
            "        branch = sibling_branch_ref(root, other_id, read_all_leases(root))\n"
            "    return leases\n"
        )
        parsed = parse_file(_write(tmp_path, "mod.py", src)).danger_ok
        violations = cache_effect_violations([parsed])
        assert any(v.rule == "PERF018" for v in violations)

    # frob:tests src/frob/perf/_cache_effects.py::cache_effect_violations  # noqa: E501
    def test_hoisted_value_threaded_through_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        src = (
            "def find_leaked(root, others):\n"
            "    leases = read_all_leases(root)\n"
            "    for other_id in others:\n"
            "        branch = sibling_branch_ref(root, other_id, leases)\n"
            "    return leases\n"
        )
        parsed = parse_file(_write(tmp_path, "mod.py", src)).danger_ok
        violations = cache_effect_violations([parsed])
        assert not any(v.rule == "PERF018" for v in violations)
