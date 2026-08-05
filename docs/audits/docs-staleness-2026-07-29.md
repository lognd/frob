# Docs staleness audit -- 2026-07-29

Status: 2026-08-05

Point-in-time audit snapshot. Denominator: 121 docs (docs/** plus
README.md, CLAUDE.md, FROBLEMS.md, CHANGELOG.md), all 121 claim-verified
by a four-pass exhaustive sweep. Baseline: the doc-family gates
(docanchor/docblocks/doclink/drift/refs/coverage) flagged exactly 2 of
the findings below (class A); every other finding is class B -- a silent
miss no gate fired on. The gate-gap classes at the bottom are the
mechanism work; the per-doc findings are the fix campaign's worklist.
Remediation tickets: see the docs-integrity epic filed 2026-07-29.

## Class A (already gate-flagged)

- docs/modules/arch.md:1825 frob.gates._dup_config unresolved (DOC006);
  moved by T-1174 to src/frob/gates/_dup.py:32.
- docs/modules/testing.md:526 unbound code block (DOC004).
- docs/guides/install.md:494,525,564 DOC004 x3 unbound code blocks.

## Class B confirmed-stale findings

### Operationally breaking

- docs/guides/agent-playbook.md:394-399 stamp-baseline recipe omits
  ffi_boundary from the gates-fast list (src/frob/check/__init__.py:271,
  T-1012), so agents following it never stamp the baseline.
- docs/guides/agent-playbook.md:135-139 claimed shared CARGO_TARGET_DIR
  was unbuilt; T-0732 landed it (Makefile:197, ~11s warm).

### Enumeration drift (prose copy of a code collection)

- docs/commands/check.md:132,159 gates-native omits exhaustive_handling
  (src/frob/check/__init__.py:321).
- docs/commands/check.md:133,160 gates-security lists 4 of 6 members
  (missing protocol_summary, opaque; __init__.py:323-333).
- docs/commands/cycle.md:8 --lang omits c (_cli_parsers/_core.py:76);
  same at docs/commands/xref.md:8 (_core.py:138).
- docs/commands/parse.md:24-34 tool table omits tsc, eslint
  (_core.py:149-165).
- docs/commands/gitlog.md:27 full-type list omits style, revert
  (src/frob/gitlog/__init__.py:23).
- docs/commands/map.md:9, outline.md:9 usage omits --all.
- docs/design/coding-performance-corpus.md:16,24-28 says PERF001-004;
  actual PERF001-008 + PERF012 (src/frob/perf/_rules.py).
- docs/guides/extending/comment-dsl-directives.md:9-11 lists 13 of 20
  verbs (src/frob/graph/dsl.py:21); :147-148 tests kinds omit property
  (dsl.py:71).
- docs/guides/extending/capability-registry.md:11 LANGUAGES omits kotlin
  (src/frob/vet/_capability_registry.py:51); :22-24,:73-78 c-cpp excused
  kinds wrong (10 actual, install-hook not among them; :1695ff).
- docs/guides/extending/ticket-kinds-states.md:7 "three StrEnum
  registries" -- 8 exist (src/frob/tickets/_models.py); :9-11 TicketKind
  missing EPIC/STORY/TICKET (10 members).
- docs/guides/extending/scenario-kinds.md:10-11 Rewrite union missing
  AddFlow (src/frob/strata/_models.py:530).
- docs/guides/extending/prover-claim-kinds.md:9-10 claim-variant list
  wrong: ClaimBody = NoFlow|Reach|BoundClaim|Independent|SetEquality
  (_models.py:452); Metric/Quantity are not variants.
- docs/guides/extending/language-grammar-handlers.md:7,11-14,72,79
  "five languages", walker list omits _walk_kotlin.py (7 keys,
  src/frob/lang/_extract.py:60); :11 _walk_tsx aliases
  _walk_typescript, not _walk_c (:55-57).
- docs/guides/extending/gate-rule-families.md:7-9 names 22 families;
  _KNOWN_GATE_RULES spans ~50 prefixes (src/frob/gates/_waive.py:140).
- docs/guides/extending/README.md:36 THREAT001-005 (THREAT006 exists,
  src/frob/strata/_threat.py:1552); :52 DUP001/002 (DUP003 exists,
  src/frob/gates/_dup.py:96).
- docs/guides/extending/dup-detector-registry.md:17-18 "two PURE rules"
  (DUP003 landed, T-1174); :29,:73 _pipeline.py is now a package.
- docs/guides/editors.md:20-22 declaration keywords miss resource
  (T-0700; strata-core/src/parse/grammar_policy.rs:333ff).
- docs/guides/extending/strata-surface-grammar.md:9-11 keyword list
  wrong (claim/deploy/managed/abstract/observe not top-level keywords).
- docs/index.md:88-89 PERF001..004 (see above); :96-97 "five languages";
  :166 SYS100-102 (SYS100-106 live).
- docs/design/system-performance-corpus.md:17-18,810-811 perf package
  "five files" -- 18 modules.
- docs/modules/arch.md:19-48 checks table ~30 of 58 ArchCategory
  members (src/frob/arch/_models.py:11-206); :1769 "six rows"; :1770
  ArchSeverity omits error (:221).
- docs/modules/app.md:128-206 runners catalog 22 of 36 *_runner modules.
- docs/modules/bind.md:16 omits --list-sources (_core.py:413-418).
- docs/modules/clean.md:26-30 tier-2 omits **/CMakeFiles,
  **/CMakeCache.txt (src/frob/clean/_rules.py:42-43).
- docs/modules/dup.md:285-289 DupError 4 of 7 members
  (src/frob/dup/_models.py:41-47); :699 phantom --all/--base flags.
- docs/modules/graph.md:498-500,537-540 EdgeKind "closed set of 9" --
  21 members (src/frob/graph/_models.py:88-149); :416-430 DSL verb
  table omits 9 verbs; :607-610 LangError 3 of 6; :683 "schema 2" --
  _SCHEMA_VERSION = 3 (src/frob/graph/cache.py:61).
- docs/modules/lang.md:3-5,11 "five grammars" -- 7 registered incl
  kotlin+strata (src/frob/lang/__init__.py:94-134); :16-23 extension
  table omits .cxx/.kt/.kts/.strata; :73-89 5-language-only tables.
- docs/modules/mutate.md:42 MutateError 2 of 4 members
  (src/frob/mutate/__init__.py:67-80).
- docs/modules/perf.md:874-877 PerfError 3 of 4; :834-835 PERF001..007
  (see rules above).
- docs/modules/testing.md:563-570 TestingError 6 of 7 (missing
  NativeAuditFailed; src/frob/testing/_runners.py:65-86).
- docs/modules/vet.md:53-54,:280 lockfile list wrong (only uv.lock,
  package-lock.json, pnpm-lock.yaml, Cargo.lock;
  src/frob/vet/_lockfile.py:1-27); :26-38 capability table omits 7
  kinds; :992-996 VetError missing CveMirrorInvalid; :1022 scan_tree
  omits timeout/jobs (src/frob/vet/_scan.py:833-839); VET007-VET010
  meanings predate T-1088 renumbering (src/frob/vet/_supplychain.py).
- docs/strata/waive.md:48-51 waivable-rule list missing SYS104/105,
  SYS200-205, REL2xx/3xx, HOST/KRB; :86-93
  MULTI_INSTANCE_WAIVER_FAMILIES missing 7 SYS ids
  (src/frob/strata/_waive.py:152-188).
- docs/strata/surface.md:120-122 multi-instance families "(4 ids)" --
  26 members (_waive.py:152).
- docs/strata/threat.md:547-548 "thirteen fingerprints" -- 19
  (src/frob/strata/_cve_fingerprint.py).
- docs/strata/evidence.md:92-107 cascade downgrades "noflow and reach"
  only -- also Independent, SetEquality (src/frob/strata/_claims.py:691).
- docs/strata/roadmap.md:89 "13 components" -- 18 nodes; :37-77 litmus
  list omits 3 of 6 programs.
- docs/strata/selfconform.md:55-56 _KIND_MAP "3 entries" -- 7
  (src/frob/strata/_effects.py:101-109); :115-117 _EXTENDED_KINDS
  membership wrong (_selfconform.py:241).

### Negative-existence claims (feature described as absent; it shipped)

- docs/commands/scaffold.md:39-43 "not yet published to PyPI" -- 0.277.0
  published, uv tool installed fleet-wide.
- docs/commands/scaffold.md:179-182 claimed "frob-natives-build" was
  absent -- frob natives build exists (_cli_parsers/_misc.py:404-427)
  and _MAKEFILE_CORE_SHIM invokes it (src/frob/scaffold/_managed.py:224).
- docs/commands/deploy.md:232-233 "Windows generation future (T-0264)"
  -- shipped (src/frob/deploy/_generate_windows.py).
- docs/design/language-adapter-tier-decision.md:10,37-38 "Kotlin
  adapter pending (T-0614)" -- KotlinAdapter exists
  (src/frob/arch/_kotlin.py:665).
- docs/design/design-pattern-traps-corpus.md:6-9 claimed "architecture-
  check-catalog.md" was absent -- it is present; reconciliation note
  never updated.
- docs/modules/cli.md:70-72 "no frob exports --consumers" -- exists
  (_core.py:377-390, T-0858).
- docs/modules/cve.md:5-7,106-112 claimed "CVE matching" was unbuilt
  (T-0147) -- built (src/frob/vet/_cve.py).
- docs/modules/dup-sota-survey.md:39-45,653 "no frob dup --probe" --
  exists (_core.py:246-260).
- docs/modules/dup.md:846-853 "DUP001/002 not wired into gates" --
  wired since T-0191 (src/frob/gates/_dup.py:69).
- docs/modules/fuzz.md:174-181 "does NOT wire CLI/gates" -- wired
  (src/frob/app/config.py:454, src/frob/gates/_fuzz.py:52); :237-240
  "hypothesis needs adding" -- present (pyproject.toml:73); :69-72
  corpus store described but unimplemented (aspirational-as-fact).
- docs/modules/perf.md:515-525 "no sampled-profile CLI yet" -- frob
  perf collect landed (self-contradicted at :638-658).
- docs/modules/render.md:135-148 "T-0459 contract not yet enforced" --
  RENDER001 live at ERROR since T-0563.
- docs/modules/serve.md:601-606 "perf hot is the one wired daemon
  proxy" -- six-plus proxies exist.
- docs/modules/strata.md:63-72 "CHK-GATE-SYS103 registry entry NOT
  added" -- exists (check-coverage.yaml:973).
- docs/modules/testing.md:796 "renumber remedy tracked as T-0162" --
  frob ticket renumber shipped (_cli_parsers/_ticket.py:404).
- docs/strata/roadmap.md:105-114 "code=/may unreachable from source"
  -- landed T-0132; :126-135 "SYS203 arbiter wiring undischarged" --
  T-1025 wired it (src/frob/strata/_contention.py:46-58).
- docs/strata/selfconform.md:30-38 "store rejects code/may" -- accepts
  since T-0166; :136-141 _UNWIRED_ENV_MODE_ALIASES removed (T-1075);
  :169-182 _alias_legacy_fs_observations removed.
- docs/strata/surface.md:391-397 "code keyword not yet lexed" and
  :457-458 "SYS-gate surfacing not wired" -- both self-contradicted
  later in the same doc.
- docs/modules/fuzz.md:54,59 invariant-anchored default claimed on --
  gate default OFF (src/frob/gates/_fuzz.py:37); :66 --budget is a
  frob check flag, not frob test (_cli_parsers/_check.py:113).
- docs/modules/vet.md:59-65 VET-JS001/JS002/[vet].internal_scopes
  presented as implemented -- none exist; :386-391 only the osv
  adapter exists; :413,:424,:68,:1087 phantom config keys/flags.

### Bare-identifier / renamed-symbol pointers (invisible to DOC006)

- docs/commands/cycle.md:49-52 CycleError/Cycle types are absent from
  the module; find_cycles returns list[list[str]]
  (src/frob/cycle/graph.py:109).
- docs/guides/extending/secrets-scan-providers.md:53 _line_marks_fake
  -- actual _fake_marker_reason (src/frob/gates/_secrets.py:676).
- docs/guides/extending/scenario-kinds.md:50 _apply_scale_rate --
  actual _apply_scale (src/frob/strata/_scenarios.py:156).
- docs/guides/extending/dup-detector-registry.md:16
  probe_smt_equivalence -- private _probe_smt_equivalence.
- docs/guides/extending/capability-registry.md:15,20
  DangerousOperation/MatrixExcuse -- private underscored names.
- docs/modules/graph.md:462-468 digest_sig etc -- private _digest_*
  (src/frob/graph/digest.py:33-51).
- docs/modules/logging.md:40-53 FrobFormatter/BelowLevelFilter --
  private _FrobFormatter/_BelowLevelFilter.
- docs/strata/host.md:168,845 host_attrs -> _host_attrs; kernel.md:321
  GROWTH_HORIZON_MONTHS -> _GROWTH_HORIZON_MONTHS; krb.md:100,318
  krb_attrs -> _krb_attrs; reliability.md:1012,1039
  SYNC_CHAIN_MAX_DEPTH -> _SYNC_CHAIN_MAX_DEPTH.
- docs/strata/threat.md:584-585,603 scan_directory_* -- private
  _scan_directory_* (src/frob/vet/_capability.py:5448,5592).
- docs/strata/waive.md:72-73,187-189 split_waiver_rule/
  validate_waiver_fields -- private.
- docs/modules/lang.md:116,187-195 leaf_tokens etc missing underscores
  (src/frob/lang/_common.py:44+).

### Moved-symbol residue (post-split file/line citations)

- docs/commands/sys.md:40-41 _add_sys_parser "in __main__.py" -- moved
  to _cli_parsers/_misc.py:443 (T-1074).
- docs/modules/dup.md:806-808 _add_dup_parser "in __main__.py" -- moved
  to _cli_parsers/_core.py:224.
- docs/modules/dup-sota-survey.md:17-487 single-file _pipeline.py line
  refs -- now a package; :14,20 lib.rs line numbers shifted.
- docs/guides/extending/strata-surface-grammar.md:8-49 and
  prover-claim-kinds.md:25-26,62, scenario-kinds.md:27,
  editors.md:10,71, selfconform.md:20,31, surface.md (8 sites),
  threat.md:395-396, host.md:76-77, reliability.md:962 -- parse.rs/
  mod.rs symbol locations; post-T-1006 split into
  grammar_policy.rs/grammar_core.rs/grammar_infra.rs/grammar_node.rs.
- docs/strata/host.md:793-794 _selfaudit_violations "in
  gates/__init__.py" -- moved by T-1188 to src/frob/gates/_sys.py:538.
- docs/modules/lang.md:113-116 walkers "in _extract.py" -- split into
  _walk_*.py modules.
- docs/modules/serve.md:778 app/ticket_runner.py -- now a package.

### Broken links / fragments (doclink blind spots)

- docs/guides/extending/pii-categories.md:58,63 links
  compliance-catalog.md -- file is compliance-registry.md.
- docs/guides/extending/benign-capabilities.md:90 fragment
  #per-repo-benign-capability-declarations not in target doc.
- docs/guides/exhaustive-research.md:46 skills/exhaustive-research/
  SKILL.md -- correct path is .claude/skills/exhaustive-research/.

### Non-python targets (Makefile, toml, yaml, Rust, tmLanguage)

- docs/guides/install.md:56 make install-tool recipe omits --extra
  serve (Makefile:280); :96-98 coverage deps claim wrong
  (Makefile:116,166).
- docs/modules/arch.md:7 "report, not a gate" and :1579-1584,:1597-1646
  severity narratives -- ARCH101/103 are error in frob.toml:265-294.
- docs/modules/render.md:21 NO_COLOR "non-empty" -- presence-only
  (src/frob/render/_color.py:18,55).

### Status/currency (audit docs, index, ticket-state prose)

- docs/audits/tickets-testing.md presents pre-T-0398 behavior as
  current ("never runs the test"); superseded by
  tickets-testing-round2.md but carries no date or supersession header.
- docs/audits/README.md:8,33 "tracked under T-0397" -- closed; residue
  under T-1193; :25 broken table row.
- docs/index.md:174-180 "Kept commands" lists map/outline/xref --
  DEPRECATED sunset 2026-10-01 (T-0580/T-0802); index link inventory
  omits 10+ existing docs.
- docs/modules/cli.md:200 "none carry frob:deprecated" -- all four do;
  :12-13 cites T-0580 where code cites T-0802.
- docs/rework.md:78 "Kept: map, outline, xref" (historical doc, flag
  only if read as current).
- FROBLEMS.md:3-4 "not tracked in git" -- it is tracked.

### Code-side bugs found by the sweep (not doc fixes)

- src/frob/gates/_lang_conformance.py:62-70 LANG002 rationale list
  still names kotlin as unregistered (registered since T-0723) --
  behavior coincidentally right, rationale stale in code.

## Drift-lock candidates (in sync today, same blind-spot class)

agent-playbook.md:356 stage-group names; sys-export-formats.md:12
_EXPORT_FORMATS; test-runner-entries.md:38-51 collectors;
install.md:305-312 DERIVED_ARTIFACTS; compliance-registry.md:16-19
checkers; litmus-fixtures.md:21-22 (omits payments_hardened.strata);
agentic-workflow.md:151 TEST001-006; ticket-kinds-states.md state
lists; registry/README.md:17-32 entry counts; index.md link inventory;
gitlog.md:32; scaffold.md:21-28; sys.md:191-195 seccomp table;
deploy.md:176-182 allowlist; cycle.md:42-45; app.md:299 STATE_STYLE;
clean/decisions/fleet/fuzz/dup/cve/graph/lang/mutate/perf/process/
render/stats/strata/serve/roadmap/host/krb/surface/threat/reliability
member tables as listed in the sweep transcripts.

## Gate-gap classes (each becomes a mechanism ticket)

1. ENUMERATION: prose tables/lists restating a code collection's
   members carry no anchor edge; DRIFT001 only covers the one anchored
   symbol's digest. Fix: frob:enumerates directive + DOCENUM001
   AST-diff of claimed vs actual members. Dominant class (~40 stale +
   ~40 at-risk instances).
2. POINTER SHAPES: bare backticked identifiers, file.py::symbol,
   rust path.rs::fn, and line-wrapped backtick spans are invisible to
   DOC006 (src/frob/gates/_docptr.py:8-33,103,220). Fix: extend the
   pointer grammar; resolve bare identifiers within the doc's anchored
   module scope; private-name awareness.
3. NEGATIVE-EXISTENCE: an "X is absent / unwired" style claim is
   unanchorable and rots when X ships. Fix: a frob:until T-#### (or
   similar) directive binding absence-claims to a ticket; claim goes
   stale when the ticket closes; unbound absence-claims flagged.
4. NON-PYTHON TARGETS: Makefile recipes/deps, frob.toml severities,
   pyproject entries, Rust file layout, tmLanguage lists have no graph
   nodes; surviving files keep path checks green while symbol-location
   claims rot. Fix: extend doc edges to the multi-language graph
   (T-1193's python-only theme) plus recipe/config anchor kinds.
5. LINK/FRAGMENT VALIDATION: doclink does not verify relative link
   basenames or #fragments in guides. Fix: DOCLNK rule for
   basename+fragment resolution.
6. STATUS/CURRENCY: audit docs need a dated status/superseded-by
   header (gate-checkable); ticket-state prose (T-#### mentions) can
   be checked against the ledger; index completeness checkable against
   the docs tree.
   - Sub-item 1 (dated status header): DONE, T-1232, DOC009.
   - Sub-item 2 (ticket-id prose vs ledger): DONE, T-1486, DOC011 --
     `src/frob/gates/_doclink_docanchor.py::docstatus_gate` now also
     flags a `T-####`/`T-draft-<hex>` doc-prose mention that does not
     resolve to any active or archived ticket. Shipped at WARN, not
     ERROR: the first live run found 10 genuine pre-existing stale
     citations across the docs tree (mostly finalized `T-draft-<hex>`
     ids never updated to the real `T-####` they became), entirely
     outside T-1486's own declared scope to fix -- tracked as a
     follow-up ticket that also promotes DOC011 to ERROR once that
     list is empty. Deliberately does NOT attempt the harder half (a
     mention whose STATE contradicts the prose, e.g. "tracked under
     T-0397" when T-0397 is closed) -- that needs sentence-level
     parsing of the surrounding claim, a separately-scoped effort.
   - Sub-item 3 (index completeness): INVESTIGATED, not built, T-1486.
     `doclink_gate` (DOC001) already treats a doc as non-orphaned when
     it is reachable via ANY of: a direct link from `docs/index.md`/
     README.md, a transitive chain through other linked docs, a
     `frob:describes` anchor, or a `frob:doc` edge target -- strictly
     BROADER than "named in docs/index.md's own link inventory," the
     sub-item's originally proposed check. A separate index-vs-tree
     rule checking only direct index links would be a STRICTER,
     narrower check than DOC001 already runs, and would false-positive
     on any doc intentionally linked only from a deeper page rather
     than the index directly (a legitimate, already-tolerated shape).
     Conclusion: this sub-item is subsumed by DOC001, not a genuinely
     distinct gap -- no new rule needed. `docs/index.md`'s own listed
     "index link inventory omits 10+ existing docs" finding (Class B,
     Status/currency section above) is a real doc-content fix, not a
     gate gap; it remains open as ordinary doc drift, not tracked here.
