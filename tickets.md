# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0139 -->
```yaml
id: T-0139
title: editor syntax highlighting for .strata (VSCode + JetBrains via one TextMate
  grammar)
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
User request: syntax highlighting for .strata in VSCode and JetBrains products. Approach: ONE TextMate grammar consumed by both -- VSCode natively via an extension under editors/vscode-strata/ (package.json contributes language+grammar, language-configuration.json, syntaxes/strata.tmLanguage.json), JetBrains via its bundled TextMate Bundles plugin pointing at the same directory (document the import steps; no full IntelliJ plugin). The grammar must be derived from the AUTHORITATIVE keyword/token tables in strata-core/src/parse.rs (top-level dispatch keywords, property keywords incl. the T-0093/T-0132/T-0136/T-0138 additions: trust clauses, code=/may strings, secret, on deploy, quoted claim ids), // and /// comments, double-quoted strings, quantities with units, claim forms and the -> flow arrow. Drift-lock: a python test that extracts the keyword tables from parse.rs and asserts every parser keyword is covered by the tmLanguage (and flags tmLanguage keywords the parser no longer accepts). Docs: docs/guides/editors.md linked from docs/index.md.

<!-- ticket:T-0140 -->
```yaml
id: T-0140
title: ticket id allocator ignores tickets-archive.md -- new ids collide with archived
  tickets
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
Found immediately after the first post-archive frob ticket new: allocation scans only the active tickets.md for the max id, so a freshly archived queue restarts at T-0001, colliding with archived ids and making the merged active+archive queue unloadable (DuplicateId on every command). Fix: allocate from the max across BOTH ledgers (load_queue already merges them; reuse that path), plus a regression test: archive a ledger, file a new ticket, assert the id continues the sequence and the merged queue loads.

<!-- ticket:T-0141 -->
```yaml
id: T-0141
title: 'cache corrupt-recovery crashes on Python 3.12 sqlite: DROP TABLE raises before
  rebuild'
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
CI (python 3.12) fails tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated: cache.connect detects the unreadable db (logs 'rebuilding') but _apply_schema then runs DROP TABLE IF EXISTS on the same corrupt connection and 3.12's sqlite raises sqlite3.DatabaseError('file is not a database') -- the T-0019 delete-and-rebuild contract never engages. Local 3.11 passes, so the recovery path is version-sensitive. Fix: when the db is detected unreadable (or when any DatabaseError escapes schema application), CLOSE the connection, DELETE the file, and reconnect fresh instead of issuing DDL over the corrupt handle; must pass on 3.11 AND 3.12 (parametrize CI already covers both).

<!-- ticket:T-0142 -->
```yaml
id: T-0142
title: standalone frob check crashes FileNotFoundError when ruff/ty binaries absent
  -- wheel declares no tool deps
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
The T-0133/T-0135 standalone CI job (bare wheel, clean venv) fails its no-traceback assertion: frob check's _run_ruff shells out to 'ruff' which the wheel neither declares as a dependency nor guards against being absent -- FileNotFoundError propagates through _run_tasks_concurrently as a raw traceback. Same exposure for ty and any other spawned tool. Fix BOTH layers: (1) declare ruff (and ty) as real [project] dependencies so a standalone install is fully functional out of the box (they are pip-installable; pin compatibly with the dev pins); (2) defense in depth per the natives-less precedent -- a missing tool binary becomes a typed ToolResult failure ('tool unavailable: ruff -- install X or use make install-tool') instead of an exception, covered by a monkeypatched-absence test. The CI job must then pass un-gated.

<!-- ticket:T-0143 -->
```yaml
id: T-0143
title: 'std.cwe catalog: transcribe the cwe-top-25 view (and stub-free ASVS decision)'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
Phase A shipped the 9 charter core-reframe CWEs backing owasp-top-10 only; cwe-top-25 / owasp-asvs / cwe-1000 were deliberately not stubbed so THREAT001 cannot lie. User asks for fuller coverage. Scope: transcribe the current MITRE CWE Top 25 into WeaknessEntry rows -- each with real cite URL, accurate title, meaningful mitigation, capability_kind where the charter's instantiation semantics genuinely apply, and honest OutOfScopeEntry rows (with specific reasons) for entries whose preconditions the kernel cannot yet express (matching the T-0114 discipline). Add the cwe-top-25 view; extend tests: view completeness proves, per-entry data spot checks, and at least two new fired-obligation cases for newly-instantiable kinds. owasp-asvs/cwe-1000: make an explicit documented decision (transcribe, or keep unstubbed with rationale in threat.md) rather than silence. Pin the catalog to a named CWE release version per the charter's staleness-review requirement.
