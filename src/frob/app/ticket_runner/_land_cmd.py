"""frob.app.ticket_runner._land_cmd -- the `land`/`merge-driver` command
family (T-1090/T-1078's atomic id-allocation and REL bump paths carried).

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/ scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim -- \
# carried from the pre-T-1089-split monolith's identical file-level waiver \
# (frob.app.ticket_runner/__init__.py)"

from __future__ import annotations

import sys
from pathlib import Path

from typani.result import Err, Ok

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.process._guard import ProcessGuardError

from ._verify import (
    _check_gate_findings_fn,
    _check_gates_summary_fn,
    _shared_check_spawn_fn,
)

_log = get_logger("frob.app.ticket_runner")


def _require_land_args(cfg: AppConfig) -> None:
    """Exit 1 (with a logged reason) unless `frob ticket land`'s required
    `<id>`/`--worktree <path>` args are both present."""
    if cfg.ticket_id is None:
        _log.error("frob ticket land requires <id>")
        sys.exit(1)
    if cfg.ticket_worktree is None:
        _log.error("frob ticket land requires --worktree <path>")
        sys.exit(1)


def _report_land_result(root: Path, report) -> None:  # noqa: ANN001
    """Log every field of a `LandReport`: the dry-run summary line, or the
    landed commit plus each changed file."""
    if report.dry_run:
        _log.info(
            "land %s: DRY RUN clean -- merged=%s wip_committed=%s "
            "(would finalize/close/squash-apply/commit onto %s)",
            report.ticket_id,
            report.merged_main_into_worktree,
            report.wip_committed,
            root,
        )
        return
    _log.info(
        "land %s: landed as %s at %s (%d file(s) changed)",
        report.ticket_id,
        report.final_id,
        report.commit_sha,
        len(report.files_changed),
    )
    for f in report.files_changed:
        _log.info("  %s", f)
    if report.release_bumped_to is not None:
        _log.info(
            "land %s: REL001 bumped to %s",
            report.ticket_id,
            report.release_bumped_to,
        )
    if report.natives_rebuilt:
        _log.info("land %s: native extension(s) rebuilt", report.ticket_id)


# frob:ticket T-0398
def _land_collected_fn(worktree: Path):  # noqa: ANN201
    """D-05 CLI closure: `land()` calls this with no args, AFTER its
    internal merge, to get the post-merge worktree's collected node ids.
    Best-effort -- a collection failure logs and returns an empty set
    (fail-closed: `land`'s post-merge check then treats every non-cmd
    evidence id as unresolved, refusing the landing, rather than silently
    skipping the check)."""

    def fn() -> frozenset[str]:
        from frob.app import ticket_runner as _ticket_runner

        collected = _ticket_runner._collect_python_and_rust_ids(worktree)
        if collected.is_err:
            _log.warning(
                "land: post-merge collection failed (%s) -- treating all "
                "evidence as unresolved",
                collected.danger_err,
            )
            return frozenset()
        python_ids, rust_ids, _runners = collected.danger_ok
        return python_ids | rust_ids

    return fn


# frob:ticket T-0398
def _land_passed_fn(worktree: Path):  # noqa: ANN201
    """D-05 CLI closure: `land()` calls this with the post-merge ticket's
    non-cmd evidence ids, AFTER its internal merge, and expects back the
    subset actually observed passing -- reuses `_verify_ids_passing`
    (D-01's same real-run verification) against the worktree."""

    def fn(node_ids) -> frozenset[str]:  # noqa: ANN001
        from frob.app import ticket_runner as _ticket_runner

        collected = _ticket_runner._collect_python_and_rust_ids(worktree)
        if collected.is_err:
            _log.warning(
                "land: post-merge collection failed (%s) -- treating all "
                "evidence as NOT passing",
                collected.danger_err,
            )
            return frozenset()
        python_ids, rust_ids, runners = collected.danger_ok
        from frob.app import ticket_runner as _ticket_runner

        return _ticket_runner._verify_ids_passing(
            worktree, node_ids, python_ids, rust_ids, runners
        )

    return fn


# frob:ticket T-0398
# frob:ticket T-0774
def _land_covers_scope_fn(worktree: Path):  # noqa: ANN201
    """D-05/D-02 CLI closure: `land()` calls this TWICE -- once (T-0774) as
    a PRE-merge preflight simulation with the worktree's still-unmerged
    `Ticket` (via `_land_precheck`), and once, as before, with the post-
    merge/post-finalize `Ticket` (via `_land_finalize_and_close`) -- and
    expects back the D-02 scope-binding answer computed against the
    WORKTREE's graph (not root's) either way. `worktree` itself does not
    change between the two calls (it is this same closure's captured
    argument); only the ticket state on disk under it does, since `land`'s
    internal merge mutates the worktree tree in between. The post-merge
    call remains authoritative -- the merged, about-to-be-squashed tree is
    the one whose scope/evidence actually matter -- the pre-merge call is
    only an early, best-effort refusal for the common case where the
    ticket's scope files are untouched by any concurrent main-side change."""

    def fn(ticket):  # noqa: ANN001, ANN202
        from frob.app import ticket_runner as _ticket_runner

        return _ticket_runner._covers_scope_for_ticket(worktree, ticket)

    return fn


# frob:ticket T-0338
def _land_bump_version_fn():  # noqa: ANN201
    """CLI closure: `land()` calls this AFTER the squash-apply is staged
    onto `root`, computing whatever `frob.release` says the just-squashed
    public API demands and applying it -- the REL001 half of T-0338's
    coordinator-plumbing consolidation. `frob.release`/`frob.graph` access
    lives here (the CLI layer), not in `frob.tickets` (docs/rework.md
    cycle-avoidance, same reasoning as `_land_covers_scope_fn`)."""

    def fn(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
        return _apply_release_bump_for_land(root, ticket, final_id)

    return fn


# frob:ticket T-1011
def _land_sync_gate_rules_fn():  # noqa: ANN201
    """CLI closure (T-1011): `land()` calls this AFTER the REL001 bump is
    staged onto `root`, letting a landing that changes `_KNOWN_GATE_RULES`
    (`src/frob/gates/__init__.py`) auto-file the matching `check-coverage.
    yaml` rows in the SAME commit -- ending the manual `frob registry audit
    --sync-gate-rules` re-sync docs/audits/coordination-churn.md's item 6
    disclosed drifting twice in one drive. `frob.gates`/`frob.registry`
    access lives here (the CLI layer), not in `frob.tickets` (docs/rework.md
    cycle-avoidance, same reasoning as `_land_bump_version_fn`)."""

    def fn(root: Path, pre_land_tip: str):  # noqa: ANN202
        return _sync_gate_rules_for_land(root, pre_land_tip)

    return fn


# frob:ticket T-1011
def _sync_gate_rules_for_land(root: Path, pre_land_tip: str):  # noqa: ANN201
    """The body of `_land_sync_gate_rules_fn`'s callback (T-1011): diffs
    `root`'s just-squashed working tree against `pre_land_tip` for
    `src/frob/gates/__init__.py`; if `_KNOWN_GATE_RULES` does not appear in
    that diff, nothing needs syncing (`Ok(None)`, the common case). If it
    does, scans `root`'s ON-DISK tree (`generated_gate_rule_ids`, the T-0964
    scanner -- never a live `frob.gates` import, which would read THIS
    process's own already-imported module, not root's freshly-squashed
    source) for the live rule-id set and appends any `check-coverage.yaml`
    row still missing one (`sync_gate_rule_entries`), staging the result.
    A registry-level failure (missing/malformed `check-coverage.yaml`) is
    logged and treated as `Ok(None)` -- best-effort, not a landing-critical
    guarantee the way a REL001 version bump is; only a git staging failure
    (a genuinely broken working tree) escalates to `Err(GitFailed)`, which
    `land()` unwinds exactly like a `bump_version` failure."""
    from frob.gates._rule_id_scan import generated_gate_rule_ids
    from frob.gitio import run_argv
    from frob.registry._staleness import sync_gate_rule_entries
    from frob.tickets._land import LandError

    diffed = run_argv(
        [
            "git",
            "-C",
            str(root),
            "diff",
            pre_land_tip,
            "--",
            "src/frob/gates/__init__.py",
        ]
    )
    if diffed.is_err:
        return Err(LandError.GitFailed)
    if "_KNOWN_GATE_RULES" not in diffed.danger_ok.stdout:
        return Ok(None)

    known = generated_gate_rule_ids(root)
    target = root / "docs" / "design" / "registry" / "check-coverage.yaml"
    synced = sync_gate_rule_entries(target, known)
    if synced.is_err:
        _log.warning(
            "land: gate-rule registry auto-sync skipped (%s at %s) -- run "
            "`frob registry audit --sync-gate-rules` by hand if needed",
            synced.danger_err,
            target,
        )
        return Ok(None)
    added = synced.danger_ok
    if not added:
        return Ok(None)
    staged = run_argv(
        [
            "git",
            "-C",
            str(root),
            "add",
            "--",
            "docs/design/registry/check-coverage.yaml",
        ]
    )
    if staged.is_err or staged.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(added)


# frob:ticket T-0338
# frob:ticket T-1007
def _required_release_bump(root: Path, final_id: str):  # noqa: ANN201
    """The REL001-required version string for `root`'s current public API
    against its tracked release manifest AS RECORDED AT ROOT'S OWN GIT HEAD
    (T-1007 -- never the worktree-carried on-disk copy), or `Ok(None)` if
    no bump is needed (no manifest yet, or `BumpClass.NONE`) -- split out of
    `_apply_release_bump_for_land` to keep each half under the ARCH001
    line-count threshold (T-0338)."""
    from frob.app import ticket_runner as _ticket_runner
    from frob.release import BumpClass, diff_class, required_version
    from frob.tickets._land import LandError

    manifest = _ticket_runner._root_release_manifest(root)
    if manifest is None:
        _log.debug("land: no release manifest at %s HEAD, skipping REL001 bump", root)
        return Ok(None)

    from frob.app import ticket_runner as _ticket_runner

    snapshot = _ticket_runner._graph_snapshot(root)
    if snapshot.is_err:
        _log.error(
            "land: %s graph unavailable (%s), cannot compute REL001 bump",
            final_id,
            snapshot.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)

    bump = diff_class(manifest, snapshot.danger_ok)
    if bump == BumpClass.NONE:
        return Ok(None)

    needed = required_version(manifest.version, bump)
    if needed.is_err:
        _log.error(
            "land: %s manifest version %r is not parseable, cannot compute REL001 bump",
            final_id,
            manifest.version,
        )
        return Err(LandError.ReleaseBumpFailed)
    return Ok(needed.danger_ok)


# frob:ticket T-0338
# frob:ticket T-1007
def _apply_release_bump_for_land(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN201
    """Compute the REL001 bump class for `root`'s just-squashed public API
    against its release manifest -- read from ROOT's OWN git HEAD via
    `_root_release_manifest` (T-1007: never the worktree-carried on-disk
    copy that rides the squash-apply, the root cause of the repeat
    monotonicity-guard refusals T-0992 could only catch, not prevent) --
    and, if the declared version does not already cover it, bump
    `pyproject.toml`'s `version`, append a minimal CHANGELOG.md entry
    (satisfies `_changelog_mentions`'s "the version string appears
    somewhere" contract), and `frob release stamp` the new manifest --
    staging all three files in `root`'s index so they land in the same
    commit as the squash-apply (T-0338).

    Returns `Ok(None)` (no write at all) when no manifest exists yet (the
    repo has never opted into `frob release stamp`) or when the diff class
    is `BumpClass.NONE`; `Ok(new_version)` after a successful bump+stamp;
    `Err(LandError.ReleaseBumpFailed)` on any failure along the way (an
    unreadable manifest, an unparsable `pyproject.toml` version, or a
    graph build failure) -- fail-closed, since a silently-skipped bump
    would let a landed API change slip past REL001 undetected."""
    from frob.gitio import run_argv
    from frob.release import stamp
    from frob.tickets._land import LandError

    needed = _required_release_bump(root, final_id)
    if needed.is_err:
        return Err(needed.danger_err)
    if needed.danger_ok is None:
        return Ok(None)
    new_version = needed.danger_ok

    written = _write_release_bump(root, ticket, final_id, new_version)
    if written.is_err:
        return Err(written.danger_err)

    from frob.app import ticket_runner as _ticket_runner

    fresh_snapshot = _ticket_runner._graph_snapshot(root)
    if fresh_snapshot.is_err:
        _log.error(
            "land: %s graph unavailable post-bump (%s), cannot stamp release manifest",
            final_id,
            fresh_snapshot.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)
    stamp(root, fresh_snapshot.danger_ok, new_version)

    staged = run_argv(
        [
            "git",
            "-C",
            str(root),
            "add",
            "pyproject.toml",
            "CHANGELOG.md",
            ".frob-release.json",
        ]
    )
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.error("land: %s failed to stage the REL001 bump files", final_id)
        return Err(LandError.ReleaseBumpFailed)
    return Ok(new_version)


# frob:ticket T-0338
# frob:ticket T-1009
def _write_release_bump(root: Path, ticket, final_id: str, new_version: str):  # noqa: ANN001, ANN201
    """Rewrite `root/pyproject.toml`'s `version = "..."` line to
    `new_version` and add a `## [new_version] - unreleased` CHANGELOG.md
    entry naming `final_id`/`ticket.title` (T-0338), via the shared
    `frob.release` helpers (T-1009 -- the same regex/insertion logic
    `frob release sync` uses, kept in one home rather than duplicated
    here)."""
    from frob.release import changelog_skeleton_entry, rewrite_pyproject_version
    from frob.tickets._land import LandError

    pyproject_path = root / "pyproject.toml"
    rewritten = rewrite_pyproject_version(root, new_version)
    if rewritten.is_err:
        _log.error(
            'land: %s could not find a `version = "..."` line in %s (%s)',
            final_id,
            pyproject_path,
            rewritten.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)

    changelog_skeleton_entry(root, new_version, note=f"{final_id}: {ticket.title}")
    _log.info(
        "land: %s wrote REL001 bump -> %s in %s and CHANGELOG.md",
        final_id,
        new_version,
        pyproject_path,
    )
    return Ok(None)


# frob:ticket T-0338
def _land_rebuild_natives_fn():  # noqa: ANN201
    """CLI closure: `land()` calls this with `root` only when the landed
    changeset touches a native source tree (frob-core/, strata-core/) --
    runs `make core` in `root` and returns whether it exited 0 (T-0338).
    Best-effort: `land` treats a `False` as a logged warning, never a hard
    failure (a native rebuild is cheap to re-run by hand, and a `make
    core` failure in a from-scratch clone is not necessarily this land's
    fault)."""

    def fn(root: Path) -> bool:
        # T-0803: routed through `guarded_subprocess_run` (T-0778's guard)
        # so `FROB_DISABLE_EXEC=1` refuses this `make core` spawn too;
        # treated as a failed rebuild (`False`, logged) rather than a hard
        # error, matching this function's existing best-effort contract.
        from frob.app import ticket_runner as _ticket_runner

        guarded = _ticket_runner.guarded_subprocess_run(
            ["make", "core"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if guarded.is_err:
            _log.warning(
                "land: `make core` in %s refused to spawn (%s)",
                root,
                ProcessGuardError.ExecDisabled,
            )
            return False
        result = guarded.danger_ok
        if result.returncode != 0:
            _log.warning(
                "land: `make core` in %s exited %d -- stdout=%r stderr=%r",
                root,
                result.returncode,
                result.stdout[-2000:],
                result.stderr[-2000:],
            )
        return result.returncode == 0

    return fn


def _land(root: Path, cfg: AppConfig) -> None:
    """`frob ticket land <id> --worktree <path> [--dry-run]`: run the whole
    merge-check-splice-close-commit chain via `frob.tickets.land`, reporting
    every field of the resulting `LandReport` (or the exact `Err` + remedy
    already logged by `land` itself) before exiting non-zero on failure.

    T-0398: this is the CLI's STRICT default -- `collected`/`passed`/
    `covers_scope` are ALWAYS supplied (as closures over the worktree,
    since `land`'s internal merge determines the post-merge state they
    must be computed against, see `land`'s own docstring), so a stale/
    red/unrelated evidence id can never silently land onto main through
    the real `frob ticket land` command, even though the library function
    itself still defaults to permissive (`None`) for other callers/tests.

    T-0338: `bump_version`/`rebuild_natives` are ALSO always supplied here
    (`_land_bump_version_fn`/`_land_rebuild_natives_fn`), folding the
    REL001 version-bump/stamp and native-rebuild-trigger coordinator steps
    into this same one command.

    T-0754: `check_gates` (`_check_gates_summary_fn`, the SAME closure
    `_done_report` captures with) is ALSO always supplied here, so a
    ticket carrying a `### Captured claims` section is re-verified against
    the post-merge tree before `frob ticket land` ever finalizes/closes/
    squash-applies it. The claim's test-count half reuses `passed` above
    -- no separate `run_tests` parameter at the land layer (review round 2
    fix #3: derive from D-05's own real run instead of a duplicate one)."""
    from frob.tickets import land
    from frob.tickets._land import _resolve_primary_checkout

    _require_land_args(cfg)
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced above
    assert cfg.ticket_worktree is not None
    worktree = cfg.ticket_worktree

    # T-1003 (churn item 4): `root` here is `(cfg.ticket_path or Path("."))
    # .resolve()` -- the invoker's cwd. `land()` itself now resolves the
    # SAME "root defaulted to inside --worktree" shape internally (see its
    # own T-1003 doc), but this CLI wrapper's own `root` local is used
    # AGAIN after `land()` returns, for `_report_land_result`/
    # `_push_after_land` -- resolving it here too (same shared helper,
    # not a re-implementation) keeps those post-land steps pointed at the
    # real primary checkout instead of silently reporting against/pushing
    # from the worktree path that was never actually landed onto.
    if root.resolve() == worktree.resolve():
        resolved_root = _resolve_primary_checkout(worktree)
        if resolved_root is not None and resolved_root != worktree.resolve():
            _log.info(
                "ticket land: %s root defaulted to the cwd inside "
                "--worktree (%s) -- resolved the primary checkout %s from "
                "its git common dir instead (T-1003), no manual cd "
                "required",
                cfg.ticket_id,
                root,
                resolved_root,
            )
            root = resolved_root

    if cfg.ticket_skip_mutation_evidence:
        _log.warning(
            "ticket land: %s --skip-mutation-evidence set -- a TEST016 "
            "confirmatory-only-evidence finding will be logged but will NOT "
            "refuse this land (justification required: use only for a "
            "genuine false positive)",
            cfg.ticket_id,
        )

    # T-0919: one shared spawn feeds BOTH check_gates/check_gate_findings
    # below instead of each running its own full `frob check --ticket`.
    _shared_spawn = _shared_check_spawn_fn(worktree, cfg.ticket_id)
    result = land(
        root,
        cfg.ticket_id,
        worktree,
        dry_run=cfg.ticket_dry_run,
        collected=_land_collected_fn(worktree),
        passed=_land_passed_fn(worktree),
        covers_scope=_land_covers_scope_fn(worktree),
        bump_version=_land_bump_version_fn(),
        rebuild_natives=_land_rebuild_natives_fn(),
        sync_gate_rules=_land_sync_gate_rules_fn(),
        check_gates=_check_gates_summary_fn(
            worktree, cfg.ticket_id, spawn=_shared_spawn
        ),
        check_gate_findings=_check_gate_findings_fn(
            worktree, cfg.ticket_id, spawn=_shared_spawn
        ),
        skip_mutation_evidence=cfg.ticket_skip_mutation_evidence,
    )
    if result.is_err:
        _log.error("ticket land failed: %s", result.danger_err)
        sys.exit(1)

    report = result.danger_ok
    _report_land_result(root, report)

    if cfg.ticket_land_push:
        _push_after_land(root, report)


# frob:ticket T-0631
# frob:waive ARCH103 reason="T-0977: push-after-successful-land helper -- runs `git \
# push`, logs the outcome, and decides whether a push failure should be fatal (see \
# docstring's dry-run/Err-path guard); the log+decide pair is the SAME single concern \
# (report the push result), not two"
def _push_after_land(root: Path, report) -> None:  # noqa: ANN001
    """`frob ticket land --push`: push `root`'s current branch to its
    upstream remote, but ONLY after a real (non-dry-run) land already
    fully succeeded -- `_land` calls this AFTER `land()` returned `Ok`,
    never on the `Err` exit path above, and never for `report.dry_run`
    (a dry run performs no durable commit to push, by design; pushing
    here would either push nothing new or push a stale prior state,
    neither of which honors "the push happens only after every land
    verification passed" for THIS run). Routed through
    `guarded_subprocess_run` (T-0778's exec guard, same as
    `_land_rebuild_natives_fn`'s `make core` spawn) so
    `FROB_DISABLE_EXEC=1` refuses this push too; a refusal or a non-zero
    `git push` exit is logged at ERROR and exits the process non-zero --
    the land itself already committed and closed the ticket by this
    point, so this failure is reported as a separate, later step rather
    than unwinding the land (there is nothing left to unwind: the
    landing commit already exists)."""
    if report.dry_run:
        _log.info(
            "ticket land --push: %s was a dry run -- nothing to push",
            report.ticket_id,
        )
        return

    from frob.gitio import current_branch

    branch = current_branch(root)
    if branch.is_err:
        _log.error(
            "ticket land --push: %s landed but could not determine "
            "root's current branch to push (%s)",
            report.ticket_id,
            branch.danger_err,
        )
        sys.exit(1)
    branch_name = branch.danger_ok

    from frob.app import ticket_runner as _ticket_runner

    guarded = _ticket_runner.guarded_subprocess_run(
        ["git", "-C", str(root), "push", "origin", branch_name],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if guarded.is_err:
        _log.error(
            "ticket land --push: %s landed (%s) but `git push` refused to "
            "spawn (%s) -- push it by hand: `git -C %s push origin %s`",
            report.ticket_id,
            report.commit_sha,
            ProcessGuardError.ExecDisabled,
            root,
            branch_name,
        )
        sys.exit(1)
    pushed = guarded.danger_ok
    if pushed.returncode != 0:
        _log.error(
            "ticket land --push: %s landed (%s) but `git push origin %s` "
            "exited %d -- stdout=%r stderr=%r -- push it by hand",
            report.ticket_id,
            report.commit_sha,
            branch_name,
            pushed.returncode,
            pushed.stdout[-2000:],
            pushed.stderr[-2000:],
        )
        sys.exit(1)
    _log.info(
        "ticket land --push: %s pushed %s to origin/%s",
        report.ticket_id,
        report.commit_sha,
        branch_name,
    )


# frob:ticket T-0323
def _require_merge_driver_args(cfg: AppConfig) -> None:
    """Exit 1 (with a logged reason) unless `frob ticket merge-driver`'s
    three positional temp-file paths (%O/%A/%B, git's merge-driver
    protocol) are all present."""
    if (
        cfg.ticket_merge_base is None
        or cfg.ticket_merge_ours is None
        or cfg.ticket_merge_theirs is None
    ):
        _log.error(
            "frob ticket merge-driver requires %%O %%A %%B (base/ours/theirs "
            "temp file paths -- git supplies these when invoked as the "
            "registered merge driver, see .gitattributes / docs/modules/"
            "tickets.md#git-merge-driver)"
        )
        sys.exit(1)


# frob:ticket T-0323
def _merge_driver(root: Path, cfg: AppConfig) -> None:
    """`frob ticket merge-driver %O %A %B`: git's merge-driver entry point
    for `tickets.md` (docs/modules/tickets.md#git-merge-driver). Reads the
    `ours` (%A) and `theirs` (%B) temp files git hands it, splices them via
    the SAME `splice_ledger` `frob ticket land` uses (never a duplicate
    reimplementation), and overwrites `ours` in place with the result --
    the merge-driver protocol's contract: `ours`'s final content on disk
    IS the merge result git commits, regardless of exit status. `base`
    (%O) is accepted (git always supplies it) but unused: `splice_ledger`
    resolves per-ticket-id divergence via state-rank/Done-report tiebreaks
    over `ours`/`theirs` alone, the same as `land`'s own splice call, not
    a 3-way base diff. Exits 0 (git treats the auto-splice as a clean,
    non-conflicted merge) unless `ours`/`theirs` fail to parse as a
    ticket ledger, in which case it exits 1 and leaves `ours` untouched --
    git then reports the usual conflict for a human to resolve by hand,
    exactly as if no driver were registered."""
    from frob.tickets import splice_ledger
    from frob.tickets._land import _archived_ids

    _require_merge_driver_args(cfg)
    assert cfg.ticket_merge_ours is not None  # narrows for the type checker
    assert cfg.ticket_merge_theirs is not None
    ours_path, theirs_path = cfg.ticket_merge_ours, cfg.ticket_merge_theirs

    ours_text = ours_path.read_text(encoding="utf-8")
    theirs_text = theirs_path.read_text(encoding="utf-8")

    spliced = splice_ledger(ours_text, theirs_text, archived_ids=_archived_ids(root))
    if spliced.is_err:
        _log.error(
            "ticket merge-driver: splice_ledger failed (%s) -- leaving %s "
            "untouched for a manual conflict resolution",
            spliced.danger_err,
            ours_path,
        )
        sys.exit(1)

    ours_path.write_text(spliced.danger_ok, encoding="utf-8")
    _log.info(
        "ticket merge-driver: spliced %s (ours) + %s (theirs) -> %s",
        ours_path,
        theirs_path,
        ours_path,
    )
