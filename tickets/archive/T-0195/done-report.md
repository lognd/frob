## Done report

Changed:
- src/frob/dup/_template.py (new) -- `build_group_template`, `_region_tree`,
  `_children_of`, `_render_subtree`, `_render_skeleton`, `_member_key`,
  `_distinct_members`
- src/frob/dup/_models.py -- new `CloneBinding`, `CloneTemplate`,
  `CloneMatchGroup` frozen pydantic models; `CloneReport.groups` retyped
  from `tuple[tuple[ClonePair, ...], ...]` to `tuple[CloneMatchGroup, ...]`
- src/frob/dup/_pipeline.py -- `_clone_report` now wraps each rung group in
  a `CloneMatchGroup` with `template=build_group_template(state.root, group)`
- src/frob/dup/_rules.py -- `DUP001`/`DUP002` updated for `group.pairs`
  (was `group` directly); new `_extraction_hint`, `_dup001_message` helpers;
  DUP001's message gains `; candidate extraction: <suggested_signature>`
  whenever `group.template` is not `None`
- src/frob/dup/__init__.py -- re-exports `CloneBinding`, `CloneMatchGroup`,
  `CloneTemplate`, `build_group_template`
- tests/unit/test_dup_template.py (new) -- `TestBuildGroupTemplate`, 5 cases
- tests/test_dup_smart.py, tests/test_dup_region.py, tests/test_dup_rungs.py
  -- `for p in group` -> `for p in group.pairs` (CloneReport.groups shape
  change)
- docs/modules/dup.md -- new "Reverse-templating report" section (fold
  algorithm, per-member binding-recovery algorithm, the documented
  skeleton-not-literal-source limitation); Public API code block updated
  for `CloneMatchGroup`/`CloneBinding`/`CloneTemplate`/`build_group_template`;
  Gate integration section updated for DUP001's new message shape;
  `frob:describes` anchors added for all four new symbols

**Model naming**: the survey sketch named the new group wrapper
`CloneGroup`, but `frob.dup._legacy.CloneGroup` (Type-1/2 scanner output,
already re-exported from `frob.dup.__init__`) already owns that name --
named the new type `CloneMatchGroup` instead to avoid a real collision on
`frob.dup.__init__`'s export surface, keeping the legacy symbol unchanged.

**Multi-member groups**: NOT limited to the 2-member case. `build_group_template`
collects every distinct `CloneRegion` referenced across a group's `ClonePair`s
and folds Plotkin lgg incrementally (member_0 lgg member_1, that result lgg
member_2, ...) -- correct because `$hole_N` placeholder labels never collide
with a real node label, so folding a hole against real structure keeps it a
hole. Per-member bindings are recovered by re-anti-unifying the final folded
template against each member individually; hole ids line up identically
across every member because the folded template's shared-node structure and
preorder walk order are the same on every call. Verified directly:
`test_three_member_group_folds_to_one_shared_skeleton` builds a 3-member
group (three files differing only in one integer literal) and asserts a
single shared hole (`holes == (0,)`), one binding tuple per member, all
three literals recovered (`{"1","2","3"}`), and all three bindings naming
the same hole id.

**Report format**: `CloneTemplate.skeleton_text` is a `label(child, child,
...)` rendering of the anti-unified `(labels, parents)` node array with
`$hole_N` at each divergence point (e.g.
`function_definition(def, f, parameters((, x, )), :, block(return_statement(return,
binary_operator(x, +, $hole_0))))`); `CloneBinding.source_text` renders the
same way for the concrete subtree each hole binds to on that member
(`"1"`, `"2"`); `CloneTemplate.suggested_signature` is
`def _extracted(hole_0, ...): ...`, one parameter per distinct hole ordered
by hole id (preorder-of-first-divergence). Verified against the real DUP001
gate path end to end (not just the unit tests) with a manual `dup_gate`
call over a planted alpha-renamed clone: message came back as
`"src/a.py::compute_total duplicates pre-existing src/a.py::compute_sum
(95% similar, rung=r2); candidate extraction: def _extracted(hole_0,
hole_1, hole_2, hole_3, hole_4): ...; extract into a shared helper or
waive with: frob:waive DUP001 reason=\"...\""`.

**Cut, filed as follow-up (not this ticket's scope)**: `source_text` and
`skeleton_text` are structural label renderings, not literal source
characters, and `suggested_signature` never reuses a real identifier name
even when both instances agree on one (the survey's "reuse the identifier
when both instances agree" nicety) -- both need `frob.lang.TreeNode` to
carry a source span/text, which it does not today, and `frob.lang/**` is
outside this ticket's declared scope (`src/frob/dup/**`). Not Filed
T-draft-73900a9e (never refiled) ("frob.lang.TreeNode: carry source span/text for
reverse-templating literal source text", scope `src/frob/lang/**`); this
is a provisional id minted off the default branch (worktree branch, not
`main`) per `frob ticket new`'s off-default-branch behavior -- resolves to
a real T-#### id once landed. Documented plainly in
docs/modules/dup.md's new section rather than left silent.

Evidence (7 ids, `frob ticket evidence T-0195 ...`):
`tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_one_leaf_divergence_yields_one_hole_with_both_sides`,
`::test_identical_bodies_yield_zero_holes`,
`::test_three_member_group_folds_to_one_shared_skeleton`,
`::test_single_member_returns_none`,
`::test_unrecoverable_subtree_returns_none_not_raises`,
`tests/test_dup_smart.py::TestGateRules::test_dup001_fires_when_one_side_touched`,
`::test_dup002_fires_when_both_sides_touched`.

Test runs (all observed): one combined `uv run pytest
tests/unit/test_dup_template.py tests/test_dup_smart.py
tests/test_dup_region.py tests/test_dup_rungs.py tests/unit/test_dup_core.py
tests/test_gates.py tests/test_excludes.py tests/unit/test_dup.py -q` run,
cross-checked against `--collect-only -q`'s per-file counts (5 + 8 + 4 + 12
+ 20 + 138 + 5 + 16 = 208): 208 dots, all `.` (no `F`/`E`), 0 failures --
`tests/test_excludes.py`/`tests/unit/test_dup.py` (the legacy
`find_duplicates` surface) confirmed untouched by the `CloneReport.groups`
shape change in the same run.
`uv run pytest --collect-only -q`: clean, no collection errors (`make
core` ran first in this worktree's own `.venv` -- it had NOT inherited
natives from the parent checkout, confirmed by a `ModuleNotFoundError`-free
rebuild).

Gates: `uv run frob check --ticket T-0195` -> 8 errors, 8 warnings both
before and after this change (`git stash`-isolated comparison, playbook
sec 6) -- diffed line-by-line (`diff base_errs.txt mine_errs.txt`) and the
only difference found mid-pass was one NEW `ARCH001` on `DUP001` (33 lines,
threshold 30) from the extraction-hint wiring; fixed by extracting
`_dup001_message` as a helper, re-diffed clean (zero differences from the
pre-change baseline). All 8 baseline errors (2x COV003 on T-0214's stale
evidence ids, 5x TEST001 on `src/frob/app/_style.py`, 1x REL001 already
pending "major" bump since 0.10.0) are pre-existing and unrelated to this
ticket's scope -- confirmed identical on both sides of the stash boundary.
One new WARNING (`docs/modules/dup.md` crossed the 500-line `large-file`
threshold, 613 lines) -- warn severity, not blocking, same category
already present on 5 other `docs/modules/*.md` files pre-existing in this
repo (`gates.md` at 603, `vet.md` at 997, etc.) -- not fixed, noted here
per the honesty rule rather than silently landing without mention.
`ruff check`/`ruff format --check` clean under both `uv run ruff` and the
bare PATH `ruff` binary. `ty check src/frob/dup/` clean.
`git diff main --diff-filter=D --stat`: empty (no unintended deletions).
`uv run frob test --base main`: python exit=0 (2.58s), touched-set
selection picked up all 5 new `test_dup_template.py` cases plus the three
modified `.groups`-shape test files plus the existing DUP gate test.

Not Filed: T-draft-73900a9e (never refiled) (see "Cut, filed as follow-up" above).

Not closing per the agent playbook (review-gated flow) -- ticket left
`in-progress` (`frob ticket start` ran in this worktree's own checkout,
correcting an earlier mistaken invocation against the parent checkout
outside the worktree); reviewer closes.
