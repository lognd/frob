# frob.gates -- enforcement gates, policy, and invariants

One sentence: the checks that join the obligation graph, the ticket queue,
docs, and policy rules, and turn every unaccounted-for change -- and every
unaccounted-for *absence* of change -- into a `frob check` failure.

Two enforcement halves (see `docs/rework.md`): the drift half (nothing
declared is silently broken) and the coverage half (nothing new escapes
declaration).

## Rule catalog

| Rule | Gate | Fails when |
|---|---|---|
| DRIFT001 | drift | acked digest moved without re-ack (`frob ack`) |
| DRIFT002 | drift | edge endpoint no longer resolves (rename/delete) |
| AFFECT001 | affect_drift | a diff-touched symbol's `affects()` closure names a dependent doc anchor whose file was not also touched in this diff -- see "AFFECT001/AFFECT002 (T-0628)" below |
| AFFECT002 | affect_drift | a diff-touched symbol's `affects()` closure names a dependent symbol (`uses-contract`) whose file was not also touched in this diff -- see "AFFECT001/AFFECT002 (T-0628)" below |
| COV001 | coverage | public symbol has no `doc` edge (docstring counts via `doc` facet only if policy says so) |
| COV002 | coverage | changed symbol has neither a `frob:ticket` edge to an open ticket NOR an open ticket whose `scope` glob covers its file (so one scoped ticket accounts for a whole refactor, not a per-symbol directive). A `frob:ticket` edge to a ticket that just closed to `DONE` in this same uncommitted diff (`tickets.md` itself touched) also counts -- T-0214's grace window, see design decisions below |
| COV003 | coverage | ticket in state done with evidence ids that do not resolve to collected tests (never verifies PASS/FAIL, nor scope-binding -- see the T-0398 note below the table; node-, file-, and directory-level evidence ids all resolve, T-0298 below) |
| COV004 | coverage | attachment sha256 mismatch or file missing |
| COV005 | coverage | a diff-touched file's `frob:` directive now binds a PRIVATE symbol whose span overlaps this diff's hunks, where the same `(kind, target)` directive bound a PUBLIC symbol in that file at the diff's base revision -- a displaced obligation (T-0297), see design decisions below |
| COV006 | coverage | (warn) a `frob:tests` edge bound to a PRIVATE symbol whose test has no `frob.graph.callgraph` reachability to it -- see "COV006/COV007 (T-0483)" below, including a disclosed known false-positive shape |
| COV007 | coverage | (warn) a `frob:doc` edge whose src symbol is PRIVATE -- see "COV006/COV007 (T-0483)" below |
| PLACE001 | coverage | (warn) a `frob:` directive that genuinely class-falls-back (not a directive that correctly resolved via `following` straight to a class it precedes) where a nearby real symbol looks plausibly missed -- see "PLACE001 (T-0504)" below |
| PARSE001 | parse_failures | `frob.lang.parse_file` could not parse/read a tracked source file at all -- its entire symbol/edge set is missing from this build (`GraphSnapshot.parse_failures`, T-0558/T-0561) |
| PARSE002 | parse_failures | `frob.lang.partial_parse_files()` names a file whose tree-sitter parse was SALVAGED around a syntax error (`has_error=True` but usable structure) -- every symbol after the error region is silently missing from this build (T-0905); graph-excluded paths (frob.toml [graph].exclude, e.g. deliberately-broken parser fixtures) are skipped, since they contribute no symbols and in-file waivers cannot bind there (T-0942) |
| TODO001 | coverage | bare TODO/FIXME comment (not `frob:`-prefixed) in a diff-touched file -- work marked but not accounted for at all |
| TODO002 | coverage | `frob:todo` edge bound to a non-open (closed or missing) ticket -- work accounted for, but the reference is dangling |
| SCOPE001 | scope | diff touches paths/symbols outside the active ticket's `scope` |
| PRE001 | pre-work | ticket moved to in-progress without a recorded pre-work sweep |
| INV001 | invariant | invariant has no evidence (test or policy rule) |
| INV002 | invariant | invariant has no code anchor (`frob:invariant`) |
| INV003 | invariant | (warn) a doc file under `INV003_SPEC_DIRS` (`docs/modules`, `docs/strata`) makes a claim-shaped exclusivity/normative assertion (`only`, `sole`/`solely`, `exclusively`, `nothing else`, `never...except`, `at most/exactly one`, verb required in the same sentence) with no `<!-- frob:invariant INV-### -->` marker naming a real (loaded) invariant, and no reasoned `<!-- frob:waive INV003 reason="..." -->` marker -- see "INV003 (T-0462)" below |
| INV004 | invariant | (warn, advisory) a `docs/**.md` section uses claim-shaped normative language (`must`, `must not`, `never`, `always`, `shall`, `guarantees`, `ensures`, `requires`, plus INV003's exclusivity vocabulary) but anchors ZERO `frob:invariant` markers and carries no reasoned `<!-- frob:waive INV004 reason="..." -->` marker -- see "INV004 (T-0452)" below |
| INV005 | invariant | (warn, T-0543/B12) an invariant's evidence collects (satisfies INV001) but is never shown, via a `frob:tests` edge or same-file trust to the anchor, to actually reach its `frob:invariant`-anchored symbol -- a name-match-only existence check proves nothing about which invariant a test covers; see "INV005 (T-0543)" below |
| INV006 | invariant | (warn, T-0408) a SOURCE file under `INV006_SRC_DIRS` (`src`, `strata-core/src`, `frob-core/src`) makes a claim-shaped exclusivity assertion (same vocabulary as INV003) with no `frob:invariant` edge anchored anywhere in the file, and no `frob:waive INV006 reason="..."` edge -- see "INV006 (T-0408)" below |
| TICK006 | tickets | a Done report's affirmative "filed" claim (`Filed: T-####`, `filed as T-####`, `Filed T-draft-<hex>`, ...) whose id resolves to no block in `tickets.md` or `tickets-archive.md` -- see "TICK006 (T-0726)" below |
| TICK007 | tickets | (warn) a dispatchable (unblocked, unleased) CRITICAL/HIGH ticket has sat past its `frob.tickets.undispatched_stale` threshold -- see "TICK007 (T-0820)" below |
| TICK008 | tickets | (warn) a ticket in the checked ledger carries unknown/extra frontmatter field(s) (`Ticket`'s `extra="allow"` captured them into `__pydantic_extra__` instead of hard-failing) -- often a typoed known field, whose value is silently lost to the schema default; see "TICK008 (T-0842)" below |
| COMPLIANCE005 | compliance | a `docs/design/registry/compliance.yaml` `CMPL_REGISTRY_UNIT_IDS` member carries a `deferred`/undispositioned disposition instead of `handled_by`/`out_of_scope` -- see "COMPLIANCE005 (T-0788)" below |
| FMT001 | fmt | (warn) a diff-touched `frob:` directive comment line exceeds the project's configured line length -- see "FMT001 (T-0851)" below |
| DEC001 | decisions | a `frob:decision AD-###` edge points at a record that does not exist (opt-in: a `decisions/` dir must exist) |
| DEC002 | decisions | an `accepted` decision record has no `frob:decision` code anchor |
| TEST001 | test | public function/method has no `frob:tests` unit edge |
| TEST002 | test | unit edges for a symbol number fewer than `min_unit_cases` |
| TEST003 | test | interface (package whose public symbols are imported by another package) has fewer than `min_integration` integration edges |
| TEST004 | test | declared system has fewer than its `min_e2e` e2e edges |
| TEST005 | test | measured coverage below threshold (per-symbol branch, per-module line, or per-system line) |
| TEST006 | test | coverage evidence missing, or stale against current file hashes |
| TEST007 | test | a cross-package `frob:uses-contract` dependency has no pairwise integration test covering that boundary (opt-in via `[testing].pair_integration`) |
| DOC001 | doclink | a doc file matching `[gates.docs] include` globs (default `docs/**/*.md` -- new files auto-obligated) has no frob:describes anchor, no frob:doc edge into it, and is unreachable via markdown links from the roots (docs/index.md, README.md) |
| DOC002 | docanchor | a `frob:doc <file>#<slug>` edge whose target doesn't resolve: missing `#anchor`, missing file, or `<slug>` matches neither a heading slug (`frob.graph.dsl.slugify`) nor an explicit `<a id="...">` in `<file>` |
| POL* | policy | user-defined rules from `frob.toml` (see below) |
| DUP001/DUP002 | clones | the diff introduces a clone of an existing symbol (opt-in, `[dup].enforce`) |
| DUP003 | clones | (T-0399) `[dup].enforce=true` but frob-core is not installed/built -- clone detection was requested but is unavailable; fails CLOSED (ERROR) instead of silently skipping |
| FUZZ001-003 | fuzz | fuzz obligations under `[fuzz]` (opt-in) |
| PERF001-004 | perf | lexical performance smells (build-a-set-once, etc.) |
| REL001 | release | release-readiness check |
| SYS001 | sys | a `frob:channel/boundary/secret` directive names a construct id absent from the loaded `.strata` design model (opt-in: a `design/`, or `[strata].design_dir`, directory of `.strata` files must exist); suppressed for the whole run while any design file fails to load (SYS004 reports that instead) |
| SYS002 | sys | a `Boundary` or Secret-clearance `Node` in the design model has no `frob:boundary`/`frob:secret` code binding anywhere |
| SYS003 | sys | (warn) tier-2 code binding (`frob.strata.bind_code`/`check_import_conformance`) finds an undeclared cross-component import between two design-bound files; warn-first on landing, intended to flip to error via `[gates.severity]` once proven |
| SYS004 | sys | a `.strata` design file failed to parse/elaborate; the message names a stale native build (`make core`) as the likely remedy when one is detected (T-0347, T-0248's `frob.strata.stale_natives`), per the T-0166 incident where a grammar-ahead-of-native mismatch masqueraded as a `.strata` syntax error |
| SELFAUDIT001 | sys | (T-0756) frob's own self-conformance (SYS100/SYS101/SYS102), resource-contention (SYS2xx), and reliability (REL2xx) audit surface, folded into the ordinary `frob check` gate pipeline -- see "Self-audit at land (SELFAUDIT001, T-0756)" below |
| SEC001 | secrets | a git-tracked file contains text matching a provider's real-looking credential shape (waivable with reason) |
| SEC002 | secrets | a git-tracked `.env`/`.env.*` file exists (`.env.example`/`.env.sample`/`.env.template` excepted) |
| SEC003 | secrets | a git-tracked file contains a live Stripe secret key (`sk_live_...`) or a private-key PEM header -- unwaivable, see `_UNWAIVABLE_RULES` |
| WAIVE001 | (always on) | a `frob:waive` directive is missing `reason="..."` |
| WAIVE002 | error (T-0753; was warn) | a `frob:waive` targets a rule id that can never be matched -- see "Waive boundary" below |
| WAIVE003 | (always on) | a `frob:waive` on a package-scoped rule (TEST003/TEST004/TEST007) reaches more than one distinct violated package/system id via directory-prefix matching -- see "Waiver over-breadth (T-0470)" below |
| WAIVE004 | warn (T-0753) | a `frob:waive` on a RECOGNIZED rule id matches zero findings this run at its own site -- see "Unnecessary-waiver detection (T-0753)" below |
| WAIVE005 | error (T-0753) | a `frob:waive`'s optional `until="YYYY-MM-DD"` boundary has passed -- see "Waiver expiry (T-0753)" below |
| ARCH001 | arch | `frob.arch`'s complexity-aware long-function check (docs/modules/arch.md) still flags a function after its flat-body filter -- the one `frob.arch` category channeled into a real gate `Violation`, waivable with a reasoned `frob:waive ARCH001 reason="..." [ceiling=N]` (T-0289) |
| PII010 | pii_structural | a pydantic/dataclass/TypedDict/attrs field's name or type annotation matches a PII-shaped signature (`FIELD_SIGNATURES`), a TS `interface`/`type`/`class` field, or a Rust `struct` field (T-0352), with no `frob:waive PII010 reason="..."` -- see "PII010/SEC110" below |
| PII011 | pii_structural | a tracked `.py` file's string-literal constant is structurally email-shaped (`_is_email_shaped`, `email.utils.parseaddr`-based) with no `frob:secret-fake` marker or `frob:waive PII011 reason="..."` -- see "PII010/SEC110" below |
| PII012 | pii_structural | a plain identifier or `#`-comment word token resembles a `FIELD_SIGNATURES` keyword (suggestion severity, not deny-by-default) -- see "PII010/SEC110" below |
| SEC110 | pii_structural | an `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)` call site, a TS `process.env`/`import.meta.env` access, or a Rust `std::env::var(...)`/`env::var(...)` call (T-0352), with no `frob:waive SEC110 reason="..."` -- see "PII010/SEC110" below |
| REF001 | refs | a git-tracked file has zero inbound references (auto-detected or verified `frob:used-by`) from any other tracked file -- see "Anti-orphan file-reference gate" below |
| REF002 | refs | a git-tracked file has exactly one inbound reference (fragile single anchor) -- see "Anti-orphan file-reference gate" below |
| REF003 | refs | a `frob:used-by <consumer>` declaration is dangling: the named consumer does not exist as a tracked file, or does not itself reference the declaring file back -- see "Anti-orphan file-reference gate" below |
| DOC004 | docblocks | a fenced code block in a tracked `.md` doc references the project's OWN code surface (manifest-derived python/rust/ts namespaces) and either does not resolve (error, "stale") or resolves but carries no nearby `frob:doc`/`frob:describes`/`frob:tests` anchor (warn, "unbound") -- see "Unbound/stale doc code blocks" below |
| DOC005 | docblocks | `README.md`'s command table is out of sync with the live top-level subcommand registry: a real subcommand has no table row (error, "missing"), a table row names a subcommand that no longer exists (error, "stale"), or a "N commands" prose count claim does not equal the live count (error) -- see "DOC005 README command-table drift-lock" below |
| DOC006 | docblocks | (warn, T-0688 new-gate-at-WARN precedent) a doc's PROSE (inline code span or markdown link, not a fenced code block -- DOC004's territory) contains a pointer of a RECOGNIZED, mechanically resolvable shape (file/path, cli invocation, config reference, code symbol, doc-anchor link) that does not resolve, or a `frob:tests` directive's target uses pytest's `Class::method` collect-only separator where this graph wants a single `::` then a dotted `Class.method` qualname -- see "DOC006 doc-pointer resolution gate" below |
| EXCL001 | excludehazard | a `.git/info/exclude` entry shadows a git-tracked file or a directory containing tracked files -- see "EXCL001 (T-0465)" below |
| PROTO001 | protocol_summary | (warn) a `frob:requires`/`frob:transition`-tagged symbol's `frob.graph.summary.compute_protocol_summaries` result is `poisoned` (an `UNRESOLVED_CALLEE` somewhere in its transitive call closure) -- see "PROTO001 (T-0813)" below |
| PROTO002 | protocol_summary | (error) a `frob:requires` symbol's required state is never established anywhere reachable (or its summary is poisoned), and no language-excuse discharges it -- see "PROTO002/PROTO003 (T-0746)" below |
| PROTO003 | protocol_summary | (error) a `frob:transition` symbol's precondition state is never established anywhere reachable (or its summary is poisoned), and no language-excuse discharges it -- see "PROTO002/PROTO003 (T-0746)" below |

**T-0398 (evidence integrity) note on COV003**: COV003 only ever answers
"does this evidence id resolve to a currently-collected test" -- it does
NOT verify the test PASSED, and does NOT verify the evidence binds to the
ticket's own touched/scope symbols (any collected id, however unrelated,
satisfies it). Those two gaps are closed at the `frob.tickets.transition`/
`land` call sites instead, via optional injected parameters
(`add_evidence(..., passed=...)`, `transition(..., covers_scope=...)`,
`land(..., collected=..., passed=..., covers_scope=...)`) rather than a
new COV rule -- `frob.tickets` deliberately has no `frob.testing`/
`frob.graph` dependency (docs/rework.md cycle-avoidance), so it cannot
compute either answer itself; a caller with graph/testing access (today,
directly testable via `frob.gates.evidence_covers_scope`; the `frob
ticket` CLI's own wiring of real values into these parameters is a
disclosed follow-up, not yet done) supplies the answer. See
docs/modules/tickets.md's `add_evidence`/`transition`/`land` entries for
the parameter contracts.

**T-0298 (file-/directory-level COV003 evidence)**: an evidence id with no
`::` at all (a bare path, e.g. `tests/test_vet.py` or `tests/unit/deploy`)
resolves iff at least one collected node id lives under it -- as that exact
file (`<path>::...`) or inside that directory (`<path>/...`). Node-level
resolution (`path::Class::method`) is tried FIRST and stays the preferred,
most precise granularity; the path-level check is a fallback, not a
replacement. It is deliberately non-vacuous: a path with zero matching
collected node ids (nothing landed there, or a typo'd/nonexistent
directory) still fails COV003 -- "this whole file/dir passes" only counts
when something under it actually collected. This exists because a refactor
touching ~20 files naturally produces evidence at file granularity ("this
test file passes"), not one node id per file; forcing node-level-only
evidence for that shape of change is what produced a real 25-error
main-red incident (2026-07-19) when two agents both recorded file-level
ids COV003 could not, at the time, resolve at all.

<!-- frob:invariant INV-013 -->

Severity: `error` (exit 1) or `warn`; per-rule default overridable via the
`[gates.severity]` table in `frob.toml` (`COV001 = "warn"`), applied as a
single post-processing step in `run_gates` -- the legacy-adoption dial. A
rule produced by any of the gates above is waivable at a site via
`frob:waive RULE-ID reason="..."`; waivers are listed in every report, so a
waiver is visible debt, never silence.

### DEBT gate (T-0412)

`frob:debt <RULE> reason="..." ticket="T-####" [until="YYYY-MM-DD"|"X.Y.Z"]`
is the TEMPORARY counterpart to `frob:waive`'s PERMANENT exception (full
directive semantics: `docs/guides/extending/comment-dsl-directives.md`'s
"frob:waive vs frob:debt" section). `frob.gates.debt_gate` (rule family
`DEBT`) raises three distinct failure modes, all ERROR severity (a debt is
a structural claim about owed work, not a hygiene nit):

- **DEBT001**: a `frob:debt` missing `reason="..."` and/or `ticket="T-###
  #"` -- surfaced from `frob.graph`'s `MalformedDirective` list, mirroring
  WAIVE001's shape.
- **DEBT002**: `ticket="..."` names a ticket that is missing or not open.
  Same open-ticket check TODO002 applies to `frob:todo`, but at ERROR
  (not WARN) severity: an untracked `frob:todo` is a hygiene gap, a
  mis-tracked `frob:debt` is a lie about what is actually owed.
- **DEBT003**: `until="..."` (a `YYYY-MM-DD` date or an `X.Y.Z` semver,
  judged by `_debt_is_expired` against the run's actual date/version) has
  passed. A debt with no `until` never expires this way on its own --
  release-time blocking (below) still catches it.

`frob.gates.release_gate` (REL001) additionally refuses to bless a release
while ANY `frob:debt` is open at all, expired or not
(`_release_open_debt_violations`) -- this is T-0412's central requirement:
debt is collected and re-raised before shipping, never silently carried
forward as a de facto permanent waiver the way an un-audited
`frob:waive` can be.

`frob.gates.list_debt` (and the `frob debt [--json]` CLI,
`src/frob/app/debt_runner.py`) reports every currently-recorded entry
(rule, site, ticket, until, expired) regardless of whether it is itself
well-formed/open/unexpired -- a listing tool, not a gate; DEBT001-003 are
what actually fail the build.

### DEPRECATED gate (T-0576)

`frob:deprecated <since> sunset="YYYY-MM-DD" ticket="T-####" [reason="..."]`
generalizes `frob:debt` to the API surface itself: a ticket-bound, dated
exit for a public symbol that is still callable today. Distinct from
`frob:debt` in what it is about -- a debt suppresses a GATE FINDING (the
symptom); a deprecation is about the symbol's continued EXISTENCE.
`frob.gates.deprecated_gate` (rule family `DEPR`) raises four distinct
states:

- **DEPR001**: a `frob:deprecated` missing `sunset="YYYY-MM-DD"` and/or
  `ticket="T-####"`, or with a `sunset=` that is not a `YYYY-MM-DD` date --
  surfaced from `frob.graph`'s `MalformedDirective` list, mirroring
  DEBT001's shape. ERROR.
- **DEPR002**: `ticket="..."` names a ticket that is missing or not open --
  T-0576's "ticket closes without removal" failure mode: once the owning
  ticket closes, the directive (and presumably the symbol it sunsets) must
  be gone. Same open-ticket check DEBT002 applies to `frob:debt`. ERROR.
- **DEPR003**: the bound ticket is open and `sunset` has NOT yet passed --
  the symbol is still inside its warning window. WARN, not ERROR, so a
  live-but-scheduled deprecation stays visible in ordinary `frob check`
  output rather than being silent until the date arrives (`frob:debt` has
  no equivalent "still valid, but visible" signal -- a deprecated PUBLIC
  symbol needs one).
- **DEPR004**: the bound ticket is open and `sunset` HAS passed --
  escalates from DEPR003's warning to a hard ERROR, mirroring DEBT003's
  expiry escalation.

DEPR002 suppresses DEPR003/DEPR004 for the same edge (a mistracked ticket
is the more actionable finding); DEPR003 and DEPR004 are otherwise mutually
exclusive per edge (a given deprecation is either still in its window or
past sunset, never both).

`frob.gates.release_gate` (REL001) additionally refuses to bless a release
while ANY `frob:deprecated` is past its sunset (`_release_expired_deprecated_
violations`) -- unlike `frob:debt` (where ANY open debt blocks a release,
expired or not), a deprecation still inside its warning window is fine to
ship; only an unenforced, past-sunset one is a release blocker. This is
T-0576's central requirement: a sunset date with nothing enforcing it is
not actually a sunset.

`frob.gates.list_deprecated` (and the `frob deprecated [--json]` CLI,
`src/frob/app/deprecated_runner.py`, T-0638) reports every currently-
recorded entry (symref, since, sunset, ticket, expired) regardless of
whether it is itself well-formed/open/unexpired -- a listing tool, not a
gate; DEPR001/002/004 are what actually fail the build. The CLI
additionally cross-references `tickets.md`/`tickets-archive.md` to label
each entry's status `in-window`, `past-sunset`, or `orphaned` (ticket
missing or closed) -- a tri-state view `DeprecatedEntry.expired` alone
(in-window vs past-sunset) does not carry, mirroring DEPR002's "ticket
closes without removal" failure mode as a display, not a gate, concern.

### Typestate protocol declarations (T-0744)

`frob:protocol`/`frob:transition`/`frob:requires` (T-0739 umbrella, child 1)
are the comment-DSL declaration surface for typestate protocols --
`frob.graph.dsl` parses them into `EdgeKind.PROTOCOL`/`TRANSITION`/
`REQUIRES` edges; the summary-fixpoint engine and the actual call-graph
verification (state-requirement violations, invalid-transition errors,
cleanup-obligation checks) are later T-0739 children, not built by this
ticket -- this section documents the declaration grammar and its own
parse-time enforcement only.

```
frob:protocol <NAME> states="S1,S2,..." initial="S1" [cleanup="always"|"on-error"|"process-exit-ok"]
frob:transition proto="<NAME>" from="S" to="T"
frob:requires proto="<NAME>" state="S"
```

- `frob:protocol` declares a named state machine at whatever symbol the
  directive binds to (module, class, or function) -- `states=` is a
  comma-separated list of at least one state name, `initial=` must name one
  of those states, and the optional `cleanup=` (default `"on-error"`, the
  later cleanup-obligation gate's policy dial, T-0739 child 4) must be one
  of `always`/`on-error`/`process-exit-ok`. Any of those requirements
  failing is a `MalformedDirective`.
- `frob:transition`/`frob:requires` have no bare target token, unlike every
  other verb in this DSL -- their whole grammar is `key="value"` attrs, and
  the edge's `target` becomes the parsed `proto=` attribute itself
  (`frob.graph.dsl._ATTR_ONLY_VERBS`). `frob:transition` requires `proto=`,
  `from=`, and `to=`; `frob:requires` requires `proto=` and `state=`;
  either missing an attr is a `MalformedDirective` naming which one.
- **Zero-declaration convenience**: a bare `<prefix>_init`/`<prefix>_deinit`
  function pair in the same file (also `<prefix>_open`/`<prefix>_close` and
  `<prefix>_acquire`/`<prefix>_release`, `frob.graph.dsl._INFER_PAIRS`)
  implicitly synthesizes a 3-state `uninitialized -> active -> closed`
  protocol with no `frob:protocol` comment at all -- the same PROTOCOL/
  TRANSITION edges an explicit declaration would produce, each carrying
  `inferred="true"`. Inference is ONLY for these declared name-pair
  patterns, deliberately never a general state-machine inference heuristic
  (T-0744's explicit scope limit) -- an unpaired `*_init` with no matching
  `*_deinit` in the same file infers nothing.
- **Enforceability (user mandate)**: a `frob:protocol` bound by zero
  `frob:transition`/`frob:requires` edges in the same file is itself a
  `MalformedDirective` (`frob.graph.dsl._protocol_coherence`, mirroring
  `frob:debt`/`frob:todo` coherence's `_debt_todo_coherence`) -- the
  catalogued-is-not-enforced doctrine applied to protocols: a declaration
  nothing else in the file binds to is a drift error, never a silent no-op.
  This check is per-file (matching every other DSL-layer coherence pass);
  a protocol declared in one file and bound entirely from another still
  reads as unbound here -- a graph-wide cross-file tally is a later T-0739
  child's job, not this parse-layer pass.

No new gate rule id was added for this surface: every `MalformedDirective`
these checks produce (missing/invalid attrs, an unbound protocol) already
falls through **DSL001**'s existing generic catch-all (any malformed
`frob:` directive not already claimed by a per-flavor rule -- see the
`DEBT001`/`DEPR001` entries above for the established shape this reuses),
so a malformed or unbound protocol declaration fails `frob check` today
with no `frob.gates` change required.

### PROTO001 (T-0813)

`frob.gates._protocol_summary.protocol_summary_gate` is the production
entrypoint the T-0809 reviewer's condition (a) asked for: the first real
repo-scan caller of `frob.graph.callgraph.build_call_graph(...,
mark_unresolved=True)` feeding `frob.graph.summary
.compute_protocol_summaries`, turning the T-0745 `UNRESOLVED_CALLEE`
poisoning channel into a real `frob check` finding instead of a
fixture-only test path.

Scoped narrowly: only a symbol that itself carries a `frob:requires`/
`frob:transition` directive (an explicit T-0744 protocol participant) is
ever reported -- `compute_protocol_summaries` still analyzes every
function transitively reachable from those tagged entrypoints (poisoning
propagates through untagged helpers too, per T-0745's NO-FAIL-SILENT
contract); the scoping only decides which POISONED summaries are worth
surfacing, not what the engine computes. Grouped and cached per package
(same directory, mirroring `DEAD001`'s posture) -- `build_call_graph` and
the package's `frob:` directive parse both run at most once per package
regardless of how many tagged symbols it declares.

**False-positive disposition (dunder/cross-package attribute calls,
T-0813)**: `obj._method(...)` and `super().__init__(...)` both LOOK like
this repo's own private-symbol calling convention (leading underscore)
under `build_call_graph`'s best-effort, name-based resolution, but are
never actually a call to a local helper the graph could ever bind --
`obj`'s real class, or the base class `super()` resolves to, is not
necessarily even in the scanned `paths`. `frob.graph.callgraph
._unresolved_exempt_names` filters these out of `mark_unresolved`'s
poisoning trigger: a call name whose EVERY occurrence in a function body
is an attribute call (`<expr>.name(`) on a receiver other than `self` is
exempt from ever becoming an `UNRESOLVED_CALLEE` edge. `self._foo(...)`
is deliberately NOT exempted -- that receiver token IS the enclosing
class, exactly the intra-package private-helper call this graph exists
to catch. A name that also appears as a bare call or a `self.`-call
elsewhere in the same body is not exempt either (one confident occurrence
keeps it eligible).

Python files ONLY (`.py`): `build_call_graph`'s callee-privacy check
hardcodes Python's leading-underscore `public` convention -- the same
Rust/TypeScript/C soundness gap `DEAD001` already disclosed and scoped
around, not a new gap this gate introduces. WARN-only (advisory-but-
tracked, matching `DEAD001`/REF/PERF/FUZZ's posture), waivable with
`frob:waive PROTO001 reason="..."`.

### PROTO002/PROTO003 (T-0746)

Child 3 of the T-0739 umbrella: the two ERROR-tier verification rules over
the SAME per-package `frob.gates._protocol_summary.protocol_summary_gate`
scan that computes PROTO001 -- one pass, three findings, never three
separate repo walks.

- **PROTO002 (state-requirement violation)**: a `frob:requires proto="P"
  state="S"` symbol whose summary is poisoned (an unresolved callee makes
  it untrustworthy -- ERROR here, stricter than PROTO001's WARN for the
  identical poisoning signal, per the ticket's "unknown/poisoned summaries
  at a checked call site = ERROR" mandate), or whose required state `S` is
  never ESTABLISHED anywhere reachable from the package's tagged
  entrypoints (`S` is neither the protocol's declared `initial=` state nor
  the `to=` state of any reachable `frob:transition`). The `*_init-never-
  called`/`*_deinit-orphaned` cases the ticket names fall out of this
  directly: `frob.graph.dsl`'s T-0744 name-pattern inference (`_init`/
  `_deinit`, `_open`/`_close`, `_acquire`/`_release`) synthesizes a
  requires/transition pair with no `frob:protocol` comment at all, so an
  inferred pair whose init half is unreachable IS exactly "no transition
  into the active state is reachable".
- **PROTO003 (invalid transition)**: a `frob:transition proto="P"
  from="S" to="T"` symbol whose precondition state `S` fails the same
  established-state test PROTO002 uses -- a transition reached in a state
  the protocol can never establish.

**APPROXIMATION, disclosed, not silently papered over**:
`compute_protocol_summaries` (T-0745) has no per-call-site statement
ordering yet -- real path-sensitivity needs an ordered call graph
(deferred, T-0840). PROTO002/PROTO003 therefore ask an EXISTENTIAL
question ("is `S` established by SOME reachable transition anywhere in
the closure") rather than a path-sensitive one ("is `S` established on
EVERY path reaching this exact call site") -- deliberately biased toward
FALSE NEGATIVES (a real ordering bug can be missed if some other path in
the same closure happens to establish the state) rather than false
positives (a state genuinely unreachable by any transition anywhere is
wrong on every path, so that direction is sound). The ticket-named crisp
case -- "reachable without net_init", init never called at all -- is
caught exactly.

**Language-excuse discharge**: before either rule reports an ERROR,
`frob.arch._protocol_excuse`'s per-language predicates get a chance to
discharge it -- a runtime guarantee the T-0744 DSL cannot see but that
provably reestablishes or maintains the missing state:

| Language | Mechanism | Revoked by |
|---|---|---|
| Rust | `impl Drop for T` | `mem::forget(x)`/`ManuallyDrop<T>` observed on `T` |
| C++ | a `~T()` destructor (RAII) | (never modeled as revocable here; T-0809's `escaped`/`acquired` sets are the intended "result actually held" cross-check, not yet wired) |
| Python | a `with` block naming the resource | (lexical; Python's `__exit__` guarantee has no equivalent escape hatch) |
| TypeScript | a `using` declaration or `try`/`finally` naming the resource | (lexical, same as Python) |
| GC-finalized (Java/Kotlin/JS) | **never discharges** -- finalizer run timing is unspecified by every mainstream GC | n/a |

A discharge is recorded as a `Severity.WARN` finding (rule `PROTO002`/
`PROTO003`, never silently dropped -- NO-FAIL-SILENT), naming its
mechanism, so it stays visible and auditable instead of vanishing.
`build_call_graph`'s Python-only scope (the same disclosed limitation
PROTO001 carries) means only `frob.arch._protocol_excuse
.python_with_discharge` is wired into this repo-scan gate today -- the
Rust/C++/TypeScript/GC predicates are doctrine-complete and directly
unit-tested (`TestProtocolLanguageExcuseDischarge` in `tests/test_gates.py`),
but wiring them into a real cross-file scan is blocked on those languages
getting `build_call_graph` support at all (filed as T-0841, mirroring
T-0745's own T-0809 disclosure rather than building a second, unreviewed
call-graph substrate here).

**Severity**: ERROR by default for both rules (T-0746's own "enforceable,
never fail-silent" user mandate) -- this repo's own tracked source carries
zero real (non-fixture, non-test) `frob:protocol` usage today, so
ERROR-by-default measures clean against `main` at landing time. Both are
waivable (`frob:waive PROTO002 reason="..."` / `frob:waive PROTO003
reason="..."`) for a case the engine's existential approximation gets
wrong.

### PROTO005 (T-0747)

Child 4 of the T-0739 umbrella: cleanup obligations -- release-
postdominates-acquisition on all exits (including exceptional ones),
escape transfer, and per-protocol `cleanup=` policy. Shares PROTO001-004's
per-package `frob.gates._protocol_summary.protocol_summary_gate` scan for
package selection only; unlike PROTO001-004 it consumes neither
`build_call_graph` nor `compute_protocol_summaries`' fixpoint (those give
transitive UNION sets with no per-exit ordering, which this check
genuinely needs) -- it is a direct intraprocedural walk over each
acquiring function's own `NormalizedFunction` body plus the T-0809
resource-tracking DSL's own edges (`docs/modules/graph.md#resource-
tracking-dsl-t-0809`).

Two independent sub-checks, both reported as `PROTO005`:

- **Resource-level (intraprocedural postdominance)**: for a symbol
  carrying its own `frob:acquire <resource>` --
  - `frob:escapes <resource>` on the SAME symbol discharges it entirely
    (ESCAPE TRANSFER: the obligation moves to whichever caller receives
    the resource, an accounting that caller's own `frob:acquire`/
    `frob:escapes`/`frob:release` declarations carry, not this one).
  - `frob:release <resource>` on the SAME symbol also discharges it
    entirely -- the DSL attaches `ACQUIRE`/`RELEASE` at FUNCTION
    granularity, not a statement inside it, so a function claiming both
    is trusted whole (there is no finer attachment point to subdivide
    against).
  - Otherwise: every `return` in the function's own body (or, with none,
    one implicit fallthrough exit at the body's last line) must be
    preceded, at an earlier or equal source line, by a call to some
    OTHER same-file function that itself carries `frob:release` for that
    resource -- a `return` reached before any such call is the crisp
    "early-error return skips cleanup" case, reported by its exact line.
    A `cleanup="process-exit-ok"` policy (looked up from whichever
    `frob:protocol` binds to this symbol or its enclosing file, default
    `"on-error"`) additionally discharges silently a `return` preceded by
    a process-terminating call (`exit`/`_exit`/`quit`) -- any other
    policy still requires that exit's own release coverage.
  - EXCEPTIONAL EXIT (Python-only, reusing T-0686's `frob.arch._mayraise
    .compute_may_raise`): existential and false-negative-biased on
    purpose, matching PROTO002/003/004's own disclosed approximation
    posture -- fires only when the function's OWN may-raise set is
    non-empty AND zero release calls appear anywhere in its body at all;
    a genuine path-sensitive "release happens on some paths but not the
    one that actually raises" gap is deferred, not attempted, same
    posture PROTO002/003 already carry toward T-0840.
  - Language-excuse discharge (the same table PROTO002/003 use) is
    checked before either half reports an ERROR.
- **Protocol-level (`*_deinit-never-called`)**: a `frob:protocol
  cleanup="always"` protocol that has been ENTERED somewhere in the
  package's reachable closure (some non-initial state is established) but
  whose terminal state(s) -- any declared state with zero outgoing
  `frob:transition` anywhere in the package -- are never themselves
  established, meaning no reachable transition ever closes it back out.
  `cleanup="on-error"` (the DSL default) and `cleanup="process-exit-ok"`
  protocols are deliberately OUT of this half's scope: the former's
  obligation is conditional on an error path this existential,
  non-path-sensitive established-state view cannot distinguish from a
  clean one, and the latter explicitly waives ever needing a reachable
  close.

**Severity**: ERROR by default (matching PROTO002/003's own "enforceable,
never fail-silent" mandate) -- waivable with `frob:waive PROTO005
reason="..."` for a discharge this check's approximations cannot see (a
release genuinely performed by a different function on the exact path
taken, or a cross-file release the same-file-only bare-name resolution
above cannot follow).

T-0972: `protocol_summary_gate` (the shared PROTO001-005 per-package scan)
picked up a `frob:ticket T-0972` binding for a `sorted(set(symrefs))`
call whose set differs every package iteration -- reasoned
`frob:waive PERF004`, no behavior change.

### Self-audit at land (SELFAUDIT001, T-0756)

Root-cause analysis 2026-07-22 (tickets.md T-0756): frob's own self-
conformance/resource-contention/reliability audit surface
(`frob.strata.check_self_conformance` SYS100-102, `check_resource_
contention` SYS2xx, `check_reliability_timeouts`/`check_reliability_health`
REL2xx) was, until this ticket, reachable ONLY via the separate `frob sys
audit` CLI verb (`frob.app.sys_runner._run_audit`) -- never a `frob check`
gate, never something `frob ticket land`'s own preflight consulted. T-0724
enabled a check whose OWN landing reddened this exact surface undisclosed;
nothing structurally blocked that land, because a reviewer had to remember
to run `frob sys audit` by hand and happened not to.

`frob.gates.sys_gate` (the `sys` tool-stage function `frob check` already
calls unconditionally whenever a `design/`, or `[strata].design_dir`,
directory exists) now also runs `_selfaudit_violations`, folding every
finding from all four families into the ordinary `Violation` pipeline under
one rule id, **SELFAUDIT001** (ERROR, `_KNOWN_GATE_RULES`-registered so
`frob:waive SELFAUDIT001 reason="..."` matches like any other rule). Each
`Violation.message` embeds the ORIGINAL underlying rule id (SYS100/SYS101/
SYS102/SYS200-203/REL200/REL201/REL210/REL211) and node so a reader never
has to re-run `frob sys audit` separately to see which family fired.
Suppressed whenever any `.strata` design file failed to load (matches
DOC003/SYS001-004's posture -- a partial model cannot be honestly
self-audited).

**Why this closes both halves of the ticket's mandate with ZERO new land
wiring**: `frob ticket land`'s existing `check_gates`/`check_gate_findings`
post-merge re-verification (`frob.tickets._land.land`, T-0754/T-0846)
already re-runs `frob check --ticket` against the just-merged tree and
refuses (`LandError.ClaimDivergence`) if the recorded gate-error count no
longer matches. Once SELFAUDIT001 is an ordinary gate `frob check` reports,
that EXISTING machinery automatically covers it -- landing a change that
reddens frob's own self-audit now fails the same way landing a change that
reddens any other ERROR-severity gate already does. No `frob.tickets`/
`frob.app` code needed to change to wire this in; the fix was making the
surface a gate at all.

### New-gate-rule acceptance policy (T-0756)

The companion structural fix for the SAME root-cause class: several rejected
tickets (T-0630/T-0595/T-0616/T-0710) each shipped a gate/check rule that
was built but never actually reachable from a real invocation --
"invoked-by-nothing". A rule's own unit tests routinely pass in that state
(they call the pure function directly), so T-0755's TEST016 mutation-
evidence obligation cannot catch this class either: TEST016 only asks
whether recorded evidence is adversarial against the diff, never whether
the diff is reachable from production at all.

`frob.tickets._new_gate_rule_acceptance.new_gate_rule_ids` detects, via a
diff-aware scan of `src/frob/gates/__init__.py`'s `_KNOWN_GATE_RULES`
frozenset literal (the one registry every gate rule id must be listed in),
any rule id present in the CURRENT working tree that was not present at
`base_ref`'s tip. `frob.tickets._done_transition_guard` runs this check
UNCONDITIONALLY on every `DONE` transition (both direct `frob ticket close`
and `frob ticket land`'s finalize-and-close step, which calls the same
`transition(..., DONE)` internally -- no separate land-time wiring needed,
mirroring `frob.tickets._live_tracker.live_tracker_citations`'s posture):
if any new rule id is found, the ticket must carry at least one BOUND
acceptance criterion (`frob ticket evidence ... --accepts N`) whose text
reads as a before-fails/after-passes fixture proof (contains both a FAIL
and a PASS marker, case-insensitive) -- proving the rule fires through the
PRODUCTION invocation, not merely a pure-function unit test. A ticket
missing this is refused with `TicketError.NewGateRuleUnaccepted` /
`LandError` (via the same `transition` call land's finalize step makes).

**v1 scope, disclosed**: the detector is scoped to `_KNOWN_GATE_RULES`
specifically (the one registry file every `Violation`-producing gate rule
must be listed in) -- a rule family added some other way is a known
residual gap, not silently assumed covered. This ticket's own SELFAUDIT001
addition folds the previously-uncovered `frob sys audit` SYS1xx/SYS2xx/
REL2xx families INTO `_KNOWN_GATE_RULES` for exactly this reason. v1 also
requires ONE qualifying criterion covering the ticket as a whole (not a
1:1 criterion-per-rule-id mapping) when a diff introduces several rule ids
in one change.

### Waive boundary (T-0101, revised T-0289)

`frob:waive` only ever suppresses entries in a `GateReport`'s `violations`
tuple -- `_apply_waivers` matches a waiver's target against `Violation.rule`
and can never see anything that isn't a `Violation`. `frob check`'s
`frob-arch` tool stage calls `frob.arch.analyze_project` directly and
wraps its `ArchSuggestion`s straight into `Diagnostic`s, bypassing
`frob.gates` entirely -- `god-class`, `high-coupling`, `deep-nesting`,
`abstraction-opportunity`, and `large-file` are still only reachable that
way, so a `frob:waive` naming one of those categories is flagged as
**WAIVE002** (ineffective, ERROR since T-0753 -- was WARN; a waiver that
can never match anything is not a hygiene nit, it silently does nothing
while reading as coverage, the same "looks handled, isn't" failure mode
WAIVE001 already treats as an ERROR for a missing `reason=`).

`long-function` is the ONE exception (T-0289): `frob.gates._arch.arch_gate`
now runs `analyze_project` a second time inside the `archgate` GATE (a
distinct `frob check`/`run_gates` selection name from the `frob-arch` TOOL
stage above -- do not conflate the two) and turns every `long-function`
suggestion into a real `ARCH001` `Violation`, symref-bound to the exact
function. `ARCH001` is in `frob.gates._KNOWN_GATE_RULES`, so
`frob:waive ARCH001 reason="..." [ceiling=N]` is a real, effective,
auditable waiver -- not flagged by WAIVE002 -- while
`frob:waive long-function reason="..."` (the bare category name) still is,
since that string was never a rule id `_apply_waivers` could match.

Any rule id that is simply a typo or a rule that was never registered is
also flagged as WAIVE002 the same way. `frob.gates._KNOWN_GATE_RULES`
(plus the run's loaded `[policy]` rule ids) is the whitelist; anything
outside it is presumed unwaivable. If a future change makes another arch
category waivable, remove it from `_unwaivable_channel_rules`'s returned
set the same way `long-function` was removed, and update this note.

### COV006/COV007 (T-0483)

T-0297 shipped candidate (a) of a three-part COV idea as COV005 (a
directive silently rebound onto a private helper by an extraction).
Candidates (b) and (c) landed here as COV006/COV007:

- **COV006** (warn): a `frob:tests` edge bound to a PRIVATE symbol whose
  named test has no reachability to it in `frob.graph.callgraph`
  (T-0288/T-0290's shared call-graph substrate -- reused as-is, not a
  second traversal implementation). Restricted to PRIVATE targets only:
  `build_call_graph` never records an edge to a PUBLIC callee by
  construction (the mechanism dup/perf rely on to stop expanding at the
  public-API boundary for free), so checking a public target would ALWAYS
  report "unreachable" regardless of whether the test genuinely exercises
  it -- unsound, not merely noisier, which is why COV006 skips it
  entirely rather than caveat it.

  **Known false-positive shape, disclosed rather than tuned away**: a
  test that reaches its bound private helper only INDIRECTLY, via a
  PUBLIC entry point in the same file that itself calls the helper, is
  reported unreachable -- there is no edge for that first hop at all
  (public callees are never edges), so `closure` can never walk through
  it. This is the single most common COV006 finding on this repo's own
  suite today (many `frob:tests <private-helper>` bindings whose test body
  only calls the public gate/wrapper function). It is not a traversal bug;
  `frob.graph.callgraph`'s public-boundary-stop behavior is load-bearing
  for its other two consumers and is used unmodified here. Warn severity
  reflects exactly this: a COV006 finding is a prompt to double check, not
  proof the binding is wrong -- expect a real "adoption cliff" wave of
  these on first landing in any repo with this test-via-public-wrapper
  idiom, same as any other warn-tier gate here.

  **T-0506 update**: the most common shape above is now rescued rather
  than merely disclosed. `_cov006_public_wrapper_reachable` does a
  gate-local, one-hop lookahead: if a PUBLIC symbol in the bound
  target's own file both calls that target directly and is itself
  called, by name, from the test's own body, the binding is accepted
  without ever recording a public-callee edge in the shared `CallGraph`
  (`frob.dup`/arch's public-boundary-stop guarantee stays untouched).
  Reduced this repo's own COV006 count from 98 to 89 on landing; the
  residual is a genuinely reviewable pool, tracked as a follow-up
  burndown ticket rather than the original disclosed "expect noise"
  posture.

- **COV007** (warn): a `frob:doc` edge whose src symbol is PRIVATE. Doc
  anchors normally cover the public API surface (COV001 only ever asks
  for one on a PUBLIC symbol), so one on a private helper is usually
  either a directive that rode along onto the wrong symbol after an
  extraction (COV005's failure mode, just discovered post hoc instead of
  diff-scoped) or documentation that belongs on the public caller instead.
  Warn, not error: a private helper can legitimately warrant its own doc
  anchor (a genuinely complex internal algorithm), and this repo's own
  code has real examples of that (`frob.logging._FrobFormatter`,
  `frob.gates._pii_structural._FieldSignature`) -- COV007 flags the
  pattern for a human decision, it does not forbid it.

### PLACE001 (T-0504)

<!-- frob:describes src/frob/gates/__init__.py::_place001_missed_symbol -->
<!-- frob:describes src/frob/gates/__init__.py::_place001_bindings -->

T-0470 first prototyped a class-directive placement lint as "distance
from the class's own span start" and DELIBERATELY DROPPED it before
landing: that heuristic fires on this repo's own widespread, legitimate
idiom of a per-field `frob:waive`/`frob:ticket` comment documenting one
field deep inside a large pydantic config class (`AppConfig`'s
`frob:waive SCOPE001`, 150+ lines past the class's own `class AppConfig:`
line) -- fields are not `RawSymbol`s, so a directive above one always
falls back to the enclosing class by construction, and doing so far from
the class top is completely intentional there, not mis-scoped.

PLACE001 replaces raw distance with a materially different signal: does
a nearby REAL symbol exist that the directive plausibly should have
bound to via `following` but didn't reach, with nothing but blank
lines/comments/decorators in the gap? `_place001_missed_symbol` answers
this directly -- the per-field idiom always has genuine field-assignment
CODE in that gap (that is what makes it a field, not a stray comment),
so it can never produce a "missed" candidate regardless of how close or
far the class's next real method sits; a directive separated from its
intended `def` by one blank line too many (or an extra decorator, or a
too-long stacked-comment run) always does.

**The subtle trap this check had to avoid**: a `frob:doc`/`frob:ticket`
comment placed directly above `class Foo:` resolves via `following`
straight to `Foo` -- correct and universal across this repo -- even
though `Foo` IS a class. Naively checking "did this resolve to a class
symbol" cannot tell that apart from a directive genuinely stuck at the
class-fallback (sitting somewhere inside the class body with no
reachable `following` target at all). `_place001_bindings` mirrors
`frob.graph.dsl._resolve_block_srcs`'s exact stacked-comment-propagation
algorithm but additionally tags whether each binding was reached via a
`following` match (direct, or propagated backward through an unbroken
comment run, T-0313) versus a genuine `enclosing` fallback -- PLACE001
only ever considers the latter. An earlier draft of this gate skipped
that distinction and fired ~400 findings across this repo, almost all on
the ordinary "directive directly above its class" idiom; with it in
place the finding count on this repo's own tree is zero (the corpus is
clean), proven non-vacuous instead by `TestPlace001Gate`'s constructed
positive case.

WARN severity: best-effort, name/position-based (same tier as COV006) --
a finding is a prompt to double check, not proof the directive is wrong.

### Waiver over-breadth (T-0470)

`_match_waiver`'s directory-prefix fallback (T-0276, see the comment
above `_match_waiver` in `src/frob/gates/__init__.py`) exists because
TEST003/TEST004/TEST007's `Violation.file` is a package or system id
(`crates/foo/src`, `[[system]] my-sys`), never a real leaf file -- no
real source path can ever equal that string, so without the fallback no
placement of a waiver could ever match it. That reach is now gated to an
explicit allowlist, `frob.gates._PACKAGE_SCOPED_RULES = {TEST003, TEST004,
TEST007}` -- it used to run for every symref-less violation regardless of
rule, on the assumption that no other rule's `file` is ever directory-
shaped. Any future rule that reuses a bare directory/virtual id as `file`
must be added to that set deliberately; it no longer inherits unbounded
prefix reach as a side effect of having no symref.

Even correctly gated, the prefix fallback has a real over-breadth shape:
a waiver written in one file reaches every ANCESTOR package prefix of that
file's own path too (a waiver in `src/frob/pkg/sub/deep.py` matches a
TEST003 finding against `src/frob/pkg/sub` AND against `src/frob/pkg`
simultaneously), which is almost always broader than the author was
reasoning about when they wrote it. **WAIVE003** flags any single waiver
that reaches more than one distinct violated package/system id this way
-- the fix is to split it into one waiver per package, or move each to
that package's own file.

A second prong was investigated for this ticket -- warning when a
class-bound directive of any verb is not near the class's own top,
on the theory that a directive with nothing recognizable following it
(`frob.graph.dsl._enclosing_src`'s fallback to the ENCLOSING symbol) and
sitting far from the class start was probably meant for a nested member.
That heuristic was prototyped and DROPPED before landing: it fires
constantly on this repo's own real, intentional idiom of a per-field
`frob:waive`/`frob:ticket` comment documenting one field deep inside a
large pydantic config class (fields are not `RawSymbol`s, so a directive
above one always falls back to the enclosing class, by design, however
far into the body it sits -- e.g. `src/frob/app/config.py`'s `AppConfig`
carries several such comments 150+ lines past its `class AppConfig:`
line, none of them mis-scoped). A real version of this check needs a
different signal than raw line-distance from the class top; tracked as a
follow-up rather than shipped as a lint proven noisy against the repo's
own pattern.

### Unnecessary-waiver detection (T-0753)

WAIVE002 only catches a waiver whose RULE ID can never match anything at
all. It cannot see the other, more dangerous stale-waiver shape: a waiver
naming a perfectly real, live rule, but whose SITE currently produces zero
findings under that rule -- the underlying issue was already fixed (or
never actually applied there), and the waiver just keeps standing guard
over nothing while silently pre-forgiving the NEXT regression at that site
with no new review ever happening. **WAIVE004** is that detector:
`frob.gates._waive004_violations` re-runs `_match_waiver` for every
recognized-rule `frob:waive` edge against this run's full, pre-waiver
violation set (the same set `_waive003_violations` already consumes) and
fires when nothing matches.

WARN tier, not error: some rules are legitimately context-dependent, so a
zero-match result does not always mean the waiver is stale --

- **`--only`/gate-selection scoping**: `frob check --only gates-fast`
  excludes `dead_symbols` entirely, so every genuinely-needed
  `frob:waive DEAD001 reason="..."` in the tree reports 0 findings under
  `gates-fast` and would falsely WAIVE004 there. This is not a detector bug
  -- it is read against the wrong (partial) violation set. Trust WAIVE004
  findings only from a full, unscoped `frob check` run; treat a scoped
  run's WAIVE004 output as advisory only, never as a signal to remove the
  waiver.
- **Diff/base-scoped rules** (e.g. `SCOPE001`, `POLICY`-family checks bound
  to a diff base) can vary run to run for reasons unrelated to the waiver's
  own site.

A ratchet-to-error path via the T-0569/T-0594 waivable-warning pool is a
natural follow-up once the known-flaky set above is characterized
empirically across full runs -- not built in this pass; T-0753's mandate
was WARNING tier first.

### Waiver expiry (T-0753)

`frob:waive` gains an optional `until="YYYY-MM-DD"` boundary, parsed by
`frob.graph.dsl` with the exact same date-only grammar `frob:deprecated`'s
`sunset=` already established (T-0576) -- a non-`YYYY-MM-DD` `until=`
value is rejected at parse time as a WAIVE001-shaped `MalformedDirective`,
the same posture `frob:deprecated`'s malformed `sunset=` gets under
DEPR001. Coordinate with T-0671 (strata's bounded waivers): both sides
share this one date convention rather than inventing a second grammar --
strata's `SYSWAIVE002` is the analogous error-tier precedent on that side
(`src/frob/strata/_waive.py`'s `STALE_WAIVER_RULE`).

**WAIVE005** fires when a `frob:waive`'s `until` boundary has passed,
judged against the run's current date -- mirroring DEBT003/DEPR004's plain
expiry escalation (ERROR, not merely a warning: an unenforced expiry date
is not actually an expiry). Unlike `frob:debt`, a `frob:waive` carries no
`ticket=`, so there is no ticket-lifecycle check here (no WAIVE005
counterpart to DEBT002/DEPR002) -- WAIVE005 only makes the boundary itself
loud. An expired waiver still SUPPRESSES its matched violation (the point
is forcing a human re-review, not silently un-waiving something a prior
author deliberately excepted); resolve it by extending `until` with a
written reason, or removing the directive once it's no longer warranted.

### `frob check`'s dup/arch stage summaries are also waiver-aware (T-0375)

The `frob-dup` and `frob-arch` TOOL stages (`frob.check._python._run_dup`/
`_run_arch`, distinct from the `gates` TOOL stage above) never route
through `frob.gates.run_gates`, so they don't get the gates stage's
`N error, M warning, K waived` split for free. T-0375 gave each its own
cross-reference against the obligation graph's WAIVE edges (`_run_dup`:
exact fragment-symref match on DUP001/DUP002; `_run_arch`: reuses
`_apply_waivers` over ARCH001 `Violation`s built from the already-computed
long-function suggestions, `ceiling=` included) so their headlines also
report only unaccounted findings, with waived ones still listed as `note`
diagnostics -- see docs/modules/dup.md#check-stage-summary-is-waiver-aware-t-0375
and docs/modules/arch.md#check-stage-summary-is-waiver-aware-for-arch001-t-0375.
This does not change gate pass/fail behavior anywhere -- it only makes the
advisory count in `frob check`'s printed summary honest.

### TICK006 (T-0726)

<!-- frob:describes src/frob/gates/__init__.py::_tick006_phantom_filing -->

Two occurrences in one session of a Done report claiming a follow-up was
filed when no ledger block actually exists: T-0707 (an invented
filed-then-absorbed trail) and T-0615 (an invented `T-draft-*` id in
prose, never actually filed) -- both caught only by reviewer diligence,
not by any gate. TICK006 makes this mechanical: it scans every ticket's
Done-report content for an *affirmative filing claim* and ERRORs when the
claimed id resolves to no block, active or archived.

**Where it looks.** Only the substring of a ticket's `body` starting at
its first "Done report" heading (`_tick006_done_report_text`) is scanned
-- any markdown heading whose text contains "done report",
case-insensitive (`## Done report`, `### Done report`, `## Round 1 Done
report`, `## Done report (batch 8)`, ...). A ticket's Description/Plan
routinely narrates OTHER tickets' ids in ordinary prose (`"T-0570 landed
the...")`, and this repo's ledger already carries several `NOTE:
T-XXXX's Done report references this as T-draft-...; the draft did not
survive land..."` disclosures inside Description bodies (the T-0577
draft-loss bug's own paper trail) -- none of that is a filing claim
about the CURRENT ticket's own work, so scanning it would be a
false-positive generator on extremely common, legitimate prose.

**The filing-claim grammar recognized.** Any occurrence of the word
"filed" (case-insensitive, word-boundary) in the Done-report text opens a
claim window extending up to 300 characters forward (long enough to span
a wrapped `Filed: ... (description...)` line/sentence without bleeding
into an unrelated later paragraph). Every ticket-id-shaped token in that
window -- `T-\d{4}` or `T-draft-[0-9a-f]{8}` -- is checked against the
union of ids in the active queue and `tickets-archive.md`. This grammar
covers every real shape observed in this repo's own ledger: `Filed:
T-0104`, `Filed: none` (extracts no id, so never fires), `filed as
**T-0137**`, `filed as a follow-up` (no id, never fires), `Filed
T-draft-4e98abb1 (mints a real T-#### id at land)`, `Filed a new standing
ticket (drafted off-main as T-draft-05d8f716...)`. A literal `T-####`
placeholder (`#` is not `\d`) or `T-draft-XXXXXXXX` template placeholder
(`X` is not `[0-9a-f]`) never match, since neither is a real reference.

**Explicit negations.** A "filed" occurrence preceded, within 40
characters, by a negation word (`not`, `never`, `no`, `n't`) is skipped
entirely -- covers the "not filed", "no ticket filed", "never filed",
"not filed as a new ticket this pass" shapes this repo's ledger already
uses routinely for genuinely-not-filed disclosures.

**A currently-real historical wrinkle.** A `T-draft-<hex>` id that WAS a
real block in the filer's own worktree ledger at write time, but did not
survive `frob ticket land` (the T-0577 draft-loss bug, tracked
separately), resolves to nothing in the ledger a reader has today --
TICK006 fires on it, by design: the rule's contract is "does this id
resolve right now", not "was this claim honest when written". Several
such entries already exist on `main` (pre-dating TICK006). These are
expected to be dispositioned with a `frob:waive TICK006 reason="..."` per
instance naming the T-0577 draft-loss incident, not suppressed
structurally -- see the Done report for this ticket for the specific
instances found and waived at introduction time.

**Where it runs.** TICK006 is one of `tickets_gate`'s checks (alongside
TICK001-TICK005), which runs inside `frob check`'s `tickets` stage --
including `frob ticket close` and `frob ticket land`'s preflight -- so a
phantom filing trail cannot reach `main` undetected going forward. It is
waivable (not in `_UNWAIVABLE_RULES`): unlike TICK001/TICK002, a genuine
draft-loss disclosure is a legitimate, honestly-dispositioned case, not a
silent invariant break.

**T-0929 (perf, no behavior change).** `_tick006_phantom_filing` no
longer loads `tickets-archive.md` itself -- `tickets_gate` now loads it
ONCE and passes the `archived` `Result` down to `_tick001_duplicate_ids`/
`_tick003_stale_archive`/`_tick006_phantom_filing` alike, closing a
same-shape redundant-parse gap the T-0928 check-performance audit found
inside a single gate (docs/audits/check-performance.md row 10). Purely
an internal signature change; TICK006's own detection contract above is
unaffected.

### TICK007 (T-0820)

<!-- frob:describes src/frob/gates/__init__.py::_tick007_undispatched_stale -->

T-0752 built the pure staleness-alarm computation
(`frob.tickets.undispatched_stale`/`dispatch_stale_hours`/
`_dispatch_stale_thresholds`) and wired it into `frob ticket doable`'s
human-facing row rendering (a loud UNDISPATCHED marker) -- but that only
surfaces the alarm to someone who happens to run `doable` and read it.
T-0820 is the `frob check` half of the same signal: `tickets_gate` calls
`undispatched_stale` (imported and reused verbatim, per T-0752's own
Done-report note that the staleness judgment must live in exactly one
place -- this gate does not re-derive it) over the doable set filtered to
non-in-flight (`has_live_lease`) rows, and emits one WARN `Violation` per
alarmed ticket.

**Thresholds.** Same `[tickets]` `frob.toml` table T-0752 defined
(`dispatch_stale_critical_hours`/`dispatch_stale_high_hours`), defaulting
to 4h (CRITICAL) / 24h (HIGH). MEDIUM/LOW never alarm, matching T-0752's
mandate that "a queue always has some" at those priorities.

**Where it runs.** TICK007 is one of `tickets_gate`'s checks (alongside
TICK001-TICK006), which runs inside `frob check`'s `tickets` stage --
including `frob ticket close` and `frob ticket land`'s preflight. It is
waivable (not in `_UNWAIVABLE_RULES`): unlike TICK001/TICK002, a stale
dispatch is a queue-health signal to act on, not a structural invariant
break, so a reasoned `frob:waive TICK007 reason="..."` can disposition a
known, accepted case (e.g. a deliberately deferred CRITICAL awaiting a
blocker that has not been formally recorded yet).

### TICK008 (T-0842)

<!-- frob:describes src/frob/gates/__init__.py::_tick008_unknown_ledger_fields -->

T-0838 made `Ticket` `extra="allow"` (not `extra="forbid"`) so a ledger
written by a NEWER `frob` binary -- one that has added a field this
binary's `Ticket` does not know about yet -- loads instead of hard-failing
`MalformedFrontmatter`; unknown keys land in `__pydantic_extra__`, are
logged at WARNING (`_warn_unknown_extras`), and round-trip verbatim on the
next dump. That reviewer-caught disclosed cost: a TYPOED known field
(`priorty: low`) is indistinguishable from a genuinely-newer field at load
time -- it silently becomes an extra, the intended value is lost to the
schema default, and the only signal was that same WARNING log line, which
no gate read. TICK008 makes that drift visible mechanically: for every
ticket in the checked ledger with a non-empty `__pydantic_extra__`,
`tickets_gate` emits one WARN `Violation` per unknown field, naming the
ticket id and the field, plus a `difflib.get_close_matches` fuzzy hint
against `Ticket.model_fields` when a likely intended field name exists
(`unknown field 'priorty' -- did you mean 'priority'?`).

**Why WARN, not ERROR.** An initial ERROR pass was the original design
and was REJECTED in adversarial review of T-0842 itself -- worth stating
explicitly so a future "promote to ERROR" attempt re-derives the same
constraint rather than re-discovering it the hard way. `frob ticket
land`'s claim re-verification (`_reverify_done_report_claims_post_merge`)
spawns `frob check --ticket <id>` via `sys.executable` from the ROOT
checkout's venv -- the ROOT binary's OLD `src` tree (the playbook's
"Gate-affecting source only takes effect via `uv run frob`" stale-binary
hazard, one level up: it applies to `frob ticket land`'s own subprocess,
not just to a human running a stale global `frob`). While a schema-
extending ticket is ITSELF being landed, the root binary's `Ticket` model
does not yet know the new field that very ticket is landing -- a
populated new field on that ticket's own block gets captured as
`__pydantic_extra__` by root's stale model. `tickets_gate` correctly does
NOT scope TICK008 to only the active ticket (a stale field anywhere in
the ledger is real drift worth surfacing) -- so an ERROR here fires over
the FULL merged ledger at exactly the moment the schema-owning ticket
lands, `real_errors` diverges from the worktree-captured claim, and land
refuses via `ClaimDivergence`. A `frob:waive TICK008` cannot route around
this either: the same stale root binary evaluating the gate is the one
evaluating the waiver, so the schema gap that causes the false ERROR
equally prevents the waiver from being recognized as covering it. The
original ERROR-severity docstring's claim that "there is no case where
this rule stays red once the schema catches up" is false during exactly
that land window -- "the schema catching up" IS the land event being
refused. WARN avoids this because `frob check`'s pass/fail gating (and
land's real-errors/claim-divergence comparison) keys off ERROR-severity
counts, not warnings -- a WARN still renders as a live, mechanical `frob
check` finding (the actual T-0838 review demand: visibility, not a hard
gate), matching the TICK004/TICK006/TICK007 precedent of leaving a
schema-transition/judgment-window case as WARN rather than ERROR.

**Where it runs.** TICK008 is one of `tickets_gate`'s checks (alongside
TICK001-TICK007), which runs inside `frob check`'s `tickets` stage --
including `frob ticket close` and `frob ticket land`'s preflight. It is
waivable (not in `_UNWAIVABLE_RULES`), matching the TICK004/TICK006/
TICK007 precedent: a genuinely temporary, disclosed exception (e.g. a
worktree deliberately carrying a not-yet-landed schema-extending field
across a short review window) can be dispositioned with a reasoned
`frob:waive TICK008 reason="..."` instead of blocking on it.

### COMPLIANCE005 (T-0788)

<!-- frob:describes src/frob/gates/__init__.py::compliance_gate -->

T-0607 built the pure check
(`frob.strata._compliance.check_cmpl_registry_unit_dispositions`, the
`CMPL_REGISTRY_UNIT_IDS` constant, and `check_cmpl_registry`) but did not
wire it into `frob check` -- `_KNOWN_GATE_RULES` and a stage callback both
lived outside T-0607's declared scope, so a `deferred`/undispositioned
regression among the 17 checkable-control compliance-registry units
(`docs/design/registry/compliance.yaml`) would not have failed `frob
check` at all, only a direct call to the strata function. T-0788 is the
`frob check` half: `compliance_gate` loads `compliance.yaml` from
`docs/design/registry` (or a caller-supplied `registry_dir`), calls
`check_cmpl_registry`, and emits one ERROR `Violation` per
`CMPL_REGISTRY_UNIT_IDS` member whose disposition kind is neither
`handled_by` nor `out_of_scope` -- most concretely, a `deferred:<ticket>`
disposition that becomes factually wrong the instant the named ticket
closes (the exact T-0388/T-0607 self-reference incident this rule exists
to refuse a repeat of). T-0833 flipped all 17 `compliance.yaml` entries
under `CMPL_REGISTRY_UNIT_IDS` from `out_of_scope` to
`handled_by:COMPLIANCE005`, matching T-0788's original intent.

**Where it runs.** `compliance_gate` is dispatched as the `compliance`
stage callback (`frob check`'s `gates-fast` stage group). It is silent
(returns no violations) when `registry_dir` has no `compliance.yaml` at
all -- a repo with no compliance registry makes no COMPLIANCE005 claim,
matching `registry_gate`'s own missing-directory posture. It is waivable
(not in `_UNWAIVABLE_RULES`): a reasoned `frob:waive COMPLIANCE005
reason="..."` can disposition a specific, honest, temporary exception the
same way REG001-004 allow one.

### DERIVED001 (T-0603): derived-state integrity precheck

`frob doctor`'s `verify_derived_state` (T-0570) fingerprints every entry in
`DERIVED_ARTIFACTS` (`.frob/cache.db`, `.frob/dup.db`, `.frob/vet.db`,
`.frob/coverage-stamp`, `.frob/baseline`, `frob-coverage.lock.json`) and
reports each as absent (fine, nothing written yet -- not corruption),
healthy, or present-but-corrupt (fails a format-specific validity check:
SQLite magic header, or `json.loads`). Before T-0603, this diagnosis
existed but nothing in `frob check` ever consulted it -- a truncated
`.frob/cache.db` would silently feed the graph/dup gates wrong data
instead of failing loudly, and `frob doctor` was a diagnosis nobody was
required to run.

`frob.check._derived_state_integrity_result` (`src/frob/check/__init__.py`)
closes that gap: every `run_check`/`run_check_cpp`/`run_check_rust`/
`run_check_ts` entry point calls it once, synchronously, BEFORE
dispatching any concurrent stage. If any derived artifact is
present-but-corrupt, the entire check run short-circuits to a single
`derived-state-integrity` `ToolResult` (diagnostic code `DERIVED001`,
ERROR severity) naming every corrupt artifact and the `rm -f` command to
clear it, pointing at `frob doctor` for the full diagnosis -- no gate ever
sees the corrupt cache. An absent artifact (fresh clone, `frob clean`, a
worktree that has never run `frob check`) is NOT a violation: `run_gates`
and the cache layer already know how to build a missing artifact from
scratch, so only a PRESENT-but-invalid artifact fails closed.

This is deliberately NOT one of `_KNOWN_GATE_RULES` / the `registry_gate`
rule catalog above -- it is a check-orchestration-level precondition (the
same tier as a tool being unavailable), not a `Violation` a `frob:waive`
can target, so it stays unwaivable by construction: a corrupt cache is
never a legitimate, intentional state to accept.

**Why the check runs once, up front, rather than from inside the `gates`
stage itself.** `arch`, `dup`, and `gates` all read or rebuild the same
`.frob/cache.db`/`dup.db` inside `frob check`'s `ThreadPoolExecutor`
batch. Fingerprinting from inside one of those stages while the others
run concurrently races a live writer: a cache mid-rebuild, observed by
another thread, reads as "corrupt" (truncated/incomplete bytes) when it
is merely momentarily in-progress. This was caught for real during T-0603
development by `TestCheckBuildsGraphOnce.test_run_check_calls_build_graph_
exactly_once` turning red once the precheck lived inside `_run_gates`;
moving it to run once, serially, before any stage is dispatched removes
the race entirely and is also strictly cheaper (one fingerprint pass per
`frob check` run instead of one per gate family).

## AFFECT001 AFFECT002 (T-0628)

<!-- frob:describes src/frob/gates/__init__.py::affect_drift_gate -->

T-0325 landed `frob.graph.affects.affects` (docs/modules/graph.md#affects)
-- the warm, test-free query answering "if X's digest changed, exactly
WHICH documentation and WHICH other code must be reviewed/updated" -- but
explicitly cut its enforcement half as future work. `affect_drift_gate`
(gate name `affect_drift`, `gates-fast` stage group) is that enforcement:
for every symbol the working diff touches (`_touched_symrefs`, the same
helper `coverage_gate`/`policy_gate` use), it walks that symbol's
`affects()` closure and fails when

- a dependent doc anchor (`frob:doc`/`frob:describes`) names a file NOT
  also touched anywhere in the same diff (AFFECT001), or
- a dependent symbol (reached via a `uses-contract` chain) lives in a file
  NOT also touched anywhere in the same diff (AFFECT002).

Both are ERROR, unwaivable by default like the rest of the drift family
(waivable via the ordinary `frob:waive AFFECT001/AFFECT002 reason="..."`
channel if a change genuinely does not need its dependent updated). A
symbol whose `affects()` closure is empty (no `uses-contract` dependents,
no doc/test edges at all) is silent -- there is nothing that could have
drifted. A closure `affects()` itself reports `truncated=True` for
(`max_depth`/`max_nodes` cut the walk short) is still checked against
whatever it DID visit: the gate under-reports on a truncated closure
rather than false-positiving on nodes it never saw.

"Touched" is file-granular, not line/hunk-granular -- a dependent doc or
symbol only needs SOME hunk anywhere in its file to clear the gate, not a
hunk overlapping its own span. This mirrors `coverage_gate`'s COV002 scope
grace posture (a file-level touch accounts for its whole contents) rather
than requiring a caller to prove the exact line changed; the query-side
`frob graph affects <ref>` CLI (docs/modules/graph.md#affects) is the tool
for a developer to see precisely what the gate is asking about.

## EXHAUST001 EXHAUST002 (T-0688)

<a id="exhaust001exhaust002-t-0688"></a>
<!-- frob:describes src/frob/gates/_exhaustive_handling.py::exhaustive_handling_gate -->

Child 3 of T-0685's exception may-raise umbrella, over T-0686's
per-function may-raise resolver (`frob.arch._mayraise.compute_may_raise`,
docs/modules/arch.md#may-raise-resolver): `exhaustive_handling_gate` (gate
name `exhaustive_handling`, `gates-native` stage group, `--only
gates-native`) is the fail-closed exhaustiveness half over that resolver's
output, a static-type-checker-for-exceptions check that runs before a
single test does.

A function/method is treated as a declared BOUNDARY only once it has at
least one `except`/`catch` clause of its own (`NormalizedFunction.
catches`) -- a plain function with no attempt at handling is just
propagating, which is normal and not this gate's concern.
`compute_may_raise`'s `FunctionMayRaise.raises` is already the LEAKED
remainder after that function's own catches are subtracted (see that
resolver's own docstring), so any non-empty leaked set on a boundary is,
by construction, an incompletely-handled one:

- **EXHAUST001** -- `UNKNOWN` (an unresolvable call/raise, per the
  resolver's fail-closed doctrine) is in the leaked set and none of the
  boundary's own catches is broad enough to plausibly discharge it (a bare
  `except:` or `except Exception:`). Per the parent ticket's own
  acceptance: `Unknown` in the guarded set forces a catch-all or fixing
  the unresolvable call; a narrow `except ValueError:` never counts.
- **EXHAUST002** -- a named, non-`UNKNOWN` type is in the leaked set with
  no matching `# frob:raises <ExceptionType>` directive (below) declaring
  it as intentional propagation. The violation message names exactly the
  missing type(s).

Both rules ship at WARN severity as of this landing (T-0688) -- a first
real run against this repo's own source surfaced 176 pre-existing
findings, the same first-turn-on-debt scale T-0680's REG008-REG011 and
T-0728's ARCH101-103 both disclosed for their own new gates; promoting to
ERROR is deliberately deferred to a follow-up ticket that pays that corpus
down first, not a softened design. Both attach `symref` (the leaking
function's `path::qualname`) so `frob:waive EXHAUST001 reason="..."` /
`frob:waive EXHAUST002 reason="..."` bind precisely to that one function,
the same waiver-precision convention every other symbol-scoped rule uses.

**Declared propagation directive**: `# frob:raises <ExceptionType>`,
placed directly above the function's `def`/decorator block (the same
above-the-def placement every other `frob:` directive in this repo
already uses), marks that the function intentionally lets
`<ExceptionType>` escape uncaught -- an explicit, auditable contract
instead of a silent EXHAUST002 gap. One directive line per declared type;
`_declared_propagations` scans a bounded lookback window directly above
the function's start line (`NormalizedFunction` itself carries no raw
comment text, so this is a raw-source scan, not a model field). A
directive never discharges `UNKNOWN` -- it names a KNOWN type, and
`UNKNOWN` is definitionally not one.

**Naming note (T-0931).** This is the ONLY convention that owns the verb
text `frob:raises`. A different, unrelated same-line call-site directive
(`NormalizedCall.declared_raises`, docs/modules/arch.md#may-raise-resolver)
was originally also named `frob:raises` when T-0689 landed concurrently
with this ticket; T-0931 renamed that call-site form to
`frob:callee-raises` to keep the two unambiguous -- this above-the-def,
function-wide form keeps `frob:raises` unchanged. T-0690's planned
FFI-boundary declarations extend this same above-the-def convention, not
the call-site one.

SCOPE: python-only (same disclosed limit `compute_may_raise` itself
already carries); non-python files, files with no tree-sitter grammar, and
test files (`frob.excludes.is_test_file`) are silently skipped.

### errors-as-values advisory (T-0688)

<a id="errors-as-values-advisory-t-0688"></a>
<!-- frob:describes src/frob/arch/_exceptions.py::check_errors_as_values -->

The sibling, suggestion-severity consumer of the SAME `compute_may_raise`
output (`frob.arch._exceptions.check_errors_as_values`), wiring into
T-0623's fallibility family (docs/modules/arch.md#fallibility-checks): a
PUBLIC function/method (bare name not underscore-prefixed) whose leaked
may-raise set contains a member of the curated recoverable set
(`ValueError`/`KeyError`/`LookupError`/`TypeError`, the same four types
`frob.arch._fallibility._RECOVERABLE_EXCEPTION_TYPES` already curates),
with no same-module caller visibly discharging it (a caller with a
wrapping `except` clause that is a catch-all or names one of the
recoverable types directly -- a disclosed coarse, function-wide,
exact-type-or-catch-all proxy, not a subtype-hierarchy walk), gets an
`ArchSuggestion` (category `errors-as-values-recommended`) recommending a
typani `Result[T, E]` signature instead, with the raising function as the
sketch site. `UNKNOWN` and non-recoverable (programmer-bug-class)
exception types never trigger this advisory -- exceptions remain
sanctioned for those, per T-0623's own house doctrine.

T-0972: the message-formatting `sorted(recoverable)` call inside this
function's per-function loop now carries a reasoned `frob:waive PERF004`
(the set differs every iteration, so there is nothing to hoist) -- no
behavior change.

Like `frob.arch._fallibility.run_fallibility_checks` before it,
`check_errors_as_values` stays on the unwaivable advisory channel every
`ArchCategory` lives on by default (`frob.gates._unwaivable_channel_
rules` picks up the new category automatically) and is not yet dispatched
by `analyze_project`'s live per-file walk -- wiring the whole fallibility
family into that dispatch loop is a distinct, larger-surface follow-up
ticket (T-0616's SRP-family precedent: built and tested first, dispatch
wiring landed later as its own ticket, T-0728), not something this ticket
silently folds in.

## Public API

<!-- frob:describes src/frob/gates/__init__.py::SCOPED_RUN_FLAKY_RULE_IDS -->
<!-- frob:describes src/frob/gates/__init__.py::run_gates -->
<!-- frob:describes src/frob/gates/__init__.py::evidence_covers_scope -->
<!-- frob:describes src/frob/gates/__init__.py::drift_gate -->
<!-- frob:describes src/frob/gates/__init__.py::affect_drift_gate -->
<!-- frob:describes src/frob/gates/__init__.py::coverage_gate -->
<!-- frob:describes src/frob/gates/__init__.py::scope_gate -->
<!-- frob:describes src/frob/gates/__init__.py::prework_gate -->
<!-- frob:describes src/frob/gates/__init__.py::invariant_gate -->
<!-- frob:describes src/frob/gates/__init__.py::test_gate -->
<!-- frob:describes src/frob/gates/_coverage.py::stamp_coverage -->
<!-- frob:describes src/frob/gates/_coverage.py::load_coverage -->
<!-- frob:describes src/frob/gates/__init__.py::active_ticket -->
<!-- frob:describes src/frob/gates/_prework.py::record_prework -->
<!-- frob:describes src/frob/gates/_prework.py::sweep_ticket -->
<!-- frob:describes src/frob/policy/__init__.py::load_policy -->
<!-- frob:describes src/frob/policy/__init__.py::policy_gate -->
<!-- frob:describes src/frob/gates/invariants.py::load_invariants -->
<!-- frob:describes src/frob/gates/_coverage.py::load_stamp -->
<!-- frob:describes src/frob/gates/_prework.py::load_prework -->
<!-- frob:describes src/frob/gates/__init__.py::scope_digest -->
<!-- frob:describes src/frob/gates/__init__.py::decisions_gate -->
<!-- frob:describes src/frob/gates/__init__.py::dup_gate -->
<!-- frob:describes src/frob/gates/__init__.py::release_gate -->
<!-- frob:describes src/frob/gates/__init__.py::fuzz_gate -->
<!-- frob:describes src/frob/gates/__init__.py::doclink_gate -->
<!-- frob:describes src/frob/gates/__init__.py::docanchor_gate -->
<!-- frob:describes src/frob/gates/__init__.py::run_gates -->
<!-- frob:describes src/frob/gates/_baseline.py::stamp_baseline -->
<!-- frob:describes src/frob/gates/_baseline.py::load_baseline -->
<!-- frob:describes src/frob/gates/_baseline.py::is_baseline_stale -->
<!-- frob:describes src/frob/gates/_baseline.py::delta_violations -->
<!-- frob:describes src/frob/gates/_baseline.py::violation_fingerprint -->
<!-- frob:describes src/frob/gates/_secrets.py::secrets_gate -->
<!-- frob:describes src/frob/gates/_secrets.py::_redact -->
<!-- frob:describes src/frob/gates/_secrets.py::fake_marker_staleness_gate -->
<!-- frob:describes src/frob/gates/_pii_structural.py::pii_structural_gate -->
<!-- frob:describes src/frob/gates/_pii_structural.py::_FieldSignature -->
<!-- frob:describes src/frob/gates/_pii_structural.py::_scan_python_fields -->
<!-- frob:describes src/frob/gates/_pii_structural.py::_scan_python_env_access -->
<!-- frob:describes src/frob/gates/__init__.py::known_gate_rule_ids -->

- `load_stamp` -- the raw `.frob/coverage-stamp` document, or `None` if
  never stamped/unreadable; TEST006 compares it against live file hashes.
- `load_prework` -- the recorded pre-work sweep for a ticket, or `None` if
  `frob ticket start` never ran one; PRE001 compares it to a fresh digest.
- `scope_digest` -- the one canonical sha256 over a scope glob's matched
  file hashes, shared by `frob ticket start` and `prework_gate` so PRE001
  can never see two independently-computed digests drift apart.
- `decisions_gate` -- DEC001/DEC002 over `decisions/` records and their
  code anchors; a no-op when no `decisions/` directory exists.
- `dup_gate` -- DUP001/DUP002: flags a diff that introduces a clone of an
  existing symbol; opt-in via `[dup].enforce` in `frob.toml`. T-0399: if
  `enforce` is true but the `frob-core` native extension is unavailable,
  emits DUP003 (ERROR) instead of silently skipping -- a requested-but-
  unavailable control fails closed, not open. T-0974: also reads
  `[dup].native_rungs` (default false) and threads it into the
  `DupConfig` it builds, independently of `enforce` -- when false, the
  gate's `find_clones` call only runs R1/R2 (cheap, pure-Python); R3/R4/R5
  (native-call-per-symbol, the cost driver a whole-snapshot cold run pays)
  stay off until a repo opts in. See `docs/modules/dup.md`'s
  "[dup].native_rungs" section for the measured cost and
  `frob.dup.DupConfig.native_rungs_enabled`'s docstring for why the class
  default differs from the gate's toml default.
- `release_gate` -- REL001: the public-API change since the last release
  stamp demands a version bump the declared version does not cover.
- `fuzz_gate` -- FUZZ001..003 over the `[fuzz]` policy; opt-in via
  `[fuzz].enforce`, default off.
- `doclink_gate` -- DOC001: a doc file nothing links to (no describes
  anchor, no `frob:doc` edge, unreachable from the doc roots) is an error.
- `sys_gate` -- SYS001/SYS002/SYS003/SYS004 (T-0080): joins `frob:channel`/
  `frob:boundary`/`frob:secret` code directives and tier-2 code binding
  against a `.strata` design model; opt-in via a `design/` (or
  `[strata].design_dir`) directory of `.strata` files existing, same
  posture as `decisions_gate`. See docs/strata/surface.md#directives-t-0080.
- `docanchor_gate` -- DOC002: a `frob:doc` target whose anchor doesn't
  resolve (missing `#anchor`, missing file, or `<slug>` matches neither a
  heading slug nor an explicit `<a id>`) is an error.
- `secrets_gate` -- SEC001/SEC002/SEC003 (T-0157): scans every git-tracked
  file (never untracked/`.env`-skipped -- a tracked `.env` IS the SEC002
  finding) for real-looking provider credentials via a per-provider regex
  table; default-on. `redact` is the one function allowed to turn a matched
  token into printable output (`<provider prefix>... (<N> chars)`, never
  the token itself). A site is exempted by a placeholder shape inside the
  token (`XXXX`/`****` runs, or the words fake/changeme/example/placeholder)
  or by a `frob:secret-fake` marker comment on the same or preceding line
  -- deliberately NOT the pre-existing `frob:secret <construct-id>`
  directive, which already binds code to a strata design's Secret-clearance
  node id; see `frob.gates._secrets`'s module docstring for the full
  reasoning. `SEC003` (live Stripe secret keys, PEM private-key headers) is
  in `_UNWAIVABLE_RULES` alongside `TEST008`; `SEC001`/`SEC002` stay
  waivable with a written reason like every other rule.
- `fake_marker_staleness_gate` -- WAIVE004 (T-0978): zero-findings
  staleness for the `frob:secret-fake reason="..."` marker family, at the
  GATE level rather than the graph-edge level -- `frob:secret-fake` stays
  a reserved, DSL-invisible marker verb (T-0157,
  `frob.graph.dsl._RESERVED_MARKER_VERBS`) that never becomes a real
  `frob:waive` `Edge`, so `frob.gates._waive004_violations`'s graph-edge
  detector cannot see it. This gate re-scans every tracked file's REAL,
  reason-bearing marker sites (excluding prose mentions and a documented
  set of test files that construct marker text as a multi-line Python
  string literal, defeating this check's physical-line site mapping --
  see `_STALENESS_MULTILINE_LITERAL_EXCLUDED_FILES`'s comment) and emits a
  `WAIVE004`-rule `Violation` for any whose site trips zero real SEC00x
  patterns AND does not look email-shaped (`_plausibly_still_needed`, a
  conservative substring stand-in for PII011's real structural check,
  since this marker family is shared between `secrets_gate` and
  `pii_structural_gate`'s PII011). `run_gates` folds its output into the
  same `all_violations` set the graph-edge WAIVE004 pass feeds, so both
  sources present as one `WAIVE004` rule to a caller.
- `run_gates` -- the single entry point: loads all state once, then runs
  the selected gates in parallel and merges/severity-overrides the result.
- `known_gate_rule_ids` -- every rule id a gate can emit (T-0499), the
  live set strata's `caught_by` verification (THREAT006, COMPLIANCE004)
  needs to recognize a rule-id-shaped reference (e.g. `SEC001`) instead of
  treating it as unresolved fail-closed; threaded into
  `evaluate_exhaustiveness`/`evaluate_compliance` from `frob sys audit`'s
  `_evaluate_audit` (`frob.app.sys_runner`).

### Structural PII secrets detection T-0207

`frob.gates._pii_structural` -- `pii_structural_gate` (gate name
`pii_structural`, default-on, WARN severity, dial via `[gates.severity]`).
Extends `frob.strata._pii` (T-0154, declaration/join layer) and
`frob.gates._secrets` (T-0157, tracked-file token scan) with a THIRD,
previously-missing layer: structural observation of actual Python data
structures and env-var access sites, drawn from
`docs/design/secrets-pii-corpus.md`'s field-name/type keyword catalog.

- **PII010**: a pydantic `BaseModel` / `@dataclass` / `TypedDict` /
  `NamedTuple` / attrs class field whose NAME (`_`-tokenized match) or TYPE
  ANNOTATION (`EmailStr`, `SecretStr`) matches an entry in
  `FieldSignature`/`FIELD_SIGNATURES` fires -- deny-by-default, waivable via
  `frob:waive PII010 reason="..."`.
- **SEC110**: an `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)`
  call/subscript site fires -- an unmapped secret-source observation,
  waivable via `frob:waive SEC110 reason="..."`.
- **T-0973**: SEC110 was promoted from WARN to ERROR in `[gates.severity]`
  (`frob.toml`) after every one of the 16 unwaived findings named in
  T-0399's gates-quality audit was disposed of -- 13 got a reasoned
  `frob:waive SEC110 reason="..."` (behavior flags, internal reentrancy/
  worker-log markers, cache paths, and test-only synthetic vars, none of
  them a real secret), and 3 more (`src/frob/gates/__init__.py`'s
  `_rel001_bump_suppressed_under_agent` and its worker log-level markers)
  were folded into the same fix once T-0973's scope was extended to that
  file. `tests/test_gates.py::TestSeverityOverrides.
  test_sec110_promoted_to_error_gates_a_real_repo_toml` is the before-
  fails/after-passes fixture proving the promotion actually gates.
- Both rules are file-scoped (same waiver-matching mode as SEC001-003:
  `violation.symref` is `None`, so a waiver anywhere in the file suppresses
  every hit in it).
- Self-match exclusion (T-0201 lesson): `_pii_structural.py`'s own path is
  hardcoded-excluded from the scan, so `FIELD_SIGNATURES`'s own keyword
  string literals can never be misread as a scanned field.
- **PII010 also covers DB/DDL schema scanning (T-0348, family 2)**:
  sqlalchemy ORM declarative `name = Column(...)` assignments and alembic-
  style positional `Column("name", ...)` calls (`_scan_orm_columns`), plus
  raw-SQL `CREATE TABLE(...)` column lists embedded in tracked-`.py`
  string literals (`_scan_ddl_strings`) -- both matched against the same
  `FIELD_SIGNATURES` table, no second registry. Schema headers are the
  highest-value PII surface per the umbrella ticket body.
- **PII011 (T-0349, family 4): structural email-shape value detection**:
  every string-literal constant in a tracked `.py` file, checked via
  `email.utils.parseaddr` (an RFC 822 header parser) plus a plain
  character-set validation of the parsed local/domain parts
  (`_is_email_shaped`) -- explicitly NOT a regex, per the ticket body's
  mandate. Escaped by a `frob:secret-fake` comment on the literal's own
  line or the line directly above it, the same T-0157 marker convention
  the secrets scanner uses (a fixture literal discharges both gates with
  one comment).
- **PII012 (T-0350, family 5): keyword-sweep at suggestion severity**:
  every plain identifier (variable/parameter/function name) and every
  `#`-comment word token matching a `FIELD_SIGNATURES` name-kind keyword,
  excluding sites PII010 already reports on. Fires at WARN severity only
  -- "no hard fail on names alone" per the ticket body -- distinct from
  PII010's deny-by-default posture over an actual declared data-structure
  field.
- **std.pii/std.secrets declaration join (T-0351)**: `_load_declared_
  surface` loads every `.strata` design file under the repo's design
  directory (the same loader `sys_gate` already uses, `load_design_ids`),
  tier-2 code-binds each file to its owning `Node` (`bind_code`, also
  reused from `sys_gate`'s SYS003), and joins that node's `carries` PII
  tags (`frob.strata._pii.node_pii_tags`) and `clearance == "Secret"`
  status (the same best-effort std.secrets proxy
  `_design_load.DesignIds.secrets` already documents) into a
  `_DeclaredSurface`. A PII010 finding whose file is already code-bound to
  a node that `carries` the SAME category is discharged outright; a
  SEC110 finding whose file is code-bound to a Secret-clearance node is
  likewise discharged. A repo with no design directory (or no matching
  binding) degrades to the empty surface -- every finding still fires
  exactly as before this ticket, waiver-only. PII011 (bare string-literal
  values have no "owning field" to carry a category against) and PII012
  (already suggestion-severity, not deny-by-default) are NOT joined.
- **Deliberately not built this pass** (see `_pii_structural.py`'s module
  docstring and this ticket's Done report): non-Python language
  equivalents and non-Python DDL sources (`.sql` migration files). Filed
  as follow-on tickets, not silently dropped.
- **TypeScript/Rust field-shape and env-access equivalents (T-0352)**:
  extends the SAME PII010/SEC110 rule ids (not new rule ids) to the other
  two `frob.lang`-supported grammars, via `frob.lang.raw_tree` (the same
  single tree-sitter grammar-load dispatch `frob.arch`/`frob.dup._legacy`
  already share -- no second parser stood up):
  - PII010 over TS `interface_declaration` bodies, `type_alias_
    declaration`s whose value is an `object_type`, and `class_declaration`
    bodies (`_scan_ts_fields`), and Rust `struct_item` named fields
    (`_scan_rust_fields`) -- reusing `_field_name_hit`/`FIELD_SIGNATURES`
    (name-kind entries) unchanged.
  - SEC110 over TS `process.env.NAME`/`process.env["NAME"]` and
    `import.meta.env.NAME`/`import.meta.env["NAME"]` (`_scan_ts_env_
    access`), and Rust `std::env::var(...)`/`env::var(...)`/`std::env::
    var_os(...)` (`_scan_rust_env_access`) -- reusing `_ENV_VAR_ALLOWLIST`
    unchanged.
  - NO-FAIL-SILENT: a field shape that cannot be statically named -- a TS
    index signature (`[key: string]: T`) or computed property name
    (`[expr]: T`) -- fires PII010 as an "unresolvable field shape" finding
    demanding manual review, rather than being silently skipped. A
    dynamic (non-literal) env-access subscript key (`process.env
    [someDynamicKey]`) likewise still fires SEC110, mirroring
    `_scan_python_env_access`'s existing posture for `os.environ
    [dynamic_key]`.
  - A Rust TUPLE struct (`Point(i32, i32)`) has no source field names at
    all and is out of scope for name-based matching (no name to check
    against `FIELD_SIGNATURES` in the first place -- not a false negative
    on a real PII field, just nothing nameable to test).
  - The T-0351 declared-surface join (`_load_declared_surface`) applies
    identically -- it is keyed on rel_path alone, language-agnostic.
- **Structural PII type-kind for TS/Rust nominal PII-shaped types
  (T-0762)**: T-0352 left TYPE-kind matching (`EmailStr`/`SecretStr`)
  Python-only, an honest gap; T-0762 closes it by extending
  `FIELD_SIGNATURES`'s single-source registry with a `langs` field
  (`_FieldSignature.langs`, default all three languages for NAME-kind
  entries; explicit per-entry scope for TYPE-kind entries, since a type
  name like `SecretStr` or `SecretString` only exists in one language's
  ecosystem):
  - TS: a field typed as a known secret-wrapper type (`Secret`,
    `SecretString`, `SensitiveString`) or a branded/nominal email type
    (`Email`, `EmailAddress`) fires PII010 via `_ts_type_hit`, even when
    the field's own NAME carries no name-kind keyword. A plain
    `string`-typed field does not fire on type alone.
  - Rust: a field typed `secrecy::Secret<...>`/`secrecy::SecretString`
    (the `secrecy` crate's wrapper types named in the ticket body) or a
    conventionally-named `Email` newtype PII wrapper fires PII010 via
    `_rust_type_hit`. A plain `String`-typed field does not fire on type
    alone.
  - Both walk the type-annotation/type subtree for bare type-identifier
    names (`_type_identifier_names`, the TS/Rust analogue of
    `_annotation_names`'s Python AST walk) so a generic-wrapped or
    scoped-path type (`secrecy::SecretString`, `Secret<String>`) still
    surfaces its inner type name -- one shared walker for both grammars,
    funneled through one shared `_type_hit(names, lang)` lookup so the
    `langs` scoping logic lives in exactly one place.
  - Resolving a field/binding TYPE to an imported type's actual
    definition (distinguishing an unrelated same-named local `Email` type
    from a real PII-shaped one, or reading an import alias) is NOT
    attempted -- this is a bare type-identifier NAME match, the same
    posture `_field_type_hit` already has for Python's `EmailStr`/
    `SecretStr`. Full import-resolution-backed type-kind matching is left
    for a follow-on ticket (coordination with T-0717's capability taxonomy
    and the T-0611/T-0612 adapters' type info, per T-0762's ticket body),
    not silently guessed at here.

### Anti-orphan file-reference gate T-0396

`frob.gates._refs` -- `ref_gate` (gate name `refs`, default-on, WARN
severity, dial via `[gates.severity]`). Motivating case: the
`docs/design/registry/*.yaml` manifests were read by ZERO other tracked
files -- a silently dead/unenforced artifact no existing gate reasons
about, because every other gate reasons about SOURCE symbols
(`frob.graph`'s import/DSL edges), never about a bare tracked file's
existence being justified at all. This gate runs over EVERY git-tracked
file, regardless of type (source, docs, config, data, assets).

Two detection layers, both required to feed the same inbound-reference
count per file:

- **Auto-scan**: file X counts as referenced by file Y when Y's text
  names X (full repo-relative path or bare basename) in a real reference
  SYNTACTIC position -- a markdown link (`](path)`), a quoted string
  literal, a `frob:doc`/`frob:describes`/`frob:used-by`/`frob:tests`
  directive target, a `require`/`include`/`use` target, or a Python
  import (`from X import a, b, c` -- single-line, comma-list, OR
  parenthesized/multi-line -- and plain `import a, b.c`, EVERY imported
  name resolved, not just the module prefix). Deliberately NOT a bare
  substring match over the whole text: a README table cell or a
  ticket-body sentence merely NAMING a file (`` `patterns.yaml` ``) is
  not a reference in any of these shapes, and counting it as one
  silently defeats the gate. For `.py` targets only, a bare imported
  name or a dispatch table's quoted bare module-name string (e.g.
  `"ack_runner"` reaching `ack_runner.py`) also resolves via the
  target's extensionless stem -- restricted to `.py` targets because a
  stem match against a non-Python (data/doc) target reintroduces the
  same false-pass failure mode (an unrelated quoted English word
  colliding with a data file's stem).
- **Test-discovery IMPLICIT reference**: a file `frob.excludes.
  is_test_file` recognizes (`tests/**`, `test_*.py`, `*_test.py`, ...)
  is exempt from REF001/REF002 outright -- it is referenced by the test
  RUNNER via filesystem/naming convention, which no textual scan can see.
- **Declared** (`frob:used-by <consumer>`): a file names its own consumer
  explicitly, for references the auto-scan structurally cannot see (a
  path built at runtime, a glob loaded by a directory base). Every
  declaration is VERIFIED, not trusted: the named consumer must be a
  tracked file AND must itself reach the declaring file (same
  syntactic-position check, in reverse) -- a declaration naming a
  nonexistent or non-reaching consumer is REF003, not a silent pass. This
  is the anti-lie half: a `frob:used-by` cannot manufacture a reference
  that isn't real.

**Round-2 correction (reviewer-rejected the first landing, T-0396 Done
report):** the first working version's auto-scan produced an 86%
false-positive rate on this repo's own tree (326 of 379 REF001 findings
were detector gaps, not real orphans) -- two systemic causes, both fixed:
(1) a `from X import a, b, c` only captured the module PREFIX, never the
imported names, so any module reached ONLY through a multi-name import
was a permanent false orphan; (2) pytest-discovered test files (52% of
the false findings) are reached by filesystem convention, which no
textual auto-scan can see, and were flagged forever without the implicit
test-discovery exemption above. A post-fix full manual review of every
remaining REF001 finding on this repo found the detector's false-positive
rate at effectively zero (see T-0396's Done report for the finding-by-
finding verification and the exact before/after counts).

Tiers, over the deduped set of inbound-referencing files (auto plus
verified-declared, unioned): **0** -> REF001 (orphan), **1** -> REF002
(single fragile anchor), **2+** -> pass. All three rules are WARN -- this
never fails `frob check`'s exit code, but every REF001/REF002 must
eventually be waived-with-reason (`frob:waive REF001 reason="..."`) or
fixed, same advisory-but-tracked posture as PERF/FUZZ.

`[[refs.entrypoint]]` in `frob.toml` exempts genuinely externally-facing
files (README.md, LICENSE, pyproject.toml, the CLI `__main__.py`, ...)
from REF001/REF002 -- each entry is `{ path = "...", reason = "..." }`; a
malformed entry (missing `path`/`reason`) is skipped and logged, never
treated as a blanket mute.

`used-by` is a reserved marker verb in `frob.graph.dsl`
(`_RESERVED_MARKER_VERBS`): recognized and silently skipped by the graph's
generic directive parser (never routed through `EdgeKind`, never an
"unknown verb" `MalformedDirective`) because `_refs.py` owns and verifies
it directly via its own line-oriented scan -- a `frob:used-by` target is a
whole FILE, not a symbol, and every non-source tracked type
(yaml/md/toml/json/...) must be able to carry it too, most of which
`frob.lang` never parses at all.

### DOC004 unbound stale doc code blocks T-0436

`frob.gates._docblocks` -- `doc004_gate` (gate name `docblocks`, default-on,
mixed severity per finding). Motivating case: a fenced code block in a
`.md` doc (a python `from X import Y` example, a rust `use crate::path`
snippet) is the highest-drift-risk prose in a repo -- nothing binds it to
the code it demonstrates, so a rename/removal silently makes the doc lie.
No existing gate catches this: REF001-003 reason about whole-FILE
reachability, never a fenced block's own text; DOC001/DOC002 reason about
doc-to-doc/doc-to-symbol link structure, never code embedded in prose.

Deliberately SIMPLE, CONSERVATIVE, and PROJECT-GENERIC (the REF001
false-positive lesson applies here too: a noisy gate gets blanket-waived):

1. **Namespace derivation (never the directory name, never a hardcoded
   per-tool list)**: python from `pyproject.toml`'s `[project].name` plus
   every top-level package under `src/`; rust from the root `Cargo.toml`'s
   `[package].name` PLUS every `[workspace].members` glob's resolved
   subcrate (each subcrate is its own namespace -- a repo packaged as
   `logandapp_backend` is keyed on that name, never its directory); ts/js
   from `package.json`'s `name` plus `workspaces` members. Computed once
   per gate run.
2. **Extraction**: python `from X import ...`; rust `use X::...;`; ts/js
   `import ... from "X"` / `require("X")`. A token whose root namespace
   segment is not one of the project's own is skipped outright -- external
   libraries, generic shell, pseudo-code never flagged.
3. **Two tiers** for a token that DOES reference the project's own
   surface: **stale** (error) -- the module/crate/symbol does not resolve
   (python: checked against the real `GraphSnapshot` symbols, including a
   deliberately loose re-export check so a package `__init__.py` that only
   imports-and-re-exports a submodule's symbol via `__all__` is not a
   false positive; rust: checked by scanning the resolved crate's tracked
   `.rs` files for a matching `pub` item declaration) -- or **unbound**
   (warn) -- it resolves, but the block carries no `frob:doc`/
   `frob:describes`/`frob:tests` directive within itself or its three
   immediately-preceding doc lines, so future drift on it would go
   undetected. TS/JS is UNBOUND-only by design (no reliable static
   resolver for its export shapes here -- see the module docstring).
4. **`frob:waive DOC004 reason="..."` is prominently honored** directly
   out of the block's own nearby text (an HTML comment above the fence, or
   a comment line inside it) -- NOT routed through `frob.graph`'s WAIVE
   edge machinery, because `.md` files never go through
   `frob.graph.dsl.parse_directives` (only the narrower `markdown_anchors`
   describes-only scan), so a waiver written in doc prose has no graph
   edge to bind to. This is the deliberate escape hatch for a genuinely
   external or illustrative block the heuristic cannot confidently
   classify.

5. **Console/bash command-drift checking (T-0443)**: a
   ` ```console ``` `/` ```bash ``` `/` ```sh ``` `/` ```shell ``` ` fenced
   block's lines are scanned for `<prog> <subcommand...>` invocations of a
   CONFIGURED command source -- never a hardcoded, frob-specific
   subcommand list. `frob.toml`'s `[[docblocks.commands]]` array declares
   each source generically:

   ```toml
   [[docblocks.commands]]
   prog = "frob"
   parser = "frob.__main__:_build_parser"
   ```

   `parser` is a `module:callable` dotted path to a zero-argument factory
   returning an `argparse.ArgumentParser`; the gate imports it AT CHECK
   TIME and walks its live `add_subparsers` tree, so the argparse registry
   is the single source of truth -- a subcommand rename/removal there is
   caught automatically, with zero edits to this gate or to `frob.toml`.
   A chain that does not walk the tree is STALE (error); one that does
   resolve is checked for a nearby binding directive same as every other
   tier (UNBOUND, warn). No `[[docblocks.commands]]` entries at all (a
   project that has not opted in) means zero console/bash checking --
   fail-open, matching every other namespace source in this module.

This repo configures itself as its own first instance -- see
`frob.toml`'s `[[docblocks.commands]]` table, pointed at
`frob.__main__:_build_parser`.

**Dogfooding result (T-0436 Done report has the full finding-by-finding
detail)**: run on this repo's own tracked docs, DOC004 found 5 real
blocks -- 2 genuinely stale (`frob.edit._impl`, `frob.app.stub_runner`:
illustrative example modules referencing a removed/never-real command
surface) and 1 hypothetical-future worked example
(`export_terraform_sg`), each dispositioned with a reasoned
`frob:waive DOC004 reason="..."`; 1 initial false positive (a package
`__init__.py` re-export, `frob.strata`) was a real detector bug, fixed
before landing (see `_module_reexports`); 1 real UNBOUND advisory
(`docs/modules/logging.md`'s usage example, anchored later in the same
doc's "Public API" section rather than immediately above/inside the
block) was waived with a reason explaining why. Zero blanket waivers --
every waiver names its own specific reason.

### DOC005 README command-table drift-lock T-0435

`frob.gates._docblocks` -- `doc005_gate` (gate name `docblocks`, same as
DOC004, default-on, ERROR severity). Motivating case: `README.md` carries
~0 `frob:describes` anchors, so it is UNANCHORED prose -- DOC001/DOC002
detect drift THROUGH anchors, and DOC004 detects drift in fenced code
blocks, but neither reasons about a markdown TABLE naming commands.
README's command table drifted silently: it was missing 8 of 25 real
subcommands (a third, including whole subsystems added during the
`edit`/`dispatch`/`mission`/`todo` rework) before this ticket, and nothing
ever flagged it.

`doc005_gate` reuses DOC004's console-tier machinery WHOLESALE -- the same
`[[docblocks.commands]]`-configured `argparse.ArgumentParser` factory,
walked into the same live subparser tree (`frob.gates._docblocks.
_console_trees`) -- rather than a second, parallel registry-reading
mechanism. Two checks over `README.md`, both ERROR (concrete, present
drift, not advisory):

1. A markdown table row `| \`<prog> <name>\` | ... |` naming a `<name>`
   that is NOT a real top-level subcommand of the live tree -- STALE, the
   command was renamed/removed and the row never updated.
2. A real top-level subcommand with NO table row anywhere in `README.md`
   -- MISSING, the README silently omits a real command (this repo's
   original T-0435 finding: `clean`/`debt`/`doctor`/`pool`/`registry` had
   no row).
3. A "N commands" (or "N total commands") prose count claim whose `N`
   does not equal the live top-level command count, summed across every
   configured `[[docblocks.commands]]` source -- the "checkable counts"
   half of the ticket's mandate. No such claim in a project's README means
   nothing to check (never a false positive from an absent claim).

No `[[docblocks.commands]]` entries configured, or no `README.md` at the
scanned root, means no checking happens -- fail-open, the same posture as
every other DOC004 namespace source. This repo uses its own already-
configured `[[docblocks.commands]]` entry (`frob.__main__:_build_parser`)
-- adding a new subcommand there and never touching `README.md` now fails
`frob check` immediately; removing a command leaves its stale row failing
until the row is deleted.

### DOC006 doc-pointer resolution gate T-0437

`frob.gates._docptr` -- `doc006_gate` (gate name `docblocks`, same as
DOC004/DOC005, WARN severity at first-turn-on per the T-0688 new-gate
precedent). Motivating case: a doc's prose routinely "seems to point" at
something -- `frob edit`, `src/frob/gone.py`, `[bogus.section]`,
`docs/missing.md#x` -- and nothing checked whether the pointer was
actually real. Detecting fuzzy "seems to point" intent generically is
unhardenable (high false-positive rate); this gate instead defines a
CLOSED SET of RECOGNIZED, mechanically resolvable pointer shapes and only
fires when a pointer of a known shape targets something that does not
exist. An unrecognized/ambiguous token is never flagged -- that is the
hardening.

Five recognized pointer kinds, each detected in an inline code span or
markdown link across every tracked `.md` file's PROSE (fenced code block
bodies are DOC004's own territory and are skipped here, to avoid double-
reporting the same token under two rule ids):

1. **FILE/PATH** -- a repo-relative path (contains `/`, or a well-known
   bare manifest basename: `frob.toml`, `pyproject.toml`, `Cargo.toml`,
   `package.json`) must exist as a git-tracked file.
2. **CLI INVOCATION** -- `` `<prog> <subcommand...>` `` / `` `--flag` ``
   checked against the SAME `[[docblocks.commands]]`-configured live
   argparse registry DOC004/DOC005 already walk -- one live source of
   truth, never a second copy.
3. **CONFIG REFERENCE** -- `` `[section]` ``/`` `[section.key]` `` checked
   against this project's own loaded `frob.toml` structure.
4. **CODE SYMBOL** -- a dotted path (`module.Class.method`) whose root
   namespace is one of this project's own manifest-derived namespaces
   (`frob.gates._docblocks._project_namespaces`), resolved the same way
   DOC004's python tier resolves a `from X import Y`.
5. **DOC-ANCHOR LINK** -- `docs/x.md#anchor`: the file must exist and
   `anchor` must be a real heading/`<a id>` slug in it (the same resolver
   DOC002 uses for `frob:doc` edges).

A sixth, source-level check rides alongside the doc-prose scan for the
DRIFT002 dotted-vs-`::` confusion class (T-0940/T-0945): a `frob:tests`
directive's target is itself a recognized, mechanically-checkable shape --
`<file>::<qualname>` with exactly one `::` separating the file from a
DOTTED (`Class.method`) qualname. A target with a SECOND `::` (pytest's
own `Class::method` collect-only separator) is definitively the wrong
shape for a graph-facing `frob:tests` target, flagged here directly
instead of waiting for it to surface later as a generic DRIFT002
dangling-edge failure with a less specific message.

Every finding is `frob:waive DOC006 reason="..."`-able (same nearby-line
convention as DOC004: same line or up to 3 preceding lines), for a
genuinely external/illustrative/future-facing pointer.

**Turn-on disclosure**: shipped at WARN, not ERROR, because this repo's
own tracked docs already carry pre-existing pointer drift the gate newly
detects (see T-0437's Done report for the measured count at turn-on).

### Git-less target contract T-0705

Every gate that scans "every tracked file" (`secrets_gate`, `pii_structural_
gate`, `render_lint_gate`, `walk_lint_gate`, `ref_gate`, DOC004's `src/`/
`*.md` namespace sources) resolves its file list via `git ls-files` under
`root`. When `root` is not a git work tree at all (no `.git`, or `git`
itself missing/unavailable) that subprocess exits 128 -- not a violation,
just an environment with nothing tracked to scan.

The chosen, consistent contract for ALL of these call sites: **degrade
gracefully, never hard-error**. `git ls-files` failing on a git-less
`root` logs at WARNING and the gate returns `()` (no candidates, no
violations) -- the same posture `ref_gate`/DOC004 always had. Before
T-0705, `secrets_gate`/`pii_structural_gate`/`render_lint_gate`/
`walk_lint_gate` logged the identical condition at ERROR, painting their
line red in `frob check`'s raw log stream for a target that was never a
violation. This was an inconsistency between six call sites doing the
exact same "resolve tracked files, degrade on failure" dance, not a
deliberate severity choice -- nothing about a git-less target makes THESE
four gates more alarming than `ref_gate`/DOC004's identical fallback.

This does not weaken what any gate checks in a real git repo: the
`returncode != 0`/`is_err` branch only fires when `git ls-files` itself
fails, which never happens against an actual tracked worktree. A genuinely
untracked/dirty file in a real repo is unaffected -- `git ls-files` still
enumerates every OTHER tracked file normally, and per-file scanning logic
is untouched.

Why not the alternative (git as a hard requirement, erroring loudly with
ONE message before any gate runs)? `frob check <path>` and `frob ticket
new --path <path>` are both documented to accept a bare filesystem path
with no git precondition (`docs/modules/tickets.md`'s "ambiguous: no git
repo, detached HEAD, git unavailable" ticket-id-minting fallback is the
same call already made for a sibling concern) -- a git-less target is a
supported, if degraded, scan surface, not a usage error. Gates that
inherently need a diff against a base branch (`COV002`/`SCOPE001`/
`TODO001`) are a distinct, ALREADY-deliberate mechanism (T-0550, in
`frob.gates.coverage_gate`/`scope_gate`/`_load_diff`) with its own loud
fail-on-load-failure contract for a different reason (masking a real diff
failure as a silently-clean diff on an actual project); T-0705 does not
touch that mechanism -- see T-0705's Done report for the follow-up ticket
that tracks whether a git-less `root` should also be exempted there.

Regression coverage: `tests/system/test_cli_check.py`'s
`TestGitlessTargetGateSeverity` plants a git-less fixture directory and
asserts each of the four gates' fallback line is WARNING, never ERROR.

### WALK001 unpruned traversal T-0471

`frob.gates._walk_lint` -- `walk_lint_gate` (gate name `walk_lint`,
default-on, WARN severity). Motivating case: T-0453's `_repo_files` did
`root.rglob("*")` -- walking the ENTIRE tree including `.git`, `.venv`,
`__pycache__`, and ~129 stale worktrees under `.claude/worktrees/` --
making `frob ticket doable` take minutes. `frob.excludes` already carried
the shared prune machinery (`_should_prune_dir`/`is_always_pruned_dir`, the
built-in skip set + `frob.toml` globs, established by T-0335 for `os.walk`
sites), but nothing stopped a raw traversal call from bypassing it. This
gate turns that mistake class into a static check: no NEW unpruned
traversal can land silently.

`frob.excludes` grew two shared entry points every walking caller should
route through instead (T-0471): `walk_pruned(root)` (an `os.walk`
generator that prunes `dirnames` in place via `_should_prune_dir` BEFORE
descending) and `iter_files(root, *, suffix=None)` (prefers a `git
ls-files` fast path -- tracked files only, no traversal at all -- when
`root` looks like a git work tree, falling back to `walk_pruned`
otherwise).

Detection is AST-based (Python's `ast` module, matching `_pii_structural`'s
precedent -- a regex/lexical scan both over- and under-fires on multi-line
calls and string mentions that merely name the pattern), scanning every
git-tracked `src/frob/**/*.py` file for:

- `Path.rglob(...)` -- always unbounded recursive regardless of pattern.
- `Path.glob(...)`/`Path.iglob(...)` -- only when the pattern argument
  contains `"**"` (a non-literal/dynamic pattern is treated as
  potentially recursive, deny-by-default).
- `os.walk(...)` -- dotted or bare-imported (`from os import walk`) form.
- `glob.glob(...)`/`glob.iglob(...)` with a `"**"` pattern -- dotted or
  bare-imported form.

Self-excludes `frob/gates/_walk_lint.py` (its own detection logic) and
`frob/excludes.py` (the shared helpers' own implementation, which contains
the one legitimate raw `os.walk` call this whole gate exists to keep
singular). Waivable per-line (`frob:waive WALK001 reason="..."`) for a
genuinely small, bounded-scope walk (e.g. `design_dir.rglob("*.strata")`
over a directory that will never be large enough to matter) -- the message
always names the remedy: route through `frob.excludes.iter_files` /
`frob.excludes.walk_pruned`.

### EXCL001 (T-0465)

<!-- frob:describes src/frob/gates/_exclude_hazard.py::exclude_hazard_gate -->

`frob.gates._exclude_hazard` -- `exclude_hazard_gate` (gate name
`excludehazard`, default-on, ERROR severity, unwaivable by design -- see
below). Motivating incident: an agent added `src/frob/render/` to
`.git/info/exclude` to hide its own in-progress untracked scratch files.
`.git/info/exclude` is a personal, UNTRACKED gitignore -- but it lives
under `.git/`, which is the COMMON dir shared by every worktree of one
clone (`git rev-parse --git-common-dir`), not a per-worktree path. One
entry there silently changes `git status`/`git add -A` behavior in every
worktree of the clone AND `main` simultaneously. The hazard isn't that
excluding a directory untracks files already committed (it does not) --
it's that a real, git-tracked source directory now has a standing blind
spot: any NEW file added under it later never shows up as untracked,
never gets `git add -A`ed, and silently never gets committed. That is
exactly how the T-0448 foundation went missing.

`exclude_hazard_gate` reads the shared common dir's `info/exclude`
directly (not the repo-relative, possibly-scoped root -- the file is
one, shared, common-dir path regardless of which worktree runs `frob
check`), parses each non-comment, non-negated gitignore-format line into
its directory/file prefix, and flags any prefix that names an exact
git-tracked file or a directory under which `git ls-files` finds at
least one tracked file. An entry matching nothing tracked (`*.pyc`,
`build/`, any genuinely-generated or never-tracked path) is silent --
those are exactly what `.git/info/exclude` is FOR.

Deliberately unwaivable (no `frob:waive EXCL001` escape hatch): the
entry lives in `.git/info/exclude` itself, not in a source file a
`frob:waive` comment could attach to, and the honest fix is always the
same -- remove the entry, or use a genuinely untracked path instead of
hiding work under a real source directory.

```python
# frob/gates/__init__.py
def run_gates(cfg: GateConfig) -> Result[GateReport, GateError]
    # Orchestrates all gates (parallel where independent) over one
    # GraphSnapshot + TicketQueue + diff; single entry for check_runner.

def drift_gate(snapshot: GraphSnapshot, lock: LockFile) -> tuple[Violation, ...]
def coverage_gate(snapshot: GraphSnapshot, queue: TicketQueue,
                  diff: Diff, tests: CollectedTests) -> tuple[Violation, ...]
def scope_gate(diff: Diff, ticket: Ticket, snapshot: GraphSnapshot, *,
               root: Path | None = None,
               queue: TicketQueue | None = None) -> tuple[Violation, ...]
    # SCOPE001. When root/queue are given (run_gates always passes them),
    # a file failing this ticket's own scope is re-checked hunk by hunk via
    # git blame: a hunk is exempt only if every line is already committed
    # (never a dirty/uncommitted line) and every covering commit's subject
    # names another ticket whose own declared scope covers the file (T-0108
    # -- fixes false SCOPE001 on files an earlier ticket already committed
    # on the same branch). Callers omitting root/queue keep the old,
    # unconditional check.
def prework_gate(ticket: Ticket, snapshot: GraphSnapshot,
                 sweep: Option[PreworkSweep] = Nothing()) -> tuple[Violation, ...]
    # PRE001. T-0584: a PARTIAL sweep (gates/_prework.py::sweep_ticket ran
    # out of its bounded budget before finishing every scope pattern) whose
    # digest still matches the ticket's current scope is treated as
    # provisionally clean, not a violation -- otherwise PRE001 would demand
    # completion of the very sweep a slow mount could not finish in one
    # foreground-budget-sized call.
def invariant_gate(invariants: tuple[Invariant, ...], snapshot: GraphSnapshot,
                   tests: CollectedTests) -> tuple[Violation, ...]

def test_gate(snapshot: GraphSnapshot, systems: tuple[SystemSpec, ...],
              coverage: Option[CoverageData], tests: CollectedTests,
              cfg: TestPolicy) -> tuple[Violation, ...]
    # TEST001..TEST006. Interfaces are derived from the snapshot: every
    # package whose public symbols are imported by another package is an
    # interface and owes integration tests. Coverage is consumed as
    # recorded evidence, never produced here.

def stamp_coverage(root: Path) -> Result[Unit, GateError]
    # Called by `make coverage` after pytest-cov: records coverage.xml's
    # sha plus current per-file content hashes into .frob/coverage-stamp.
    # TEST006 compares this stamp against the live snapshot.

def load_coverage(root: Path) -> Result[CoverageData, CoverageError]
    # Parses coverage.xml (branch mode) and maps line hits onto symbol
    # spans from the snapshot -> per-symbol/module percentages.

def active_ticket(root: Path, explicit: str | None) -> Option[str]
    # --ticket flag wins; else branch name matching ^(T-\d{4})- ; else Nothing.
    # Scope/pre-work gates run only when a ticket context exists.

def record_prework(root: Path, ticket_id: str,
                   sweep: PreworkSweep) -> Result[Unit, GateError]
    # `frob ticket start` runs dup+xref over the ticket scope and stores the
    # sweep digest in the ticket body; PRE001 checks its presence.

def sweep_ticket(root: Path, ticket: Ticket,
                 budget_seconds: float | None = DEFAULT_SWEEP_BUDGET_SECONDS
                 ) -> Result[PreworkSweep, GateError]
    # T-0584: bounded and resumable. Times the per-scope-pattern xref loop
    # against `budget_seconds` (None = unbounded, for tests/an explicit full
    # sweep); the dup scan and graph load still run once, unbounded, ahead
    # of it. If the deadline is hit with patterns still remaining, records
    # a `partial=True` sweep with those patterns in `pending_patterns`
    # instead of blocking to completion -- the previous fully-synchronous
    # shape of `frob ticket sweep` (the always-available resweep-after-
    # scope-edit path) could not complete within a slow-mount agent's
    # foreground budget, and PRE001 only ever compared against a fully-
    # completed digest, so the ticket could never get back into a checkable
    # state (the T-0355-item-2 catch-22 this closes). A later call with a
    # matching digest resumes from `pending_patterns` rather than
    # rescanning patterns already swept.

# Diff/working_diff live in frob/gitio.py (the ONE git seam, shared with
# frob.testing -- see docs/modules/testing.md); base default "main", configurable
# [tool.frob] check_base. CollectedTests and its pytest-collection cache
# live in frob.testing and are imported from there.

# frob/policy/__init__.py
def load_policy(root: Path) -> Result[tuple[PolicyRule, ...], PolicyError]
def policy_gate(rules: tuple[PolicyRule, ...], snapshot: GraphSnapshot,
                diff: Diff) -> tuple[Violation, ...]

# frob/gates/invariants.py
def load_invariants(root: Path) -> Result[tuple[Invariant, ...], InvariantError]
```

## Invariants

<!-- frob:describes src/frob/gates/invariants.py::_Criticality -->
<!-- frob:describes src/frob/gates/invariants.py::Invariant -->
<!-- frob:describes src/frob/gates/invariants.py::InvariantError -->

- `Criticality` -- how severe a broken invariant would be (`high` |
  `medium`); feeds severity weighting in INV001/INV002 reporting.
- `Invariant` -- one tracked invariant: id, statement, criticality, and
  its evidence list, parsed from `invariants/INV-###.md`.
- `InvariantError` -- failure values `load_invariants` can return
  (malformed frontmatter, duplicate id).

"Proving things that matter": an invariant is a tracked statement whose
truth must have standing evidence. Files in `invariants/INV-###.md`:

```markdown
---
id: INV-007
statement: Lock writes are atomic; a crashed frob never truncates frob.lock
criticality: high             # high|medium
evidence:
  - tests/test_lock.py::test_write_atomic_under_kill   # pytest node id
  - POL-no-direct-lock-write                            # or a policy rule id
---
Rationale and threat model prose here.
```

INV001/INV002 close the loop: every invariant is anchored in code
(`frob:invariant INV-007` at the enforcing site) and backed by evidence
that `frob check` verifies still exists (test collected, rule loaded).
Security work becomes monotonic: each audit finding lands as an invariant
plus a policy rule or property test, never a one-off fix.

### INV003 (T-0462)

<!-- frob:describes src/frob/gates/invariants.py::find_exclusivity_claims -->
<!-- frob:describes src/frob/gates/invariants.py::EXCLUSIVITY_CLAIM_PATTERNS -->
<!-- frob:describes src/frob/gates/__init__.py::inv003_gate -->

INV001/INV002 close the loop for invariants that already got written down
in `invariants/INV-###.md`. INV003 catches the earlier failure mode: prose
in `docs/**.md` asserting an exclusivity/normative claim -- "only",
"sole"/"solely", "exclusively", "nothing else", "never...except",
"at most/exactly one" (`find_exclusivity_claims`,
`EXCLUSIVITY_CLAIM_PATTERNS`) -- with nothing tracking whether it still
holds. A doc file making such a claim needs a
`<!-- frob:invariant INV-### -->` marker somewhere in the same file
naming a real, loaded invariant; a marker naming an unknown id does not
count (`inv003_gate`).

INV003 is `Severity.WARN`, not `ERROR` like INV001/INV002: even after
calibration (below) a claim can be genuine design intent rather than an
enforced behavior, so WARN surfaces the signal for human triage rather
than forcing a bind-or-waive on every hit.

**T-0509 calibration.** The original bare-vocabulary scan surfaced ~90
INV003 findings (and ~677 INV004 findings, see below) across `docs/` --
mostly headings, table cells, code samples, and link text carrying the
trigger word with no actual claim attached (a `## Schema` heading, a
`| only |` table cell). Three changes narrow this to a genuinely
reviewable pool without dropping real claims:

- **Noise stripping** (`frob.gates.invariants._strip_markdown_noise`):
  fenced code blocks, inline code spans, markdown link targets, and table
  rows are removed before scanning -- code samples and URLs are not prose
  assertions.
- **Claim-shape requirement** (`_is_claim_shaped`, `_CLAIM_VERB_RE`): a
  trigger word only counts if a claim-verb (`is`/`must`/`supports`/`writes`/
  etc.) appears in the SAME sentence -- a bare heading or dangling noun
  phrase asserts nothing regardless of vocabulary.
- **Directory scoping** (`INV003_SPEC_DIRS = ("docs/modules", "docs/strata")`):
  INV003 only runs over these two spec-normative trees, not all of
  `docs/**.md` -- exclusivity claims worth gating describe enforced
  contracts, which is what those trees are for; a narrative design doc or
  changelog making a passing "only" remark is a different failure mode
  than T-0462 named. INV004 (below) still runs over all of `docs/`.

Markdown-side `frob:waive` support now also exists (`_match_waiver` keys
off graph edges, which doc prose still carries none of -- this is a
separate marker): `<!-- frob:waive INV003 reason="..." -->` anywhere in a
file dispositions that file's INV003 findings, same honesty requirement
as the code-side `frob:waive`'s WAIVE001 (a marker with no `reason=` is
not honored). Applied from `inv003_gate` via
`_file_has_reasoned_doc_waiver` rather than inside `_inv003_doc_violations`
itself -- see that helper's docstring for why (a COV005 false-positive
this repo hit once already, from directive-target reuse across public
and private symbols in the same file).

Net effect measured on this repo after T-0509 (`frob check --only
invariant`): INV003+INV004 combined, 765 -> 604 warnings (INV003 88 ->
31, INV004 677 -> 573). The residual was tracked as a follow-up burndown
ticket rather than hand-closed in one pass; see the INV004 section below
for T-0515's further calibration of that residual.

### INV004 (T-0452, T-0515)

<!-- frob:describes src/frob/gates/invariants.py::find_normative_claims -->
<!-- frob:describes src/frob/gates/invariants.py::NORMATIVE_CLAIM_PATTERNS -->
<!-- frob:describes src/frob/gates/__init__.py::inv004_gate -->

INV003 is a per-CLAIM lint: one specific exclusivity assertion needs one
specific bound invariant. INV004 is the INVERSE, FILE-level signal: a
doc file using ANY normative language at all -- `must`, `must not`,
`never`, `always`, `shall`, `guarantees`, `ensures`, `requires`, plus
INV003's exclusivity vocabulary (`NORMATIVE_CLAIM_PATTERNS`,
`find_normative_claims`) -- but anchoring ZERO `<!-- frob:invariant
INV-### -->` markers anywhere in the FILE (unlike INV003, a marker naming
an unknown id still counts here -- INV004 only asks "is *anything*
tracked here") is flagged as a likely under-specified doc: the "silence"
a per-claim lint can't see, because there is no single explicit claim to
anchor on.

Always `Severity.WARN` -- advisory by design, a suggestion to formalize
rather than a broken obligation; INV004 does not fail `frob check`.

INV004 shares INV003's T-0509 noise-stripping and claim-shape scan
(`find_normative_claims` calls the same `_claim_shaped_sentences`
preprocessing as `find_exclusivity_claims`).

**T-0515 calibration.** After T-0509, INV004 was still section-level
(`_markdown_sections`) and ran over all of `docs/**.md`, and its 573
residual warnings dwarfed INV003's 31 -- mostly many hits per file for a
handful of entirely-unbound docs, not 573 distinct under-specified
regions worth separate triage. Two changes, mirroring INV003's own T-0509
rationale:

- **File granularity, not per-section** (`_inv004_doc_violations`): one
  advisory per file (a doc large enough to need section-level invariant
  tracking should already be split into `invariants/INV-###.md` entries),
  not one per ATX section.
- **Directory scoping** (`INV003_SPEC_DIRS`, shared with INV003): INV004
  now runs only over `docs/modules` and `docs/strata`, not all of
  `docs/**.md` -- a narrative design/audit/guide doc using "must" or
  "always" in passing is a different failure mode than an
  enforced-contract doc with zero bound invariants at all.

A file-scoped markdown `frob:waive` marker (`<!-- frob:waive INV004
reason="..." -->` anywhere in the file, applied via
`_file_has_reasoned_doc_waiver` from `inv004_gate`, the same helper
INV003 uses) dispositions one under-specified file without a fake bound
invariant.

Net effect measured on this repo (`frob check --only invariant`):
INV003+INV004 combined, 604 -> 63 warnings (INV003 unchanged at 30,
INV004 573 -> 33). The residual 63 spans 33 files under `docs/modules`
and `docs/strata` that assert real behavior with no invariant bound at
all yet; each needs individual triage (bind a real invariant, reword, or
waive with a specific reason) rather than a blanket disposition -- tracked
as a further follow-up ticket rather than hand-closed in this pass.

### INV005 (T-0543)

<!-- frob:describes src/frob/gates/__init__.py::_invariant_evidence_proves_anchor -->
<!-- frob:describes src/frob/gates/__init__.py::_evidence_binds_to_symrefs -->

INV001 only asks whether an invariant's evidence list contains AT LEAST
ONE item that resolves to a collected test node id (or a loaded policy
rule id) -- existence, not proof: `def test_x(): pass`, bound to nothing,
anywhere in the repo, cleared it. INV005 is the same remedy family as
COV006/D-02's `evidence_covers_scope`: when the invariant HAS a
`frob:invariant` anchor, and evidence collected but NONE of it is shown to
actually bind to that anchor (a `frob:tests` edge either direction, or the
evidence test living in the same file as the anchor), INV005 fires.

Deliberately `Severity.WARN`, not a tightened INV001: this repo's own
`invariants/` directory already has evidence entries written before any
edge/same-file binding convention existed (17 invariants at the time this
gate was added), and forcing them all through a binding-proof pass in one
ticket was out of budget -- the same "large, needs its own dedicated
follow-up" shape as the parallel B1 (TEST001 real-coverage) and B2
(DRIFT001 body facet) gates-accounting findings. INV001/INV002 keep their
prior ERROR semantics unchanged; INV005 is the loud-but-non-blocking nudge
toward a real binding for anything NEW.

### INV006 (T-0408)

INV003/INV004 (above) are DOC-only: they scope to `INV003_SPEC_DIRS`
(`docs/modules`, `docs/strata`) and never look at source code. The user
named a two-part gap this left open: only a handful of formal invariants
exist for a large system, while a repo-wide grep finds well over a
hundred SOURCE files (Python, Rust) asserting a property in
docstrings/comments -- "always", "never", "only", "exactly once", and
so on -- with nothing checking whether enough of THOSE claims are
formalized. INV001/INV002 only ever validated invariants that already
existed; nothing checked whether enough invariants existed at all.

INV006 closes the source-code half of that gap: it reuses INV003's exact
claim vocabulary and claim-shape scan (`find_exclusivity_claims`, already
noise-filtered by T-0509's verb-in-same-sentence requirement) over every
`.py`/`.rs` file under `INV006_SRC_DIRS`, and treats a file as covered if
ANY `frob:invariant` edge (the real comment-DSL directive, not an
HTML-comment marker regex that would never match Python/Rust comment
syntax) anchors anywhere in that file. A `frob:waive INV006 reason="..."`
edge on the file (or a symbol in it) dispositions a claim that is
genuine design intent rather than an enforced behavior, mirroring
INV003's markdown-side waiver.

WARN severity, same posture as INV003 -- this repo's own first-turn-on
measurement (`frob check --only invariant`) found ~167 INV006 findings
across `src/`, `strata-core/src/`, and `frob-core/src/`; driving that
down to 0 (bind each to a real invariant, waive with a specific reason,
or reword) is tracked as a follow-up burndown, same as INV003/INV004's
own residual, not hand-closed in this pass.

## Policy rules (`frob.toml`, `[policy]`)

<!-- frob:describes src/frob/policy/_models.py::PolicyKind -->
<!-- frob:describes src/frob/policy/_models.py::PolicyRule -->

- `PolicyKind` -- the three rule kinds `frob.toml`'s `[policy]` table
  supports at alpha: `forbidden-import`, `pattern`, `norm`.
- `PolicyRule` -- one `[[policy.<kind>]]` entry; fields not used by its
  `kind` are left at their default.

```toml
[[policy.forbidden-import]]
id = "POL-no-requests-in-core"
module = "requests"
within = "src/frob/graph/**"
reason = "graph must stay offline-pure"

[[policy.pattern]]
id = "POL-no-subprocess-shell"
language = "python"
query = "(call ...)"          # tree-sitter query, file in policy/queries/
severity = "error"

[[policy.norm]]
id = "POL-max-diff-lines"
max_diff_lines = 400          # per active ticket; restraint merges
```

Three rule kinds at alpha: `forbidden-import`, `pattern` (tree-sitter query
over `frob.lang` trees), and `norm` (diff-shape rules). Taint analysis is
explicitly out of scope for 0.1.0.

## Test obligations (`frob.toml`, `[testing]` and `[[system]]`)

```toml
[testing]
min_unit_cases = 3            # TEST002: unit edges per public symbol
min_integration = 1           # TEST003: integration edges per interface
unit_branch_cov = 90          # TEST005: per-symbol branch coverage floor
module_line_cov = 85          # TEST005: per-module line coverage floor
system_line_cov = 80          # TEST005: per-system line coverage floor

[[system]]
id = "cli-check"              # target of frob:tests <id> kind="e2e"
entrypoint = "frob check"     # documentation; e2e tests drive it via subprocess
min_e2e = 5                   # TEST004
paths = ["src/frob/check/**", "src/frob/gates/**"]   # system_line_cov scope
```

Binding is explicit: a test declares what it tests via `frob:tests`
directives (see docs/modules/graph.md); the gate verifies the declared node ids are
actually collected by pytest, so a deleted test cannot keep satisfying an
obligation. Coverage is recorded evidence: `make coverage` runs pytest-cov
then `stamp_coverage`; `frob check` only reads the stamp and coverage.xml.
A stale or missing stamp is itself a violation (TEST006) -- the gate never
silently passes because tests were not run.

## Delta baseline (agent workflow, T-0095/T-0107)

`frob check` reports every kept violation on every run -- most of them
pre-existing legacy debt (ticketed, not new), not signal for the agent
driving one ticket to green. `stamp_baseline` records the current
violation set's fingerprints (rule + file + message digest, via
`violation_fingerprint`) plus a per-file content hash to `.frob/baseline`.
`delta_violations` filters a later violation set down to fingerprints
absent from that stamp; `is_baseline_stale` detects when any hashed file
has changed since the stamp, the same staleness shape `stamp_coverage`
uses for `.frob/coverage-stamp`.

Wired at the CLI as `frob check --stamp-baseline` (record and exit) and
`frob check --delta` (gates stage reports only new violations; see
docs/commands/check.md). A missing or stale baseline degrades `--delta` to
the full, unfiltered set with a warning -- this is an agent-facing filter
only, opt-in, never a silent narrowing of the human-facing report.

## Ratchet pools (T-0569)

A warn-first detector this repo has turned on more than once (INV 765,
COV ~160, PII 336, DEAD 51 findings at once) needed a hand-managed
calibrate-then-burndown campaign every time: eyeball every finding, waive
the genuine ones, fix or ticket the rest, and hope no NEW finding of the
same shape sneaks in unnoticed among the pile. Ratchet pools (T-0569)
replace that with a self-draining mechanism: freeze the CURRENT findings
of a rule as a tracked baseline, and any finding NOT in that baseline
(i.e. anything new) reports at error severity immediately instead of
quietly joining the warn pile.

`frob.gates._ratchet` (`src/frob/gates/_ratchet.py`) implements the
mechanism as a self-contained, additive module:

- **Storage**: `frob-ratchet.lock.json` at the repo root -- committed to
  git, same "outside `.gitignore`'s reach" posture as
  `frob-coverage.lock.json` (T-0545) -- holds one `RatchetPool` (a
  `rule_id` plus a tuple of `RatchetEntry(key, baselined)`) per rule that
  has ever been snapshotted. `key` is a stable per-finding location
  string (e.g. `path:line`); `baselined` is the date the entry first
  entered the pool.
- **`frob pool snapshot RULE --key KEY [--key KEY ...]`**
  (`snapshot_ratchet`) merges the given keys into `RULE`'s pool: a
  genuinely new key gets stamped with today's date, an already-baselined
  key keeps its ORIGINAL date (re-running snapshot is idempotent, not a
  bulk re-date every time).
- **`frob pool clear RULE --key KEY --reason TEXT`**
  (`clear_ratchet_entry`) is the only way to remove a baselined entry --
  `Err(ClearReasonMissing)` if `--reason` is blank, mirroring the
  `frob:waive` discipline this repo already holds itself to (a suppression
  with no stated reason is a silent discard). This is the TICK004-style
  "eventual disposition" every baselined finding still owes: fix it, then
  clear it, don't leave it frozen forever with no accounting.
- **`resolve_ratchet_severity(rule_id, finding_key, lock)`** is the
  integration point: `"warn"` if `finding_key` is already baselined for
  `rule_id`, `"error"` if it is new. It does not decide WHICH rules are
  ratcheted -- `ratchet_enabled_rules(root)` reads that from `[gates.ratchet]
  rules = [...]` in `frob.toml` (opt-in per rule, empty/absent means no
  rule is ratcheted, matching every other per-section `frob.toml` reader's
  missing-is-default posture, e.g. `load_arch_config`).

**Wired into a live gate (T-0594)**: `INV006` (`inv006_gate`,
`src/frob/gates/__init__.py`) is the first rule opted into
`[gates.ratchet] rules = ["INV006"]` in this repo's own `frob.toml`.
`inv006_gate` loads `ratchet_enabled_rules(root)` and (only when INV006 is
enabled) `load_ratchet_lock(root)` once per run, then
`_inv006_src_violations` calls `resolve_ratchet_severity("INV006", rel,
lock)` per file to pick the reported `Severity` (`rel`, the finding's
repo-relative path, is INV006's stable key -- findings are file-level,
`line=0`). This repo's own 29 pre-existing INV006 findings at the point
ratcheting was enabled were baselined with `frob pool snapshot INV006
--key <path> ...` so they keep reporting WARN; any file with a NEW,
unbound exclusivity claim now reports INV006 at ERROR instead of quietly
joining the warn pile. The storage format, CLI, and severity-resolution
contract are tested against synthetic rule ids in
`tests/test_gates_ratchet.py`/`tests/test_pool_runner.py`; the live-gate
integration itself (opt-in config read, baseline hit stays warn, fresh
finding errors, calibration against this repo's own committed
`frob-ratchet.lock.json`) is tested in `tests/test_gates.py`. Any other
warn-first rule can opt in the same way: add its id to `[gates.ratchet]
rules`, baseline its current findings with `frob pool snapshot`, and call
`resolve_ratchet_severity` at that gate's own severity-decision call
site -- no new mechanism needed.

## Data models

<!-- frob:describes src/frob/gates/_models.py::Severity -->
<!-- frob:describes src/frob/gates/_models.py::WaiverRef -->
<!-- frob:describes src/frob/gates/_models.py::Violation -->
<!-- frob:describes src/frob/gates/_models.py::GateStats -->
<!-- frob:describes src/frob/gates/_models.py::GateReport -->
<!-- frob:describes src/frob/gates/_models.py::GateConfig -->
<!-- frob:describes src/frob/gates/_models.py::PreworkSweep -->
<!-- frob:describes src/frob/gates/_models.py::SystemSpec -->
<!-- frob:describes src/frob/gates/_models.py::TestPolicy -->
<!-- frob:describes src/frob/gates/_models.py::CoverageData -->

- `Severity` -- a violation's exit-code weight: `error` fails
  `frob check`, `warn` does not.
- `WaiverRef` -- the `frob:waive` edge that suppressed a violation, kept
  on the `Violation` so waivers stay visible debt rather than silence.
- `Violation` -- one gate finding: rule id, severity, site, and a message
  that always embeds its own remedy command.
- `GateStats` -- per-gate counters (violation counts, timing, skipped
  gates) attached to every `GateReport`.
- `GateReport` -- the merged result of `run_gates`: kept violations,
  waived violations, and stats.
- `GateConfig` -- everything `run_gates` needs to load state and select
  which gates run (root, base ref, ticket, gate subset). **The `drift`
  gate (DRIFT001/DRIFT002) always evaluates regardless of `gates`/`--only`
  narrowing (T-0265)**: `_build_jobs` unconditionally folds a `drift` job
  into the selected set even when a caller's `gates` subset omits it (e.g.
  a ticket-scoped `--only scope` pre-flight check), so a narrowly-scoped
  run can never report clean on a dangling edge (DRIFT002) that a full,
  unscoped `frob check` on the identical tree would catch -- one
  authoritative answer to "does this edge endpoint resolve"
  (`test_gate`'s own docstring: "DRIFT002 already covers TESTS edges"),
  not two evaluation paths that can silently disagree. This costs nothing
  extra: `st.snapshot`/`st.lock` are already unconditionally loaded for
  every gate run before selection is even applied.
- `PreworkSweep` -- a recorded dup+xref sweep over a ticket's scope,
  stamped at `frob ticket start` time; PRE001's evidence. T-0584: also
  carries `partial` (the sweep hit its budget before finishing every scope
  pattern) and `pending_patterns` (the patterns still left to scan) --
  `prework_gate` treats a partial sweep as provisionally clean as long as
  its `digest` still matches, and `sweep_ticket` resumes from
  `pending_patterns` on its next call rather than rescanning from scratch.
- `SystemSpec` -- one `[[system]]` entry: an e2e-tested surface, its
  entrypoint, and its coverage scope for TEST004/TEST005.
- `TestPolicy` -- the `[testing]` table: all test-obligation floors
  (unit case counts, coverage percentages), each overridable.
- `CoverageData` -- parsed `coverage.xml` mapped onto the snapshot:
  per-symbol branch and per-module line percentages.

```python
class Violation(BaseModel):
    rule: str                   # "DRIFT001", "POL-..."
    severity: Severity          # ERROR | WARN
    file: str
    line: int
    message: str                # human sentence incl. the fix command
    waived: WaiverRef | None    # populated when a frob:waive matched

class GateReport(BaseModel):
    violations: tuple[Violation, ...]
    waived: tuple[Violation, ...]
    stats: GateStats            # counts per gate, timing per gate

class GateConfig(BaseModel):
    root: Path
    base: str = "main"
    ticket: str | None = None   # explicit --ticket
    gates: frozenset[str]       # subset selection for frob check --only

class Diff(BaseModel):
    base: str
    hunks: tuple[Hunk, ...]     # file, span, touched symrefs (resolved
                                # against the snapshot by frob.gates)

class PreworkSweep(BaseModel):
    date: date
    dup_findings: int
    xref_hits: tuple[str, ...]
    digest: str                 # over scope file hashes at sweep time
    partial: bool = False       # T-0584: budget exceeded before finishing
    pending_patterns: tuple[str, ...] = ()  # scope patterns left to scan

class Invariant(BaseModel):
    id: str                     # ^INV-\d{3}$
    statement: str
    criticality: Criticality
    evidence: tuple[str, ...]

class CollectedTests(BaseModel):
    node_ids: frozenset[str]    # from pytest --collect-only -q, cached

class SystemSpec(BaseModel):
    id: str
    entrypoint: str
    min_e2e: int
    paths: tuple[str, ...]

class TestPolicy(BaseModel):    # [testing] table, all floors overridable
    min_unit_cases: int = 3
    min_integration: int = 1
    unit_branch_cov: int = 90
    module_line_cov: int = 85
    system_line_cov: int = 80

class CoverageData(BaseModel):
    source_sha: str             # coverage.xml sha recorded by the stamp
    symbol_branch: Mapping[str, float]   # symref -> percent
    module_line: Mapping[str, float]     # package path -> percent
```

## Error types

<!-- frob:describes src/frob/gates/_models.py::GateError -->
<!-- frob:describes src/frob/gates/_models.py::CoverageError -->
<!-- frob:describes src/frob/policy/_models.py::PolicyError -->
<!-- frob:describes src/frob/gates/__init__.py::GateOrderDriftError -->

- `GateError` -- failure values `run_gates` and its loading steps
  (graph build, ticket queue, lock, git diff) can return.
- `CoverageError` -- failure values `load_coverage`/`stamp_coverage` can
  return (missing `coverage.xml`, malformed XML).
- `PolicyError` -- failure values `frob.policy`'s rule loading and
  matching paths can return (malformed rule, non-compiling tree-sitter
  query).
- `GateOrderDriftError` (T-0839) -- raised, not returned as a `Result`:
  `_merge_canonical_order` hits it when the process/thread pool result
  dict names a gate absent from `_CANONICAL_GATE_ORDER`. This is
  unrecoverable wiring drift (a gate registered in `_ALL_GATES`/
  `_build_jobs` but never added to the order tuple) -- exactly the T-0788
  incident, where the "compliance" gate briefly had this gap and its
  findings would have been silently dropped from `frob check` output. A
  module-level `assert set(_CANONICAL_GATE_ORDER) == _ALL_GATES` next to
  the order tuple's definition also catches the same drift at import
  time, before any gate ever runs.

```python
class GateError(ErrorSet):
    GraphUnavailable = "Graph build failed; gates cannot run"
    GitFailed        = "git diff/merge-base failed"
    NoTicketContext  = "Scope gate requested but no active ticket resolved"

class PolicyError(ErrorSet):
    MalformedRule = "Policy rule failed schema validation"
    BadQuery      = "tree-sitter query does not compile"

class InvariantError(ErrorSet):
    Malformed   = "Invariant file failed schema validation"
    DuplicateId = "Two invariant files share an id"

class CoverageError(ErrorSet):
    Missing  = "No coverage.xml/stamp found; run make coverage"
    Malformed = "coverage.xml could not be parsed"
```

## frob fmt: directive canonicalization (T-0441)

`frob.gates._fmt_directives` is a canonical-form line-wrap/UN-wrap
normalizer for `frob:` directive comment lines, exposed as `frob fmt
[path] [--check] [--json]`. It exists so a long `frob:waive`/`frob:debt`/
etc. reason never has to fight ruff E501 by hand: canonical form is the
FEWEST physical lines that keep every line within the project's line
length, using T-0286's own trailing-backslash continuation syntax. The
operation is two-directional and idempotent in both directions:

- `fmt(single-line-too-long)` -> minimally wrapped (word-boundary splits,
  each non-final physical line ending in `` \ ``).
- `fmt(wrapped-but-now-fits)` -> joined back to one physical line (the
  reason got shorter, or the limit got raised, or it was split
  unnecessarily to begin with).

T-0972: `canonicalize_text`'s own two-pointer merge scan over lines/runs
picked up a reasoned `frob:waive PERF003` (position-free token detector
false-positive: it is one O(n) pass, not a cross join) -- no behavior
change.
- `fmt(already-canonical)` -> no-op.

T-0984: fixed an off-by-one in `_canonical_lines`' word-boundary cut
search (`rfind(" ", 0, budget + 1)` let a space AT index `budget` itself
match, and keeping that space on the earlier line produced a physical
line one column over `limit`) -- this is the bug T-0972 found wrapping to
89 columns against an 88-char limit and touching ~180 out-of-scope files
on a repo-wide run. Fixed by excluding index `budget` from the search span
(`rfind(" ", 0, budget)`); regression coverage in
`tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984` pins the
at-limit/one-under/one-over boundary plus the specific space-at-budget
shape that triggered the overflow.

Public API (`src/frob/gates/_fmt_directives.py`):

- `marker_for(path) -> str | None` -- the line-comment marker (`#`, `//`)
  for a file's suffix, or `None` for an unsupported language. T-0441 scope
  is `#`/`//` line comments only; a directive written inside a `/* */`
  block comment is left untouched.
- `read_line_length(root) -> int` -- reads `[tool.ruff] line-length` from
  `root/pyproject.toml`, falling back to ruff's own default (88). Known
  limitation: this is ONE project-wide limit sourced from ruff's config; a
  genuinely per-language limit (`rustfmt.toml`'s `max_width`, a
  `.prettierrc`'s `printWidth`, clang-format's `ColumnLimit`) is not wired
  up -- every supported language wraps against this single limit today.
- `canonicalize_text(text, *, path, limit) -> str` -- rewrites every
  `frob:` directive run in `text` to canonical form; non-directive
  comments and all code are untouched byte-for-byte. T-0985: a run whose
  logical text ends in a `# noqa`/`# noqa: CODE` pragma is a deliberate
  escape hatch (content is one unbreakable token, e.g. a long dotted
  pytest node id with no space to wrap at) and is left byte-identical
  rather than force-wrapped -- previously the pragma comment was treated
  as ordinary directive text and force-wrapped anyway, defeating its
  purpose.
- `format_paths(root, *, check_only, limit=None) -> FmtReport` -- walks
  `root` (via `frob.excludes.iter_files`, so the usual excluded/pruned dirs
  are skipped) and canonicalizes every supported file; `check_only=True`
  reports without writing (`frob fmt --check`, CI-friendly, exits 1 if
  anything is non-canonical).

**T-0985: repo-wide recompaction deliberately deferred.** A large slice of
this repo's own `frob:` directive comments predate T-0441's "fewest
physical lines" canonical form (hand-wrapped, or wrapped by an older/
looser tool version) -- a fresh `frob fmt .` still reports ~260 files as
non-canonical purely from this legacy layout, even after the noqa fix
above. Actually performing that one-time repo-wide recompaction was
investigated and found UNSAFE today: rewrapping shifts word-wrap
boundaries, and in some files this places a `frob:`-shaped prose token
(inside a `reason="..."` string, referring to `frob:describes` by name
rather than invoking it) at the start of a continuation line, which
`frob.graph.dsl.parse_directives` misparses as a bogus new directive --
see the filed follow-up tickets (DSL continuation-parsing fix, then the
deferred recompaction itself) for the full repro. `frob fmt`'s own
idempotence (running it twice is a no-op) holds regardless of whether
the legacy files have been recompacted yet.

Folding an existing continuation run back into one logical string reuses
`frob.graph.dsl.fold_comment_runs` -- T-0286's own continuation fold,
extended with a physical-line-count 4th tuple element so a caller that
needs to REWRITE physical lines (not just read the folded text, which is
all `frob.graph.dsl.parse_directives` needs) knows exactly which lines a
logical directive's current form spans. `_fold_continuations` is now a
thin wrapper over `fold_comment_runs` that drops the count -- one fold
implementation, not two.

**CRLF preservation (T-0441 review round 1 fix).** `format_paths` reads
and writes through the plain `open()` builtin with `newline=""`
(`pathlib.Path.read_text`/`write_text` only gained a `newline=` parameter
in Python 3.13; this repo targets 3.11) -- this disables Python's
universal-newline translation in BOTH directions. Without it, reading a
CRLF-authored file (any Windows-authored TS/Rust/C/C++ source) silently
translates every `\r\n` to `\n`, and writing back re-translates `\n` to
`os.linesep` (a no-op on Linux) -- so on a Linux worktree, a `frob fmt` run
over a CRLF file flattened EVERY line's terminator to LF, including lines
the formatter never touches, not just the directive it rewrapped.
`canonicalize_text` itself preserves each untouched physical line's own
trailing `\r` verbatim (it only ever splits on `"\n"`, never `"\r\n"`), and
re-attaches a matching `\r` to any freshly generated canonical directive
line based on that RUN's own original convention (not a single
file-global guess). `format_paths`' check-only change-detection
(`rewritten == original`) reads both sides through the same `newline=""`
transform, so it cannot report a false-positive change from a
newline-translation mismatch between the two reads.

**T-0441 known cut, closed by T-0851:** `frob check`'s own remediation-hint
half of this ticket ("directive line over NN cols; run `frob fmt` to
wrap", emitted as a `frob check` finding when a non-canonical directive
line is touched) was NOT implemented in T-0441's pass -- `src/frob/check/`
was outside its declared scope, and wiring a new gate rule into the
existing stage/rule-catalog machinery in `frob.gates.__init__` and the
check orchestrator was a separate unit of work. See "FMT001 (T-0851)"
below for the gate that closes this gap. `frob fmt --check` remains
available standalone (non-zero exit on any non-canonical file) either way.

### FMT001 (T-0851)

`frob.gates.fmt_gate` (gate name `fmt`, default-on, WARN severity,
diff-scoped). The T-0441 follow-up above: fires when a diff-touched
`frob:` directive comment line exceeds the project's configured line
length (`frob.gates._fmt_directives.read_line_length`), with a
remediation hint naming `frob fmt <path>` as the auto-fix -- the same
self-remedying-message contract as every other gate.

Additive only, by design: FMT001 never suppresses or rewrites the
underlying ruff `E501`/lint finding on the same line -- it only
*annotates* the situation with the one-command fix. A directive line over
the limit still shows up as a normal ruff finding too; FMT001 exists so an
agent chasing the ruff finding also sees the faster remedy instead of
hand-wrapping (fighting T-0286's own continuation syntax by hand) or
truncating the reason.

Detection reuses two pieces of T-0441's own machinery rather than
re-deriving them: `marker_for` (which languages/suffixes are in scope --
`#`/`//` line comments only, same as `frob fmt` itself) and
`frob.graph.dsl.fold_comment_runs` (the same continuation-run folding
`canonicalize_text` folds through, so a run's boundaries are identified
exactly once, in exactly one place). Diff scope comes from the same
`Diff.hunks` machinery TODO001 uses (`_touched_files`/hunk spans) -- only
physical lines the diff's hunks actually cover are checked, never a
pre-existing non-canonical line elsewhere in an untouched part of the
file. Only a folded run whose logical text starts with `frob:` is
checked: an ordinary long comment or a long code line never enters such a
run, so neither is flagged -- matching the gate's own remediation (`frob
fmt` only ever rewrites directive lines, so a finding named FMT001 must
mean a directive line specifically).

## Design decisions

- **Gates are pure functions over loaded state.** Load once (snapshot,
  queue, lock, diff, tests), run gates in parallel. Most gates run on a
  `ThreadPoolExecutor`; the CPU-bound giants (archgate, sys, clones, perf,
  pii_structural, secrets -- docs/audits/perf.md H3) run on a separate
  `ProcessPoolExecutor` instead, so they get real parallelism rather than
  GIL-serializing on the shared thread pool (T-0415). Results from both
  pools are merged back in a fixed gate-name order, so output stays
  byte-identical regardless of which pool finishes a given job first. No
  gate does IO; `run_gates` owns all loading.
- **Ticket context is optional; scope/pre-work gates degrade to skipped,
  not failed**, when no ticket resolves -- humans doing exploratory work on
  main are not fighting the tool. COV002 still catches unticketed diffs at
  check time, so nothing escapes; it just fails later rather than louder.
- **Every violation message embeds its remedy** ("run: frob ack <ref>",
  "run: frob ticket new ..."). Agents act on messages; a message without a
  next command is a dead end.
- **Waivers are per-site, reasoned, and reported.** Global rule disabling
  requires editing `frob.toml` in a reviewed commit.
- **Bare TODO/FIXME comments are violations** (TODO001). The habit the
  system replaces must not survive alongside it.
- **COV002 has a same-diff grace window for a ticket that just closed**
  (T-0214). Without it, closing the covering ticket while its edit is still
  uncommitted is a catch-22: the ticket moves out of `_OPEN_STATES`
  immediately, so every symbol it was covering becomes a hard "changed with
  no open ticket" error before the user has a chance to commit. The
  narrowest honest fix: a `DONE` ticket's `frob:ticket` edge still counts
  if `tickets.md` itself is part of the current diff -- i.e. the close and
  the covered edit are landing together as one change, not two. Once the
  close lands as its own commit and drops out of the diff, the grace window
  closes and a genuinely later, unrelated touch to the same symbol is
  caught exactly as before.
- **COV005 catches a directive silently rebound to the WRONG symbol, not
  just an unattached one** (T-0297). COV001 only proves a directive resolves
  to SOME symbol; it says nothing about whether that symbol is still the
  one the directive's author meant. Extracting a private helper directly
  above an existing public `def` (a common refactor shape) silently moves
  every trailing `frob:` directive that used to describe the public `def`
  onto the new private helper, because the DSL's `following`/`enclosing`
  binding always attaches to the NEAREST symbol below the comment, not the
  one the author intended -- and every other gate stays green afterward,
  since the directive still resolves. This bit twice in this repo's own
  history (`scan_tree`, `renumber_one`) and was only caught by manual
  review. COV005 is git-diff-aware and scoped to files the current diff
  touches: for each `(kind, target)` pair a directive carries in the
  current tree, it compares against the SAME `(kind, target)` pair's
  binding at `diff.base` (via `git show <base>:<file>`, reparsed) -- if that
  pair bound a PUBLIC symbol at `diff.base` and now binds a PRIVATE one, it
  is a CANDIDATE rebind, flagged as an ERROR only if the new private
  symbol's own span also overlaps one of the diff's hunks in that file --
  i.e. the private symbol carrying the directive is itself part of what
  this diff just changed, the "extracted helper directly above an existing
  def" shape the ticket describes. A `(kind, target)` pair alone is NOT a
  unique directive identity: this repo's own convention reuses one
  `frob:doc <page>#<anchor>` target across every public function a doc
  page covers, so comparing old vs new bindings FILE-WIDE (without the
  hunk-overlap restriction) flagged roughly 50 pre-existing, untouched
  private helpers that merely happen to share an anchor with some
  unrelated public function elsewhere in the same file -- the
  hunk-overlap guard is what keeps COV005 from being a repo-wide,
  diff-oblivious full scan. Files with no
  resolvable blob at `diff.base` (new files) are skipped -- there is no
  "before" to compare a new file's directives against, and COV001 already
  covers a new symbol's own missing-doc obligation. The other two
  candidate detections from the ticket -- (b) `frob:tests` evidence whose
  named test does not actually reach the bound symbol (call-graph
  reachability, ties into T-0288/T-0290's shared substrate) and (c) a
  `frob:doc #public-api` anchor specifically on a private helper -- are
  deliberately out of scope for this pass; each needs its own ticket rather
  than folding into COV005's git-diff comparison.
- **pytest collection is the evidence oracle** for test node ids, cached in
  `.frob/` keyed on test-file hashes; running tests is `make test`'s job,
  existence is the gate's job.
- **Test obligations verify existence, quantity, and measured reach -- not
  quality.** Counts and coverage floors are gameable proxies (assert-free
  tests pass them); the honest quality oracle is mutation testing, which is
  tracked in the ticket ledger (mutation testing shipped as `frob mutate`). A `pattern` policy rule
  banning assert-free test functions ships as a first defense.
- **Interfaces are derived, not declared.** Any package whose public
  symbols another package imports owes integration tests; deriving this
  from the graph means a new boundary cannot be forgotten. Pair-level
  (consumer x provider) strictness is deferred; per-provider at alpha.
- **Coverage thresholds are floors in config, not goals in prose.**
  Raising a floor is a reviewed `frob.toml` commit; lowering one is too,
  and shows up in diff review.

## Dependencies

- `frob.graph` (snapshot, lock, drift), `frob.tickets` (queue),
  `frob.policy`, `frob.lang` (pattern queries).
- git via subprocess (diff, merge-base, branch name).
- `pydantic`, `typani`.

## Integration points

- `frob.check`: `run_check` gains a gates stage; `frob check --only gates`,
  `--ticket T-0042`, `--base <ref>` flags; exit code folds into the
  existing errors-first report and `frob parse` output format.
- `frob ticket start` calls `record_prework` (dup + xref over scope).
- Pre-commit hook and CI both run `frob check`; agents run it after every
  ticket before writing a done-report.

## Phase 4 implementation notes (deviations from the design above)

The design above is otherwise as-implemented. The following are the
concrete choices made where the design was ambiguous or where a
dependency's real API did not match the sketch:

- **`WAIVE001` is derived from `GraphSnapshot.malformed`, not a separate
  scan.** `frob.graph.dsl.parse_directives` already refuses to turn a
  `frob:waive` directive lacking `reason="..."` into an `Edge` -- it
  becomes a `MalformedDirective` instead. `gates._waive001_violations`
  simply surfaces any malformed directive whose reason text mentions
  `frob:waive`. Every `Edge` with `kind == WAIVE` that reaches a gate is
  therefore guaranteed to already carry a `reason` attr.
- **`prework_gate` takes an extra `sweep: Option[PreworkSweep] = Nothing()`
  argument** beyond the doc's `(ticket, snapshot)` signature. The sweep is
  loaded state (see below) and gates must not do IO, so `run_gates` loads
  it via `gates._prework.load_prework` and passes it in.
- **`invariant_gate` takes an extra `policy_rule_ids: frozenset[str] =
  frozenset()` argument** beyond `(invariants, snapshot, tests)`, so
  INV001 can treat a loaded policy rule id as valid evidence (the doc's
  own example evidence list includes `POL-no-direct-lock-write`); without
  it the pure function would have no way to see policy state.
- **`record_prework` storage**: `frob.tickets` exposes only
  `record_failure` (a fixed "## Failure log" section), not a generic
  body-section appender, and growing `frob.tickets`'s public surface is
  out of scope for this phase. The sweep is instead stored as JSON at
  `.frob/prework/<ticket_id>.json` (`gates/_prework.py`), read back by
  `load_prework`. `PRE001` compares `sweep.digest` against a fresh
  `_scope_digest(ticket, snapshot)` (sha256 over the ticket's scope-glob-
  matched `snapshot.file_hashes` entries).
- **Hunk-to-symref resolution is reimplemented in `gates`**, not imported
  from `frob.testing._select`: `select_tests` does the same span-overlap
  match inline as part of a larger algorithm and never exposes it as a
  standalone function. `gates._touched_symrefs`/`_touched_files` are a
  documented duplicate of that overlap primitive, same posture as the
  extension-table duplicates already accepted across
  `frob.graph`/`frob.testing`/`frob.policy`.
- **TEST003 interface derivation, alpha semantics**: the graph has no
  cross-file import edges (only `frob:` directive edges and doc anchors),
  so real "package A's public symbols imported by package B" derivation
  is not available. Alpha instead treats every `src/<pkg>/<subpkg>`
  directory containing at least one public, non-test symbol as an
  interface owing `min_integration` integration `frob:tests` edges -- the
  simple, honest over-approximation the design's own "Interfaces are
  derived, not declared" note anticipates. Pair-level (consumer x
  provider) strictness is deferred.
- **TEST001/TEST002/TEST005 skip symbols in test files themselves**
  (`gates._is_test_file`, a documented duplicate of
  `frob.testing._select._is_test_file`'s heuristic) -- a public `test_*`
  function does not owe itself a unit test.
- **TEST005 system floor** is approximated as the mean of `module_line`
  percentages for files matching any of `[[system]].paths`, since
  `CoverageData` (per the doc's own model) has no separate per-system
  map; `load_coverage` only ever produces `symbol_branch`/`module_line`.
- **`frob.gates` does not re-export `PolicyRule`/`PolicyError`/
  `load_policy`/`policy_gate`.** `frob.policy` imports `Violation`/
  `Severity`/`WaiverRef` from `frob.gates._models`, so a module-level
  `from frob.policy import ...` in `frob.gates.__init__` would form an
  import cycle the first time either package is imported standalone.
  `run_gates` imports `load_policy`/`policy_gate` lazily inside its own
  body instead; callers needing policy types import them from
  `frob.policy` directly.
- **`policy_gate`'s `forbidden-import` and `pattern` rules read file
  content off disk via `Path(snapshot.root)`** plus
  `snapshot.file_hashes` (for glob-matched file listing), since the
  signature `policy_gate(rules, snapshot, diff)` carries no separate
  root parameter; `GraphSnapshot.root` already carries it.
- **`GateError` collapses every loading failure** (`frob.graph`,
  `frob.graph.lock`, `frob.tickets`, `frob.gates.invariants`,
  `frob.policy`) into one of `GraphUnavailable` / `QueueUnavailable` /
  `ConfigMalformed` / `GitFailed` / `WriteFailed`, rather than a full
  `GraphError | LockError | TicketError | InvariantError | PolicyError`
  union, to keep `run_gates`'s `Result[GateReport, GateError]` a single
  small enum callers can match on directly.
- **Severity defaults per rule** are fixed in code (`ERROR` for
  DRIFT/COV002-004/SCOPE001/PRE001/INV001-002/TEST001/TEST004/WAIVE001/
  policy rules with no `severity` override; `WARN` for COV001, TODO001,
  TODO002, TEST002/003/005). Per-rule severity overrides in `frob.toml` were
  scoped out of this phase; `PolicyRule.severity` is the only
  user-configurable severity today (via `[[policy.*]].severity`).
