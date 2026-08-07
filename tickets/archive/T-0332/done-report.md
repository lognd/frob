## Done report

Implemented `frob.arch._patterns` (T-0332): an advisory design-pattern
recommender mapping structural HALLMARKs to recommended PATTERNs and
detected ANTI-PATTERNs to ESCAPE routes, surfaced via two new
`ArchSuggestion` categories (`pattern-recommendation`,
`anti-pattern-escape`), both `severity="suggestion"` on the existing
unwaivable advisory channel -- never build-blocking.

7 of the plan's 13 registry rows shipped with real, precision-checked
tree-sitter detectors requiring a >=3-occurrence structural signal each:
type-switch->Strategy, state-field-chain->State machine,
telescoping-ctor->Builder, scattered-construction->Factory/DI,
wrap-delegate->Decorator, god-object->SRP decompose (paired with the
existing god-class finding, no re-walk), stringly-typed->newtype.

## Reviewer round 2 (rejected close, code approved)

1. Merged `main` (T-0385 registry reconciliation for patterns.yaml
   landed, plus the real follow-up ticket T-0605 replacing my
   T-draft-4fb8deee, which does not survive land per T-0577).

2. Re-dispositioned all 41 `deferred:T-0332` rows in
   `docs/design/registry/patterns.yaml`. Investigated whether any could
   honestly become `handled_by:<rule>`: the 41 rows are DDD tactical
   patterns (9: Layered Architecture, Entities, Value Objects, Domain
   Events, Services, Modules, Aggregates, Repositories, Factories),
   Release-It resilience patterns (24: circuit breaker, bulkhead,
   timeouts, backpressure, cascading failures, etc.), and Python idioms
   (8: context manager, descriptor protocol, duck typing, iterator
   protocol, decorator syntax, sentinel object, mixin, dataclass) -- none
   are the structural code-smell hallmarks my 7 shipped detectors target.
   Tried the closest nominal match (`DDD-II-FACTORIES` ->
   `handled_by:scattered-construction`) against the real gate
   (`registry_gate`/REG002): it fails, because `handled_by:<target>` is
   verified against the LIVE gate/policy rule-id registry
   (`known_gate_rule_ids()` union policy rules) via
   `_classify_handled_by`, and `frob.arch`'s advisory pattern-recommender
   rule ids (`type-switch`, `scattered-construction`, etc.) are not
   registered gate/policy rules -- only `ArchSuggestion` categories on the
   unwaivable channel, not `Violation` rule ids. Confirmed empirically:
   setting that disposition and running
   `tests/test_registry_reconciliation_patterns.py` produces a real
   REG002 ERROR ("names a rule that does not exist in the live
   gate/policy rule registry"). Registering `frob.arch`'s pattern rule
   ids as gate/policy rules would require editing `src/frob/gates/
   __init__.py`'s `_KNOWN_GATE_RULES` (or a policy pack), which is outside
   this ticket's scope and a nontrivial design decision on its own (noted
   for whoever picks up T-0605 or a further ticket, not silently
   assumed). Result: **0 entries re-dispositioned to `handled_by`, all 41
   re-dispositioned to `deferred:T-0605`** (T-0605 is real, queued,
   scoped to exactly this handoff). `docs/design/registry/patterns.yaml`
   added to this ticket's scope (`frob ticket scope --add`) since it was
   genuinely touched.

3. `uv run pytest tests/test_registry_reconciliation_patterns.py
   tests/unit/test_arch.py -p no:cacheprovider -q`: 61 passed (7 + 54).

4. Closed the reviewer's precision-test gap: added 3 near-miss
   (stays-silent) tests for the 3 detectors that previously only had
   fires-tests: `test_non_state_attribute_chain_not_flagged_state_machine`
   (a `self.<attr>` elif chain with no state/status/mode/phase/stage name
   hint must not recommend State machine), `test_two_method_delegating_
   wrapper_not_flagged_decorator` (2 pass-through methods, below the
   `_MIN_DELEGATE_METHODS=3` floor, must not recommend Decorator), and
   `test_class_at_threshold_not_flagged_god_object` (a class at exactly
   the default `max_class_methods=12` must not fire god-class, so its
   paired SRP-decompose escape must not fire either).

5. `frob check --ticket T-0332` / `--delta`: 0 errors except `REL001`
   (version bump needed since 0.73.0 -- a release/land-time
   responsibility per this repo's convention, `pyproject.toml` outside
   this ticket's scope). Deletion-filter
   (`git diff main --diff-filter=D --stat`) is empty against the current
   `main` (merge-base equals `main`'s tip). Evidence refreshed to 15
   node ids (12 original + 3 new near-miss tests).

Handoff: T-0605 ("design-pattern recommender phase 2") now owns all 41
re-dispositioned rows plus the 6 detector rows T-0332 deferred in round 1
(Adapter, Flyweight/pool, Observer, anemic-domain-model, poltergeist/
lava-flow, sequential-coupling) -- its own scope already includes
`docs/design/registry/patterns.yaml` for re-dispositioning as it ships
each new detector.

### Changed
```
 docs/modules/arch.md       |  83 ++++++
 src/frob/arch/__init__.py  |  59 +++-
 src/frob/arch/_models.py   |   8 +
 src/frob/arch/_patterns.py | 701 +++++++++++++++++++++++++++++++++++++++++++++
 tests/unit/test_arch.py    | 195 +++++++++++++
 tickets.md                 | 121 +++++++-
 6 files changed, 1147 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestPatternRecommender::test_isinstance_chain_recommends_strategy` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_state_field_chain_recommends_state_machine` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_telescoping_ctor_recommends_builder` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_scattered_construction_across_files_recommends_factory` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_wrap_delegate_recommends_decorator` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_god_class_pairs_with_srp_escape` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_stringly_typed_recommends_newtype` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_two_arm_isinstance_chain_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_normal_ctor_not_flagged_as_telescoping` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_construction_in_two_files_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_short_string_chain_not_flagged_stringly_typed` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_simple_python_no_pattern_recommendations` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_non_state_attribute_chain_not_flagged_state_machine` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_two_method_delegating_wrapper_not_flagged_decorator` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_class_at_threshold_not_flagged_god_object` (pytest node id, verified passing when recorded)
