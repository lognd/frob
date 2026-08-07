---
id: T-0280
title: 'CRITICAL: HOST001/HOST002 movement proofs + compromised-user scenario are
  unreachable from any CLI command'
state: done
kind: security
origin: human
created: '2026-07-19'
priority: medium
parent: T-0254
tier: ticket
sprint: null
scope:
- src/frob/strata/_audit.py
- src/frob/app/sys_runner.py
- src/frob/app/deploy_runner.py
- src/frob/strata/**
- tests/**
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_audit.py::TestHostWiring::test_shared_model_gaps
- tests/system/test_system.py::test_sys_audit_shared_writable_two_user_model_exits_nonzero_with_host001
- tests/unit/strata/test_audit.py::TestHostWiring::test_hardened_model_proved
designated_repro_test: null
threat: elevation-of-privilege
component: null
---
T-0260 malmberg pilot HIGH finding, coordinator-confirmed by grep: evaluate_host_isolation_waived / evaluate_lateral_isolation / evaluate_vertical_isolation / build_compromised_user_scenario (all from T-0256, the deploy epic's SECURITY CORE) have ZERO callers outside _host_isolation.py + the package __init__ export. frob sys audit's _audit.py::evaluate_exhaustiveness never invokes them; frob deploy has no audit-of-isolation verb; the pilot could only get the HOST001/002 verdict via a hand-written python harness. So the user's central ask -- PROVABLE lateral/vertical isolation, red-team blast-radius containment -- is built and sound (T-0256 review verified the logic) but a user CANNOT RUN IT. T-0256's own spec said 'wired into frob sys audit output beside self-conformance'; the wiring was never delivered and neither the T-0256 review nor the coordinator caught the missing CLI reachability (review verified logic soundness, not runnable path -- lesson). FIX: (1) fold evaluate_host_isolation_waived into _audit.py::evaluate_exhaustiveness so _strata_files: design/litmus/audit_hardened.strata excluded by [graph].exclude
_strata_files: design/litmus/audit_vuln.strata excluded by [graph].exclude
_strata_files: design/litmus/chirp.strata excluded by [graph].exclude
_strata_files: design/litmus/deploy_secret.strata excluded by [graph].exclude
_strata_files: design/litmus/payments.strata excluded by [graph].exclude
_strata_files: design/litmus/payments_hardened.strata excluded by [graph].exclude
_strata_files: design/litmus/tube.strata excluded by [graph].exclude
strata parse ok: module 'frob'
node cli declares 2 code glob(s)
node graphlang declares 3 code glob(s)
node gates declares 1 code glob(s)
node checker declares 1 code glob(s)
node stratamod declares 1 code glob(s)
node core declares 23 code glob(s)
node vet declares 1 code glob(s)
store tickets_ledger declares 1 code glob(s)
store tickets_ledger -> node at trust trusted, attrs=['code=src/frob/tickets/**', 'engine=git_tracked', 'append_only']
cache graph_cache of graphlang -> node + fill flow (age=value=1.0 unit='s') + 1 invalidation edge(s)
elaborated std.infra for module frob: 1 store(s), 1 cache(s), 0 queue(s), 0 cdn(s), 0 balancer(s), 0 diagnostic(s)
elaborated module frob: 10 node(s), 27 flow(s), 1 boundary(ies), 13 claim(s), 0 refine(s)
load_design_ids: 27 channel(s), 1 boundary(ies), 0 secret(s), 0 error(s)
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
closure from registry reached 0 node(s)
worst_age(graph_cache) = 1.0 via ['graphlang', 'graph_cache__fill', 'graph_cache']
closure from gates reached 6 node(s)
evaluated 13 claim(s): {'proved': 3, 'evidenced': 0, 'assumed': 10, 'refuted': 0}
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
closure from registry reached 0 node(s)
worst_age(graph_cache) = 1.0 via ['graphlang', 'graph_cache__fill', 'graph_cache']
closure from gates reached 6 node(s)
evaluated 13 claim(s): {'proved': 3, 'evidenced': 0, 'assumed': 10, 'refuted': 0}
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
closure from registry reached 0 node(s)
worst_age(graph_cache) = 1.0 via ['graphlang', 'graph_cache__fill', 'graph_cache']
closure from gates reached 6 node(s)
evaluated 13 claim(s): {'proved': 3, 'evidenced': 0, 'assumed': 10, 'refuted': 0}
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
closure from registry reached 0 node(s)
worst_age(graph_cache) = 1.0 via ['graphlang', 'graph_cache__fill', 'graph_cache']
closure from gates reached 6 node(s)
evaluated 13 claim(s): {'proved': 3, 'evidenced': 0, 'assumed': 10, 'refuted': 0}
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
compliance: discharge check over 10 node(s)/27 flow(s) -> 0 violation(s)
compliance: evaluated view='all-regulations' catalog=6 out_of_scope=0 -> 0 violation(s)
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
compliance: discharge check over 10 node(s)/27 flow(s) -> 0 violation(s)
compliance: evaluated view='us-coppa' catalog=6 out_of_scope=0 -> 0 violation(s)
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
compliance: discharge check over 10 node(s)/27 flow(s) -> 0 violation(s)
compliance: evaluated view='eu-gdpr' catalog=6 out_of_scope=0 -> 0 violation(s)
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
compliance: discharge check over 10 node(s)/27 flow(s) -> 0 violation(s)
compliance: evaluated view='us-hipaa' catalog=6 out_of_scope=0 -> 0 violation(s)
pii: evaluated 10 node(s)/27 flow(s) -> 0 violation(s)
lint: evaluated 10 node(s)/27 flow(s)/0 scenario(s) -> 5 violation(s)
cve_fingerprint: checked 9 fingerprint(s) against 13 cwe catalog entries -> 0 violation(s)
waive: LINT004 finding on checker (sub_target=None) waived (reason='no real kill switch around subprocess spawning yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
waive: LINT004 finding on core (sub_target=None) waived (reason='no real kill switch around subprocess spawning yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
waive: LINT004 finding on stratamod (sub_target=None) waived (reason='no real kill switch around net calls yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
waive: LINT004 finding on tickets_ledger (sub_target=None) waived (reason='no real kill switch around subprocess spawning yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
waive: LINT004 finding on vet (sub_target=None) waived (reason='no real kill switch around net calls yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
audit: evaluated views=11 -> 0 gap(s), 5 waived, 0 stale waiver(s)
code binding: 201 file(s) bound, 159 foreign
capability binding: 0 additional non-python file(s) bound
dispatching path=/home/logan/projects/frob/src/frob/__main__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/ack_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/app.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/app.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/app/arch_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/bind_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/check_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/check_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/config.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/config.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/cycle_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/deploy_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/deploy_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/docs_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/dup_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/exports_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/exports_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/gitlog_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/graph_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/map_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/mutate_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/outline_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/parse_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/perf_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/release_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/release_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/scaffold_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/serve_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/stats_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/sys_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/sys_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/test_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/ticket_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/vet_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/xref_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_cpp.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_python.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/bind/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/check/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/check/_native.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_native.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/check/_python.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_python.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/check/_ts.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_ts.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/cve/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cve/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cve/_parser.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cycle/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cycle/graph.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_audit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_conform.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_drift.py to grammar=python
vet: /home/logan/projects/frob/src/frob/deploy/_drift.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/deploy/_generate.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_vm_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/deploy/_vm_runner.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/docs/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_cache.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_core.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_cpp.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_py.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_pipeline.py to grammar=python
vet: /home/logan/projects/frob/src/frob/dup/_pipeline.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/dup/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/exports/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_arbitrary.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_obligations.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_run.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_signatures.py to grammar=python
vet: /home/logan/projects/frob/src/frob/fuzz/_signatures.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_stamp.py to grammar=python
vet: /home/logan/projects/frob/src/frob/fuzz/_stamp.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_baseline.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_baseline.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_coverage.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_coverage.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/_prework.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_prework.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_secrets.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/decisions.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/invariants.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gitio.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gitio.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/gitlog/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gitlog/__init__.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/graph/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/cache.py to grammar=python
vet: /home/logan/projects/frob/src/frob/graph/cache.py: capabilities observed: ['fs-write', 'sql']
dispatching path=/home/logan/projects/frob/src/frob/graph/digest.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/dsl.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/lock.py to grammar=python
vet: /home/logan/projects/frob/src/frob/graph/lock.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/lang/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_extract.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_c.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_python.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_rust.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_strata.py to grammar=python
vet: /home/logan/projects/frob/src/frob/lang/_walk_strata.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_typescript.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/color.py to grammar=python
vet: /home/logan/projects/frob/src/frob/logging/color.py: capabilities observed: ['env']
dispatching path=/home/logan/projects/frob/src/frob/logging/filter.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/formatter.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/handler.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/logger.py to grammar=python
vet: /home/logan/projects/frob/src/frob/logging/logger.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/logging/quiet.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/map/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/mutate/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/mutate/__init__.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/outline/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_harness.py to grammar=python
vet: /home/logan/projects/frob/src/frob/perf/_harness.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/perf/_heat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_profile.py to grammar=python
vet: /home/logan/projects/frob/src/frob/perf/_profile.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/perf/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/policy/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/policy/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/policy/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/cargo.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/clang.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/clang_tidy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/eslint.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/junit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/pytest.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/ruff.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/tsc.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/ty.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/valgrind.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/release/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/release/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/scaffold/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/scaffold/project.py to grammar=python
vet: /home/logan/projects/frob/src/frob/scaffold/project.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/serve/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/serve/_tools.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/serve/server.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/stats/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_ast.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_atomic.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_audit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_breach.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_claims.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_code_binding.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_compliance.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_crash.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_deploy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_design_load.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_effects.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_effects.py: capabilities observed: ['net']
dispatching path=/home/logan/projects/frob/src/frob/strata/_elaborate.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_errors.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_export.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_facts.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_facts.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/strata/_host.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_host_isolation.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_infra.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_lint.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_packs.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_packs.py: capabilities observed: ['ffi']
dispatching path=/home/logan/projects/frob/src/frob/strata/_parse.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_parse.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/strata/_pii.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_plan.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_policy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_report.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_scenarios.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_secrets.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_selfconform.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_sysdoc.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_threat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_waive.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/_collect.py to grammar=python
vet: /home/logan/projects/frob/src/frob/testing/_collect.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/testing/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/_runners.py to grammar=python
vet: /home/logan/projects/frob/src/frob/testing/_runners.py: capabilities observed: ['env', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/testing/_select.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/__init__.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/tickets/_land.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/_land.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/tickets/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/_provisional.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/_store.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/_store.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/tickets/clipboard.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/clipboard.py: capabilities observed: ['env', 'exec']
dispatching path=/home/logan/projects/frob/src/frob/vet/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_allow.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_cache.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_containment.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_cve.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_ecosystem.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_ecosystem.py: capabilities observed: ['install-hook']
dispatching path=/home/logan/projects/frob/src/frob/vet/_hook.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_lifecycle.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_lockfile.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_nvd.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_nvd.py: capabilities observed: ['fetch_url', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/vet/_obfuscation.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_osv.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_cargo.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_npm.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_popular_npm.py: capabilities observed: ['net']
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_pypi.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_popular_pypi.py: capabilities observed: ['ffi']
dispatching path=/home/logan/projects/frob/src/frob/vet/_registry.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_registry.py: capabilities observed: ['fetch_url', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/vet/_scan.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_source.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_source.py: capabilities observed: ['env']
dispatching path=/home/logan/projects/frob/src/frob/vet/_typosquat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/xref/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/__main__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/ack_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/app.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/app.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/app/arch_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/bind_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/check_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/check_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/config.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/config.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/cycle_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/deploy_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/deploy_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/docs_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/dup_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/exports_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/exports_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/gitlog_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/graph_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/map_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/mutate_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/outline_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/parse_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/perf_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/release_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/release_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/scaffold_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/serve_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/stats_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/sys_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/sys_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/test_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/ticket_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/vet_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/xref_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_cpp.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_python.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/bind/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/check/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/check/_native.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_native.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/check/_python.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_python.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/check/_ts.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_ts.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/cve/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cve/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cve/_parser.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cycle/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cycle/graph.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_audit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_conform.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_drift.py to grammar=python
vet: /home/logan/projects/frob/src/frob/deploy/_drift.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/deploy/_generate.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_vm_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/deploy/_vm_runner.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/docs/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_cache.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_core.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_cpp.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_py.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_pipeline.py to grammar=python
vet: /home/logan/projects/frob/src/frob/dup/_pipeline.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/dup/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/exports/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_arbitrary.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_obligations.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_run.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_signatures.py to grammar=python
vet: /home/logan/projects/frob/src/frob/fuzz/_signatures.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_stamp.py to grammar=python
vet: /home/logan/projects/frob/src/frob/fuzz/_stamp.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_baseline.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_baseline.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_coverage.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_coverage.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/_prework.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_prework.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_secrets.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/decisions.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/invariants.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gitio.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gitio.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/gitlog/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gitlog/__init__.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/graph/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/cache.py to grammar=python
vet: /home/logan/projects/frob/src/frob/graph/cache.py: capabilities observed: ['fs-write', 'sql']
dispatching path=/home/logan/projects/frob/src/frob/graph/digest.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/dsl.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/lock.py to grammar=python
vet: /home/logan/projects/frob/src/frob/graph/lock.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/lang/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_extract.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_c.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_python.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_rust.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_strata.py to grammar=python
vet: /home/logan/projects/frob/src/frob/lang/_walk_strata.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_typescript.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/color.py to grammar=python
vet: /home/logan/projects/frob/src/frob/logging/color.py: capabilities observed: ['env']
dispatching path=/home/logan/projects/frob/src/frob/logging/filter.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/formatter.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/handler.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/logger.py to grammar=python
vet: /home/logan/projects/frob/src/frob/logging/logger.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/logging/quiet.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/map/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/mutate/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/mutate/__init__.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/outline/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_harness.py to grammar=python
vet: /home/logan/projects/frob/src/frob/perf/_harness.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/perf/_heat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_profile.py to grammar=python
vet: /home/logan/projects/frob/src/frob/perf/_profile.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/perf/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/policy/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/policy/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/policy/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/cargo.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/clang.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/clang_tidy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/eslint.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/junit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/pytest.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/ruff.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/tsc.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/ty.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/valgrind.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/release/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/release/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/scaffold/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/scaffold/project.py to grammar=python
vet: /home/logan/projects/frob/src/frob/scaffold/project.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/serve/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/serve/_tools.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/serve/server.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/stats/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_ast.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_atomic.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_audit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_breach.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_claims.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_code_binding.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_compliance.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_crash.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_deploy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_design_load.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_effects.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_effects.py: capabilities observed: ['net']
dispatching path=/home/logan/projects/frob/src/frob/strata/_elaborate.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_errors.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_export.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_facts.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_facts.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/strata/_host.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_host_isolation.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_infra.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_lint.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_packs.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_packs.py: capabilities observed: ['ffi']
dispatching path=/home/logan/projects/frob/src/frob/strata/_parse.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_parse.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/strata/_pii.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_plan.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_policy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_report.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_scenarios.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_secrets.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_selfconform.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_sysdoc.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_threat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_waive.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/_collect.py to grammar=python
vet: /home/logan/projects/frob/src/frob/testing/_collect.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/testing/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/_runners.py to grammar=python
vet: /home/logan/projects/frob/src/frob/testing/_runners.py: capabilities observed: ['env', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/testing/_select.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/__init__.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/tickets/_land.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/_land.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/tickets/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/_provisional.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/_store.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/_store.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/tickets/clipboard.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/clipboard.py: capabilities observed: ['env', 'exec']
dispatching path=/home/logan/projects/frob/src/frob/vet/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_allow.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_cache.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_containment.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_cve.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_ecosystem.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_ecosystem.py: capabilities observed: ['install-hook']
dispatching path=/home/logan/projects/frob/src/frob/vet/_hook.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_lifecycle.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_lockfile.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_nvd.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_nvd.py: capabilities observed: ['fetch_url', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/vet/_obfuscation.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_osv.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_cargo.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_npm.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_popular_npm.py: capabilities observed: ['net']
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_pypi.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_popular_pypi.py: capabilities observed: ['ffi']
dispatching path=/home/logan/projects/frob/src/frob/vet/_registry.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_registry.py: capabilities observed: ['fetch_url', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/vet/_scan.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_source.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_source.py: capabilities observed: ['env']
dispatching path=/home/logan/projects/frob/src/frob/vet/_typosquat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/xref/__init__.py to grammar=python
selfconform: 0 violation(s), 0 waived, 0 stale waiver(s) found under /home/logan/projects/frob
sys audit: checked 11 view(s): security:owasp-top-10, quality:web-performance-baseline, quality:reliability-baseline, quality:web-quality-security-baseline, compliance:all-regulations, compliance:us-coppa, compliance:eu-gdpr, compliance:us-hipaa, pii:model, lint:model, cve-fingerprint:catalog
sys audit: PROVED (5 waived) -- zero UNWAIVED gaps across every configured view
sys audit: self-conformance PROVED -- zero SYS gaps
sys audit: capability coverage: 13 kind(s) x 4 language(s), 30 cell(s) patterned+proven, 22 excused with reasons, 0 unexcused on any model with 2+ runs_as users emits HOST001/HOST002 findings (honoring the T-0174 waiver channel, as a FamilyGap family like lint/pii); (2) auto-generate one compromised-user scenario per runs_as user inside sys audit (mirror _crash.py's auto node-loss scenarios) and fold the blast-radius NoFlow results into the report; (3) surface it in  too if that's the more natural home -- decide, but it MUST be reachable from at least one command. Litmus already exists (test_litmus_host_isolation); add a CLI-level test that _strata_files: design/litmus/audit_hardened.strata excluded by [graph].exclude
_strata_files: design/litmus/audit_vuln.strata excluded by [graph].exclude
_strata_files: design/litmus/chirp.strata excluded by [graph].exclude
_strata_files: design/litmus/deploy_secret.strata excluded by [graph].exclude
_strata_files: design/litmus/payments.strata excluded by [graph].exclude
_strata_files: design/litmus/payments_hardened.strata excluded by [graph].exclude
_strata_files: design/litmus/tube.strata excluded by [graph].exclude
strata parse ok: module 'frob'
node cli declares 2 code glob(s)
node graphlang declares 3 code glob(s)
node gates declares 1 code glob(s)
node checker declares 1 code glob(s)
node stratamod declares 1 code glob(s)
node core declares 23 code glob(s)
node vet declares 1 code glob(s)
store tickets_ledger declares 1 code glob(s)
store tickets_ledger -> node at trust trusted, attrs=['code=src/frob/tickets/**', 'engine=git_tracked', 'append_only']
cache graph_cache of graphlang -> node + fill flow (age=value=1.0 unit='s') + 1 invalidation edge(s)
elaborated std.infra for module frob: 1 store(s), 1 cache(s), 0 queue(s), 0 cdn(s), 0 balancer(s), 0 diagnostic(s)
elaborated module frob: 10 node(s), 27 flow(s), 1 boundary(ies), 13 claim(s), 0 refine(s)
load_design_ids: 27 channel(s), 1 boundary(ies), 0 secret(s), 0 error(s)
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
closure from registry reached 0 node(s)
worst_age(graph_cache) = 1.0 via ['graphlang', 'graph_cache__fill', 'graph_cache']
closure from gates reached 6 node(s)
evaluated 13 claim(s): {'proved': 3, 'evidenced': 0, 'assumed': 10, 'refuted': 0}
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
closure from registry reached 0 node(s)
worst_age(graph_cache) = 1.0 via ['graphlang', 'graph_cache__fill', 'graph_cache']
closure from gates reached 6 node(s)
evaluated 13 claim(s): {'proved': 3, 'evidenced': 0, 'assumed': 10, 'refuted': 0}
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
closure from registry reached 0 node(s)
worst_age(graph_cache) = 1.0 via ['graphlang', 'graph_cache__fill', 'graph_cache']
closure from gates reached 6 node(s)
evaluated 13 claim(s): {'proved': 3, 'evidenced': 0, 'assumed': 10, 'refuted': 0}
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
closure from registry reached 0 node(s)
worst_age(graph_cache) = 1.0 via ['graphlang', 'graph_cache__fill', 'graph_cache']
closure from gates reached 6 node(s)
evaluated 13 claim(s): {'proved': 3, 'evidenced': 0, 'assumed': 10, 'refuted': 0}
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
compliance: discharge check over 10 node(s)/27 flow(s) -> 0 violation(s)
compliance: evaluated view='all-regulations' catalog=6 out_of_scope=0 -> 0 violation(s)
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
compliance: discharge check over 10 node(s)/27 flow(s) -> 0 violation(s)
compliance: evaluated view='us-coppa' catalog=6 out_of_scope=0 -> 0 violation(s)
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
compliance: discharge check over 10 node(s)/27 flow(s) -> 0 violation(s)
compliance: evaluated view='eu-gdpr' catalog=6 out_of_scope=0 -> 0 violation(s)
fact base built: 10 node(s), 27 flow(s), 1 boundary(ies), 0 diagnostic(s)
compliance: discharge check over 10 node(s)/27 flow(s) -> 0 violation(s)
compliance: evaluated view='us-hipaa' catalog=6 out_of_scope=0 -> 0 violation(s)
pii: evaluated 10 node(s)/27 flow(s) -> 0 violation(s)
lint: evaluated 10 node(s)/27 flow(s)/0 scenario(s) -> 5 violation(s)
cve_fingerprint: checked 9 fingerprint(s) against 13 cwe catalog entries -> 0 violation(s)
waive: LINT004 finding on checker (sub_target=None) waived (reason='no real kill switch around subprocess spawning yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
waive: LINT004 finding on core (sub_target=None) waived (reason='no real kill switch around subprocess spawning yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
waive: LINT004 finding on stratamod (sub_target=None) waived (reason='no real kill switch around net calls yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
waive: LINT004 finding on tickets_ledger (sub_target=None) waived (reason='no real kill switch around subprocess spawning yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
waive: LINT004 finding on vet (sub_target=None) waived (reason='no real kill switch around net calls yet -- T-0200 is the follow-on ticket to build one' ticket=T-0200)
audit: evaluated views=11 -> 0 gap(s), 5 waived, 0 stale waiver(s)
code binding: 201 file(s) bound, 159 foreign
capability binding: 0 additional non-python file(s) bound
dispatching path=/home/logan/projects/frob/src/frob/__main__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/ack_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/app.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/app.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/app/arch_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/bind_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/check_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/check_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/config.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/config.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/cycle_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/deploy_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/deploy_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/docs_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/dup_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/exports_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/exports_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/gitlog_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/graph_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/map_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/mutate_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/outline_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/parse_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/perf_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/release_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/release_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/scaffold_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/serve_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/stats_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/sys_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/sys_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/test_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/ticket_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/vet_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/xref_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_cpp.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_python.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/bind/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/check/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/check/_native.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_native.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/check/_python.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_python.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/check/_ts.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_ts.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/cve/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cve/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cve/_parser.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cycle/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cycle/graph.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_audit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_conform.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_drift.py to grammar=python
vet: /home/logan/projects/frob/src/frob/deploy/_drift.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/deploy/_generate.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_vm_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/deploy/_vm_runner.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/docs/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_cache.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_core.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_cpp.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_py.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_pipeline.py to grammar=python
vet: /home/logan/projects/frob/src/frob/dup/_pipeline.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/dup/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/exports/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_arbitrary.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_obligations.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_run.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_signatures.py to grammar=python
vet: /home/logan/projects/frob/src/frob/fuzz/_signatures.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_stamp.py to grammar=python
vet: /home/logan/projects/frob/src/frob/fuzz/_stamp.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_baseline.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_baseline.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_coverage.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_coverage.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/_prework.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_prework.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_secrets.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/decisions.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/invariants.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gitio.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gitio.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/gitlog/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gitlog/__init__.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/graph/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/cache.py to grammar=python
vet: /home/logan/projects/frob/src/frob/graph/cache.py: capabilities observed: ['fs-write', 'sql']
dispatching path=/home/logan/projects/frob/src/frob/graph/digest.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/dsl.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/lock.py to grammar=python
vet: /home/logan/projects/frob/src/frob/graph/lock.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/lang/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_extract.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_c.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_python.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_rust.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_strata.py to grammar=python
vet: /home/logan/projects/frob/src/frob/lang/_walk_strata.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_typescript.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/color.py to grammar=python
vet: /home/logan/projects/frob/src/frob/logging/color.py: capabilities observed: ['env']
dispatching path=/home/logan/projects/frob/src/frob/logging/filter.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/formatter.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/handler.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/logger.py to grammar=python
vet: /home/logan/projects/frob/src/frob/logging/logger.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/logging/quiet.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/map/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/mutate/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/mutate/__init__.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/outline/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_harness.py to grammar=python
vet: /home/logan/projects/frob/src/frob/perf/_harness.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/perf/_heat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_profile.py to grammar=python
vet: /home/logan/projects/frob/src/frob/perf/_profile.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/perf/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/policy/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/policy/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/policy/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/cargo.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/clang.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/clang_tidy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/eslint.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/junit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/pytest.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/ruff.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/tsc.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/ty.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/valgrind.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/release/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/release/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/scaffold/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/scaffold/project.py to grammar=python
vet: /home/logan/projects/frob/src/frob/scaffold/project.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/serve/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/serve/_tools.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/serve/server.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/stats/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_ast.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_atomic.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_audit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_breach.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_claims.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_code_binding.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_compliance.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_crash.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_deploy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_design_load.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_effects.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_effects.py: capabilities observed: ['net']
dispatching path=/home/logan/projects/frob/src/frob/strata/_elaborate.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_errors.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_export.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_facts.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_facts.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/strata/_host.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_host_isolation.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_infra.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_lint.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_packs.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_packs.py: capabilities observed: ['ffi']
dispatching path=/home/logan/projects/frob/src/frob/strata/_parse.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_parse.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/strata/_pii.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_plan.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_policy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_report.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_scenarios.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_secrets.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_selfconform.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_sysdoc.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_threat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_waive.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/_collect.py to grammar=python
vet: /home/logan/projects/frob/src/frob/testing/_collect.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/testing/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/_runners.py to grammar=python
vet: /home/logan/projects/frob/src/frob/testing/_runners.py: capabilities observed: ['env', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/testing/_select.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/__init__.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/tickets/_land.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/_land.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/tickets/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/_provisional.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/_store.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/_store.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/tickets/clipboard.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/clipboard.py: capabilities observed: ['env', 'exec']
dispatching path=/home/logan/projects/frob/src/frob/vet/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_allow.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_cache.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_containment.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_cve.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_ecosystem.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_ecosystem.py: capabilities observed: ['install-hook']
dispatching path=/home/logan/projects/frob/src/frob/vet/_hook.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_lifecycle.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_lockfile.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_nvd.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_nvd.py: capabilities observed: ['fetch_url', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/vet/_obfuscation.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_osv.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_cargo.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_npm.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_popular_npm.py: capabilities observed: ['net']
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_pypi.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_popular_pypi.py: capabilities observed: ['ffi']
dispatching path=/home/logan/projects/frob/src/frob/vet/_registry.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_registry.py: capabilities observed: ['fetch_url', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/vet/_scan.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_source.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_source.py: capabilities observed: ['env']
dispatching path=/home/logan/projects/frob/src/frob/vet/_typosquat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/xref/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/__main__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/ack_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/app.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/app.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/app/arch_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/bind_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/check_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/check_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/config.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/config.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/cycle_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/deploy_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/deploy_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/docs_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/dup_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/exports_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/exports_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/gitlog_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/graph_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/map_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/mutate_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/outline_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/parse_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/perf_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/release_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/release_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/scaffold_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/serve_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/stats_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/sys_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/app/sys_runner.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/app/test_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/ticket_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/vet_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/app/xref_runner.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_cpp.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/arch/_python.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/bind/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/check/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/check/_native.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_native.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/check/_python.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_python.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/check/_ts.py to grammar=python
vet: /home/logan/projects/frob/src/frob/check/_ts.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/cve/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cve/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cve/_parser.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cycle/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/cycle/graph.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_audit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_conform.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_drift.py to grammar=python
vet: /home/logan/projects/frob/src/frob/deploy/_drift.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/deploy/_generate.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/deploy/_vm_runner.py to grammar=python
vet: /home/logan/projects/frob/src/frob/deploy/_vm_runner.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/docs/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_cache.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_core.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_cpp.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_legacy_py.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/dup/_pipeline.py to grammar=python
vet: /home/logan/projects/frob/src/frob/dup/_pipeline.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/dup/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/exports/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_arbitrary.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_obligations.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_run.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_signatures.py to grammar=python
vet: /home/logan/projects/frob/src/frob/fuzz/_signatures.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/fuzz/_stamp.py to grammar=python
vet: /home/logan/projects/frob/src/frob/fuzz/_stamp.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_baseline.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_baseline.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_coverage.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_coverage.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/_prework.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gates/_prework.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/gates/_secrets.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/decisions.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gates/invariants.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/gitio.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gitio.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/gitlog/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/gitlog/__init__.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/graph/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/cache.py to grammar=python
vet: /home/logan/projects/frob/src/frob/graph/cache.py: capabilities observed: ['fs-write', 'sql']
dispatching path=/home/logan/projects/frob/src/frob/graph/digest.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/dsl.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/graph/lock.py to grammar=python
vet: /home/logan/projects/frob/src/frob/graph/lock.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/lang/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_extract.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_c.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_python.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_rust.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_strata.py to grammar=python
vet: /home/logan/projects/frob/src/frob/lang/_walk_strata.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/lang/_walk_typescript.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/color.py to grammar=python
vet: /home/logan/projects/frob/src/frob/logging/color.py: capabilities observed: ['env']
dispatching path=/home/logan/projects/frob/src/frob/logging/filter.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/formatter.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/handler.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/logging/logger.py to grammar=python
vet: /home/logan/projects/frob/src/frob/logging/logger.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/logging/quiet.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/map/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/mutate/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/mutate/__init__.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/outline/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_harness.py to grammar=python
vet: /home/logan/projects/frob/src/frob/perf/_harness.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/perf/_heat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/perf/_profile.py to grammar=python
vet: /home/logan/projects/frob/src/frob/perf/_profile.py: capabilities observed: ['exec', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/perf/_rules.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/policy/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/policy/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/policy/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/cargo.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/clang.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/clang_tidy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/common.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/eslint.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/junit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/pytest.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/ruff.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/tsc.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/ty.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/process/parsers/valgrind.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/release/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/release/__init__.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/scaffold/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/scaffold/project.py to grammar=python
vet: /home/logan/projects/frob/src/frob/scaffold/project.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/serve/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/serve/_tools.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/serve/server.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/stats/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_ast.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_atomic.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_audit.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_breach.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_claims.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_code_binding.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_compliance.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_crash.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_deploy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_design_load.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_effects.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_effects.py: capabilities observed: ['net']
dispatching path=/home/logan/projects/frob/src/frob/strata/_elaborate.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_errors.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_export.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_facts.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_facts.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/strata/_host.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_host_isolation.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_infra.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_lint.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_packs.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_packs.py: capabilities observed: ['ffi']
dispatching path=/home/logan/projects/frob/src/frob/strata/_parse.py to grammar=python
vet: /home/logan/projects/frob/src/frob/strata/_parse.py: capabilities observed: ['eval']
dispatching path=/home/logan/projects/frob/src/frob/strata/_pii.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_plan.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_policy.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_report.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_scenarios.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_secrets.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_selfconform.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_sysdoc.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_threat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/strata/_waive.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/_collect.py to grammar=python
vet: /home/logan/projects/frob/src/frob/testing/_collect.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/testing/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/testing/_runners.py to grammar=python
vet: /home/logan/projects/frob/src/frob/testing/_runners.py: capabilities observed: ['env', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/testing/_select.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/__init__.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/__init__.py: capabilities observed: ['exec']
dispatching path=/home/logan/projects/frob/src/frob/tickets/_land.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/_land.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/tickets/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/_provisional.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/tickets/_store.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/_store.py: capabilities observed: ['fs-write']
dispatching path=/home/logan/projects/frob/src/frob/tickets/clipboard.py to grammar=python
vet: /home/logan/projects/frob/src/frob/tickets/clipboard.py: capabilities observed: ['env', 'exec']
dispatching path=/home/logan/projects/frob/src/frob/vet/__init__.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_allow.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_cache.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_containment.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_cve.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_ecosystem.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_ecosystem.py: capabilities observed: ['install-hook']
dispatching path=/home/logan/projects/frob/src/frob/vet/_hook.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_lifecycle.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_lockfile.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_models.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_nvd.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_nvd.py: capabilities observed: ['fetch_url', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/vet/_obfuscation.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_osv.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_cargo.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_npm.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_popular_npm.py: capabilities observed: ['net']
dispatching path=/home/logan/projects/frob/src/frob/vet/_popular_pypi.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_popular_pypi.py: capabilities observed: ['ffi']
dispatching path=/home/logan/projects/frob/src/frob/vet/_registry.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_registry.py: capabilities observed: ['fetch_url', 'fs-write']
dispatching path=/home/logan/projects/frob/src/frob/vet/_scan.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/vet/_source.py to grammar=python
vet: /home/logan/projects/frob/src/frob/vet/_source.py: capabilities observed: ['env']
dispatching path=/home/logan/projects/frob/src/frob/vet/_typosquat.py to grammar=python
dispatching path=/home/logan/projects/frob/src/frob/xref/__init__.py to grammar=python
selfconform: 0 violation(s), 0 waived, 0 stale waiver(s) found under /home/logan/projects/frob
sys audit: checked 11 view(s): security:owasp-top-10, quality:web-performance-baseline, quality:reliability-baseline, quality:web-quality-security-baseline, compliance:all-regulations, compliance:us-coppa, compliance:eu-gdpr, compliance:us-hipaa, pii:model, lint:model, cve-fingerprint:catalog
sys audit: PROVED (5 waived) -- zero UNWAIVED gaps across every configured view
sys audit: self-conformance PROVED -- zero SYS gaps
sys audit: capability coverage: 13 kind(s) x 4 language(s), 30 cell(s) patterned+proven, 22 excused with reasons, 0 unexcused on a shared-writable-path model exits nonzero with HOST001. ACCEPTANCE: a real repo (malmberg) can run one command and see its isolation proved or its gaps named. This is the highest-priority deploy ticket.