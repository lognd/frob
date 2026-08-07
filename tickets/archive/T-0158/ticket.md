---
id: T-0158
title: 'capability exhaustiveness matrix: every reserved kind provably detected in
  every supported language'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_registry.py
- src/frob/strata/**
- src/frob/app/sys_runner.py
- design/frob.strata
- tests/**
- docs/modules/vet.md
- docs/strata/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_matrix_covers_every_kind_and_language
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_operation_kind_and_language_registered
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_excuse_kind_and_language_registered
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_cell_is_both_patterned_and_excused
- tests/test_capability_registry.py::TestValidateRegistryKinds::test_known_kinds_pass
- tests/test_capability_registry.py::TestValidateRegistryKinds::test_unknown_kind_reported
- tests/test_capability_registry.py::TestValidateRegistryKinds::test_every_threat_catalog_kind_is_registered
- tests/test_capability_registry.py::test_fire_fixture_flags_capability
- tests/test_capability_registry.py::test_fire_fixture_names_a_registry_entry
- tests/test_capability_registry.py::TestNegativeFixtures::test_re_compile_is_not_eval
- tests/test_capability_registry.py::TestNegativeFixtures::test_c_socket_header_alone_is_not_net
- tests/test_vet.py::TestCapabilityScan::test_scan_file_operations_names_registry_entry
- tests/test_vet.py::TestCapabilityScan::test_scan_file_operations_no_language
- tests/test_vet.py::TestCapabilityScan::test_scan_file_operations_bare_compile
- tests/test_vet.py::TestCapabilityScan::test_scan_file_operations_dotted_compile_not_matched
- tests/test_vet.py::TestCapabilityScan::test_scan_file_operations_unreadable_file
- tests/test_vet.py::TestCapabilityScan::test_c_source_exec_detected
- tests/test_vet.py::TestCapabilityScan::test_language_for_known_and_unknown_extensions
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/test_capability_registry.py::TestNoSilentNeedleRegression::test_every_pre_registry_needle_still_fires_somewhere
- tests/test_capability_registry.py::TestNoSilentNeedleRegression::test_every_reclassified_needle_actually_still_fires_under_its_new_kind
- tests/test_capability_registry.py::TestNoSilentNeedleRegression::test_popen_bare_call_still_flags_exec
designated_repro_test: null
threat: null
component: null
---
Make the security proof chain sound end to end: THREAT003/THREAT004/SYS100 conclusions (code observes what the design declares, obligations discharge) are only valid if NO reserved capability kind can hide in an unscanned language or an unpatterned cell. Today that is not provable: vet _capability's _PATTERNS covers python/typescript/rust per-kind ad hoc, and C/C++ is excused wholesale ('honestly-empty'). Deliverables: (1) SINGLE-SOURCE capability registry -- one authoritative enumeration of every reserved kind (union of: _PATTERNS keys, every capability_kind in CWE_CATALOG/CWE_TOP_25_CATALOG, every may declaration the surface grammar accepts, DEFAULT_BENIGN_CAPABILITIES) -- with all consumers importing it; any kind used anywhere but absent from the registry fails loudly (extends the T-0150 drift-lock). (2) COVERAGE MATRIX GATE: for every (kind x supported-language) cell, either detection patterns exist OR an explicit per-cell excuse entry with a written reason ('client_storage: no C idiom -- browser-only concept', 'html_render in rust: covered via templating-crate needles ...'). The blanket C/C++ excuse is retired: each kind gets its own C/C++ decision. Unexcused empty cell = gate failure; excuse entries follow the OutOfScopeEntry discipline (specific reason naming the missing idiom, never boilerplate). (3) PER-CELL FIRE FIXTURES: for every patterned cell, a minimal real code snippet in that language that the scanner MUST flag, parametrized so a pattern without a firing fixture fails (T-0145 drift-lock style); plus per-cell negative fixtures locking the documented false-positive boundaries (T-0151 lessons: dotted-call exclusions, self-match). (4) CROSS-CHECKS: matrix kinds reconcile against the threat catalog joins (every capability_kind used by a WeaknessEntry must be a registry kind with at least one patterned language) and against design/frob.strata's may declarations. (5) Wire the matrix verdict into frob sys audit output beside self-conformance ('capability coverage: N kinds x M languages, K cells patterned+proven, J excused with reasons, 0 unexcused') so the exhaustiveness claim is a printed, checkable proof, not folklore. Expect cascading consequences (new patterns change observed capabilities -> design/goldens -- handle per T-0150/T-0151 precedent, green honestly.

Addendum (user, 2026-07-18) -- the matrix cells must be a STRUCTURED
DANGEROUS-OPERATIONS REGISTRY, not anonymous needle strings: promote
every _PATTERNS needle into a first-class entry {language, library
(stdlib module / crate / npm package), function-or-pattern,
capability_kind, cwe_links (joining the threat catalog), rationale (one
line: why dangerous), safer_alternative, severity}. Coverage mandate per
language: the dangerous surface of the COMMON libraries, not just
builtins -- python: subprocess/os.system+popen+exec*/pickle/marshal/
shelve/ctypes/importlib/eval+compile/socket+http+urllib+requests/
sqlite3+DB-API string interp; typescript-js: eval/Function/child_process/
vm/innerHTML+outerHTML+document.write/dangerouslySetInnerHTML/
localStorage+sessionStorage+indexedDB/fetch+XMLHttpRequest+WebSocket;
rust: std::process::Command/unsafe extern FFI/libloading/std::net/
mem::transmute; c-cpp: system+popen+exec family/dlopen/strcpy+sprintf+
gets family/socket -- each an entry with metadata, each backed by a
matrix fire fixture. Audit output upgrades accordingly: a capability
finding names the registry entry (library, function, rationale,
safer_alternative), so 'frob sys audit' findings become actionable
prose, not bare kind labels. T-0153's CVE fingerprints join THIS
registry's kind vocabulary and may cite its entries, but remain a
separate catalog (known-vulnerable usage shapes vs capability-granting
operations). The T-0159 extension guide for this registry documents the
add-an-operation recipe.

Addendum 2 (user, 2026-07-18) -- EXHAUSTIVE and CLOSED-WORLD, IO-monad
style: (1) the registry must cover the ENTIRE effectful surface of each
language's builtins and standard library (python: every stdlib module
that can touch process/fs/net/env/dynamic-code -- os, sys, subprocess,
socket, http, urllib, ftplib, smtplib, pickle, marshal, shelve, ctypes,
importlib, runpy, code, pty, signal, tempfile, shutil, pathlib-write,
sqlite3, multiprocessing, asyncio subprocess/net, webbrowser, platform
exec paths -- curated exhaustively, with pure modules explicitly listed
as no-capability so exhaustiveness is checkable, not sampled). (2)
CLOSED WORLD: every import/call into a third-party library must resolve
to (a) a registry entry, (b) a VETTED library -- vet capability
introspection over its installed source using THE SAME scanner engine
(single implementation, no parallel matcher), cached per
package+version -- or (c) LOUD FAILURE: 'unknown, unvetted, uninspected'
is itself a violation. Effects only through accounted channels; the
audit prints the accounting (N registry ops, M vetted libraries, K
explicit no-capability entries, 0 unknown) so the exhaustiveness claim
is a printed proof. (3) REAL-WORLD PRIORITY, from the 2026-07-18
ten-repo dependency survey: python 3rd-party to cover first -- pydantic,
httpx(6 repos), fastapi(5), numpy(4), cryptography(3), jinja2(3),
python-dotenv(3), uvicorn(3), sqlalchemy, asyncpg, alembic, redis,
boto3, stripe, anthropic, argon2-cffi, aiosmtpd, playwright, Pillow,
requests-family; npm -- react/react-dom, vite/vitest, playwright,
openapi-typescript, eslint tooling; cargo -- pyo3, serde/serde_json,
tracing, libloading (dynamic loading -- dangerous), wasm-bindgen,
crossbeam, thiserror. Libraries outside this list go through the vet
path, not hand-registry entries.

Scope extension (agent, 2026-07-18): the structured registry was split
into a new module, `src/frob/vet/_capability_registry.py` -- outside the
original `src/frob/vet/_capability.py`-only scope entry, but the single-
source registry deliverable (1) is meaningless split across two files
with no room to grow; `_capability.py` now imports and compiles from it.
`design/frob.strata` and `src/frob/app/sys_runner.py` are added because
the deliverables are cascading by design: new `DangerousOperation`
entries change what `_capability.py` observes in this repo's OWN
`src/frob/vet/**`/`src/frob/graph/**` trees (sql/fetch_url/deserialize
newly patterned), which SYS100/THREAT002/THREAT003 catch against
`design/frob.strata`'s `may` declarations (T-0150/T-0151 precedent this
ticket explicitly names) -- fixing green honestly requires editing the
design file, not narrowing the scanner. `sys_runner.py` gets deliverable
(5)'s matrix-verdict print line beside the existing self-conformance
print, the only call site `frob sys audit` has.
title: 'extending frob: developer guides for every registry and extension point'
state: queued
kind: docs
origin: human
created: '2026-07-18'
blocked_by:
- T-0153
- T-0154
- T-0155
- T-0157
- T-0158
parent: null
scope:
- docs/guides/**
- docs/index.md
- src/frob/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
A guide series under docs/guides/extending/ making every registry trivially extendable. INVENTORY FIRST: enumerate every registry/extension point in the codebase -- at minimum: gate rule families and their registration (COV/TEST/DRIFT/SCOPE/PRE/DOC/PERF/SYS/THREAT/COMPLIANCE/WAIVE), comment DSL directives (frob:ticket/tests/doc/waive/todo/invariant/channel/boundary/secret), threat catalog (WeaknessEntry/OutOfScopeEntry/views incl. the separate-views precedent), compliance regulations/views, capability registry + pattern tables + per-language matrix cells (T-0158), CVE fingerprints (T-0153), PII categories (T-0154), design-lint rules (T-0155), secrets-scan providers (T-0157), prover claim kinds, scenario kinds, strata surface grammar keywords (and the tmLanguage drift-lock), [[test.runner]] entries, language grammar handlers, sys export formats, litmus fixture mappings, benign capabilities, ticket kinds/states. ONE GUIDE PER REGISTRY on a common template: what it is and where it lives (file paths + symbol names); step-by-step 'add a new entry' recipe; WHICH DRIFT-LOCKS WILL FIRE when you add one and exactly what each demands (fixture, test, excuse entry, doc anchor, golden regen); a worked example diff; common mistakes (cite real session incidents where instructive, e.g. separate-views vs widening defaults, self-match false positives, stale-comment traps). ANTI-ROT MECHANISM (the point of doing this in frob): every guide is bound to its registry's code symbol with frob:doc anchors so the DOC gates flag drift when the registry changes; plus a completeness drift-lock test -- a machine-readable registry-of-registries (the inventory above) asserting every entry has a guide file and a live anchor, so ADDING A NEW REGISTRY without a guide fails the build. docs/index.md gains an Extending section linking every guide. Writing guides will require reading each registry's code carefully -- fix nothing beyond doc anchors; file tickets for any defect discovered while documenting.