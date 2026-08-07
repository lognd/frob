## Done report

Resolved all 6 T-0332-deferred registry rows on their own merits instead
of shipping a uniform "fuzzier signal" pass, per the ticket's own noise
mandate (an imprecise recommender trains users to ignore the advisory
channel -- worse than honest silence).

## Per-pattern decision

1. **Adapter** (`incompatible-interface-bridging`) -- SHIPPED a real
   detector, `_check_interface_translate` (rule id `interface-translate`).
   Reuses `wrap-delegate`'s "stores one constructor-param object as
   `self.<attr>`" shape but requires the OPPOSITE call-name relationship:
   >=3 methods whose entire body is a single call to a DIFFERENTLY-named
   method on the inner object (vs `wrap-delegate`'s same-name pass-
   through -> Decorator). The two hallmarks are disjoint PER-METHOD ONLY
   (a same-name delegating method can never also count as a translating
   one) -- NOT per-class. See "Reviewer round 1" below: a class mixing
   both shapes legitimately fires both recommendations.

2. **Flyweight/pool** (`expensive-object-reuse`) -- NOT-CHECKABLE,
   disposition unchanged (`GOF-FLYWEIGHT` stays `out_of_scope:advisory-
   design-pattern-recommendation`, already correct). No single-file
   structural signal distinguishes "expensive to construct, should be
   shared/pooled" from an ordinary loop building N legitimately
   different objects without value/dataflow analysis this package does
   not have.

3. **Observer** (`manual-callback-list`) -- SHIPPED a real detector,
   `_check_manual_callback_list` (rule id `manual-callback-list`).
   Requires THREE co-occurring structural facts in one class: an empty-
   list attribute initialized in `__init__`, a DISTINCT method that
   appends to it, and a DISTINCT method that iterates it calling each
   element -- the register/notify shape a hand-rolled Observer always
   has. Neither fact alone (plain accumulator list, or iterate-and-call
   over a list nothing appends to) fires.

4. **Anemic domain model** (`anemic-domain-model`) -- SHIPPED a real
   detector, `_check_anemic_accessors` (rule id `anemic-accessors`, an
   `anti-pattern-escape`). Requires >=3 non-`__init__`, non-dunder
   methods where EVERY one is a trivial single-statement getter (`return
   self.<attr>`) or setter (`self.<attr> = <param>`) -- one real method
   with actual logic anywhere disqualifies the whole class.

5. **Poltergeist/lava-flow** -- NOT-CHECKABLE, disposition unchanged
   (`PAT-TRAP-20-ANEMIC-DOMAIN-GOD-OBJECT-LAVA-FLOW` stays `out_of_scope:
   advisory-design-pattern-recommendation`, already correct).
   `docs/design/architecture-check-catalog.md` itself notes poltergeist
   is "dup of Middle Man, at extreme" -- its degenerate case is not
   distinguishable from a small, well-designed wrapper without knowing
   whether the class is load-bearing elsewhere, and lava-flow ("nobody
   dares remove it") needs whole-program reachability/usage evidence
   (dead-code/call-graph analysis), a different kind of analysis this
   per-file structural walk does not do.

6. **Sequential coupling** -- NOT-CHECKABLE, no registry row change
   needed (no dedicated `patterns.yaml` row for this hallmark beyond the
   combined PAT-TRAP-20 row above; `ACC-4-SEQUENTIAL-COUPLING` lives in
   `arch-checks.yaml`, `deferred:T-0391`, outside this ticket's scope --
   `docs/design/registry/patterns.yaml` is the file in scope here). The
   catalog notes it is "dup of Connascence of Execution"; the closest
   structural proxy (a private flag set by one method, checked-and-
   raised by another) is indistinguishable from ordinary guard-clause
   precondition validation without tracking real call-order violations
   across callers -- a call-graph-class investment, not a bigger
   detector.

## Registry disposition note

Verified (as T-0332's round-2 Done report already established) that
`docs/design/registry/patterns.yaml`'s disposition tracks whether a row
is subject to enforceable GATE tracking, not whether `frob.arch` happens
to implement an advisory recommender for its hallmark -- a GoF/trap
catalog entry is inherently advisory-only either way. `GOF-STRATEGY`
(T-0332, detector shipped) and `GOF-ADAPTER` (T-0605, detector shipped
this ticket) carry the IDENTICAL `out_of_scope:advisory-design-pattern-
recommendation` disposition, confirming no yaml edit was needed for the
3 shipped rows either. No `docs/design/registry/patterns.yaml` changes
were required by this ticket's own resolution; the file remains in
scope and was read/verified, not blindly skipped.

## Reviewer round 1 (REJECT, one finding)

The reviewer's precision/noise verification over `src/frob/**` and every
near-miss/disposition/registry-precedent claim came back sound. One real
finding: the module docstring, `_check_interface_translate`'s docstring,
and this Done report's original "structurally disjoint per-method, so a
class cannot double-fire both" claim was FALSE at class level -- the
reviewer constructed a class with 3 same-name pass-through methods PLUS 3
differently-named translating methods on one `self._inner`, and
`analyze_project` fires BOTH `wrap-delegate` (Decorator) and
`interface-translate` (Adapter) on it.

Decision: option (a) -- correct the claim rather than add mutual
exclusion. Disjointness genuinely only ever held PER-METHOD (a single
method can never satisfy both the same-name and differently-named
conditions at once); it was never a per-class guarantee, and the
original prose overstated it. A class mixing both method shapes has two
independently true structural facts about two disjoint method subsets --
recommending Decorator for the pass-through subset AND Adapter for the
translating subset is not a contradiction, it is two correct, narrowly-
scoped suggestions. Suppressing one would throw away a true finding for
no real benefit (STRONG-HALLMARK-ONLY already prevents noise; this is
not noise, it is two true things about disjoint code).

Fixed:
- `frob.arch._patterns` module docstring and `_check_interface_translate`
  docstring rewritten to state disjointness is per-method only, and both
  now point at the new pinning test.
- `docs/modules/arch.md`'s registry table section gained the same
  correction paragraph.
- Added `test_mixed_delegate_and_translate_methods_fires_both`: the
  reviewer's exact construction (3 same-name pass-throughs + 3
  translating methods on one `self._inner`), asserting BOTH `Decorator`
  and `Adapter` suggestions fire -- pinned as intentional, accepted
  behavior, not a regression to fix later.
- Re-ran `tests/unit/test_arch.py` + `tests/test_registry_reconciliation_
  patterns.py` (147 passed, was 146), `ruff check`/`ruff format --check`
  (clean, both PATH and `uv run` ruff), and the full chunked `--only`
  gate loop (`lint`, `static`, `gates-fast`, `gates-native`, `gates-
  security`) -- 0 errors in every group, `gate:ARCH` still passes (the
  dual-fire is two advisory suggestions on the unwaivable channel, never
  a gate error). `git diff main --diff-filter=D --stat` still empty.
- Recorded the new test as evidence (`frob ticket evidence T-0605
  tests/unit/test_arch.py::TestPatternRecommender::
  test_mixed_delegate_and_translate_methods_fires_both --accepts 0`,
  bound to the ticket's single UNBOUND acceptance criterion).

## Evidence

- `tests/unit/test_arch.py::TestPatternRecommender::test_translating_wrapper_recommends_adapter` (fires)
- `tests/unit/test_arch.py::TestPatternRecommender::test_same_name_wrapper_not_flagged_adapter` (near-miss: same-name -> wrap-delegate/Decorator territory, disjointness proof)
- `tests/unit/test_arch.py::TestPatternRecommender::test_two_translating_methods_not_flagged_adapter` (near-miss: below floor)
- `tests/unit/test_arch.py::TestPatternRecommender::test_manual_callback_list_recommends_observer` (fires)
- `tests/unit/test_arch.py::TestPatternRecommender::test_append_only_list_not_flagged_observer` (near-miss: append with no notify loop)
- `tests/unit/test_arch.py::TestPatternRecommender::test_iterate_without_append_not_flagged_observer` (near-miss: notify loop with no append)
- `tests/unit/test_arch.py::TestPatternRecommender::test_anemic_accessors_recommends_move_behavior` (fires)
- `tests/unit/test_arch.py::TestPatternRecommender::test_class_with_real_method_not_flagged_anemic` (near-miss: one real method disqualifies)
- `tests/unit/test_arch.py::TestPatternRecommender::test_two_accessor_class_not_flagged_anemic` (near-miss: below floor)
- `tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations` (reconciliation pin test, kept green)
- `tests/unit/test_arch.py::TestPatternRecommender::test_mixed_delegate_and_translate_methods_fires_both` (reviewer round 1 pin: legitimate dual-fire is intentional, not a bug)

`uv run pytest tests/unit/test_arch.py tests/test_registry_reconciliation_patterns.py -q -o addopts=""`:
147 passed (post-review-round-1; was 146 pre-round-1).

## Gates

`uv run frob ticket sweep T-0605` refreshed (PRE gate was stale after
mid-ticket edits, re-swept clean). Chunked `--only` loop, all groups:
- `lint`: 0 errors, 1 warning (pre-existing `ruff-format` debt in
  `tests/test_ticket_land.py`, outside this ticket's scope)
- `static`: 0 errors (frob-exports warnings are all pre-existing,
  unrelated modules)
- `gates-fast`: 0 errors, 1118 warnings, 161 waived (pre-existing debt;
  `gate:ARCH` passes -- new `pattern-recommendation`/`anti-pattern-
  escape` findings from the 3 new detectors are advisory suggestions on
  the unwaivable channel, never gate errors)
- `gates-native`: 0 errors, 905 warnings, 35 waived
- `gates-security`: 0 errors, 894 warnings, 18 waived

`git diff main --diff-filter=D --stat`: empty.

## Deviations from plan

- No `docs/design/registry/patterns.yaml` edits: verified against
  T-0332's own established precedent (identical disposition on shipped
  vs unshipped rows) that none were needed; recorded the reasoning above
  and in `frob.arch._patterns`'s module docstring / `docs/modules/
  arch.md` instead of touching the registry file for cosmetic parity.
- `poltergeist`/`sequential-coupling` do not have their OWN dedicated
  `patterns.yaml` rows -- they are covered by the combined `PAT-TRAP-20`
  row (poltergeist+anemic+lava-flow) and by `arch-checks.yaml`'s
  `ACC-4-*` rows (deferred to T-0391, a different ticket, outside this
  ticket's `patterns.yaml`-only scope). Noted so this isn't silently
  read as ticket-scope creep into `arch-checks.yaml`.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-a17965924e60aad20

### Changed
```
 docs/modules/arch.md       |  60 ++++--
 src/frob/arch/__init__.py  |  14 +-
 src/frob/arch/_patterns.py | 470 ++++++++++++++++++++++++++++++++++++++++++++-
 tests/unit/test_arch.py    | 225 ++++++++++++++++++++++
 tickets.md                 | 159 ++++++++++++++-
 5 files changed, 900 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestPatternRecommender::test_translating_wrapper_recommends_adapter` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_same_name_wrapper_not_flagged_adapter` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_two_translating_methods_not_flagged_adapter` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_manual_callback_list_recommends_observer` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_append_only_list_not_flagged_observer` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_iterate_without_append_not_flagged_observer` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_anemic_accessors_recommends_move_behavior` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_class_with_real_method_not_flagged_anemic` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_two_accessor_class_not_flagged_anemic` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_mixed_delegate_and_translate_methods_fires_both` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 0 error(s), 1211 warning(s), 210 waived
