# frob.tickets -- landing: `frob ticket land`, evidence, liveness, cross-ticket safety

Part of the `frob.tickets` reference, split out of `docs/modules/tickets.md` by T-1780 so this subject's own lease no longer blocks every other ticket working a different one; see [`docs/modules/tickets.md`](tickets.md#split-files-t-1780) for the full split index.

## `frob ticket land`

<!-- frob:describes src/frob/tickets/_land.py::land -->
<!-- frob:describes src/frob/tickets/_land_ledger_merge.py::splice_ledger -->
<!-- frob:describes src/frob/tickets/_land_squash.py::_assert_land_complete -->
<!-- frob:describes src/frob/tickets/_land_squash.py::_worktree_full_changeset -->
<!-- frob:describes src/frob/tickets/_land_release.py::_apply_release_bump -->
<!-- frob:describes src/frob/tickets/_land_release.py::_maybe_rebuild_natives -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_apply_release_bump_for_land -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_write_release_bump -->
<!-- frob:describes src/frob/app/ticket_runner/__init__.py::_root_release_manifest -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_land_rebuild_natives_fn -->

The landing procedure used to be manual coordinator surgery repeated per
ticket: wip-commit in the worktree, merge main into it, a deletion-filter
check, squash-apply onto main, a ledger splice on conflict, close, a
conventional commit. `frob ticket land <id> --worktree <path> [--dry-run]`
(`frob.tickets.land`) does the whole chain atomically:

```python
# frob/tickets/_land.py
def land(root: Path, ticket_id: str, worktree: Path, *,
         dry_run: bool = False,
         collected: frozenset[str] | None = None,
         passed: frozenset[str] | None = None,
         covers_scope: bool | None = None,
         bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]] | None = None,
         rebuild_natives: Callable[[Path], bool] | None = None,
         sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]] | None = None,
         check_gate_claims: Callable[[Ticket], bool | None] | None = None) -> Result[LandReport, LandError]
    # T-1410: `check_gate_claims(ticket)`, when supplied, re-verifies every
    # acceptance criterion shaped "0 <RULE> findings under <glob>"
    # (frob.tickets._evidence._gate_claim_criteria) against the POST-MERGE
    # worktree tree and refuses the land (ClaimDivergence, reused rather
    # than adding a new LandError variant) when it returns False -- the
    # T-1276 defect this closes: a criterion phrased this way used to be
    # satisfiable by ANY bound evidence id, and T-1276 itself closed done
    # and landed (LAND-PROOF verified) against 116 live TEST005 findings
    # under its own criterion's glob, because nothing ever computed this.
    # Defaults to `None` (skip) for the same cycle-avoidance reason as
    # collected/passed/covers_scope; `frob ticket land` supplies it by
    # default (`ticket_runner._land_gate_claims_fn`, which reuses
    # `_close_gate_claims_for_ticket`'s exact computation against the
    # worktree).
    # T-0398 D-05: `collected`/`passed`/`covers_scope`, when supplied by a
    # caller with a fresh test-collection/run/graph-binding oracle computed
    # against the POST-MERGE worktree tree, re-verify the ticket's evidence
    # (resolution, pass, scope-binding) BEFORE finalize/close -- `land`
    # previously trusted whatever the worktree's pre-merge report claimed
    # and re-ran nothing. All three default to `None` (skip, unchanged
    # behavior) since computing them needs frob.testing/frob.graph access
    # frob.tickets deliberately does not have.
    # T-0338: `bump_version(root, ticket, final_id)` and `rebuild_natives
    # (root)`, when supplied, fold the REL001 version-bump/stamp and
    # native-rebuild-trigger coordinator steps into this same land -- both
    # invoked AFTER the squash-apply is staged (so their writes land in the
    # SAME commit) but BEFORE the T-0463 completeness assertion and final
    # commit. Both default to `None` (skip) for the same cycle-avoidance
    # reason as collected/passed/covers_scope; `frob ticket land` supplies
    # both by default.
    # T-1011: `sync_gate_rules(root, pre_land_tip)`, when supplied, runs
    # right after `bump_version` (same staged-but-uncommitted point) and
    # decides for itself, by diffing the landing diff, whether
    # `_KNOWN_GATE_RULES` changed; if so it auto-files any missing
    # `check-coverage.yaml` row (REG010) into the SAME land commit, ending
    # the manual `frob registry audit --sync-gate-rules` re-sync
    # docs/audits/coordination-churn.md disclosed drifting twice in one
    # drive. Defaults to `None` (skip) for the same cycle-avoidance reason;
    # `frob ticket land` supplies it by default
    # (`ticket_runner._land_sync_gate_rules_fn`).
    # T-1358: `_apply_release_bump` (called from inside `land` for the
    # `bump_version` step) now runs an UNCONDITIONAL final coherence check
    # (`_ensure_release_quartet_coherent`) comparing pyproject.toml's
    # on-disk version against `.frob-release.json`'s on-disk version,
    # regardless of what `bump_version` itself reported back -- closing a
    # gap the T-1078 resync left open: that resync only fires inside the
    # `bumped.danger_ok is not None` branch, so a callback that reports
    # `Ok(None)` (or a manifest write that silently failed) could still
    # leave the quartet desynced (the real T-1340 incident: pyproject.toml
    # bumped 0.289.0 -> 0.290.0 on main, `.frob-release.json` left at
    # 0.289.0, blocking every subsequent land on the T-0992 monotonicity
    # guard until a coordinator hand-reconciled). The new check force-
    # resyncs the manifest to pyproject.toml's value whenever the two
    # on-disk files disagree, as the very last step before `_apply_release_
    # bump` returns.
    # T-1771: the "release quartet" is `pyproject.toml`/`.frob-release.
    # json`/`uv.lock`/`CHANGELOG.md`. `_ensure_release_quartet_coherent`
    # verifies the FIRST THREE at land time (`uv.lock`'s own check,
    # `_ensure_uv_lock_coherent`, added by this ticket, runs whenever
    # `pyproject_version` is known at all -- NOT nested inside the
    # pyproject/manifest-disagree branch the way an earlier version of
    # this fix left it, which skipped the lock check entirely in the
    # common already-coherent case). `CHANGELOG.md`, the fourth member,
    # is deliberately checked elsewhere: REL001 (`frob.gates.
    # release_gate`) refuses with "no CHANGELOG.md entry for {version}"
    # at GATE time instead of land time, since a missing entry is
    # something an operator can see and fix (there is no single correct
    # PROSE to auto-write the way there is a correct version NUMBER for
    # the other three). This split is deliberate, not an oversight --
    # written down here so it does not go unnoticed the way the `uv.lock`
    # gap itself did.
def splice_ledger(ours_text: str, theirs_text: str, *,
                   base_text: str | None = None) -> Result[str, TicketError]
    # Merge two tickets.md texts at the TICKET-ID level (newest state per
    # id wins) instead of git's line-level textual merge. T-0398 D-09: the
    # winning side's evidence is UNIONED with the losing side's (never
    # dropped) on a same-id divergence.
    # T-1154: `base_text` (the true 3-way merge-base's ledger text, when
    # the caller has one) sharpens a same-id divergence: whichever side is
    # byte-identical to `base_text` made no deliberate edit and has no
    # claim on the id, so the side that DID change wins outright, before
    # ever falling back to the state-rank/richness tiebreak above. This is
    # the fix for the wrong-side-merge corruption class (3rd occurrence):
    # a worktree's untouched, merely-stale copy of a ticket main had since
    # content-edited (e.g. an evidence-path migration inside an already-
    # `done` block) used to tie on rank/richness and arbitrarily win.
    # `frob ticket land`'s own `tickets-archive.md` splice
    # (`_splice_and_stage_archive`) threads this through from the true
    # `git merge-base`; `None` (the default) degrades to the pre-T-1154
    # behavior unchanged.
```

Order of operations, and why it is this order:

0. **Resolve `root` from `worktree` itself when they resolve to the
   IDENTICAL path** (T-1003, docs/audits/coordination-churn.md#4): `root`
   defaults to the CLI invoker's cwd (`ticket_runner.py`'s `_land`), so
   running `frob ticket land <id> --worktree <path>` from a shell that
   never `cd`ed out of the worktree first makes `root` resolve to
   `worktree` for free -- the "chained cd" ritual every land used to
   require. `git -C <worktree> rev-parse --git-common-dir` (git's own,
   cwd-independent answer to "where is this clone's primary checkout")
   resolves the true `root` transparently whenever it differs from
   `worktree` -- a real linked worktree, the common case. When it comes
   back equal to `worktree` (no linked worktree exists at all --
   `--worktree` was pointed at the primary checkout itself), `root` is
   left unchanged and the T-0795 `_refuse_if_root_is_worktree` guard in
   step 1 still refuses exactly as before; this step never weakens that
   guard, only retires the manual-cd case it used to also (mis-)catch.
1. **Refuse on a dirty `root`** (`git status --porcelain` non-empty) --
   `Err(DirtyMain)`, remedy: `git -C <root> status`, commit or stash.
2. **Validate close preconditions in the worktree FIRST** (evidence
   non-empty, a substantive `## Done report` section, T-0398 D-03) --
   `Err(NotCloseable)` here means NOTHING has been merged or committed
   anywhere yet. This ordering is the whole point: closing is the step
   most likely to be forgotten, and it is checked before any irreversible
   git operation, not after the merge has already landed. This is a
   PRE-merge check against the worktree's own report; see step 5.5 below
   for the T-0398 D-05 POST-merge re-verification.
2.5. **Refuse on an out-of-scope, undeclared uncommitted `frob:waive`
   deletion** (T-1323): before ANY git mutation -- strictly before the
   wip-commit in step 3 that would otherwise fold a dirty worktree's
   edits into the merge unattributed -- `_check_uncommitted_waive_
   deletions` diffs the worktree's UNCOMMITTED state against `HEAD` for
   any deleted `frob:waive` comment line. A deletion whose file is
   neither covered by the ticket's `scope` nor named (file or rule) in
   its Done report refuses loudly (`Err(OutOfScopeWaiveDeletion)`,
   remedy: add the file to scope or name it/the rule in the Done report
   if intentional, `git checkout -- <file>` in the worktree if
   accidental). This is the 2026-07-29 incident's own laundering path: a
   wip-snapshot commit is not supposed to be a way to smuggle
   unattributed repo-wide edits onto main, and nothing before this check
   ever inspected what a wip-commit was about to capture. See
   docs/modules/gates.md's Tier-A section for the companion `WAIVE004`
   auto-fix guard this incident also produced.
2.6. **Tier-A auto-fix crash recovery** (T-1348). Before `land()` (the
   function documented by this numbered list) is ever called, `frob
   ticket land`'s CLI layer (`_absorb_pre_land_fixes`, T-1175) already ran
   `frob fmt`, `frob sys sync-interface`, and every Tier-A `--fix` handler
   (`apply_tier_a_fixes`, `src/frob/gates/_fix_engine.py`) directly against
   the worktree, on disk, with NO commit of any kind yet -- this step's
   own wip-commit (step 3 below) is the FIRST commit that captures any of
   it. A `frob ticket land` process killed during that window (a real
   incident, T-1338: a timeout mid-Tier-A left
   `src/frob/gates/_debt_deprecated.py` GARBLED, a half-applied rewrite,
   and the obvious `git checkout -- <file>` recovery then silently
   destroyed an unrelated uncommitted test in a DIFFERENT file) used to
   leave the tree in a state that was neither the pre-fix nor the
   post-fix original. T-1348 closes this two ways, entirely inside
   `apply_tier_a_fixes` and its handlers (`src/frob/gates/_fix_engine.py`)
   -- `_land.py`'s own step 3 wip-commit timing is UNCHANGED, since moving
   it earlier would require reordering `_absorb_pre_land_fixes` and
   `land()` at their call site (`src/frob/app/ticket_runner/_land_cmd.py`,
   a different ticket's scope):
   - Every Tier-A handler that rewrites a file in place now does so via
     `_write_text` (temp file + `fsync` + `os.replace` in the same
     directory, reusing `frob.tickets._store.atomic_write`'s existing
     T-0456 primitive) instead of a bare `path.write_text(...)`. A kill at
     ANY point up to and including the moment before the `os.replace`
     swap leaves the ORIGINAL file's bytes on disk, untouched -- there is
     no window in which the tracked path itself is half-written.
   - `apply_tier_a_fixes` writes `.frob/land-autofix-manifest.json`
     (`write_autofix_manifest`) after EVERY handler completes, not once at
     the end, listing every distinct file path any handler has rewritten
     SO FAR in the current run; it is cleared (`clear_autofix_manifest`)
     only once the whole pass finishes successfully. A process killed
     partway through the handler loop leaves this manifest naming exactly
     what Tier-A actually touched up to that point -- a recovering agent
     diffs `git status --porcelain` against the manifest's `rewritten_
     paths` list instead of a blanket `git checkout --` that cannot tell
     "Tier-A garbled this" from "my own uncommitted work is in this
     other file", the exact ambiguity that caused the T-1338 data loss.
3. **wip-commit** any uncommitted worktree changes (`wip: pre-land snapshot
   for <id>`) so nothing an agent forgot to commit is silently dropped by
   the merge that follows. T-1003: `worktree`'s own `uv.lock` frob-
   version-only flap (the same T-0793 shape step 1's `root`-side restore
   already tolerates -- a prior `uv run`/`uv lock` against a pyproject a
   sibling land already bumped, with nothing else in the tree touched) is
   auto-restored HERE first, before the dirty check -- otherwise the flap
   would get silently wip-committed as noise and squash-applied into the
   landing commit in step 9, needing the same manual `git checkout --
   uv.lock` ritual land already killed on the `root` side.
4. **Merge main into the worktree** (`git merge --no-commit --no-ff`,
   staged, not committed). Any conflict outside `tickets.md` aborts loudly
   (`Err(MergeConflict)`, remedy: resolve manually in the worktree, commit,
   retry). A `tickets.md` conflict is ALWAYS resolved via `splice_ledger`
   (see below), never git's line-level algorithm, then the merge is
   completed with a `merge <main> into worktree for landing <id>` commit.
5. **Deletion-filter check** (the stale-base guard): `git diff <main>
   --diff-filter=D --name-only` in the now-merged worktree -- every deleted
   path must match the ticket's `scope` globs, or land refuses loudly
   (`Err(UnownedDeletions)`, remedy: add the path(s) to scope if
   intentional, or `git checkout <main> -- <path>` in the worktree if
   accidental) and unwinds the merge (`git merge --abort`) first. This is
   what catches a worktree branched from a stale main base that ends up,
   relative to main's CURRENT tip, silently deleting a feature main already
   landed. T-0398 D-12: the deletion filter is STRICTER than an ordinary
   `scope_matches` check here -- a scope glob broad enough to be "the
   whole tree" or a bare top-level directory (`.`, `src/`) is never
   trusted to authorize a deletion (`_deletion_owned`), even though it
   would satisfy `scope_matches` for every other purpose; a more specific
   glob (`src/frob/tickets/`) is still trusted.
5.5. **Re-verify evidence against the POST-MERGE tree** (T-0398 D-05, only
   when the caller supplied `collected`/`passed`/`covers_scope`): reload
   the ticket from the worktree's now-merged ledger and re-check
   resolution/pass -- the ledger state about to be finalized may differ
   from what step 2 validated pre-merge (a splice can rewrite
   `ticket.evidence`). Runs BEFORE the `--dry-run` early return in step 6,
   so a clean dry run is still a real guarantee under D-05 too.
6. **`--dry-run` stops here**, unwinding the staged merge (`merge --abort`)
   -- everything above this point has ACTUALLY run (real merge, real
   splice, real deletion diff), so a clean dry run is a guarantee, not a
   guess. Nothing below this point (finalize/close/squash-apply/commit) is
   simulated, because nothing below it can fail for a reason the checks
   above didn't already catch.
7. **Finalize a draft id** (`finalize_draft`, T-0162's mechanism) if
   `ticket_id` is a `T-draft-*` id -- against the worktree's now-merged
   view, so the final id is allocated against current reality, not a stale
   pre-merge snapshot.
8. **Close** (`transition(..., DONE)`) in the worktree.
9. **Squash-apply onto `root`**: `git merge --squash --no-commit
   <worktree-branch>`. Any conflict outside `tickets.md` aborts loudly
   (`Err(SquashConflict)`, remedy: resolve manually, commit, retry) and
   resets `root` (`git reset --hard && git clean -fd`) back to exactly how
   it was found. `tickets.md` is again ALWAYS resolved via `splice_ledger`
   -- this is what makes the "main and the worktree each independently
   appended a new ticket near the same line" case a clean merge instead of
   a textual conflict requiring a human.
9.5. **Completeness assertion** (T-0463, BEFORE the commit in step 10): the
    worktree's finalized branch is diffed against `main` (`git diff
    --name-only <main>...HEAD` in the worktree) to get the COMPLETE
    changeset it introduces -- tracked edits, untracked new files, AND
    deletions all show up in this one call, because step 3's wip-commit
    already turned every untracked/deleted path into a tracked commit on
    the branch. This set is compared against what step 9 actually staged
    in `root` (`git diff --cached --name-only`); anything present in the
    worktree's changeset but missing from staging aborts the land loudly
    (`Err(IncompleteLand)`, the exact missing paths logged) and unwinds the
    squash (`git reset --hard && git clean -fd`) -- the commit in step 10
    never happens. This is the fix for the T-0448 incident: a manual
    coordinator land done via a raw `git diff HEAD` / patch-apply (NOT
    `frob ticket land`) only ever sees tracked deltas against the current
    commit, so it silently dropped an untracked `docs/modules/render.md`
    with no error at all. `frob ticket land`'s wip-commit + real `git
    merge --squash` design was already structurally immune to that
    specific failure mode; this step makes the immunity a checked
    invariant instead of an assumption, and is what actually catches any
    OTHER way a file could go missing (a git bug, a future refactor that
    reintroduces a diff-based step, etc.). The verified changeset is
    reported back as `LandReport.worktree_changeset`, and the actually
    landed paths as `LandReport.files_changed` -- on a real (non-dry-run)
    success the former is always a subset of the latter, by construction.
9.6. **REL001 version bump** (T-0338, only when `bump_version` was
    supplied, runs right after step 9's squash and BEFORE the step 9.5
    completeness assertion): `bump_version(root, ticket, final_id)`
    computes the semver class the just-squashed public API demands
    (`frob.release.diff_class`/`required_version` against the tracked
    `.frob-release.json` manifest), and if the declared `pyproject.toml`
    version does not already cover it, rewrites `version = "..."`,
    prepends a minimal `## [<version>] - unreleased` CHANGELOG.md entry
    naming the ticket, and `frob release stamp`s the new manifest --
    staging all three files so they land in the SAME commit as the
    squash-apply. `Ok(None)` (no manifest yet, or no bump needed) is a
    no-op; `Err(LandError.ReleaseBumpFailed)` unwinds the squash (`git
    reset --hard && git clean -fd`) exactly like any other land failure --
    a silently-skipped bump would let a landed API change slip past
    REL001 undetected. Reported back as `LandReport.release_bumped_to`.

    **T-0992 monotonicity assertion**: `_apply_release_bump` independently
    reads main's own pre-land `pyproject.toml` version via `git show
    <pre_land_tip>:pyproject.toml` (a git-object read, immune to whatever
    the squash-apply's working-tree mutation did to the on-disk file --
    `pyproject.toml` is not scope-protected, so a ticket's own worktree can
    carry it through the squash) BEFORE invoking `bump_version`, and
    hard-refuses (same unwind-and-`Err(ReleaseBumpFailed)` path) unless the
    callback's returned version is strictly greater than that captured
    baseline. This is a caller-independent backstop: twice in one day a
    `bump_version` implementation computed its "next version" from a
    stale, worktree-carried input and clobbered a higher version already
    on main (T-0976, T-0989) -- this assertion makes that class of bug a
    loud land failure instead of a silent regression, sibling to T-0959's
    archive-splice integrity check and T-0740's ledger integrity check.

    **T-1007 producer fix**: `ticket_runner._apply_release_bump_for_land`
    (the library's own `bump_version` callback, wired via
    `_land_bump_version_fn`) used to derive its bump BASELINE from
    `frob.release.load_manifest(root)` -- an on-disk read of `.frob-
    release.json` AFTER the squash-apply, exactly the working-tree
    mutation the T-0992 assertion above exists to be immune to. A stale,
    out-of-scope worktree copy of `.frob-release.json` riding the squash
    silently under-computed the required bump every time, tripping the
    T-0992 refusal on the FIRST land attempt and forcing a manual merge +
    reland round trip (the recurring churn item T-1007 was filed
    against). `_root_release_manifest` (T-1007) now reads `.frob-
    release.json` via `git show HEAD:.frob-release.json` -- root's own
    committed pre-land state, never the worktree-carried working-tree
    copy -- making the T-0992 guard a never-fires invariant for this
    callback instead of a per-land speed bump.

    **T-1078 quartet-atomicity backstop**: after a successful, monotonic
    bump, `_apply_release_bump` force-resyncs `.frob-release.json`'s
    `version` field to the callback's reported version via
    `frob.release.set_manifest_version` and stages it in this SAME step
    -- regardless of whether `bump_version`'s own implementation wrote
    (or correctly wrote) the manifest itself. This is the fix for the
    incident where a land's REL001 bump updated `pyproject.toml`/
    `CHANGELOG.md` but silently left the manifest on its old version:
    every subsequent land then re-derived an already-taken "next
    version" from the stale manifest and refused on the T-0992
    monotonicity guard, blocking three lands in a row until a
    coordinator hand-reconciled the manifest and ran `frob release
    sync`. The refusal diagnostic for that guard also now detects this
    exact desync independently (comparing `.frob-release.json`'s version
    against `pyproject.toml`'s version, both read at `pre_land_tip` via
    `_read_root_manifest_version`/`_read_root_pyproject_version`) and,
    when it is the actual cause of a monotonicity refusal, names the
    incoherent quartet explicitly and prescribes `frob release sync`
    instead of the bare "not strictly greater than main's pre-land
    version" message.

    **T-1760 recompute-not-carry fix**: none of `pyproject.toml`/
    `CHANGELOG.md`/`.frob-release.json` is protected by `ticket.scope`,
    so `git merge --squash` can resolve a change to any of them CLEANLY
    (no conflict object at all -- `_auto_resolve_out_of_scope_conflicts`
    only ever fires on a genuine git conflict) by taking the worktree's
    side, if the worktree's own copy differs from root's current HEAD in
    a way git's 3-way merge does not treat as contested. When that
    happens, root's working tree can already hold a REGRESSED version/
    manifest before `_apply_release_bump` ever runs -- and, critically,
    the T-0992 monotonicity guard above only ever validates a bump
    `bump_version` itself REPORTS (`bumped.danger_ok is not None`); a
    `bump_version` callback that legitimately reports `Ok(None)` (this
    land's own diff needs no new bump) left that regression completely
    uncontested, since `_ensure_release_quartet_coherent`'s own check
    only compares the two ALREADY-regressed files to EACH OTHER, which a
    self-consistent stale pair passes trivially. Measured on main across
    four consecutive lands (T-1692/T-1754/T-1755/T-1756): the version
    oscillated 0.366.0 -> 0.365.0 -> 0.366.0 -> 0.365.0, with the
    REL001 baseline manifest regressing right along with it -- silently,
    since the version string going backwards was the only visible
    symptom.

    `_reset_release_artifacts_to_pre_land` now runs UNCONDITIONALLY, as
    the very first step of `_apply_release_bump`, before `bump_version` is
    even invoked: `git checkout <pre_land_tip> -- pyproject.toml
    CHANGELOG.md .frob-release.json` discards whatever the squash carried
    for these three files and resets them to root's own true, last-
    committed state. This is RECOMPUTE, NOT CARRY -- the bump is a
    function of (root's manifest, the landing API) and is now always
    evaluated from root's own pre-land state, never from anything a
    worktree happened to bring along, closing the regression class at its
    source rather than only detecting it after the fact. `_assert_no_
    monotonicity_regression` runs as an unconditional final check
    afterward (even on the `Ok(None)` branch) as belt-and-braces defense
    in depth, comparing the working tree's final versions against
    `pre_bump_version`/`pre_manifest_version` via `_version_not_regressed`
    (the `>=` sibling of `_release_bump_is_monotonic`'s strict `>`, since
    "unchanged" is the CORRECT outcome on a no-bump-needed land) --
    refusing and unwinding the squash if it ever fires, which after the
    reset above should never happen in practice.
9.7. **Native rebuild trigger** (T-0338, only when `rebuild_natives` was
    supplied AND the landed changeset touches a native source tree --
    `frob-core/` or `strata-core/`): `rebuild_natives(root)` runs `make
    core` in `root`. Best-effort: a `False`/failed rebuild is logged as a
    warning (alongside the existing T-0248 stale-native warning, which
    still fires unconditionally) but never unwinds or blocks the land --
    a native rebuild is cheap to re-run by hand. Reported back as
    `LandReport.natives_rebuilt`.
9.75. **TICK005-backed regression sweep** (T-0631, immediately after step
    9's splice, BEFORE the completeness assertion): `land()`'s own
    `_tick005_land_regressions(root_pre_text, spliced_text, archived_ids)`
    (`_land.py`) compares `root`'s ledger text from just before this
    land's splice against the text just staged by it, and refuses
    (`Err(LandError.TerminalStateRegression)`, unwinding the squash via
    `_verified_reset_root` exactly like a `SquashConflict`) if any ticket
    that was terminal (DONE/DROPPED) pre-splice is neither terminal nor
    archived post-splice. This mirrors `frob check`'s `TICK005` gate
    (`_tick005_merge_state_regression`, T-0537's hand-resolved-conflict
    resurrection incident) but runs it directly around THIS land's own
    squash-splice instead of relying on a later `frob check` catching it
    on some unrelated future merge commit -- `_land_squash_apply`'s own
    squash-apply is always a single-parent commit, so the gate's `HEAD^2`
    precondition (a genuine two-parent merge) can never fire for a land
    at all, the exact gap this closes. The two implementations are
    deliberately NOT shared code: `frob.gates` depends on `frob.tickets`,
    never the reverse (docs/rework.md cycle-avoidance), so `_land.py`
    reimplements the same terminal-state-regression semantics against its
    own pre/post ledger texts rather than importing the gate.
9.8. **Stacked-sibling absorption check** (T-1001, docs/audits/coordination-
    churn.md#2, immediately before step 10's commit): when one worktree
    carries several tickets, the first land's squash-apply absorbs every
    sibling's files and ledger state -- each subsequent land then stages
    an EMPTY squash in step 9, and an unconditional `git commit` would
    exit 1 with no stderr, surfacing as an unexplained `CommitFailed`.
    `_land_squash_apply` checks whether anything is actually staged
    (`git diff --cached --name-only`) right before attempting the commit;
    if not, it VERIFIES (never assumes) genuine absorption -- `final_id`
    must already be `done` in `root`'s current ledger, AND every file in
    the ticket's own `scope` must already match content-for-content
    between the worktree's finalized HEAD and `root`'s current HEAD (a
    direct cross-checkout `git diff`, since a worktree shares its object
    store with its primary checkout). Both holding returns a clean
    success naming the ALREADY-EXISTING absorbing commit
    (`LandReport.commit_sha`, unchanged) with `LandReport.ledger_spliced
    =False` as the signal nothing new was committed this call (the
    frozen `LandReport` model has no dedicated field for this). Either
    check failing falls through to the ordinary step 10 commit attempt
    and its unmodified, honest `CommitFailed` error -- an empty stage for
    some OTHER, unexplained reason is never silently reported as success.
10. **Commit** with a conventional-commit message template
    (`<type>(tickets): land <final-id> <title>`, type derived from
    `ticket.kind`; `feature`->`feat`, `bug`/`security`/`ux`/`incident`->
    `fix`, `docs`->`docs`, `invariant`->`test`). ASCII only, no
    `Co-Authored-By` line, matching repo convention.
10.5. **Record `land_commit`** (T-2220, best-effort, immediately after step
    10's commit sha is known): `_record_land_commit`
    (`frob.tickets._land_squash`) loads `final_id` fresh from `root` (now
    holding step 10's committed content), sets its `land_commit` field to
    step 10's own sha, and commits THAT write as a small follow-up commit
    (`chore(tickets): record land commit for <final-id>`) under
    `FROB_LAND_INTERNAL=1` -- structurally the earliest point this can
    happen, since a commit cannot embed its own hash in its own tree (see
    `Ticket.land_commit`'s own docstring). A failure here (ticket not
    found post-squash, a write/add/commit git failure) is logged loudly
    and swallowed, never turned into a `LandError` -- step 10's land is
    already sealed on `root` by this point, and an already-sealed land is
    never failed over a missing convenience field. `root`'s tip after a
    successful `land()` call is therefore this record commit, one ahead
    of `LandReport.commit_sha` (step 10's own sha, unchanged) -- both are
    ancestors of `main` either way, so nothing downstream that already
    checks `LandReport.commit_sha` needs to change.
    `scripts/verify_lands.py` and `_find_landing_commit`
    (`frob.app.ticket_runner._lifecycle`) both resolve a ticket id to a
    commit by reading this field directly -- see
    `docs/guides/coordinator-scripts.md#load_land_commit` -- never by
    grepping a commit subject for the ticket id, which cannot match a
    `--plan` land (below) at all.
11. **`--push`** (T-0631, CLI-only, opt-in): once `frob ticket land`'s
    entire chain above has actually succeeded -- step 10's commit exists
    and every check before it passed, never on a `--dry-run` (nothing
    durable was committed to push) and never after a failed land (there is
    nothing new to push) -- `frob ticket land <id> --worktree <path>
    --push` runs `git -C <root> push origin <branch>` for `root`'s current
    branch (`ticket_runner._push_after_land`). A push failure (a refused
    spawn under `FROB_DISABLE_EXEC=1`, or a non-zero `git push` exit) logs
    the exact remedy (`git -C <root> push origin <branch>` by hand) and
    exits the process non-zero, but does NOT unwind the already-landed
    commit -- by this point the land itself is done and there is nothing
    left to undo, only a later, separate step (the push) that failed.

If close (step 8) fails or the final commit (step 10) fails, the merge
commit already landed in the WORKTREE's own branch history (never in
`root`/main) -- the log line names the exact undo (`git -C <worktree>
reset --hard HEAD~1`) alongside the retry instruction, so a failed landing
is always recoverable without touching main.

`splice_ledger` never trusts git's line-level merge for `tickets.md`:
it parses both ledger texts into id -> Ticket maps and unions them,
picking the "newer" version on a genuine same-id divergence -- state-machine
rank first (done/dropped > in-progress/blocked > planned > queued), then
presence of a substantive Done report, then the incoming side as the final
deterministic tiebreak. A ticket id present on only one side is always
kept. T-0398 D-09: whichever side wins the tiebreak has its evidence
UNIONED with the losing side's (deduplicated, winner's own ids first),
never dropped -- previously an evidence-count tiebreak picked ONE side's
evidence set wholesale, silently discarding the other side's ids when two
worktrees closed the same ticket with disjoint evidence.

## Frob ticket land --plan (T-1269)

<!-- frob:describes src/frob/tickets/_land.py::land_plan -->

`frob ticket land <id>` requires a closeable WORKED ticket (evidence +
Done report, `_validate_closeable`) -- a design-phase worktree that only
carries docs plus ledger changes (a planning pass that filed several draft
tickets but closed none of them) has no such ticket to land under. Before
T-1269, landing one of these required manual coordinator surgery: a
guarded plain `git merge` (`FROB_LAND_INTERNAL=1`) plus a hand-assigned
`frob ticket renumber <draft> <next-id>` call PER incoming draft --
observed costing 15 hand-assigned renumbers across 4 batches landing four
planner worktrees in one drive.

`frob ticket land --plan --worktree PATH [--dry-run]`
(`frob.tickets.land_plan`) does the whole chain atomically instead:

1. Refuse if `root`/`--worktree` are the same path, or `root` has any
   uncommitted change (the same two `land()` preflight checks, reused
   verbatim).
2. Merge `--worktree`'s branch onto `root`'s current branch (`git merge
   --no-ff` -- never a squash; there is no single worked ticket to squash
   under, unlike `land`'s own per-ticket path). Any `tickets.md` conflict
   splices via the registered git merge driver
   (`docs/modules/tickets.md#git-merge-driver`) the same way an ordinary
   `git merge`/`pull` already would -- `land_plan` performs no ledger
   surgery of its own. A real conflict `git merge --abort`s (nothing was
   committed yet) and refuses with `LandError.MergeConflict`.
3. Finalize EVERY draft id (`is_draft_id`) now present in `root`'s merged
   ledger to the next free real id, one `finalize_draft` call each
   (T-0162's existing allocator-locked next-id computation -- never a
   hand-assigned id). T-2220: for each `(draft_id, final_id)` pair, also
   stamp `final_id`'s own `land_commit` field to step 2's `merge_commit`
   sha -- already a real, prior commit by this point, so (unlike the
   per-ticket `land <id>` path's own step 10.5 above) this needs no
   separate follow-up commit at all; it is staged in-memory and rides
   into the SAME `chore(tickets): land --plan finalize ...` commit this
   step already makes. This is the field's PRIMARY motivating case
   (T-2220's own measured defect): this commit's subject carries no
   ticket id anywhere in it, so `merge_commit` recorded here is the ONLY
   way `scripts/verify_lands.py`/`_find_landing_commit` can ever resolve
   a `--plan`-finalized ticket by id -- a `git log --grep "land T-####"`
   structurally cannot match this subject. A `--plan` land with no
   incoming draft ids records nothing (nothing was finalized).
   Then commit the rewrite in one
   `chore(tickets): land --plan finalize ...` commit.
4. Optionally re-check the TICK gate via an injected `check_ticks()`
   callable (`frob ticket land --plan`'s CLI supplies `frob check --only
   tickets`, cycle-avoidance-consistent with `land`'s own `check_gates`/
   `covers_scope`/etc. -- `frob.tickets` cannot import `frob.gates`
   directly, docs/rework.md) -- a non-clean result refuses with
   `LandError.PlanTickGateDirty`.

On ANY failure after the merge (step 3's finalize, or step 4's TICK
re-check), `root` is `git reset --hard`ed back to its pre-merge tip -- no
half-merged ledger, no partially-renumbered draft survives. `dry_run=True`
runs the merge and finalize exactly as a real call would, then always
`git reset --hard`s back regardless of outcome, returning the
`LandPlanReport` of what WOULD have happened. The whole chain runs under
`root`'s `_land_lock` (T-0577, the same cross-process lock `land()` uses),
so a concurrent `land()`/`land_plan()` call against the SAME `root` blocks
at the lock acquire instead of racing this one.

## Mutation-evidence obligation (TEST016, T-0755)

<!-- frob:describes src/frob/tickets/_mutation_evidence.py::check_ticket_mutation_evidence -->
<!-- frob:describes src/frob/gates/_mutation_evidence.py::mutation_evidence_violations -->
<!-- frob:describes src/frob/tickets/_land.py::_check_mutation_evidence -->

Several real rejects (T-0611, T-0571, T-0682, T-0574, T-0710) shared one
root cause: the implementer's own recorded evidence tests PASSED before
the fix even existed, because they were written CONFIRMATORY ("assert the
thing I just built does the thing") instead of ADVERSARIAL ("prove a
mutant of this logic gets caught"). A confirmatory test that would pass on
both the pre-change and post-change code proves nothing about the change
it claims to cover.

`frob.tickets._mutation_evidence.check_ticket_mutation_evidence(root,
ticket, base_ref)` closes this with a bounded, diff-scoped mutation pass
that reuses `frob.mutate` (`generate_mutants`/`run_mutations`) as its ONLY
mutation engine -- there is no second one:

1. `_evidence_test_ids(ticket)` -- the subset of `ticket.evidence` shaped
   like a pytest node id (`path::name`); `cmd:` evidence and anything else
   is excluded (nothing `frob.mutate`'s `test_argv` can re-run).
2. `_touched_python_files(root, ticket, base_ref)` -- `.py` files the
   ticket's own `scope` covers that differ from `base_ref` in the working
   tree (`frob.gitio.working_diff`, the one diff seam every other caller
   in this repo already uses). Test files themselves (`test_*.py`,
   `*_test.py`, anything under a `tests/` path segment) are excluded --
   mutating a test file and re-running THAT SAME file as the kill oracle
   is a self-referential no-op; the boundary this check exists to
   interrogate is test-vs-logic, not test-vs-itself.
3. For up to 3 touched files (`_MAX_FILES`), mutate up to 8 points each
   (`_MAX_MUTANTS_PER_FILE`, `run_mutations`' new `max_mutants` cap, taken
   in source order so the run is deterministic) and re-run the ticket's
   own evidence test ids as the kill command, each mutant capped at 30s
   (`_TIMEOUT_S`). Mutation points are restricted to the file's OWN
   CHANGED LINES (`run_mutations`' `line_ranges`, fed from the diff's
   per-file hunk spans) -- a file-wide selection previously let an
   unrelated pre-existing line supply every mutant for a tiny diff,
   flagging evidence that had nothing to say about code the ticket never
   touched. A file where every mutant SURVIVED (0 killed, total > 0)
   becomes a `ConfirmatoryFinding` naming the file and the evidence ids
   that failed to distinguish it.

No test evidence recorded, no in-scope touched Python file, or a touched
file with zero mutable points within its changed lines (a docstring-only
change, an unmutable one-line diff) are all `Ok(())` -- "nothing to
check," not a finding. A refused mutant spawn
under the exec kill switch (`FROB_DISABLE_EXEC=1`, T-0803's own posture)
is `Err(MutationEvidenceError.ExecDisabled)`, never silently reported as a
clean pass.

**The sweep has a real wall-clock budget (T-1727).** Before this,
`_MAX_FILES * _MAX_MUTANTS_PER_FILE * _TIMEOUT_S` (up to 720s) was a
worst-case ceiling nobody actually enforced as a deadline -- a bound
evidence test that itself spawns real subprocesses (a watchdog test,
say) could push the true wall-clock well past a caller's own foreground
timeout, and the sweep had no way to stop early or say so: the
documented incident is ten consecutive 540s `frob ticket close` timeouts
(~90 minutes) that produced no result at all, with the agent's only
visible escape being to unbind its own slowest (and most adversarial)
tests. `check_ticket_mutation_evidence`'s `sweep_budget_s` (default:
`_sweep_budget_s()`, itself `FROB_MUTATION_SWEEP_BUDGET_S`-overridable,
90s out of the box) is a SINGLE deadline shared across the whole
sweep -- every file, every mutant -- computed once at the top of the
call and threaded down through `run_mutations`'
`deadline_monotonic`/`_run_mutants`'s per-mutant check. A file whose
mutants could not all be attempted before the deadline, or one never
even started because an earlier file already spent the whole budget, is
reported as `ConfirmatoryFinding(unmeasured=True, ...)` -- a DIFFERENT
outcome from a genuine confirmatory-only finding (`unmeasured=False`,
the pre-existing shape): nothing was proven weak, nothing was run long
enough to prove anything at all. `frob.gates._mutation_evidence
._test016_unmeasured_message` gives this its own wording so a human or
agent reading the finding never mistakes "could not measure" for
"measured and failing" (T-1703's exact lesson, same shape as a budget-
truncated `frob check` misread as clean). `_run_mutants` also logs one
INFO line per mutant attempted (`mutant N/M of <file>`), so a long sweep
is visibly progressing rather than indistinguishable from a hang --
requirement 3 of T-1727, directly answering "is this still working or
did it wedge?" the ten-timeout incident could never answer.
Deliberately NOT fixed by raising the timeout: the cost is
multiplicative in mutants x test time, so a bigger constant only
postpones the same wall -- the fix is an internal deadline that reports
an honest partial result, not a bigger one that still eventually runs
out with nothing to show.

**Bind-time cost projection (T-1727 requirement 2).**
`frob.tickets._evidence._warn_bind_time_mutation_sweep_cost`, called
from `add_evidence` right after a successful write, projects the SAME
close-time sweep cost the deadline above enforces -- one bounded timing
run of the ticket's full bound evidence-id set (capped at `_TIMEOUT_S`,
the same per-mutant budget the real sweep uses) times the planned mutant
count for the ticket's diff-touched files (a cheap, subprocess-free
`generate_mutants` count) -- and logs a WARNING naming the bound test
ids and the projected seconds when that projection exceeds the sweep
budget. This moves the discovery point from close time (an hour of work
later, when unbinding the slow-but-honest test is the only escape an
agent can see, T-1733's own incentive problem) to bind time (seconds
after `frob ticket evidence`, while rebinding/splitting/speeding up the
test is still cheap). Best-effort and advisory only: any failure (no
touched files yet, exec disabled, an unresolvable diff) degrades to a
silent no-warn, and it never affects the evidence write it runs after.

`frob.gates.mutation_evidence_violations(root, ticket, base_ref)` turns
any `ConfirmatoryFinding`s into `TEST016` `Violation`s: WARN severity by
default, promoted to ERROR for `security`/`bug`-kind tickets (the exact
kinds the root-cause incidents above came from). This is a plain per-
ticket `kind` check, not `frob.gates._ratchet`'s baseline-pool mechanism
-- no retroactive concern applies, because the obligation only ever runs
at THIS ticket's own close/land time, never re-scanning an already-closed
ticket's evidence, so landing this rule cannot turn a past close red.

**Wired into `frob ticket land`** (`_land.py::_check_mutation_evidence`,
called from `_land_precheck` right after `current_branch` resolves, before
any git mutation): as of T-1518, only a `security`-kind ticket runs the
mutation subprocess SYNCHRONOUSLY here and can still refuse the land on
an ERROR-severity TEST016 finding (`LandError.EvidenceConfirmatoryOnly`).
Every other kind's TEST016 obligation (including `bug`-kind, previously
also synchronous+blocking) is deferred: `_check_mutation_evidence`
enqueues a `frob.tickets._mutation_sweep_queue.SweepEntry` instead of
running the mutation subprocess inline, and does NOT block the land for
it -- see "Batch mutation-evidence sweep (TEST016, T-1518)" below.
BUG002 (`bug_repro_violations`) is unaffected by this change and stays
synchronous+ERROR-always for bug/security kind on every land, deferred
kind or not -- it is cheap (re-runs already-bound evidence against a
single prior commit, no mutation subprocess) and proves a different
property. `frob ticket land --skip-mutation-evidence` (AppConfig
`ticket_skip_mutation_evidence`, default off) is the documented escape
hatch for the still-synchronous `security`-kind path: the check still
runs and logs its findings at WARNING, it just cannot refuse the land.
Deliberately NOT part of `frob.check`'s `test_gate`/`_ALL_GATES` snapshot
pipeline (`frob.check` is out of this ticket's scope): every other TEST
rule is a pure function of the graph snapshot, safe to run on every `frob
check` invocation; this rule spawns real bounded subprocesses per ticket,
which would violate the "must not slow the default `frob check` path for
tickets that never opt in" guard if it ran unconditionally there.

### Batch mutation-evidence sweep (TEST016, T-1518)

<!-- frob:describes src/frob/tickets/_mutation_sweep_queue.py::enqueue_pending_sweep -->
<!-- frob:describes src/frob/tickets/_mutation_sweep_queue.py::run_pending_sweep -->

TEST016's mutation subprocess is the single most expensive, least
incremental land stage (2026-08-04 dev-cycle review) -- its marginal
per-ticket value is test-strength validation, not main-correctness, so
running it synchronously on every land does not pay for itself except for
`security`-kind tickets. `frob.tickets._mutation_sweep_queue` moves the
rest of that work off the per-land critical path onto a batch/nightly
cadence:

- **Enqueue.** `_check_mutation_evidence` calls `enqueue_pending_sweep(
  worktree, ticket.id, base_ref, ticket.kind)` for any kind outside
  `SYNC_BLOCKING_KINDS` (`{security}`) instead of running the mutation
  subprocess inline. This appends a `pending` `SweepEntry` to
  `.frob/mutation-sweep-queue.json`, guarded by the same `fcntl`-advisory-
  lock discipline `frob.tickets._land_queue` (T-1345) already established
  for `.frob/land-queue.json` -- a separate file, a separate lock, same
  pattern.
- **Batch run.** `run_pending_sweep(root)` processes every `pending`
  entry: re-runs `check_ticket_mutation_evidence` against `root`'s
  current tree and the entry's recorded `base_ref`, then marks the entry
  `swept`. Never mutates the original ticket's state and never blocks
  anything retroactively. A `bug`-kind entry (the one deferred kind that
  used to promote TEST016 to ERROR) whose batch run still finds
  confirmatory-only evidence files a NEW `bug`-kind ticket
  (`origin=agent`) naming the offending land, so the finding re-enters
  the normal doable-ticket queue instead of vanishing into a log line.
  Every other kind's confirmatory-only finding is logged at WARNING only,
  matching `mutation_evidence_violations`' own WARN severity for those
  kinds.
- **Cadence.** `frob ticket land --drain` (T-1444's merge-queue drainer)
  calls `run_pending_sweep` automatically after draining every queued
  land -- the natural batch boundary the ticket body names. A standalone
  `frob ticket land --run-mutation-sweep` CLI flag (AppConfig
  `ticket_land_run_mutation_sweep`) runs the same batch pass without
  `--drain`, for a deployment (e.g. a nightly cron) that never calls
  `--drain` at all.
- **Visibility.** `pending_sweep_count(root)` returns how many entries
  are currently `pending`, for a caller that wants queue depth without
  mutating anything.

**Also wired into `frob ticket close` (T-0844)**, the direct non-land
close path: `frob.app.ticket_runner._close` computes the same
`mutation_evidence_violations` check against the CURRENT checkout (there
is no separate worktree/base_ref split on this path, so it runs against
`root` as both the tree scanned and the diff base's own checkout -- see
`_close_mutation_evidence_for_ticket`) and passes the ERROR/no-ERROR
verdict to `transition(..., mutation_evidence=...)`, which
`_done_transition_guard` enforces the same way `_check_mutation_evidence`
does at land (`Err(TicketError.EvidenceConfirmatoryOnly)`). `frob ticket
close --skip-mutation-evidence` (AppConfig
`ticket_close_skip_mutation_evidence`, default off) is the close-path
twin of land's escape hatch: the check still runs and logs its findings,
it just cannot refuse the close. A security/bug-kind ticket can no longer
dodge this obligation by closing directly instead of landing.

**T-1438 fix: the diff/repro base is the merge-base with `main`, not
`current_branch(root)`.** The base ref this check diffs/repros against
used to be `current_branch(root)` -- in a dispatched worktree agent's
normal flow that resolves to the WORKTREE'S OWN branch, which by close
time already carries the ticket's own fix commit at its tip. BUG002's
`_bug_repro_outcome_at_ref` then ran `git worktree add --detach <scratch>
<that-branch>`, checking out the FIX itself rather than the pre-fix
parent, so the designated repro test trivially "passed at parent" for
every single bug-kind ticket closed this way -- forcing
`--skip-mutation-evidence` on every bug-kind close, not just genuine false
positives. `_close_mutation_evidence_for_ticket` now resolves
`frob.gitio._merge_base(root, base_ref)` (`base_ref` defaults to `"main"`,
threaded from `cfg.ticket_base_ref`) and diffs/repros against THAT commit
instead -- the ticket's true starting point, mirroring the same
merge-base computation `working_diff` already performs internally.
`frob ticket land`'s own precheck (`_land_precheck` /
`_resolve_main_branch_for_land`) does NOT share this defect: there,
`root` is the actual main checkout being landed INTO (not the worktree
being landed), so `current_branch(root)` correctly resolves to `main`
itself, not to the ticket's own branch.

### `--check-repro` cannot verify a squashed ticket's repro test after it lands (T-2025)

<!-- frob:describes src/frob/gates/_mutation_evidence.py::_BugReproOutcome -->

**This is a permanent, by-construction limitation, not a bug to be fixed
later.** `frob ticket evidence <id> --check-repro [NODE-ID] [--base-ref
REF]` (the on-demand read-only twin of `--designate-repro`'s validation,
T-1929) re-runs the designated test against `REF`'s checked-out tree and
classifies the result. This is a genuine, meaningful check WHILE a
ticket is still in-progress, inside its own worktree, before it lands --
`REF` (or the default merge-base against `main`) points at a real commit
that predates the ticket's own work, and the check runs the ticket's
new test against that pre-fix code.

**Once a ticket lands, this stops being true for any test the ticket
itself added or modified.** `frob ticket land` squashes every commit a
worktree accumulated (`ticket new`'s own scope/evidence/Done-report
commits, the actual code+test commits, everything) into ONE commit on
`main`. Confirmed directly (T-2019/T-2025): a landed ticket's own
worktree commits are provably NOT ancestors of `main` --
`git merge-base --is-ancestor <worktree-commit> main` returns false for
every one of them; only the single squash commit is. This means main's
history NEVER contains a commit where a landed ticket's own repro test
exists WITHOUT that ticket's fix already applied -- the test and the fix
are, by definition, in the exact same commit. Running `--check-repro`
against ANY ref in main's history for such a test -- including the
squash commit's own immediate parent, main's tip right before the land
-- cannot produce a real verdict: pytest exits 5 ("no tests collected"),
because the specific test method does not exist yet at that ref, and
`bug_repro_outcome_at_ref` reports this as `TEST_ABSENT_AT_PARENT`
(T-2025; a prior, less specific `NO_VERDICT` covered this same case
before T-2025 gave it its own outcome and an honest message pointing
back here instead of the generic "e.g. it calls a function that does
not exist there yet" wording, which read like a possibly-transient
failure rather than a permanent one).

**Measured, not theoretical**: T-2019 attempted exactly this --
re-verifying 9 already-landed BUG002 repro designations against main's
own history, post-land. All 9 returned `TEST_ABSENT_AT_PARENT`/
`NO_VERDICT`. Confirmed by directly inspecting the git blob at two of
the chosen parent refs (T-1546, T-1907): the designated test method is
textually absent from the test file at that commit, while the
surrounding test class is present -- exactly the squash-history shape,
not a per-ticket anomaly, and not fixable by choosing a different
`--base-ref` from main's own history, because no such ref exists.

**Two options were weighed and rejected in favor of documenting this
(T-2025's own decision):**

1. *Record the pre-squash test-only commit at land time* (e.g. tag it
   under a `refs/frob-repro/<id>` namespace so `--check-repro` has a
   real ref to check post-land) was rejected as not worth its cost:
   - It only works if the implementer split their work into a
     test-alone commit followed by a separate fix commit -- most
     tickets do not (the common case is one commit with both), so this
     would require a NEW, universally-enforced commit-discipline rule
     across every dispatched agent, plus a gate to catch a ticket that
     skipped it -- ceremony added to literally every land, for a
     capability (post-land re-verification) that is rarely exercised.
   - The recorded ref would need active retention (a real branch/tag,
     not a bare sha in ticket metadata) or it becomes unreachable and
     gets garbage-collected the moment the worktree is removed --
     permanent extra ref-namespace bookkeeping and repo object growth,
     forever, per bug/security-kind ticket.
   - It does not actually restore the property people rely on `frob
     ticket land` for: "one clean, atomic commit per ticket on `main`."
     The squash guarantee stays intact; this option only threads a
     side-channel around it, which is exactly the kind of fragile
     mechanism that LOOKS like it gives a verdict while depending on a
     discipline nobody can see failing until the day it does.
2. *Keep the generic `NO_VERDICT` wording* was rejected because it
   reads like a possibly-transient infrastructure failure (the existing
   message's own phrasing: "a native extension the parent commit's
   isolated checkout never built") when, for a post-land ticket, it is
   actually a PERMANENT, always-reproducible outcome -- worth a distinct
   name and an explicit explanation rather than lumping it in with a
   genuinely-retryable spawn/collection failure.

**What T-2025 actually shipped instead**: `TEST_ABSENT_AT_PARENT`, a
`_BugReproOutcome` member distinct from `NO_VERDICT`
(`src/frob/gates/_mutation_evidence.py`), fired specifically on pytest's
exit 5, with a message that names the structural cause and points here
-- refuse loudly and explain why, rather than emit a verdict-shaped
"no verdict" that reads as ambiguous or retryable. Every existing
caller (`bug_repro_violations`, `--designate-repro`'s synchronous
validation, `--check-repro`'s own refusal) already treats any non-
`FAILED_AT_PARENT` outcome identically for gating purposes (`is not
FAILED_AT_PARENT`/`is not PASSED_AT_PARENT` checks), so this is a
messaging refinement, not a new gating behavior -- no caller needed to
change to stay correct.

**What still works, and is the actual answer for a ticket that genuinely
needs a provable pre-fix repro**: commit the repro test ALONE first (a
real, separate commit, before the production fix), confirm it fails
against the still-unfixed code, THEN commit the fix, and pass the
test-only commit's own sha as `--designate-repro`'s `--base-ref` --
T-2021's own evidence used exactly this technique and produced a
genuine `FAILED_AT_PARENT` verdict. This works because the test-only
commit is a REAL commit reachable from the worktree's own branch history
at the moment `--designate-repro` runs (before land squashes anything);
it stops working the moment the ticket lands and the worktree is
removed, for the same reason described above.

### `BUG003`: the positive-direction must-still-pass control (T-2193)

<!-- frob:describes src/frob/gates/_mutation_evidence.py::must_still_pass_violations -->

BUG002 and TEST016 both only ever prove a NEGATIVE claim: a designated
repro test that genuinely failed before this ticket's fix (BUG002), or
diff-touched lines this ticket's bound evidence can mutation-kill
(TEST016). Neither says anything about whether a capability the fix
NARROWS -- resolution, matching, filtering, gating -- still accepts or
matches anything real after the change. A narrowing fix that
over-corrects until it accepts/matches NOTHING passes both checks
vacuously: there is no surviving false positive to find, and there is
no mutant to kill in code that never runs. Three measured instances in
one session (T-2193's own ticket body) all passed every existing gate
this way: T-2156's cross-file resolution accepted zero cross-file
candidates after its own primitive silently returned `None` for every
intra-repo import; T-2177's scope-plausibility check warned on an
unrelated file but none of the three real mis-scopings it targeted;
`frob cycle` found a planted cycle in a top-level layout and missed the
identical one in src-layout.

`frob:must-still-pass NODE-ID` (declared in `ticket.body`, the same
body-text-directive mechanism `frob:waive BUG002 reason="..."`/
`frob:no-behavior-change reason="..."` already use -- see
`_must_still_pass_controls`) is the explicit, author-named positive
control: `must_still_pass_violations` runs the SAME node id twice, once
against the ticket's own fix (`root`'s current tree) and once against
`base_ref` (the parent, via the same `_bug_repro_outcome_at_ref`
machinery BUG002 already uses). `BUG003`, always ERROR, fires in exactly
two shapes: the control FAILS at the fix (the capability broke -- the
incident this control exists to catch), or the control never PASSED at
the parent either (a misconfigured designation that was never
established as "working before" and so cannot prove the fix kept it
working). Every other combination -- both pass, or either side is
genuinely unresolvable (`NO_VERDICT`/`SAME_AS_HEAD`/
`TEST_ABSENT_AT_PARENT`) -- degrades to no violation, mirroring BUG002's
own posture: an unmeasurable comparison is never guessed at as either a
pass or a fail.

Deliberately opt-in and explicit, never inferred from the evidence set
or from the suite passing (per T-2193's own acceptance criteria): in
all three measured instances above, the FULL SUITE passed, because the
disabled capability had no test asserting it still functioned at all --
"more tests" or a coverage threshold cannot express this specific claim,
only a named designation can. Not restricted to `bug`/`security` kind
(unlike BUG002/TEST016): the narrowing-fix shape is not kind-specific,
and the directive itself is the opt-in gate.

**Not yet wired into any `frob ticket land`/`frob ticket close` call
site** -- T-2193's own declared scope is `src/frob/gates/
_mutation_evidence.py` alone (plus this doc and its own test file), the
same one-file-at-a-time discipline its sibling ticket T-2205 used for
`verify_imports`. Wiring `must_still_pass_violations` into
`frob.tickets._land`/`frob.app.ticket_runner`'s existing BUG002/TEST016
call sites is a follow-up ticket's job, not this one's.

## Live-tracker citation preflight (T-0854)

<!-- frob:describes src/frob/tickets/_live_tracker.py::live_tracker_citations -->

The T-0605-orphaned-41-rows incident class: closing/landing T-0605
instantly turned 41 `docs/design/registry/patterns.yaml` rows with
`disposition: "deferred:T-0605"` into main-wide REG003 errors, discovered
only on the NEXT `frob check`, one close too late. WAIVE006 already models
the identical hazard for `frob:waive ... ticket=<id>` bindings, but
neither check ran AT CLOSE/LAND TIME for the ticket about to disappear.

`frob.tickets._live_tracker.live_tracker_citations(root, ticket_id, *,
own_scope=())` is a plain `git grep` (not a full registry/graph parse --
the ticket's own PERF guard: "a targeted grep-shaped scan, not a full
registry parse per close") for every site that still cites `ticket_id` as
its live tracker: a registry `deferred:`/`tracked_by:` disposition
(`duplicate_of:` is excluded -- it never claimed the target still had open
work), or a waiver `ticket=`/`ticket "..."` attribute (both the
`frob:waive` comment grammar and the `.strata` `waive` clause grammar),
OR (T-1559) a waiver `follow_up=` attribute -- WIRE001/WIRE002's own
binding, the SAME "this ticket is still cited as live tracker" hazard
for a different waiver family. T-1559's own incident: T-1490/T-1488
landed and closed on 2026-08-05 while 16 `frob:waive WIRE001 ...
follow_up="T-1490"`-shaped directives still bound them; WIRE002 (only
enforced at `frob check` time, not at close/land) caught it one check
too late, turning main red with 16 orphan errors nobody was warned about
at close time -- the exact T-0605 shape this preflight already existed
to close for `ticket=`, now folded into the same scan/pattern rather
than a parallel mechanism. A
provisional draft id is always clear (WAIVE006/WAIVE007's own `T-draft-*`
exemption, same rationale: land's draft-finalize step rewrites every
draft-id reference to the final id in the same commit). `own_scope` (the
closing/landing ticket's own declared `scope`) excludes citations inside
files the ticket itself owns -- a self-citing waiver lands/closes in the
SAME commit as the citation, never orphaned; the T-0605 incident class is
specifically an unrelated file citing a ticket that closes out from under
it.

**Wired into `frob ticket land`** (`_land.py::_check_live_tracker_
citations`, called from `_land_precheck` right after the scope preflight,
before any git mutation): any citation refuses the land
(`LandError.LiveTrackerCited`), scanned against the worktree's own tree
(what is about to be merged). **Also wired into `frob ticket close`**
(the direct non-land path): `_done_transition_guard` runs the SAME check,
unconditionally (no injection needed -- unlike `covers_scope`/`reviewed`/
`mutation_evidence`, this needs no external context beyond `root` and the
ticket itself, so every caller gets it for free), refusing on
`TicketError.LiveTrackerCited`. Neither path has a skip flag: the ticket's
own plan does not call for one, and the remedy (file a successor ticket
and re-point the citing rows, or re-point them in this same change) is
always mechanical.

**Left-anchored patterns, and the ledger excluded from the waiver grep
(T-1633).** The waiver alternatives (`ticket=`/`ticket "..."`/
`follow_up=`) originally had a right-hand word boundary but no left-hand
one, so `ticket=T-0605` matched as a SUBSTRING of any longer identifier
ending that way -- `active_ticket=T-0605` in ordinary Done-report prose
read as a citation and refused a land twice (2026-08-06, T-1582) before
the id in question was even the citing pattern's actual target.
`_WAIVER_TICKET_PATTERN` is now left-anchored with an explicit
leading-character alternation, `(^|[^A-Za-z0-9_.-])`, rather than a
lookbehind -- the pattern is handed to `git grep -E` (POSIX ERE), which
has no lookbehind support at all. Separately, the waiver grep now
EXCLUDES `tickets.md`/`tickets-archive.md`/`tickets/**`
(`_WAIVER_PATHSPEC`) entirely: a real `frob:waive ... ticket=`/
`follow_up=` directive is a source-code comment and never legitimately
appears in the ledger, where every occurrence is narrative -- a Done
report quoting the very pattern that misfired, or an incident write-up
describing this class of bug (the ticket text you are reading right now
is exactly that shape, and an earlier revision of it WAS itself flagged
and refused the land describing the fix -- a self-demonstrating
instance of the underlying problem). The registry-disposition grep is
unaffected -- a registry YAML row is structured data, not narrative
prose, so no analogous exclusion applies there.

**The `frob:quote(...)` mention escape (T-1970).** The T-1633/T-1632
exclusions above are all POSITIONAL/STRUCTURAL narrowing (exempt the
ledger, require left-anchoring) -- they cannot help a genuine source
comment that legitimately DISCUSSES a citation rather than making one,
e.g. a discharge comment explaining `follow_up="T-1956"` was already
handled, or a reworded comment describing a removed `frob:waive
WIRE001` directive. Both refused real lands on pure English wording
before T-1970. `live_tracker_citations`'s `_scan` now drops any `git
grep` hit whose matched text falls entirely inside a `frob:quote(...)`
escape span (`_drop_escaped_mentions`, re-running the same pattern
against `frob.graph.dsl.mask_frob_mentions`-masked text) -- the SAME
escape `frob.graph.dsl`'s own directive parser honors
(docs/modules/graph.md#comment-dsl), so a discharge comment can quote
the directive text it is explaining without either scanner reading it
as live.

## Land hardening (T-0577)

Three gaps found in one real landing session, closed together:

- **Registry yaml reference rewrite at draft finalize.** `finalize_draft`'s
  rename primitive (`renumber_one`) rewrote `frob:` directive lines and the
  ledger, but a registry yaml's `disposition: "deferred:<ticket>"` /
  `"duplicate_of:<ticket>"` value (docs/design/registry/*.yaml's grammar,
  `frob.registry._models.parse_disposition`) is a ticket-id REFERENCE that
  lives in YAML data, not a source comment -- it was left pointing at the
  now-dead draft id, breaking REG003 until a human hand-swapped it (a real
  incident: T-0388's compliance.yaml). `_rewrite_registry_references`
  (`frob.tickets.__init__`) rewrites these too, independent of the
  `frob:` directive-line matcher, whenever `renumber_one` runs.
- **Sibling Done-report preservation on splice.** `_splice_only_ticket`
  (T-0479) deliberately takes every ticket id OTHER than the one being
  landed from main untouched, to prevent a worktree's stale, requeued
  sibling state from resurrecting on main (T-0475). That guard has a real
  cost in a multi-ticket worktree: landing one ticket first silently
  erased a SIBLING ticket's already-written Done report (in-progress,
  review-gated, awaiting its own `land`) whenever main's copy of that
  sibling was still a bare `queued`/`planned` block -- a real incident
  (landing T-0386 regressed T-0387/T-0388 to queued, Done reports gone).
  `_preserve_sibling_done_reports` closes this without reopening T-0479:
  for each sibling id, the worktree's copy wins ONLY when it carries a
  substantive Done report main's copy lacks -- a stale advanced state with
  NO Done report on either side (the T-0479/T-0475 case) is untouched,
  main's side still wins. **T-1721 replaced this Done-report-only special
  case with a general base-aware comparison** -- see "Sibling ledger
  edits, carried forward or refused (T-1721)" below; it did not generalize
  on its own, see that section for why.
- **Land-call serialization (`_land_lock`).** The entire `land()` body
  (precheck through the squash-commit) now runs under a dedicated,
  cross-process `flock` on `<root>/.frob/land.lock` -- a SEPARATE file from
  `frob.tickets._store.ledger_lock`'s `.frob/tickets.lock` (reusing that
  exact path was tried first: a worktree's own committed
  `.frob/tickets.lock`, picked up by `land`'s `git add -A` wip-commit/
  finalize-commit steps, collides by identical relative path with the
  untracked lock file `root`'s own lock would create, and git's
  squash-merge refuses outright rather than picking a side). A second
  `land()` against the SAME `root` blocks at the lock acquire instead of
  racing this one -- the fix for 6 REL001 version-number collisions from
  parallel branches in one session (two lands could previously both read
  the same pre-bump manifest version and each compute the same "next"
  version). `.frob/land.lock` is expected to be `.gitignore`d like every
  other `.frob/` path; `_porcelain_dirty` ignores anything under `.frob/`
  when deciding whether `root`/a worktree is "dirty" for exactly this
  reason.
- **Raw ticket-branch merges refused.** `frob.scaffold.
  install_worktree_lease_hook`'s `pre-merge-commit` hook (T-0431) now ALSO
  carries a second guard (`_FORBID_RAW_TICKET_MERGE_SCRIPT`): it refuses a
  real merge commit whose incoming side is a `worktree-agent-*` branch,
  from ANY shell -- including a coordinator's, which the T-0431 FROB_AGENT
  check deliberately exempts. Detects the incoming branch via
  `$GIT_REFLOG_ACTION` (git sets this to `merge <branch>` in every hook's
  environment; `.git/MERGE_HEAD` was tried first and observed, empirically,
  to no longer be readable by the time `pre-merge-commit` fires on a
  plain conflict-free merge under this git version/backend). `frob ticket
  land`'s OWN internal git calls never trip this hook in the first place --
  both its worktree-into-main merge (`--no-commit` then a later plain
  `git commit`) and its squash-apply (`git merge --squash`) suppress the
  automatic merge commit `pre-merge-commit` fires for; `FROB_LAND_INTERNAL=1`
  is offered anyway as an explicit, documented manual override, never set
  by `land` itself since it never needs it.

## Sibling ledger edits, carried forward or refused (T-1721)

The T-0577 Done-report preservation above closed ONE shape of the
T-0479-scoping cost (a sibling's Done report silently erased); a
different shape of the SAME cost went unnoticed for a full session
afterward: `_splice_only_ticket`'s blanket "every sibling id comes from
main untouched" default also silently discards a worktree's genuine
EDIT to a sibling ticket's OWN section whenever that edit does not
happen to change Done-report presence -- an evidence-list rebind (e.g.
`frob ticket evidence <other-id> --replace OLD NEW`, made in the same
worktree while landing a DIFFERENT ticket) is invisible to
`_preserve_sibling_done_reports`'s narrower check.

**Field incident.** T-1637 (a DONE, unrelated ticket) needed its
evidence rebound after T-1679 renamed the tests it cited. The rebind was
made correctly, in the same worktree, and verified locally -- and then
silently vanished, THREE separate times in a row, regardless of which
ticket's land was carrying it (T-1679's own land, a dedicated follow-up
ticket T-1714 filed specifically to re-fix it, and T-1706 after that) --
because `_splice_only_ticket` never even considered T-1637's section for
anything but a wholesale main-wins overwrite. The pattern was diagnosed
as structural only after the third silent loss.

**Why T-1154's fix did not cover this.** T-1154 already threaded a true
merge-base 3-way comparison into the TICKETS-ARCHIVE.MD splice for
exactly this class of problem -- but that fix's own docstring explicitly
reasoned tickets.md's OWN scoped splice "does not need this" because
"`ticket_id`-scoping (T-0479) already makes every sibling id come from
`main_text` untouched". That is a true description of T-0479's
mechanism and a wrong justification: the untouched-by-default behavior
IS the bug, not a reason base-awareness is unnecessary. T-0577's own fix
generalized only as far as the ONE incident shape it was built to close
(Done-report presence), not to arbitrary sibling content changes.

**Fix.** `_carry_forward_or_refuse_sibling_edits`
(`frob.tickets._land_ledger_merge`) replaces the narrow Done-report-only
check with a full base-aware 3-way comparison, when a `base_text`
snapshot (the true merge-base's `tickets.md`, resolved via the same
`_true_merge_base` + `_read_text_at_ref` pattern T-1154 already
established for the archive file) is available -- now threaded into
BOTH `_splice_and_stage` call sites: the pre-squash `_merge_main_into_
worktree` stage and the FINAL `_squash_and_splice_ledger` stage that
actually lands on main. For each sibling id, comparing main's current
copy, the worktree's copy, and the common base's copy:

- worktree unchanged since base: main's copy stands (the ordinary,
  already-correct T-0479 case).
- worktree changed, main unchanged since base: the worktree made a real,
  isolated edit main never touched -- carried forward. This is the
  T-1637 shape.
- both sides changed but converged to the same content: nothing to do.
- both sides changed to DIFFERENT content: neither side is stale -- both
  made a real, independent edit since the same base. This is the case
  the OLD `_newer` richness heuristic (T-0682/T-0764: state-rank, then
  Done-report/evidence/acceptance richness, never raw content) could not
  actually answer -- a same-rank, same-richness divergence fell through
  to an arbitrary positional tiebreak that silently discarded whichever
  side lost. Per the explicit design constraint driving this fix:
  silently choosing is the bug, not WHICH side gets chosen. Refused
  instead (`Err(TicketError.SiblingLedgerEditConflict)` /
  `LandError.SiblingLedgerEditConflict` at the land layer), naming the
  conflicting id, so an operator resolves the real conflict by hand (or
  lands the sibling ticket on its own first) instead of a land quietly
  deciding it for them.

`base_text=None` (git could not resolve the true merge-base, or its
ledger text failed to parse) degrades to the pre-T-1721
`_preserve_sibling_done_reports` heuristic exactly as before -- never a
hard failure just because the sharper comparison was unavailable this
once.

## Land exclusivity lease (T-1619)

`_land_lock`'s `flock` (T-0577, "Land hardening" above) only ever
serialized `land()` against ANOTHER `land()` call -- it said nothing to
any OTHER ledger-writing verb. Real incident, 2026-08-05: `frob ticket new`
auto-commits the ledger (T-1130); running it while a land was staging
moved `root`'s tip mid-run, and `_verified_reset_root`'s drift guard
(T-0907) correctly refused to unwind rather than risk destroying the
concurrent commit -- but that left the land's staged REL001 bump (four
files) dangling with no disclosure of what, specifically, was left
behind. It happened three times in one session to an operator actively
trying to avoid it.

Two fixes, both scoped to this repo's actual ledger-commit choke point
(`frob.tickets._leases._add_and_commit_tickets_md` -- the single function
`commit_ticket_ledger_change`/`commit_start_transition` both funnel
through, so `new`/`close`/`drop`/`fail`/`requeue`/`block`/`start`/
`evidence`/`done-report` are all covered by one guard, not nine separate
ones):

- **`refuse_if_land_in_progress(root)`** (`frob.tickets._leases`) probes
  `root`'s `LAND_LOCK_REL` (`.frob/land.lock`, the SAME file `_land_lock`
  holds -- the path constant now lives in `_leases`, and
  `frob.tickets._land` imports it, so both sides of the check share one
  literal, never two independently-defined copies that could drift) with
  a non-blocking `flock` acquire-then-release attempt. Failing to acquire
  means a land is genuinely alive holding it right now; succeeding (or
  finding no lock file at all) means it is safe to proceed.
  `_add_and_commit_tickets_md` calls this before ever running `git add`,
  so a refusal touches nothing -- the caller's own working-tree write (a
  freshly filed ticket, a `--evidence` addition) stays uncommitted for a
  later retry, but no commit races the land's.

  Crash-safety comes from the primitive itself, not a second liveness
  layer: POSIX `flock` is released by the kernel the instant its holding
  process exits, by any means including `SIGKILL` -- there is no "dead
  holder, lock still held" state to probe for, unlike a plain on-disk
  lease file (`_probe_worktree_liveness`'s confirmed_absent/ambiguous
  split exists precisely because a directory does not vanish just because
  its creating process died; a kernel-held advisory lock has no such
  gap). A killed land's lock is free for the very next probe, no TTL, no
  polling, no timeout to tune.

  `land()` itself writes the lock's holder metadata with `ticket_id` now
  included (`_land_lock_holder_metadata`), so a refused caller's log line
  names the actual landing ticket ("a land is in progress for T-1619 ...")
  rather than a bare pid.

- **Refusal message on the drift-guard's leftover state.** T-0907's
  `_verified_reset_root` drift refusal (the exact path the incident above
  hit) now runs `git status --porcelain` before logging and lists every
  path it is leaving staged/uncommitted, instead of only pointing at
  "inspect by hand". With the exclusivity lease above closing the actual
  race, this refusal should no longer be reachable via a concurrent
  ledger write -- it remains as defense for any OTHER process that
  mutates `root` while holding no lock at all (manual coordinator
  surgery outside `frob ticket` entirely, which no lease can see).

**Belt-and-braces process scan.** The repo owner's own coordinator-side
shell wrapper additionally refused a ledger write whenever a `frob ticket
land` PROCESS was alive against `root`, even before it had acquired
`land.lock` -- folded into `frob` itself rather than staying a wrapper only
one operator ran (agents and CI bypassed it entirely). `refuse_if_land_
in_progress` now also calls `_scan_for_live_land_process(root)`
(`/proc`-based, Linux-only, degrading to a silent no-op finding on any
other platform or scan failure) after the flock probe finds no held lock:
it looks for a process whose argv contains the literal tokens `"ticket"`
and `"land"` and whose `/proc/<pid>/cwd` resolves to `root` -- the exact
shape a real `frob ticket land <id> --worktree <path>` invocation produces,
run from the primary checkout's own directory per playbook convention.
This closes the narrow window between a land process starting and its
first `_land_lock` acquisition, and the fallback path for a platform where
`fcntl` degrades to a no-op (the flock check never engages there at all).
A finding refuses exactly like a held flock does, naming the ticket id
parsed from the process's own argv (a `T-####`-shaped token) when one
was found.

**Land-wait budget config and start-relative scaling (T-2023).**
<!-- frob:describes src/frob/tickets/_leases.py::_load_land_wait_timeout_s -->
<!-- frob:describes src/frob/tickets/_leases.py::_land_lock_started_at -->
<!-- frob:describes src/frob/tickets/_leases.py::_resolve_land_wait_budget -->
A caller waiting on this lease (rather than refusing outright) no longer
waits a fixed span measured from its OWN arrival. `_resolve_land_wait_
budget` instead resolves the wait against the in-flight land's own
recorded start time (`_land_lock_started_at`, read off the lock's holder
metadata `land()` already writes): the remaining budget is `resolved_
timeout - (now - started_at)`, floored at zero, so a caller that shows up
partway through a long land waits only for what is actually left, not a
fresh full timeout stacked on top of time the land had already spent.
The base timeout itself is configurable per repo via `frob.toml`'s
`[tickets] land_wait_timeout_s` (`_load_land_wait_timeout_s`, default
`330` seconds when unset or when the config value is not a positive
int) -- a repo whose real land time regularly exceeds the built-in
default no longer has to patch source to raise it.

## Root checkout write guard (T-1779)

T-1619 (above) closed the ledger-COMMIT race between `land()` and every
OTHER ledger-writing verb -- but `refuse_if_land_in_progress` only ran
inside `_add_and_commit_tickets_md`, the commit-time choke point. A
mutating verb's HANDLER runs first and already writes its change to the
working tree (`write_ticket` is a plain filesystem write with no guard of
its own) before that commit-time check ever gets a chance to refuse
anything; `renumber`/`promote` write across many tracked files with no
commit step at all (T-1615 deliberately excludes them from the uniform
auto-commit, since each owns its own multi-file transaction), so the
commit-time check never even ran for them. A real 2026-08-06/07 session
hit five shapes of this same underlying gap -- root itself, not any
agent's worktree, has no guard against a coordinator's own git commands
racing a land -- one of which corrupted a closed ticket's state (T-1678
read `done` on main with its code absent, because `frob ticket close` ran
for it between a land's pre-land snapshot and its staging step).

**Gap 1 -- every mutating verb, not just the closeout family, and BEFORE
the write, not merely before the commit.**
`frob.app.ticket_runner._refuse_if_land_in_progress_for_dispatch` runs
BEFORE `handler(root, cfg)`, wrapping the single dispatch call site in
`run()` (the same T-1615 "one choke point, no per-verb code" shape
`_auto_commit_ledger_after_dispatch` already established) -- so this
closes for every verb added to `_ticket_dispatch_table()` in the future
too, with nothing new to remember per verb.

**Incident 6 (observed live, after the first five, T-1779 follow-up)**
sharpened WHERE this refusal has to run: the pre-T-1779 guard lived only
in `_add_and_commit_tickets_md`, so `frob ticket runs-last <id> on`'s
handler ran to completion -- writing `runs_last=True` to the ticket file
-- and only the SUBSEQUENT auto-commit refused with `LandInProgress`. A
"successful write, refused commit" is a PARTIAL write, not a clean
refusal, and is the same corruption class T-1678 already paid for
(incident 5). Refusing before `handler()` runs at all, not merely before
its commit, is what actually closes this -- `test_refused_verb_never_
writes_the_ticket_file_at_all` (`tests/test_ticket_leases.py::
TestDispatchLandGuard`) asserts the ticket's on-disk field is UNCHANGED
after a refused attempt, not merely uncommitted.

Incident 6's OTHER half is a different bug entirely, already ticketed:
`frob ticket new` itself left `tickets/T-1780/` on disk, UNTRACKED, with
no commit step of its own -- `new_ticket` (and `write_ticket`/other
`frob.tickets` mutators called directly) is a pure library call with no
auto-commit; T-1615's uniform auto-commit wraps the CLI DISPATCH layer,
not the library call underneath it. That untracked directory later
DirtyMain-refused an unrelated agent's land. This is T-1758's scope
(`src/frob/tickets/_new_renumber.py`/`_leases.py`/`_store.py`), not
T-1779's -- the two are two halves of one fix (this ticket stops a
verb's WRITE from racing a land already in progress; T-1758 stops a
verb's write from becoming root dirt that blocks a LATER land), and
leaving either one unlanded leaves the other's protection incomplete.

Two explicit sets decide who is exempt from the T-1779 pre-dispatch
guard:

- `_LAND_SAFE_READ_ONLY_VERBS` (`list`/`show`/`doable`/`board`/`epic`/
  `brief`/`flow`) -- verbs that never write anything, so a coordinator
  can still inspect state while a land runs. Deliberately a SHORT
  allowlist rather than an exclusion set: the default posture for any
  verb not proven read-only here is GUARDED, so a future mutating verb
  that forgets to add itself to an exclusion list still runs safely by
  default (it is merely less convenient during a land, never unsafe).
- `_LAND_LOCK_EXEMPT_VERBS` (`land`/`merge-driver`/`sweep-async`) --
  exempt for a reason OTHER than being read-only: `land` is the process
  HOLDING the lock (`_land_lock` already refuses a second concurrent
  land at the OS `flock` level, so gating it here too would be
  redundant, not unsafe, but the exclusion is kept explicit);
  `merge-driver` is invoked BY git as a subprocess of a land that is
  ALREADY holding the lock, and a fresh `open()` in that child process
  would not observe itself as the same holder, so gating it here would
  make a land deadlock against its own merge callback; `sweep-async`
  (T-1699) deliberately races the lock on its own terms.

**Gap 2 -- refuse to START a land on top of someone else's staged
content.** Already closed, not new code: `_land_precheck` (the first
thing `_land_locked` runs, before ANY of land's own staging) already
calls `_refuse_if_main_dirty`, and `describe_root_dirt`'s T-1740 staged-
path callout already names exactly this shape ("N STAGED (likely a
prior land's leftover index, T-1740)"). Verified directly against
incident 3 above: a staged `git rm -r agents skills` left in root DID
refuse the next land with `DirtyMain`, naming the staged paths -- the
guard worked as designed; the incident's cost was the wasted diagnosis
time from three agents who could not see root, not a guard failure. No
new refusal was added for this gap.

**Gap 3 -- a safe path easier to reach than raw `git worktree remove`.**
`git worktree remove` itself cannot be guarded (it is not this repo's
code), so the fix is a safe ALTERNATIVE that is easier to reach than the
raw command, not a wrapper around it. `frob.tickets._leases.
remove_worktree(root, path, *, dry_run=False, force=False)` (T-1779) is
the single-worktree twin of `sweep_worktrees` (T-0836/T-1739): it reuses
`_sweep_verdict_for_worktree` directly for exactly ONE candidate, so the
same liveness-first-and-unconditional gate (`kept:live` if a process is
cwd'd into the worktree), the same clean/lease/age gates, and the same
`force` escape hatch apply unchanged -- one candidate through
`sweep_worktrees`'s own per-candidate loop body, not a re-derived
mechanism. `Err(NotARegisteredWorktree)` if the target path is not one
of `root`'s own git-registered `.claude/worktrees/` agent worktrees, the
same restriction the bulk sweep already enforces.

`frob worktree remove PATH [--dry-run] [--force]` (`frob.app.
worktree_runner`) is the CLI surface -- same subcommand family as `frob
worktree sweep`, one new `argparse` subparser, no new dispatch mechanism.

**Gap 4 -- land-lock visibility without `pgrep` (partial).** The only
way to check "is a land running against root right now" today is
`.frob/land.lock`'s existence plus whether its `flock` is currently
held -- `ls -la .frob/land.lock` shows the file exists (the repo has
landed at least once) but not whether it is CURRENTLY held; a reliable
answer needs a non-blocking `flock` probe, which
`frob.tickets._leases.refuse_if_land_in_progress` already performs and
which any of the guarded verbs above will now report if attempted. A
dedicated `frob doctor`-style one-line surface for this (so a
coordinator can check before touching root without a probe command that
also has other side effects) is not built in this pass -- filed as a
natural, small follow-up rather than half-built here.

## Shared land-path liveness authority: `is_effectively_in_progress` (T-1999)

<!-- frob:describes src/frob/tickets/_leases.py::is_effectively_in_progress -->

Every land-path guard T-1639 narrowed to gate on `IN_PROGRESS` must call
`is_effectively_in_progress(root, ticket_id, ledger_state)` instead of
trusting `root`'s own ledger `state` field directly.

**Root cause this closes:** `frob ticket start` records a ticket's
cross-worktree LEASE (`record_lease`, this module) and flips its LOCAL
ledger to `IN_PROGRESS` in the same operation -- but the worktree that
did this and `root`'s own checkout of `tickets.md` are two different
files. `root` only observes the `IN_PROGRESS` transition once something
merges/lands that worktree's ledger back in. In the window between "a
worktree took the lease" and "main observed the state transition", a
guard that reads only `root`'s ledger sees `state: planned`/`queued`
for a ticket that is, in fact, actively held (T-1977's land of
`f3257572a` carried a change into T-1665's live scope while T-1665's
lease was held and main's copy still read `planned` -- T-1999's own
measured repro).

A ticket counts as effectively in progress if EITHER:

- a live lease for `ticket_id` exists (`read_all_leases`, which already
  prunes dead-worktree leases via `_live_leases_pruning_stale` -- the
  real-time, cross-worktree-visible signal `record_lease`/
  `release_lease` maintain), OR
- `ledger_state` itself already reads `IN_PROGRESS` (the fallback for
  the ordinary case where a lease was never taken by a different
  worktree, or has since been released but the ledger write has not
  landed either way).

This is a strict widening of "state says IN_PROGRESS" to "state says
IN_PROGRESS OR a live lease says so" -- it can only make a
dormant-looking ticket refuse more correctly; it can never make a
genuinely dormant ticket (no lease, state not IN_PROGRESS) refuse, so
T-1639's queued/planned-does-not-block outcome is unchanged for the
case that has neither signal.

## Orphaned-lease detection and release (T-1779 finding 7)

A seventh incident, found live during T-1779 itself: T-1766's lease
(`.git/frob-leases/T-1766.json`) named a NESTED worktree (a `t-1766`
worktree created UNDER another agent's own `.claude/worktrees/` entry)
whose PARENT worktree had already been retired and removed, taking the
nested one -- and its lease's target path -- with it. `frob ticket
doable` correctly refused to offer T-1766 forever, held by a ghost, and
nothing in the system ever reported why: the lease file survived,
because nothing ties a lease's lifetime to the existence of the path it
names.

**Why `read_all_leases` itself could not have caught this.** Its own
liveness filter (`_live_leases_pruning_stale`) exists to decide whether
it is SAFE to opportunistically unlink a stale lease, and is tuned
conservatively for that destructive operation: `_probe_worktree_
liveness` classifies a worktree path as `"present"`, `"confirmed_
absent"` (only a `FileNotFoundError` AND a still-reachable PARENT
directory -- the parent-reachability check exists so a mount failure can
never be misread as "just this one worktree is gone"), or `"ambiguous"`
(any other `OSError`, treated conservatively as "cannot confirm"). A
`"confirmed_absent"` lease is unlinked and never appears in `read_all_
leases`'s return value at all; an `"ambiguous"` one is SILENTLY DROPPED
from every consumer's view (`doable` included) and never unlinked
either. T-1766's shape -- the PARENT worktree also gone -- reads as
`"ambiguous"`, so it was invisible everywhere `read_all_leases` feeds
(the CLI, `doable`, `frob worktree sweep`) while persisting on disk
forever. That is a gate lying by omission, not a corner case.

**`frob.tickets._leases.orphaned_leases(root) -> tuple[_LeaseRecord,
...]`** answers a cheaper, different question, built on the RAW parse
(`_parse_lease_files_cached`) rather than `read_all_leases`, so it never
inherits the ambiguous-drop blind spot above: for every currently
recorded lease, does `Path(lease.worktree).exists()`. No process scan,
no three-way ambiguity split -- a REPORT (never a destructive unlink)
can afford to treat "cannot confirm" the same as "looks gone" and let a
human decide.

**`frob.tickets._leases.release_orphaned_lease(root, ticket_id)`**
(`frob worktree release-lease TICKET-ID`) is the targeted, SAFE release
verb this incident needed and did not have: it releases exactly ONE
ticket's lease, and ONLY after confirming (via the same raw-parse
lookup) that the lease's recorded worktree path is genuinely gone --
`Err(NoLeaseForTicket)` if there is no lease at all, `Err(
LeaseWorktreeMismatch)` if the lease is not actually orphaned (its
worktree still exists -- use `frob worktree remove`/the ordinary
ticket-close path instead). This is the fix for the actual recovery
T-1766 forced: the coordinator ran `rm .git/frob-leases/T-1766.json` by
hand with five live agents running, because no scoped verb existed to
release ONE stale lease without a fleet-wide `frob worktree sweep`
(unsafe with several live agents mid-ticket). Every incident across
T-1779's full finding set ends the same way -- a coordinator doing raw
filesystem or git work because no scoped verb existed for the specific
narrow thing that needed doing -- and this is that pattern's most direct
instance yet.

**Deliberately not built in this pass**, filed separately per this
finding's own instruction to keep the fix small: (1) wiring `orphaned_
leases` into a `frob check`/`frob doctor` GATE finding (this pass adds
the detection primitive and a CLI report path, not a new gate rule --
gate wiring lives in `src/frob/gates/**`, outside this fix's scope); (2)
refusing (or warning on) creating a NESTED worktree at the SOURCE
(`frob ticket work`) -- T-1766's own worktree was nested under another
worktree, which is why it died when its parent was retired; this is the
root cause the orphan is a downstream symptom of, filed as its own
ticket since it may be larger than a small guard.

## Verify-then-destroy: `frob ticket land --retire-on-proof` (T-1619)

Real incident, same session as the lease gap above: an operator ran `frob
ticket land <id> --worktree <path>` and then `git worktree remove
<path>` as two separate commands. The land had actually FAILED; the
`git worktree remove` ran anyway, destroying a worktree holding 38
verified waiver-deletion commits -- recoverable only because git happened
to keep the dangling commit in its object store. `--finish` (T-1175,
above) already closes this for the CLI's own combined invocation (the
worktree removal is gated on `_print_land_proof`'s `verified` bool and
`_land`'s own `sys.exit(1)` on a failed `land()` never reaches the
finish/retire tail at all) -- but `--finish` only ever removed the
worktree CHECKOUT, leaving its branch (and every commit only reachable
through it) in place, so an operator who also wanted the branch gone was
back to a manual, unguarded `git branch -D` themselves.

`--retire-on-proof` is `--finish` plus branch deletion, sharing the exact
same `verified` gate (`_finish_land_after_success`):

1. `_print_land_proof` computes `verified` (commit is-ancestor-of-main AND
   the ticket's state on main is done/dropped) -- unchanged from `--finish`.
2. If `not verified`: refuse (`sys.exit(1)`), touching neither the
   worktree nor its branch. Identical posture to `--finish`'s own refusal,
   now shared code path (`wants_finish = ticket_land_finish or
   ticket_land_retire_on_proof`).
3. If `verified`: `_worktree_branch_name(root, worktree)` reads the
   worktree's checked-out branch name from `git worktree list --porcelain`
   BEFORE `_finish_worktree` removes the checkout (branch deletion itself
   does not need the worktree to still exist, but capturing the name
   first avoids any ordering ambiguity), then `_finish_worktree` removes
   the worktree exactly as `--finish` does, then `_delete_worktree_branch`
   runs `git branch -D <branch>` -- logged at ERROR with the exact manual
   recovery command on failure, never silent.

Because `_land`'s own top-level `sys.exit(1)` on a failed `land()` call
(`if result.is_err: ...; sys.exit(1)`) returns BEFORE `_finish_land_after_
success` is ever invoked, there is no code path from a failed land to
either the worktree or its branch being touched when `--retire-on-proof`
is passed -- the unsafe two-step sequence the incident hit is no longer
expressible as a single command.

Test coverage: `tests/test_ticket_leases.py::TestRefuseIfLandInProgress`
covers the no-lock-file pass-through, the held-lock refusal (and that the
refusal names the landing ticket), the belt-and-braces process-scan
refusal with no lock file at all, the SIGKILL-then-immediately-free
crash-safety case, and an end-to-end proof that a `land()` call holding
`_land_lock` makes a concurrent `frob ticket new` fail without moving
`root`'s tip or committing the racing ticket.
`tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish`
covers `--retire-on-proof`'s branch deletion on a real verified land, the
`None`-branch no-op, and the refuse-and-touch-nothing path on an
unverified proof.

## Worktree liveness scan (T-1715, T-1739)

`--finish`/`--retire-on-proof`'s `verified` gate (above) proves the LAND
succeeded. It proves nothing about whether the WORKTREE being removed is
still in use -- and dispatch briefs tell an agent to run `frob ticket land
<id> --worktree <their own path>` from the root checkout, so the natural,
documented invocation is the one that deletes the caller's own sandbox.
Real incident, 2026-08-06: `--finish` did exactly what its contract said
and removed a just-landed worktree that the calling agent's own process
was still cwd'd into -- every subsequent tool call failed with "the
isolation worktree appears to have been removed", the agent could not
create a replacement (worktree creation is reserved to whatever spawned
it), and it had to be abandoned and re-dispatched, losing its accumulated
context. `frob worktree sweep` (T-0836, "Coordinator worktree cleanup" in
the playbook) has the identical hazard at fleet scale: its keep-criteria
(lease/dirty/age) are all PROXIES for liveness, not liveness itself, and a
2026-08-07 dry-run during a four-agent drive caught them exactly inverted
-- the one worktree kept belonged to a retired agent holding a stale
lease, the three worktrees marked for removal belonged to agents that
were actively running (one mid-implementation on a critical ticket). The
sharpest edge: `dirty` under-covers precisely because a well-behaved agent
COMMITS its work-in-progress as stall insurance (this repo's own
guidance) -- following the guidance makes a worktree look MORE removable,
not less.

Both incidents share one fix mechanism rather than each growing a new
heuristic: `scan_for_live_worktree_process(path)`
(`frob.tickets._leases`) generalizes T-1619's `_scan_for_live_land_process`
`/proc` walk (see "Land exclusivity lease" above) to answer "is ANY live
process cwd'd into `path`", not just a `frob ticket land` process cwd'd
into the primary checkout. Same degrade-to-no-finding contract: `/proc`
unavailable, an unreadable pid, or simply no match all return `None`,
never a refusal by themselves. `refuse_if_worktree_in_use(root, worktree)`
combines that scan with the existing lease machinery
(`read_all_leases`/`is_lease_ttl_expired`, factored into a shared
`_live_lease_for_worktree` helper) into one `Result`:
`Err(WorktreeInUseError.LiveProcess)` names the pid and its argv;
`Err(WorktreeInUseError.LiveLease)` names the pinning ticket id and when
the lease was recorded. Both are logged at ERROR before returning, so a
refusal always names what it is refusing to remove and why -- "could not
finish" with no cause named is the exact DirtyMain-class mistake
(playbook section, T-1698/T-1699) this repo has already paid for once.

**`--finish`/`--retire-on-proof`** (`_finish_worktree`,
`frob.app.ticket_runner._land_cmd`): calls `refuse_if_worktree_in_use`
immediately before `git worktree remove`, after the existing `verified`
LAND-PROOF gate has already passed. A refusal here `sys.exit(1)`s WITHOUT
unwinding anything -- the land itself already fully succeeded, only the
cleanup step is refused, and the worktree branch remains the recovery
path exactly as it did before `--finish` existed. `frob ticket land <id>
--worktree PATH --finish --force` overrides the refusal, for a worktree
independently confirmed genuinely wedged (the process scan cannot always
prove a pid is dead); `--force` has no effect on anything except this
guard.

**`frob worktree sweep`** (`sweep_worktrees`/`_sweep_verdict_for_worktree`,
`frob.tickets._leases`; CLI in `frob.app.worktree_runner`): the liveness
scan runs FIRST, before the pre-existing dirty/lease/age gates, and
produces a new `kept:live` verdict naming the pid
(`kept:live(pid <N>) <path>`) -- unconditionally, regardless of whether
the worktree is clean, leased, or old, which is exactly the property the
2026-08-07 incident needed and the old three-gate design did not have.
`frob worktree sweep --force` overrides the `kept:live` gate specifically
(dirty/age are unaffected by `--force`); refuse-by-default is the point
of the flag existing at all, so reach for it narrowly, worktree by
worktree, not as a blanket unblock for a whole sweep.

Both call sites share `scan_for_live_worktree_process` and
`_live_lease_for_worktree` directly -- there is intentionally only one
process-liveness scanner and one lease-liveness judgment in
`frob.tickets._leases`, not a third or fourth heuristic layered
alongside lease/dirty/age. "Could not determine liveness" is never
reachable as "prove it is dead": both underlying checks degrade to
`None`/no-match on any uncertainty, and a `None`/no-match result is
always treated as "not proven in use" -- never as "proven not in use" --
by the two call sites, not by the checks manufacturing false confidence
themselves.

Regression coverage (`tests/unit/test_land_finish_guard.py`,
`tests/test_worktree_guard.py`) specifically covers the exact shape that
would have killed three agents: a worktree that is CLEAN, holds NO lease,
has a RECENT HEAD commit, and has a live process cwd'd into it -- asserts
it is kept/refused and that the pid is named, not just that some
generically-stale worktree is caught.

Related, separately ticketed rather than folded in here: T-1739 also
surfaced a lease/state disagreement (a stale lease naming one ticket as
the `doable --show-blocked` holder while the ledger has a different
ticket queued) -- that is a distinct defect in `doable`'s own attribution
logic, not a liveness question, and is tracked as its own ticket (see
T-1743) rather than folded into the scan this section documents.

## Passenger-ticket disclosure (T-1618)

`frob ticket land <id> --worktree W` merges `W`'s BRANCH, not just the
commits belonging to `<id>`. `_check_cross_ticket_leakage` (T-1355/T-1639,
above) already refuses on a scope-glob-plus-ledger-record-diff heuristic
when a sibling ticket is `IN_PROGRESS` -- but it explicitly EXEMPTS any
sibling already `DONE`/`DROPPED` (`_find_leaked_tickets`'s `effective_
state in (DONE, DROPPED): continue`), on the assumption that a closed
ticket's scope claim is "spent". Real incident, 2026-08-05: worktree
w24-waive-family held five tickets; T-1579's WAIVE004 self-heal escape
was judged unsafe and reverted IN THE WORKTREE, but landing a DIFFERENT
sibling (T-1581) still carried T-1579's code onto main, where it deleted
55 live `frob:waive` directives across five gate families before anyone
noticed. Whatever state T-1579's own ledger record ended up in, its CODE
never actually left the branch -- exactly the shape the DONE/DROPPED
exemption cannot see, because it never looks at the diff's own content at
all, only at scope declarations and ledger state.

`_check_passenger_tickets` (`frob.tickets._land`) is a deliberately
DIFFERENT, complementary signal: it scans the branch's FULL diff (`git
diff base_ref...HEAD`, not `--name-only`) for `frob:ticket <id>` directive
lines naming any ticket OTHER than the one landing. This asks a narrower,
more precise question than scope-matching -- whose fingerprint is on the
code actually riding along, full stop -- and does not consult any
sibling's ledger state at all, so a DROPPED sibling whose code is still
physically present is caught exactly as readily as an IN_PROGRESS one.
Wired into `_land_precheck_remaining_checks` alongside the existing
leakage check, sharing the SAME `--allow-cross-ticket` escape hatch
(`frob ticket land --allow-cross-ticket`) -- one flag an operator already
knows, not a second differently-named override. A refusal (`LandError.
PassengerTickets`) lists every passenger id found; an acknowledged
override logs the same list at WARNING before proceeding. Nothing about
the land is silent either way -- the T-1618 incident's own root complaint
("nothing in the output said T-1579 was going to main") no longer has a
code path where that holds.

**T-2082 fix -- relocation is no longer a false positive:** the original
version counted an id as a passenger the moment ANY `+`-prefixed line
named it, with no regard for whether the same directive was also removed
elsewhere in the same diff. A refactor that RELOCATES a function carrying
a pre-existing `frob:ticket <id>` comment emits both a `+` at the new
site and a `-` at the old -- net occurrence delta zero -- and the old
check refused every such move, forcing two independent agents to
`--allow-cross-ticket` in the same hour on pure ARCH001 splits that added
none of the named tickets' code (T-2073, four ids; T-2077, one id).

The discriminator (`_passenger_ids_from_line_buckets`) is now each id's
OCCURRENCE COUNT delta between `+`- and `-`-prefixed lines: an id is a
genuine passenger only if `+`-line occurrences strictly EXCEED `-`-line
occurrences. An equal-count id is exempt only when the exact multiset of
added directive lines equals the exact multiset of removed directive
lines (verbatim text, not just id match) -- so a relocation that ALSO
edits the directive line itself (folding it into another comment, or
changing the line it sits on) still fails the verbatim check and is still
reported, deliberately erring toward refusing when the two sides are not
an exact match. This does not weaken the original guard: the 2026-08-05
incident's passenger code was physically ADDED with no corresponding
removal, so its count strictly increases under either version of the
check, and `tests/unit/test_land_cross_ticket_leakage.py::
TestPassengerTickets` carries a regression test reproducing that exact
incident shape to prove the refusal still fires.

## Already-landed-on-main: first-class outcome (T-1618)

The second, benign-but-confusing half of the same incident: once one
ticket's land has carried a sibling's code onto main (the passenger check
above stops this going forward, but does nothing for a worktree that
already leaked before this fix existed), that sibling's own later `frob
ticket land` finds nothing left to contribute -- its scope's diff against
main is empty. Before this fix, that fell through into whatever the
normal land path does with an empty changeset: BUG002 finds the repro
test already passing at the parent, TEST016 finds an empty diff with no
mutants to kill. Both gates are technically CORRECT; the ticket is simply
already done. The operator diagnosed and routed around this by hand three
times in one session (verify content on main, `frob ticket close
--skip-mutation-evidence`).

`_check_already_landed` (`frob.tickets._land`) recognizes the shape
directly: when `worktree` is CLEAN (`_porcelain_dirty` -- see below for
why this matters), the ticket's own declared scope (excluding the ledger
path, which changes on every land regardless) has zero hits in
`_branch_changed_files(worktree, base_ref)`, AND (T-1675) the ticket's own
ledger record read directly off `base_ref` (`_ledger_ticket_at_ref`)
already shows `state: done` there, it refuses with `LandError.
AlreadyLandedOnMain` and a message naming the exact manual recipe the
incident's operator worked out by hand: verify the content against
`base_ref`, then `frob ticket close <id>` directly. This function still
does NOT verify the content's correctness itself -- `frob.tickets` cannot
run `base_ref`'s tests or gates (docs/rework.md's cycle-avoidance rule:
that needs `frob.gates`/`frob.testing`, which this package does not
import) -- so a `AlreadyLandedOnMain` refusal remains a strong,
well-targeted HINT, not a full proof; the operator's own verification step
is still real work, just no longer undirected work.

**The signal problem, and its fix (T-1675).** "No diff in the declared
scope" alone was being asked to answer "was this already landed?", and it
could not: an empty scope-diff is equally consistent with *the work is
already on main*, *the work landed outside its declared scope globs*, and
*this ticket legitimately changed only docs or the ledger*. That was
absence-of-evidence read as evidence-of-absence, and it forced this check
off by default -- it never ran for a real land, so the defect class it
targets still reached main. T-1675 closed the gap by requiring a SECOND,
positive signal alongside the empty diff: the ticket's own ledger record,
read directly off `base_ref`, must already claim `state: done` there. A
ticket that has not yet landed cannot already be `done` on `base_ref` --
only `frob ticket close`/`land`'s own squash-apply ever write that state
-- so this is genuine positive evidence the content made it to main, not
an inference from silence. A docs-only, ledger-only, or scope-mismatched
ticket landing for the FIRST time still gets `Ok(None)` here: its scope-
diff may be empty, but its own record on `base_ref` is not yet `done`,
so the refusal correctly does not fire.

**On by default, no opt-in flag (T-1675).** An early draft (T-1618) wired
the empty-diff signal alone into `_land_precheck` unconditionally and it
regressed 20 existing tests across this repo's own `test_ticket_land.py`
suite -- an empty scope-diff turns out to be the ORDINARY shape of a large
legitimate class (a docs-only ticket, a ledger-only/Done-report-only
ticket, a test fixture that declares a scope without ever writing a file
under it). That forced the check behind a now-removed `land` opt-in flag
(formerly `--check-already-landed`). The positive on-main-state
requirement above is what makes an unconditional default safe now: every
member of that false-positive class is landing for the first time, so its
own record on `base_ref` cannot already show `done` -- the flag and its
CLI switch are gone; the check always runs. `_porcelain_dirty` still gates
it: this check runs in `_land_precheck`, BEFORE `land`'s own wip-commit
stage folds uncommitted work into a real commit, so a DIRTY worktree's
empty COMMITTED diff would otherwise look identical to "already landed"
even though the real work simply has not been committed yet -- the check
is skipped entirely whenever the worktree is dirty, deferring to whatever
the rest of the land pipeline does with that uncommitted work.

**A second positive signal, for a ticket that never landed at all
(T-1950).** T-1675's DONE-state signal only fires for a RE-land -- a
ticket whose content is already on main because it (or an earlier attempt
at it) closed there before. It cannot see the complementary shape: a
ticket whose content rode onto main under a SIBLING's `--allow-cross-
ticket` land BEFORE this ticket itself ever landed once. `ticket.id`'s
own record on `base_ref` is still `queued`/`planned`/`in-progress` in
that case -- not `done` -- so T-1675's check correctly stays silent, and
the land proceeds to squash-apply an empty scope-diff, reporting `LAND-
PROOF verified=True` and passing `scripts/verify_lands.py` for a commit
that carries none of its own ticket's work. Measured for real, 2026-08-10:
T-1720's land (`48f49d78b8db`) landed exactly this way -- its feature had
already ridden onto main under T-1922's earlier `--allow-cross-ticket`
land (`b508b0ad3eec`), including the source-linking directive this
repo's own convention puts on every touched public symbol naming its
owning ticket, but T-1720's
own ledger record was never `done` on `base_ref` at land time, so T-1675's
check never fired.

`_ticket_directive_present_on_ref` supplies the missing signal: does
`base_ref`'s CURRENT tree already contain a literal `frob:ticket <ticket.
id>` directive anywhere under `src/`? That directive is written by this
repo's own convention onto every touched public symbol, never by an
external replacement, and never present for a ticket that has contributed
no code anywhere yet -- so, like the DONE-state signal, it is positive
evidence, not an inference from absence. A docs-only or ledger-only
ticket landing for the first time (T-1675's own regression target) never
carries this directive on any file, so it stays unaffected: `_check_
already_landed` now refuses on EITHER positive signal (DONE-state OR
directive-present), sharing the same refusal message and remedy
(`_refuse_already_landed`) with only the naming of which signal fired
differing.

### Already-landed markers at DISPATCH time (T-1744 case 1)

T-1675's `_check_already_landed` above catches a ticket already `state:
done` on `base_ref` at the moment IT is being landed a second time. It
has no reach into a different failure mode: a fix that lands on `main`
by a DIRECT commit, never through `frob ticket land`/`close` at all. Two
confirmed instances (T-1487, T-1587, both 2026-08-07) sat `queued` for
days -- one flagged CRITICAL by the dispatch-stale alarm -- while their
described work was already on `main`, because nothing about the direct
commit ever touched either ticket's own ledger record. An agent
dispatched onto either spent real budget re-verifying a fix that had
shipped days earlier.

`already_landed_markers` (`frob.tickets._doable`) closes this at DISPATCH
time instead: for every doable candidate (queued/planned, unblocked --
`_doable_candidates`, the same input `doable`/`doable_blocked` use), it
greps the files the ticket's OWN declared scope names for that ticket's
own `frob:ticket <id>` directive text, verbatim. A hit means the code
already carries this ticket's attribution marker despite the ledger
still calling it open -- exactly the T-1487/T-1587 shape, caught before
an agent is ever assigned rather than after one has spent budget
re-deriving it by hand.

This is a POSITIVE signal, same discipline as T-1675's own fix: it never
infers from an empty diff, a stale ticket, or ledger prose, only from the
directive text actually present in a scoped file. Any over-broad scope
entry (`_over_broad_scope_entries`, the same criterion `leased_by`'s
lease-demotion and `large_glob_warnings`'s nudge both already consult) is
excluded from the scan entirely (`_narrow_scope_files`) -- scanning every
file a `src/**`-shaped glob matches for one ticket's marker would be
noise, not signal, and would make a broad-scoped ticket falsely look
"already landed" the moment ANY sibling ticket's directive happened to
land somewhere under that glob.

This function returns data, not a refusal -- unlike `_check_already_
landed`, which blocks a `land` call outright, `already_landed_markers` is
read-only: a coordinator or dispatch-alarm caller consults it and decides
what to do (flag the ticket for a quick land-outside-workflow check,
surface it in `--show-blocked`-style output, etc.). CLI/alarm wiring for
this is intentionally NOT part of this change -- `frob.tickets._doable`
is the shared computation both a future `doable` CLI decoration and a
future dispatch-alarm consumer would call, kept in the one file per this
package's existing split-by-question convention (module docstring:
"is this ticket dispatchable right now, and if not, why"), with the
actual CLI/alarm surface left to a follow-up ticket scoped to
`frob.app.ticket_runner`.

T-1744 case 3 (a ticket whose PREMISE is already false -- the bug it
describes was fixed by a DIFFERENT ticket's change, not its own directive
marker) is a distinct, harder problem this function does not attempt:
there is no positive textual signal to grep for when the fix landed under
someone else's attribution. That case needs its own design pass and is
tracked separately, not folded into this marker sweep.

**Why `CrossTicketLeakage` did not fire for the T-1579 case** (the
ticket's own explicit question): two independent reasons, both closed by
the passenger-ticket work above rather than by changing the leakage check
itself (T-1639's IN_PROGRESS-only refinement was its own deliberate,
already-considered fix for a different false-positive class and must not
regress). First, `_find_leaked_tickets` exempts any sibling whose
EFFECTIVE state is DONE/DROPPED outright -- if T-1579's in-worktree
"revert" updated its OWN ticket record to a terminal state (even without
fully reverting the code), the leakage check would treat it as settled
and never re-examine its files at all. Second, even for a non-exempt
sibling, the leakage check's signal is `changed_paths` from `--name-only`,
a net diff -- if the revert's own commit brought a FILE back to byte-
identical content relative to `base_ref`, that file simply stops
appearing as changed at all, regardless of the sibling ticket's ledger
state, so a scope hit against it can vanish even though other, un-reverted
files the same ticket touched (per the incident, the 55 `frob:waive`
deletions landed in files across arch/strata/perf/graph/vet, not
necessarily the exact file that was "reverted") remain. Both gaps trace
to the same root property: `_check_cross_ticket_leakage` was built to
answer "does a scope declaration overlap a change", never "whose
`frob:ticket` fingerprint is physically in this diff" -- the latter is
what `_check_passenger_tickets` answers instead, deliberately not by
patching the former's heuristics to try to cover both questions.

## Cross-ticket leakage only refuses on an IN_PROGRESS sibling (T-1639)

<!-- frob:describes src/frob/tickets/_land.py::_find_leaked_tickets -->
<!-- frob:describes src/frob/tickets/_land.py::_check_cross_ticket_leakage -->

`_check_cross_ticket_leakage` (T-1355) refuses a land whose branch touches
files covered by a DIFFERENT ticket's declared `scope`, when that other
ticket is `IN_PROGRESS` on `root`'s ledger -- the incident class where
landing one ticket out of a multi-ticket series worktree silently carries
a sibling's still-open work onto main.

T-1639: before this fix, "still open" meant "not `DONE`/`DROPPED`" --
which also matched `QUEUED`/`PLANNED`/`BLOCKED`. Filing a ticket with a
generously broad scope (this repo's own convention: declare scope early
and wide so nothing is silently out of bounds) reserved that scope
against every OTHER land immediately, before a single commit existed for
it -- measured 2026-08-06: a freshly filed, unstarted ticket (T-1637)
blocked an unrelated land (T-1636) over 12 files that only overlapped by
declaration, forcing `--allow-cross-ticket` as a reflex habit.

The fix reuses the same line `frob.tickets._leases` already draws for
worktree leases: a lease (and now a CrossTicketLeakage refusal) exists
only for a ticket that is actually being worked, never one merely filed.
`_find_leaked_tickets` still computes every scope-overlap hit exactly as
before (including the T-1390 "sibling's own ledger record never moved"
exemption), but only a hit against an `IN_PROGRESS` sibling lands in the
`leaked` map that `_report_leaked_tickets` refuses on. A hit against a
`QUEUED`/`PLANNED`/`BLOCKED` sibling is still logged (at INFO, naming the
ticket and its state) so the overlap is disclosed, not silently dropped
-- it just no longer blocks. This does not weaken the T-1618 case the
check exists for (a shared series worktree carrying a sibling's
COMMITTED work onto main): that case always involves a sibling that was
actually started, so it is always `IN_PROGRESS` by the time it could
leak anything.

**T-1967 removed the T-1370 same-worktree exemption entirely.** A
sibling ticket leased to the SAME worktree as the landing ticket used to
be exempted here unconditionally, no matter its state -- "one agent
landing its own tickets back to back, not a real cross-agent leak".
Measured 2026-08-10: that exemption was exactly the guard hole that let
a docs-only ticket's land (T-1958) silently carry a sibling's (T-1956's)
entire production change onto main, with no flag and no warning printed
at all -- sharing a worktree across a ticket series is the NORMAL,
endorsed dispatch pattern here (playbook section 0), which made this the
default configuration, not an edge case. A same-worktree sibling with a
real hit now flows into the exact same refusal/`--allow-cross-ticket`
path a cross-worktree leak already used. This does not reintroduce
T-1370's original mutual-deadlock concern: a hit only ever exists once a
sibling has genuinely been worked (`IN_PROGRESS`, ledger record moved)
on this branch, and `--allow-cross-ticket` remains the explicit, logged
way through for a genuinely intentional joint land -- once the first of
two mutually-scoped same-worktree tickets lands, the second's own later
land finds the first already `DONE` and exempt.

## Orphaned evidence deletion (T-1946)

<!-- frob:describes src/frob/tickets/_land.py::_check_orphaned_evidence_deletion -->

`_check_orphaned_evidence_deletion` refuses a land whose branch's OWN
committed changes (`_branch_changed_files`, three-dot -- only paths this
diff itself touched can ever trigger it) delete or rename a pytest test
node bound as evidence on a DIFFERENT ticket, such that the other
ticket's evidence no longer resolves against the worktree's currently
collected tests.

MEASURED (2026-08-10): two independent actors orphaned three unrelated
tickets' evidence in one hour, each deleting/replacing a test with no
signal the diff was touching anything outside its own declared scope --
100% of the then-current unscoped error floor (4 COV003 findings, one
deletion took out three tickets at once since blast radius is
superlinear in how well-cited a test is). This had been recorded as a
known hazard before (re-measure unscoped after a refactor lands) and
still happened twice to two different actors in the same hour -- the
written-down rule alone did not enforce itself.

Runs in `_land_precheck_remaining_checks`, right after `_check_cross_
ticket_leakage` and before the mutation-evidence obligation, using the
same `load_all(worktree)` ledger the leakage check reads -- so a rename
that ALSO re-points the affected ticket's evidence in the SAME diff is
never refused: the check evaluates the ledger's POST-diff state, and a
re-pointed evidence id that now resolves against the worktree's
collected tests is simply valid, no special-case needed. Deliberately
does NOT auto-repoint or auto-delete the stale evidence itself -- the
WAIVE004 lesson (a "safe" cleanup silently deleted 55 live waivers)
applied to evidence: the binding is the only record a ticket was ever
proven, so repointing it automatically would fabricate proof. The
refusal names every orphaned ticket id and evidence id; resolving it is
a human/agent decision -- re-point to the replacement test, or re-scope
the ticket and record fresh evidence.

Best-effort like the other land-time checks in this section: a `_branch_
changed_files` or `collect_python_tests` failure is logged and treated
as `Ok(None)` rather than blocking the land on an unrelated tooling
problem -- COV003's own authoritative sweep still runs at `frob check`
regardless of whether this preflight could evaluate.

Not yet re-run post-mutation the way `_check_cross_ticket_leakage` is
(`_reverify_cross_ticket_leakage_post_mutation`, T-1932) -- the T-1931
hazard that motivated that second call site was a Tier-A auto-fix
handler regenerating a specific leaked interface edge, and no Tier-A
handler in this repo deletes or renames test files, so the mutation
window this check would need to close is narrower. Recorded as a known
gap rather than silently assumed safe; a future Tier-A handler that
touches test files should re-open this question.

## Evidence-only scope (T-1944)

<!-- frob:describes src/frob/tickets/_scope.py::demote_to_evidence_only -->
<!-- frob:enumerates src/frob/tickets/_models.py::Ticket -->

`scope` used to serve two different purposes wrongly conflated into one
field: evidence coverage ("this ticket's recorded evidence lives here",
D-02's `evidence_covers_scope`) and write lease ("no other ticket may
modify these paths", `_scope_add_conflicts`/`_find_leaked_tickets`).
Citing a PRE-EXISTING test as evidence -- an explicitly endorsed pattern
for a ticket with no new code path -- used to be satisfiable only by
adding that test's file to `scope`, which ALSO claimed a write lease on
it. LIVE INCIDENT: T-1686 (an epic, done-report on main, zero lines of
code changed) cited one existing test in `tests/test_ticket_land.py` and
therefore permanently held a write lease on the repo's highest-traffic
land test file -- `scope --remove` correctly refused
(`ScopeRemoveOrphansEvidence`) because dropping the path would have
orphaned the recorded evidence, so the epic was trapped holding a lease
it never used, blocking an unrelated land (T-1922) with
`CrossTicketLeakage`.

**The fix**: `Ticket.evidence_scope` (a second `tuple[str, ...]`,
disjoint from `scope`) covers evidence without ever claiming a write
lease -- `_scope_add_conflicts`/`_find_leaked_tickets`/`scope_lease_
conflict` read `scope` alone, so a path that lives ONLY in `evidence_
scope` is invisible to every lease/leakage check by construction, not by
a special-case exemption. `evidence_covers_scope` (D-02) checks `scope +
evidence_scope` together, so evidence recorded there is exactly as
"covered" as evidence recorded under `scope`.

- **Non-leasing by default, no flag**: `add_evidence` auto-populates
  `evidence_scope` (never `scope`) whenever a newly cited node's file is
  not already covered by either field -- per the standing "a command
  requires knowledge of the command" directive, an agent citing a pre-
  existing test as evidence gets the non-leasing behavior automatically,
  with nothing new to remember to pass.
- **`frob.tickets.demote_to_evidence_only(root, ticket_id, globs,
  reason=...)`**: the remedy for a ticket ALREADY stuck the old way (the
  T-1686 shape) -- moves one or more EXISTING `scope` entries into
  `evidence_scope` in ONE atomic write, so D-02 coverage is never
  momentarily false between the removal and the re-add a plain `scope
  --remove` + `--add` round-trip would require (and which would itself
  deadlock on `ScopeRemoveOrphansEvidence`, since the removal alone
  would look like it orphans evidence). Refuses `ScopeRemoveNotDeclared`
  for a glob not currently in `ticket.scope`, the same "must be declared
  to be removed" rule `mutate_scope`'s own remove path enforces.
  Applied to T-1686 itself on 2026-08-10 as the mechanism's first real
  case: its lease on `tests/test_ticket_land.py` released, evidence
  coverage confirmed unaffected (`scope_lease_conflict` returns `None`
  for that path afterward). Not yet wired to a `frob ticket scope` CLI
  flag -- library-only for now (`T-1975` tracks the CLI surface).
- **`ScopeRemoveOrphansEvidence` is UNCHANGED**: a plain `scope --remove`
  with no matching `evidence_scope` demotion still refuses exactly as
  before -- this fix adds a new, narrower escape hatch, it does not
  weaken the existing guard the way a "safe" auto-repoint would have
  (the WAIVE004 lesson, applied here: evidence coverage is the only
  record a ticket was ever proven, so nothing here ever repoints or
  deletes it, only relocates WHICH field of the SAME ticket claims it).
- **Legacy scope entries are unaffected until demoted**: this fix does
  not retroactively migrate every existing ticket's `scope` -- a ticket
  filed before T-1944 that already conflated evidence coverage with a
  write lease keeps behaving exactly as it did until someone runs
  `demote_to_evidence_only` on it.

## Post-mutation reverification (T-1932)

<!-- frob:describes src/frob/tickets/_land.py::_reverify_cross_ticket_leakage_post_mutation -->

THE INVARIANT: on the land path, no mutation may run after a guard whose
decision that mutation can invalidate. This has been violated three
separate times, each fixed as a one-off before T-1932 named the general
shape: T-1903 (the pre-land strata parse guard ran before the T-1138
Tier-A rewrite it was meant to catch corruption from -- three lands
published an unparseable `design/frob.strata` at `LAND-PROOF
verified=True`); T-1910/T-1920 (the ticket close and REL001 bump rode the
same commit the ancestry check tests, fixed BY CONSTRUCTION rather than
by a later check); T-1931 (the CrossTicketLeakage guard correctly
refused, a human reverted the offending line, and land's own Tier-A
auto-fix pass silently re-added it before the next attempt -- the guard
fired and was overruled).

T-1931's root cause: `_check_cross_ticket_leakage`'s diff source
(`_branch_changed_files`, `git diff base_ref...HEAD`) reads ONLY
committed history, by construction. `frob ticket land`'s own T-1175
pre-land auto-fix absorption (`_absorb_pre_land_fixes`: `frob fmt` + the
Tier-A handlers) runs BEFORE `land()` is even called and leaves its
rewrites as ORDINARY UNCOMMITTED changes for `land()`'s own wip-commit
(inside `_land_merge_stage`) to pick up later. So the preflight leakage
check -- deliberately the very first thing `land()` does, before any git
mutation, for a cheap fail-fast -- structurally cannot see content
Tier-A already wrote to disk but had not yet committed. The wip-commit is
the FIRST point any such mutation becomes part of history.

THE FIX: `_reverify_cross_ticket_leakage_post_mutation` is a pure
re-invocation of `_check_cross_ticket_leakage` with the same arguments
the preflight call used -- there is exactly one implementation of the
check, called from two points in `_land_locked`'s sequence, never two
copies that can drift apart. `_land_locked` calls it immediately after
`_land_merge_stage` returns (the wip-commit has already run, so every
prior uncommitted mutation is now visible to `_branch_changed_files`
exactly as the preflight call would have seen it had it run then), and
before the D-05 dry-run early return (a `--dry-run` must preview the
exact refusal a real run would hit). A refusal aborts the just-created
merge via the existing `_abort_merge` unwind -- the same shape every
other post-merge check in `_land_locked` already uses, no new unwind
path.

HOW A NEW GUARD IS PREVENTED FROM SILENTLY VIOLATING THIS (T-1932
acceptance criterion 4): not yet by a fully generic, structural
mechanism -- that is residue (see the ticket filed from T-1932's own Done
report, tracked as a follow-up to build a registry that forces every
committed-diff-reading guard in `_land_precheck_remaining_checks` to
register a post-mutation twin). What DOES exist now is a worked pattern
with a locked regression test:
`tests/unit/test_land_step_ordering.py::TestPostMutationRecheckOrdering::test_leakage_recheck_runs_after_the_wip_commit_in_land_locked`
asserts, via `inspect.getsource(_land_locked)`, that the post-mutation
re-check call appears strictly AFTER the `_land_merge_stage` call in
source order -- a future edit that reorders these two calls (reintroducing
the exact T-1931 shape for THIS guard) fails mechanically, not by relying
on a reviewer remembering the rule. A future guard added elsewhere in the
preflight sequence should copy this same shape (self-delegating
re-invocation, called after `_land_merge_stage`, pinned by an equivalent
source-order test) until the generic registry exists.

## Auto-sync after a successful land (T-1720, rebase replaced by merge in T-2173)

<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_auto_sync_worktree_onto_main -->

Every land performed across two multi-ticket series worktrees in one
measured session hit the same sequence: land a ticket successfully
(`LAND-PROOF: ... verified=True`), then the NEXT `frob check --ticket
<next-id>` in the SAME worktree reports spurious SCOPE001/COV002 findings
on files the just-landed ticket touched -- the worktree's own step-by-
step commits for that already-landed work are still present on its
branch, and the branch has not moved to `main`'s new (squashed) tip, so
`git diff main` for those files looks non-empty even though the content
is byte-identical. Resolved by hand, every single time (six for six),
with `git merge main` before starting the next ticket.

`frob ticket land` does this automatically: `_auto_sync_worktree_
onto_main` merges `<main>` into the worktree right after a real
(non-`--dry-run`) land, but only when `--finish`/`--retire-on-proof` was
NOT passed (a worktree about to be removed by `_finish_worktree` gains
nothing from being synced first, and only takes on the same small
conflict-abort risk for no benefit).

T-2173: T-1720's original implementation used `git rebase <main>`, not
`git merge`. That rebase failed identically on four separate real lands
in one day, across three different worktrees, every time conflicting on
a ledger file, every time cleared by a by-hand `git merge main` instead.
Two candidate mechanisms were investigated and TESTED DIRECTLY rather
than assumed:

1. **Falsified**: "the `tickets.md`/`tickets-archive.md` `merge=frob-
   ledger` driver (`.gitattributes`) is only invoked by `git merge`, not
   by `git rebase`'s internal per-commit replay." A real registered
   driver on a throwaway file was invoked identically by both `git merge`
   and `git rebase` -- this was never the actual mechanism.
2. **Confirmed**: the classic "rebase a branch after its own content was
   already squash-merged" conflict class, independent of any merge
   driver. Reproduced directly with no driver registered at all: a
   worktree branch making several separate commits that walk one file
   through a sequence of states (mirroring the auto-commits `frob ticket
   scope`/`start`/`evidence`/`done-report` each make), then `main`
   receiving the SAME final state as ONE squash-applied commit (exactly
   what `frob ticket land`'s own squash-apply does) -- `git merge` from
   the worktree branch succeeds with no conflict (one 3-way diff of
   final-vs-final finds nothing real to resolve); `git rebase main` from
   the same branch conflicts on the FIRST replayed commit, even though
   the two branches' final content is byte-identical, because rebase
   replays each of the worktree's original, now-superseded intermediate
   commits one at a time against main's already-final post-squash tip.
   This is deterministic, not a race -- every `frob ticket land` squash-
   applies, so this fired on every affected land, not occasionally.

`git merge` is structurally immune to (2) by construction; `git rebase`
is structurally exposed to it, regardless of merge drivers.

ORDERING (T-1932's own finding, applied here, unchanged by T-2173): the
merge runs strictly AFTER `_print_land_proof` has already confirmed
`verified=True`. That check reads `root`'s own `main` ref and the just-
landed commit sha, neither of which a merge of the WORKTREE's own branch
touches -- so placing the mutation after that guard means it cannot
retroactively invalidate a verdict the guard already reached. Nothing
later in the same `frob ticket land` invocation re-reads the worktree's
branch state, so this mutation introduces no new guard for a later step
to defeat either -- it is the last thing the successful-land path does.

T-2173: the merge only runs when the worktree is CLEAN (`git status
--porcelain` empty) -- merging into a dirty worktree risks destroying an
agent's own uncommitted in-progress edits, which this function cannot
distinguish from "safe to auto-sync" any more reliably than a human
operator checking by hand would need to. A dirty worktree is skipped
silently, same posture as the existing detached-HEAD/no-resolvable-
`main` skips.

Best-effort, never fails an already-successful land: a real conflict
aborts immediately (`git merge --abort`), restores the worktree to its
exact pre-merge state, and logs a WARNING naming the ticket and worktree
for manual resolution -- never left mid-merge, which would otherwise hand
a LATER guard (the next ticket's own T-1922 committed-waive-deletion
scan, or its pre-work sweep) a half-mutated worktree to reason about.

## OutOfScopeWaiveDeletion false-refusal on a stale worktree (T-1922)

<!-- frob:describes src/frob/tickets/_land.py::_restrict_to_branch_own_files -->

`_committed_waive_deletions`'s T-1550 two-dot diff (`main_branch..HEAD`)
is a plain CONTENT diff between two commits, not an ancestry-scoped one --
it reports a line as "deleted" whenever `main_branch`'s CURRENT tip has
it and `HEAD` does not, regardless of WHICH side actually changed. When
`main_branch` has moved forward (an unrelated, already-landed ticket
edited a `frob:waive` comment's text on a file this branch never touched
at all) while this worktree has not yet merged that forward, the two-dot
diff reads main's own new text as though HEAD deleted it -- attributing
an entirely unrelated, already-landed edit to whichever ticket happens to
retry a land next, off a worktree whose last `git merge main` predates
it.

The real 2026-08 incident: T-1918 reworded an `AFFECT001` waiver's reason
string in `_renumber_v2.py`; two UNRELATED worktrees (T-1911's, T-1904's),
neither of which had ever touched that file, both got refused with
`OutOfScopeWaiveDeletion` naming it, purely because their own merge-base
predated T-1918's land. The confirmed workaround (`git merge main`
immediately before retrying) worked every time specifically because it
moved the two-dot diff's LEFT side forward past the unrelated edit -- it
never touched what the check was actually measuring.

T-1550's own two-dot-against-live-tip design is NOT reverted -- it is
exactly what makes an already-landed SIBLING ticket's deletion (on this
same branch) invisible once main independently reflects the same state
(`_committed_waive_deletions`'s own T-1550 rationale). Replacing it with
a naive three-dot `main_branch...HEAD` diff (ancestry-scoped, i.e.
re-diffing from the STALE fork point) would silently UNDO that fix and
reintroduce the T-1225/T-1444 re-attribution bug T-1550 closed -- a
worktree that has not rebased keeps the same old merge-base either way,
so a three-dot diff from it would show the sibling's already-landed
commits all over again.

The actual missing filter is orthogonal to both: does a finding's file
even belong to something THIS BRANCH'S OWN COMMITS changed at all?
`_restrict_to_branch_own_files` answers exactly that, reusing
`_branch_changed_files(worktree, main_branch)` -- the same three-dot
`main_branch...HEAD` --name-only diff `_check_cross_ticket_leakage`
already uses for an identical "what did this branch itself commit"
question -- independent of content equality. A file this branch's own
history never touched can never appear in that set, no matter how stale
the worktree's last merge is or how much main has moved; findings whose
file is NOT in it are dropped. A genuine out-of-scope, undeclared
`frob:waive` deletion the branch's OWN commits made still refuses
normally, since its file IS in `_branch_changed_files`'s own set (proven
by `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal
.test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses`,
alongside the false-positive regression test
`.test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse`).

## Post-land unscoped error sweep (T-1456)

<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_unscoped_error_findings -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_apply_root_tier_a_fixes -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_post_land_unscoped_error_sweep -->

Every wave of a busy drive left small unscoped residue on main a
`--ticket`-scoped land verification could not see: a waiver that did not
travel with a relocated block of prose (INV006/PII012 on a file split), a
format drift, a stale registry denominator, a SELFAUDIT interface
attribute for a store block. Each was invisible to `land`'s own T-0754/
T-1410 claim-divergence machinery -- which compares SCOPED (`--ticket`)
counts/identities -- and only surfaced in the coordinator's next full,
unscoped `frob check`, forcing a hand-fix cycle between lands.

`frob ticket land`'s CLI layer (`_land`, `_land_cmd.py`) now brackets the
real `land()` call with an UNSCOPED, `--budget`-bounded (default 90s)
error-identity sweep of `root`:

1. **Before `land()` runs** (real, non-dry-run lands only): capture
   `root`'s current `HEAD` (`pre_land_sha`) and an unscoped `(rule_id,
   file)` error-finding set (`_unscoped_error_findings`, no `--ticket`
   filter -- deliberately the opposite of `_check_gate_findings_fn`'s
   scoped set) as the baseline. Either capture failing (a spawn refusal,
   an unparsable run) degrades to `None`, never a guessed empty set.
2. **After `land()` returns `Ok`** (the squash-apply commit has already
   landed on `root`): `_post_land_unscoped_error_sweep` re-runs the same
   unscoped scan and diffs it against the baseline. `new_findings = fresh
   - baseline` is the residue THIS land's squash-apply introduced that no
   `--ticket`-scoped check could have caught.
3. **No new findings**: silent no-op, the common case.
4. **New findings, Tier-A auto-fixable**: `_apply_root_tier_a_fixes` runs
   the T-1138 deterministic auto-fix handlers against `root`'s whole tree
   (unscoped, unlike the pre-land `_tier_a_pre_land_step`'s touched-set
   scoping) and commits the result as a follow-up `fix(land): <id>
   post-land Tier-A cleanup (...)` commit if it resolves every new
   finding.
5. **New findings NOT resolved by auto-fix**: refuse. `root` is hard-reset
   back to `pre_land_sha` (`git reset --hard`), the exact finding list is
   logged, and the CLI exits non-zero -- a landing that would have
   regressed main's error floor never reaches it, and a reset FAILURE is
   itself logged loudly (manual repair, rather than a silently landed
   regression) instead of assumed to have succeeded.

Either side of the comparison coming back unmeasurable (`None`) skips the
sweep entirely rather than comparing a real set against a guess -- the
same unmeasured-is-not-zero posture `_check_gates_summary_fn`/
`_check_gate_findings_fn` (T-0832/T-0846) already use for the scoped
claim-divergence check this complements, not replaces.

## `frob check --land-parity` (T-1535)

<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::land_parity_findings -->
<!-- frob:describes src/frob/app/check_runner.py::_run_land_parity -->

Every blind repair round on 2026-08-04/05 traced back to worktree-check
vs. land-sweep divergence (module docstring's motivating incidents for
the post-land sweep above apply equally in the OTHER direction: a
worktree agent's own scoped verification passing while the same tree
would refuse at land). `land_parity_findings` (called by `frob check
--land-parity`, `_run_land_parity`) runs the EXACT same evaluation the
pre-commit/post-land sweeps above run against the CURRENT worktree tree
with no baseline diff: `_unscoped_error_findings` (this section's own
spawn+parse function, reused verbatim) with `FROB_NO_GATE_CACHE=1`
forced into the SPAWNED check's environment (never this process's own
`os.environ` -- the caller's `env=` param on `_unscoped_error_findings`,
T-1535, exists for exactly this), then `_drop_checkpoint_exempt_findings`
(this section's own T-1524 exemption function, reused verbatim) applied
unconditionally.

`None` (unmeasurable) exits 1 with a loud "could not evaluate" message,
never a false-clean pass; an empty set exits 0; a non-empty set prints
every `(rule, file)` finding and exits 1 -- see
`docs/guides/agent-playbook.md#6g-run-frob-check---land-parity-before-writing-your-done-report-t-1535`
for the per-dispatch usage recipe. Reusing both functions verbatim (never
a second hand-copied parser or exemption list) is what makes this a
PARITY check rather than an approximation: `tests/test_ticket_work_and_
land_finish.py::TestLandParityFindings.test_parity_with_the_land_sweeps_own_exemption_function`
pins that `land_parity_findings`'s output on a fixed raw finding set is
byte-identical to calling `_drop_checkpoint_exempt_findings` directly
against that same set.

## `frob ticket evidence --replace` (T-1537)

<!-- frob:describes src/frob/tickets/_evidence.py::replace_evidence -->

A renamed or parametrized test that was already bound as ticket evidence
used to orphan the binding -- `frob ticket land` would refuse ("evidence
no longer resolves post-merge") with no CLI remedy; the coordinator had
to hand-edit via `write_ticket` directly, twice, on 2026-08-04 (the T-1520
parametrization incident this ticket closes). `frob ticket evidence <id>
--replace OLD-NODE-ID NEW-NODE-ID` rebinds one evidence id everywhere it
appears -- the flat `ticket.evidence` list AND every acceptance
criterion's own `evidence` tuple -- in a SINGLE atomic `write_ticket`
call (`replace_evidence`, the same single-writer path every other
evidence mutation already uses, never a second ad hoc write; the append
and the acceptance rebind can never be split across two writes, mirroring
`_append_evidence_and_write`'s own "no partial state" guarantee).

`NEW-NODE-ID` is held to the exact same bar a fresh `--evidence` id is:
schema-validated, resolved against the collected pytest/rust node id set,
and required to have actually PASSED on the CLI's own verification run
(the same `_verify_ids_passing` oracle `_apply_evidence` uses) -- a
`--replace` can never let an unresolved or currently-failing id sneak in
just because it is nominally a rename rather than an addition.
`OLD-NODE-ID` must be present in EITHER the flat evidence list or at
least one acceptance criterion's evidence -- `Err(EvidenceReplaceNotFound)`
otherwise, a typo'd source id is never a silent no-op. `OLD-NODE-ID ==
NEW-NODE-ID` (after the same dot-to-`::` normalization every evidence id
goes through) is itself a no-op SUCCESS -- nothing to replace is not a
failure.

`--replace` composes with the positional node-id list and `--evidence-cmd`
in one `frob ticket evidence` invocation (all three modes can fire in the
same call; the command only refuses when NONE of the three is given).

<!-- frob:waive DOC006 reason="the prose itself discloses 'frob refactor rename' as a separate, not-yet-built ticket -- it names a future command, not a live one" -->
Disclosed follow-up (this ticket's own body): `frob refactor rename`
detecting a bound-evidence reference and offering the `--replace` rebind
automatically is a separate, not-yet-built ticket -- this ships the CLI
primitive that follow-up would call, not the detection.

### `--archived` (T-1561)

<!-- frob:describes src/frob/tickets/_store.py::write_archived_ticket -->

`--replace`'s load/write path (`_load_one`/`write_ticket`) only ever
sees ACTIVE storage -- an already-archived ticket resolves to
`Err(NotFound)`, even though COV003 still scans `tickets-archive.md`/
`tickets/archive/**` for stale evidence bindings on it. This is the
2026-08-05 incident T-1561 closes: COV003 fired on archived T-1269/
T-1495 after their bound tests were renamed by wave-4 unwind-semantics
work, `evidence --replace` answered `NotFound`, and the coordinator
worked around it with a raw string swap directly in
`tickets-archive.md` -- exactly the hand-edit-the-ledger hazard the
`frob ticket` CLI exists to make unnecessary.

`frob ticket evidence <id> --replace OLD NEW --archived` retargets both
halves at archive storage: `ticket_id` is loaded via `load_archive`
instead of `_load_one`, and the rebound ticket is written back via
`write_archived_ticket` (the archive-side analog of `write_ticket`)
instead of `write_ticket` -- so the repair lands in the archive, never
resurrecting the ticket into active storage as a side effect.
`write_archived_ticket` mirrors `write_ticket`'s own per-mode shape: v2
mode writes under `tickets/archive/T-####/ticket.md` via the per-ticket
`ticket_lock`; single mode splices into `tickets-archive.md`'s raw text
(`_splice_ticket_section`) under the SAME T-1536 post-splice integrity
check (`_post_splice_integrity_check`) `write_ticket` already holds for
the active ledger, so a repair can never itself corrupt a sibling
archived ticket.

```python
# frob/tickets/_store.py
def write_archived_ticket(root: Path, ticket: Ticket) -> Result[None, TicketError]
    # Upsert ONE ticket into ARCHIVE storage -- the archive-side analog
    # of write_ticket, which only ever writes to ACTIVE storage.
```

