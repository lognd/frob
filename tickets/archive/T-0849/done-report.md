## Done report

T-0849 worked or dispositioned all 41 patterns.yaml rows T-0605 left pointed at deferred:T-0849 (9 DDD-II-*, 24 RELEASEIT-*, 8 PYIDIOM-*).

Two new real, precision-checked detectors shipped in src/frob/arch/_patterns.py, both PYIDIOM-* rows: dataclass-boilerplate (PYIDIOM-DATACLASS -> @dataclass, fires on an undecorated class whose ONLY member is an __init__ doing nothing but self.<attr> = <attr> for 3+ same-named params) and manual-decorator-wrap (PYIDIOM-DECORATOR-SYNTAX -> decorator syntax, fires on 3+ module-level def f(...) / f = wrapper(f) reassignment pairs in one file). Both wired into frob.arch.__init__'s python check pass, both documented in docs/modules/arch.md's design-pattern-registry table and a "T-0849 phase 3" narrative section, both carry fires + near-miss tests in tests/unit/test_arch.py::TestPatternRecommender.

Reviewer round 1 rejected the first pass for a real precision defect in dataclass-boilerplate: the class-body member scan only collected function_definition nodes, so a decorated extra method (a @property, @staticmethod, @classmethod, @cached_property, etc.) is a decorated_definition node and silently vanished from the extra-member count -- an __init__-only-looking class with an extra @property method wrongly fired "consider @dataclass" even though the detector's own docstring promised any extra method disqualifies the class. Fixed by collecting both function_definition and decorated_definition nodes as class members, only proceeding when there is exactly one member and it is a plain (undecorated) function_definition named __init__. Added the exact near-miss fixture the reviewer specified (__init__ with 3 param assignments plus a separate @property method) as test_dataclass_boilerplate_with_decorated_extra_method_not_flagged, and hand-verified it is load-bearing: reverting the member-collection filter back to function_definition-only made the new test fail with the false positive firing again, then restored the fix and reran the full TestPatternRecommender suite (36 tests) green.

Re-ran the noise measurement after the fix: dataclass-boilerplate still fires exactly once over src/frob/** (src/frob/vet/_osv.py's OsvAdvisory, the same genuine __slots__ value holder true positive as before), zero times over tests/**; manual-decorator-wrap fires zero times over both src/frob/** and tests/**.

I also hand-verified both original near-miss discriminators are load-bearing (from the prior round, unchanged by this fix): mutating dataclass-boilerplate's value.type != "identifier" check made test_dataclass_boilerplate_with_computed_field_not_flagged fail, and dropping manual-decorator-wrap's _MIN_MANUAL_DECORATOR_WRAPS floor to 1 made test_two_manual_decorator_wraps_not_flagged fail; both reverted.

Per-family disposition of the remaining 39 rows (all out_of_scope:advisory-design-pattern-recommendation, matching the T-0332/T-0605 precedent that pattern-recommendation/anti-pattern-escape rows stay on this disposition regardless of whether a detector exists, since findings are advisory-only and never gate-enforced): DDD-II-* (9 rows: Layered Architecture, Entities, Value Objects, Domain Events, Services, Modules, Aggregates, Repositories, Factories) are Evans's own building-block vocabulary, not a described structural hallmark -- "is this class actually an Entity vs. a Value Object vs. an Aggregate" is a domain-semantic judgment no single-file structural signal can answer without fabricating a claim, matching sibling DDD-I-*/DDD-III-* rows already out_of_scope in the same catalog. RELEASEIT-* (24 rows: 12 stability anti-patterns + 12 stability patterns -- timeouts, circuit breaker, bulkheads, chain reactions, cascading failures, dogpile, etc.) are runtime/distributed-systems properties observed under real network latency/failure/load across a running system, not a single-file structural shape any per-file AST walk in this package can see; RELEASEIT-PAT-TIMEOUTS' disposition comment cross-references strata's REL2xx timeout-obligation family at the concept level rather than inventing a duplicate weaker arch check. The remaining 6 PYIDIOM-* rows (Context Manager, Descriptor Protocol, Duck Typing Protocol, Iterator Protocol, Sentinel Object, Mixin) each carry their own specific structural-proxy-is-insufficient reason in the yaml comment.

Every one of the 41 rows' disposition line in docs/design/registry/patterns.yaml carries a one-line reasoned comment directly above it, following compliance.yaml's existing handled_by-comment convention.

tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_every_deferred_entry_targets_an_open_ticket previously asserted patterns.yaml must have at least one DEFERRED entry to check against; after this ticket resolved the last 41 deferred rows the file has zero DEFERRED entries, so that assertion is no longer true and was removed (the positive-case loop itself stays, exhaustive-but-empty until a future deferral reactivates it) -- documented in the test's own updated docstring.

Gates: uv run frob check --ticket T-0849, run chunked per docs/guides/agent-playbook.md section 3b's --only loop (lint, static, gates-fast, gates-native, gates-security) -- all 5 stage groups pass 0 errors both before and after the reviewer's fix. REG003/REG-family all pass for patterns.yaml (uv run pytest tests/test_registry_reconciliation_patterns.py -q: 7 passed). Full TestPatternRecommender suite: uv run pytest tests/unit/test_arch.py -k TestPatternRecommender -q: 36 passed. ruff check + ruff format clean under uv run ruff on every touched file. git diff main --diff-filter=D --stat is empty.

Scope was extended by one file, docs/modules/arch.md (frob ticket scope T-0849 --add), because the two new PATTERN_REGISTRY rows' frob:doc directives target that file's design-pattern-registry anchor, the same anchor every existing row's frob:doc directive already targets.

Mid-task ledger-drift incident (self-corrected, documented for the record): an earlier round's frob ticket scope/evidence calls ran against a tickets.md that had drifted from a concurrently-advancing main, producing a spurious T-0596 done->queued regression in the diff. Fixed per the agent playbook's section 10b recipe: git checkout main -- tickets.md, then re-ran frob ticket start/scope/sweep/evidence/done-report fresh on top of the restored ledger. Final git diff main -- tickets.md touches only T-0849's own block.

No blockers. No new tickets filed -- all 41 rows were genuinely resolvable within this ticket's own scope.

### Changed
```
 docs/design/registry/patterns.yaml             | 123 ++++++++-----
 docs/modules/arch.md                           |  78 ++++++++
 src/frob/arch/__init__.py                      |   2 +
 src/frob/arch/_patterns.py                     | 244 +++++++++++++++++++++++++
 tests/test_registry_reconciliation_patterns.py |  10 +-
 tests/unit/test_arch.py                        | 194 ++++++++++++++++++++
 tickets.md                                     |  97 +++++++++-
 7 files changed, 704 insertions(+), 44 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_recommends_dataclass` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_with_computed_field_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_with_extra_method_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_with_decorated_extra_method_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_already_dataclass_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_manual_decorator_wrap_recommends_decorator_syntax` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_two_manual_decorator_wraps_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPatternRecommender::test_decorator_syntax_wrap_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_declared_total_is_346` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 0 error(s), 1236 warning(s), 220 waived
- error-findings: none (measured, zero errors)
