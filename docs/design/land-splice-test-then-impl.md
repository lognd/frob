# Land splice: tests-first then implementation (T-3546)

Owner's bar: `frob ticket land` should publish substantial, readable
history -- ideally a `test(...)` commit (red by construction where a
genuine repro exists) followed by a `feat`/`fix(...)` commit that turns
it green, rather than today's single squash. This document designs that
split against the T-3053/T-3088/T-3089 out-of-tree compose + CAS-publish
model already live in `frob.tickets._land_compose`
(`compose_tree_out_of_tree`/`publish_ref_cas`/`fold_worktree_into_commit`)
and `_land_squash.py`'s `_fold_publish_and_resync`.

## Why this is safe to build on top of the existing primitive

`compose_tree_out_of_tree`/`fold_worktree_into_commit` already build a
commit object entirely against a scratch `GIT_INDEX_FILE` or a disposable
worktree, parented on an explicit base sha, without touching `root`'s
checked-out tree or `HEAD`. Composing a SECOND commit the same way,
parented on the FIRST composed commit's own sha (not on `root`'s tree at
all), costs nothing extra in git-plumbing terms -- `git commit-tree` only
ever needs a tree object and a parent sha, neither of which requires a
checkout. The publish step stays exactly what it is today: **one**
`publish_ref_cas(root, ref, pre_land_tip, final_sha)` compare-and-swap,
moving `refs/heads/<main>` directly from the OLD tip to the LAST composed
commit. A sibling land's CAS races against this exact same pair
(`pre_land_tip`, `final_sha`) it always raced against -- the intermediate
test-only commit is never itself a CAS target, never independently
published, and never observable mid-flight. This is the load-bearing
property that makes the whole design safe: **splitting one commit into
N never changes how many ref moves happen, and it stays exactly one.**

## The split algorithm

1. Compute the ticket's full changed-path set the same way
   `_worktree_full_changeset`/`fold_worktree_into_commit` already do
   (the disposable worktree's own diff against `pre_land_tip`).
2. Classify each changed path as TEST (matches this repo's own test-path
   convention: under a `tests` path segment, or named `test_*`/`*_test.py`
   -- the SAME heuristic `frob.gates._is_test_path` already applies for
   doc-obligation exemption, not a second independently-invented rule)
   or IMPL (everything else).
3. **Clean-split precondition** (mechanical, no guessing): the split
   proceeds ONLY when BOTH groups are non-empty. Zero TEST paths (a pure
   docs/chore/refactor ticket, or a bug ticket that waived BUG002/T-1616
   with no test changes) or zero IMPL paths (a test-only follow-up
   ticket, e.g. a coverage-drain ticket) has no meaningful "tests-first"
   story to tell -- there is nothing on one side of the split. Fall back
   to today's single squash, unchanged, in either case. **Never** force
   a split by moving a file across the boundary or by guessing which
   half of a mixed-concern file belongs where -- file-level classification
   by path is unambiguous by construction (a path is or is not under
   `tests/**`), so there is no "ambiguous file" case to handle; the ONLY
   fallback trigger is one side being empty.
4. Compose commit 1: `git diff pre_land_tip stage -- <TEST paths>`
   applied via the SAME `git apply --cached` scratch-index mechanism
   `compose_tree_out_of_tree` already uses, parented on `pre_land_tip`.
   Message: `test(<scope>): <ticket's own test summary>`.
5. Compose commit 2: `git diff pre_land_tip stage -- <IMPL paths>`
   applied on top of commit 1's OWN tree (via `git read-tree
   <commit-1-sha>` into the scratch index, not `pre_land_tip` again),
   parented on commit 1. Message: today's existing squash message
   (`feat`/`fix(<scope>): ...`).
6. (Optional, unchanged from today) a third `chore: ...` commit for
   ledger/doc residue the land pipeline itself adds (T-2220's land_commit
   record, release-bump fragments) -- these already compose as a SEPARATE
   commit today (`_compose_and_publish_land_commit_record`), so no new
   mechanism is needed for step 3; it simply chains onto commit 2 instead
   of onto today's single squash commit.
7. Publish: **one** `publish_ref_cas(root, ref, pre_land_tip, commit-2-sha)`.
   commit 1 is never a CAS target -- it becomes visible to the world only
   as an ancestor of the published tip, atomically, in the same instant
   commit 2 becomes reachable.

## Consequence 1: `--check-repro` becomes verifiable post-land

Today's gap (`docs/modules/tickets.md#check-repro-post-land-limitation-
t-2025`, `TEST_ABSENT_AT_PARENT`): a squash commit contains the test and
its fix atomically, so no ref in main's history ever holds the test
WITHOUT the fix -- `bug_repro_outcome_at_ref` run against any ref in
main's history collects zero items for a newly-added test's node id.

With the split, commit 1's own sha genuinely holds the test with the fix
NOT yet applied -- exactly the state `bug_repro_outcome_at_ref` needs. No
new `Ticket` field or dedicated bookkeeping commit is needed to find it:
T-3543 already removed the old T-2220 second-commit-records-the-sha
mechanism in favor of `derive_land_commit_by_grep`, deriving the landing
sha from the commit history's own subject line
(`f"{commit_type}(tickets): land {final_id} {title}"`) instead. This
design reuses that exact convention for commit 1's own subject --
`f"test({scope}): land {final_id} tests for {title}"` -- so `git log
--grep="land {final_id} " --fixed-strings` against `ref`'s history
resolves BOTH commits by the same literal-substring match
`derive_land_commit_by_grep` already performs, oldest-first ordering
distinguishing "test" from the `feat`/`fix` commit that follows it. `frob
ticket evidence <id> --check-repro` resolves `parent_ref` to the OLDER of
the two matches when exactly two exist for `final_id`, falling back to
today's merge-base-against-`--base-ref` resolution when only one match
(or none) exists -- single-squash tickets, or tickets landed before this
feature, are unaffected. `TEST_ABSENT_AT_PARENT`'s own error message
keeps its unconditional "retroactive post-land verification ... is not
achievable" claim ONLY for the single-match/no-match case -- it becomes
false, and the message must be corrected, for any ticket that landed
split.

## Consequence 2: the bisect story

A `git bisect` walk that lands exactly on commit 1 sees a red test suite
by construction -- this is not a regression bisect is meant to find, it
is the ticket's OWN test intentionally failing one commit before its own
fix. Two complementary mitigations, both mechanical:

- **Commit trailer**: every commit 1 carries a trailer line,
  `Land-Splice-Role: test-before-fix`, and every commit 2 carries `Land-
  Splice-Role: implementation`. `git log --grep`/`git show -s --format`
  can filter on this without any new git feature.
- **`git bisect run` guidance** (documented, not enforced): a bisect
  script should treat a commit whose trailer reads `test-before-fix` as
  `git bisect skip`, not a pass/fail verdict -- this repo's own `docs/
  guides/` should gain a short recipe (`git log -1 --format=%B | grep -q
  "Land-Splice-Role: test-before-fix" && exit 125` as the skip-exit
  convention `git bisect run` already recognizes). A plain interactive
  `git bisect` (no `run` script) surfaces the trailer in `git show`'s
  own output, which is enough for a human to recognize and `git bisect
  skip` by hand.

This is a documentation-only mitigation deliberately -- there is no way
to make a genuinely-red intermediate commit report green without either
skipping the test (defeating the entire point of landing it red) or
special-casing bisect's own pass/fail interpretation (out of scope, and
not something a downstream repo consuming this history could rely on
without also adopting the trailer convention).

## Consequence 3: CI-on-main semantics

No change needed. GitHub Actions' `on: push` trigger fires once per ref
UPDATE event, not once per commit reachable from that update -- today's
land already CAS-publishes straight from `pre_land_tip` to the final
tip in one `update-ref`, and CI has never seen (nor needed to see) the
intermediate git objects that existed only in the disposable worktree
before that single ref move. Splitting the SAME ref move into a two- or
three-commit chain changes nothing about how many pushes reach GitHub --
still exactly one, still only ever observing the final tip. The
intermediate red test-only commit is real, permanent git history, but it
is never independently pushed as its own ref update, so CI never runs
against it and was never expected to.

## Consequence 4: fallback to single squash

Per the split-algorithm's step 3 precondition, fallback is automatic and
silent-but-logged whenever either group is empty. No `frob:` directive
or ticket-body opt-out is needed for the common case; a ticket owner who
wants a split forced against the algorithm's own judgment is out of this
design's scope (T-1616's own "never force a fabricated split" doctrine
mirrors this ticket's identical instruction).

## Rollout plan (T-3550 precedent: design first, implementation gated)

This document is the design-only deliverable. The actual wiring into
`_fold_publish_and_resync`/`_publish_squash_apply` touches the single
highest-incident-density code path in this repo (T-3066, T-3114, T-3121,
T-3163 all root-caused in this exact function family) -- landing it in
the same pass as the design, against a live fleet mid-land, is the kind
of risk this repo's own precedent (T-3550 -> a design ticket, then a
SEPARATE implementation ticket blocked by owner sign-off) exists to
avoid. The mechanical, UNWIRED primitives this ticket lands
(`classify_test_then_impl_paths`/`compose_test_then_impl_commits` in
`frob.tickets._land_squash`, proven against a scratch repo, called from
NOTHING in the live land path yet -- the same "prove the primitive in
isolation, wire it later" shape `_land_compose.py`'s own module
docstring describes for T-3088/T-3089) are the T-3550-style safe slice;
the wiring itself is filed as its own ticket, blocked on this document's
owner sign-off.
