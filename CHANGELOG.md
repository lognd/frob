# Changelog

All notable changes to `frob` are recorded here. Format is loosely
Keep-a-Changelog; entries reference the ticket id (`T-####`) that shipped
them so the full rationale is always one `frob ticket show` away.

There has never been a tagged release of this project before. `0.2.0` is
the first. Everything below landed on `main` between the initial commit
(`ad79fd6`, tree-sitter/jinja2 scaffold) and the tip at the time of this
release (393 commits). The version was bumped from the placeholder
`0.1.0a0` because the alpha tag no longer describes the project: 161
tickets closed across five strata phases, a threat/CWE/CVE/compliance
obligation catalog, a capability exhaustiveness matrix, a design lint
family, smart-dup (frob-core), the extending-frob guide series, and a
release gate of its own are all live and gated by `frob check`. This
list is derived mechanically from every `state: done` ticket in
`tickets.md` + `tickets-archive.md` at merge time; the claimed count
matches `grep -oE 'T-[0-9]{4}' CHANGELOG.md | sort -u | wc -l` exactly.

## [0.307.0] - unreleased

- T-1423: frob check crashes with an unhandled database is locked under concurrent load

## [0.306.0] - unreleased

- T-1428: WIRE001: refuse a ticket that adds code nothing outside its own tests can reach

## [0.305.0] - unreleased

- T-1421: BUG002: a bug ticket must prove the defect no longer reproduces -- evidence must fail at the parent commit

## [0.304.0] - unreleased

- T-1422: frob ticket accept can only append: add amend and remove for acceptance criteria, with a recorded reason

## [0.303.0] - unreleased

- T-1270: arch: 32-file LARGE001 residue after T-1195 split

## [0.302.0] - unreleased

- T-1410: Wire gate_claims_verified into close/land so the T-1399 guard actually fires

## [0.301.0] - unreleased

- T-1399: Evidence binding does not verify the criterion: land closed T-1276 against 116 live TEST005 findings

## [0.300.0] - unreleased

- T-1391: FMT001's Tier-A fix pass rewrites the whole tree, colliding with land scope discipline

## [0.299.0] - unreleased

- T-1341: Tier-A auto-fix handler: write the paired suppression in canonical order, idempotently

## [0.298.0] - unreleased

- T-1375: frob-coverage.lock.json was rewritten during a session where no run stamped it

## [0.297.0] - unreleased

- T-1384: frob ticket close must check the ticket's own doc/strata/REL obligations before allowing the close

## [0.296.0] - unreleased

- T-1385: Logging handler holds a stale captured sys.stderr, polluting stderr assertions and crashing xdist workers

## [0.295.0] - unreleased


## [0.293.0] - unreleased

- T-1358: T-1340 land desynced .frob-release.json from pyproject.toml, blocking all lands

## [0.292.0] - unreleased

- T-1363: A failed coverage run must not overwrite a good stamp or ratchet floors down

## [0.291.0] - unreleased

- T-1348: Land auto-fix phase must be transactional and leave a safe recovery path

## [0.290.0] - unreleased

- T-1340: SUPPRESS001 detector: suppression-dialect registry + evidence-driven mismatch detection

## [0.289.0] - unreleased

- T-1347: frob ticket brief emits concurrent sibling leases so dispatch is one line

## [0.288.0] - unreleased

- T-1327: mutate: stale mutation-backup journal restore clobbers live in-progress edits

## [0.287.0] - unreleased

- T-1336: RENDER001 x4 + ARCH001 + COV007/COV001 residue in src/frob/refactor

## [0.286.0] - unreleased

- T-1258: ledger v2: land merge story on native git per-file merge, retire frob-ledger driver

## [0.285.0] - unreleased

- T-1203: strata: may-mutation audit -- prove every may is load-bearing and double-detected

## [0.284.0] - unreleased

- T-1197: refactor: reference-rewrite engine (resolve/plan/apply/verify pipeline)

## [0.283.0] - unreleased

- T-1250: compliance triage: CMPL-FROB-CATALOG-ENTRIES row -- the 6 RegulationEntry units counted against themselves

## [0.282.0] - unreleased

- T-1234: fix LANG002 rationale text still naming kotlin as unregistered

## [0.281.0] - unreleased

- T-1261: gates --fix Tier-A batch 2: fmt/registry-regen/release-sync/WAIVE004 handlers

## [0.280.0] - unreleased

- T-1242: compliance: exposure:public-web attr + PRIVACY-NOTICE RegulationEntry -- public web-facing nodes demand a privacy-policy mitigation

## [0.279.0] - unreleased

- T-1252: strata: migrate design/frob.strata off deprecated fs/fs-read spellings

## [0.278.0] - unreleased

- T-1194: arch: split remaining seams of _land_merge.py/_land_finalize.py -- T-1189 residue

## [0.277.0] - unreleased

- T-1192: arch: large-file residue after T-1074/T-1186/T-1187 splits (34 unowned LARGE001 findings)

## [0.276.0] - unreleased

- T-1188: arch: split remaining ~7 gate families out of src/frob/gates/__init__.py (7309 lines) -- T-1187 residue

## [0.275.0] - unreleased

- T-1173: bug: cross-worktree lease not renamed when a draft ticket is renumbered at land

## [0.274.0] - unreleased

- T-1186: arch: split tickets/_land.py (4973 lines) -- T-1171 residue

## [0.273.0] - unreleased

- T-1187: arch: split remaining ~8 gate families out of src/frob/gates/__init__.py (7960 lines) -- T-1183 residue

## [0.272.0] - unreleased

- T-1183: arch: split remaining ~9 gate families out of src/frob/gates/__init__.py (8015 lines) -- T-1174 residue

## [0.271.0] - unreleased

- T-1171: arch: extract tickets/__init__.py done-report/review/drop/attach family + split _land.py -- T-1152 residue

## [0.270.0] - unreleased

- T-1177: fix-engine: Tier-A auto-carry of split-carried waivers (T-1137 child; coordinator decision recorded)

## [0.269.0] - unreleased

- T-1176: gates: named waiver presets -- frob:waive RULE preset=<name> resolving to one documented reason text

## [0.268.0] - unreleased

- T-1179: land: draft renumbering allocated an id already taken on main, clobbering a main-side block (T-1090 gap on the land path)

## [0.267.0] - unreleased

- T-1180: coverage pipeline: flake-tolerant end-to-end -- serial rerun of failures, stale-data cleanup, deflation guard before stamp

## [0.265.0] - unreleased

- T-1170: arch: split remaining ~11 gate families out of src/frob/gates/__init__.py (8349 lines) -- T-1159 residue

## [0.264.0] - unreleased

- T-1161: doctor/testing: detect root-venv entrypoint shebangs pointing outside this venv; collector must fail loudly, not emit 6219 COV003s

## [0.263.0] - unreleased

- T-1163: fix: CLI_WIRING_FILES still points at retired src/frob/app/ticket_runner.py

## [0.262.0] - unreleased

- T-1152: arch: extract tickets/__init__.py evidence/transition + done-report/review/drop/attach families + split _land.py -- T-1151 residue

## [0.261.0] - unreleased

- T-1159: arch: split remaining ~12 gate families out of src/frob/gates/__init__.py (8408 lines) -- T-1140 residue

## [0.260.0] - unreleased

- T-1148: check: detect missing/stale strata_core+frob_core natives and fail honestly (or auto-build) instead of 43 bogus DRIFT002s

## [0.259.0] - unreleased

- T-1154: land: take main's side for ledger/archive files the ticket did not deliberately edit (wrong-side-merge corruption, 3rd occurrence)

## [0.258.0] - unreleased

- T-1134: gates: INV006 split-assist -- detect verbatim-moved claim prose and carry/suggest the source file's waiver

## [0.257.0] - unreleased

- T-1155: gates: new-gate-rule-acceptance preflight lost _KNOWN_GATE_RULES after the _waive.py move -- resolve dynamically, fail loudly on miss

## [0.256.0] - unreleased

- T-1150: strata: frob sys sync-interface -- measure and update interface= attrs mechanically (SYS104-mandatory upkeep)

## [0.255.0] - unreleased

- T-1138: gates --fix Tier-A batch 1: directive-form rewrite + unique anchor-slug correction + TICK002 renumber

## [0.254.0] - unreleased

- T-1151: arch: extract remaining tickets/__init__.py families (setters/evidence/done-report) + split _land.py -- T-1123 residue

## [0.253.0] - unreleased

- T-1123: arch: extract remaining tickets/__init__.py families + split _land.py -- T-1108 residue

## [0.252.0] - unreleased

- T-1140: arch: split remaining ~13 gate families out of src/frob/gates/__init__.py (T-1115 residue after DEBT/DEPR)

## [0.251.0] - unreleased

- T-1061: wire SYS205 mode-conformance into CLI dispatch + waiver channel + docs

## [0.250.0] - unreleased

- T-1130: tickets: ticket new/drop/fail auto-commit their ledger transition on main (parity with T-1054 start)

## [0.249.0] - unreleased

- T-1127: serve: RPC surface for exports/stats proxying (T-1106 residual; outline/map/xref moot pending T-0802 sunset)

## [0.248.0] - unreleased

- T-1131: tickets: fail/retire releases leases; doctor flags leases on nonexistent worktrees

## [0.247.0] - unreleased

- T-1126: daemon: wire run_coverage_wait through the daemon-owned coverage lease RPC (T-1097 follow-up)

## [0.246.0] - unreleased

- T-1132: tickets: validate blocked_by/parent ids at write time; doctor scans for malformed edges

## [0.245.0] - unreleased

- T-1128: daemon: reconcile CLI payload shapes to proxy graph-query/check-delta/touched-tests/doable (T-1106 residual)

## [0.244.0] - unreleased

- T-1025: strata SYS203: make shared-store-write contention consult a resource's declared arbiter, drop tickets_ledger waivers

## [0.243.0] - unreleased

- T-1099: strata-core: split parse.rs (4346 lines) into grammar-family modules

## [0.242.0] - unreleased

- T-1100: frob ticket flow: created/day vs landed/day vs net + naive burn-down ETA (one table, builds on T-0938 velocity mining)

## [0.241.0] - unreleased

- T-1114: arch: abstraction-opportunity gates package extraction (T-1082 remainder)

## [0.240.0] - unreleased

- T-1115: arch: split remaining ~14 gate families out of src/frob/gates/__init__.py (~9802 lines) -- T-1077 residue refile

## [0.239.0] - unreleased

- T-1029: ticket CLI: add acceptance criteria to an existing ticket (only ticket new supports --acceptance)

## [0.238.0] - unreleased

- T-1085: arch: abstraction-opportunity app package extraction (T-0393/T-1067 remainder, 5 findings)

## [0.237.0] - unreleased

- T-1122: arch: extract doable/leases/scope-breadth family from tickets/__init__.py (T-1108 partial)

## [0.236.0] - unreleased

- T-0671: strata: bounded/staleness-gated assume+waiver mechanism - un-droppable floor view for conformance obligations

## [0.235.0] - unreleased

- T-1097: daemon: resource leases/semaphores (coverage=1 writer) arbitrated by the socket daemon

## [0.234.0] - unreleased

- T-1082: arch: abstraction-opportunity gates package extraction (T-0393/T-1067 remainder, 29 findings)

## [0.233.0] - unreleased

- T-1095: daemon: cross-worktree single-flight coverage/collection keyed by source digest

## [0.232.0] - unreleased

- T-1059: detector: frob ticket start warns when worktree is N+ commits behind main tip

## [0.231.0] - unreleased

- T-1081: arch: ARCH102 fires on newly-split src/frob/gates/_waive.py (35 exports, 4 clusters)

## [0.230.0] - unreleased

- T-1088: implement 5 statically-detectable-only SC-* supply-chain detectors with no enforcing check today

## [0.229.0] - unreleased

- T-1027: sequential-independent-awaits should suggest asyncio.gather (T-0698 disclosed cut)

## [0.228.0] - unreleased

- T-0668: strata: exact interface-conformance check - declared node interface == real public code surface

## [0.227.0] - unreleased

- T-1105: daemon: real version-handshake RPC on the socket daemon (replace sidecar meta-file skew detection)

## [0.226.0] - unreleased

- T-1077: arch: split remaining gate families out of src/frob/gates/__init__.py (T-0395/T-1072 remainder)

## [0.225.0] - unreleased

- T-1094: daemon: FS-watch push invalidation replaces git-status-poll warm-state key

## [0.224.0] - unreleased

- T-1103: arch: split tickets/__init__.py (4287) and tickets/_land.py (4762) -- T-1089 residue after ticket_runner.py split landed

## [0.223.0] - unreleased

- T-1093: daemon: CLI auto-proxy to socket daemon with transparent in-process fallback

## [0.222.0] - unreleased

- T-1089: arch: split ticket_runner.py (3957), tickets/__init__.py (4260), tickets/_land.py (4762) -- T-1086 residue (refile after T-1087 id collision)

## [0.221.0] - unreleased

- T-1092: daemon: standalone unix-socket JSON-RPC process + single-instance guard

## [0.220.0] - unreleased

- T-0781: vet/gates: taint rule -- repo-writable state (.git/.frob JSON or text) reaching subprocess argv requires validation or '--'

## [0.219.0] - unreleased

- T-1079: strata: model tests/**, scripts/**, frob-core, strata-core in design/frob.strata or adopt reasoned exclusions (SYS103 264-finding follow-up)

## [0.218.0] - unreleased

- T-1086: arch: split remaining T-1076 tier-2 large files (dup/_pipeline, ticket_runner, tickets/__init__, _land)

## [0.217.0] - unreleased

- T-1076: arch: split 2000-5000 line files (T-0395 remainder tier 2)

## [0.216.0] - unreleased

- T-1067: arch: abstraction-opportunity per-package extraction pass (T-0393 remainder)

## [0.215.0] - unreleased

- T-1078: land REL001 bump updates pyproject/CHANGELOG but can leave .frob-release.json version stale -- quartet desync makes every later land refuse on the T-0992 guard

## [0.214.0] - unreleased

- T-1072: arch: split src/frob/gates/__init__.py (12047 lines, T-0395 remainder tier 1)

## [0.213.0] - unreleased

- T-1069: add frob ticket tier CLI verb to mutate an existing ticket's tier

## [0.212.0] - unreleased

- T-1075: wire env.read/env.write tier-2 join (_KIND_MAP + WIRED_MODE_FAMILIES)

## [0.211.0] - unreleased

- T-1073: reconcile FAMILY_MODES 'proc' vs vet registry's 'exec' kind naming mismatch

## [0.210.0] - unreleased

- T-0771: capability taxonomy: wire net/env/proc/ffi mode split + sibling-repo migration (T-0717 follow-up)

## [0.209.0] - unreleased

- T-0938: sprint velocity/burndown derived from ledger state-transition history

## [0.208.0] - unreleased

- T-0667: strata: SYS-COV coverage-totality check - every capable module binds to a modeled node

## [0.207.0] - unreleased

- T-0871: exports policy residue: drive all frob-exports missing-symbol lines to zero (9 packages, 57 symbols)

## [0.204.0] - unreleased

- T-1052: DEPR005: callgraph-resolved references + line-insensitive baseline keying (bare-name text match plus file:line keys red-main on nearly every land)

## [0.203.0] - unreleased

- T-1054: frob ticket start from a worktree leaves the root ledger state transition uncommitted -- DirtyMain then blocks every land until a human commits it

## [0.202.0] - unreleased

- T-0701: strata mode-conformance enforcement: prove each node's code OBEYS its declared access mode (read/append/write/exclusive)

## [0.201.0] - unreleased

- T-0861: frob-dup: triage src/frob/** extraction-candidate groups (25 groups, split from T-0597)

## [0.200.0] - unreleased

- T-1022: EXHAUST001/002 turn-on debt burn-down: 190 escape-hatch sites (135 unknown-escape, 55 named-escape)

## [0.199.0] - unreleased

- T-1047: vet/opaque: extend RUNTIME_OPAQUE_CONSTRUCTS + OPAQUE_SOURCE_INVISIBLE for ~25 taxonomy runtime-opaque rows found unaddressed by T-0666, plus Rust struct-field / C++ pointer-to-member alias tracking

## [0.198.0] - unreleased

- T-0602: serve: per-obligation dependency-tracked partial re-evaluation inside gate dispatch

## [0.193.0] - unreleased

- T-0862: frob-dup: triage tests/**-only near-dup groups (105 groups, split from T-0597)

## [0.192.0] - unreleased

- T-0690: frob:raises directive: declared exception surfaces at FFI boundaries, cross-checked where statically visible

## [0.191.0] - unreleased

- T-0894: Registry-backed gates (COMPLIANCE005/REG*/DEC*) cannot distinguish never-adopted from deleted-registry

## [0.190.0] - unreleased

- T-1011: auto-sync check-coverage gate_rule_entries at land + generate command tables from argparse registry

## [0.189.0] - unreleased

- T-1005: frob ticket reverify: re-run close verification on a done ticket without state transition

## [0.188.0] - unreleased

- T-1010: generate _KNOWN_GATE_RULES from the T-0964 scanner (registry = scan, allowlist only for retired ids)

## [0.187.0] - unreleased

- T-1009: single-source version: frob release sync regenerates the quartet + REL coherence error

## [0.186.0] - unreleased

- T-0998: scope generation: doc-edge + code-edge closure validation (no code without its docs in scope and vice versa) + private-helper capture

## [0.185.0] - unreleased

- T-0997: coverage pipeline: merge subprocess coverage and exclude .j2 templates from the module map (34% join fraction)

## [0.184.0] - unreleased
- coordinator repair: versions 0.183.0/0.184.0 were hand-bumped after two
  land REL001 recompute collisions (T-0976/T-0989 incidents; producer fix
  tracked under the churn epic); this entry reconciles the changelog and
  release manifest with pyproject's 0.184.0.

## [0.182.0] - unreleased

- T-0989: Split frob.lang's tree-sitter node utilities into their own module

## [0.181.0] - unreleased

- T-0976: ARCH001 burn-down: remaining 47 long-function findings

## [0.180.0] - unreleased

- T-0960: static checks: kernel/userspace-interface classification + per-process cgroup resource-bound declaration obligations

## [0.179.0] - unreleased

- T-0584: PRE001 catch-22 on slow mounts: sweep needs a timeout/partial-state or async design (T-0355 item 2)

## [0.178.0] - unreleased

- T-0437: Doc-pointer resolution gate: every doc reference of a RECOGNIZED resolvable shape must resolve (hardened closed-set, not fuzzy 'seems to point')

## [0.177.0] - unreleased

- T-0703: strata starvation/throughput obligations: serialization-point utilization, writer starvation, unbounded waits

## [0.176.0] - unreleased

- T-0417: Evidence integrity round 2: close still not converged -- empty-scope bypass, no re-verify-at-close, vacuous-test passes (docs/audits/tickets-testing-round2.md)

## [0.175.0] - unreleased

- T-0700: strata grammar: access modes + shared-resource/lease declarations for contention proofs

## [0.174.0] - unreleased

- T-0652: strata: exactly-once vs at-least-once delivery-semantics declaration on queues

## [0.173.0] - unreleased

- T-0953: port archgate's near-duplicate body-similarity clustering to frob_core (measured rust-candidate sub-boundary)

## [0.172.0] - unreleased

- T-0930: move audit-proven frob check hot paths to Rust in frob_core (maturin natives)

## [0.171.0] - unreleased

- T-0948: frob.perf collectors cannot see thread-pool/process-pool gate dispatch

## [0.170.0] - unreleased

- T-0715: ticket organization model: epic -> story -> ticket tiers, sprint grouping, and team views

## [0.169.0] - unreleased

- T-0688: exhaustive-exception gate + errors-as-values advisory over may-raise sets

## [0.168.0] - unreleased

- T-0922: perf: shared interprocedural effect-summary substrate for all PERF rules (sub-call tracking)

## [0.167.0] - unreleased

- T-0651: strata: MESSAGE SCHEMA VERSION obligation on events/queues

## [0.166.0] - unreleased

- T-0918: Wire derived_state_lock exclusive side into dup/graph cache rebuilders (needs process-wide reentrancy signal)

## [0.165.0] - unreleased

- T-0892: arch: fold TypeDesignCategory into ArchCategory once _models.py lease is free (T-0621 follow-up)

## [0.164.0] - unreleased

- T-0919: done-report's internal check_gates/check_gate_findings spawns are too slow for CLI foreground use (T-0887 follow-up)

## [0.163.0] - unreleased

- T-0917: MCP tool mirror for frob perf hot (T-0712 follow-up)

## [0.162.0] - unreleased

- T-0887: done-report --base-ref hangs when the named base ref does not exist in the clone

## [0.161.0] - unreleased

- T-0712: hot-graph query surface + slow-operation advisories + perf regression ratchet

## [0.160.0] - unreleased

- T-0650: strata: transactional-boundary obligation on multi-write ops

## [0.159.0] - unreleased

- T-0686: python may-raise resolver: raise sites + callee propagation + builtin-raiser table, Unknown fail-closed

## [0.158.0] - unreleased

- T-0628: frob graph affects CLI subcommand + digest-drift gate (T-0325 follow-on)

## [0.157.0] - unreleased

- T-0889: ticket CLI write-back clobbers externally-replaced ledger with stale in-memory snapshot (reverted 3 done tickets)

## [0.156.0] - unreleased

- T-0775: perf: loop-invariant effectful call detector (spawn/fs-walk callee in a loop with loop-invariant args)

## [0.155.0] - unreleased

- T-0681: arch TS adapter phase 2: interface/type-alias/enum declarations + TSX

## [0.154.0] - unreleased

- T-0864: natives build subcommand: frob-owned maturin develop per [natives] crate with git-common-dir shared CARGO_TARGET_DIR

## [0.153.0] - unreleased

- T-0765: frob perf CLI: live collector wiring (perf/V8/JFR + python sampler) end-to-end subcommand

## [0.152.0] - unreleased

- T-0638: frob deprecated CLI subcommand: list deprecations with sunset/ticket status

## [0.151.0] - unreleased

- T-0625: arch: module dependency cycle detection (ARCH1xx)

## [0.150.0] - unreleased

- T-0756: self-audit-green-at-land + new-gate-rule end-to-end acceptance policy (kill invoked-by-nothing structurally)
- T-0646: strata: BACKPRESSURE bounded-intake obligation on queues/consumers

## [0.149.0] - unreleased

- T-0620: arch: DIP layering contract (declared allowed-module-dependency graph) + no-DI construction smell

## [0.148.0] - unreleased

- T-0723: lang: wire kotlin into central dispatch (_EXTENSION_TABLE + RawSymbol walker + COMMENT_TYPES)

## [0.147.0] - unreleased

- T-0840: path-sensitive per-call-site state verification (ordered call graph)

## [0.146.0] - unreleased

- T-0641: strata: RETRY backoff+jitter + non-idempotent-op guard + IDEMPOTENCY key obligation

## [0.145.0] - unreleased

- T-0719: check: COV002/SCOPE001/TODO001 hard-error on a genuinely git-less root, not just a real repo's bad diff

## [0.144.0] - unreleased

- T-0618: arch: LSP checks (ARCH1xx) -- override contract violations

## [0.143.0] - unreleased

- T-0711: hot-graph sketch store: log-bucket quantile sketches with decayed merge in .frob sqlite

## [0.142.0] - unreleased

- T-0859: DERIVED001 cross-process TOCTOU: a concurrent frob process can rewrite .frob between the integrity precheck and a stage's read

## [0.141.0] - unreleased

- T-0727: arch: PythonAdapter never detects class-level annotated fields (_py_class_fields gates on a nonexistent expression_statement wrapper)

## [0.140.0] - unreleased

- T-0679: flake quarantine: recent-tail-window variant of is_hard_regression

## [0.139.0] - unreleased

- T-0738: worktree warm pool: frob scaffold pool N pre-warmed worktrees with background refresh

## [0.138.0] - unreleased

- T-0858: xref sunset reevaluation: consumer-audit need is real and recurring but agents answer it with grep -- fold into exports/graph surface before 2026-10-01 deletion

## [0.137.0] - unreleased

- T-0844: wire TEST016 mutation-evidence obligation into frob ticket close (not just land)

## [0.136.0] - unreleased

- T-0857: mutate: crashed harness leaves mutants on disk -- journal originals and detect/restore leftovers

## [0.135.0] - unreleased

- T-0600: frob-exports triage: src/frob/gates, src/frob/graph, src/frob/process/parsers, src/frob/registry (14 symbols across 4 packages)

## [0.134.0] - unreleased

- T-0604: derived-state manifest: persist fingerprints and detect drift across runs

## [0.133.0] - unreleased

- T-0847: land: wip pre-land snapshot fails on line-ending phantom-dirty worktrees (nothing to commit after add -A renormalizes)

## [0.132.0] - unreleased

- T-0849: pattern registry phase 3: work or disposition the 41 recommender rows previously deferred to T-0605

## [0.131.0] - unreleased

- T-0851: frob check: FMT001 gate for non-canonical frob: directive lines (T-0441 follow-up)

## [0.130.0] - unreleased

- T-0441: frob fmt: auto-wrap over-length frob: directive comment lines via T-0286 continuation so ruff E501 never fires on waive reasons

## [0.129.0] - unreleased

- T-0846: land: ClaimDivergence compares exact error counts across run contexts; scoped-flaky rules make landing a refresh-retry loop

## [0.128.0] - unreleased

- T-0605: design-pattern recommender phase 2: Adapter, Flyweight/pool, Observer, anemic-domain-model, poltergeist/lava-flow, sequential-coupling detectors

## [0.127.0] - unreleased

- T-0755: adversarial evidence obligation: ticket tests must fail on a diff-scoped mutant (confirmatory-only tests flagged)

## [0.126.0] - unreleased

- T-0440: strata model debt: deploy/serve/mutate swept into coarse utility-hub node, not modeled as distinct capabilities with own effects/threat surface

## [0.125.0] - unreleased

- T-0834: ticket CLI: no kind editor; evidence-cmd runs from invoking cwd not --path

## [0.124.0] - unreleased

- T-0836: worktree sweep command: lease-aware stale-worktree cleanup (raw git sweep destroyed a live agent env)

## [0.123.0] - unreleased

- T-0838: tickets ledger: schema-extending features brick their own land (extra_forbidden on new fields, empty collections serialized)

## [0.122.0] - unreleased

- T-0839: gates: _merge_canonical_order silently drops violations of gates missing from order tuple (hit live via T-0788)

## [0.121.0] - unreleased

- T-0746: protocol verification gate: state-requirement + invalid-transition errors with recorded language-excuse discharges

## [0.120.0] - unreleased

- T-0571: frob review: structured adversarial review channel as first-class evidence

## [0.119.0] - unreleased

- T-0728: arch: wire ARCH1xx SOLID checks into analyze_project, frob.toml thresholds, gate registry

## [0.118.0] - unreleased

- T-0788: gates: register COMPLIANCE005 in the live rule set and dispatch check_cmpl_registry in frob check

## [0.117.0] - unreleased

- T-0832: land: T-0754 re-verification compares -1 sentinel when fresh check cannot run (done ticket, no lease)

## [0.116.0] - unreleased

- T-0754: captured Done-report claims: test-count and gate-state fields populated from real command output, re-verified at land

## [0.115.0] - unreleased

- T-0574: agent environment hardening: auto-inject FROB_WORKTREE/FROB_AGENT + mechanical stash guard

## [0.114.0] - unreleased

- T-0813: graph: production entrypoint wiring mark_unresolved=True into compute_protocol_summaries (opt-in flag currently invoked by nothing)

## [0.113.0] - unreleased

- T-0752: doable: priority column, in-flight/dispatchable split, and undispatched-critical staleness alarm

## [0.112.0] - unreleased

- T-0809: wire real callee-resolution + resource-tracking DSL into the T-0745 protocol summary engine

## [0.111.0] - unreleased

- T-0808: gates: WAIVE007 dangling-waiver-ref -- unresolvable BINDING ticket ref in a waiver is a warning, not silence

## [0.110.0] - unreleased

- T-0807: check: auto-suppress land-owned REL001 bump-half in worktree/ticket context (reviews keep tripping on it)

## [0.109.0] - unreleased

- T-0764: friction: archive/concurrent-ledger-rewrite silently reverts in-flight tickets start+evidence+acceptance (recovered T-0753 by hand)

## [0.108.0] - unreleased

- T-0782: leases: implement T-0476 cleanup -- unlink stale leases opportunistically + TTL for dead-agent leases (daemon stops re-simulating)

## [0.107.0] - unreleased

- T-0745: protocol summary engine: per-function fixpoint over the call graph, shared with may-raise

## [0.106.0] - unreleased

- T-0779: gates: stale-waiver detection -- waive reason citing a DONE/DROPPED ticket is an error (WAIVE-tier)

## [0.105.0] - unreleased

- T-0796: tickets CLI: --evidence-cmd with --accepts silently records evidence UNBOUND (add_cmd_evidence has no accepts param)

## [0.104.0] - unreleased

- T-0784: gitio: promote git_common_dir to the single git seam (3 divergent copies) + batch the lease-write double spawn

## [0.103.0] - unreleased

- T-0787: check CLI: wire resolve_lease pinning into --ticket resolution (promote T-0766's lost draft)

## [0.102.0] - unreleased

- T-0773: tickets: memoize git-common-dir/lease reads per CLI invocation (dozens of identical rev-parse spawns per command)

## [0.101.0] - unreleased

- T-0776: testing: subprocess spawn-budget litmus for CLI hot paths (fail on duplicate identical argv per invocation)

## [0.100.0] - unreleased

- T-0607: implement checkable-control enforcement for CMPL-* compliance registry units

## [0.99.0] - unreleased

- T-0766: lease resolution cross-talk: frob check --ticket ran against another agent's worktree via stale lease under concurrent load

## [0.98.0] - unreleased

- T-0717: capability taxonomy: mode-qualified names (fs.read/fs.write, net.connect/net.listen), one vocabulary with T-0700 modes, deprecated-alias migration

## [0.96.0] - unreleased

- T-0644: strata: HEALTH liveness+readiness obligation on every service node

## [0.95.0] - unreleased

- T-0716: ticket list: overlay live lease state so worktree-started tickets show in-progress on main

## [0.94.0] - unreleased

- T-0710: hot-graph collector: sampling profiler + normalized-model section attribution

## [0.93.0] - unreleased

- T-0627: frob check: chunked/stage-wise invocation that stays under agent foreground caps

## [0.92.0] - unreleased

- T-0736: scaffold conformance: managed boilerplate blocks (Makefile shim, guard hooks, gitignore) drift-checked by doctor across all repos

## [0.91.0] - unreleased

- T-0724: strata: wire `check_resource_contention` (SYS200-203) into the production `frob sys audit` path, threading `Module.stores` id set (`DesignIds.store_ids`) so SYS203 (shared store write) can fire; waived the 4 SYS203 findings frob's own `design/frob.strata` surfaces on `tickets_ledger` (arbitrated by `.frob/tickets.lock`, T-0458/T-0633, until T-0700's grammar can express it)
- T-0724: strata: `_gap_rule_in_scope` (`_audit.py`) now excludes SYS200-203 from `evaluate_exhaustiveness`'s own waiver-staleness sweep, matching the existing SYS100-102/HOST001-002 exclusion -- fixes a cross-family collision where a legitimate SYS203 waiver was reported stale
- T-0587: testing: real vitest/ctest test collectors (`frob.testing.collect_ts_tests`, `frob.testing.collect_cpp_tests`)
- T-0616: arch: SRP/cohesion checks (ARCH1xx) -- LCOM4, god-module, mixed-concern function (`frob.arch._srp`)
- T-0617: arch: OCP checks (`frob.arch._ocp`) -- `type-dispatch-smell` and `non-exhaustive-enum-match`, reusing T-0332's isinstance-chain detector via the new shared `frob.arch._patterns.iter_type_switch_chains`

## [0.90.0] - unreleased

- T-0630: strata/vet: wire real code binding into production discharge entrypoints (`evaluate_exhaustiveness`, `render_audit_matrix`, `plan_obligations`, `build_containment_report`) so THREAT003's G1 code-bound-predicate join actually fires outside unit tests

## [0.89.0] - unreleased

- T-0614: arch: Kotlin adapter for the normalized code model (`frob.arch._kotlin.KotlinAdapter`)
- T-0707: selfconform: SYS102 unmodeled code src/frob/registry -- model the registry package

## [0.88.0] - unreleased

- T-0612: arch: Rust adapter for the normalized code model (`frob.arch._rust.RustAdapter`)

## [0.86.0] - unreleased

- T-0636: flake quarantine: hard regression under live quarantine is invisible to both gate and alarm

## [0.85.0] - unreleased

- T-0573: frob fleet: cross-repo status, gate rollup, and ticket routing for the 9-repo estate

## [0.84.0] - unreleased

- T-0576: frob:deprecated directive: API sunset dates gated like debt

## [0.83.0] - unreleased

- T-0575: flake quarantine: per-test stability tracking + quarantine-with-ticket in frob test

## [0.81.0] - unreleased

- T-0595: strata audit G1 (full closure): bind ENDORSE boundary predicate to an OBSERVED sanitizer call site in code

## [0.80.0] - unreleased

- T-0613: wire tree-sitter-kotlin grammar into frob.lang (raw walk only, via `frob.lang._walk_kotlin`; no normalized-model mapping yet)
- T-0609: arch: normalized code model (language-agnostic node types + adapter protocol)

## [0.79.0] - unreleased

- T-0264: frob deploy generate windows: PowerShell/DSC install/status/uninstall from the manifest, drift-locked

## [0.78.0] - unreleased

- T-0325: doc-drift digest graph: warm 'what code/docs must update when X changes' query (the north-star)

## [0.77.0] - unreleased

- T-0435: DOC005, README command-table + checkable-count drift-lock -- binds README.md's command table to the live top-level subcommand registry (`frob.gates._docblocks.doc005_gate`)
- T-0332: design-pattern recommender: hallmark->pattern + anti-pattern->escape registry (advisory)

## [0.76.0] - unreleased

- T-0261: std.host windows backend: services, gMSA/service accounts, ACLs, named pipes, firewall ports

## [0.75.0] - unreleased

- T-0570: derived-state integrity manifest: doctor-first fingerprint check for every derived artifact

## [0.74.0] - unreleased

- T-0177: frob serve daemon: incremental gate evaluation over the warm obligation graph

## [0.73.0] - unreleased

T-0579: `frob ticket drop <id> --reason TEXT [--absorbed-by T-####]` is
now first-class CLI, replacing the pre-T-0579 workflow of hand-editing
`state: dropped` directly into `tickets.md` (which left leases dangling
and recorded no reason at all). `frob.tickets.drop_ticket` appends a
dated line under a `## Drop reason` body heading (same append-a-section
shape as `record_failure`'s `## Failure log`), then transitions to
DROPPED through the ordinary state machine so a held worktree lease
releases the normal way. New `TicketError.DropReasonMissing` -- a drop
with no reason is indistinguishable from a silent discard later.

## [0.72.0] - unreleased (merge-resolution bump)

Version bump to resolve a merge conflict between this branch's own
0.69.0 (T-0545/T-0552/T-0547/T-0556/T-0548, below) and `main`'s
concurrently-landed 0.71.0 (T-0322/T-0410/T-0408) -- no additional public
API change of its own, just the coordinating bump above both parents.

## [0.69.0] - unreleased (attestable coverage lock, B5)

T-0545 (docs/audits/gates-accounting.md B5): `.frob/coverage-stamp` and
`coverage.xml` are both gitignored, so no committed artifact let a
reviewer or CI verify a TEST005/006 coverage claim. `frob.gates._coverage`
gained a new committed summary artifact, `frob-coverage.lock.json`
(deliberately outside `.gitignore`'s reach, and rounded/summarized rather
than the raw xml): `write_coverage_lock`/`load_coverage_lock` write/read
it, `coverage_lock_diff` reports which modules' claimed line coverage
drifted beyond tolerance from a fresh `coverage.xml`. `stamp_coverage`
now optionally refreshes the lock itself when passed a `GraphSnapshot`,
so an existing `--stamp-coverage` call can adopt it with no new CLI flag.
New advisory gate TEST012 (WARN) flags a missing or drifted lock. Left
deliberately split for follow-up (see T-0545's Done report): wiring
`frob check --stamp-coverage`'s CLI entry point
(`frob.app.check_runner._run_stamp_coverage`) to pass its snapshot
through, and promoting TEST012 to ERROR once the lock is adopted
repo-wide.

T-0552 (docs/audits/gates-accounting.md B3): a ts/c/cpp `frob:tests` edge
credited toward TEST001-004 purely by name/path convention, with zero
execution evidence, stayed silently indistinguishable from a genuinely
executed test. `frob.gates._edge_is_native_unverified` splits that
structural-fallback check out; new advisory gate TEST013 (WARN) names
every edge relying on it, without withdrawing the underlying credit
(promoting to ERROR needs a real vitest/ctest collector, split to
T-draft-2411b5b6).

T-0547 (docs/audits/gates-accounting.md B6): `_inferred_unit_cases`
matches a public symbol to a collected test by snake-cased leaf name
alone, no module/path binding -- two different files' same-named public
functions can both clear TEST001 off one test exercising only one. New
advisory gate TEST014 (WARN) flags the ambiguity (verified: a blanket
path-correlation tightening breaks 81/81 convention matches in this
repo's own layout, so credit is left unchanged; 5 real collisions found
and split to T-draft-b7c57519).

T-0556 (docs/audits/gates-accounting.md B2): `frob.graph.lock`'s default
ack facet (`sig`) meant rewriting a documented function's BODY after ack
never tripped DRIFT001. `_facets_for_ref` now always also locks `body`
(a compat survey found only 43 lock entries repo-wide, all sig-only,
safe to change as the new default outright).

T-0548 (docs/audits/gates-accounting.md B1): TEST001, the only blocking
per-symbol test gate, is satisfied by a name-matched test with no
assertion at all (`def test_myfunc(): pass` clears it). New advisory
gate TEST015 (WARN) reuses T-0549's existing assertion heuristic to
flag it, without changing what TEST001 blocks on (the actual
coverage-tied credit tightening is cross-cutting, split to
T-draft-934c675a).

T-0567: two DEAD001 residuals in `frob.gates.__init__` resolved --
`_documented_srcs` was genuinely orphaned (deleted); `_run_jobs`/
`_timed_job` had `frob:tests` directives misplaced above the TEST
function instead of the source symbols (moved).

## [0.71.0] - unreleased (registry pipeline: INV006 source-side coverage, frob:enforces, corpus add, REG010)

T-0408: new `INV006` gate (`frob.gates.inv006_gate`, WARN severity)
extends INV003's exclusivity-claim scan from doc-only (`docs/modules`,
`docs/strata`) to SOURCE trees (`INV006_SRC_DIRS`: `src`,
`strata-core/src`, `frob-core/src`) -- the coverage-COMPLETENESS half of
T-0408's gap: INV001/INV002 only ever validated invariants that already
existed, and INV003/INV004 never looked past `docs/`, leaving well over a
hundred source docstrings/comments asserting "only"/"never...except"/
"exactly one" guarantees entirely outside any gate's reach. INV006 reuses
INV003's exact noise-filtered claim vocabulary
(`frob.gates.invariants.find_exclusivity_claims`) and treats a file as
covered by any real `frob:invariant` edge anchored anywhere in it
(joined against the same `GraphSnapshot` every other code-anchor gate
already loads), with `frob:waive INV006 reason="..."` as the disposition
path for a claim that is genuine design intent rather than an enforced
behavior.
## [0.70.0] - unreleased (misc chain: coverage --wait, DOC004 c/cpp)

T-0322: `frob test --wait-coverage` -- a foreground, single-flight,
blocking-until-fresh coverage contract. Replaces backgrounding `make
coverage` and stalling on a notification a dispatched sub-agent can never
receive (docs/guides/agent-playbook.md section 6b): the new command
blocks under a `.frob/coverage.lock` file lock (so concurrent callers
serialize onto one real run instead of each re-running the full suite),
checks the recorded coverage stamp against the current source tree
(the same staleness contract TEST006 already enforces), and either
returns immediately if already fresh or runs `make coverage-fast` and
returns a definitive fresh-or-failed result. New public API:
`frob.testing.run_coverage_wait`, `coverage_lock_path`,
`CoverageWaitOutcome`, `CoverageWaitError`.
## [0.69.0] - unreleased (T-0410 perf: parse_file run-scoped memo)

T-0410: `frob.lang.parse_file` gained a run-scoped `@memoize_per_run` memo
(T-0423's mechanism, generalized to a new call site), applied via a
first-call-deferred wrapper (`_parse_file_uncached` + the public `parse_file`
wrapper) to dodge a real `frob.lang`/`frob.check` circular import a
module-level decorator would hit. Closes a gap `_parse`'s own content-hash
cache left open: `_parse` cached the raw tree-sitter `Tree`, but `extract()`
(the symbol/comment walk over it) re-ran on every call regardless -- COV006's
rescue helpers call `parse_file` ~2000+ times per `frob check`, many repeats
on the same path across different candidate edges. Measured: isolated
`coverage_gate` profile 155.8s -> 15.9s; real `frob check`'s `coverage` stage
timing 36-45s -> 3.5-4.7s. `frob.excludes.BUILTIN_SKIP_DIRS` also gained
`.hypothesis`/`.serena` (perf audit finding M6, `docs/audits/perf.md`) --
neither has a tree-sitter grammar but every rglob-based stage was still
walking/stat'ing/opening every entry inside them.

## [0.69.0] - unreleased (INV006 source-side invariant coverage)

T-0408: new `INV006` gate (`frob.gates.inv006_gate`, WARN severity)
extends INV003's exclusivity-claim scan from doc-only (`docs/modules`,
`docs/strata`) to SOURCE trees (`INV006_SRC_DIRS`: `src`,
`strata-core/src`, `frob-core/src`) -- the coverage-COMPLETENESS half of
T-0408's gap: INV001/INV002 only ever validated invariants that already
existed, and INV003/INV004 never looked past `docs/`, leaving well over a
hundred source docstrings/comments asserting "only"/"never...except"/
"exactly one" guarantees entirely outside any gate's reach. INV006 reuses
INV003's exact noise-filtered claim vocabulary
(`frob.gates.invariants.find_exclusivity_claims`) and treats a file as
covered by any real `frob:invariant` edge anchored anywhere in it
(joined against the same `GraphSnapshot` every other code-anchor gate
already loads), with `frob:waive INV006 reason="..."` as the disposition
path for a claim that is genuine design intent rather than an enforced
behavior.

## [0.66.0] - unreleased (graph leaves + DEAD001/PARSE001, part 2)

T-0422: new `DEAD001` gate (`frob.gates._dead_symbols.dead_symbol_gate`,
WARN severity) flags a private Python function/class/method with no
call-graph caller and no `frob:tests`/`frob:describes`/`frob:invariant`
edge -- the symbol-level analog of REF001's anti-orphan file gate
(`_arch_violations_from_suggestions`, written but never wired, was the
motivating T-0418 case). `frob.graph.callgraph` gained a new public
`build_reference_graph` function: broader recall than `build_call_graph`
(catches a dispatch-table/registry bare-identifier reference, not only a
`name(...)` call token) -- `build_call_graph` alone measured a large
false-positive rate against this repo's own `app/*_runner.py` dispatch
tables during development. Python (`.py`) files only for now: Rust/
TypeScript/C use a different visibility marker than Python's
leading-underscore convention, which `callgraph`'s privacy check does
not (yet) account for -- see the gate's own docstring and T-0422's Done
report for the measured ~100% false-positive rate that scoping decision
avoids.

## [0.66.0] - unreleased (graph leaves + DEAD001/PARSE001, part 1)

T-0558: `frob.graph.GraphSnapshot` gained a `parse_failures` field (new
public `ParseFailure` model) -- a file `frob.lang.parse_file` could not
parse/read at all (any `LangError` other than the expected
`NativeParserUnavailable` degrade) used to come back as
`(True, (), (), ())`, indistinguishable from an empty file, silently
erasing its entire symbol/edge/doc-obligation set for that build (T-0404
finding 2). New standalone `frob.gates._parse_failures.parse_failure_gate`
(`PARSE001`, ERROR severity) turns a recorded failure into a real `frob
check` violation instead of a warning only visible in logs. Never cached
across builds -- a fixed file drops out of the list on its next
successful build, same as before this fix.

## [0.65.0] - unreleased

T-0461/T-0459/T-0562: `RENDER001` (bare stdout `print()` outside
`frob.render`) landed on `main` between this branch's fork point and its
merge back in; bumped here to cover that surface alongside T-0550's own
change (below) since both are unreleased public-API deltas the release
gate had not yet been stamped against.

## [0.64.0] - unreleased

T-0549/T-0550: two more gates-accounting audit fixes (T-0403 B7/B8).
`_case_count` caps a parametrized python test's counted variants to 1
unless its body actually contains an assertion-shaped construct, closing
the `@pytest.mark.parametrize(range(N))`-with-no-assertions escape from
`TEST002`/`TEST003`/`TEST009`'s minimum-case floors. `coverage_gate`
gained an optional `diff_load_failed: bool = False` kwarg: a genuinely
FAILED `working_diff` (bad `--base`, no merge-base, git error) now fires
a loud `COV002`/`SCOPE001`/`TODO001` violation instead of silently
degrading to an empty, clean-looking diff.

## [0.63.0] - unreleased

T-0541/T-0542: two gates-accounting audit fixes (T-0403 B9/B10).
`coverage_gate` gained an optional `active_ticket: str | None = None`
kwarg (COV002 now prefers the active ticket's own scope, and treats two
open tickets whose scopes ambiguously, equally cover the same file as
NOT covering it rather than picking the first match found). `run_gates`
no longer silently skips `SCOPE001`/`PRE001` when no active ticket is
derivable and the diff touches real source (only a `tickets.md`-only or
empty diff still skips cleanly) -- it now emits a blocking violation
instead, closing an off-convention-branch/`main`-commit escape from
scope and pre-work enforcement.

## [0.62.0] - unreleased

T-0555: `frob.lang` gained `partial_parse_files()`, a `reset_parse_cache`-
scoped accessor (mirroring `parse_cache_stats`'s shape) returning the
display paths of every file whose tree-sitter parse was salvaged around a
syntax error since the last reset (T-0404 finding 9) -- previously only a
scattered `_warn_if_partial_tree` (T-0434) `WARNING` log line, invisible
below `-v` and with no structured consumer, especially for Rust/C++/TS
repos with no gates stage at all (T-0546/T-0554) to notice it. Wiring a
blocking `frob check` violation off this list is a `frob.gates`-family
change tracked separately.

## [0.61.0] - unreleased

T-0424: reflexive check-coverage registry -- `docs/design/registry/
check-coverage.yaml` is a tenth `docs/design/registry/*.yaml` instance
(added to `frob.gates._registry_exhaustiveness.REGISTRY_FILES`, the same
unified gate T-0407 built, no second mechanism), seeded honestly from the
live `frob.gates.known_gate_rule_ids()` inventory (82 entries, each
self-referentially `handled_by` its own rule id) plus the `docs/audits/`
7-auditor pessimistic-pass concern families (5 cross-cutting themes + 8
per-subsystem verdicts, 13 entries, each `deferred:T-0397`, the real open
audit-remediation epic). An un-dispositioned concern reds the same
REG001-REG007 exhaustiveness gate every other registry instance is bound
to -- frob's own check-coverage is now a first-class, exhaustible,
gate-enforced registry rather than something only the user's eyeballs
audit (see docs/design/registry/README.md#check-coverageyaml-t-0424-frobs-own-reflexive-check-coverage-registry).

## [0.60.0] - unreleased

T-0407: unified registry capability -- new `frob.registry` module
(`RegistryEntry`/`Disposition`/`DispositionKind`/`RegistryFile`/
`RegistryAudit`, `load_registry_dir`, `audit_registry_file`,
`parse_disposition`) is now the single source of truth for the
`docs/design/registry/*.yaml` entry shape and disposition grammar;
`frob.gates._registry_exhaustiveness.registry_gate` (T-0343) was
refactored onto it rather than carrying a second, duplicated inline
parser. Two early-exit/partial-coverage holes the pre-unification gate
silently allowed are now closed: **REG006** (a malformed list item --
not a mapping, or missing a string `id` -- previously vanished from every
count with no trace) and **REG007** (the same `id` defined by two or
more entries anywhere in the registry, a real collision distinct from an
intentional `duplicate_of:` reference). New CLI subcommand `frob
registry audit` reports the per-file `handled`/`deferred`/`duplicate`/
`out_of_scope`/`unaccounted`/`malformed` accounting against `total`, so
"is this registry exhausted" is a one-line honest read (see
docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407).

## [0.58.0] - unreleased

T-0454: professional ticket organization -- `Ticket`/`TicketSpec` gained
`component: str | None` (freeform module/area) and `labels: tuple[str,
...]` (freeform tags orthogonal to component), both additive/optional so
every pre-existing ticket stays valid on load. New public
`set_component`/`mutate_labels` mutation functions (same single-writer,
ledger-locked pattern as `set_priority`/`mutate_scope`), `board_view`/
`BoardColumn`/`BOARD_STATES` (a fixed-column, priority-ordered board over
the whole active queue), and `epic_rollup`/`EpicRollup` (the `parent`
chain's full descendant subtree, a done/total rollup, and any BLOCKED
leaf). New CLI subcommands `frob ticket component <id> <name>`, `frob
ticket label <id> --add/--remove TAG...`, `frob ticket board
[--component/--label]`, `frob ticket epic <id>`; `frob ticket new` gained
`--component`/`--label`. Sprints/milestones and a doable/list component-
label filter were deliberately deferred as follow-ups (see
docs/modules/tickets.md#organization-components-labels-board-epics-t-0454).

## [0.57.0] - unreleased

T-0510: `frob.strata._threat` gained five `WeaknessEntry` rows in
`QUALITY_CATALOG` (CWE-916 weak-hash password storage, CWE-1321
prototype pollution, CWE-1333 ReDoS, CWE-601 open redirect, CWE-1336
SSTI), each catalog-only (`capability_kind=None`, discharged by the
`std.cve` fingerprint layer, mirroring CWE-295's precedent) -- previously
disclosed gaps `_cve_fingerprint.py`'s own docstring named as blocked on
a missing `WeaknessEntry`. `frob.strata._cve_fingerprint.CVE_FINGERPRINTS`
gained a matching real-CVE-cited needle per CWE (FP-WEAKHASH-PASSWORD-001,
FP-PROTO-POLLUTION-001, FP-REDOS-REGEX-001, FP-OPEN-REDIRECT-001,
FP-SSTI-TEMPLATE-001), 13 -> 18 entries. `docs/design/registry/
weaknesses.yaml`'s five matching `SEC-CVE-FINGERPRINT-CWE-*` rows flipped
from `disposition: deferred:T-0510` to `handled_by:SEC-CVE-FINGERPRINT-001`
with the new fingerprint ids cross-referenced.

T-0511: `frob.strata._threat.BenignCapability` gained an optional
`family: str | None` field ("security" | "quality", `None` for the
built-in `DEFAULT_BENIGN_CAPABILITIES` tuple) -- mandatory for every
`load_repo_benign_capabilities` (`[[strata.benign_capabilities]]`
frob.toml) entry, verified at load time against that family's own
catalog: an entry whose `kind` is already classified in the family it
names is rejected (`Err(StrataError.MalformedBenignConfig)`) rather than
accepted as a blanket, unverified excuse (strata audit G12).

T-0512: `frob.strata._audit.AuditReport` gained
`narrower_than_baseline: tuple[str, ...]` -- every security-family
baseline view (`VIEWS` union `CWE_TOP_25_VIEWS`) a `frob sys audit` run's
configured `security_views` did not include (empty for a genuinely
exhaustive run); `frob sys audit`'s CLI printer now discloses this
unconditionally instead of a PROVED report silently meaning "narrower
than the full catalog baseline" (strata audit G6).

## [0.56.0] - unreleased

T-0358: `frob.app.config.stale_install_warning` -- a loud stderr warning,
printed by `main()` before every subcommand dispatches, when the running
`frob` is a globally installed binary whose version differs from the
current checkout's `pyproject.toml`-declared version (the stale-global-
binary phantom-numbers trap: an old installed gate implementation silently
running against a newer working tree, producing wrong violation counts).

T-0433: `frob.graph.cache._FINGERPRINT_PACKAGES` (G6, T-0402 residual) is
now derived from `frob.lang.GRAMMAR_FINGERPRINT_PACKAGES` (a new public
constant -- the tree-sitter grammar packages every non-`.strata` language
in `frob.lang` loads through) instead of a hand-copied tuple, so a future
grammar-loading package change updates the cache-invalidation fingerprint
automatically. Also fixed G7 (T-0402 residual): `_parse_source_file_fresh`
now stores `parsed.content_hash` -- the hash `frob.lang` computed from the
exact bytes it read and parsed -- rather than a hash the caller read
separately beforehand, closing the hash/parse TOCTOU window where a write
between the two reads could store fresh symbols under a stale hash.

## [0.55.0] - unreleased (tickets chain 3: frob:debt)

T-0412: `frob:debt` vs `frob:waive` -- a TEMPORARY, ticket-bound, tracked
exception distinct from `frob:waive`'s PERMANENT one. New public API:
`EdgeKind.DEBT`, `frob.gates.debt_gate`/`list_debt`/`DebtEntry`, and the
`DEBT001`/`DEBT002`/`DEBT003` rule ids (malformed directive / non-open
ticket / expired `until`). `frob.gates.release_gate` (REL001) now
additionally fails while ANY `frob:debt` is open, expired or not -- debt
is collected and re-raised before a release, never silently carried
forward. New `frob debt [--json]` CLI (`frob.app.debt_runner`) lists every
outstanding entry (rule, site, ticket, until, expired). Migration of the
~143 existing debt-shaped `frob:waive` directives to `frob:debt` is
deliberately NOT done in this release -- see docs/guides/extending/
comment-dsl-directives.md's migration-guidance note; it is a follow-up
burndown ticket.

## [0.54.0] - unreleased (tickets chain 3: intent journal)

T-0456: crash/interrupt recovery, the remaining delta after T-0473
(cross-worktree lease registry)/T-0476 (reconcile)/T-0479 (own-block ledger
splice) had already landed the rest. Added `frob.tickets._journal` (new
public `write_intent`/`clear_intent`/`read_all_intents`/`LandIntent`/
`JournalError`/`journal_dir`): `frob ticket land` now records a small
`.frob/journal/<ticket-id>.json` marker before it starts mutating anything
and clears it in a `finally` block on every exit, so a marker outliving the
process means it crashed mid-land. `frob ticket reconcile` gained a third
anomaly class, orphaned land intents, reported every run and cleared
(never auto-resumed) under `--apply`. `frob.tickets._store.atomic_write`
now `fsync`s the temp file before the `os.replace` that makes it visible,
closing the "rename completed but data unflushed" crash window for every
`tickets.md`/`.frob-release.json`/lease/journal write.

T-0507: extended the T-0431 `FROB_WORKTREE` lease guard to `frob release
stamp` (`frob.release.stamp`, new `ReleaseError.WorktreeLeaseViolation`
member) and `frob ack` (`frob.app.ack_runner.run`) -- the two remaining
mutating entry points T-0431 had not yet covered.

## [0.53.0] - unreleased

T-0517: `frob.dup._cache`'s `dup.db` gained a version fingerprint (reusing
`frob.graph.cache._compute_fingerprint`, the T-0243 pattern) -- a
`dup.db` written under an older frob/tree-sitter grammar version now has
its `fingerprints`/`verdicts` rows invalidated on reconnect instead of
silently serving stale content-addressed rows under an algorithm change.
`tests/test_dup_cross_lang.py` also no longer leaks an untracked
`.frob/dup.db` into the tracked fixture directory it runs against.

T-0518: `frob.dup._exhaustiveness.DUP_CLAIMS` gained the r5/typescript
cell (`compute_total`/`computeTotal`, T-0494's fixture), mirroring the
r5/rust entry T-0487 already added -- the cross-language R5 capability
this repo actually has is now reflected in the exhaustiveness matrix
instead of falling through the generic non-python language-gap excuse.

## [0.52.0] - unreleased (tickets-bugs chain)

T-0446: `frob.tickets.scope_matches` gained an optional `kind` keyword --
when `kind=TicketKind.FEATURE`, the three well-known CLI-wiring files
(`src/frob/__main__.py`, `src/frob/app/config.py`,
<!-- frob:waive DOC006 reason="src/frob/app/ticket_runner.py is a frozen historical release-note reference (0.52.0); file has since been split into a package" -->
`src/frob/app/ticket_runner.py`, `frob.tickets._models.CLI_WIRING_FILES`)
are implicitly in scope, mirroring `LEDGER_PATH`'s always-in-scope rule
(T-0241). The SCOPE001 gate (`scope_gate`) now passes `ticket.kind`
through, so a feature ticket adding a new `frob ticket <subcommand>` no
longer needs a `frob ticket scope --add` per wiring file just to avoid
SCOPE001 -- the exact "scope-expansion ceremony" T-0323 (adding `frob
ticket merge-driver`) hit and T-0446 was filed to close. `kind=None` (the
default, and every pre-T-0446 call site) preserves prior behavior exactly;
non-FEATURE tickets still trip SCOPE001 on these files as before.

## [0.51.0] - unreleased (gates-calibration chain)

- T-0506: COV006's disclosed T-0483 false-positive shape (a test reaching
  its bound private target only via a same-file public wrapper) is now
  rescued by a gate-local one-hop lookahead
  (`_cov006_public_wrapper_reachable`), reducing COV006 from 98 to 89
  findings on this repo without weakening `frob.graph.callgraph`'s
  public-boundary-stop guarantee (still load-bearing for frob.dup/arch).
  Residual burndown filed as a follow-up ticket per its count.
- T-0509: INV003/INV004 calibrated -- claim-shape scanning now strips
  fenced/inline code, link targets, and table rows before matching, and
  requires a claim-verb in the same sentence as the trigger word
  (`frob.gates.invariants._is_claim_shaped`); INV003 is scoped to
  `INV003_SPEC_DIRS` (docs/modules, docs/strata) rather than all of
  docs/**.md; markdown-side `<!-- frob:waive INV003|INV004
  reason="..." -->` support lets a genuine-but-unprovable claim be
  dispositioned honestly. INV003+INV004 combined warnings: 765 -> 604.

## [0.50.0] - unreleased

T-0411: queue health + priority model. Tickets carry a `priority`
(low/medium/high/critical, default medium) field; `frob ticket doable`
orders by priority first, then age (previously age-only); a new TICK004
gate warns (escalating to error) when a queued/planned ticket sits past
its priority-specific rot-day threshold (default 3/7/30/90 days for
critical/high/medium/low, configurable via `frob.toml`'s `[tickets]`
table); `frob ticket priority <id> <level>` reprioritizes an existing
ticket through the single-writer ledger path.

## [0.49.0] - unreleased (reconciliation)

Another parallel landing chain (T-0335/T-0462/T-0452/T-0465, gates-area
tickets worked sequentially in one worktree) independently claimed
version numbers 0.44.0-0.46.0, colliding with the land-machinery/strata
chains reconciled at 0.47.0/0.48.0 below. Final reconciled version is
0.49.0; that chain's own three sections follow immediately below under
the numbers they were authored with, same reconciliation pattern as
0.47.0.

## [0.46.0] - unreleased (gates-area chain)

Public-API surface change since 0.45.0 (mechanical semver via REL001): an
additive (minor) bump -- new hazard-guard gate rule.

- T-0465: EXCL001, a new (ERROR-severity, unwaivable) gate rule flagging
  `.git/info/exclude` entries that shadow git-tracked source. `.git/
  info/exclude` is the SHARED common-dir file across every worktree of a
  clone -- an agent once added `src/frob/render/` to it to hide its own
  scratch files, silently blinding `git status`/`git add -A` to every
  NEW file added under that real source directory afterward, in every
  worktree, until the T-0448 foundation went missing. New public
  `frob.gates.exclude_hazard_gate` (`src/frob/gates/_exclude_hazard.py`).
  Added the same hazard as a hard rule in
  docs/guides/agent-playbook.md (section 1c).

## [0.45.0] - unreleased (gates-area chain)

Public-API surface change since 0.44.0 (mechanical semver via REL001): an
additive (minor) bump -- new advisory invariant density lint.

- T-0452: INV004, a new advisory (warn-severity, never fails `frob
  check`) invariant gate rule complementing INV003's per-claim check
  with the section-level inverse: a `docs/**.md` section using ANY
  normative language ("must", "must not", "never", "always", "shall",
  "guarantees", "ensures", "requires", plus INV003's exclusivity
  vocabulary) but anchoring ZERO `frob:invariant` markers at all is
  flagged as likely under-specified -- the "silence" a per-claim lint
  can't see. New public `frob.gates.invariants.find_normative_claims` /
  `NORMATIVE_CLAIM_PATTERNS` and `frob.gates.inv004_gate`.

## [0.44.0] - unreleased (gates-area chain)

Public-API surface change since 0.43.0 (mechanical semver via REL001): an
additive (minor) bump -- new invariant-language lint.

- T-0462: INV003, a new (warn-severity) invariant gate rule: a
  `docs/**.md` file making an exclusivity/normative claim ("only",
  "sole"/"solely", "exclusively", "nothing else", "never...except", "at
  most/exactly one") needs a `<!-- frob:invariant INV-### -->` marker in
  the same file naming a real, loaded invariant. New public
  `frob.gates.invariants.find_exclusivity_claims` /
  `EXCLUSIVITY_CLAIM_PATTERNS` (the exclusivity-word corpus) and
  `frob.gates.inv003_gate`. WARN, not ERROR: the vocabulary's bare "only"
  surfaces ~90 findings across this repo's own pre-existing docs;
  hardening specific docs to ERROR (or building markdown-side
  `frob:waive` support) is follow-up work, not done in this pass.

## [0.48.0] - unreleased (strata round 2, part 2)

Public-API surface change since 0.44.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.strata.scan_text_for_fingerprints`/
`FingerprintHit` and `frob.gates.cve_fingerprint_scan_gate`.

- T-0439: added SEC-CVE-FINGERPRINT-001, a `frob check` gate scanning
  first-party repo source for the `CVE_FINGERPRINTS` needle corpus
  (`frob.strata._cve_fingerprint`) -- the missing first-party-source-lint
  sibling of CVEFP001 (catalog-drift only, no source scan) and `frob vet`'s
  `_scan_file_fingerprints` (third-party dependency source, no file:line).
  New `frob.strata.scan_text_for_fingerprints`/`FingerprintHit` do the
  line-level needle scan; `frob.gates.cve_fingerprint_scan_gate`
  (`src/frob/gates/_cve_fingerprint_scan.py`) walks every git-tracked,
  language-bucketed file and wires it into `frob check` as WARN-severity
  `SEC-CVE-FINGERPRINT-001` (registered in `_KNOWN_GATE_RULES`). Litmus
  pair: `tests/unit/strata/test_cve_fingerprint_scan.py` -- a "smelly" fixture
  (`shell=True`) fires, a "clean" one (`shell=False`) and an out-of-language
  file do not.

## [0.48.0] - unreleased (strata round 2, part 1)

Public-API surface change since 0.43.0 (mechanical semver via REL001): an
<!-- frob:waive DOC006 reason="frob.strata.COMPLIANCE_OUT_OF_SCOPE is a frozen historical release-note reference; symbol/module has since been reorganized" -->
additive (minor) bump -- new `frob.strata.COMPLIANCE_OUT_OF_SCOPE` catalog.

- T-0503: COMPLIANCE004 (`caught_by` integrity for compliance out-of-scope
  exclusions) was vacuous in production -- `_audit.py` never threaded an
  `out_of_scope` catalog into `evaluate_compliance` (unlike the security/
  quality families' `CWE_TOP_25_OUT_OF_SCOPE`/`QUALITY_OUT_OF_SCOPE`), so
  it always defaulted to `()` and the check trivially passed regardless of
  a fabricated `caught_by`. Added `COMPLIANCE_OUT_OF_SCOPE` (a real,
  production `OutOfScopeRegulation` catalog, `frob.strata._compliance`) and
  threaded it into `_compliance_pii_lint_fingerprint_gaps`'s
  `evaluate_compliance` call. Non-vacuous proof: `tests/unit/strata/
  test_audit.py::TestExhaustiveness.
  test_compliance_out_of_scope_bad_caught_by_fails_real_audit_path` shows a
  fabricated `caught_by` failing through the real production entrypoint
  (`evaluate_exhaustiveness`, exactly what `frob sys audit` calls), not
  just the unit-level `check_regulation_caught_by_integrity` evaluator.

## [0.47.0] - unreleased

Reconciliation section: two parallel landing chains independently claimed
overlapping version numbers. The check-output UX chain (T-0419/T-0420/
T-0421: TTY progress task-list, per-family gate stages + gate-summary,
skip_unchanged per-language reporting; new RenderWriter-driven check
runner surface) stamped 0.44.0 without a section, colliding with the
land-machinery chain's sections below. Final reconciled version is
0.47.0; the sections below document the land-machinery surface under the
numbers they were authored with.

## [0.46.0] - unreleased

Public-API surface change since 0.45.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.tickets.enforce_worktree_lease` and
`frob.scaffold.install_worktree_lease_hook`.

- T-0431: worktree-lease guard. New `FROB_WORKTREE=<abs path>` env var
  names the one worktree an agent's shell is authorized to mutate frob's
  tracked ticket state in; `frob.tickets.enforce_worktree_lease(root)`
  refuses (`Err(WorktreeLeaseViolation)`) when it is set and `root`'s
  actual git top-level does not match it -- wired as the first statement
  of every mutating `frob.tickets` entry point (`new_ticket`,
  `transition`, `add_evidence`, `add_cmd_evidence`, `set_done_report`,
  `record_failure`, `attach`, `archive`, `renumber`/`renumber_one`) and
  into `frob.gates`' `stamp_baseline`/`stamp_coverage`. Unset (the
  coordinator's own commands) is unrestricted, matching prior behavior.
  New `frob.scaffold.install_worktree_lease_hook` installs `pre-commit`/
  `pre-merge-commit` git hooks that abort loudly when `FROB_AGENT` is set
  non-empty, catching a raw `git commit`/`git merge` an agent shell ran
  directly against the wrong checkout, independent of `frob.tickets`.

## [0.45.0] - unreleased

Public-API surface change since 0.44.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.tickets.closed_ticket_ids`.

- T-0409: ledger-hygiene gate (TICK003). WARN (escalating to ERROR past a
  hard cap) when the active `tickets.md` ledger holds more than a
  configurable threshold (`frob.toml` `[tickets]` `stale_archive_warn`/
  `stale_archive_error`, default 20/60) of closed (done/dropped) tickets
  sitting un-archived -- the repeated "we got away with not running `frob
  ticket archive`" gap this ticket exists to close. New public
  `frob.tickets.closed_ticket_ids(queue)` is the shared "which tickets are
  closed" predicate the gate counts over. Resurrection-safe by
  construction: the gate only counts and recommends `frob ticket archive`,
  never writes anything itself, so it can never interact with the land/
  splice path's archive-resurrection guards (`_drop_resurrected_ids`,
  `splice_ledger`).

## [0.44.0] - unreleased

Public-API surface change since 0.43.0 (mechanical semver via REL001): a
signature change to an existing public symbol (`frob.tickets.land`), so
REL001 computes it as MAJOR-class -- under the "0.x is initial
development" semver rule this bumps the MINOR, not to 1.0.0.

- T-0338: `frob ticket land` now owns the two remaining coordinator-
  plumbing steps the T-0479 own-block-only splice did not cover: a
  REL001 version-bump/stamp step and a native-rebuild trigger. New
  optional `land()` parameters `bump_version` and `rebuild_natives`
  (both default `None`, matching the T-0398/D-05 `collected`/`passed`/
  `covers_scope` pattern): `bump_version(root, ticket, final_id)` is
  invoked right after the squash-apply is staged, computing whatever
  `frob.release` says the just-squashed public API demands and, if
  needed, rewriting `pyproject.toml`'s version, prepending a minimal
  CHANGELOG.md entry, and `frob release stamp`-ing the manifest, all
  staged into the same landing commit; `rebuild_natives(root)` runs only
  when the landed changeset touches `frob-core/`/`strata-core/` and
  triggers a rebuild (best-effort, non-blocking on failure). `LandReport`
  grew `release_bumped_to`/`natives_rebuilt` fields. The `frob ticket
  land` CLI supplies both by default
  (`frob.app.ticket_runner._apply_release_bump_for_land`/
  `_land_rebuild_natives_fn`).

## [0.43.0] - unreleased

Public-API surface change since 0.42.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.tickets.replay_evidence_from_done_report`.

- T-0357: coordinator-land evidence-loss recovery. A ticket closed straight
  from a hand-merged worktree (`git merge --no-ff`, bypassing `frob ticket
  land`'s ledger splice) could arrive at `transition(..., DONE)` with an
  empty structured `evidence:` field even though its Done report prose
  still carried the rendered ids -- failing MissingEvidence and forcing a
  manual `frob ticket evidence` re-record on main (the T-0248/T-0266
  incidents). New `frob.tickets.replay_evidence_from_done_report` parses a
  ticket's own rendered `### Evidence` Done-report section (the inverse of
  `render_evidence_block`) and recovers those ids into the structured
  field; `transition(..., DONE)` now attempts this automatically,
  best-effort, before falling through to the ordinary MissingEvidence
  rejection.

## [0.42.0] - unreleased

Public-API surface change since 0.41.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.tickets._reconcile` module and `frob
ticket reconcile` CLI command.

- T-0476: ticket<->worktree binding + liveness reconcile. New `frob.
  tickets.reconcile`/`ReconcileReport` (`src/frob/tickets/_reconcile.py`),
  reusing the T-0473 lease registry to judge two anomaly classes
  structurally: a stale `IN_PROGRESS` hold (a checkout's own ledger shows
  it, but no live lease backs it -- requeued to `QUEUED` via the same edge
  `frob ticket requeue` uses) and an orphan live worktree (a real `git
  worktree` entry with no lease naming it -- flagged, and only removed with
  `--remove-orphans`, a strictly more destructive opt-in gated separately
  from `--apply`). New `frob ticket reconcile [--apply] [--remove-orphans]`
  CLI command.

## [0.41.0] - unreleased

Public-API surface change since 0.40.0 (mechanical semver via REL001):
additive minor bump -- DOC004 console/bash command-drift tier driven by
[[docblocks.commands]] (T-0443) and PERF007 cross-stage redundant-
recomputation detection in frob.perf._redundancy (T-0413).

## [0.40.0] - unreleased

Public-API surface change since 0.39.0 (mechanical semver via REL001):
strata caught_by integrity -- new COMPLIANCE004 check, shared public
`caught_by_unresolved_tokens` helper in frob.strata._threat (T-0382),
and the eval/CWE-94 threat join with self-conformance updates (T-0401
G3).

## [0.39.0] - unreleased

Public-API surface change since 0.38.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.testing.python_coverage_targets`
(touched-set incremental coverage, T-0484) plus file-/directory-level
COV003 evidence resolution and parametrized-node-id fixes (T-0298,
T-0324). The 0.38.0 bump (cross-worktree lease registry
`frob.tickets._leases`, T-0473) landed without its own section; both are
reconciled here.

## [0.37.0] - unreleased

Public-API surface change since 0.36.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.check._memo` run-scoped memoization
module.

- T-0423: compute-once contract for the heavy pure analyses. New
  `frob.check._memo` module: `run_memo_scope` (context manager activating
  memoization for one `frob check` invocation), `reset_run_memo` (test/
  convenience entry into an unconditionally-active scope), `run_memo_stats`
  (hit/miss instrumentation, mirroring `frob.lang.parse_cache_stats`), and
  `memoize_per_run` (the decorator itself). Applied to `frob.graph.
  build_graph` and `frob.arch.analyze_project` at their definition site --
  a second call with identical arguments while a scope is active is a
  cache hit, not a recompute, regardless of which `frob check` stage calls
  it. Generalizes the T-0414 parse-cache pattern one level up; closes the
  T-0418 arch-double-run class of bug. `frob.dup.find_duplicates` was
  deliberately NOT touched (out of this ticket's scope; `src/frob/dup/` is
  concurrently under active rework) -- filed as a follow-up.

## [0.36.0] - unreleased

Public-API surface change since 0.35.0 (mechanical semver via REL001): an
additive (minor) bump -- new render vocabulary on `frob.render`.

- T-0460: render vocabulary follow-on to the T-0448 foundation -- `table`,
  `tree`, and `count_deltas` elements (each total: plain-mode shape and
  color-mode painting are identical once ANSI is stripped), plus `Progress`
  (TTY-only, cursor-controlling, clears on completion per the T-0419
  contract; a no-op on any non-TTY stream). New `RenderWriter` methods:
  `table`, `tree`, `count_deltas`, `progress`. See
  `docs/modules/render.md`.

## [0.34.0] - unreleased

Public-API surface change since 0.33.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.render` package.

- T-0448: FOUNDATION for the unified TTY-aware CLI output layer EPIC. New
  `frob.render` package -- `Renderer` (the only object a command runner
  should print through), `RenderWriter` (the standardized element
  vocabulary, namespaced off `Renderer.write`: heading, subhead, kv,
  status, count_summary, path, ticket_id, good, warn, critical, muted),
  `resolve_color` (single TTY/color decision honoring `NO_COLOR`,
  `FROB_NO_COLOR`, `--no-color`, `--color=auto|always|never`, `TERM=dumb`,
  `CLICOLOR_FORCE`), the five-name colorblind-safe semantic palette
  (`good`/`warn`/`critical`/`muted`/`accent`), and `RenderError`. `frob
  doctor` and `frob map` are migrated as the two FOUNDATION exemplars
  (`--json` paths unchanged). See `docs/modules/render.md`.

## [0.33.0] - unreleased

Public-API surface change since 0.32.0 (mechanical semver via REL001): an
additive (minor) bump -- one new public function and five new public
constants, no removal or signature-breaking change to any existing caller.

- T-0373: the arch gate (`frob.gates._arch.arch_gate`, the ARCH stage of
  `frob check`) used to always call `frob.arch.analyze_project` with the
  library's own conservative keyword defaults (30-line functions, 500-line
  files), silently ignoring the calibrated 60-line/800-line thresholds the
  user had already decided on -- that calibration only ever reached the
  standalone `frob arch` CLI, never the gate `frob check` actually runs.
  New `frob.app.config.load_arch_config(root)` reads a `[arch]` table from
  `frob.toml` (`max_function_lines`, `max_class_methods`,
  `max_local_imports`, `max_nesting_depth`, `max_file_lines`), defaulting
  every unset key to the calibrated values (new `ARCH_DEFAULT_MAX_*`
  constants), and `arch_gate` now threads it through. This repo's own
  `frob.toml` now carries an explicit `[arch]` table disclosing the
  calibration.
- T-0319: new `frob doctor` subcommand -- verifies the native extensions
  (`frob_core`, `strata_core`) are importable, reports availability and
  version for each, and exits nonzero with the remediation command
  (`make core` / `make install-tool`) when either is missing, so a
  natives-less install gets a clear diagnosis instead of silently degraded
  gates. `frob doctor --json` emits the same report machine-readably. New
  public `frob.doctor` module (`run_diagnosis`, `DoctorReport`,
  `NativeExtensionStatus`, `NATIVE_EXTENSIONS`, `REMEDIATION_HINT`).

## [0.32.0] - unreleased

No public-API change recorded for this version.

## [0.31.0] - unreleased

Public-API surface changes since 0.29.0 (mechanical semver via REL001): an
additive (minor) bump -- new optional parameters and new public functions,
no removal or signature-breaking change to any existing caller.

- T-0398: evidence-integrity fix for the audit's central North-Star hole
  (docs/audits/tickets-testing.md D-01..D-12) -- close/land previously
  meant only "a test with this name exists in collection," not "the work
  was actually tested, covers the ticket, and passed." `add_evidence`
  gained `passed` (D-01: a collected-but-currently-failing test is
  rejected, `EvidenceNotPassing`), `transition`/`land` gained
  `covers_scope` (D-02: evidence that binds to none of the ticket's
  touched/scope symbols is rejected, `EvidenceScopeUnbound`, via new
  `frob.gates.evidence_covers_scope`), `land` gained `collected`/`passed`/
  `covers_scope` callables for post-merge re-verification (D-05), a Done
  report must carry real content under its heading (D-03), an unknown-
  language file change no longer silently selects zero tests (D-04), a
  module-level edit forces selection even under `fallback="warn"` (D-06),
  the `uses-contract` ripple horizon widened from one hop to a bounded
  BFS (D-07), a splice union's evidence instead of dropping one side's
  (D-09), and a new `reverify_cmd_evidence` re-checks a `cmd:` evidence
  entry's reproducibility on demand (D-10). The real `frob ticket
  evidence`/`close`/`land` CLI commands (`ticket_runner.py`) now compute
  and supply these by default -- the library functions themselves keep a
  permissive `None` default for backward compatibility, but the CLI's
  default path is the strict one.

## [0.29.0] - unreleased

Public-API surface changes since 0.28.0 (mechanical semver via REL001): a
minor bump -- the public surface SHRANK (a compatible reduction of
internal-only names, not a breaking change to any documented API).

- T-0369: 73 genuinely package-internal helpers (0-1 intra-package
  consumer, never imported cross-package) were demoted to private
  (`name` -> `_name`) across `dup`, `gates`, `graph`, `lang`, `logging`,
  `strata`, `tickets`, and `vet`, with every in-repo reference and
  `frob:doc`/`frob:describes` anchor updated in lockstep. This completes
  the T-0362 export-or-demote pass: the public surface of each package is
  now exactly its intended API, and `frob-exports` reports zero
  unaccounted-for public symbols outside test packages.
- T-0359/0360/0370/0372: the arch analyzer's advisory categories are now
  materially more precise (test-file/data-file exemption, dispatch-family
  recognition, abstraction-opportunity gated on body-similarity or
  signature-specificity) -- no public API change, noted here for the
  release narrative.

## [0.28.0] - unreleased

Public-API surface changes since 0.27.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0362: export-or-demote pass over every package `__init__.py`. Error
  classes callers catch are now re-exported from their package roots
  (`frob.gitio.GitError`, `frob.gates.decisions.DecisionError`,
  `frob.graph.lock.LockError`, `frob.scaffold.project.ScaffoldError`),
  alongside the `app.*_runner.run` entry points and `app._style` helpers.
  The `frob-exports` checker no longer flags pytest symbols in `tests/`
  packages (they were never meant to be package exports). 74 true-internal
  helpers deferred to T-0369; two console-script entrypoints reason-noted.
- T-0359: `frob.excludes.is_test_file` -- the single shared test-file
  predicate -- is now public; three drifted private copies (in `gates`,
  `arch`, `testing`) were collapsed into it, and it recognizes TS/JS
  `*.test.*` naming the Python-only copies missed. Test files are now
  exempt from the arch advisory categories (long-function, god-class,
  abstraction-opportunity).
- T-0360: the arch abstraction-opportunity detector recognizes intentional
  dispatch/validator families (via tree-sitter structural references) and
  no longer flags them; internal `_collect_file_dispatch_refs` is private.

## [0.27.0] - unreleased

Public-API surface changes since 0.26.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0353: disposition of frob's own PII010/SEC110 findings. The over-broad
  `fingerprint` biometric field signature is narrowed to genuine biometric
  field names (`fingerprint_scan`/`fingerprint_template`); SEC110 gains a
  known-non-secret env-var allowlist (DISPLAY/TERM/PATH/PYO3_PYTHON/...) that
  does not fire; the true residue (passwd-audit metadata, tooling env reads)
  carries honest per-site `frob:waive` reasons. `frob check --only
  pii_structural` on frob's own tree is now 0/0.

## [0.26.0] - unreleased

Public-API surface changes since 0.25.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0207: structural PII/secrets detection. New `frob.gates._pii_structural`
  gate with `PII010` (a data-structure/schema FIELD whose name matches a
  PII/credential signature -- drawn from the secrets+PII corpus's
  `FIELD_SIGNATURES`) and `SEC110` (an `os.environ` read is a secret-source
  observation to map to a declared std.secrets node or waive). Both waivable
  with a reason, per the anti-evasion bounded-escape-hatch rule.

## [0.25.0] - unreleased

Public-API surface changes since 0.24.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0248: stale native-extension detection. New `frob.strata._native_staleness`
  (`stale_natives`, `stale_native_warning`, `check_native_staleness_or_exit`,
  `StaleNative`, `NATIVE_SOURCE_DIRS`) compares each `[[native]]`'s source dir
  mtime against its built artifact (reusing the T-0333 fingerprint), so a
  grammar-affecting change that left the native unrebuilt is caught: `make
  check` fails loudly, and `frob ticket land` warns pre-commit.

## [0.24.0] - unreleased

Public-API surface changes since 0.23.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0232: per-gate timing attribution corrected (measured via
  `time.thread_time()` per job instead of wall-clock, so GIL contention no
  longer smears every gate's cost toward the slowest), and `.frob` db read
  contention removed -- new `frob.graph.cache.connect_readonly` lets pure
  readers (`load_graph`) open the cache without taking sqlite's write lock,
  and `_apply_schema` no-ops when the schema is already current.

## [0.23.0] - unreleased

Public-API surface changes since 0.22.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0241: ticket scope parsing fixed. New `frob.tickets.scope_matches` is the
  single shared scope matcher -- splits comma-joined scope entries, expands a
  bare `dir/` prefix to `dir/**`, and always treats `tickets.md` as implicitly
  in scope; every fnmatch call site (land + the scope gates) now delegates to
  it, and `Ticket`/`TicketSpec` normalize comma-joined scope at construction.

## [0.22.0] - unreleased

Public-API surface changes since 0.21.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0244: embedded-code blind spot closed. The capability scanner now
  detects HTML/JS embedded in python string literals (`_embedded_code_regions`)
  and, per the anti-evasion fail-closed rule, always emits a new
  `embedded_code` capability kind for a detected region (best-effort
  needle re-scan on top), so dangerous embedded code can no longer hide
  from the scan. `embedded_code` added to `CAPABILITY_KINDS` with per-language
  matrix excuses.

## [0.21.0] - unreleased

Public-API surface changes since 0.20.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0247: the strata store grammar gains four `node_prop` productions --
  `on-deploy`, `observe`, `errors_total`, `panics_contained_by` -- so a
  `store` node can carry the same deploy/observability obligations other
  nodes already do. `StoreDecl` gains the four fields; elaboration and the
  observability validators now walk `module.stores`.

## [0.20.0] - unreleased

Public-API surface changes since 0.19.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0180: closed-world unknown-import accounting (T-0158 addendum 2
  remainder). New `frob.vet` module `_closedworld` with `ImportResolution`
  / `ClosedWorldAccounting` models: walks a project's absolute imports,
  resolves each against the capability registry / vetted-library cache /
  local-source scan, and reports the residue of genuinely-unknown imports
  as a closed-world accounting.

## [0.19.0] - unreleased

Public-API surface changes since 0.18.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0236: `frob ticket land` now refreshes the pre-work sweep post-merge,
  pre-close, so PRE001 stops re-firing stale sweep findings after a land in
  the multi-agent loop. New `frob.gates.sweep_ticket(root, ticket)` (the
  single dup+xref+digest sweep-computation function).

## [0.18.0] - unreleased

Public-API surface changes since 0.17.0 (mechanical semver via REL001).

- T-0171: THREAT002 no longer fires in quality views for a capability that
  IS classified, just in a different family's catalog (e.g. a security-only
<!-- frob:waive DOC006 reason="frob.strata.ALL_CATALOG is a frozen historical release-note reference; symbol/module has since been reorganized" -->
  `exec`/`html_render`). New `frob.strata.ALL_CATALOG` (the union sink
  taxonomy across every family catalog) and a `taxonomy=` parameter on
  `check_capability_completeness` (defaults to the per-family `catalog`, so
  single-family callers are unchanged); the exhaustiveness sweep classifies
  against the union while still scoping obligations per family.

## [0.17.0] - unreleased

Public-API surface changes since 0.16.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0234: generated-file marker respected by the coverage gate.
  `frob.graph._generated.is_generated_source` + `GENERATED_MARKER_RE`
  detect a generated-by/`@generated`/`DO NOT EDIT` header in a file's first
  lines; COV001 then exempts such files from the frob:doc obligation
  (nobody hand-documents generated code). The file stays fully in the graph
  (xref/dup/arch still see it) -- only the documentation obligation is
  waived, deliberately distinct from `[graph] exclude`.

## [0.16.0] - unreleased

Public-API surface changes since 0.15.0 (mechanical semver via REL001): in
0.x a breaking change bumps the minor (semver section 4).

- T-0233: a broken `frob:doc` target no longer suppresses other coverage
  findings on the same file. `_cov001` now counts a symbol documented only
  when its `frob:doc` edge actually RESOLVES (reusing DOC002's resolution
  logic), so a dangling doc anchor is reported as its own DOC002 error
  without masking the real COV001 gap. `coverage_gate`/`_cov001` gained a
  `root: Path` parameter (the breaking change driving this bump).

## [0.15.0] - unreleased

Public-API surface changes since 0.14.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0170: `kotlin` capability-scanner column for Android nodes. Added as a
  fully registry-backed language (`_capability_registry.LANGUAGES` +
  `DANGEROUS_OPERATIONS` net/exec/client_storage rows + `MatrixExcuse`
  entries for its unpatterned cells), so the T-0169 language-coverage
  drift-lock stays strict equality with no carve-out. `.kt`/`.kts` files
  now scan for net/exec/client-storage capabilities.

## [0.14.0] - unreleased

Public-API surface changes since 0.13.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0188: `CWE-295` (Improper Certificate Validation) `WeaknessEntry` added
  to `QUALITY_CATALOG`, plus three `std.cve` fingerprints (FP-TLS-VERIFY-001/
  002/003) for TLS certificate-verification bypass across Python
  (`verify=False`), TypeScript/Node (`rejectUnauthorized: false`), and Rust
  (`danger_accept_invalid_certs(true)`), each cited by a real CVE.
- T-0189: `CWE-611` (XML External Entity) `WeaknessEntry` added to
  `CWE_CATALOG`, plus the `FP-XXE-PARSE-001` fingerprint (Python
  `resolve_entities=True` / `xml.sax.make_parser`), cited by CVE-2013-1665.

## [0.13.0] - unreleased

Public-API surface changes since 0.12.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0333: native-extension-aware test collection. `frob.testing.NativeSpec`
  + `load_natives` parse a new `frob.toml` `[[native]]` table; the pytest
  collection cache key now folds in a fingerprint over each declared
  native's compiled artifacts (`.so`/`.pyd`/`.dylib`), so building or
  rebuilding a native (`make core`) invalidates the cache automatically
  instead of leaving a stale set that reds COV003. COV003 now names an
  unbuilt native and its build command (via `CollectedTests.missing_natives`)
  instead of pointing at a nonexistent flag; `frob test --collect`
  (`drop_collection_cache`) is the explicit cache-refresh escape hatch.
  Toolchain/platform-agnostic (maturin/pyo3 and setuptools/pybind11 alike;
  Linux/macOS/Windows, x86/arm).

## [0.11.0] - unreleased

Public-API surface changes since 0.10.0 (mechanical semver via REL001). Per
semver section 4, breaking changes while in 0.x bump the MINOR (0.10 -> 0.11),
not to 1.0.0 -- REL001 now enforces this (a breaking change no longer forces
a premature 1.0.0).

- T-0288: `frob.graph.callgraph` (`CallGraph`, `build_call_graph`,
  `closure`) -- a shared interprocedural call-graph substrate; dup's
  `find_clones` now inlines bounded PRIVATE-helper call closures before
  fingerprinting (`DupConfig.inline_calls`/`inline_max_depth`/
  `inline_max_nodes`), plus a dedicated `find_helper_clones` population
  pass (`DupConfig.helper_min_tokens`) for over-split tiny-helper families.
- T-0222: `ffi` capability needle for compiled-extension imports
  (`importlib.machinery.ExtensionFileLoader`).
- T-0289: complexity-aware long-function arch rule + `arch_gate`/ARCH001
  reasoned per-function override.
- T-0195: dup template report (`build_group_template`, `CloneTemplate`,
  `CloneBinding`, `CloneMatchGroup`); `CloneReport.groups` retyped.
- T-0179: `frob.app._style` CLI-presentation helpers (private module).
- release: `required_version` -- a breaking change in 0.x bumps the minor,
  not the major (semver section 4).

## [0.10.0] - unreleased

Public-API surface changes since 0.9.0 (mechanical semver via REL001):

- T-0194: anti-unification kernel (Plotkin least-general-generalization)
  over the `(labels, parents)` node-array representation
  `apted_similarity` already consumes -- the foundation of the dup-engine
  reverse-templating chain (T-0195 template report, T-0287
  type-generalization). New `frob-core/src/lib.rs::anti_unify`: a
  lockstep top-down walk emitting shared nodes where two trees agree and
  a fresh `$hole_N` at each divergence (label mismatch or arity
  mismatch), never recursing into a hole's diverging subtrees.
  Deterministic left-to-right/top-down hole numbering. HOLE-CEILING
  sanity: a template that is >50% holes carries no real generalization
  value, so the kernel returns a false-ok sentinel (never raises across
  the PyO3 boundary) that the Python shim turns into
  `Err(DupError.HoleCeilingExceeded)`, letting the caller fall back to a
  plain (non-generalized) clone pair. New Python surface:
  `frob.dup._core.anti_unify`, `frob.dup.AntiUnifyTemplate` (frozen
  pydantic model: `labels`, `parents`, `bindings_a`, `bindings_b`), and
  `DupError.HoleCeilingExceeded`, all re-exported from `frob.dup`.

## [0.9.0] - unreleased

Public-API surface changes since 0.8.0 (mechanical semver via REL001):

- T-0262: `std.krb` -- Kerberos/AD domain trust, SPNs, and delegation as
  first-class strata (deploy epic T-0254's auth pillar, built on T-0255's
<!-- frob:waive DOC006 reason="strata-core/src/parse.rs is a frozen historical release-note reference (0.9.0); file has since been split (T-1099) into strata-core/src/parse/" -->
  `HostManifest`/`runs_as`). New grammar (`strata-core/src/parse.rs`):
  node clauses `realm "NAME"`, `kdc`, `spn "SPN"`+, `delegation
  none|constrained|rbcd|unconstrained [target "SPN"]*`, `trusts IDENT
  [direction "one-way"|"two-way"] [transitive]`+, and a flow clause
  `authenticates_via tgt|st`. New `frob.strata._krb` (pure, fully unit-
  and litmus-tested): `KrbManifest`, `KrbDelegationKind`, `KrbTrust`,
  `krb_attrs`, `krb_manifest_for`, `krb_trust_flows`,
  `flow_authenticates_via`. New `frob.strata._ast.KrbTrustDecl`. Domain
  trusts desugar to a synthesized `Flow` at elaboration time
  (`_elaborate.py::_elaborate_module`) so the existing reach/noflow
  closure model-checks cross-realm reachability with no new kernel
  primitive (charter law 1). MODEL + VOCABULARY ONLY: delegation-abuse
  obligations are T-0263, out of scope here. tmLanguage grammar synced
  (`editors/vscode-strata/syntaxes/strata.tmLanguage.json`);
  `docs/strata/krb.md` documents the vocabulary and its scope cuts (no
  store-level clauses, no generator).

## [0.8.0] - unreleased

Public-API surface changes since 0.7.0 (mechanical semver via REL001):

- T-0259: `frob deploy audit --vm <name>` -- VirtualBox snapshot-diff
  harness proving artifact-free install/uninstall against a live guest
  (deploy epic T-0254 child 5, NOT run by `frob check`/`make check`).
  New `frob.deploy._audit` (pure, fully unit-tested): `StateCapture`,
  `FileFact`, `StateDiff`, `diff_states`, `idempotence_holds`,
  `artifact_freeness_holds`, `install_exactness_holds`,
  `assert_not_installed`, `assert_healthy`, `CheckpointResult`,
  `AuditAttestation`, `build_attestation`, `ALLOWLIST_PATTERNS` -- the
  four proofs (idempotence, artifact-freeness, install-exactness, and
  the per-checkpoint `status.sh` health assertions) plus attestation
  JSON. New `frob.deploy._vm_runner` (the one VM-gated, untested-in-CI
  sliver, deliberately kept thin): `VmAuditConfig`, `AuditRunResult`,
  `run_vm_audit`, `vboxmanage_available` -- drives restore-snapshot ->
  CHECK C0 -> install -> CHECK C1 -> install again -> CHECK C1' ->
  uninstall -> CHECK C2, and degrades to a clear `status="skipped"`
  (never a fabricated pass) when `VBoxManage` is not on `PATH`. New
  `frob deploy audit` CLI verb (`src/frob/app/deploy_runner.py`,
  `src/frob/__main__.py`) and `make deploy-audit` Makefile target.

## [0.7.0] - unreleased

Public-API surface changes since 0.6.0 (mechanical semver via REL001):

- T-0258: `frob deploy`'s bidirectional conformance check -- new
  `frob.deploy.deploy_conformance_violations`, `ConformanceViolation`,
  `extract_mutation_surface`, `expected_mutation_surface`,
  `MutationTarget` (`_conform.py`): structured extraction of committed
<!-- frob:waive DOC006 reason="deploy/install.sh is a frozen historical release-note reference to a deploy-epic artifact path as it existed at that release" -->
  `deploy/install.sh`/`uninstall.sh`'s actual mutation surface
  (`useradd`/`groupadd`/`userdel`/`groupdel`/`mkdir`/`install`/`cp`/
  `chown`/`chmod`/`rm -f`/`rm -rf`/`systemctl enable|disable|start|
  stop`/unit-heredoc writes), compared bidirectionally against the
  current `HostManifest` set as `DEPLOY002` (script mutation not
  declared in the manifest) and `DEPLOY003` (manifest entry no
  mutation implements), wired into `frob check` as an extra
  `deploy-conformance` stage alongside `DEPLOY001`.

## [0.6.0] - unreleased

Public-API surface changes since 0.5.0 (mechanical semver via REL001):

- T-0257: `frob deploy generate` -- new `frob.deploy` package
  (`generate_all`, `generate_install_script`, `generate_status_script`,
  `generate_uninstall_script`, `manifest_digest`,
  `sorted_manifest_entries`, `deploy_drift_violations`,
  `DeployDriftViolation`, `ManifestEntry`) compiling `std.host`
  `HostManifest` facts (T-0255) into idempotent Linux/systemd
  install/status/uninstall bash, plus the `DEPLOY001` drift check
  (wired into `frob check` as an extra `deploy-drift` stage) and the
  `frob deploy generate [--check] [--out-dir]` CLI verb. Also adds
  `frob.strata.node_allowed_syscalls`/`node_may_kinds` (public exports
  of previously-private `_export.py`/`_effects.py` helpers, reused by
  the new generator for `SystemCallFilter=`/`CapabilityBoundingSet=` so
  neither mapping is duplicated).

## [0.5.0] - unreleased

Public-API surface changes since 0.4.0 (mechanical semver via REL001):

- T-0193: R1.5 exact-region dup kernel -- new public `frob_core.exact_regions`
  (generalized suffix array + LCP over a normalized token corpus) and
<!-- frob:waive DOC006 reason="frob.dup._core.exact_regions is a frozen historical release-note reference; symbol has since moved/reorganized in the dup pipeline split" -->
  `frob.dup._core.exact_regions`; `DupConfig` gained `region_kernel_enabled`
  and `region_min_tokens` fields (`[dup].region_kernel`/`region_min_tokens`
  in frob.toml). Off by default, independent of `[dup].enforce`.

## [0.4.0] - unreleased

Public-API surface changes since 0.2.0 (mechanical semver via REL001):

- T-0212: new public `frob.graph.dedupe_slug`; GitHub-compatible anchor slugger.
- T-0253: `frob.vet.is_self_pattern_path` gained a `root` param (scan-target
  discriminator closing a capability-scan evasion hole).
- T-0209: `frob.lang.COMMENT_TYPES` made public (capability scanner drops
  needle hits inside comment spans).
- T-0231: `frob --version` prints the installed package version instead of
  an argparse error; `frob sys plan` (no `--apply`) labels its output
  "DRY RUN (no tickets created; pass --apply to compile)"; DOC001's orphan
  hint resolves an actually-existing configured docs root instead of
  blindly naming `docs/index.md` in repos that never created one.
- T-0255: new public `frob.strata` std.host manifest symbols
  (`HostManifest`/`HostOwns`/`HostPlatform`/`host_manifest_for`/`OwnsDecl`).
- T-0256: new public `frob.strata` movement-impossibility symbols --
  `HostIsolationViolation`, `evaluate_lateral_isolation` (HOST001),
  `evaluate_vertical_isolation` (HOST002), `evaluate_host_isolation_waived`,
  `HOST_MULTI_INSTANCE_WAIVER_FAMILIES`, `COMPROMISED_OWNER_CATALOG`,
  `COMPROMISED_OWNER_OUT_OF_SCOPE`, `COMPROMISED_OWNER_VIEWS`,
  `host_movement_flows`, `AddFlow` (new `Rewrite` variant), and
  `build_compromised_user_scenario` (the compromised-service-owner
  red-team scenario builder; its blast-radius `NoFlow` claims are proved
  over the declared-flow graph PLUS `host_movement_flows`'s
  HostManifest-derived filesystem/socket sharing edges, closing a
  review-round vacuity gap where a shared writable path with no declared
  app `Flow` would otherwise vacuously prove the claim).

## [0.2.0] - unreleased

Ticket list frozen at the T-0156 landing commit; T-0174 (sys-audit waiver
channel) and T-0208 (vet obfuscation-scan performance) closed during the
final review rounds and are included below. Tickets closed after this
landing appear in the next release's section.

### strata (design-language kernel, prover, policy, self-conformance)

- T-0174: waive clause for sys-audit findings: RULE:SUBTARGET specificity,
  mandatory reasons, stale-waiver drift-lock, PROVED-(N-waived) reporting

- T-0047: strata: provable system-design language (epic)
- T-0048: strata charter + design doc tree under docs/strata/
- T-0049: strata phase 0: kernel + prover core
- T-0050: strata phase 1: surface language v0 + std.trust + refinement
- T-0051: strata phase 2: std.infra + bounds + policy forms + boundaries
- T-0052: strata phase 3: scenarios, crash contracts, atomicity
- T-0053: strata phase 4: code binding (tier 2) + self-hosting
- T-0054: strata phase 5: std.secrets, std.deploy, work-order compiler, exporters
- T-0055: strata kernel data model: Node/Flow/Boundary/Bound/Claim/Scenario
- T-0056: strata fact base + semi-naive Datalog closure engine
- T-0057: strata claim evaluation: noflow/bound/reach with counterexample traces
- T-0058: strata payments litmus as kernel facts + golden findings
- T-0059: strata lexer + recursive-descent parser (pydantic AST, Result diagnostics)
- T-0060: strata elaborator framework + std.trust vocabulary
- T-0061: strata assert/assume: owner, expiry, verdict report
- T-0062: strata refinement: abstract components, refine blocks, faithfulness
- T-0063: strata payments litmus in surface syntax + CI goldens
- T-0064: strata std.infra: store/cache/queue/cdn/balancer elaboration
- T-0065: strata age/staleness propagation (TTL = rotation = RPO = expiry)
- T-0066: strata capacity arithmetic: utilization, fanout, skew, growth horizons
- T-0067: strata policy sublanguage: 5 forms, semantic scoping, tree-sitter compilation
- T-0068: strata std.policy.analyzable base pack + enables soundness cascade
- T-0069: strata six-phase boundaries + outcome-conditioned frames
- T-0070: strata errors-total, panics-contained, observe blocks (ERR/OBS gates)
- T-0071: strata-core: independent Rust/PyO3 kernel crate (closure + propagation)
- T-0072: strata tube + chirp litmus models + goldens
- T-0073: strata scenario engine: node loss, rate surge, trust downgrade
- T-0074: strata crash contracts: on-crash, no-hang check, crash-retry-idempotency join
- T-0075: strata atomic/saga: cross-store refusal + fault-injection generation
- T-0076: strata breach scenarios: blast radius + recovery-path independence
- T-0077: strata as 6th frob.lang grammar: design constructs become graph symbols
- T-0078: strata code binding: code globs + import-level conformance
- T-0079: strata effect extraction: net/fs/exec facts vs may-capabilities
- T-0080: strata directives (frob:channel/boundary/secret) + SYS gates in run_gates
- T-0081: strata self-hosting: design/frob.strata models frob itself
- T-0082: strata std.secrets: credentials as cache-of-authority
- T-0083: strata std.deploy: endorsement pipeline, canary schedules, rollback budgets
- T-0084: strata frob sys plan: obligation -> ticket compiler
- T-0085: strata frob sys doc + DOC002 claims audit
- T-0086: strata exporters: k8s netpol / seccomp / IAM from the model
- T-0093: strata grammar: explicit trust clause for queue/balancer
- T-0099: document demand() behavior shift for unresolvable rates (propagates vs drops)
- T-0103: std.infra drops declared store capacity (UTILIZATION can never target a store)
- T-0109: strata obligation catalog: CWE/CVE + quality anti-pattern auditing (epic)
- T-0110: threat D: NVD CVE->CWE ingestion into vet + containment report
- T-0111: threat A: std.cwe catalog + weakness/capability grammar + THREAT001/003
- T-0112: threat B: capability->obligation instantiation + THREAT002 precondition completeness
- T-0113: threat C: CWE-sink effect extraction + mitigation chokepoint verification
- T-0114: threat E: std.perf/reliability/compat anti-pattern families
- T-0115: threat F: frob sys audit exhaustiveness matrix + DOC002 + vuln litmus
- T-0116: threat G: std.compliance -- COPPA/GDPR/HIPAA + privacy-policy-as-claims
- T-0132: strata surface grammar: code=<glob>/may <capability> unreachable from .strata source text
- T-0134: frob.strata._facts hard 'import strata_core' crashes standalone installs with a design/ dir (found while working T-0133)
- T-0136: strata surface grammar: on deploy / secret constructs unreachable from .strata source text
- T-0138: strata claim ids cannot carry ':' or '-' -- discharge claims unauthorable from .strata source
- T-0139: editor syntax highlighting for .strata (VSCode + JetBrains via one TextMate grammar)
- T-0144: pytest --collect-only hard-fails repo-wide when strata_core native ext is absent, blocking frob ticket evidence for any ticket
- T-0145: per-CWE litmus fixtures: every catalog weakness fires from real .strata source
- T-0148: drive frob check gates to zero violations
- T-0150: self-conformance: vet capability scan of our own source must match design/frob.strata interfaces
- T-0151: vet capability scanner self-matches its own pattern-table literals
- T-0153: std.cve fingerprints: pattern catalog for known vulnerable-usage classes
- T-0154: PII declarations: first-class personal-data modeling and flow proofs in strata
- T-0155: design lint family: caching, resource bounds, rate-limiting, kill-switch rules over the kernel model
- T-0158: capability exhaustiveness matrix: every reserved kind provably detected in every supported language
- T-0164: COV002 demands per-declaration frob:ticket edges inside .strata files -- boilerplate x28
- T-0166: store grammar rejects code/may despite surface.md implying support
- T-0168: TEST001 fires on flow declarations in .strata files -- undefined semantics
- T-0169: capability conformance did not scan TS/JS in the logand.app pilot -- verify per-language wiring
- T-0172: managed marker for config-only infra nodes promised in surface.md but unimplemented
- T-0201: selfconform self-match: pattern-catalog data files observed as live capabilities -- main red

### check / gates

- T-0015: Implement per-rule severity overrides in frob.toml (gates currently hardcodes severity in code)
- T-0021: frob.perf: profiling, heat-maps, PERF linear-scan rules (docs/modules/perf.md)
- T-0022: Polyglot monorepo check: per-subtree stage detection, frob.toml [check] scoping, TypeScript stage (tsc/eslint)
- T-0031: Single-file tickets.md ledger + scope-based COV002 (reduce ticket/annotation spam)
- T-0035: REL001 release gate: mechanical semver from public-API digests
- T-0037: Smart-dup: frob-core Rust kernels + DUP gate + build wiring
- T-0038: ADR decision records: frob:decision edges + DEC gates
- T-0039: Convention-based unit-test binding inference (reduce frob:tests burden)
- T-0042: TEST007: pair-level integration obligations from uses-contract edges
- T-0090: TEST002 misses frob:tests directives bound cross-file to rust symbols
- T-0092: rust test integration: [[test.runner]] for cargo + COV003 evidence resolution
- T-0095: frob check --delta: report only violations new since a stamped baseline
- T-0101: extend frob:waive to arch/perf tool channels or document the boundary
- T-0102: frob check must FAIL, not silently pass, when the ticket queue fails to load
- T-0106: Wire frob ticket new/close --evidence to tickets.add_evidence
- T-0107: Wire frob check --stamp-baseline/--delta CLI flags and docs
- T-0108: SCOPE001 flags files already committed by earlier tickets on the same branch
- T-0122: frob check races concurrent build_graph calls against shared .frob/cache.db
- T-0124: frob check --ticket exits 1 with no diagnostic output (repro on closed T-0075)
- T-0125: frob.logging.quiet_stdout_logs is not thread-safe; races across concurrent frob.arch/frob.dup calls
- T-0135: sys_gate imports frob.strata (and its unguarded strata_core dep) before the design/ opt-in check -- crashes frob check on ANY repo in a standalone install (supersedes/extends T-0134)
- T-0142: standalone frob check crashes FileNotFoundError when ruff/ty binaries absent -- wheel declares no tool deps
- T-0157: secrets-scan gate: real-looking API tokens in tracked files fail check unless marked fake
- T-0162: make ticket-id collision structurally impossible across checkouts and worktrees
- T-0165: DOC002 anchor errors: report the computed slug and suggest nearest valid anchor
- T-0202: frob check default output: stats summary, gate chatter to DEBUG, standardized log format
- T-0203: perf_gate: silence UnsupportedLanguage skips for non-code files
- T-0205: pytest collects Test*-prefixed product classes -- set __test__ = False
- T-0215: non-pytest evidence channel for docs/design tickets + close-from-queued hint

### tickets (queue, evidence, worktree/ledger safety)

- T-0032: Ticket schema: incident kind, acceptance, STRIDE threat, renumber
- T-0043: Migrate arch + dup/_legacy off frob.ast, then delete frob.ast
- T-0088: reorganize flat docs/ into guides/ modules/ commands/ hierarchy
- T-0094: frob ticket evidence subcommand: append structured evidence ids from the CLI
- T-0096: frob ticket archive: rotate done tickets out of the active ledger
- T-0097: README banner with goblin mascot (aviator cap, crystal ball of rune-code)
- T-0098: frob ticket attach without path should error usefully outside a TTY
- T-0117: fresh frob_core rebuild fails TestR5Dataflow::test_no_false_positive_against_unrelated_function
- T-0126: annotate newly-extracted module constants with frob:doc edges (COV001 x21)
- T-0128: extend rust [[test.runner]] coverage to frob-core (second PyO3 crate)
- T-0130: design/litmus strata symbols: exclude from doc/test obligations
- T-0137: frob test --base main mixes touched non-test source symbols into pytest argv
- T-0140: ticket id allocator ignores tickets-archive.md -- new ids collide with archived tickets
- T-0141: cache corrupt-recovery crashes on Python 3.12 sqlite: DROP TABLE raises before rebuild
- T-0149: frob test: no [[test.runner]] for language=strata blocks touched-set selection on .strata fixtures
- T-0152: packaging is an undeclared runtime dependency -- bare frob install crashes on import
- T-0159: extending frob: developer guides for every registry and extension point
- T-0163: frob sys audit <file> appends bogus path segment instead of erroring
- T-0167: frob sys --help: add example invocations and directory-root convention
- T-0175: agent playbook in-repo: kill per-dispatch retreading
- T-0176: frob ticket land: one-command landing (merge-check-splice-close-commit)
- T-0184: frob ticket close prints ERROR MissingEvidence but exits 0
- T-0185: exhaustive-research agent: frontier-loop with external graph-knowledge store
- T-0186: link docs/guides/exhaustive-research.md from docs/index.md
- T-0227: gitio treats untracked gitlink/directory as file (Errno 21 warning spam)

### dup (clone detection, frob-core)

- T-0001: frob-core PyO3/maturin crate + smart dup (Phase 7)
- T-0016: Re-platform map/outline/xref/cycle/dup onto frob.lang; delete frob.ast
- T-0026: Unify exclude surface: dup/arch/cycle scanners must respect [graph] exclude
- T-0041: dup follow-on: --probe CLI, full APTED, real CFG/DFG

### vet (dependency vetting)

- T-0034: Wire fuzz+vet: FUZZ gate, frob test --fuzz, capability scan merge, gates degrade without diff
- T-0208: obfuscation scan rewritten single-pass (~100x on pathological files),
  per-package progress, honest per-package timeout verdicts
- T-0181: survey-prioritized third-party python/npm/cargo dangerous-surface registry entries (T-0158 addendum 2 remainder)

### threat / CVE / compliance

- T-0146: cvelistV5 record parser: pydantic models for CVE Record Format v5
- T-0147: frob vet: match dependencies against a local cvelistV5 mirror, link CVEs to the threat catalog

### docs

- T-0010: frob serve: MCP adapter over stale_docs/doable_tickets/check_scope/pre_work
- T-0025: Colors, frob.toml check config, DOC001, overload fix, log dedup
- T-0028: frob check red at HEAD: 16 orphan docs (DOC001) and ruff-format drift in 9 files
- T-0036: frob stats: DORA-ish delivery measurement (queue health + commit cadence)
- T-0040: frob mutate: mutation testing quality oracle
- T-0161: PERF001-004 lexical heuristic: false-positive classes need real fixes, not permanent waivers

### other

- T-0019: cache.connect does not recover from a non-sqlite-file corrupt cache.db
- T-0020: Gate convergence: collection oracle, evidence matching, fixture excludes
- T-0024: graph: @overload chains crash build_graph (UNIQUE symref); dedupe last-def-wins
- T-0027: perf: cProfile masks workload exit code; profile_command cannot detect failed runs
- T-0029: graph: concurrent build_graph on shared cache.db raises disk I/O error; add busy_timeout
- T-0030: ticket new --origin flag
- T-0044: Comment binder: directive above nested method binds to enclosing class
- T-0045: perf: split heat/profile long functions and clear PERF-rule self-flags
- T-0046: Refactor: clear perf/arch/test warnings in app,process,serve,testing,map,outline,xref,cycle,gitlog,policy
- T-0087: python CONST extraction misses call-expression assignments (X = Foo(...))
- T-0089: test_scaffold_dx flaky under full-suite run, passes in isolation
- T-0091: make core creates a stray venv under strata-core/, contaminating the editable install
- T-0100: frob:tests directives silently degrade when stacked 3+ or separated from def
- T-0119: perf: split long functions in app/perf_runner.py (_heat_body, _annotate)
- T-0120: perf: split long test in tests/system/test_cli_perf.py
- T-0123: register pytest 'slow' marker in pyproject.toml
- T-0127: DOC002-style gate: validate frob:doc anchors resolve to real doc slugs
- T-0129: wire .strata into frob.graph/outline/xref/testing/policy/cycle scanners
- T-0131: frob ticket resolves repo root to main checkout from inside a linked worktree (first invocation)
- T-0133: standalone tool install crashes: strata_core hard import in frob.lang (hotfixed); bundle or degrade natives properly
- T-0143: std.cwe catalog: transcribe the cwe-top-25 view (and stub-free ASVS decision)
- T-0182: per-operation fire+negative fixture parametrization for the full DANGEROUS_OPERATIONS table (T-0158 deliverable 3 remainder)
