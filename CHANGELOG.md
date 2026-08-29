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

## [0.531.0] - unreleased

- T-1549: Tier-A auto-fix: ClaimDivergence re-run via done-report recap
- T-1599: Language adapter capability matrix: make the cross-language contract statically enforced
- T-1600: Language support: C#
- T-1604: Language support: Bash/Shell
- T-1606: Per-language line-length: each formatter owns its own width, not ruff's
- T-1614: RUNS LAST: audit every frob:waive for cop-outs, after all other work is complete
- T-1654: Audit remaining real-repo build_graph tests for T-1433/T-1635 xdist self-scan contention
- T-1660: PERF014 remainder: 3 confirmed real per-line finditer nesting sites (cpp_mayraise, ffi, rule_id_scan)
- T-1666: Classify and re-waive the 142 OPAQUE001 findings T-1659's symref fix surfaced; sweep PERF/PII/SEC005 for the same shape
- T-1945: Bulk-reformat the 77 ruff-format + 265 frob-fmt drifted files (deferred from T-1928)
- T-2080: gate-gap class 4 (non-python doc targets): frob.toml severity + remaining config surfaces still unanchored
- T-2100: TestRevalidateDispatchableSweepTickets: two tests intermittently interfere when run together (pre-existing)
- T-2128: SCOPE002 for docs/modules/tickets.md#coalescing-verify-worker-t-1688 is ERROR-severity while every other SCOPE002 against this doc is a warning
- T-2134: tickets.md monofile looks stale/orphaned since the v2 sharded-ticket migration -- investigate and remove or document
- T-2141: --allow-cross-ticket carries an undeclared set: the operator cannot state which tickets they expect to carry, so a legitimate sibling batch and an accidental foreign carry look identical
- T-2197: frob ticket promote inside a worktree produces an id invisible to the whole fleet until that worktree's branch lands
- T-2234: Map the tickets/app/serve/verify/testing/strata/gates/... mega-cluster (180+ files) into sub-SCCs before any mechanical fix leaf can be scoped
- T-2237: T-2226 residue: 2 DOC011 dangling T-draft-* prose citations, mappings resolved via git archaeology, blocked by live leases on the target docs
- T-2244: Repoint trivial Makefile aliases (format/lint/typecheck/test*) at existing frob quality/fmt subcommands
- T-2245: Rewrite docs + agent-playbook to name frob subcommands first; audit remaining Makefile references in src/frob/**
- T-2251: frob format subcommand: replace make format/lint-fix/all (ruff fix+format wrapper)
- T-2301: Relocate two archgate SCOPE002-widening tests out of test_examined_sites.py
- T-2311: DOC006: repair remaining docs/modules/tickets-*.md pointers (tickets.md-adjacent contended family)
- T-2359: Reformat the 138 files pending ruff-format as one deliberate commit, unblocking T-2244/T-2245
- T-2361: Profile-collapse: migrate the 5 if-rapid call sites onto LandProfileSettings
- T-2362: Profile-collapse: add a structural gate against ProfileName branches outside _profile.py
- T-2363: 5-package import cycle (serve/stats/tickets/testing/app) needs an owner decision on which dependency to invert
- T-2364: frob-cycle gate emits identity-less findings (code=None, file=None) -- an unownable finding masked three real cycles
- T-2366: COV003: T-1205/T-1235/T-1397/T-1526 evidence does not resolve against tests/unit/test_makefile_coverage.py
- T-2369: Burn REF001/REF002 + REG008 WARN gates to zero, then promote to error
- T-2372: Burn TICK004/TICK007/TICK011 WARN gates to zero, then promote to error
- T-2373: Burn ruff I001 (import-sort) warnings to zero, keep enforced
- T-2374: Burn DOC004/DOC006 WARN gates to zero, then promote to error
- T-2375: Burn LARGE001 WARN gate to zero, then promote to error
- T-2378: Decompose and burn frob-dup (exact+renamed) WARN findings to zero, then promote to error
- T-2389: retarget hardcoded src/frob/ literal in _env_var_docs.py and _root_asset_dirs.py to the T-2195 source-root resolver
- T-2391: a zero-findings gate result is ambiguous: unmeasured and inapplicable gates report as green
- T-2405: widen PORT001 scan scope past src/frob/gates/ (repo-wide src/frob/ hardcoded-identity sweep)
- T-2408: frob.lang.extract_imports has no typescript/rust/kotlin walker (import_graph capability gap)
- T-2409: no kotlin test collector (test_discovery capability gap)
- T-2410: walk_strata hardcodes RawSymbol.public=True (no real publicness semantics)
- T-2411: wire LANG004 capability_conformance_gate into the check job table
- T-2444: Fix pre-existing duplicate-title SystemExit failures in test_app_runners_t1738_wave.py
- T-2445: every land writes CHANGELOG.md and the version line, so scope-disjoint lands still conflict
- T-2452: _dispatch exceeds ARCH001 line threshold (found while T-2443 touched it)
- T-2455: related-title duplicate detector false-positives on holder/collider, breaking a pre-existing start test
- T-2464: Network dangerous-ops needles do not distinguish read vs write HTTP/DB verbs
- T-2466: LEXCHECK001 scans only gates/ and only re.* calls, so it missed a substring-matching security detector in vet/
- T-2467: Reshape T-1614: periodic watermark-based waiver audit, drop runs_last
- T-2469: LEXCHECK001 widening surfaced 5 real symref-less lexical deciders in vet/_supplychain.py
- T-2470: C++ ARCH symref producer spells qualnames with :: instead of frob's canonical . join
- T-2473: frob check has no global concurrency limit, so a busy fleet swaps and throughput drops as agents are added
- T-2475: fleet_status NEEDS CLOSE bucket can misclassify a partially-split, still-blocked story as closeable
- T-2476: drop the T-2448 COV001 waiver on gate_rule_registry_violations now that GATERULE001 has a doc entry
- T-2477: post-land sweep regression from T-1135: 5 new (rule, file) identit(ies), 0 finding(s) (E501, F401)
- T-2479: boto3/aiohttp/asyncpg mutating-verb split not covered by T-2464's net-mutate scanner signal
- T-2480: check-repro's fixed 60s budget turns a slow but valid repro test into an indistinguishable NO_VERDICT
- T-2481: the root-write guard does not cover Bash, which is how all three root-dirtying incidents actually happened
- T-2482: Declare fs.read/fs.write/exec for T-2467's waive-audit module+tests (SELFAUDIT001 SYS100)
- T-2484: T-2473's concurrent-check advisory writes to stdout, corrupting frob check --json under fleet load
- T-2485: waive-audit complete has no partial-catchup-progress path, defeating the 100-item bound
- T-2486: nothing structurally prevents a stdout write from corrupting --json output; T-2484 fixed one instance
- T-2487: add a post-Bash root-cleanliness detector for agent context (complementary to T-2481's guard)
- T-2488: Bump capability-via-ratchet.lock.json ceilings for T-2482/T-2464 (SELFAUDIT001 SYS111)
- T-2489: post-land sweep regression from T-2411: 1 new (rule, file) identit(ies) (E501)
- T-2490: SYS100: T-2411's wiring test in test_lang_conformance_gate.py declares no exec capability
- T-2491: sync docs/modules/app.md#runners for T-2486's structural --json stdout guard
- T-2492: audit other --json runners for the same unguarded-stdout-write class T-2486 fixed in check
- T-2493: waive-audit has no systematic INERT-waiver check (path/symbol-shape mismatch)
- T-2494: capability_import_graph_status hardcodes language set, stale after T-2408
- T-2495: declare may exec for gates node covering _mutation_evidence.py's direct guarded_subprocess_run call
- T-2496: wire find_collision_suspects into a waive-audit CLI subcommand
- T-2498: frob ticket body --append silently misroutes into done-report.md when one exists
- T-2499: capability_test_discovery_status hardcodes language set, stale after T-2409
- T-2500: boto3 net-mutate: exhaustive per-service mutating-verb survey (S3/DynamoDB/IAM done, ~347 services remain)
- T-2502: strata fragments: imports that cannot break a system apart
- T-2503: ambient vs enumerated capability grants: kill the via-list churn without losing the guard
- T-2504: confined to: prove path confinement on the existing summary engine, report-only first
- T-2505: DOC006/COV003/REF001 should not police historical records (117 of 140 findings)
- T-2507: vet resolves identities then compares them by substring; LEXCHECK001 trigger set misses the in operator
- T-2508: audit non-node/store/queue strata constructs for a future clearance concept
- T-2509: frob ticket evidence --check-repro ignores explicit --base-ref, always resolves to a fixed unrelated commit
- T-2517: fleet_status reports ORPHANED FORKSERVERS 0 while 82 stale pools hold 12GB of swap
- T-2519: confinement census: give parameter-position credit to close 727 of 740 UNKNOWN sites
- T-2520: post-land sweep regression from T-2507: 1 new (rule, file) identit(ies), 0 finding(s) (WIRE001)
- T-2521: auto-drop treats an incomplete measurement as proof of absence: 7 tickets dropped with ~66 live findings
- T-2523: wire check_ambient_capability_reasons into a gate and backfill the 27 reasonless ambient grants
- T-2524: agent scratch files in the repo root get committed by the next land
- T-2526: post-land sweep regression from T-2503: 5 new (rule, file) identit(ies) (E501, F401, F811)
- T-2527: re-add subprocess-coverage measurement to native_coverage_refresh (Loss-A regression, T-1235/T-1205/T-1397/T-1526 orphaned)
- T-2530: strata fragment merge is extend-only by implementation, not by type: seal the grant mapping
- T-2531: post-land sweep regression from T-2503: E501/F401 residue (3 files, unrelated to T-2526's F811)
- T-2532: WIRE001 reach scan misses dotted classmethod/staticmethod calls
- T-2533: DOC006 CLI-invocation walker misses several _dispatch_*-bypassed verbs' real subcommands
- T-2534: T-2505's historical-ticket-doc exemption should cover evidence/attachments dirs too
- T-2537: tool parsers report a crashed run as zero findings: attach an error diagnostic on unparsable output
- T-2539: may-raise resolver reports false EXHAUST002 leaks for multi-type except clauses and slice subscripts
- T-2543: may-raise resolver still mis-types two EXHAUST002 classes: subscript KeyError default and int()/float() TypeError
- T-2544: document tool_parse_failure_result in docs/modules/process.md and drop T-2537's AFFECT001 waivers
- T-2547: CrossTicketLeakage matches a zero-scope ticket as covering an unrelated unclaimed file
- T-2549: COV007 reads a strata security clearance as API privacy: 25 false findings on design/frob.strata
- T-2550: COV006: all 18 live findings are call-graph blindness (cross-file public entry, test-helper indirection), not unexercised bindings
- T-2551: COV007 is mis-scoped for files with no public surface: 78 findings in scripts/ and .claude/hooks/
- T-2552: builtin-raiser table attributes impossible raises: int/float TypeError, getattr/next default-arg overloads
- T-2556: worktree-lease pre-commit hook refuses agent commits inside the leased worktree, and its error message advises a remedy that does not work
- T-2557: no gate catches an in-progress ticket with an EMPTY scope: SCOPE001 is diff-driven, TICK009 only checks breadth
- T-2559: DOC006 flag resolution has the same _build_parser()-mirror-drift false positive T-2533 fixed for subcommand chains
- T-2561: Stale live lease scope drifts from an in-progress ticket's declared scope, undetected
- T-2563: ledger-only ticket edits from a worktree strand on the branch and never reach main
- T-2564: a land killed between stage and commit leaves content in the shared index where another land can absorb it
- T-2565: hook header comment and _OURS_MARKER name a nonexistent 'frob scaffold install-worktree-lease-hook' command
- T-2569: ticket close reports an UNMEASURABLE evidence batch as evidence no longer passes
- T-2570: ledger mirror makes main a second writer of per-ticket files: decide the v2 merge strategy
- T-2571: Post-land sweep files identical (rule,file) identities as new regressions across unrelated lands: baseline recurrence/phantom-path bug
- T-2574: M1: Ticket.milestone field, semver ordering, CLI surface
- T-2575: no grammar registered warning is 57 percent of command output: the pre-filter obligation is on callers and mostly unmet
- T-2576: M2: backfill open tickets to 1.0.0, add MILE003 gate
- T-2577: M3: milestone as primary doable sort axis, inheritance, --milestone filter
- T-2578: M4: rescope runs_last to the ticket's own milestone
- T-2579: M4b: MILE004 gate for multiple runs-last tickets in one milestone
- T-2580: M5: MILE001/MILE002 milestone-deadlock gates
- T-2581: M6: REL001 extension -- refuse release cut with open milestone-X tickets
- T-2582: human-mode query commands drown their answer in DEBUG chatter: xref emits 5958 lines for a 13-line result
- T-2583: Owner decision needed: pick which edge to invert to break the 160-node serve/stats/tickets/testing/app import cycle
- T-2584: CYCLE001 findings never pass through the waiver pipeline -- frob:waive CYCLE001 is silently inert
- T-2585: frob check has no durable result: replay an unchanged-tree verdict automatically, never as a flag
- T-2586: fleet_status reports ROOT DIRTY from a stat-dirty index, falsely blocking dispatch
- T-2587: Wire frob ticket promote into the T-2563 ledger mirror so a promoted id is visible on main immediately, not only after land
- T-2588: frob cycle reports a false CLEAN on the natural invocation and exits 0 on findings
- T-2595: Lock or CAS-write .frob/rapid-sweep-baseline.json against concurrent detached-sweep writers
- T-2596: four real E501 lines in src/ raised quarantine and forced the whole fleet into synchronous lands
- T-2598: stale AFFECT001 waiver hides cycle_runner doc drift: the follow-up ticket its reason promised was never filed
- T-2599: 34 registered worktrees, ~20 idle 9-13 days: audit needs a stranded-vs-stale test that squash-landing does not fool
- T-2602: test_doable_sprint_filter has been red on main since T-1995: the duplicate-title guard fires on its own fixture
- T-2603: three ledger-write patterns across two disjoint verb sets plus a special case: one table with a declared per-verb strategy
- T-2604: quarantine re-raises on findings already owned by an open ticket, forcing synchronous lands fleet-wide every sweep
- T-2606: waiver reasons promising a follow-up ticket should be enforced
- T-2609: land-time new-public-symbol doc/test-edge check does not offset for decorators
- T-2610: WIRE001 resolver misses @property attribute reads as real callers
- T-2611: core.autocrlf=true puts CRLF in every source file, silently breaking any length or byte-level measurement
- T-2612: every waiver citing a LIVE lease has an expired premise: 0 of 12 named tickets still hold one
- T-2613: Sync docs/modules/gates.md frob:enumerates member list (DOCENUM001, includes MILE003)
- T-2614: T-2450 scope is a single semicolon-joined glob string, not two scope entries
- T-2615: changelog emits an entry for a DROPPED ticket and duplicates the ticket id on 101 lines
- T-2616: milestone missing from MIRRORED_LEDGER_VERBS; 4 verbs unclassified in dispatch-table accounting test
- T-2617: worktree classifier reports 18 STRANDED where the verified answer is stale-behind-main, reproducing the exact test T-2599 specified against
- T-2618: declared_source_prefixes/declared_project_package_name never got their promised lang.md anchor (T-2612 audit)
- T-2619: unlanded_branch_work anomaly class undocumented (T-2612 lease-premise audit)
- T-2620: evidence_changes/EvidenceReplaceReasonMissing never got their promised tickets-data-storage.md entries (T-2612 audit)
- T-2622: unify lease-premise and follow-up-ticket-promise waiver checks (coordinate with T-2606)
- T-2623: roughly 19 tests are red on unmodified main, hiding real regressions in the noise
- T-2624: CLI wiring for runs_last_parallel_safe
- T-2625: worktree classifier: ACTIVE verdict does not distinguish queued-idle from a live lease
- T-2626: scope write path never validates individual glob syntax (semicolon-joined entries silently stored)
- T-2629: frob ticket doable does not complete: rendering scans all 938 branches with a temp-file parse per directive
- T-2630: tests/unit/strata/test_export_golden.py red on main: golden export drift
- T-2631: test_lang_parse_guard.py: guard-helper wiring assertion red on main
- T-2632: test_mutation_sweep_queue.py: test_counts_only_pending_entries red on main
- T-2633: CLI test drift: renumber/land SystemExit + stamp-baseline output string (4 tests red)
- T-2634: Self-conform/mutation-audit/threat cluster: 6 tests red on main, design vs live-repo drift
- T-2635: test_exports.py: frob-exports reports missing symbols in src/frob, red on main
- T-2636: tmLanguage grammar missing 'exclusive' clause keyword (test red on main)
- T-2637: test_conftest_stackdump.py: _FakeItem stub missing get_closest_marker, red on main
- T-2638: disclosure-remainder guard is lexical and blind to draft ids: rewording a heading defeats it, drafts can never satisfy it
- T-2639: Wire WAIVE009 into frob check + document in gates.md
- T-2641: clean up stray changelog.d/T-2593.md fragment left by the T-2615 bug
- T-2645: unlanded-branch directive parsing uses a temp-file round trip per candidate
- T-2646: 938 stale local branches are accumulated debt -- needs a stranded-work analysis before pruning
- T-2647: unused _LEDGER_TRANSACTIONAL_VERBS import raises quarantine and forces synchronous lands fleet-wide
- T-2651: fleet_status enumerates leases from worktrees, so a leaked lease with no worktree is invisible -- the exact case that matters
- T-2653: post-land sweep regression from T-2638: 45 new (rule, file) identit(ies), 71 finding(s) (ARCH103, COV001, COV003, COV004)
- T-2654: fleet_status: flag an in-progress ticket that is also blocked_by an open blocker
- T-2655: T-2651 landed new fleet_status symbols without test/doc edges (COV001+DOC002), raising quarantine
- T-2656: Fix 13 stale lease/binding-premise waivers surfaced by WAIVE006's T-2622 extension
- T-2662: docs/modules/gates.md: add table rows for CYCLE001/MILE001-004/TICK012/WAIVE009
- T-2664: DOCENUM001 passes with member ids listed but never documented
- T-2665: lease-leak detector reports [LEAK] for a ticket whose worktree exists, inviting a destructive requeue
- T-2666: testsuite node's ambient exec grant (T-2503) collides with SYS107 fail-closed policy (T-2224)
- T-2667: Owner decision needed: break the remaining stats-independent serve/tickets/testing/app import cycle (candidates 1/3/4/5 + a missed sixth edge)
- T-2668: land records 'gates: unmeasured' and proceeds while a real SELFAUDIT001 error sits in its own findings list
- T-2669: rapid-profile land fails to commit its own rapid-debt.jsonl, dirtying the shared root and DirtyMain-blocking the fleet (70x today)
- T-2670: docs/modules/gates.md: 80 gate rule ids in the DOCENUM001 member list have zero documentation
- T-2672: sweep attributes findings to lands that never touched the flagged files: 6 of 6 tickets, including two filed after T-2571 and T-2595
- T-2673: DOCENUM001's ID_TOKEN_RE cannot match hyphenated ids ending in letters (PORT001-IDENT, PORT001-PATH)
- T-2674: Persistent unfixed repo-debt tracking (continuation of T-2653): 37 identit(ies) remaining
- T-2675: test_derived_match hardcoded MIRRORED_LEDGER_VERBS set is stale after T-2624
- T-2677: fleet_status.py's REPO constant resolves via __file__, giving 0 live leases when run from a worktree
- T-2678: frob ticket body writes an archived ticket's update to a fresh non-archive copy, causing DuplicateId
- T-2679: A timed-out land marks the ticket done and records evidence while zero code reaches main
- T-2680: playbook 5b's FROB_WORKTREE/FROB_AGENT leak fix only covers tests/system/**, not direct land()/new_ticket() calls elsewhere
- T-2681: Add frob ticket unblock verb -- blocked_by can only be appended, never removed, via CLI
- T-2682: LANG004: behavioral coverage for test_discovery (the last of 7 capabilities left structural-only)
- T-2683: Consumer-side self-disclosure when an OPTIONAL adapter capability gap silently degrades output
- T-2685: Persistent unfixed repo-debt tracking (continuation of T-2674): 35 identit(ies) remaining
- T-2686: COV003 on 6 closed tickets: deleted/renamed test node ids, six materially different dispositions needed
- T-2688: Gate: refuse/warn when a diff deletes or renames a test cited as some ticket's evidence
- T-2690: TICK006 phantom-filing auto-recovery is 92% false-positive and its refusal blocks unrelated lands
- T-2693: TICK006 phantom-refile of T-draft-be1e79b5 (cited by T-2685) collides with T-2689's identical title/scope
- T-2694: Split src/frob/app/telemetry.py: 3 real seams (event/footgun/usage), T-1656 successor
- T-2695: LARGE001 remainder batch 2: ~80 files after T-1656's batch-1 (2 waived, 1 seam filed)
- T-2697: post-land sweep regression from an unattributed source (sweep spawned by T-1549): 1 new (rule, file) identit(ies), 1 finding(s) (DOC006)
- T-2698: LANG004: behavioral test_discovery coverage for rust/typescript/c/cpp/kotlin (cost-blocked, needs a bounded offline-safe fixture design)
- T-2700: Wire import_graph_gap_disclosure into frob.cycle.graph's real DependencyGraph/find_cycles output
- T-2702: T-2690's phantom-refile fix does not work: two more auto-filed recoveries from lands that contained it
- T-2703: DOC006 scans inline code spans, reading C++ lambda captures as TOML section keys (72 false positives downstream)
- T-2704: DOC008/DOC011 normalize ../ with a string replace instead of path resolution, breaking every valid parent-relative link (2 sites)
- T-2705: DOC010 only resolves make targets against the root Makefile, missing nested project Makefiles
- T-2706: LANG004 reports frob's own src/frob/ paths into consumer repos, where they are unactionable
- T-2707: SYS004 replaces the real ImportError with a hardcoded not-installed message, misdirecting diagnosis
- T-2708: make install-tool is broken on uv 0.11.19: uv tool install has no --extra flag, blocking the only sanctioned install path
- T-2709: Single-mode test coverage for set_body's archive routing (T-2678 successor)
- T-2710: Thread the real failing ledger path through GateError.QueueUnavailable (T-2684 successor)
- T-2711: A passenger ticket's content lands via --allow-cross-ticket while its own ledger state stays non-terminal, leaking its scope lease
- T-2712: Re-triage 20 newly-unwaived PII010/011/012 findings after T-2696's symref population
- T-2713: Deferred verification advances the watermark and records the rolling baseline from a budget-truncated check (saw 2 of 40 error identities, called it GREEN)
- T-2714: A killed land strands its staged snapshot in the shared root, DirtyMain-blocking the whole fleet
- T-2715: Deferred verification is deadlocked: the 480s budget is 12s short of the tool's own recorded 492s stage total
- T-2719: RENDER001: add directory/file exemptions for standalone no-frob-import scripts
- T-2720: COV005: reduce false positives on brand-new private helpers sharing a directive anchor
- T-2721: waive-audit progress is gitignored per-checkout, so an agent's audit pass is destroyed with its worktree
- T-2722: post-land sweep regression from an unattributed source (sweep spawned by T-1614): 1 new (rule, file) identit(ies), 2 finding(s) (TICK006)
- T-2723: Gate cache is not invalidated by a frob upgrade, so consumers keep seeing pre-fix findings on an unchanged tree
- T-2726: disclosure_shaped_language signal 1 (phrase match) scans the whole ticket body, not just the Done report
- T-2728: Wire migrate_missing_v2 into the CLI, or delete it
- T-2729: LARGE001: split strata/_selfconform.py (2290 lines) by SYS1xx rule family
- T-2732: post-land sweep regression from an unattributed source (sweep spawned by T-2723): 137 new (rule, file) identit(ies), 1 finding(s) (ARCH001, ARCH102, ARCH103, E501)
- T-2733: remove now-redundant frob:waive RENDER001 directives in .claude/hooks and scripts/fleet_status.py
- T-2735: Document T-2721's git-tracked/mirrored waive-audit watermark in docs/modules/app.md
- T-2738: frob ticket close does not promote pending drafts, so a closed ticket's follow-ups are silently lost
- T-2739: verify T-2481/T-1943 COV005 waivers against T-2720's narrowed detector, remove any that no longer reproduce
- T-2740: waive-audit cannot distinguish a necessary waiver from an inert one: 11 RENDER001 waivers sat on paths the gate never scanned
- T-2741: Fix 2 remaining PII012 waiver-placement gaps T-2712 could not touch
- T-2742: No reliable way to detect an in-flight land: every hand-rolled pgrep matches the polling shells themselves
- T-2743: Repo-wide pre-existing debt surfaced by T-2713/T-2715's deferred-verification repair (from T-2716 re-triage)
- T-2744: Quarantine was cleared citing an auto-filed ticket that does not exist, releasing findings against a phantom home
- T-2745: post-land sweep regression from an unattributed source (sweep spawned by T-2712): 1 new (rule, file) identit(ies), 1 finding(s) (DOC006)
- T-2746: WIRE001 cannot see a @property's own attribute-access caller (false positive)
- T-2747: fleet_status reports a live worktree as a leaked lease when the worktree is not named t-<id>
- T-2749: post-land sweep regression from T-2738: 2 new (rule, file) identit(ies), 7 finding(s) (ARCH103, DRIFT002)
- T-2751: close draft-promotion scan (T-2738) attempts already-terminal DROPPED drafts, spurious failure
- T-2753: WIRE001 call-graph resolver cannot see pytest fixture consumption via dependency injection
- T-2755: worktree_content_classification's ticket_id resolution keys on t-<id> worktree naming, same class as T-2747
- T-2757: post-land sweep regression from an unattributed source (sweep spawned by T-2741): 1 new (rule, file) identit(ies), 1 finding(s) (DOC011)
- T-2759: DOC011: docs/modules/tickets-verify-sweep.md cites phantom T-2736 without a waiver
- T-2760: Two tickets can own the same (rule, file) finding: the duplicate check compares titles, not finding identity
- T-2761: Wire frob fmt callers to per-language resolve_line_length (T-1606 follow-up)
- T-2762: Reproduce/fix xdist contention for 4 real-repo build_graph tests found by T-1654 audit
- T-2763: Coverage data is 14 days stale because the refresh OOMs in parallel and overruns serially, leaving TEST005 silently unmeasurable
- T-2764: frob check does not run check_native_staleness_or_exit; make check does (workflow-parity gap)
- T-2766: docs/modules/arch.md severity table stale: ARCH101/ARCH102 listed as warning, frob.toml overrides to error
- T-2770: frob ticket has no parent setter, so a mis-parented ticket cannot be corrected without a forbidden ledger hand-edit
- T-2771: retarget OVER_BROAD_LITERAL_GLOBS off hardcoded src/frob/ literal in tickets/_models.py
- T-2772: retarget hardcoded src/frob glob in _new.py's related-check-function suggestion
- T-2773: Reformat batch 1/N: 15 files pending ruff-format (T-2359 child)
- T-2774: a contended land is SIGKILLed mid-work because the 500s lock-wait guard bounds only the wait, not wait+work against the caller's cap
- T-2775: no shared primitive for 'wait until a land slot is free', so every agent hand-rolls a noisy poll loop that misreads failure as zero
- T-2776: Reformat batch 2/N: 10 files pending ruff-format (T-2359 child)
- T-2777: Reformat batch 3 of ruff-format-only reformat (T-2359 child)
- T-2778: WIRE001's call-graph walk cannot resolve a symbol wired only as a passed-by-name callback argument
- T-2779: agent-playbook documents a superseded landing rule that stranded four agents and permitted the concurrent-land kill
- T-2780: add set-parent to tickets-lifecycle.md's verb-strategy table doc
- T-2782: landing is serialized on a ~300s critical section, capping fleet throughput at ~1 ticket/5-6min regardless of agent count
- T-2783: Reformat batch 4/N: 10 files pending ruff-format (T-2359 child)
- T-2785: frob ticket set-parent reports success while its auto-commit was refused, leaving the shared root dirty and blocking every agent land
- T-2786: Reformat batch 5/N: 13 files pending ruff-format (T-2359 child)
- T-2787: Reformat batch 6/N: 13 files pending ruff-format (T-2359 child)
- T-2788: Burn ruff I001 batch 1: src/frob non-gates files
- T-2789: Reformat batch 7/N: 13 files pending ruff-format (T-2359 child)
- T-2790: frob check's 274s cost is now the only lever on fleet throughput: profile the top four whole-program stages and decide what is reducible
- T-2792: Reformat batch 8/N: 13 files pending ruff-format (T-2359 child)
- T-2793: stale natives make frob check fast-exit in 14s, and the rapid sweep records that 2-finding abort as the rolling baseline -- verification reports GREEN having run zero gates
- T-2794: Reformat batch 9/N: 13 files pending ruff-format (T-2359 child)
- T-2795: Reformat batch 10/N: 13 files pending ruff-format (T-2359 child)
- T-2796: a large fraction of the queued backlog is already resolved by landed work, and 'already resolved' was being requeued instead of dropped
- T-2798: size a content-hash cache for sys's ast-based capability scan (currently fully uncached, largest single stage)
- T-2800: Burn ruff I001 batch 2: tests/ subset
- T-2801: post-land sweep regression from T-2794, T-2686, T-2795, T-2675, T-2790: 18 new (rule, file) identit(ies), 37 finding(s) (COV001, CYCLE001, DOC001, DOC006)
- T-2804: post-land sweep regression from an unattributed source (sweep spawned by T-2796): 3 new (rule, file) identit(ies), 3 finding(s) (DOC001, DOC011, TICK006)
- T-2805: native-staleness content-digest check is a permanent latch: a reproducible rebuild is byte-identical, so frob natives build can never clear NATIVE001
- T-2806: Stamp the parse-artifact cache env before build_graph, not just before the gate process pool
- T-2807: wait_for_land_slot reports a free slot during the window where frob's own T-1619 process scan still refuses LandInProgress
- T-2808: Reformat batch 11/N: 13 files pending ruff-format (T-2359 child)
- T-2809: land deadline guard has a load feedback loop: contended stage timings inflate estimated_work_s until every land declines, exactly when the fleet is busiest
- T-2810: COV007 burn-down batch 1/N: src/frob/strata/_multifile.py duplicate doc anchors
- T-2811: Reformat batch 12/N: 13 files pending ruff-format (T-2359 child)
- T-2812: REG008 burn-down batch 1/N: 19 missing frob:enforces directives in gates/perf modules
- T-2813: Reformat batch 13/N: 13 files pending ruff-format (T-2359 child)
- T-2814: Reformat batch 14/N: 13 files pending ruff-format (T-2359 child)
- T-2815: Reformat batch 15/N: 10 files pending ruff-format (T-2359 child)
- T-2816: land-lock wait budget spends the caller's own work-time budget on queueing, not just measuring it
- T-2817: document T-2807's unattributed-land-process probe in coordinator-scripts.md
- T-2818: fleet_status reports 0 orphaned forkservers while 90 leaked ones hold 13GB: the orphan check tests only the immediate parent, not the ancestry root
- T-2820: REF001/REF002 systematic collapse (glob entrypoints) + promote to error
- T-2821: Reformat batch 16/N: 12 files pending ruff-format (T-2359 child)
- T-2822: LARGE001: split or waive oversized frob.tickets modules, batch 2 of 2
- T-2823: LARGE001: split or waive oversized frob.vet/graph/arch modules
- T-2824: LARGE001: split or waive oversized misc small-package modules + native (rust) files
- T-2825: LARGE001: split or waive oversized frob.tickets modules, batch 1 of 2
- T-2826: LARGE001: split or waive oversized frob.strata modules (excludes T-2729's _selfconform.py)
- T-2827: LARGE001: split or waive oversized frob.gates modules, batch 2 of 2
- T-2828: LARGE001: split or waive oversized frob.gates modules, batch 1 of 2
- T-2829: LARGE001: split or waive oversized frob.app/ticket_runner modules, batch 2 of 2
- T-2830: LARGE001: split or waive oversized frob.app/ticket_runner modules, batch 1 of 2
- T-2831: LARGE001: promote large-file from WARN to ERROR in _arch.py (T-2375 successor)
- T-2832: REG008 burn-down batch 2/N: 17 missing frob:enforces directives across gates/app/strata/check modules
- T-2833: Split frob.tickets._leases's worktree-sweep family into _worktree_sweep.py
- T-2834: Split frob.tickets._setters's sprint/flow analytics family into _flow.py
- T-2836: REG008 burn-down batch 3/N: CHK-GATE-DOC012 (final entry, lease cleared)
- T-2839: Fix malformed frob:waive LARGE001 directive on arch/_patterns.py (T-2823 regression)
- T-2840: frob ticket requeue from a worktree reports success while its ledger mirror never reaches main, leaving a stale in-progress state and a held lease
- T-2841: Fix I001 import-sort regression in T-2729's selfconform split (6 files)
- T-2843: Split frob.gates._doclink_docanchor's later-bolted docstatus/docmake/docseverity gates out
- T-2844: Split _host_isolation.py along lateral/vertical/movement seams (blocked on via-scope migration review)
- T-2845: Split scripts/fleet_status.py into readiness/procscan/rot submodules
- T-2846: Split frob-core/src/lib.rs's clone-detection rungs into sibling modules
- T-2847: LARGE001: src/frob/tickets/_setters.py unwaived after T-2834's split (1111 lines)
- T-2849: frob check leaks its multiprocessing forkservers: ~150 orphans reaped by hand in one session, once reaching 16.7GB swap and stalling all lands for 45 minutes
- T-2850: root-write-guard cannot see a pre-worktree agent: both its signals are set by frob ticket work, so an agent editing the root before creating its worktree is indistinguishable from a human
- T-2851: Split BUG002/must-still-pass repro-classification family out of frob.gates._mutation_evidence
- T-2853: LARGE001: src/frob/tickets/_leases.py unwaived after T-2833's split (3182 lines)
- T-2854: malformed-directive false-positive: docstring prose containing 'frob:waive reason' parsed as an attribute
- T-2855: post-land sweep regression from T-2846: 22 new (rule, file) identit(ies), 172 finding(s) (COV001, DOC006, DRIFT002, REF001)
- T-2857: the frob comment DSL drops malformed directives SILENTLY: four distinct failure modes measured in one session, each leaving a finding unsuppressed with no diagnostic
- T-2858: Main red: DRIFT002/DOC006/COV001/TEST001 outside T-2855 scope (tickets-data-storage.md, test005 audit, callgraph.py, _multifile.py)
- T-2860: T-2850 blocks frob ticket land from the root, and its FROB_COORDINATOR escape hatch only works session-wide, so the choice is guard-on-nobody-lands or guard-off-for-everyone
- T-2864: F401/F822: T-2851 split left import/export hygiene debt in _mutation_evidence.py/_bug_repro.py
- T-2865: Burn COV006 WARN findings to zero via individual waivers (never promote)
- T-2869: docs/modules/tickets-landing.md has a frob:enumerates anchor with no members= attribute
- T-2870: BUG002 ticket-body waiver regex silently ignores an unquoted/malformed reason= value
- T-2871: Fix SELFAUDIT001: T-2851/T-2843 splits left gates capability via-lists stale, plus 2 ratchet ceiling bumps
- T-2872: Fix COV003: 12 tickets cite renamed test_large_file_fires_large001_warn
- T-2873: Write 36 individual COV007 waivers (all but the T-2849-blocked _reap.py finding)
- T-2874: Waive COV007's last finding (_reap.py) and promote COV007 to ERROR
- T-2875: frob.graph.dsl._RESERVED_MARKER_VERBS omits callee-raises, so a real # frob:callee-raises call-site marker fires DSL001 unknown-verb
- T-2877: SELFAUDIT001: T-2849's process/_reap.py env.read growth and a new via-less core ffi grant lack ratchet/because coverage
- T-2878: close's draft auto-promote sweeps ANOTHER ticket's pending draft, races its rightful promotion
- T-2879: Red-tail sweep: COV001/DRIFT002/DOCENUM001/PERF004/DOC011/DOC006 (6 independent causes, CYCLE001/TICK004 verified correctly left alone)
- T-2880: T-2849's PDEATHSIG fix is loaded but forkservers still leak: 27 new orphans in the 49 minutes after it landed, likely an already-started helper that never sees the arming env var
- T-2883: docs/modules/gates.md: document T-2870's BUG002 malformed-waiver diagnostic
- T-2884: Daemon version-skew self-heal is version-string-based, blind to source-only changes with no version bump
- T-2885: OPAQUE001/sys false positives: module docstring not excluded when a comment precedes it
- T-2888: Red-tail sweep round 2: OPAQUE001 fix, LANG004/TICK003/TICK006 characterized
- T-2891: twelve *SCHEMA-family gates (plus FLAGCOV) resolve UNRESOLVED off-repo and render as a clean pass
- T-2892: T-2384: bind evidence to acceptance criteria and close epic
- T-2893: post-land sweep regression from an unattributed source (sweep spawned by T-2875): 13 new (rule, file) identit(ies), 12 finding(s) (COV004, DOC006)
- T-2895: Root-write guard: cwd-keyed target, dead FROB_COORDINATOR hatch, mis-scoped ledger exemption
- T-2899: post-land sweep regression from an unattributed source (sweep spawned by T-2361): 1 new (rule, file) identit(ies), 2 finding(s) (I001)
- T-2900: wire or drop _parse_bash (bash raw-parse test helper)
- T-2901: call_graph: bash bare-word invocation unrecognized by shared token-adjacency call detector
- T-2902: post-land sweep regression from T-2891, T-1604: 5 new (rule, file) identit(ies), 5 finding(s) (DOC006, DOC008, LANG003)
- T-2905: wire or drop _parse_csharp (csharp raw-parse test helper)
- T-2906: wire bash+csharp into frob.vet/frob.dup/frob.gates._docblocks (capability/dup/docblock facets)
- T-2908: frob-suggest: three nudge rules misfire and tax every agent call with a retry
- T-2909: Agent cold-start: split agent-playbook.md into a hot-path checklist plus an appendix
- T-2910: frob sys init: derive a starting strata model so a new repo gets value on day one
- T-2911: frob status: show movement (burned/promoted/closed) so a large finding count does not read as no progress
- T-2912: Instrument agent tool-call histograms to target token cost at measured hotspots
- T-2913: Rapid land still runs a full inline frob check on the land critical path, serialized under land.lock
- T-2914: WIRE002: T-2645's WIRE001 waiver on _unlanded.py::_remove_scratch_file missing follow_up
- T-2915: Re-run branch stranded-work classification with the real directive parser, not bare regex
- T-2917: CI runs ubuntu-latest only: add windows-latest and macos-latest to the matrix so platform regressions are detectable at all
- T-2918: Advisory locks degrade to a logged NO-OP without fcntl: concurrent lands/sweeps are unserialized on Windows
- T-2919: PLATFORM001 gate: every POSIX-only primitive must declare a cross-platform path or refuse LOUDLY, never warn-and-continue
- T-2920: Strata ratchet: shrink-only auto-tightening, capability escalation is always an error
- T-2922: Unwire the live may= auto-WIDENING Tier-A fixer: capability escalation is silently rubber-stamped today
- T-2923: frob sys shrink: tighten unobserved may= capabilities, never widen
- T-2927: frob-suggest: add missing must-stay-quiet fixtures for 5 rules
- T-2928: WIRE001 and REF002 both MISS provably dead symbols: measured 1-of-3 detector hit rate on a controlled deletion
- T-2929: rapid verification debt drifts silently and poisons attribution (post-land sweep files false regressions on a stale baseline)
- T-2930: Triage macOS-only pytest failures found via T-2917 CI matrix (156 failures, non-fcntl/prctl remainder)
- T-2931: Generalize WIRE001's dynamic-dispatch exemption to recognize atexit.register callbacks
- T-2932: frob-suggest: recursive-grep negative pattern misses a scoped command's own 2>&1 redirect
- T-2934: Fix 5 real PLATFORM001 findings: fcntl warn-and-continue in _lock.py/_land.py/_land_git_ops.py/_store.py
- T-2935: Delete _sync_may.py's dead SYS100 auto-widening functions
- T-2936: frob does not IMPORT on Windows: signal.SIGKILL evaluated as a default arg at module load crashes in 54s before any test runs
- T-2937: frob ticket new blocks up to ~5min on an unrelated land, then strands an uncommitted ticket on timeout
- T-2938: Move ClaimDivergence re-verification onto the deferred post-land queue instead of scoping it inline
- T-2940: README.md: add the frob status command-table row/count (T-2911 land-tooling workaround)
- T-2941: frob ticket land: DOC005 pre-merge guard checks a same-diff new subcommand against a stale, pre-merge registry (refuses forever, unwaivable)
- T-2942: macOS CI: remaining small failure clusters needing individual triage (SYS107, FIFO pipe, timing threshold, resolved-root, load_lock)
- T-2943: macOS: git subprocess returncode=128 in test fixtures - 100+ system/CLI test failures, root cause unconfirmed
- T-2944: PLATFORM001 misses sys.platform-string guards; /proc-only worktree-liveness scan is permissive on macOS/Windows
- T-2945: AF_UNIX socket path too long on macOS: relocate daemon.sock off deep project-root paths
- T-2946: Burn TICK004/TICK007 to zero via real ticket-queue triage, then promote
- T-2947: Land writes state=done and promotes drafts BEFORE the git merge succeeds: tip-drift leaves ledger-done with code absent from main
- T-2949: frob ticket land --finish: 'already done' check reads uncommitted working-tree state, not main's HEAD -- can delete a worktree before the real land happens
- T-2950: frob status takes 5m41s: an adoption surface nobody will wait for, and it exceeds the 200s foreground budget
- T-2951: PLATFORM001 gap: does not catch platform-restricted attributes evaluated at import/def time (default args, module/class constants, decorator kwargs)
- T-2952: Windows still cannot import frob: bare unconditional 'import fcntl' in _new_renumber.py/_socketd.py/_coverage_wait.py
- T-2953: Windows: natives build crashes with UnicodeDecodeError decoding maturin subprocess output (cp1252)
- T-2954: frob ticket archive can strand a non-terminal ticket with no restore path (T-0450)
- T-2955: frob-dup: triage tests/ duplicate cluster (~490 groups)
- T-2956: frob-dup: triage src/frob/gates renamed-duplicate cluster (20 groups)
- T-2961: Windows: ty check fails on POSIX-only stdlib attrs (socket.AF_UNIX, socketserver.ThreadingUnixStreamServer, os.nice)
- T-2966: frob-dup: finish src/frob/gates cluster triage (23 residue groups)
- T-2968: test_cli_cycle.py: 3 exit-code assertions predate cycle-found=1 CLI contract
- T-2969: Audit remaining test_cli_*.py fixtures for the same missing-git-init pattern as T-2943
- T-2970: frob-dup: narrow the tests/ renamed-detector threshold (fixture-repetition false positives)
- T-2971: Re-measure macOS CI after T-2943/T-2969 land
- T-2977: post-land sweep regression from an unattributed source (sweep spawned by T-2966): 2 new (rule, file) identit(ies), 2 finding(s) (F401)
- T-2978: Long-running commands show no live progress: no phase, no unit count, no elapsed time on a TTY
- T-2979: Default output is debug spam: gitio/process spawn traces drown the result on nearly every command
- T-2980: ubuntu-latest CI hangs in the Test step for 2+ hours: no green baseline exists on any platform
- T-2981: windows-latest CI fails at Typecheck on main after passing native build, both cargo suites and lint
- T-2983: gh_io part 1: typed gh seam with named failure modes (no gh, no auth, no GitHub remote, rate limit, empty-log-on-failed-job)
- T-2984: gh_io part 2: structured CI failure reporting -- typed run/job/step/test-node records, clustered by signature, no raw log grepping
- T-2985: gh_io part 3: CI result validity -- classify each outcome STILL VALID / STALE / UNKNOWN against the affects graph, never render stale as green
- T-2986: Archive move breaks COV004 attachment path resolution repo-wide (tickets/archive/<id> vs recorded tickets/<id> path)
- T-2988: Docstrings: replace the blanket one-line rule with a utility/reuse test and per-visibility tiers; move ticket archaeology out of code
- T-2989: Rename frob.yamlio to frob.yamlio for io-seam naming consistency (via frob refactor, not hand-edits)
- T-2990: frob refactor has no module/file move verb: symbol-scoped only, so a module rename falls back to hand-editing imports
- T-2991: frob subprocess children spawned by system tests can be orphaned when their pytest worker is killed
- T-2992: capture and triage the real test failures the ubuntu CI hang was hiding
- T-2993: Ticket-narrative comment blocks: 1728 blocks / 11116 lines of T-id archaeology in code, still being written
- T-2995: Docs narrative: 44% of doc lines sit in paragraphs citing a ticket id; keep the change info, move the story
- T-2996: Language-support matrix has 5 facets but 13 packages specialize per-language; refactor is silently Python-only and invisible to detection
- T-2997: rapid-debt.jsonl grows unbounded in git with no rotation: 2882 lines / 345KB, appended by every land, a merge-conflict hotspot
- T-2999: Baseline lock files: staleness warning, and a LOUD failure when the producer that stamps them stops running
- T-3000: Verbose flag after a subcommand is silently accepted and ignored: only the pre-subcommand position works
- T-3001: Verification debt can never drain under fleet load: the budgeted verify run truncates, reports Unmeasurable, and retries forever
- T-3003: Windows now reaches the Test stage: 19 failures across 7 files, clustered in test_cli_check and test_rule_id_scan_branches
- T-3005: strata-core graph kernel: generic typed nodes, typed edges, closure, level constraints, cycle detection (see T-3004 section 4)
- T-3006: Multi-modal strata redesign: behaviour/implementation/configuration split, VHDL entity-architecture model (T-3004 section 5)
- T-3007: V-model spec graph as strata instances: requirement/spec/design/component nodes with paired verification levels (T-3004 sections 1-2)
- T-3009: Enforce TDD from git history: a verification nodes introducing commit must precede its implementation node (T-3004 section 7)
- T-3011: Epic: publish frob-core and strata-core wheels to PyPI -- build now, publish only on explicit owner consent
- T-3013: post-land sweep regression from an unattributed source (sweep spawned by T-2990): 1 new (rule, file) identit(ies), 0 finding(s) (DOC006)
- T-3014: Wire NARR001 (T-2993's narrative-block detector) into gates/__init__.py
- T-3015: guarded_subprocess_run raises subprocess.TimeoutExpired uncaught instead of returning Err
- T-3017: post-land sweep regression from an unattributed source (sweep spawned by T-2993): 2 new (rule, file) identit(ies), 1 finding(s) (I001, REF002)
- T-3018: os.kill(pid,0) liveness probe can actually TerminateProcess on Windows (land.py, leases.py)
- T-3019: frob check fires spurious REF001/PRE001/SCOPE001 on any clean project; frob check is not repo-clean on main
- T-3025: A single trivial unattributed finding disables fleet-wide landing: four occurrences today, ~90 minutes lost, no severity proportionality
- T-3026: Post-land findings from the T-3006/T-2995/T-3014 batch: ARCH103, DOC001, E501, 2x LARGE001, REF001, REF002
- T-3027: post-land sweep regression from an unattributed source (sweep spawned by T-3011): 1 new (rule, file) identit(ies), 3 finding(s) (E501)
- T-3029: self-conformance (SYS100/SYS102/SYS107) red on main: ci_report.py/ci_validity.py/ghio.py unbound, env.read gaps
- T-3030: _STAGE_GROUPS missing milestone/env_var_docs/root_asset_dirs/profile_boundary gates
- T-3031: TestCheckTypescript::test_clean_ts_passes_tsc fails on main (REF001 on node_modules/package.json/tsconfig.json, MILE003 on real tickets.md)
- T-3033: test_doctor.py times out under xdist contention (branch-scan cost)
- T-3034: 26 uncharacterized Linux test failures need per-test triage
- T-3035: ticket-leases dispatch-table fixture missing --reason for mutate verbs (5 tests)
- T-3037: stale ticket-minting test fixture trips T-2394 empty-scope guard (28 tests)
- T-3038: evidence bind-time cost probe loses timeout floor after T-3015
- T-3039: mutate scores timeout as run-abort not killed-mutant after T-3015
- T-3040: frob cycle refuses on bare tmp_path, breaking 3 test_system.py tests
- T-3041: 13 live-repo self-conformance tests fail (repo currently non-zero on multiple gates)
- T-3042: V-model H1: vmodel_check has zero callers and no authoring format, so the epic can complete without ever checking anything
- T-3043: V-model H2: the four closure rules check local edge degree, not path closure -- a mutual-satisfies pair with zero requirements passes all four
- T-3044: V-model H3: graph nodes carry no payload -- test nodes bind to nothing runnable, artifacts bind to no code, supersedes cannot carry a reason
- T-3045: V-model H5: the UI/UX requirement has no design; CMD_EVIDENCE_ALLOWED_KINDS structurally forbids UX tickets from carrying non-pytest evidence
- T-3046: V-model M6: evidence laundering -- T-3005 and T-3007 landed on parse-test evidence that never touches the graph code they added
- T-3050: Land H3: DirtyMain auto-heal will auto-commit a false state=done to main -- it never checks the orphan ticket state
- T-3051: Land H4: the quarantine deadlock is UNFIXED -- _dispose_to_existing_duplicate_or_none handles DuplicateTicket but not DuplicateFinding
- T-3052: Land H5: the rolling baseline is written before the outcome is decided, so an unfilable finding is silently certified green after one wake
- T-3056: docs/strata/vmodel.md: update closure-rule prose for T-3043's path-reachability fix and new rule 5
- T-3057: Wire TDD001 ordering check into frob ticket land pre-land path
- T-3060: override_ratchet disables the pre-commit sweep, so lands publish lint errors: two classes reached main this way today
- T-3061: Put the 2.9s lint gate back on the rapid land path without re-enabling TEST016 mutation testing
- T-3062: Lint for waive-vs-debt misuse: flag a frob:waive whose reason is temporary (cites a ticket, until, pending, once X lands)
- T-3064: Break the 182-node import cycle: extract universal value types out of gates._models into a leaf module
- T-3065: Quarantine finding identities are keyed by literal string equality on a path whose shape varies by caller; normalize at write time
- T-3066: frob refactor split/move-module false-refuses on any nested import of the source module
- T-3069: Hook: nudge hand-performed renames toward frob refactor, without misfiring on ordinary import edits
- T-3072: Forkserver orphans persist after T-2880: 23 detected with no live check ancestry, and no command reaps them
- T-3075: Five tests read ambient developer state (global git identity, real ~/.claude) and so pass locally but fail in CI
- T-3078: TEST001 gap: T-3044's new graph::model attrs API has no bound unit test
- T-3079: post-land sweep regression from T-3044: 2 new (rule, file) identit(ies), 2 finding(s) (LARGE001)
- T-3080: Remaining T-2394 empty-scope fixture drift (10 tests, T-3037 residue)
- T-3081: TicketSpec.no_scope_declared silently dropped by new_ticket
- T-3085: post-land sweep regression from T-3065, T-3039, T-3060: 1 new (rule, file) identit(ies), 0 finding(s) (I001)
- T-3086: Break the 182-node import cycle (redo): T-3064 closed done without performing the extraction
- T-3087: A ticket can reach done with an unsatisfied blocked_by, and a falsely-closed ticket cannot be reopened
- T-3088: Land compose: out-of-tree tree/commit-object plumbing + CAS ref publish primitive
- T-3089: Wire out-of-tree compose+CAS publish into the squash-apply land stage
- T-3092: Warn when a FEATURE/BUG ticket closes with an empty code diff
- T-3093: fleet_status reports lock WAITERS as holders: label claims more than the /proc fd scan measures
- T-3094: T-2221 fleet xdist bound never reaches pytest: 0 of 40 running workers carry PYTEST_XDIST_AUTO_NUM_WORKERS
- T-3095: Isolate land's three post-squash file-mutating stages so the whole transaction is invisible in the shared tree
- T-3099: Wire T-3094 apply_agent_env/warn_if_xdist_bound_missing into pytest-spawn call sites
- T-3104: BUG002 cannot verify environment-absence bugs: the sandbox always has the thing whose absence is the defect
- T-3105: refactor split: import-rewrite drags unmoved names to destination module
- T-3106: Fix fleet_status.py orphan false-positive and add frob process reap command
- T-3107: Out-of-tree three-way squash compose via a disposable worktree
- T-3108: TICK006 auto-recovery files duplicate tickets for citations of ids minted in sibling worktrees
- T-3109: refactor split/move: import-rewrite drops indentation on a nested (function-local/block) import
- T-3110: frob refactor verbs have no realistic corpus test: three independent defects shipped and were found by one real extraction
- T-3111: Move land's native rebuild after the landing commit, out of the dirty-root window
- T-3112: post-land sweep regression from an unattributed source (sweep spawned by T-3107): 20 new (rule, file) identit(ies), 38 finding(s) (AFFECT001, COV002, I001, SUPPRESS001)
- T-3113: frob ticket block is add-only: a mistaken blocked_by edge cannot be removed without hand-editing the ledger
- T-3114: Add resync_root_to_published_tip primitive for the post-CAS root resync
- T-3115: WIRE003 reports the working 'frob refactor' verb as unresolvable; the verb is also missing from frob --help
- T-3116: Land's ty gate refuses on pre-existing findings in touched files, manufacturing unrelated suppressions
- T-3119: frob refactor verbs' Verify phase never checks import breakage outside the plan's own touched files
- T-3120: TEST001 gap: Graph::has_cycle in strata-core/src/graph/query.rs has no unit test
- T-3121: Flip the squash-apply stage onto a disposable worktree and publish by CAS
- T-3122: frob refactor split moves symbol bodies without carrying their own needed imports
- T-3123: Stop FROB_WORKTREE leaking between tests in test_ticket_land.py
- T-3124: frob ticket new warns on scope overlap but never on duplicate titles or bodies
- T-3125: frob --help does not list refactor/narrative subcommands
- T-3126: Land-commit record still dirties root and moves main without CAS after the publish
- T-3128: fleet_status reports a live registered worktree as a leaked lease
- T-3129: Stale global frob reports the same version as the project build but has a different CLI surface
- T-3130: frob check cache.db/parse-artifacts.db: database is locked under concurrent checks
- T-3132: Pre-land lint gate (T-3061) attributes findings to the file, not the diff, same as T-1907's ty gate did
- T-3133: frob ticket evidence individual-reverify: run_selected path never applies fleet xdist bound
- T-3134: T-3121 landing-doc section still describes the post-publish land_commit record as an in-root commit
- T-3135: A persistent warm sweep stage is the only shape that can make the T-1514 unscoped sweep stage-capable
- T-3136: verify_pytest_collect passes non-Python touched files straight to pytest, false-refusing rc=4
- T-3137: frob ticket fail from a worktree never reaches main and does not say so
- T-3139: frob ops process reap and fleet_status disagree about orphaned forkservers; the reap verb is right
- T-3140: T-3034 residual: 10 test failures need deeper per-item investigation
- T-3141: T-3034 residual: close may no longer refuse unrelated evidence (D-02 regression?)
- T-3142: Break the 182-node import cycle (name the real next cut from the current cycle output)
- T-3143: refactor split leaves type-annotation-only import sites unrepointed
- T-3144: 5 real failures in test_ticket_land.py masked by the FROB_WORKTREE leak (T-3123)
- T-3145: new_ticket-calling test fixtures spuriously fail evidence reverification under an agent's own FROB_WORKTREE lease
- T-3147: Audit closes landed 2026-08-10..2026-08-27 for D-02 self-cover false positives (T-1944/T-3141)
- T-3148: _KNOWN_RULE_FIXABILITY literal missing SYS100 (T-3140 item 4)
- T-3149: WIRE001 false positive for CLI dest present in _config_external.py (T-3140 item 6)
- T-3151: frob-exports gap: ci_report/ci_validity/doctor/ghio/repo_meta/coverage_wait (T-3140 item 5)
- T-3152: fleet_status and frob.process._reap use different age heuristics for the same forkserver (mtime vs stat starttime)
- T-3154: post-land sweep regression from T-3145: 1 new (rule, file) identit(ies) (SEC110)
- T-3155: Extract evidence_covers_scope out of frob.gates to break the gates<->tickets edge
- T-3156: D-02 has no legitimate evidence route for docs-only bug-kind or Rust-only tickets
- T-3157: Ground-truth fixture suite for scripts/fleet_status.py
- T-3158: post-land sweep regression from T-3139: 2 new (rule, file) identit(ies), 1 finding(s) (DOC006, DRIFT001)
- T-3160: post-land sweep regression from an unattributed source (sweep spawned by T-3152): 1 new (rule, file) identit(ies), 1 finding(s) (missing-argument)
- T-3162: frob ticket reopen crashes mirroring to primary checkout (missing LEDGER_VERB_STRATEGY entry)
- T-3163: T-1036 ledger-splice regression under T-3121 disposable-stage: concurrent sibling write can silently drop the just-landed ticket's own record
- T-3172: post-land sweep regression from T-3156: 2 new (rule, file) identit(ies), 7 finding(s) (DRIFT001, SYS003)
- T-3174: T-2114 fork-based concurrent-writer sim spuriously skips lock contention once ledger_lock spans the fork point
- T-3176: Document T-3135 warm sweep stage and split _squash_apply_on_disposable_stage
- T-3177: Declare or waive SYS003 scripts_ops -> graphlang in branch_stranded_work_analysis.py
- T-3178: Refresh add_cmd_evidence kind-gate description in tickets-data-storage.md
- T-3179: Attribution engine records UNATTRIBUTED for findings with a directly findable cause (2 measured)
- T-3180: Scope-lease overlap check refuses provably-disjoint globs (literal accepted, wildcard refused)
- T-3181: Tracked agent scratch file emits a permanent REF001 ERROR in the repo error floor
- T-3191: Local gate typechecks only the host platform: Windows/macOS ty diagnostics are unreachable before CI
- T-3192: A hanging CI job produces no failure signal: turn ubuntu hangs into timed failures with stack dumps
- T-3195: A done-report recording zero evidence and zero changed files reached main while the work sat unlanded
- T-3196: post-land sweep regression from T-2710: 2 new (rule, file) identit(ies) (DRIFT001, SYS003)
- T-3211: Burn down platform-unsafe code surfaced by multi-platform ty (T-3191)
- T-3216: DirtyMain reports an unreadable git status as uncommitted work and tells the reader not to retry
- T-3218: Gate: refuse over-long ticket-citing comment blocks in src, and ticket ids outside docs provenance sections
- T-3219: post-land sweep regression from T-3195: 23 new (rule, file) identit(ies) (COV003, DOC007, DRIFT002, REF002)
- T-3220: frob clean --deep wholesale-deletes .frob/, which now also deletes rapid-debt.jsonl (T-2997)
- T-3222: Post-land sweep files findings that are 90% stale: 27 of 30 identities across two samples no longer reproduce
- T-3223: DOC006: dead path pointers in tickets/T-2962/ticket.md
- T-3224: REG005/REG008 findings on docs/design/registry/check-coverage.yaml
- T-3225: WAIVE006: AFFECT001 waiver on _rule_id_scan.py bound to closed ticket T-2993
- T-3227: post-land sweep regression from an unattributed source (sweep spawned by T-2878): 2 new (rule, file) identit(ies), 1 finding(s) (CLAUDE001, OPAQUE001)
- T-3228: LOUD gate failure for ratchet/deprecated-baseline lock producer abandonment
- T-3230: Audit failed-subprocess-folded-into-positive-finding sites (T-3216 sibling survey)
- T-3236: post-land sweep regression from T-2885: 1 new (rule, file) identit(ies) (OPAQUE001)
- T-3238: post-land sweep regression from T-3220: 1 new (rule, file) identit(ies), 2 finding(s) (DRIFT002)
- T-3243: post-land sweep regression from T-3228: 4 new (rule, file) identit(ies), 6 finding(s) (ARCH102, DEPR006, REG005, WAIVE011)
- T-3244: Burn down remaining platform-unsafe test-fixture code surfaced by multi-platform ty (T-3211 split)
- T-3246: SUITE-RESULT reports an ABORTED run (exitstatus=3) in the same shape as a completed one: failed=24 is a lower bound read as a count
- T-3247: Whole-repo-scan tests exceed the 120s per-test cap, killing the xdist worker and aborting the whole suite (root cause of the ubuntu hang)
- T-3249: Unowned 11-failure cluster: frob check fires spurious REF001/PRE001/SCOPE001 only under concurrent load (T-2992 misattributed it to the already-landed T-3019)
- T-3250: macOS CI hangs at 99% for 10m49s with ZERO diagnostics: T-3192 instrumented only ubuntu on a premise this run falsifies
- T-3251: Release can be dispatched from a red main: nothing gates the PyPI upload on green CI for the released commit
- T-3254: frob release check REFUSES 0.530.0 (BUMP REQUIRED, need >= 0.531.0): no documented release-cut procedure places the version bump
- T-3255: Fix malformed directive false-positive in docarch001_violations wiring comment
- T-3256: Six concurrent frob check runs drive the box to zero free memory: each sizes its pool against the whole machine, with no cross-process budget
- T-3257: AppConfig(command=...) unknown-argument ty finding, unrelated to platform work
- T-3263: render_lint_gate git-ls-files WARNING log line loses its level prefix under pytest
- T-3264: TestNativeMissingFailsLoud SYS004 test: unhandled NativeExtensionUnavailable crashes main instead of degrading to SYS004 finding
- T-3266: 136 done-reports claim '0 passed (from 0 evidence id(s))' while their ticket carries real evidence (T-3244 has 47)
- T-3268: frob perf spawns a hardcoded bare 'python' instead of sys.executable: wrong interpreter or outright SpawnFailed for real users
- T-3271: frob scaffold new writes into the output dir, not <output>/<name>: contradicts its own quickstart and scattered a project across a user's home
- T-3272: Ledger v2 must be the default for new repos: all six scaffold manifests still emit the v1 single-file tickets.md
- T-3273: frob.toml boilerplate: seven *_schema tables exist only to name frob's own internal constants, and omitting them silently reports UNMEASURED
- T-3276: Missing external tools degrade quietly instead of failing loud: no central resolution, doctor checks one binary, xdist absence unaccounted
- T-3277: A freshly scaffolded project fails its own make check with 16 errors: docs promise green immediately, nothing tests scaffold-then-check
- T-3283: 6 of T-3041's 13 live-repo self-conformance tests fail again: genuine post-close drift, not a stale claim
- T-3285: close-time disclosure check false-positives on split done-report.md
- T-3288: frob ticket land --finish DELETED a worktree without merging: the T-2108 shortcut trusts main's ledger state instead of branch ancestry
- T-3295: A waiver whose reason promises follow-up is debt, ticket or not: the discriminator already exists and WAIVE009 wires it to the wrong conclusion (2656 waive vs 124 debt)
- T-3303: frob ticket show auto-commits: NOT_TICKET_SCOPED verbs fall through to the generic commit path when ticket_id is set
- T-3305: _python_for_tree trusts a tree venv without checking frob is importable, breaking self-verification in every consumer repo
- T-3311: Collapse the three divergent external-tool spawn conventions into one resolution helper
- T-3316: warn_if_xdist_bound_missing does not detect the xdist plugin's absence, only an unset fleet bound
- T-3326: frob check --fix is repo-wide even from a targeted invocation, and a killed run leaves an unrecorded partial rewrite
- T-3341: fix FROB_VERBOSE env leak in TestVerboseFlag (test isolation)
- T-3342: Fix gate:DOC errors (DOC001-007 cluster)
- T-3344: Clear gate:DRIFT findings (53 errors) for release gate
- T-3346: Residual gate errors outside T-3342/3343/3344: ARCH/SEC/LARGE/PII/WIRE/PERF/LEXCHECK/WAIVE/FLAGCOV/DEPR (27)
- T-3347: Fix gate:COV errors: strata-core graph doc anchors, COV003 evidence kind, COV007 private-anchor placement
- T-3360: T-3266's stale-claims guard wrongly blocks reverify's own post-close evidence-add flow
- T-3361: fix stale mock signature in test_ticket_close_bug002_t1427
- T-3364: Fix gate:REG002/REF002 errors: register 3 missing gate rule ids, waive REF002 on 3 single-consumer support-module docs
- T-3374: T-3191's multi-platform ty union triples SUPPRESS001 findings for a cross-platform diagnostic
- T-3380: ruff format repo-wide sweep (81 files, no owning gate)
- T-3382: Fix gate:REG002 errors: register VERSION001/TDD001/VMOD001 as known gate rules
- T-3384: fix gate:DOC, gate:DRIFT, gate:SELFAUDIT residue (EO slice)

## [0.530.0] - unreleased

- T-2445: T-2445: every land writes CHANGELOG.md and the version line, so scope-disjoint lands still conflict
- T-2464: T-2464: Network dangerous-ops needles do not distinguish read vs write HTTP/DB verbs
- T-2466: T-2466: LEXCHECK001 scans only gates/ and only re.* calls, so it missed a substring-matching security detector in vet/

## [0.529.0] - unreleased

- T-2445: T-2445: every land writes CHANGELOG.md and the version line, so scope-disjoint lands still conflict
- T-2466: T-2466: LEXCHECK001 scans only gates/ and only re.* calls, so it missed a substring-matching security detector in vet/

## [0.528.0] - unreleased

- T-2445: T-2445: every land writes CHANGELOG.md and the version line, so scope-disjoint lands still conflict

## [0.527.0] - unreleased

- T-2448: Surface find_unregistered_rule_ids as a standing repo-wide frob check gate

## [0.526.0] - unreleased

- T-2435: T-2390 child: validate [gates] table (incl. [gates.ratchet]) against a declared schema

## [0.525.0] - unreleased

- T-2394: an empty ticket scope is only caught at land time

## [0.524.0] - unreleased

- T-2388: PORT001: meta-gate detecting gates that hardcode project identity instead of resolving it

## [0.523.0] - unreleased

- T-2443: frob check leaks multiprocessing forkservers: 94 orphans held 17GB of swap and stalled the fleet

## [0.522.0] - unreleased

- T-2407: Burn down the final 8 SYS003 findings (X -> cli coupling), then promote to error

## [0.521.0] - unreleased

- T-2434: T-2390 child: validate [[docblocks.commands]] table against a declared schema (incl. T-2397's config=/forwarded= keys)

## [0.520.0] - unreleased

- T-2433: T-2390 child: validate [arch] table against a declared schema

## [0.519.0] - unreleased

- T-2432: T-2390 child: validate [testing] table against a declared schema (already has TestPolicy model)

## [0.518.0] - unreleased

- T-2431: T-2390 child: validate top-level scalar keys (min_frob_version, check_base) against a declared schema

## [0.517.0] - unreleased

- T-2430: T-2390 child: validate [profile] table against a declared schema

## [0.516.0] - unreleased

- T-2400: TICK006 auto-files false phantom-citation tickets for ids that exist on main but postdate the worktree

## [0.515.0] - unreleased

- T-2406: deferred verification drains self-refuse and discard: 49% of post-land sweeps never run

## [0.514.0] - unreleased

- T-2429: T-2390 child: validate [[native]] table against a declared schema

## [0.513.0] - unreleased

- T-2403: Burn down the 133 genuine SYS003 findings post-calibration, then promote to error

## [0.512.0] - unreleased

- T-2428: T-2390 child: validate [[refs.entrypoint]] against a declared schema (58 leaves, largest table)

## [0.511.0] - unreleased

- T-2365: Adapter-capability axis + behavioral conformance suite for the 6 registered languages

## [0.510.0] - unreleased

- T-2397: Wire find_dropped_cli_flags into frob check as a gate (T-2387 visibility gap)

## [0.509.0] - unreleased

- T-2380: Decompose SYS003 (undeclared cross-component import) WARN campaign -- 4834 findings, 603 files

## [0.508.0] - unreleased

- T-2392: no CLI verb amends a ticket body, forcing agents to hand-edit the ledger

## [0.507.0] - unreleased

- T-2396: the shared-root write guard fires at commit time, after the damage is done

## [0.506.0] - unreleased

- T-2386: sync-skills: provenance-aware sync to stop cross-repo agents/skills deletion

## [0.505.0] - unreleased

- T-2360: Profile-collapse: build LandProfileSettings resolver for the 5 remaining if-rapid branches

## [0.504.0] - unreleased

- T-2358: Three live import cycles in src/frob (deploy, vet, serve/stats), invisible to accounting because the cycle gate emits identity-less findings

## [0.503.0] - unreleased

- T-2353: priority/kind/component/tier mutations have no --reason audit trail

## [0.502.0] - unreleased

- T-2355: Ledger v2 migration: build the golden round-trip test and migrate the 108 legacy-only tickets

## [0.501.0] - unreleased

- T-2352: sweep auto-filer must relativize absolute finding paths into scope: (T-2342 producer-side half, deferred behind T-2313's lease)

## [0.500.0] - unreleased

- T-2351: frob ticket land's pre-land WIP-commit path silently discards uncommitted in-scope edits (T-2328 follow-up, narrower root cause)

## [0.499.0] - unreleased

- T-2344: meta-check: a gate rule constructed from raw text without symref/AST binding must itself be a finding

## [0.498.0] - unreleased

- T-2333: Persist frob worktree release-lease --force's reason on the ticket ledger, not just the WARNING log

## [0.497.0] - unreleased

- T-2320: frob quality check: split ruff-check/ruff-format skip flags + add a real ruff-autofix/format write mode

## [0.496.0] - unreleased

- T-1777: Wire frob.tickets._leases.force_release_lease into a CLI verb

## [0.495.0] - unreleased

- T-2126: Consider surfacing verify queue depth/age in fleet_status.py, symmetric to T-2049's quarantine line

## [0.494.0] - unreleased

- T-2310: rapid profile needs a real verification-debt drain mechanism (design decision deferred from T-2290)

## [0.493.0] - unreleased

- T-2298: frob fmt with a broad path rewrote 49 unrelated .strata fixture files; a test-input corpus must not be reformattable by an unscoped fmt

## [0.492.0] - unreleased

- T-2290: rapid profile defers verification with no drain: watermark 6 days and 403 commits stale, and reported unverified depth (84) understates it ~5x

## [0.491.0] - unreleased

- T-2068: xdist retry serial fix does not neutralise pyproject addopts -n auto

## [0.490.0] - unreleased

- T-2291: reconcile --apply writes ledger demotions before its LandInProgress guard refuses, stranding them uncommitted and DirtyMain-blocking every agent land

## [0.489.0] - unreleased

- T-1783: New rule: every top-level CLI verb needs a dedicated doc section, not just a table row

## [0.488.0] - unreleased

- T-2282: Agents strand themselves ending a turn with a pending background task: the guard enumerates slow commands instead of catching the stranding (3 stalls this session)

## [0.487.0] - unreleased

- T-2284: Land's Tier-A auto-fix edits files outside the landing ticket's scope (and under other tickets' live leases), forcing CrossTicketLeakage refusals and manual reverts

## [0.486.0] - unreleased

- T-2261: Nothing ever invokes frob worktree sweep: 107 worktrees / 67GB / 95 idle accumulated, and the land prints 'run it later' instead of acting

## [0.485.0] - unreleased

- T-2281: fleet_status scope-collision check misses tickets whose land is in flight (in-progress + no lease is not a lease-recording bug)

## [0.484.0] - unreleased

- T-2236: Documented invocation of coordinator scripts (bare python3) violates requires-python >=3.11, and the failure is a raw ImportError -- broke fleet_status the minute a legal 3.11 feature landed

## [0.483.0] - unreleased

- T-2249: fleet_status's concurrency guidance keys on MEM available, which read 11.5GB healthy while the machine was already swapping 6GB with 0 free RAM

## [0.482.0] - unreleased

- T-2231: Break gates/lang/graph import cycle: _docblocks<->_docblocks_refs split plus lang<->graph.cache lazy-break not recognized by static cycle check

## [0.481.0] - unreleased

- T-2242: Add frob release publish subcommand; retire Makefile upload bash recipe

## [0.480.0] - unreleased

- T-2254: T-2226's attachment backfill has no CLI entry point: the repair is unreachable and 2 COV004 findings remain, now that T-2239 removed the CRLF blocker

## [0.479.0] - unreleased

- T-2220: A landed ticket does not record its own land commit, so verify_lands.py cannot be addressed by ticket id (--plan lands unreachable)

## [0.478.0] - unreleased

- T-2248: frob-timeout-guard misses ticket work and ticket new: both auto-backgrounded today, one stalled an agent, one risked a duplicate id allocation

## [0.477.0] - unreleased

- T-2241: Add frob sync-skills subcommand; retire Makefile bash bidirectional sync loop

## [0.476.0] - unreleased

- T-2225: fleet_status --ticket reports dispatchable=True when the ticket's SCOPE FILES are held by another agent's live lease (two mis-dispatches measured)

## [0.475.0] - unreleased

- T-2226: T-2199 residue: tickets promoted before the fix still record dead T-draft-* attachment paths, and no repair path exists (6 of 41 floor errors)

## [0.474.0] - unreleased

- T-2222: fleet_status reports a raw lease COUNT with concurrency guidance attached, so reclaimable and root-residual leases read as live agents (6 leases = 4 agents)

## [0.473.0] - unreleased

- T-2224: Via-less grants on fail-closed capability kinds (exec/eval/install-hook/ffi) are WARN-only, never enforced

## [0.472.0] - unreleased

- T-2221: Every agent's pytest claims the whole machine: -n auto oversubscribes ~4x under a multi-agent fleet (load 28 on 12 CPUs)

## [0.471.0] - unreleased

- T-2207: A malformed empty-identity finding makes quarantine PERMANENTLY unclearable: dispose rejects it as malformed while clearing requires every finding disposed, so deferred landing stays off fleet-wide with no recovery path

## [0.470.0] - unreleased

- T-2193: Evidence discipline only proves the bug existed, never that the fix kept the capability: --check-repro verifies a test FAILED at parent, so a fix that disables the feature entirely passes every gate

## [0.469.0] - unreleased

- T-2182: Ticket rot is measured by TICK004 in the gates layer but never surfaced where dispatch happens, so 15 tickets aged past threshold (3 critical, up to 20d) while every wave picked freshly-filed work

## [0.468.0] - unreleased

- T-2188: callgraph.py's build_call_graph/build_reference_graph/build_ordered_call_graph resolve cross-file private candidates by bare short name, unverified against imports -- same T-2156 mechanism, three unfixed consumers (COV006, DEAD001, PROTO001-005)

## [0.467.0] - unreleased

- T-2191: REDUNDANT_RERUN asserts 'this run could not have produced a different result' from the repo tree hash alone, but verbs like claude sync --check read state outside the repo and legitimately change verdict

## [0.466.0] - unreleased

- T-2181: T-2179 residue: 'already implemented' still decides from scope-file overlap, so any branch that touched a shared file claims someone else's ticket -- t-2107 and t2049-series falsely claim T-2114

## [0.465.0] - unreleased

- T-2179: fleet_status.py::worktrees_touching_ticket reports ledger-only churn as 'already implemented' (T-2172 follow-up)

## [0.464.0] - unreleased

- T-2156: Sweep finding identities carry ABSOLUTE paths so commit attribution always fails, every finding reads unattributed, and that raises the quarantine which switches deferred landing off fleet-wide

## [0.463.0] - unreleased

- T-2157: A land killed by its shell timeout leaves its staged merge in the shared root index, DirtyMain-blocking every other agent until someone lands or clears it by hand

## [0.462.0] - unreleased

- T-2129: LAND-PROOF reports verified=SKIPPED-UNMEASURED/ERROR for a successful QUEUED-with-failure-log land (is_ancestor_of_main=True contradicts its own ERROR)

## [0.461.0] - unreleased

- T-2049: A raised quarantine silently forces synchronous verification on every land and is surfaced nowhere an operator looks -- two unused imports cost an hour of fleet land throughput

## [0.460.0] - unreleased

- T-1782: New rule: every FROB_* env var needs a doc anchor or an explicit waiver

## [0.459.0] - unreleased

- T-1784: New rule: flag repo-root asset directories with zero code references

## [0.458.0] - unreleased

- T-2105: Detect a duplicate ticket id after a merge silently resolves two records (T-2092 half 2)

## [0.457.0] - unreleased

- T-2107: argparse suggests flags from a different subparser: 'unrecognized arguments: --set X (did you mean: --set?)' names a flag the invoked subcommand does not have

## [0.456.0] - unreleased

- T-2079: Ledger ownership: refuse a main-side write to a leased tickets/T-#### path

## [0.455.0] - unreleased

- T-2090: Evidence collection discards the missing_natives it already computed, so a fresh worktree reports UnknownEvidence and advises deleting the cache instead of building natives

## [0.454.0] - unreleased

- T-2084: Ticket-state palette: dropped and queued are both DIM, so terminal work is indistinguishable from waiting work

## [0.453.0] - unreleased

- T-2023: T-1961s land-wait timeout is calibrated below the observed land duration, so ledger verbs now cost 60s and refuse anyway

## [0.452.0] - unreleased

- T-1584: Wire frob profile CLI (show/downgrade) to frob.tickets._profile

## [0.451.0] - unreleased

- T-2018: Symbolic attribution exists but is invisible where findings are reported, so agents attribute floor errors by unsound git-diff guessing

## [0.450.0] - unreleased

- T-2006: T-1983's auto-drop only runs inside the next sweep, so a stale sweep ticket stays dispatchable until an unrelated land happens

## [0.449.0] - unreleased

- T-1939: No rule-level telemetry: cannot measure which of 293 gate rules ever fire

## [0.448.0] - unreleased

- T-1961: Ledger verbs refuse with LandInProgress instead of waiting: hit 4x in one hour, forces hand-rolled retry loops

## [0.447.0] - unreleased

- T-2004: A CLI flag can be parsed, tested, and silently dropped by from_external's allowlist: tested is not reached

## [0.446.0] - unreleased

- T-2005: BUG002 repro-check silently drops its own PYTHONPATH override, so it verifies against the wrong source

## [0.445.0] - unreleased

- T-1927: design a population/date-projected capacity evaluator for frob sys capacity

## [0.444.0] - unreleased

- T-1925: design a ThreatViolation-to-boundary join for a boundary-scoped frob sys threats

## [0.443.0] - unreleased

- T-2001: Tier-A auto-fixes design/frob.strata but not the capability ratchet lock, so half the obligation self-heals and the breach surfaces on an unrelated later land

## [0.442.0] - unreleased

- T-1999: Land-path guards decide ticket liveness from main's IN_PROGRESS state, not the live lease, so a started-but-unsynced worktree's files land unguarded

## [0.441.0] - unreleased

- T-1995: frob ticket new does not surface existing or archived coverage: 7 tickets filed and dropped this session, several costing a dispatch

## [0.440.0] - unreleased

- T-1981: Burn down SYS110_UNAUDITED_NODES: T-1629's rule enforces on 2 of 17 nodes until the 15 exempted mirrors are hand-audited

## [0.439.0] - unreleased

- T-1968: frob:waive in markdown is silently ignored: waivers written by a burn-down suppress nothing and nothing says so

## [0.438.0] - unreleased

- T-1970: No way to mention a frob directive without using it: prose blocked two lands, and no escape syntax exists

## [0.437.0] - unreleased

- T-1985: build a file-level resolved-import edge substrate in frob.graph (prerequisite for T-1665)

## [0.436.0] - unreleased

- T-1974: Adding one gate rule id needs three hand edits and none is checked before the land: DOCENUM001+REG010 regressed the floor twice

## [0.435.0] - unreleased

- T-1628: strata: capability via lists only ever grow -- add a one-way ratchet

## [0.434.0] - unreleased

- T-1944: Scope conflates evidence coverage with write lease: citing an existing test permanently leases its whole file

## [0.433.0] - unreleased

- T-1629: strata: interface= should declare INTENDED surface, not mirror every public symbol

## [0.432.0] - unreleased

- T-1958: DOCENUM001: docs/modules/gates.md#rule-catalog stale after T-1937's 8 new rule ids

## [0.431.0] - unreleased

- T-1938: 21 byte-identical copies of the RELWAIVE002 stale-waiver block across strata (DUP001 type-name blind spot)

## [0.430.0] - unreleased

- T-1937: Gate rule registry is not authoritative: 10 live rule ids bypass the acceptance preflight

## [0.429.0] - unreleased

- T-1808: Fold Claude-config sync (sync-claude-config.py) into a real frob verb

## [0.428.0] - unreleased

- T-1921: Per-site analysis-coverage substrate for WAIVE004 escape (T-1904 successor)

## [0.427.0] - unreleased

- T-1929: Confirmatory-only evidence is only detectable at land: --designate-repro validates nothing and BUG002 has no on-demand path

## [0.426.0] - unreleased

- T-1924: Finish T-1911's Tier-A snapshot-param drop on the 5 handlers in _fix_engine_sync.py

## [0.425.0] - unreleased

- T-1556: cli hygiene remainder: warning collapse, read-only check --ticket, close porcelain, cli-hygiene principles doc (T-1271 split)

## [0.424.0] - unreleased

- T-1911: Tier-A handler dispatch signature is stricter than any handler needs, so new tests reach for None and re-trip invalid-argument-type

## [0.423.0] - unreleased

- T-1916: REG002 red on main: CHK-GATE-SYS-IFACE-ORDER claims an enforced gate rule, but SYS-IFACE-ORDER is only a Tier-A auto-fix handler

## [0.422.0] - unreleased

- T-1891: frob ticket new prints a DirtyMain --no-commit warning even when it DID commit the ledger

## [0.421.0] - unreleased

- T-1867: Wire frob ticket anchor CLI + doable-output disclosure (T-1856 follow-up)

## [0.420.0] - unreleased

- T-1882: frob ticket renumber with no arguments silently renumbers EVERY ticket, destroying the whole id space

## [0.419.0] - unreleased

- T-1893: Document T-1886 WAIVE004 proportional-check sample-size floor in gates.md

## [0.418.0] - unreleased

- T-1872: Tier-A canonical ordering for interface= : group by resolved symbol kind, alphabetical within group, order-only

## [0.417.0] - unreleased

- T-1880: frob ticket start grants a lease without checking cross-ticket scope collision at grant time

## [0.416.0] - unreleased

- T-1870: Delete frob sys sync-interface: interface= must be declared intent, not an auto-measured mirror nothing reads

## [0.415.0] - unreleased

- T-1648: A ticket can close with disclosed unfinished work and no follow-up, silently dropping it

## [0.414.0] - unreleased

- T-1850: post-land sweep regression from T-1545: 2 new error(s) (invalid-argument-type, invalid-type-form)

## [0.413.0] - unreleased

- T-1856: First-class anchor marker for permanent-waiver-target tickets

## [0.412.0] - unreleased

- T-1689: Batch test selection: run a batch's union touched-set in one pytest process

## [0.411.0] - unreleased

- T-1843: wire find_policy_weakenings (INV-051) into a frob check gate over design/ policies

## [0.410.0] - unreleased

- T-1695: Verify-worker resource budget: never starve foreground agents

## [0.409.0] - unreleased

- T-1842: post-land sweep regression from T-1787: 1 new error(s) (DOCENUM001)

## [0.408.0] - unreleased

- T-1836: SCOPE001 fires on every ticket's own tickets/T-XXXX/ticket.md (stale LEDGER_PATH)

## [0.407.0] - unreleased

- T-1853: An anchor ticket cited by a permanent waiver can never land ANY ledger record, not just close

## [0.406.0] - unreleased

- T-1838: frob:waive comments in .claude/hooks/** never take effect (BUILTIN_SKIP_DIRS prunes .claude from frob.graph's walk)

## [0.405.0] - unreleased

- T-1848: FEATURE-kind tickets implicitly lease all of ticket_runner/**, blocking unrelated agents; scope --remove cannot narrow it

## [0.404.0] - unreleased

- T-1749: frob ticket evidence --designate-repro is a second silent BUG002-check-redirect asymmetry

## [0.403.0] - unreleased

- T-1545: Tier-A auto-fix: SYS100 EXTENDED-kind capability declaration (eval/process-control/ffi/...)

## [0.402.0] - unreleased

- T-1697: frob verify: surface the unverified window -- depth, age, quarantine, attribution

## [0.401.0] - unreleased

- T-1482: build policy refinement-monotonicity diff pass (INV-030)

## [0.400.0] - unreleased

- T-1819: SCOPE001 false-positives on a ticket's own tickets/<id>/** shard file (LEDGER_PATH predates sharded ledger)

## [0.399.0] - unreleased

- T-1572: frob coverage: add --base override, thread through make coverage-fast BASE=

## [0.398.0] - unreleased

- T-1264: gates --fix fixability registry field: generated-verified auto/verified/assisted/manual tier per rule id

## [0.397.0] - unreleased

- T-1366: CI still cannot verify the .frob/-local coverage stamp and delta baseline (T-1265 successor)

## [0.396.0] - unreleased

- T-1569: cli regrouping: frob ops verb group (release/natives/doctor/clean/fleet/deploy/scaffold/gitlog/stats)

## [0.395.0] - unreleased

- T-1738: frob ticket wave: partition the doable set into N mutually scope-disjoint groups for parallel dispatch

## [0.394.0] - unreleased

- T-1568: cli regrouping: frob design verb group (sys/registry/docs/graph/exports)

## [0.393.0] - unreleased

- T-1466: extend T-1433 SIGUSR1 stack-dump handler beyond pytest-only scope

## [0.392.0] - unreleased

- T-1744: Detect a queued ticket whose described fix already landed outside the ticket workflow (false queue signal)

## [0.391.0] - unreleased

- T-1567: cli regrouping: frob quality verb group (check/test/dup/arch/bind/cycle/mutate/perf)

## [0.390.0] - unreleased

- T-1643: Wire a real Tier-B --fix handler (T-1262 shipped only the synthetic TIERBDEMO001 reference handler)

## [0.389.0] - unreleased

- T-1746: Implement real fix for WIRE001 same-file test-fixture reuse false positive

## [0.388.0] - unreleased

- T-1328: strata: build an independent second detector for app-level capability kinds (eval/env/ffi/install-hook/sql/deserialize/fetch_url)

## [0.387.0] - unreleased

- T-1719: Fold Claude-config sync into a frob verb, gate the drift, and report global-vs-local frob skew in doctor

## [0.386.0] - unreleased

- T-1806: Generalize lease staleness: path-gone, ticket-gone, and holder-dead are all the same check

## [0.385.0] - unreleased

- T-1479: wire remaining daemon-proxy subcommands named by T-0321's integration map

## [0.384.0] - unreleased

- T-1505: vet/resolvers: close remaining 3 structural points-to gaps (rust macro_rules, cpp ptr-to-member, kotlin operator-invoke) -- T-1063 residue

## [0.383.0] - unreleased

- T-1544: Tier-A auto-fix: TICK006 phantom draft citation refile+renumber

## [0.382.0] - unreleased

- T-1758: T-1615's uniform ledger auto-commit does not cover programmatic (non-CLI) callers of new_ticket/write_ticket

## [0.381.0] - unreleased

- T-1790: Refuse (or warn on) creating a nested agent worktree under another worktree (T-1779 finding 7, source)

## [0.380.0] - unreleased

- T-1620: Degraded-run detection misses zero-findings under-reports and sub-threshold mass staleness

## [0.379.0] - unreleased

- T-1693: Quarantine circuit breaker: a red batch stops further deferred lands until attributed

## [0.378.0] - unreleased

- T-1789: Orphaned-lease detection gate + targeted lease-release verb (T-1779 finding 7)

## [0.377.0] - unreleased

- T-1222: rust: arch python metrics single-pass walk export (extraction only, rules stay Python)

## [0.376.0] - unreleased

- T-1724: Measure dispatch cost against tickets landed: join agent telemetry to a dispatch record in frob stats --agentic

## [0.375.0] - unreleased

- T-1779: Nothing guards the root checkout against a coordinator writing during a land: five stalls and one corrupted ticket state

## [0.374.0] - unreleased

- T-1221: rust: capability-scan resolver in frob_core -- import table + alias propagation + candidate resolution

## [0.373.0] - unreleased

- T-1768: frob release stamp --allow-unbumped silently rebaselines the REL001 manifest with no reason and no audit record

## [0.372.0] - unreleased

- T-1613: frob cannot express runs-last: add a marker that stays undoable while any other ticket is open

## [0.371.0] - unreleased

- T-1743: doable --show-blocked names the wrong ticket as lease holder, and an orphaned lease has no supported release path

## [0.370.0] - unreleased

- T-1220: rust: tree-extraction kernel -- source bytes to symbols/spans/tokens/identifiers/comment+docstring spans/import specs

## [0.369.0] - unreleased

- T-1763: INV006/AFFECT001/DUP001 have a 100% waive rate: 406 waivers, zero findings -- make them symbolic or delete them

## [0.368.0] - unreleased

- T-1762: Every --force override discharges a safety obligation with no reason and no audit trail; audit the whole flag family

## [0.367.0] - unreleased

- T-1760/T-1317/T-1627: release-artifact recompute, ack accountability, symbol-form via

## [0.366.0] - unreleased

- T-1692/T-1755/T-1756: backpressure, sweep self-commit, lint fixes

## [0.365.0] - unreleased

- T-1733: Weakening a ticket's evidence is silent and free, while the honest escape hatch is logged and justified

## [0.364.0] - unreleased

- T-1715: frob ticket land --finish deletes the calling agent's own worktree cwd, stranding it with no recovery

## [0.363.0] - unreleased

- T-1615: frob ticket block leaves the ledger dirty: audit every ledger-writing verb for auto-commit parity

## [0.362.0] - unreleased

- T-1727: Close-time mutation-evidence sweep has no budget: 10 consecutive 540s timeouts, and its cost structure rewards binding weak evidence

## [0.361.0] - unreleased

- T-1688: Coalescing verify worker: drain the queue to its tip, verify once, advance the watermark

## [0.360.0] - unreleased

- T-1700: TICK006 fires on a Done report DISCUSSING a code-spanned ticket id; reuse DOC011's code-span stripping

## [0.359.0] - unreleased

- T-1670: frob ticket evidence: designate repro test explicitly + validate node-id shape at bind time

## [0.358.0] - unreleased

- T-1675: already-landed detection is opt-in because it cannot tell 'no diff' from 'docs-only ticket'

## [0.357.0] - unreleased

- T-1558: WIRE001 module-local test-helper false-positive class: teach the gate or wire the helpers (T-1490/T-1488 successor, waiver home)

## [0.356.0] - unreleased


## [0.355.0] - unreleased

- T-1663: Classify every gate rule: semantic, legitimately lexical, or lexical-and-wrong

## [0.354.0] - unreleased

- T-1637: Manual draft refile silently discards evidence and Done reports; renumber already exists and is undocumented

## [0.353.0] - unreleased

- T-1619: Land has no exclusive lease: a concurrent frob ticket new corrupts it mid-staging

## [0.352.0] - unreleased

- T-1624: strata: sync-interface appends duplicate attr interface blocks instead of replacing

## [0.351.0] - unreleased

- T-1646: LARGE001 remainder: 52 oversized files T-1420 disclosed but did not attempt

## [0.350.0] - unreleased

- T-1420: arch: 51-file LARGE001 residue after T-1270's 2-file split

## [0.349.0] - unreleased

- T-1588: ledger v2 has no stale-snapshot guard: write_archive/write_all expected_digest is a v1-only primitive

## [0.348.0] - unreleased

- T-1590: suite red: extending-guides drift, exports residue, unregistered gate rule literal

## [0.347.0] - unreleased

- T-1581: COV002 Tier-A insertion handler must use the target file's comment leader

## [0.346.0] - unreleased

- T-1279: TEST005 burn-down: src/frob/gates (179 findings, 12 at 0.0%)

## [0.345.0] - unreleased

- T-1575: Development profiles: frob.toml profile=rapid|standard|fortress with one-way auto-ratchet

## [0.344.0] - unreleased

- T-1518: move TEST016 mutation evidence off the per-land critical path: batch/nightly cadence, land-blocking only for security-kind

## [0.343.0] - unreleased

- T-1547: Tier-A auto-fix: E501 introduced by merge, targeted ruff-format

## [0.342.0] - unreleased

- T-1492: ledger v2: wire migrate --to v2 CLI flag onto migrate_v1_to_v2

## [0.341.0] - unreleased

- T-1525: coverage: user-facing frob coverage CLI verb + decide frob check auto-trigger for non-agent callers

## [0.340.0] - unreleased

- T-1271: cli hygiene: no hidden-argument hell, maximally informative output, mined from real agent usage

## [0.339.0] - unreleased

- T-1555: type-debt pass: clear all ty diagnostics (incl. signature drift in landed land-machinery) + ruff format/check backlog

## [0.338.0] - unreleased

- T-1445: Extend gate-result cache to root-scanning process-pool gates + add --no-cache CLI flag

## [0.337.0] - unreleased

- T-1531: auto-repair the recurring land-refusal classes via Tier-A/B fix handlers (strata declarations, ticket edges, report refresh, draft renumber)

## [0.336.0] - unreleased

- T-1536: ledger self-corruption: done-report section replacement can duplicate a foreign ticket block and break whole-store YAML load

## [0.335.0] - unreleased

- T-1318: perf: telemetry redact_command pulls in the whole frob.gates package via frob.gates._secrets

## [0.334.0] - unreleased

- T-1520: CACHE001 static gate: a cached computation's observed read-set must be covered by its cache-key inputs

## [0.333.0] - unreleased

- T-1517: coverage: per-file content-hash incremental caching layer

## [0.332.0] - unreleased

- T-1514: run the unscoped error sweep pre-land on a merge-preview worktree instead of post-land on mutated main

## [0.331.0] - unreleased

- T-1470: TEST005 strata sweep: _native_test.py at 30% branch coverage, below floor

## [0.330.0] - unreleased

- T-1198: strata: eliminate attr interface= boilerplate (4236 of 5588 frob.strata lines) via generated fragment or compact grammar

## [0.329.0] - unreleased

- T-1439: Reclassify process-control registry entries (signal.signal, sys.exit/os._exit) out of capability kind env

## [0.328.0] - unreleased

- T-1201: refactor: split verb (built on T-1072/T-1077 family-extraction pattern)

## [0.327.0] - unreleased

- T-1223: rust(interim): tree-sitter Query captures for comment/docstring spans shared by sys+opaque+vet

## [0.326.0] - unreleased

- T-1218: doctor: stale-global-frob self-check -- invoked version vs repo floor

## [0.325.0] - unreleased

- T-1500: arch: LARGE001 split of vet _capability TS/rust/C/kotlin families + tail (T-1420 delivered portion 7)

## [0.324.0] - unreleased

- T-1464: perf: persist parse-artifact cache across process-pool gate workers (correctly scoped)

## [0.323.0] - unreleased

- T-1259: ledger v2: migration (frob ticket migrate --to v2, golden round-trip, deprecation gate, final cutover)

## [0.322.0] - unreleased

- T-1262: gates --fix Tier-B transaction engine: apply-verify-rollback per fix

## [0.321.0] - unreleased

- T-1269: ticket land --plan: atomic design-phase land with automatic draft finalization

## [0.320.0] - unreleased

- T-1267: refactor: prose/doc-anchor carrier (docstring, docs/**, anchor-slug rewrite)

## [0.319.0] - unreleased

- T-1231: doclink basename+fragment validation -- resolve relative link targets and #fragment anchors

## [0.318.0] - unreleased

- T-1484: WAVE14-B: drain TICK warning class (scope-breadth ack mechanism + TICK004/TICK003 cleanup)

## [0.317.0] - unreleased

- T-1450: strata: SYS101 staleness judged per may-via surface, not whole-node kind

## [0.316.0] - unreleased

- T-1229: negative-existence claims -- bind absence-claims to a ticket via frob:until, flag unbound ones

## [0.315.0] - unreleased

- T-1360: Footgun detection: warn when a command failed or under-reported in a way that looks like success

## [0.314.0] - unreleased

- T-1454: T-1346 gate cache serves stale DRIFT001 result across a frob ack boundary

## [0.313.0] - unreleased

- T-1458: arch: LARGE001 split of tickets _new_renumber v2 backend (T-1420 delivered portion 4)

## [0.312.0] - unreleased

- T-1440: strata: scoped may clauses -- a capability grant must name its surface, not bless the whole node

## [0.311.0] - unreleased

- T-1446: T-1420 delivered portion 3

## [0.310.0] - unreleased

- T-1346: Memoize gate results on content digests

## [0.309.0] - unreleased

- T-1442: T-1420 delivered portion 2

## [0.308.0] - unreleased

- T-1441: arch: LARGE001 splits of gates _sys and _dead_symbols (T-1420 delivered portion 1)

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
  docs/**.md; markdown-side `<!-- frob:waive INV003|INV004 reason="..." -->`
  support lets a genuine-but-unprovable claim be dispositioned honestly.
  INV003+INV004 combined warnings: 765 -> 604.

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
