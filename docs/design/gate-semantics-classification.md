# Gate semantics classification (T-1663)

Precursor pass for the T-1662 "semantics, not text" epic. For every gate
module (owning one or more rule ids from `frob.gates._waive.
_KNOWN_GATE_RULES`), records what it asserts, what it inspects TODAY, whether
its findings carry a `symref`, and a classification:

- **(a) semantic already** -- decides from a resolved AST node, a graph
  edge (import/call/DSL), or a typed model, not raw text.
- **(b) lexical but legitimately so** -- the check's own subject IS text
  (a comment's reason string, a secret-shaped literal, a directive's own
  wire format) or the target has no symbol to resolve against. No fix
  needed.
- **(c) lexical and wrong** -- decides from text/path/name matching where a
  resolved symbol or graph edge exists (or could exist) and would change
  the answer. Gets its own ticket, filed below.

This groups by MODULE, not by individual rule id, when every rule in a
module shares one detection mechanism (true for the large majority here --
one gate module is one AST pass or one graph query, emitting several rule
ids off the same walk). Where rules in a module differ in kind, they are
split out.

Table columns: **Rule ids | Module | Asserts | Inspects | symref? | Class**

## Graph/AST-resolved gates (class a)

| Rule ids | Module | Asserts | Inspects | symref | Class |
|---|---|---|---|---|---|
| COV001-007 | `_docblocks.py`, `_docptr.py` | every public symbol has a doc edge; doc pointers resolve; private-helper doc anchors are legitimate | `frob.graph` snapshot (import/call edges), AST-parsed doc anchors, resolved namespaces | yes | a |
| PLACE001 | `_docblocks.py` | a `frob:` directive binds to the nearest real symbol, not a false-fallback class | AST symbol-span lookup | yes | a |
| DRIFT001/002 | `__init__.py` (`drift_gate`) | an acked doc ref's target digest has moved since ack | `frob.graph` snapshot digests vs `LockFile` | yes | a |
| AFFECT001/002 | `__init__.py` (`affect_drift_gate`) | a diff's root touches a dependent doc/symbol without touching the dependent | `affects()` closure over the graph snapshot | yes | a |
| SCOPE001/002 | `__init__.py` (`scope_gate`) | a diff only touches files inside the ticket's declared scope globs | diff file list vs parsed scope globs (path-glob match is the correct mechanism here -- scope IS a path-glob contract) | yes | a |
| SUPPRESS001 | `_suppress.py` | a suppressed line's OTHER configured checker still reports a live diagnostic on it | resolved per-tool diagnostic output, line-joined | yes | a |
| PRE001 | `_prework.py` | pre-work dup/xref sweep ran and is fresh for the ticket's scope | recorded sweep state vs scope digest | n/a (ticket-level) | a |
| INV001-008 | `_design_invariants.py`, `invariants.py` | `frob:invariant` obligations (no_import, establishes, etc.) hold | `frob.graph` import edges / `frob.strata` design graph | yes | a |
| TEST001-017 | `_coverage.py`, `__init__.py` (`test_gate`) | every public symbol has a real, executed, assertion-bearing test; coverage/mutation/dedup obligations hold | `frob.graph` snapshot + `coverage.xml`/mutation results + parsed test ASTs | yes | a |
| BUG002 | `_mutation_evidence.py` | a bug ticket's evidence test genuinely failed at the parent commit | subprocess re-run of the test against parent commit | yes (ticket) | a |
| TODO001/002 | `_todo_fmt.py`, `__init__.py` | a `frob:todo`/bare `# TODO` binds to a real open ticket | AST/comment-directive parse + ticket ledger resolution | yes | a |
| TODO003 | `__init__.py` | a `frob:todo` deferral predates a released version bump | directive metadata vs release history | yes | a |
| DEBT001-003 | `_debt_deprecated.py` | `frob:debt` is well-formed, ticket-bound, not expired | directive parse + ticket ledger + date compare | yes | a |
| DEPR001-005 | `_debt_deprecated.py`, `_deprecated_baseline.py` | `frob:deprecated` sunset contract holds; no new caller of a sunsetting symbol | directive parse + `frob.exports`/`frob.graph` caller resolution | yes | a |
| DSL001 | `__init__.py` | a `frob:` directive parses under the DSL grammar | `frob.graph.dsl` parser | yes | a |
| WAIVE001/002/003/005/006/007 | `_waive.py`, `_waive_comments.py`, `_waive_lease.py` | a waiver is well-formed, matches a real rule id, matches >=1 real finding, isn't over-broad, ticket resolves | directive parse + live finding set + ticket ledger | yes | a |
| DEC001/002 | `_decisions_compliance.py`, `decisions.py` | a `frob:decision`/compliance obligation resolves and is honored | directive parse + resolved policy model | yes | a |
| REL001/002 | `__init__.py` (`release_gate`) | version/changelog/lock coherence; no open debt/deprecation crossing a release boundary | parsed `pyproject.toml`/`uv.lock`/`.frob-release.json` + ledger | n/a (project-level) | a |
| DOC001/002 (DOC family under `_doclink_docanchor.py`), DOC008 | `_doclink_docanchor.py` | doc links/anchors resolve to real targets | markdown AST + anchor-slug computation against target file structure | yes | a |
| DOC004-006 (DOC004 family) | `_docblocks_refs.py`, `_docptr.py` | fenced code / prose pointers (CLI invocation, config key, code symbol) resolve against live sources of truth | live argparse tree, loaded `frob.toml`, resolved import namespace | yes | a |
| DOC009 | `__init__.py`/`_docblocks.py` | an audit doc carries a dated status header | structured header field parse (a header field IS text by nature, but the check is "field present and parses as a date", not a content-text match) | yes | a |
| DOC010 | `__init__.py` | a `` `make <target>` `` prose citation is a real Makefile recipe | parsed Makefile target list vs extracted invocation token | yes | a |
| DOC011 | `__init__.py` | a `T-####`/`T-draft-<hex>` doc mention resolves to a real ticket | extracted id vs ticket ledger resolution | yes | a |
| DUP001-003 | `_dup.py` | near-duplicate code/config blocks | structural (AST-normalized) similarity, not raw text diff | yes | a |
| FUZZ001-003 | `_fuzz.py` | fuzz-target obligations hold | resolved harness entry points | yes | a |
| PERF001-011,013,014 | `__init__.py` (`perf_gate`), root-cause modules under `frob.perf` | hot-path/complexity/allocation smells | parsed AST + call-graph hot-path analysis (`frob.perf._hotpath_smells`) | yes | a |
| VET001-011, VET-JS*, VET-PY*, VET-RS*, VET-SOURCE-UNAVAILABLE, VET-TIMEOUT | `frob/vet/**` (outside `gates/`, same registry) | dependency/supply-chain structural risk | parsed manifests + resolved package graphs | yes | a |
| SYS001-004 | `_sys.py`, `_sys_selfaudit.py` | every strata design secret/capability has a code attestation | `frob.strata` design graph vs code-side directive resolution | yes | a |
| NATIVE001 | `__init__.py` | a declared `[[native]]` extension actually imports | live import attempt | n/a (project-level) | a |
| SEC001/002/003 | `_secrets.py` | see lexical-legitimate table below (SEC004 is directive-malformed, same family) | -- | -- | see (b) |
| TICK001/002/003/004/007/008/009/010 | `_tickets_gate.py` | ledger state-machine/hygiene invariants (stale archive, queue rot, undispatched-stale, unknown fields, scope-breadth, stale lease) | parsed `Ticket` pydantic models + ledger state machine | n/a (ticket-level) | a |
| TICK011 | `_tickets_gate.py` | a Done report's disclosed cut names a real ticket or an explicit no-ticket-needed reason | phrase-scan over Done-report prose, THEN a ticket-id resolution against the ledger | n/a | b (see below -- the phrase-scan half is a legitimate heuristic trigger, not the actual pass/fail decision; the decision is the id resolution) |
| FFI001/002 | `_ffi_boundary.py` | pyo3 cross-boundary raised-type declarations match the observed Rust-side raises | `frob.arch._ffi` AST scan of both `.rs` and `.pyi` sides | yes | a |
| RENDER001 | `_render_lint.py` | no bare stdout write outside `frob.render` | AST `ast.Call` match on `print`/`click.echo`/`sys.stdout.write` (matches call-target name via AST, not text substring; a `def print(...)` shadow or renamed import is a known, accepted false-negative gap of the same shape as WALK001 below) | yes | a (with the WALK001-shaped attribute-name caveat -- see WALK001 entry) |
| GATE (`_gate_cache.py`, `_cache_gate.py`) | n/a (infra, not a rule id) | -- | -- | -- | a |

## Legitimately lexical (class b)

| Rule ids | Module | Asserts | Inspects | symref | Reason legitimate |
|---|---|---|---|---|---|
| SEC001-004 | `_secrets.py` | a tracked file contains a real-looking credential/token, or an unmarked one | entropy/pattern scan over raw file text | no (file-line, not symbol) | The subject genuinely IS unstructured text -- a credential has no AST node or graph edge to resolve. A `frob:secret-fake reason="..."` marker is itself a textual escape hatch by design (see the module's own scoping note on why it deliberately does NOT reuse the `frob:secret` DSL verb). Legitimate. |
| EXCL001 | `_exclude_hazard.py` | a `.git/info/exclude` entry shadows tracked source | glob-pattern-vs-tracked-file-list match | no (path-level) | `.gitignore`-style shadowing IS a path-glob-vs-file-list question; there is no richer semantic model for "does this glob pattern shadow this path" than pattern matching itself. Legitimate. |
| `frob fmt` directive-wrap (no independent rule id family beyond DSL001/WAIVE001, `_fmt_directives.py`) | `_fmt_directives.py` | a `frob:` comment's line-wrap is canonical | text reflow of the directive's own reason string | n/a | The subject is literally the wrapping of a text string. Legitimate. |
| `_rule_id_scan.py` (drift-lock generator behind the `_KNOWN_GATE_RULES` literal; not itself a rule id) | `_rule_id_scan.py` | every `rule="..."`/`rule=CONST` literal in gate source is registered | regex/text scan over `src/frob/gates/**` and `src/frob/vet/**` source for the literal `rule=` pattern | n/a | This scanner's OWN job is "what rule-id string literals exist in source" -- that is a text-authority question by construction (it is the generator that keeps `_KNOWN_GATE_RULES` in sync), not a case where a resolved symbol would give a different or better answer. Legitimate. |
| SEC004 | `_secrets.py` | a `frob:secret-fake` marker is well-formed (has `reason=`) | directive-comment text parse | n/a | Directive wire-format parsing is inherently textual (parsing IS reading text into structure); the DECISION it gates (malformed marker) has no other substrate to check against. Legitimate. |
| TICK011 (phrase-scan trigger half) | `_tickets_gate.py` | a Done report's prose plausibly discloses a cut | conservative phrase list over Done-report free text | -- | Free-text disclosure detection has no AST/graph substrate to resolve against -- English prose is not code. The ACTUAL pass/fail decision downstream (does a named id resolve in the ledger) is already class (a); only the trigger heuristic is textual, and it is explicitly WARN-tier, first-turn-on, precisely because it is a heuristic. Legitimate as a trigger, not as the decision. |
| WAIVE004 (stale/unnecessary waiver half) | `_waive.py` | a waiver's rule id currently matches 0 live findings | live finding-set membership test (structurally a set lookup, not text matching, despite scoring high on the raw-lexical-signal heuristic in the ticket's shortlist -- the "and" in `_waive.py`'s high import count is driven by directive PARSING, which is legitimately textual per the same reasoning as SEC004/DSL001) | yes | Directive parsing is textual by necessity (see SEC004); the finding-membership test itself is a set operation over already-resolved violations. Legitimate. |

## Lexical and wrong (class c) -- tickets filed

| Rule id | Module | Wrong today | Fix direction | Ticket |
|---|---|---|---|---|
| REF001 | `_refs.py` | Inbound reference decided by full-path or bare-basename TEXT mention across every tracked file's prose/strings -- misses aliased imports, constructed paths, dynamic dispatch (false dead); counts a bare prose/changelog mention as a real reference (false live). | For code targets: resolve via `frob.graph.callgraph`'s import/call edges. Keep `frob:used-by` as the sole declared non-code channel, each declaration verified bidirectionally. Report UNRESOLVED (T-1664) where reachability cannot be decided. | T-1665 (this epic, already filed -- no new ticket needed) |
| DEAD001/OPAQUE001 (symref-hole check named in T-1663's own body) | `_dead_symbols.py`, `_opaque.py` | Both modules score fully semantic on the mechanism heuristic (AST/graph-heavy), but neither finding today carries a `symref` field distinguishing which specific symbol inside a file is dead/opaque -- a waiver against either rule id is a file-wide amnesty, silently covering every OTHER symbol in the same file too. This is not a lexical-vs-semantic defect (the DECISION is already correctly semantic) but it is the exact "waiver blast radius" failure T-1663 was asked to flag alongside classification. | Add a per-symbol `symref` to `DeadSymbolViolation`/`OpaqueViolation` construction so a `frob:waive DEAD001` / `frob:waive OPAQUE001` binds to one symbol, not one file. | T-1683 (filed) |

No other module in the survey combines (1) a resolvable symbol/graph edge
that the current implementation ignores in favor of text/path/name matching,
with (2) a live, reachable false-positive or false-negative shown by
inspection. WALK001 was flagged as a T-1663 "already evidenced" candidate;
direct inspection of `_walk_lint.py` shows it is AST-based (`ast.Call`
matching) and import-alias-aware for bare calls (`_collect_import_bindings`
tracks `from os import walk as w`) -- it is NOT a raw-text scan. Its one
real gap (attribute-name matching, e.g. `.rglob(`, cannot distinguish a
`pathlib.Path.rglob` from an unrelated object with a same-named method,
since Python has no static type info here without a type checker) is the
same class of limitation as RENDER001's `print`-shadow gap: an accepted,
disclosed limit of AST-without-types analysis, not a text-match defect a
graph edge would fix. Reclassified (a), not (c) -- the ticket's shortlist
was itself a hint to verify, not a verdict, and this one did not hold up
under inspection.

## Summary

- (a) semantic already: the large majority of rule ids (COV, DRIFT, AFFECT,
  SCOPE, SUPPRESS, PRE, INV, TEST, BUG002, TODO, DEBT, DEPR, DSL001, WAIVE
  (matching half), DEC, REL, DOC (link/anchor/pointer families), DUP, FUZZ,
  PERF, VET, SYS, NATIVE001, TICK (state-machine half), FFI, RENDER001).
- (b) legitimately lexical: SEC001-004, EXCL001, `frob fmt` wrap,
  `_rule_id_scan.py`'s generator, TICK011's trigger phrase-scan, WAIVE004's
  parsing half.
- (c) lexical and wrong: REF001 (T-1665, this epic). One adjacent
  symref-blast-radius defect filed as T-1683 (DEAD001/OPAQUE001).

## Method note

Classification was done at module granularity (one detection mechanism per
module, in this codebase's own convention of one gate family per file) with
targeted source inspection of every module the ticket's own lexical-import-
count shortlist flagged, plus the two named candidates (REF001, WALK001) and
the four prose-as-declaration detectors named in the ticket (DOC004/DOC006
family -- `_docblocks_refs.py`, `_docptr.py`, `_doclink_docanchor.py`,
`invariants.py`). The shared "this span is explanatory text, not a
declaration" substrate those four could reuse is a DSL-parser concern
(T-1633/T-1640 lineage), not a per-rule semantics defect on its own --
tracked there, not re-filed here.
