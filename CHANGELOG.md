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
