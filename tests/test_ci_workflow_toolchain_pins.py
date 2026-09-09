"""T-4338: neither CI leg pinned a `uv` version, so the three platform legs
could silently run different toolchains. The setup action caches the
binary under a key including OS/arch/system-Python; one leg's cache HIT
reused an older `uv` while another's cache MISS pulled the current
release, whose new strict validation rule produced 68 failures that
looked like a platform bug (T-4327). Locks that every toolchain this
workflow installs -- uv, the Rust toolchain, and maturin -- is pinned to
an explicit version read from one place, and that a resolved-version
report step exists so a failed run states what it actually used.
"""

from pathlib import Path

import yaml

# frob:ticket T-4338
_CI_WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
)


# frob:ticket T-4338
def _load_ci_workflow() -> dict:
    """Parse .github/workflows/ci.yml (frob:tests target) into a dict."""
    return yaml.safe_load(_CI_WORKFLOW_PATH.read_text(encoding="utf-8"))


# frob:ticket T-4338
def _assert_every_step_pins(
    workflow: dict, *, uses_prefix: str, with_key: str, env_var: str
) -> None:
    """Every step whose `uses:` starts with `uses_prefix` must set
    `with.<with_key>` to `${{ env.<env_var> }}` -- the shared shape behind
    each toolchain-pin assertion below (uv/Rust/maturin all install a
    tool this workflow builds and tests with, so all three must resolve
    identically across every platform leg, T-4327)."""
    all_steps = [
        step for job in workflow["jobs"].values() for step in job.get("steps", [])
    ]
    steps = [
        step for step in all_steps if str(step.get("uses", "")).startswith(uses_prefix)
    ]
    assert steps, f"expected at least one {uses_prefix} step"
    expected = "${{ env." + env_var + " }}"
    for step in steps:
        actual = (step.get("with") or {}).get(with_key)
        assert actual == expected, (
            f"{uses_prefix} step {step.get('name')!r} does not pin "
            f"{with_key}: {expected} -- an unpinned leg can silently "
            "resolve a different toolchain version than its siblings "
            "(T-4327)"
        )


# frob:ticket T-4338
class TestUvVersionIsPinned:
    """T-4338/T-4327: an unpinned `uv` let ubuntu's cache-hit stale binary
    and macOS's cache-miss current release silently diverge."""

    # frob:ticket T-4338
    def test_workflow_declares_a_uv_version_pin(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        assert workflow.get("env", {}).get("UV_VERSION"), (
            "ci.yml must declare env.UV_VERSION at workflow scope so every "
            "leg reads the same pin"
        )

    # frob:ticket T-4338
    def test_every_setup_uv_step_pins_the_shared_version(self) -> None:
        # frob:tests .github/workflows/ci.yml
        _assert_every_step_pins(
            _load_ci_workflow(),
            uses_prefix="astral-sh/setup-uv@",
            with_key="version",
            env_var="UV_VERSION",
        )


# frob:ticket T-4338
class TestRustToolchainVersionIsPinned:
    """T-4338: dtolnay/rust-toolchain with no `toolchain:` input resolves
    whatever 'stable' means on the day it runs -- the same class of
    cross-leg drift risk as the unpinned uv, just not yet measured to
    have bitten."""

    # frob:ticket T-4338
    def test_workflow_declares_a_rust_toolchain_pin(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        assert workflow.get("env", {}).get("RUST_TOOLCHAIN_VERSION"), (
            "ci.yml must declare env.RUST_TOOLCHAIN_VERSION at workflow "
            "scope so every leg reads the same pin"
        )

    # frob:ticket T-4338
    def test_every_rust_toolchain_step_pins_the_shared_version(self) -> None:
        # frob:tests .github/workflows/ci.yml
        _assert_every_step_pins(
            _load_ci_workflow(),
            uses_prefix="dtolnay/rust-toolchain@",
            with_key="toolchain",
            env_var="RUST_TOOLCHAIN_VERSION",
        )


# frob:ticket T-4338
class TestMaturinVersionIsPinned:
    """T-4338: PyO3/maturin-action with no `maturin-version:` installs
    latest-matching-constraint at run time, an unpinned toolchain input of
    the same shape as the uv/Rust ones."""

    # frob:ticket T-4338
    def test_workflow_declares_a_maturin_version_pin(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        assert workflow.get("env", {}).get("MATURIN_VERSION"), (
            "ci.yml must declare env.MATURIN_VERSION at workflow scope so "
            "every leg reads the same pin"
        )

    # frob:ticket T-4338
    def test_every_maturin_action_step_pins_the_shared_version(self) -> None:
        # frob:tests .github/workflows/ci.yml
        _assert_every_step_pins(
            _load_ci_workflow(),
            uses_prefix="PyO3/maturin-action@",
            with_key="maturin-version",
            env_var="MATURIN_VERSION",
        )


# frob:ticket T-4338
class TestResolvedToolchainVersionsAreReported:
    """T-4338: 'make the run state what it used' -- a version a reader
    must infer from a setup action's own cache-hit-or-miss log line is
    not reported."""

    # frob:ticket T-4338
    def test_build_job_prints_resolved_toolchain_versions(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        build_steps = workflow["jobs"]["build"]["steps"]
        names = [step.get("name", "") for step in build_steps]
        assert any("Print resolved toolchain versions" in name for name in names), (
            "build job has no step reporting the resolved uv/rustc/cargo "
            "versions where a reader of the run would see them"
        )

    # frob:ticket T-4338
    def test_standalone_install_job_prints_resolved_toolchain_versions(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["standalone-install"]["steps"]
        names = [step.get("name", "") for step in steps]
        assert any("Print resolved toolchain versions" in name for name in names), (
            "standalone-install job has no step reporting the resolved "
            "toolchain versions it used"
        )
