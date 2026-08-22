## Done report

T-1629's SYS110 exemption frozenset covered 15/17 nodes with real drift (734 findings, measured at T-1629 time). Audited the smallest exempted node first (natives, a 3-entry interface= block): _load_audit_model + check_self_conformance with the exemption temporarily lifted (measurement only, not committed) found exactly 1 real finding -- CARGO_CACHE_DIRNAME, which is genuinely in the module's own __all__ and consumed by tests/unit/test_natives_build.py, so it belongs in interface= by hand-audited intent, not by regenerating a mirror. Added it by hand, removed natives from SYS110_UNAUDITED_NODES, re-measured: 0 findings for natives, 0 findings introduced anywhere else. 14 nodes remain exempted; each needs its own per-node audit in a follow-up pass -- this ticket demonstrates the process and clears the first (smallest) node rather than rushing all 15.

### Changed
```
 tickets/T-1981/ticket.md | 20 +++++++++++++++++++-
 1 file changed, 19 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_burn_down_shrinks_the_exemption_never_widens_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, DSL001@docs/commands/sys.md, DSL001@docs/design/coding-performance-corpus.md, DSL001@docs/design/cwe-1000-registry.md, DSL001@docs/design/design-pattern-traps-corpus.md, DSL001@docs/design/language-adapter-tier-decision.md, DSL001@docs/design/registry/RECONCILIATION.md, DSL001@docs/design/system-performance-corpus.md, DSL001@docs/guides/coordinator-scripts.md, DSL001@docs/guides/editors.md, DSL001@docs/guides/exhaustive-research.md, DSL001@docs/guides/install.md, DSL001@docs/modules/app.md, DSL001@docs/modules/arch.md, DSL001@docs/modules/bind.md, DSL001@docs/modules/clean.md, DSL001@docs/modules/cli.md, DSL001@docs/modules/cve.md, DSL001@docs/modules/decisions.md, DSL001@docs/modules/deploy.md, DSL001@docs/modules/dup-sota-survey.md, DSL001@docs/modules/dup.md, DSL001@docs/modules/fleet.md, DSL001@docs/modules/fuzz.md, DSL001@docs/modules/gates.md, DSL001@docs/modules/graph.md, DSL001@docs/modules/lang.md, DSL001@docs/modules/logging.md, DSL001@docs/modules/mutate.md, DSL001@docs/modules/perf.md, DSL001@docs/modules/process.md, DSL001@docs/modules/release.md, DSL001@docs/modules/render.md, DSL001@docs/modules/serve.md, DSL001@docs/modules/stats.md, DSL001@docs/modules/strata.md, DSL001@docs/modules/testing.md, DSL001@docs/modules/tickets.md, DSL001@docs/modules/vet.md, DSL001@docs/strata/boundary.md, DSL001@docs/strata/charter.md, DSL001@docs/strata/evidence.md, DSL001@docs/strata/host.md, DSL001@docs/strata/kernel.md, DSL001@docs/strata/krb.md, DSL001@docs/strata/policy.md, DSL001@docs/strata/reliability.md, DSL001@docs/strata/roadmap.md, DSL001@docs/strata/selfconform.md, DSL001@docs/strata/surface.md, DSL001@docs/strata/threat.md, DSL001@docs/strata/waive.md, F401@/home/logan/projects/frob/.claude/worktrees/queue-hygiene/tests/unit/test_tickets_evidence_only_scope.py
