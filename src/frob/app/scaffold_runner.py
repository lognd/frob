from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.scaffold._managed import apply_managed_blocks
from frob.scaffold._pool import lease_worktree, pool_status, warm_pool
from frob.scaffold._unity_project import render_unity_project
from frob.scaffold.project import list_project_types, render_project

_log = get_logger(__name__)


# frob:ticket T-0877
# frob:tests tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli.test_warm_lease_status_roundtrip  # noqa: E501
# frob:waive ARCH103 reason="T-0977: thin CLI wrapper dispatching to \
# warm_pool/lease_worktree/pool_status by subcommand and rendering the result \
# text-or-json -- the dispatch+render IS this wrapper's whole documented job (see \
# docstring)"
def _run_pool(cfg: AppConfig) -> None:
    """`frob scaffold pool warm/lease/status` (T-0877): thin CLI wrapper
    over `frob.scaffold._pool`'s `warm_pool`/`lease_worktree`/
    `pool_status`, the same three operations the Makefile's
    `pool-warm`/`pool-lease`/`pool-status` inline-python shims called
    directly -- this is what those targets now delegate to."""
    pool_cmd = cfg.scaffold_pool_command
    repo_root = Path(".")

    if pool_cmd == "warm":
        warmed = warm_pool(repo_root, cfg.scaffold_pool_n)
        if warmed.is_err:
            _log.error("pool-warm failed: %s", warmed.danger_err.value)
            sys.exit(1)
        for entry in warmed.danger_ok:
            _log.info("%d: %s ready=%s", entry.index, entry.path, entry.ready)
        return

    if pool_cmd == "lease":
        leased = lease_worktree(repo_root)
        if leased.is_err:
            _log.error("pool-lease failed: %s", leased.danger_err.value)
            sys.exit(1)
        _log.info(str(leased.danger_ok.path))
        return

    if pool_cmd == "status":
        status = pool_status(repo_root)
        if status.is_err:
            _log.error("pool-status failed: %s", status.danger_err.value)
            sys.exit(1)
        for entry in status.danger_ok:
            _log.info("%d: %s ready=%s", entry.index, entry.path, entry.ready)
        return

    _log.error("frob scaffold pool requires a subcommand (warm/lease/status)")
    sys.exit(1)


# frob:ticket T-4578
# frob:tests tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli.test_success  # noqa: E501
# frob:tests tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli.test_output_exists_refusal  # noqa: E501
# frob:tests tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli.test_not_a_unity_project  # noqa: E501
def _run_unity_project(cfg: AppConfig) -> None:
    """`frob scaffold unity-project <dir> [--force]` (T-4578): thin CLI
    wrapper over T-4503's `render_unity_project`, whose root-only
    signature does not fit `render_project`'s uniform type+name+output
    dispatch (see `render_unity_project`'s own docstring) -- routes each
    `ScaffoldError` to a clean logged message and a non-zero exit rather
    than letting one escape as a raw exception."""
    root = cfg.scaffold_unity_root
    if root is None:
        _log.error("frob scaffold unity-project requires <dir>")
        sys.exit(1)

    force = cfg.scaffold_unity_force
    result = render_unity_project(Path(root), force=force)

    if result.is_err:
        _log.error("scaffold unity-project failed: %s", result.danger_err.value)
        sys.exit(1)

    for p in result.danger_ok:
        _log.info("created %s", p)


# frob:doc docs/modules/app.md#runners
# frob:doc docs/guides/worktree-pool.md#cli-frob-scaffold-pool-t-0877
# frob:doc docs/modules/land-profiles.md#land-profiles-rapid-vs-standard-t-4416
# frob:ticket T-0736
# frob:ticket T-4578
# frob:ticket T-4416
# frob:tests tests/system/test_cli_scaffold_apply.py::TestScaffoldApplyCli.test_apply_reports_changes  # noqa: E501
# frob:tests tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli.test_success  # noqa: E501
# frob:tests tests/system/test_cli_scaffold_apply.py::TestScaffoldNewProfileRecommendation.test_new_small_project_prints_no_recommendation  # noqa: E501
# frob:waive AFFECT001 reason="see T-4416's Done report / ticket body for why \
# app.md#runners and worktree-pool.md need no edit"
def run(cfg: AppConfig) -> None:
    cmd = cfg.scaffold_command
    if cmd in ("list", None):
        for t in list_project_types():
            _log.info(t)
        return

    if cmd == "apply":
        result = apply_managed_blocks(Path("."))
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        for line in result.danger_ok:
            _log.info(line)
        return

    if cmd == "pool":
        _run_pool(cfg)
        return

    if cmd == "unity-project":
        _run_unity_project(cfg)
        return

    if cmd == "exports":
        _run_exports(cfg)
        return

    proj_type = cfg.scaffold_type
    proj_name = cfg.scaffold_name

    if proj_type is None or proj_name is None:
        _log.error("frob scaffold new requires <type> and <name>")
        sys.exit(1)

    out_dir = cfg.scaffold_output or Path(".")
    force = cfg.scaffold_force
    result = render_project(proj_type, proj_name, out_dir, force=force)

    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    for p in result.danger_ok:
        _log.info("created %s", p)

    _print_profile_recommendation(out_dir / proj_name)


# frob:ticket T-4416
def _print_profile_recommendation(project_dir: Path) -> None:
    """T-4416: after `frob scaffold new` writes a fresh project's
    `frob.toml` (every manifest in `frob.scaffold.project._MANIFESTS`
    includes one), measure the newly-created `project_dir` the same way
    `frob doctor` measures an existing repo (`frob.doctor.
    profile_recommendation`) and print the same advisory nudge if it is
    already above `_PROFILE_RECOMMEND_THRESHOLD` -- in practice a brand
    new scaffold is essentially always below threshold (0 tickets, a
    handful of template files), so this almost always prints nothing,
    matching acceptance criterion 3 (never force `rapid` below
    threshold); it exists for the rarer case of scaffolding a new project
    type INTO an already-large existing tree (`--output` pointed at one)."""
    from frob.doctor import profile_recommendation

    recommendation = profile_recommendation(project_dir)
    if recommendation:
        _log.info(recommendation)


# frob:ticket T-4692
def _run_exports(cfg: AppConfig) -> None:
    """`frob scaffold exports <path>` (T-4692): the GENERATE half of the
    old flat `frob exports` verb (owner decision 2026-09-19: scaffolding
    output, not analysis) -- delegates straight into `frob.app.
    exports_runner.run`, the unchanged implementation, so behavior is
    identical to the pre-fold standalone verb. The CHECK half (missing-
    exports detection) is unrelated code that already runs as `frob
    check --only exports`."""
    from frob.app.exports_runner import run as exports_run

    exports_run(cfg)
