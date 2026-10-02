# Lint requirements: the queries a universal IR must answer

Status: research input for code-model.md section 5 (structural IR) and rules.md
section 3 (universal vs language rules). ASCII only. Derived bottom-up from every
rule that exists (v1, 667 ids), is landed (v2 crates), or is designed (grimble,
crunk). Nothing here was executed (no cargo, no frob); every claim about landed
code is from reading the source and is marked "by reading".

## 0. Honest status line

- Universe (denominator): 667 v1 rule ids (notes/v1/gates-and-rules.md, 129
  distinct id prefixes plus the hyphenated VET-*, HOST-BLAST, SEC-CVE-FINGERPRINT), 33 landed v2 rule ids (grep of `id = "..."` in
  crates/, of which DEM001/DEM002/FIXT001/XRL001 are test fixtures), the designed
  v2 families (EXC002-015, NARR001-005, PM001-029, REL003, DEC004, DEPR, BIND,
  SYS001-009, CAP001-003, GPOL), and crunk's 13 families (about 30 ids).
- Mapped: all of them, in section 2 (37 family rows, R01-R37). The prefix-by-prefix
  checklist is section 10; its completeness is checked there against the v1 file.
- Pending: 0. Blocked: 0. Soft spots: per-id detail of the 249 v1 web ids and the
  55 REL ids is by family summary (v1's own catalog says "reserved"); the crunk
  rules are from the survey (notes/crunk.md), not crunk's source.
- Headline results (details below):
  1. 47 named queries in 5 groups cover every KEEP/MERGE rule and every designed
     rule. 17 are total given text, files and names (the milestone-1 baseline);
     11 are interval-valued; 19 more are capability-gated. Counted by feature:
     8 queries need no language feature at all, 33 name a required one
     (names and static call/reference sites gate the most).
  2. The one structural addition the IR needs beyond a node tree is an ANSWER
     LATTICE: `Exact | Bounds{lo,hi} | Unknown | NotApplicable`. Rules are
     classified by polarity (fire on presence, fire on absence, equality,
     threshold); polarity decides which bound a rule may fire on and which it may
     certify clean on (section 3). That single mechanism is "unmeasured is not
     zero".
  3. The landed Rust adapter silently answers three polarity-sensitive queries
     with one bound (calls, public_api, comments in digests); section 9 lists 19
     gaps found by reading.

## 1. Vocabulary used in the tables

Fact codes (what a rule reads). Syntactic = decidable from one parse (S);
semantic = needs name resolution, types, evaluation, or external data (M).

| Code | Fact | Class |
|---|---|---|
| F | artifact membership, path, size, language, parse status | S |
| sym | declared symbols: kind, name, span, parent, nesting | S |
| vis | visibility or export status of a symbol | S (modifiers) or M (re-exports, export lists) |
| attr | attributes, annotations, decorators, pragmas on a symbol | S |
| doc | doc text attached to a symbol (comment-before, docstring, doc attribute) | S |
| cmt | comments: position, kind (line, block, doc-outer, doc-inner, html), text | S |
| prose | markdown structure: headings, links, fences, code spans, tables, html comments | S |
| imp | import declarations (syntactic), then resolved import edges | S then M |
| call | call sites (syntactic), then resolved call edges | S then M |
| ref | name uses / mentions (a superset of calls: values passed, operands of composition) | S then M |
| lit | literals and string contents (typed: number, color, length, string, regex) | S |
| ctl | control structure: loops, branches, nesting, returns, try, cyclomatic proxy | S |
| fld | members: fields, params, return and field type TEXT, enum variants | S |
| tok | normalized token or AST stream (digests, clone detection) | S |
| txt | raw text and layout (line length, whitespace, any bytes) | S |
| kv | structured data keys (TOML, JSON, YAML manifests and configs) | S |
| emb | embedded-language regions (md fences, SQL in strings, JSX/CSS, quasi-quotes) | S |
| opq | opaque regions: macro token trees, splices, eval, preprocessor, dynamic dispatch | S (detect), M (see through) |
| tst | test items (a convention: attribute, name, path, directive pair) | S (convention) |
| eff | effect sites: a call resolved to a library function with a capability atom | M |
| typ | types of expressions, trait/class impl sets, dispatch targets | M |
| cst | constant evaluation (literal folding, const refs) | M |
| bind | cross-language binds (symbol a is symbol b across a boundary) | M |

Side inputs (not IR; they join to the IR through symref, file, span):
tkt (ticket ledger), lock (frob.lock, grimble.lock), diff (changed files and the IR
at two revisions), cfg (config tables), cov (coverage data), git (history), reg
(registry yaml), grm (grimble model), run (a subprocess result: tests, mutation,
render, osv, tailwind), net (external data).

Columns of the family table. XF: needs cross-file info. XL: needs cross-language
info (Y* = only through `binds` edges, which grimble supplies). S/M: the strongest
class among the facts read. Pol: rule polarity, defined in section 3: P+ (fires
on presence of a bad thing), P- (fires on absence of a good thing), P0 (equality
of two digests or sets), Pn (threshold on a count or metric), Pc (closure or
cycle), "--" (reads no IR).

## 2. Rule-family table

Ids in parentheses are v1 unless prefixed v2. One row can absorb many ids; a v1
id appears in exactly one row (the section-10 checklist proves it by script).

| Row | Family (ids) | Facts read | XF | XL | S/M | Pol |
|---|---|---|---|---|---|---|
| R01 | DRIFT (v2 DRIFT001-003; v1 DRIFT001/002, COV005 rebinding) | sym, tok(sig/body/doc facets), prose(headings, section digest), lock, directives(doc edges), nearest-heading edit distance | Y | Y (any-language symbol to md anchor, by symref only) | S | P0 (digest equality); dangling is P- on symbol existence, exact |
| R02 | AFFECT (v2 AFFECT001; v1 AFFECT001/002) | sym, vis, tok(sig), reverse closure of call/ref edges, containers, lock(acked_at), doc anchors | Y | Y* | M (edge resolution) | P+ over the HI bound of dependents (a missed dependent is a silent pass) |
| R03 | Doc coverage (v2 DOC001; v1 COV001, COV007, COV010, COV009, DOC001 obligations) | sym, vis, doc, attr(`#[doc]`), directives(doc), entrypoint symbols | N (DOC001) or Y (anchor groups) | N | S, M if vis needs re-exports | P+ over public_api membership |
| R04 | Test reach (v2 COV001, TEST001, COV003 alias; v1 COV006, TEST001) | sym, vis, tst, forward closure over call+ref edges from tests, directives(tests), resolve_symref | Y | Y* (py test to rust symbol) | M | P- (no test reaches: fire iff HI has none) |
| R05 | Diff accountability (v1 COV002, COV008, LANDPARITY001, WIRE001/002; v2 touched-set) | diff (IR at 2 revisions: changed symbols by digest), directives(ticket), tkt/lease scope, referencers of new symbols | Y | N | S (digest diff), M (callers) | P+ (change unowned), P- (WIRE001: no non-test caller, fire iff HI empty) |
| R06 | Test tiers and evidence (v1 TEST002-004/007/009, TEST005/006/008/011/012/017/019, TEST015, TEST016, TEST018, TESTMOCK) | directives(tests kind), package ownership, cov (file+line hits joined to symbol spans), call(assertion vocabulary in test bodies), run(mutation) | Y | Y | M (coverage, mutation external) | Pn (counts/floors); TEST015 is P- on assertion calls |
| R07 | Invariants (v2 INV001/002; v1 INV001-011, INV051, INVLVL001) | directives(invariant), F(invariants/*.md), imp (forbidden-import with crate/glob matching), ref/call (INV011 reach of guarded constant), grm (INV051) | Y | N | S (INV001/002), M if import must resolve | P+ (forbidden import exists), P- (anchor missing) |
| R08 | Doc links (v2 DOC002; v1 DOC002/003/008/010/011) | prose(links, headings, slugs), F(target exists), cmt(html) | Y | N | S | P+ (broken link) |
| R09 | Doc pointers (v1 DOC004/005/006/007/012/013/014, ENV001, PKG001-003) | prose(code spans, fences), emb(fenced code), pointer resolution to symbol, file, ticket id, make target, CLI command; cfg(command tables) | Y | Y (md to any language) | M | P- (pointer resolves: fire iff HI has no target) |
| R10 | Enumeration drift (v1 DOCENUM001, DOC013/014, NEGEXIST001) | prose(member lists, tables), fld(enum variants / collection literal items), cst | Y | Y | M (const eval of the real collection) | P0 (set equality) |
| R11 | References and orphans (v2 REF001 ticket ref; v1 REF001-003, ROOT001) | F, references_to(file) from imports, md links, directives(used-by), cfg paths; tkt | Y | Y | M | P- (zero inbound: fire iff HI empty) |
| R12 | Comment hygiene (v2 TODO001/002, NARR001-005; v1 TODO001-003, NARR001, DOCARCH001/002, CPLACE001/002, DSTACK001) | cmt(kind, text, line count, doc vs plain, adjacency), directives, tkt standing | N | N | S | P+ (marker present), Pn (line caps) |
| R13 | Exceptions (v2 EXC001-015; v1 WAIVE001-012, DEBT001-003, DEPR001-004/006, SYSWAIVE002/003, RELWAIVE002, SEC004) | directives bound to symbol spans (enclosing or following), span containment of other rules' findings, body digest vs lock, tkt standing, `until` dates, full re-evaluation of every other rule for staleness | Y | N | S | P0/P+ policing; EXC013 stale is P- over ALL rules' output and inherits their Unresolved |
| R14 | Parse and directive grammar (v2 PARSE001, DSL001/002; v1 PARSE001/002, DSL001, PLACE001, TEST010, FMT001/002, LANG001-004) | parse status with error spans, cmt, directive tokens, adapter capability matrix | N | N | S | P+ |
| R15 | Import cycles (v2 CYCLE; v1 CYCLE001) | imp with scope and time (module, function-local, type-only; static, deferred, dynamic), resolved edges, SCC | Y | N (cross-language cycles only via binds) | M (import resolution) | Pc: cycle exists is P+ on LO edges; acyclic claim needs HI edges |
| R16 | Size and shape metrics (v1 ARCH001, ARCH101-103, LARGE001, LANDPARITY002; v2 designed metric core) | ctl (loops, branch arms, max nesting, cyclomatic proxy), span lines or token count, fld (methods, fields), receiver-field access (LCOM4), imp count (coupling) | N | N (thresholds are per-language idiom) | S | Pn (max-type: fire on LO) |
| R17 | Layering and owners (v1 ARCH104 layering, SYS003; v2 grimble ARCH, SYS004) | imp and call/ref edges between OWNER sets (path+qualname globs), owner(sym), declared flows | Y | Y | M | P+ (edge in a forbidden direction: LO fires, HI certifies clean) |
| R18 | Dead code (v1 DEAD001; v2 DEAD) | sym, vis, references_to, entrypoints, opq | Y | Y* | M | P- (zero references: fire iff HI empty) |
| R19 | Clones (v1 DUP001-003, rungs R1-R7; v2 R1-R5) | tok (R1 token hash; R2 alpha-renamed needs binder analysis; R3/R4 AST shape; R5 def-use graph), diff | Y | Y (R5 only; R1-R4 miss cross-language) | S (R1,R3,R4), M (R2, R5) | Pn (similarity >= t, verified pair) |
| R20 | Pattern and policy rules (v1 OPAQUE001, FORBID001-003, PROTO001-005, POL000, POL*; v2 POL, GPOL) | pattern_match over raw tree or IR, call+callee vocabulary, lit args, opq, ordered calls (PROTO) | per rule | N | S (pattern), M if callee path must resolve | P+; POL000 zero-match is P- over the subject count |
| R21 | Lexical security (v1 SEC001-003/005, SEC110, SEC-CVE-FINGERPRINT-001, CVEFP001, PII011) | txt (every artifact: code, comments, outputs, cell values), lit, entropy, F(path `.env`) | N | N | S (legitimately lexical) | P+; clean only over the SCANNED set |
| R22 | Structural PII (v1 PII010, PII012, PII013) | fld (field names and type text), lit(email-shaped), callee vocabulary (client storage) | N | N | S + vocab | P+ |
| R23 | Supply chain (v1 VET001-012, VET-JS, VET-PY, VET-RS, VET-SOURCE-UNAVAILABLE, VET-TIMEOUT) | kv(manifests, lockfiles), artifacts OUTSIDE the work tree (dependency source), eff over them, F(binary blobs), net | Y | Y | S (manifests), M (dep capability scan, osv) | P+; unavailable source is Unresolved by the scanned-set rule |
| R24 | Deprecation, release, versions (v1 DEPR005, REL001/002, VERSION001; v2 REL003, DEPR, PM026) | directives(deprecated with dates), attr(deprecated), references_to(sym) diffed against a baseline, kv(versions), public-API signature diff between revisions | Y | Y | M | P+ |
| R25 | Tickets and process (v2 TICK001-003, SCOPE001, PM001-029; v1 TICK001-015, BASE001, MILE001-004, CROSSTICKET001, QUEUE001, PRE001, BUDGET001, LEDGERV1001, BUG002/003, TDD001, SCOPE001/002, AUTOFIX001, DERIVED001, SUBJECT001, CHECK001, CACHE001, CLAUDE001, EXCL001) | no IR; F (membership, globs), diff (changed paths) | -- | -- | n/a | -- |
| R26 | Registries and decisions (v1 REG001-012, DEC000-003, COMPLIANCE001/004-007, THREAT001/006, GATERULE001, GATES001, the 11 *SCHEMA001 ids; v2 DEC004) | kv (yaml/toml), directives(enforces, decision), rule-id set | Y | N | S | P+/P-; *SCHEMA and GATERULE die by serde and enum |
| R27 | Engine and repo-health self checks (v2 CFG001, GEN001, TOOL001, PERF001, PROC001; v1 TOOL001-003, BARETOOL001, WRAP001-003, DEPLOY001-003, PLATFORM001/002, PROFILE001, PORT001, LEXCHECK001, WALK001, RENDER001, NATIVE001, LANDFMT001, the ruff pseudo ids E501/F401/I001, fixture id TIERBDEMO001) | kv(config tables vs schema), generated bytes, process runs; the v1 self-lints are forbid-call/forbid-import patterns | N | N | S, run | P+; PROC001 is the INV002/CAP shape (forbid a capability in an owner set) |
| R28 | Model-to-code binding (v2 SYS001-009; v1 SYS001/002/003/102-113, THREAT004/005) | grm (owns selectors, flows via producer/consumer/contract, surface), select(selector), vis, edges between owners, digests (lock: SYS006/7), by_digest (SYS008) | Y | Y | M | SYS001 is P- (selector matches zero: fire iff HI empty); SYS003/009 are P+ over symbols with effects/public |
| R29 | Capability matrix (v2 CAP001-003; v1 SYS100/101/105/111, THREAT004/005, REL390-397 proofs) | eff(symbol) atoms with confidence, grm(`may`/`excuses`), adapter detectors, matrix n/a | Y | Y | M (typed call-site detectors; lexical fallback) | CAP001 P+ (observed not granted: LO fires); CAP002 P- (granted never observed: fire iff HI lacks); CAP003 matrix over applicability |
| R30 | Cross-language binds (v2 BIND001/002; v1 FFI001/002, `frob bind`) | attr (`#[pyfunction]`, `wasm_bindgen`), normalized Sig on both sides (param names, arity, Type lattice), stub files (`.pyi`), binds edges | Y | Y (the point) | M (type lattice) | P0 (sig equality under the lattice), P- (counterpart exists) |
| R31 | Declared-plus-proven (v1 REL200-397 about 55 ids; v2 one parametric marker+evidence rule) | grm(markers), pattern_match over symbols owned by the node for evidence tokens | Y | Y | S | the PROOF side is P- (absence of evidence fires only if HI lacks it; any opq region in scope gives Unresolved) |
| R32 | Pure design-model rules (v1 SYS2xx, SYS114-120, SYS300-303, LINT001-005, PII001-005, COMPLIANCE002/003, THREAT002/003, HOST001/002, HOST-BLAST, KRB001-004, CAP001 capacity, REL250/340/360/380-383, VMOD001, MSCLOSE001, SELFAUDIT001, SYS900, INV051) | grm only; VMOD `code_ref` and `runnable` call resolve_symref and test_items | -- | -- | n/a | -- |
| R33 | Lexical perf (v1 PERF001-018, perf hot-graph; v2 PERF001 is engine timing, row R27) | ctl (loop nesting), call + callee vocabulary (sort, index, count, spawn), typ (list vs set for membership), profile frames (file,line) to symbols | N | N | S + vocab; M for container type | P+ |
| R34 | Python-semantic (v1 EXHAUST001-004, RACE001/002, GUARD001, CLAIM001, ROUTE001, CONFIGPATH001, SUPPRESS001, CPPTHROW001, FUZZ001-003, FLAGCOV001) | raise/catch sets (M, may-raise resolver), decorators (attr), pydantic fields (fld), noqa comments (cmt), arbitrary-type registries | Y | N | M | P+ ; all DROP, re-expressible per section 8 |
| R35 | Web families (v1 WEBSEC, A11Y, SEO, WEBPERF, SQL, COMPLY, LAUNCH, LAYOUT, SQLEXPLAIN; 249+4 ids) | markup element tree with attributes (HTML/JSX/templates), route decorators (attr), emb(SQL in strings), header config (kv), render (run) | Y | Y | S (element patterns), M (framework, render) | P+/P- |
| R36 | crunk design system (COLOR, SPACE, TYPE, RADIUS, SIZE, LAYER, CONTRAST, ORG, TW, BP, TOKENS, GALLERY, WAIVE001) | CSS declarations (property, typed value literal, selector and at-rule context), custom-property def/use graph, JSX style props and className STATIC fragments, kv(crunk.toml scales and palette), F(bucket placement), generated-file drift, run(tailwind via node, playwright) | Y | Y (JSX to CSS to Tailwind config) | S (declarations), M (var resolution, Tailwind) | P+ (off-scale value); COLOR002 undefined var is P- and needs a complete HI definition set |
| R37 | Directive planes of sibling products (crunk:accept/defer/waive, grimble:binds/node/channel/effect/may/excuses) | same as R13/R14 with a namespace parameter | Y | N | S | as R13/R14 |

Reading the table, five fact clusters carry almost every rule:
(1) symbols + visibility + doc + attributes (R01-R04, R18, R24, R28, R30),
(2) comments and prose (R08, R09, R12, R13, R14), (3) import/call/reference EDGES
with confidence (R02, R04, R15, R17, R18, R24, R28, R29), (4) digests by facet
(R01, R02, R05, R13, R19, R28), (5) a pattern matcher over the concrete tree
(R20, R21, R22, R31, R33, R34, R35, R36 and every GPOL/POL). R25, R26 and R32 read
no IR at all; they only need `F` and side inputs, so the IR must not be on their
critical path.

## 3. The answer lattice and rule polarity ("unmeasured is not zero", made mechanical)

### 3.1 Answers

```
Answer<T> = Exact(T)
          | Bounds { lo: T, hi: T, why: [Reason] }   // lo subset-of truth subset-of hi
          | Unknown(Reason)                          // exists, could not be determined
          | NotApplicable(Reason)                    // the concept does not exist here
```

- A set-valued query returns `Exact(set)` or `Bounds`. `Exact` is `lo == hi`.
  `Unknown` is `lo = empty, hi = everything`. This is v1's "monotone poisoning"
  (any UNRESOLVED_CALLEE poisons its callers) stated as an interval: one
  unresolvable call site makes `hi` of that caller's callee set the universe.
- A boolean-valued query returns `Exact(bool)` or `Unknown`; tri-state is the
  degenerate interval.
- `Unknown` is per site and reported per finding site. `NotApplicable` is
  declared by the adapter once and rolled up to ONE Unresolved per (rule,
  language, scope), as code-model.md section 7 already does for the capability
  matrix (`n/a` is one Unresolved per node, never a clean cell and never an error).

### 3.2 Polarity decides which bound a rule may use

| Polarity | Rule shape | Fires when | Certified clean when | Else |
|---|---|---|---|---|
| P+ presence | forbidden import, secret literal, broken link, long function, undeclared capability | an offender is in `lo` | no offender in `hi` | Unresolved, listing `hi minus lo` as the maybe-set |
| P- absence | undocumented public, untested, dead, orphan file, selector matches nothing, capability granted but never seen | `hi` contains no good thing | `lo` contains a good thing | Unresolved |
| P0 equality | digest drift, set equality (DOCENUM), sig equality (BIND) | both sides `Exact` and differ | both `Exact` and equal | Unresolved if either side is not `Exact` |
| Pn threshold | `lines > N` (max-type), `fewer than N tests` (min-type) | max-type: measured `lo > N`; min-type: `hi < N` | max-type: `hi <= N`; min-type: `lo >= N` | Unresolved |
| Pc closure | cycle exists, A reaches B | path inside `lo` edges | no path inside `hi` edges | Unresolved with the poisoned frontier |

Consequences worth stating once:

1. Over-approximated edges (name-only, ambiguous candidates) are legal and useful
   for P- rules and for "affects" lists; they are illegal as the sole basis for a
   P+ finding. Under-approximated edges (certain only) are the reverse.
2. A rule must not receive a bare set; it receives an `Answer<Set>` and the rule
   author writes only the polarity. The framework applies the table. This removes
   the entire class of bug "adapter could not see X, rule read that as none".
3. EXC013 and WAIVE004 (stale exception) are P- over the findings of ALL other
   rules. An exception matched by a rule whose run was Unresolved is not stale;
   it is unprovable. The stale check therefore needs each rule's outcome to carry
   its Unresolved sites, not just its findings.
4. Subject accounting (v1 SUBJECT001, "enforcing gate examined zero subjects"):
   every rule outcome carries `subjects_examined`. If the adapter says the rule
   applies and `subjects_examined == 0` over a non-empty scope, the outcome is
   Unresolved("vacuous"), never clean. This is what makes the Brainfuck and
   spreadsheet cases (section 7) honest.
5. "Scanned set" for lexical rules (R21, R23): the clean claim is stated over the
   set of artifacts and regions actually scanned. Cell outputs, dependency source
   not on disk, binary parts are either in the set or listed as not scanned.

### 3.3 Rule declarations should name queries, not "inputs(graph, docs)"

rules.md section 2 declares `inputs(graph, docs)`. Replace the coarse input list
with the query set: `#[rule(needs(Q::PublicApi, Q::Doc, Q::Attributes))]`, plus a
`polarity` field. The framework intersects `needs` with the adapter's capability
declaration (section 5) and decides applicability per file before the rule body
runs. A rule author cannot forget the Unresolved path; an adapter that answers
`NotApplicable` for any needed query yields the rolled-up Unresolved with the
reason string for free. The pair-fixture doctrine then needs a third fixture: a
language that lacks the feature, expecting Unresolved (not clean).

## 4. The minimal query interface

Conventions. `Loc` is a locator, not a byte range: `Span(file, range) |
Cell(artifact, address) | NodePath | Hash` (landed `Finding.span` is a byte range
only; section 9 G13). `Artifact` is any addressable source unit: a file, a
notebook cell, a spreadsheet sheet. Tier tags: [T] total on any text language
with a grammar; [C] capability-gated (adapter may declare NotApplicable or Gap);
[I] interval or three-valued answer. Q-ids are referenced by sections 5-8.

### 4.1 Pure syntax (one parse, no cross-file state)

| Id | Query | Answer | Tag | Needed by |
|---|---|---|---|---|
| Q01 | `artifacts() -> Set<Artifact{id, path, sub, kind, lang, text_model}>` | Exact | T | all; F membership (R11, R25) |
| Q02 | `parse_status(a) -> Ok \| Partial{error_locs} \| Failed(reason) \| NoText \| Unsupported` | Exact | T | R14; every P- rule (a Partial parse makes lost symbols invisible) |
| Q03 | `text(loc) -> Option<&str>`; `size(a, Bytes\|Lines\|Tokens\|SourceLines)`; `line_col` | Exact / Option | T (None for NoText) | R16, R21, layout rules |
| Q04 | `symbols(a) -> Answer<Set<Symbol{symref, kind, name: Option, spans: [Loc], parent}>>` | Exact, or Bounds when macros/splices/preprocessor may generate or hide symbols | T (Bounds via Q17) | R01-R04, R18, R28 |
| Q05 | `symbol_at(loc)`, `enclosing(loc)`, `following(loc, max_lines)` | Option<Symbol> | T | directive binding (gob-directives bind), R13 span containment |
| Q06 | `kind(sym) -> Kind \| Other(lang_kind)` (closed core enum plus escape) | Exact | T | R03, R16, R18 |
| Q07 | `visibility(sym) -> Public \| Crate \| Private \| Local \| NotApplicable \| Unknown` | Exact per modifiers; see Q33 for the exported set | C | R03, R18, R28 |
| Q08 | `attributes(sym) -> [Attr{path, args_text, style: Outer\|Inner\|Decorator\|Pragma, loc}]` | Exact | C | R03 (`#[doc]`), R04 (`#[test]`), R30 (`#[pyfunction]`), R24, R34 |
| Q09 | `doc(sym) -> Option<Doc{text, style, loc}>` (comment-before, docstring, doc attribute, PlDoc) | Exact | C | R03, R01 (doc facet) |
| Q10 | `comments(a) -> Set<Comment{loc, kind, text, in_string: false, enclosing: Option<Sym>, following: Option<Sym>}>`; `comments_near(loc, lines)` | Exact | C (CommentChannel) | R12, R13, R14, directive scan |
| Q11 | `prose(a) -> {headings(tree, slug), links(dest, loc), fences(info, loc), code_spans, tables, html_comments}` | Exact | T for markdown | R08, R09, R10, R01 |
| Q12 | `import_decls(a) -> [ImportDecl{path_segments, alias, glob, scope: Module\|Function\|TypeOnly\|TestOnly, time: Static\|Deferred\|Dynamic, loc}]` | Exact | C | R07, R15, R17 |
| Q13 | `name_uses(scope) -> [NameUse{path, ns: Value\|Type\|Module\|Macro, use_kind: Call\|Reference\|Unclassified, loc, in_opaque}]`; `call_sites(scope)` is the `use_kind = Call` subset | Exact (classification may be Unclassified) | C | R02, R04, R18, R20, R29 |
| Q14 | `literals(scope, kind) -> [Literal{kind: Str\|Num\|Color\|Length\|Regex\|Bool, value, loc, enclosing}]` | Exact | C (None in Brainfuck) | R21, R22, R36, R10 |
| Q15 | `members(sym)`, `params(sym) -> [Param{name: Option, type_text: Option, default, mode}]` (or `Implicit(valence)`), `returns(sym)`, `fields(sym)` | Exact | C | R16 (LCOM), R22, R30 |
| Q16 | `control(sym) -> {loops(kind: For\|While\|Forever\|Elab), branch_arms, max_nesting, cyclomatic, returns, tries, lines}`; `descendants(scope, IrKind)` | Exact | C | R16, R33, R20 |
| Q17 | `opaque_regions(scope) -> [Opaque{loc, kind: MacroCall\|Splice\|Eval\|Preprocessor\|DynamicDispatch, mentions: [NameUse], may_define: Yes\|No\|Unknown, may_read_scope: Yes\|No\|Unknown}]` | Exact | T (empty is a claim the adapter must make) | R18, R20 (OPAQUE001), R31; poisons Q04 and Q22 |
| Q18 | `embedded(a) -> [(Loc, Lang, Artifact)]` (md fences, SQL in strings, JSX-in-TS, quasi-quotes, notebook magics) | Exact | C | R09 (DOC004), R35, R29 |
| Q19 | `keys(a) -> KeyTree` for TOML/JSON/YAML, with locs | Exact | T for structured files | R07, R23, R26, R27, R36 |

### 4.2 Binding (names to declarations; semantic)

| Id | Query | Answer | Tag | Needed by |
|---|---|---|---|---|
| Q20 | `binds_to(use: NameUse) -> One(Sym) \| Candidates([Sym], order: Unknown\|Backward\|Forward) \| External(PkgRef) \| Unknown(reason)` | tri-valued | I | R02, R04, R18, R29 |
| Q21 | `resolve_import(decl) -> Internal(Artifact\|Symbol) \| External(PkgRef) \| Candidates \| Unknown` | tri-valued | I | R15, R17, R07 |
| Q22 | `resolve_symref(text) -> One \| Ambiguous([Sym]) \| NotFound` (landed `SymbolGraph::resolve`) | tri-valued | T | R01, R04, R09, R28, directives |
| Q23 | `package_of(a)`, `module_path(a) -> [segment]` (language-neutral segments; `.`, `::`, `/` are adapter spellings) | Option | C | R06, R07, R17 |
| Q24 | `const_value(expr) -> Known(Value) \| Unknown(reason)` | Exact or Unknown | C | R10, R36, R22 |
| Q25 | `type_of(expr)`, `impls_of(trait)`, `dispatch_targets(call) -> Bounds<Set<Sym>>` | Bounds | I (tier 3, optional) | R33 (container type), R02 (class dispatch), R30 |
| Q26 | `external_ref(use_or_import) -> Option<{package, version, item_path}>` | Option | C | R29, R23 (effects from library calls) |

### 4.3 Graph (derived; every edge carries confidence)

Edge kinds are an adapter-extensible closed set: `Contains, Imports, Calls,
References, Instantiates, Extends, Binds`. `Calls subset-of References` always.
`confidence = Certain | ImportVerified | NameOnly | Lexical`. `Certain` and
`ImportVerified` edges are in `lo`; every edge, plus one wildcard edge per unknown
call site, is in `hi`.

| Id | Query | Answer | Tag | Needed by |
|---|---|---|---|---|
| Q27 | `contains(a, b)`, `parent(s)`, `ancestors(s)` | Exact | T | R01, R13, R18 |
| Q28 | `edges(sym, kinds) -> Bounds<[Edge{kind, target: Resolved\|Candidates\|External\|Unknown, confidence, site}]>` | Bounds | I | R02, R04, R15, R17, R18, R29 |
| Q29 | `referrers(target: Sym\|Artifact, kinds) -> Bounds<Set<Ref>>` (inbound; includes md links, directives, config paths, imports) | Bounds | I | R11, R18, R24, R05 |
| Q30 | `closure(from, kinds, dir, depth) -> Bounds<Set<Sym>>`; `reaches(a, b, kinds) -> Yes(path) \| No \| Unknown(frontier)` | Bounds/tri | I | R02, R04, R07 (INV011), R05 |
| Q31 | `scc(kinds, scope) -> Bounds<[Cycle]>` | Bounds | I | R15 |
| Q32 | `select(selector{lang?, path_glob, qualname_glob?, kind?}) -> Bounds<Set<Sym>>`; `owner(sym) -> One(node) \| Ambiguous \| Foreign` (most specific wins) | Bounds | I | R17, R28, R29, R31 |
| Q33 | `public_api(scope) -> Bounds<Set<Sym>>` (modifier chain plus re-exports plus export lists; `hi` adds maybe-re-exported items) | Bounds | I | R03, R04, R24, R28, PM026 |
| Q34 | `effects(sym) -> Bounds<Set<EffectSite{atom, loc, via: Typed\|Lexical, confidence}>>` | Bounds | I | R29, R31, R23 |
| Q35 | `test_items(scope) -> Answer<Set<TestItem{sym_or_loc, name, shape: Attr\|Name\|Path\|DirectivePair\|Custom, params, confidence}>>` | Exact/Bounds | C | R04, R06, R05 |
| Q36 | `binds(sym) -> Bounds<Set<BindEdge{a, b, via, sig_a, sig_b}>>` (grimble supplies) | Bounds | I | R30, R02, R04 |
| Q37 | `entrypoints(scope) -> Set<Sym>` (main, bins, exported, top modules, `__main__` guards) | Exact | C | R18, R03 (v1 COV010) |

### 4.4 Digests

| Id | Query | Answer | Tag | Needed by |
|---|---|---|---|---|
| Q38 | `facet_digest(sym, Sig\|Body\|Doc\|Attr) -> Digest \| Absent \| Unknown`; defined over the adapter's CANONICAL facet stream, not over whitespace-collapsed text | Exact | T | R01, R02, R05, R13, R28 |
| Q39 | `norm_sig(sym) -> Sig{name, params[(name?, Type, default?)], ret, vis, async, generics}` over the Type lattice; `arity: Known(n) \| Valence(Unknown)` | Exact or Unknown | C | R30 |
| Q40 | `shape_digest(sym, rung: R1..R5) -> Digest`; `defuse(sym) -> Graph` for R5 | Exact | C | R19 |
| Q41 | `section_digest(heading)`, `file_digest(a)`, `region_digest(loc)` | Exact | T | R01, R14 |
| Q42 | `by_digest(facet, d) -> [Sym]` (rename candidates) | Exact | T | R01, R28 (SYS008) |
| Q43 | `at_revision(rev) -> IrSnapshot`; `diff_symbols(old, new) -> [Change{sym, New\|Gone\|Sig\|Body\|Doc\|Attr}]` | Exact | T | R05, R02, R13, R24 |

### 4.5 Language-specific escape (ast-grep style, concrete tree)

| Id | Query | Answer | Tag | Needed by |
|---|---|---|---|---|
| Q44 | `pattern(scope, lang, pat{pattern, kind, inside, has, follows, precedes, regex, not, constraints}) -> [Match{node, captures, loc}]` | Exact w.r.t. the tree; caveat Q02 and Q17 | T (per grammar) | R20-R22, R31-R36, GPOL |
| Q45 | `ts_query(scope, scm) -> [Capture]` (raw tree-sitter) | Exact | T | language rules |
| Q46 | `ir_pattern(scope, pat) -> [Match]` over IrKind plus `callee_vocab` (universal rules) | Exact over mapped kinds | C (adapter ir_map) | R33 and every `language = "*"` rule |
| Q47 | `callee_vocab(lang, class) -> [CalleePattern{path, arg_shape, atom?}]` (data: sort, print, exec, assert, open, env-read) | Exact; empty means NotApplicable, never "no hits" | C | R20, R29, R33, R06 (assertions) |

Autofix support (rules.md fix tiers) is not a query but needs one operation the IR
must expose: `splice(loc, text) -> Edit` plus `reparse_ok(edit)`, because crunk's
INV-FIX-01 and v1 tier-A fixes need "bytes outside the span untouched" and
re-check idempotence. NoText artifacts return NotApplicable and the fix tier
degrades to Manual.

### 4.6 IrKind additions forced by the worked examples

code-model.md section 5 lists `Module | Function | Class | Block | Loop | Branch |
Call | Assign | Return | Try | Lambda | Literal | Name | Attribute | Import |
Comment | Other`. The rules and languages studied need these additions:

| Addition | Why (first language that breaks the list) |
|---|---|
| `Apply{f, args}` unclassified application | Haskell, APL, Forth, Lisp: juxtaposition is not a call until `f` binds to a function; `call_sites` is Q13's `use_kind = Call` subset, derived after Q20 |
| `Clause` and multi-part symbols (`spans: [Loc]`) | Prolog clauses, Haskell signature plus equations, C declaration plus definition |
| `Instantiate{target, params}` edge and node | Verilog/VHDL module instances; static structure that is neither import nor call |
| `Loop{kind: Elab}` | Verilog `generate for`; not runtime work, PERF rules must not fire |
| `Branch{kind: Match, arms}` | Haskell/Prolog/Rust: cyclomatic wants arms; v1 excluded `match` as flat dispatch |
| `Assign{mode: Blocking\|NonBlocking\|Bind}` | Verilog `=` vs `<=`; also Prolog unification, Haskell `<-` |
| `Opaque{kind}` | macro call, splice, eval, preprocessor use, `call/N` with a variable goal |
| `Decl` (non-executable declarations: signatures, fields, params, ports) | type signatures, record fields, ports; carry `type_text` |
| `Cell`, `Sheet` as `Module`-like containers | notebooks, spreadsheets (Artifact `sub` addresses) |
| `Decl{selector}`, `AtRule` | CSS (crunk): property/value declarations in selector and media context |
| `Element{tag, attrs}` | markup for the web families and JSX |
| `NameUse.use_kind = Unclassified` | APL, Haskell composition operands |

## 5. Capability requirements: what a per-language adapter must declare

### 5.1 The declaration

code-model.md section 3 already has `Implemented | NotApplicable(reason) |
Gap(ticket)` cells. Two changes: (a) the cells are per QUERY (Q-ids above), not
per facet, so the framework can compute rule applicability from a rule's `needs`;
(b) add a fourth value `Approximate(bound_kind, note)` meaning "I answer, but with
`Bounds`, and this is how loose" (for example calls: `lo = Certain, hi = NameOnly
plus wildcard for dynamic dispatch`). The adapter also declares the LANGUAGE
FEATURES below; a query's required features determine its default cell, and the
conformance fixture proves each cell.

```rust
struct Features {
    artifacts:  Files | Cells | Objects,          // what Q01 enumerates
    locator:    ByteRange | CellAddress | NodePath | Hash,
    names:      Always | Sometimes | None,        // symbols may be anonymous
    nesting:    bool,                             // symbols contain symbols
    comments:   Safe | UnsafeLexical | AnnotationOnly | None,
    docs:       Convention(CommentBefore | Docstring | Attr | PlDoc) | None,
    visibility: Modifiers | ExportList | NamingConvention | AllPublic | None,
    attributes: bool,
    imports:    Static | StaticAndDeferred | None,
    calls:      Static | NameBased | DynamicDispatch | Unclassified(juxtaposition) | None,
    types:      None | Declared | Inferred,
    tests:      Attr | Name | Path | DirectivePair | Custom | None,
    effects:    VocabPresent | None,
    consts:     bool,
    embedded:   [Lang],
    opaque:     [MacroCall | Splice | Eval | Preprocessor | DynamicDispatch],
    stable_ids: bool,                             // cell ids, hash ids: acks survive reorder
}
```

### 5.2 Query by feature (R = required, the answer is NotApplicable/Unknown
without it; o = optional, absence widens the Bounds; . = not needed)

Feature columns: TXT text with stable spans, ART file artifacts, NAM names, CMT
comment channel, DOC doc convention, VIS visibility concept, ATT attributes,
IMP static import mechanism, CAL statically resolvable call/reference sites, TYP
static types, TST test convention, EFF library-effect vocabulary, CST constant
evaluation, EMB embedded languages.

| Q | TXT | ART | NAM | CMT | DOC | VIS | ATT | IMP | CAL | TYP | TST | EFF | CST | EMB | If the feature is absent |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q01 artifacts | . | R | . | . | . | . | . | . | . | . | . | . | . | . | adapter enumerates cells/sheets; else file only |
| Q02 parse_status | o | . | . | . | . | . | . | . | . | . | . | . | . | . | NoText or Unsupported (never Ok by default) |
| Q03 text/size | R | . | . | . | . | . | . | . | . | . | . | . | . | . | None; layout rules NotApplicable; size unit is adapter-defined |
| Q04 symbols | . | . | R | . | . | . | o | . | . | . | . | . | . | . | empty set plus subjects=0 (vacuous), or positional names flagged Unstable |
| Q05 symbol_at | o | . | R | . | . | . | . | . | . | . | . | . | . | . | bind directive to enclosing named symbol, else the artifact |
| Q06 kind | . | . | o | . | . | . | . | . | . | . | . | . | . | . | Other(lang_kind) |
| Q07 visibility | . | . | . | . | . | R | . | . | . | . | . | . | . | . | NotApplicable (public-set rules roll up to one Unresolved) or declared AllPublic |
| Q08 attributes | . | . | . | . | . | . | R | . | . | . | . | . | . | . | empty list is a claim; pragma-bearing languages must declare Gap, not empty |
| Q09 doc | . | . | . | . | R | . | o | . | . | . | . | . | . | . | NotApplicable; DOC001 Unresolved |
| Q10 comments | o | . | . | R | . | . | . | . | . | . | . | . | . | . | NotApplicable; directives need a sidecar; TODO001 Unresolved |
| Q11 prose | R | . | . | . | . | . | . | . | . | . | . | . | . | . | markdown only |
| Q12 import_decls | . | . | . | . | . | . | . | R | . | . | . | . | . | . | NotApplicable; CYCLE and INV-import Unresolved |
| Q13 name_uses | . | . | o | . | . | . | . | . | R | . | . | . | . | . | Unclassified uses only, or None |
| Q14 literals | . | . | . | . | . | . | . | . | . | . | . | . | o | . | empty is Exact when the language has no literals |
| Q15 params/fields | . | . | R | . | . | . | . | . | . | o | . | . | . | . | Implicit(valence Unknown); BIND Unresolved |
| Q16 control | . | . | . | . | . | . | . | . | . | . | . | . | . | . | total on any grammar |
| Q17 opaque_regions | . | . | . | . | . | . | . | . | . | . | . | . | . | . | total, but the adapter must declare which opaque kinds it can detect |
| Q18 embedded | . | . | . | . | . | . | . | . | . | . | . | . | . | R | none: embedded code is invisible to every rule (declare Gap) |
| Q19 keys | . | . | . | . | . | . | . | . | . | . | . | . | . | . | structured files only |
| Q20 binds_to | . | . | R | . | . | . | . | o | R | o | . | . | . | . | Unknown per use; hi = candidates by name |
| Q21 resolve_import | . | . | . | . | . | . | . | R | . | . | . | . | . | . | External(unresolved) |
| Q22 resolve_symref | . | . | R | . | . | . | . | . | . | . | . | . | . | . | file-level only |
| Q23 package/module | . | R | . | . | . | . | . | o | . | . | . | . | . | . | None; package rules (TEST003, INV from-glob) Unresolved |
| Q24 const_value | . | . | . | . | . | . | . | o | . | . | . | . | R | . | Unknown; DOCENUM Unresolved |
| Q25 type_of | . | . | . | . | . | . | . | . | . | R | . | . | . | . | Bounds with hi = all candidates; typed detectors fall back to Lexical |
| Q26 external_ref | . | . | . | . | . | . | . | R | o | . | . | . | . | . | None; effects fall back to lexical needles |
| Q27 contains | . | . | . | . | . | . | . | . | . | . | . | . | . | . | total (flat file = one level) |
| Q28 edges | . | . | . | . | . | . | . | o | R | o | . | . | . | . | Bounds with lo empty, hi wildcard |
| Q29 referrers | . | . | . | . | . | . | . | o | R | . | . | . | . | . | md links and directives still counted (Exact for those kinds) |
| Q30 closure/reaches | . | . | . | . | . | . | . | . | R | . | . | . | . | . | Unknown(frontier = poisoned callers) |
| Q31 scc | . | . | . | . | . | . | . | R | o | . | . | . | . | . | NotApplicable for the import kind |
| Q32 select/owner | . | o | R | . | . | . | . | . | . | . | . | . | . | . | file-granular selectors only (stated) |
| Q33 public_api | . | . | . | . | . | R | . | o | . | . | . | . | . | . | per Q07; hi adds re-export candidates |
| Q34 effects | . | . | . | . | . | . | . | . | R | o | . | R | . | . | NotApplicable for the atom; n/a per node in the matrix |
| Q35 test_items | . | . | . | . | . | . | o | . | . | . | R | . | . | . | NotApplicable; COV/TEST rules Unresolved, never "all untested" |
| Q36 binds | . | . | R | . | . | . | o | . | . | . | . | . | . | . | binds(...) is grimble data; absent adapter side = missing counterpart Unresolved |
| Q37 entrypoints | . | . | . | . | . | o | . | o | . | . | . | . | . | . | exported symbols only (stated over-approximation) |
| Q38 facet_digest | o | . | . | . | o | . | o | . | . | . | . | . | . | . | Absent per facet; adapter-defined canonical stream |
| Q39 norm_sig | . | . | R | . | . | . | . | . | . | o | . | . | . | . | arity Unknown(valence) |
| Q40 shape_digest | . | . | o | . | . | . | . | . | o | . | . | . | . | . | R1/R3 only; R2/R5 NotApplicable without binder or def-use info |
| Q41 section/file digest | . | . | . | . | . | . | . | . | . | . | . | . | . | . | total |
| Q42 by_digest | . | . | . | . | . | . | . | . | . | . | . | . | . | . | total |
| Q43 at_revision/diff | . | . | . | . | . | . | . | . | . | . | . | . | . | . | total (pure function of artifact bytes) |
| Q44 pattern | R | . | . | . | . | . | . | . | . | . | . | . | . | . | tree-literal patterns for NoText languages (adapter-defined) |
| Q45 ts_query | R | . | . | . | . | . | . | . | . | . | . | . | . | . | NotApplicable |
| Q46 ir_pattern | . | . | . | . | . | . | . | . | . | . | . | . | . | . | needs adapter `ir_map`; unmapped kinds become Other |
| Q47 callee_vocab | . | . | . | . | . | . | . | . | R | . | . | R | . | . | empty vocabulary is NotApplicable, never "no offenders" |

Headline (counted from the table above by script): 8 of 47 queries need no
language feature at all (Q16, Q17, Q19, Q27, Q41, Q42, Q43, Q46); 14 have no
REQUIRED feature (their precision varies, their existence does not); the other 33
each name at least one required feature whose absence turns the answer into
NotApplicable, Unknown or a widened Bounds. Required-feature counts by column:
NAM 8 queries, CAL 7, TXT 4, IMP 4, ART 2, VIS 2, EFF 2, and 1 each for CMT, DOC,
ATT, TYP, TST, CST, EMB. Names and statically resolvable calls/references are the
two features most worth asking every new language about first; they gate every
graph query and every P- rule. A rule whose `needs` set includes a gated query
inherits its degradation automatically. The [T] tag in section 4 means "total
given text, files and names", the baseline of the milestone-1 languages (Rust,
markdown, TOML); the table above is what happens when those assumptions are
dropped.

## 6. Rules that are impossible or wrong where a feature is missing

Cell codes. ok: works as written. U: skip with Unresolved (rolled up once per
rule and language). A: approximate with a STATED over-approximation (the finding
text says which bound was used). C: requires the named adapter capability or a
generalization of the rule's own input type; without it, U.

| Rule family (row) | No files (NF) | No names (NN) | No static calls (NC) | No comments (CM) | No text (NT) | No convention (vis/tests/docs) |
|---|---|---|---|---|---|---|
| R01 DRIFT | C: symref grammar for `path#cell=ID::Q`, `path#Sheet!B7` | A: bind to enclosing named symbol; positional ids are Unstable and acks on them are refused | ok | ok (digests need no comments) | C: facet digest over canonical stream | ok |
| R02 AFFECT | C | A | A: use hi (references plus wildcard); say so | ok | C | ok |
| R03 doc coverage | ok | U (nothing to document) | ok | U if docs live in comments and there are none | U | U for visibility (no `public`), unless AllPublic declared |
| R04 test reach | ok | U | A: forward closure over `References` hi; fire only if hi lacks | ok | ok | U: no test convention means Unresolved, NEVER "all untested" |
| R05 diff accountability | C | A | A | ok | C | ok |
| R06 tiers/evidence | ok | ok | ok | ok | ok | U |
| R07 invariants | C (glob `from` over artifact paths) | ok | ok | ok | ok | ok |
| R08/R09 md links, pointers | ok (md is its own artifact kind) | ok | ok | ok | ok | ok |
| R10 DOCENUM | ok | ok | ok | ok | C: const_value | ok |
| R11 orphans | C: orphan artifact (cell, sheet) not orphan file | ok | A: referrers hi | ok | ok | ok |
| R12 TODO/NARR | ok | ok | ok | U unless a comment-like channel (notes, labels) is declared | U | ok |
| R13 EXC | C: sidecar binding | A | ok | C: sidecar binding (no inline directive) | C | ok |
| R14 PARSE/DSL | ok | ok | ok | ok | NoText status | ok |
| R15 CYCLE | ok | ok | U (call cycles) / ok (import cycles) | ok | ok | ok |
| R16 size, nesting | A: size unit is SourceLines or Tokens, never file bytes | ok (artifact is the unit) | ok | ok | U for line-based | ok |
| R17 layering | C | A | A | ok | ok | ok |
| R18 DEAD | ok | U | A: hi; wildcard poison makes it U | ok | ok | U without a visibility model |
| R19 DUP | ok | ok | ok | ok | C: canonical stream | ok |
| R20 pattern/policy | ok | ok | ok | ok | C: tree-literal patterns | ok |
| R21 SEC lexical | C: scan outputs and cell values or state not scanned | ok | ok | ok | C: rendered text or U | ok |
| R22 PII structural | ok | ok | ok | ok | ok | ok |
| R28/R29 owners, caps | C: selectors over artifact addresses | A | A: Lexical-confidence detectors, never Certain | ok | C | ok |
| R30 BIND | ok | U (names and arity) | ok | ok | ok | ok |
| R33 lexical perf | ok | ok | ok | ok | ok | U if callee vocabulary empty |

Specific judgments the table compresses:

1. NO FILES (notebooks, spreadsheets, image-based Smalltalk). The unit of
   address, ownership, size and orphaning is not the file. The IR's root type
   must be `Artifact` with a `sub` address; rules phrased in "files" (LARGE001,
   REF001, INV002's `from`, PROC001's crate allowlist, SYS owns globs) are
   re-expressed over artifact kinds. LARGE001 is WRONG on a notebook if it
   measures file bytes (base64 outputs dominate); it must call
   `size(a, SourceLines)`.
2. NO NAMES (point-free, concatenative, tacit APL, Brainfuck). A symref needs a
   name segment. Anonymous items cannot hold acks, so DRIFT, `frob:accept` and
   SYS owns degrade to the nearest named container; a positional id is allowed
   only as `Unstable` and refused as a lock key. `BIND001` compares param names
   and arity, which tacit definitions do not have, so it is Unresolved, not
   "matches".
3. NO STATIC CALLS (dynamic dispatch, Prolog meta-calls, Haskell type classes,
   JS `eval`, Python `getattr`). `calls` is `Bounds` with a wildcard hi. P-
   rules (DEAD, COV, WIRE001) use `References` (mentions) as hi; if the scope
   holds an Opaque with `may_read_scope != No` they are Unresolved. OPAQUE001
   (v1 KEEP) is not impossible here, it is the rule that REPORTS this condition
   and must stay on every language that has an opaque kind.
4. NO COMMENTS (visual languages, Brainfuck, LabVIEW, Simulink). The directive
   plane (`frob:`, `grimble:`, `crunk:`) has no inline channel. Required
   capability: a declared ANNOTATION channel (cell notes, block labels,
   metadata fields) or a sidecar file `<artifact>.frob` that binds by symref.
   Without either, R13 exceptions cannot be written for that artifact and the
   finding stays unsuppressible; that is reported, not hidden. Brainfuck is the
   dangerous case: its comment channel is UNSAFE (any `,` or `.` in prose is a
   command), so a directive written inline changes the program. The adapter
   declares `UnsafeLexical` and DSL parsing refuses inline directives there.
5. NO TEXT (projectional editors, Unison, MPS). Spans do not exist. Findings
   need `Loc` generalized; digests must be over a canonical serialization (the
   facet stream) rather than whitespace-collapsed source; layout rules (FMT,
   line caps, trailing whitespace, `directive over line length`) are
   NotApplicable; ast-grep text patterns become tree-literal patterns or are
   NotApplicable. Content-addressed languages (Unison) invert identity: the hash
   is the id and the name is mutable metadata, so `by_digest` is the primary
   index and rename detection (SYS008, DRIFT002 candidates) is exact.
6. NO CONVENTION (no visibility, no tests, no docs). The most dangerous
   silent pass: "public symbol with no test" over a language with no test
   convention reads as "all public symbols untested" or, worse, "none public".
   Both are wrong. Q07/Q35/Q09 return NotApplicable and R03/R04/R06 roll up to
   one Unresolved per language.

## 7. Worked examples

Each example states the adapter's feature declaration, what the IR must produce
(symrefs, edges with confidence, digests, opaque regions) and what every relevant
rule does: FIRES, CLEAN, UNRESOLVED or NOT-APPLICABLE (rolled up once). Glyphs
and non-ASCII are spelled in words so this file stays ASCII.

### 7.1 Haskell (type-class dispatch, where-helpers, point-free, Template Haskell)

```haskell
module Stats (mean, total, Item(..)) where
-- | Average of a list.
mean :: [Double] -> Double
mean xs = s / fromIntegral n
  where (s, n) = go (0, 0) xs
        go acc [] = acc
        go (a, k) (y:ys) = go (a + y, k + 1) ys
total :: [Item] -> Int
total = sum . map price          -- point-free
data Item = Item { price :: Int, label :: String }
instance Show Item where show = label
$(deriveJSON defaultOptions ''Item)   -- splice
helper = 42
```

Features: names Sometimes (patterns anonymous), nesting yes, comments Safe, docs
CommentBefore (`-- |`), visibility ExportList, attributes yes (pragmas), imports
Static, calls Unclassified (juxtaposition), types Inferred (Gap: no inference),
tests Custom (hspec `it "..."`, `prop_` names), opaque Splice and Preprocessor
(CPP), embedded quasi-quote languages.

IR:
- Symbols: `src/Stats.hs::Stats.mean` (Function, Public by export list, spans
  `[signature line, equation]`, a multi-part symbol); `Stats.mean.go` (Function,
  `Local`, two clauses as one symbol); `Stats.total`; `Stats.Item` (type, fields
  `Stats.Item.price` and `.label`); `Stats.Item[Show]` (instance; instances are
  always exported and exempt from DOC001, as landed `implements.is_some()` already
  does); `Stats.Item[Show].show`; `Stats.helper` (Private, not in the export list).
  The pattern binding `(s, n)` yields two Local symbols sharing one span.
- Opaque: the splice is `Opaque{Splice, may_define: Yes, may_read_scope: Unknown,
  mentions: [deriveJSON, defaultOptions, 'Item]}`. So `symbols(a)` is `Bounds`
  (lo = the list above, hi = lo plus unknown generated instances).
- Edges: `mean` References `go` (Certain, lexical scope), `fromIntegral`
  (External base). `total` has a Call to `map` (head of an `Apply`, External) and
  References `sum` and `price` (operands of composition; they are applied later
  by `.`, not at this site): `calls(total)` is Bounds{lo = {map}, hi = {map, sum,
  price}}, confidence NameOnly for the hi part. A call `show x` elsewhere is an
  edge to `Candidates{class method Show.show -> instances}`: lo empty, hi = every
  instance in the repo plus External (open world). Without `type_of` (Q25) that
  hi cannot narrow.
- Digests: `mean` sig facet = the declared type signature text (a separate
  declaration from the equations); body = equations plus where block, comments
  excluded; doc = the haddock text. `total` is identical in shape. If a function
  has NO signature (legal Haskell), sig facet is `Absent`, not the digest of the
  empty string.

Rules:
- DOC001 (P+ over public_api): `total` and `Item` fire (lo members, no doc). The
  splice makes hi larger than lo, so ONE Unresolved for the module: "splice may
  define exported names".
- COV001 (P-): test items are not symbols (`it "mean of empty"` is a call site in
  `spec`); `TestItem{loc, name}` must be allowed to be a locator inside a symbol.
  `total` is reached because `spec` has an `Apply` whose head is `total` (a Call).
- DEAD001 (P-) on `helper`: no referrers in lo; the splice has may_read_scope
  Unknown. With policy `OpaqueClosedOverMentions` (stated over-approximation:
  generated code uses only names the splice mentions or reifies) it FIRES; with
  strict policy it is UNRESOLVED. The policy is a config knob, default strict.
- AFFECT001 on `Item[Show].show`: dependents are hi = every `show` call site;
  the rule must cap and say "dispatch over-approximated", else it floods.
- INV002 forbidden import `Data.Map`: import_decls are Exact; FIRES without any
  resolution (text match on an external path).
- CYCLE001 runs on Imports (hs-boot files are explicit edges). PERF rules:
  callee vocabulary empty, NOT-APPLICABLE. OPAQUE001 fires on the splice.
- CAP: `readFile` is External via `external_ref` and gives `fs.read` Typed; effects
  hidden behind `MonadIO` are only Lexical. Quasi-quote `[sql| ... |]` appears in
  `embedded()` as a SQL artifact (effect atom `sql`, Lexical).

### 7.2 Prolog (predicates, clauses, unification, no return)

```prolog
:- module(family, [ancestor/2]).
:- dynamic seen/1.
%!  ancestor(?A, ?D) is nondet.
ancestor(A, D) :- parent(A, D).
ancestor(A, D) :- parent(A, X), ancestor(X, D).
parent(tom, bob).  parent(bob, ann).
visit(X) :- \+ seen(X), assertz(seen(X)), call(X).
:- begin_tests(family).
test(root) :- ancestor(tom, ann).
:- end_tests(family).
```

Features: names Always (name/arity), nesting no, comments Safe (percent and block),
docs PlDoc, visibility ExportList, attributes yes (declarations such as `dynamic`
act as Pragma attributes), imports Static (`use_module`), calls Static for goals
plus DynamicDispatch (`call/N`, `assert*`, term expansion), types None, tests
DirectivePair (begin_tests..end_tests), effects VocabPresent, opaque Eval.

IR:
- `kb/family.pl::family.ancestor/2` (Predicate, Public via export list, TWO
  clause spans in one symbol; landed `[dupN]` disambiguation would be WRONG here,
  all clauses of a predicate are one symbol). `params()` is `Implicit(arity 2)`
  with modes from PlDoc (`?`, `?` = InOut); `returns()` is NotApplicable.
  `family.parent/2` Private (facts). `family.seen/1` carries attribute
  `dynamic`; `family.visit/1`.
- Edges: `ancestor/2` Calls `parent/2` (Certain: same module, unqualified, no
  import override) and Calls itself. `visit/1` Calls `seen/1` (site flag
  `negated`), References `seen/1` through `assertz(seen(X))` (the argument is a
  term that becomes a clause, a reference not a call), and has
  `Opaque{DynamicDispatch, may_read_scope: Yes}` at `call(X)`. `test(root)` Calls
  `ancestor/2`. Builtins (`assertz`, `call`) are External with the callee
  vocabulary supplying arg shapes (meta-argument positions for `findall/3`,
  `forall/2`, user `:- meta_predicate`).
- Digests: sig = `ancestor/2` plus mode declarations; body = the ORDERED clauses
  (order is semantic in Prolog, so reordering changes the digest, correctly);
  doc = the PlDoc block. Variables are clause-scoped binders, so R2 alpha-renamed
  shape digests are trivial here. `facet_digest(seen/1, Body)` is `Absent`
  (dynamic predicate: clauses appear at runtime).

Rules:
- DOC001 (P+): public set is Exact (export list) = {ancestor/2}, documented,
  CLEAN. COV001 (P-): test items Exact via DirectivePair; reached Certain, CLEAN.
- DEAD001 (P-): `parent/2` has a Certain referrer, CLEAN. `visit/1` has no
  referrer and `call/N` exists in the module with may_read_scope Yes, so hi is
  everything: UNRESOLVED("dynamic dispatch in module").
- CYCLE001 reads Imports only; self-recursion is not a finding. Recursion is the
  iteration primitive: `control()` reports loops = 0; branches come from `;`,
  `->` and `\+`. PERF005/006 (v1, DROP) would be wrong here; the reason they were
  dropped (heuristic) applies doubly.
- Rules about return values (EXHAUST, unhandled result): `returns()` is
  NotApplicable, so NOT-APPLICABLE, never clean. BIND001: NOT-APPLICABLE unless
  `use_foreign_library`.
- OPAQUE001 fires at `call(X)`. CAP: `assertz` mutates the clause database; no
  existing atom matches (fs, net, exec, env), so the adapter contributes an atom
  or the node's cell is `n/a` (one Unresolved, never silent).

### 7.3 APL (tacit trains, no named parameters)

Spelled with glyph names: `avg` is defined as the train "plus-reduce, divide,
tally"; `sumsq` is a dfn `{ plus-reduce of omega squared }`; `dist` is a dfn
using alpha and omega and calling `sumsq`.

Features: names Sometimes (definitions named, trains anonymous), nesting limited
(namespaces, classes), comments Safe (lamp glyph), docs CommentBefore,
visibility AllPublic (workspace functions), calls Unclassified, types None,
tests None, effects none declared, loops Explicit only.

IR:
- Symbols: `avg.dyalog::avg` (Function; `params()` = `Implicit(valence Unknown)`
  because a fork is monadic or dyadic by use); `::sumsq` (dfn; scanning the body
  for alpha shows it is never used, so arity Known(1)); `::dist` (arity Known(2)).
  No symbol exists for the unnamed train parts.
- A name inside a train, such as `sumsq` in `dist`, is `NameUse{Unclassified}`.
  Whether it is called or merely a value is decided by the NAME CLASS of its
  binding: `binds_to` returns `One(sumsq)` with class Function, and only then is
  the Call edge derived. `calls()` therefore depends on Q20; it is not a pure
  syntax query in APL (or Haskell, Forth, Lisp). Glyph primitives are External
  builtins whose class is known statically, so their applications are Certain
  Calls.
- Digests: `avg` sig facet = `Absent` (no signature; a valence change from
  monadic to dyadic is a BODY change). Body = the glyph token stream (a space
  between numerals is significant, so token stream, not collapsed text).

Rules:
- DOC001 works (AllPublic, so it demands a comment on every definition; stated).
- AFFECT001 is UNRESOLVED for `avg` ("no signature facet"); DRIFT001 and EXC005
  still track body changes.
- BIND001 UNRESOLVED (arity Unknown). COV001 UNRESOLVED once (tests None).
- ARCH001: array code has no loops or branches, so "long AND complex" never
  fires on a 200-glyph one-liner and the result is a lie. The adapter must define
  `control.max_nesting` as parenthesis depth and `size` as tokens, and the finding
  says "approximate: nesting is paren depth". PERF rules: callee vocabulary
  empty, NOT-APPLICABLE.

### 7.4 Jupyter notebook (cells, out-of-order state)

```
analysis.ipynb (nbformat 4.5, python kernel)
  a1 markdown        "# Load data"
  b2 code (exec 4)   import pandas as pd ; def load(p): return pd.read_csv(p)
  c3 code (exec 2)   df = load("data.csv")
  d4 code (exec 3)   print(df.describe())       # output text contains an API key
  e5 code            !pip install foo
```

Features: artifacts Cells (file `analysis.ipynb` plus cells), locator CellAddress,
names Always inside code cells, comments Safe (python), docs Docstring,
visibility None, imports Static (python), calls NameBased with SHARED NAMESPACE
across cells, types None, tests None, stable_ids true only for nbformat >= 4.5,
embedded python and shell magics.

IR:
- Artifacts: the file and `analysis.ipynb#cell=b2` etc. Symbols:
  `analysis.ipynb#cell=b2::load`; headings of markdown cell a1 as
  `analysis.ipynb#load-data`. Symref grammar must grow `path#cell=ID` and
  `path#cell=ID::Qual.Name` (today `#` and `::` are exclusive).
- `binds_to(load in c3)` = `One(b2::load)` with `flow: Sequential{def_exec: 4,
  use_exec: 2}`: the recorded state in c3 was produced by an OLDER version of
  `load`. The binding model is `Sequential(ExecutionCount)`, not lexical.
- Digests: cell facets are over `source` only; outputs, execution_count and
  metadata are excluded (else every re-run drifts every ack). The whole-file
  digest churns on each run and must never be an ack key.
- Opaque: `!pip install foo` is `Opaque{ShellEscape}` giving effect `exec` Typed
  and an undeclared dependency (`external_ref` = External(pypi:foo)).

Rules:
- DRIFT works only with stable ids; old notebooks key cells by index, so their
  acks are flagged Unstable and refused as lock keys.
- LARGE001: `size(a, SourceLines)`; file bytes would be dominated by base64
  outputs and the rule would be wrong.
- SEC001 (lexical): the scanned set must include cell OUTPUTS; the adapter exposes
  them as `text(cell, Outputs)`. The key in d4's output FIRES. An adapter that
  skips outputs makes SEC001 UNRESOLVED("outputs not scanned"), not clean.
- CYCLE001 NOT-APPLICABLE (cells have uses, not imports). DOC001/COV001 roll up to
  ONE Unresolved per notebook (visibility and tests NotApplicable).
- A language rule NB001 (stale dependency: a binding whose def_exec exceeds
  use_exec) FIRES on c3; NB002 (use before definition by position) is the same
  query with `order: Backward`. Both are P+ over Q20 and need no IR extension.

### 7.5 Spreadsheet (cells as symbols, formulas as expressions, no files)

`budget.xlsx`: sheets Inputs, Rates, Report. `Report!B7` is
`=SUM(B2:B6)*(1+Rates!C3)`, `Report!B9` is `=INDIRECT("B"&A9)`, named range
`Total` = `Report!B7`, an external link `[prices.xlsx]Sheet1!A1`, a note on
`Inputs!A1` holding a directive.

Features: artifacts Cells, locator CellAddress, names Sometimes (named ranges),
nesting (workbook, sheet, range, cell), comments AnnotationOnly (cell notes), docs
notes, visibility Convention (hidden and very-hidden sheets, named ranges),
imports Static (external workbook links only), calls Static (formula references)
plus DynamicDispatch (INDIRECT, OFFSET), types Declared (number formats), tests
None, effects VocabPresent (WEBSERVICE, external links, VBA), consts true.

IR:
- Symbol policy (a declared completeness): only formula cells, named ranges and
  annotated cells are symbols; data cells are `Literal` nodes inside their sheet.
  This is `Partial(policy)`, so P- rules over "all cells" are UNRESOLVED by
  construction. Symrefs: `budget.xlsx#Report!B7`, `budget.xlsx::Total`,
  `budget.xlsx#Report` (a Sheet container).
- Edges: B7 References `B2..B6` (5 cells) and `Rates!C3`, Certain; Calls `SUM`
  (External builtin, Certain). `Total` References B7. B9 is
  `Opaque{DynamicDispatch, may_read_scope: Yes}`: its hi is every cell of the
  workbook. The external link is an External edge plus effect `fs.read` Typed;
  `WEBSERVICE` gives `net.connect` Typed.
- Digests: formula body is normalized to R1C1 so fill-down copies share a digest
  (clone detection R1 works natively); sig = kind plus number format; doc = the
  note; cached computed values are excluded from formulas (recalc noise) but ARE
  the body of a constant cell.

Rules:
- CYCLE001 on the References kind IS the circular-reference check: a cycle inside
  lo FIRES (Certain). No cycle can be certified clean while any Opaque exists,
  so the workbook gets UNRESOLVED instead of a pass.
- DEAD001 and REF001 (orphan sheet): referrers(sheet) is Bounds; the INDIRECT
  wildcard makes both UNRESOLVED for the workbook. Without INDIRECT they work.
- DOC001: public = named ranges; `Total` has no note, FIRES. Cell-level DOC001 is
  NOT-APPLICABLE (visibility None below named ranges).
- SEC001: scanned set = string cells, shared strings, formulas, notes (stated).
  The directive in the note binds to `Inputs!A1`; `frob:accept` there works
  through the AnnotationOnly channel.
- COV001/TEST UNRESOLVED once (tests None). LARGE001 uses used-cell count.
  Layout rules NOT-APPLICABLE. A `.xlsm` VBA project is `Unsupported`: one
  Unresolved per workbook for CAP, never a clean cell.

### 7.6 Verilog (modules, always blocks, clocked assignment)

```verilog
/** 8-bit counter with sync reset. */
module counter #(parameter W = 8) (input clk, input rst, output reg [W-1:0] q);
  always @(posedge clk) begin
    if (rst) q <= 0; else q <= q + 1;
  end
endmodule
module top(input clk, input rst, output [7:0] q);
  counter #(.W(8)) u0 (.clk(clk), .rst(rst), .q(q));
endmodule
module bad(input clk, output reg q);  always @(posedge clk) q = ~q;  endmodule
```

Features: names Sometimes (always blocks anonymous), nesting yes, comments Safe,
docs CommentBefore, visibility AllPublic for modules and ports and Private for
internals, attributes yes (`(* keep *)`), imports Static (`include`, packages),
calls Static (functions, tasks) plus Instantiates, types Declared (widths), tests
Heuristic (`tb_*`), effects VocabPresent (`$fopen`, `$system`, `$readmemh`), consts
true (parameters), opaque Preprocessor, loops with kind Elab for `generate for`.

IR:
- `rtl/counter.v::counter` (Module{hdl}); `params()` = ports with direction
  (clk in, rst in, q out) plus generic `W` default 8; `returns()` NotApplicable.
  `counter.always[posedge clk]` is an anonymous Process named by its sensitivity
  text (disambiguated `#2` on repeats; weak identity, flagged Unstable).
  `top.u0` is an Instance symbol with an `Instantiates` edge to `counter`
  (Certain; `.W(8)` has `const_value` Known). `q <= 0` is `Assign{NonBlocking}`.
- Preprocessor uses (`` `WIDTH ``) are `Opaque{Preprocessor, may_define: No}`;
  `const_value` is Unknown there but R1 token digests still work.
- Digests: counter sig = parameter and port list; body = process contents,
  comments excluded; doc = the block comment.

Rules:
- A universal HDL rule over IR: `Assign{mode: Blocking}` inside
  `Process{clocked: true}` FIRES on `bad` (exact pattern, P+). The same rule as a
  level-1 GPOL needs only `pattern(always @(posedge $CLK) ... $L = $R ...)`; both
  work, the IR form also covers VHDL and SystemVerilog.
- DOC001: public Exact = {counter, top, ports}; `top` has no comment, FIRES.
- DEAD001: uninstantiated modules are tops (`entrypoints()`), exempt.
- COV001: test items are Heuristic (confidence), so results are Advisory not
  Error. Forward closure kinds must include `Instantiates` (Q30 takes kinds).
- CYCLE001 on Instantiates: unconditional self-instantiation is a cycle in lo
  (FIRES); one inside `generate if` is in hi only, so UNRESOLVED.
- PERF-style loop rules must skip `Loop{Elab}`. CAP: `$system` gives `exec`,
  `$fopen` `fs.write`; the synthesizable subset has no net or fs, so those cells
  are `n/a`, one Unresolved per node (as designed). DPI-C `import` is an FFI bind
  for BIND (`via = dpi-c`).

### 7.7 Brainfuck (no structure except brackets)

```
++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.
```
plus, in the same file, the prose line `see ticket frob:todo X, then fix.`

Features: artifacts Files, names None, nesting only Loop, comments UnsafeLexical
(every non-command byte is a comment, but the prose above contains `,` and `.`
which ARE commands), docs None, visibility None, calls None, types None, tests
None, effects (`,` reads stdin, `.` writes stdout; needs detectors).

IR:
- Symbols: `Exact({})` plus the file-module `hello.bf`. Every rule that needs a
  symbol examines 0 subjects. `parse_status` is Ok iff brackets balance; an
  unmatched bracket is `Partial` and PARSE001 FIRES.
- `control()` = loops nested by bracket depth. `literals()` is `Exact({})`.
- Comments: maximal runs of non-command bytes. The prose line is NOT a comment,
  it executes (`,` reads input, `.` prints). A directive written inline, with a
  `because="..."` containing punctuation, changes the program. The adapter
  declares `UnsafeLexical`; the scanner refuses inline directives for it (a
  proposed finding DSL003 "directive in an unsafe comment channel") and a sidecar
  is required.
- Digests: file body over the COMMAND stream only; comments (prose bytes) do not
  drift acks. sig and doc are `Absent`.

Rules:
- DOC001, COV001, DEAD001, AFFECT001, BIND001: symbols empty, `subjects_examined
  = 0`, so ONE Unresolved("no symbols") per rule, never clean. DRIFT works at file
  granularity only.
- LARGE001: size unit Tokens (a program is one line). ARCH001: the module is the
  function; nesting = bracket depth; flagged "approximate: module as function".
- DUP001: R1 works but the alphabet is 8; `min_tokens` must be expressed in bits
  (`tokens * log2(alphabet)`), otherwise every program clones every other.
- PERF rules: vocabulary empty, NOT-APPLICABLE. SEC001: no strings exist; the text
  scan is valid and the clean claim is over bytes only. TODO001 fires on marker
  words in comment fragments, with the unsafe-channel caveat in the message.

## 8. Rules that silently assumed one language, and what replaces the assumption

### 8.1 v1 rules and mechanisms that assumed Python

| v1 rule or mechanism | Silent assumption | Re-express as (query + capability) |
|---|---|---|
| Symbol kinds: UPPER_CASE module assignment is CONST | naming convention infers kind | `kind(sym)` (Q06) from the grammar; naming conventions are adapter data |
| Publicness = leading underscore (python, bash); `__all__` defines exports | naming-convention visibility | `visibility` model NamingConvention or ExportList (Q07), `public_api` (Q33) honoring export lists |
| COV010 `__main__` guard is an entrypoint | python idiom | `entrypoints()` (Q37), adapter-defined |
| Docstring is the doc; docstrings scanned as directive carriers | doc is the first-statement string | `doc(sym)` style Docstring (Q09); `comments()` kind Docstring (Q10) so the directive scan sees it |
| Decorators stay in sig; `@property`, `@staticmethod`, `@pytest.fixture`, `@pytest.mark.parametrize` | decorators belong to the signature | `attributes(sym)` style Decorator (Q08), an `Attr` facet (Q38); pytest meaning lives in `test_shape` |
| Parametrized ids `path::Class.test[case]`, `symref_to_nodeid` (dot to `::`), DOC007 | pytest id grammar | bracket suffix stays opaque; the adapter `runner` owns id spelling; DOC007 disappears |
| Test discovery: `test_*`, `tests/`, conftest, pytest collect | python/pytest convention | `test_items()` (Q35) shape Attr, Name, Path or Custom; `is_test_file` becomes adapter data (`tests/`, `__tests__`, `_test.go`, `src/test/`) |
| TEST015 assertion evidence: `assert`, `self.assertX`, `pytest.raises` | python test vocabulary | `callee_vocab(lang, assert)` (Q47); empty means NotApplicable |
| CYCLE001 `import_time` (function-local and TYPE_CHECKING imports ignored) | python deferred imports | `ImportDecl.scope/time` (Q12); the rule ignores `Deferred` and `TypeOnly` by config; Rust `#[cfg(test)] use` is `TestOnly` |
| `resolve_local_import`: src-layout, pyproject roots, relative dots | python packaging | `resolve_import` (Q21) plus `package_of`/`module_path` (Q23); one resolver per ecosystem (Cargo, tsconfig paths, go.mod) |
| Call graph: "public callees are never edges", private by leading underscore (COV006) | python publicness inside graph construction | all callees are real edges with confidence; privacy comes from `visibility`, never from names inside graph code |
| ARCH101 LCOM4 via `self.field` | receiver convention | `fields(type)` plus `name_uses` carrying `receiver: SelfLike` set by the adapter (self, this, named Go receiver) |
| ARCH001 cyclomatic counts `except`, boolean ops, excludes `match/case` as flat dispatch | python control constructs | `control()` (Q16) counts branch arms uniformly; flat-dispatch exclusion is an adapter flag |
| Mutable defaults, isinstance chains, feature envy, data clumps (arch misc) | python idioms | GPOL `pattern` rules, never universal |
| EXHAUST001-004, `frob:raises`, `frob:callee-raises` | exception model (raise/except, may-raise) | language rule over `pattern` plus `Try`; Rust and Go use Result, a different rule; needs a feature `error_model` the adapter must declare |
| FFI001/002: pyo3 `Py*Error::new_err`, ctypes calls, `.pyi` docstring pragma | python-Rust boundary only | BIND `via` adapters (Q36); ctypes calls via `callee_vocab`; the `.pyi` is a Python-adapter artifact whose symbols are the counterparts |
| PERF010 yaml loader, PERF013 `ast.walk`, PERF014 `re.finditer`, WALK001 `os.walk`, RENDER001 bare stdout, TOOL003 `shutil.which`, PLATFORM002 `os.kill`, CACHE001 `@memoize_per_run`, PROFILE001, PORT001 | python stdlib calls | GPOL `forbid call <vocab path>` data (policy-pack examples, not core rules) |
| SEC005 argv taint (`shell=True`), SEC110 env-read sites | python vocabulary and taint | Q47 classes `env-read`, `exec`, `argv-sink`; SEC005 stays DROP (needs dataflow, not offered) |
| OPAQUE001 `eval`, non-literal `getattr` | python reflection | Q17 kinds `Eval`, `DynamicDispatch` plus per-language vocabulary (`eval`, `Function(...)`, `reflect`, `Class.forName`, `dlsym`) |
| ROUTE001 FastAPI/Flask decorators, web families | framework decorators | `attributes` plus a framework adapter pack |
| CONFIGPATH001 pydantic `*_path` fields; PII010 pydantic/dataclass fields | pydantic and dataclass | `fields(type)` plus attribute match; PII010 via Q15 |
| SUPPRESS001, FMT002 `noqa`, E501/F401/I001 | python tool dialect | comment text match (Q10); DROP |
| PKG001-003, VET008, VET-PY001-003 (setup.py cmdclass, `.pth`) | PyPI packaging | `keys(a)` on manifests per ecosystem pack |
| TESTMOCK001 | python mock | DROP |
| Dup R6/R7 execute python functions, z3 | runs user code | not an IR query; stays `run`; needs a declared `executable_sandbox` capability |
| Dup R2 alpha-renaming | python scoping of binders | `shape_digest(R2)` (Q40) needs NAM plus binder info (capability); R1 and R3 are syntactic |
| DOC006 `make <target>` and command pointers | Makefile and CLI | tiny Makefile adapter (comments, targets via `keys`) |
| SYS003 import conformance by stdlib `ast`; hard-coded `src/frob` root; fnmatch globs | python-only, one repo | `select()` (Q32) with real path and qualname globs; `edges(Imports)` (Q28) in every language |
| INV007 dotted `no_import="a.b"` | python module spelling | `module_path` segments (Q23); landed INV002 uses `::` and normalizes `-` to `_` (Rust spelling) |
| `classify_evidence_reach` UNKNOWN for non-Python scope | reach is python-only | Q30 over `Binds` edges returns `Unknown(frontier)` explicitly instead of a silent UNKNOWN |

### 8.2 Rust assumptions already inside landed generic crates (by reading)

| Where | Assumption | Replace with |
|---|---|---|
| frob-tests `catalog.rs`: `is_test_attribute`, `is_test_file` (`tests/`), `module_prefix` (`src/`, `lib|main|mod`, ROOT_DIRS), `Packages` (Cargo.toml) | Rust and Cargo layout in a crate named for all tests | adapter `runner`, `package_of` (Q23), `test_items` (Q35); nextest naming stays in the Rust adapter |
| gob-directives `bind.rs`: `is_test_item` (any `#[` line containing "test", any path segment `tests` or `test`) | Rust attributes | `test_items` (Q35); one definition of "test" |
| frob-obligations `doc.rs`: `has_doc_attribute` (`#[doc`) | Rust attributes | `doc(sym)` already includes attribute docs (Q09) |
| frob-obligations `todo.rs`/`util.rs`: marker words TODO FIXME XXX HACK; `comments.rs` (`//`, `<!--`, `#`) | English markers, three comment syntaxes | `comments(a)` kinds (Q10); marker set is config |
| frob-obligations `cov.rs`: exempts `implements.is_some()` | Rust trait impls | `Symbol.relation: Implements` generic (Haskell instances, Java overrides) |
| frob-obligations `inv.rs`: `locate` finds the `use` line by text | Rust `use` | `ImportDecl.loc` (Q12) |
| gob-symbols `graph.rs`: `is_rust`, `crate_and_module` in call and import resolution | Rust only; other languages get NO edges, silently | per-adapter `edges` capability; non-Rust returns `Unsupported`, not empty |
| gob-symbols `rust.rs`: `Type[Trait]` bracket | Rust impls | the bracket suffix is already opaque and generic (Haskell `Item[Show]`) |
| frob-check `PROC001` (gob-exec `proc001`): text scan for `std::process` | Rust, plus textual | R27: forbid-capability pattern over resolved imports and calls (same shape as INV002 and CAP001) |

## 9. Gaps found in the landed code (by reading; not run)

Each gap is where the landed adapter answers a polarity-sensitive query with one
bound without saying so. They are the concrete reason section 3 is needed.

| Gap | Where | Problem | Polarity effect |
|---|---|---|---|
| G1 | `frob-obligations/cov.rs` `adjacency` | `CallEdge::Unresolved` is dropped from reach; no poisoning. COV001 then needs the lexical `called_names` backstop | P- rule fed `lo`; the backstop approximates `hi` unlabeled |
| G2 | `gob-symbols/graph.rs` `resolve_call` | "Resolved" means a unique name within the crate; imports are never consulted; there is no confidence field, though code-model.md section 6 promises `Certain \| ImportVerified \| NameOnly` | `lo` and `hi` conflated |
| G3 | `gob-symbols/rust.rs` `call_target` | only `call_expression` is recorded; a function passed as a value (`iter.map(helper)`) is no edge | COV001, DEAD, affects miss real uses |
| G4 | `frob-tests/reach.rs` | calls inside macro token trees are invisible (documented); no `opaque_regions`; the lexical scan also sees names inside comments and strings of the body text | silent under- and over-approximation |
| G5 | `SymbolRecord` | carries no attributes; four sites re-read text above a symbol (`is_test_fn`, `has_doc_attribute`, `is_test_item`, `has_macro_export`) | duplication; Q08 absent |
| G6 | `bind.rs::is_test_item` vs `catalog.rs::is_test_fn` | two definitions of "test item": `#[cfg(test)]` helpers count in one and not the other | directive reorientation and test selection disagree |
| G7 | `rust.rs` `push` | sig is node text minus body; outer attributes are sibling `attribute_item` nodes (the doc scan skips them as previous siblings), so `#[pyfunction]`, `#[deprecated]`, `#[test]` are outside every facet; v1 kept decorators in sig and BIND depends on them | P0 drift misses attribute changes |
| G8 | `rust.rs` `push` | body facet is the collapsed text of the body block, so comments inside a body (and any `frob:` directive written there) change the body digest; v1 excluded comment nodes ("comments never affect sig/body") | spurious DRIFT001 and EXC005 |
| G9 | `markdown.rs` | a heading's body digest spans its nested subsections, so editing a child changes every ancestor's digest | possibly intended; unstated |
| G10 | `graph.rs` `public_api`/`exported` | only the modifier chain is followed; `pub use` re-exports, `cfg`, and workspace-crate boundaries are ignored | `lo` presented as exact; DOC001/COV001 silently miss re-exported items |
| G11 | `pipeline.rs` `extract_file` | `tree.has_errors()` only logs; `degraded` is set only when no tree exists; a partial parse is invisible to rules though the design promises PARSE002 | P- rules over a partial symbol set pass silently |
| G12 | `model.rs` | `SymbolKind` is Rust-shaped and differs from code-model.md section 2 (no `Field`, no `Other`, has `Impl`, `Heading`, `Static`, `TypeAlias`); `Visibility` lacks NotApplicable and Unknown | cannot express Prolog, spreadsheets, HDL |
| G13 | `gob-rules` `Finding.span` | a byte-range `Span` only; symbol spans are one contiguous range | blocks cells, sheets, multi-part symbols |
| G14 | `symref.rs`, `rust.rs` `disambiguate` | every symbol needs a name; collisions get `[dupN]` by order, unstable under insertion | wrong for Prolog clauses (one symbol), anonymous processes |
| G15 | `model.rs` `ImportEdge` | no span, scope (function-local, test-only, type-only), alias or confidence; `is_internal` means `crate::` only | CYCLE and INV need all of them |
| G16 | `rust.rs` `function` | items nested in function bodies and closures are not symbols; undeclared | needs `local_items: No` in the matrix |
| G17 | `gob-directives/comments.rs`, `frob-obligations/comments.rs`, `rust.rs` `doc`, `doc.rs` DOC002, `proc001` | comment and markdown lexing done five separate ways (two hand-rolled fence detectors, one tree-based code-range scan, three hash-comment scanners for TOML); TOML has no tree and is scanned by naive quote handling | `comments()` and `prose()` delete this duplication |
| G18 | `frob-tests/touched.rs` | touched set is Rust-only (`is_rust`) and ignores doc/attr facets and markdown | should be Q43 for every adapter |
| G19 | `pipeline.rs` `language_of` | any non-Rust, non-markdown file yields an empty `FileSymbols` with `degraded: false`, indistinguishable from an empty file | a TOML or Python file reads as "no symbols" and P- rules pass |

## 10. Coverage checklist and adequacy verdict

### 10.1 v1 families mapped (prefix to row; every prefix appearing in notes/v1/gates-and-rules.md)

A11Y R35; AFFECT R02; ARCH R16 (ARCH001, ARCH101-103) and R17 (ARCH104);
ARCHSCHEMA R26; AUTOFIX R25; BARETOOL R27; BASE R25; BUDGET R25; BUG R25; CACHE R25;
CAP R32 (v1 capacity) and R29 (v2 capability matrix); CHECK R25; CLAIM R34; CLAUDE R25;
COMPLIANCE R26 (001, 004-007) and R32 (002, 003); COMPLY R35; CONFIGPATH R34;
COV R03 (001, 007, 009, 010), R01 (005), R04 (006), R05 (002, 008), R04 (v2 001);
CPLACE R12; CPPTHROW R34; CROSSTICKET R25; CVEFP R21; CYCLE R15; DEAD R18; DEBT R13;
DEC R26; DEPLOY R27; DEPR R13 (001-004, 006) and R24 (005); DERIVED R25; DOC R03, R08,
R09, R10 (013, 014); DOCARCH R12; DOCBLOCKSSCHEMA R26; DOCENUM R10; DRIFT R01;
DSL R14; DSTACK R12; DUP R19; DUPSCHEMA R26; E R27 (E501); ENV R09; EXCL R25;
EXHAUST R34; F R27 (F401); FFI R30; FLAGCOV R34; FMT R14; FORBID R20; FUZZ R34;
GATERULE R26; GATES R26; GATESSCHEMA R26; GRAPHSCHEMA R26; GUARD R34; HOST R32; I R27
(I001); INV R07; INVLVL R07; KRB R32; LANDFMT R27; LANDPARITY R05 (001) and R16
(002); LANG R14; LARGE R16; LAUNCH R35; LAYOUT R35; LEDGERV1 R25; LEXCHECK R27;
LINT R32; MILE R25; MSCLOSE R32; NARR R12; NATIVE R27; NATIVESCHEMA R26; NEGEXIST R10;
OPAQUE R20; PARSE R14; PERF R33; PII R22 (010, 012, 013), R21 (011), R32 (001-005);
PKG R09; PLACE R14; PLATFORM R27; POL R20; PORT R27; PRE R25; PROFILE R27;
PROFILESCHEMA R26; PROTO R20; QUEUE R25; RACE R34; REF R11; REFSCHEMA R26; REG R26;
REL R31 (200-397 declared+proven), R29 (390-397 capability proofs), R32
(250, 340, 360, 380-383); RELWAIVE R13; RENDER R27; ROOT R11; ROUTE R34; SCOPE R25;
SEC R21 (001-003, 005, 110), R13 (004); SELFAUDIT R32; SEO R35; SQL R35; SQLEXPLAIN
R35; SUBJECT R25; SUPPRESS R34; SYS R28 (v1 001, 002, 102, 103, 106, 109, 110, 113; v2 001-009), R29 (v1 100,
101, 105, 111), R32 (v1 107, 108, 114-120, 2xx, 300-303, 900), R17 (v1 003; v2 004),
R26 (v1 004, design load error); SYSWAIVE R13; TDD R25;
TEST R06 (002-019), R04 (001), R14 (010); TESTINGSCHEMA R26; TESTMOCK R06;
TESTRUNNERSCHEMA R26; THREAT R26 (001, 006), R32 (002, 003), R28 and R29 (004, 005);
TICK R25; TIERBDEMO R27; TODO R12; TOOL R27; TOPSCALARSCHEMA R26; VERSION R24;
VET R23 (including VET-JS, VET-PY, VET-RS, VET-SOURCE-UNAVAILABLE, VET-TIMEOUT);
VMOD R32; WAIVE R13; WALK R27; WEBPERF R35; WEBSEC R35; WIRE R05; WRAP R27.
The 11 `*SCHEMA001` ids are covered by row R26 collectively (named above).
Also: HOST-BLAST R32; SEC-CVE-FINGERPRINT R21; PORT001-PATH/-IDENT/-DEFAULT R27.

v2 landed and designed families: COV R03/R04; TODO R12; DOC R03/R08; REF R11 (v2
REF001 is a ticket-ref check, v1 REF001 an orphan check, the same id for two rules);
INV R07; EXC R13; DRIFT R01; AFFECT R02; TEST R04/R06; TICK, SCOPE, PM R25; PROC,
CFG, GEN, PERF (engine), TOOL R27; PARSE, DSL R14; NARR R12; DEC, REG R26; REL003,
DEPR R24; CYCLE R15; ARCH, LARGE, DEAD, DUP R16-R19; SEC, PII R21/R22; VET R23.
Grimble: SYS R28/R32, CAP R29, BIND R30, ARCH R17, POL/GPOL R20. Crunk: COLOR, SPACE,
TYPE, RADIUS, SIZE, LAYER, CONTRAST, ORG, TW, BP, TOKENS, GALLERY, WAIVE R36/R37.

Checked by script after the last edit: 129 of 129 distinct v1 id prefixes
appear in 10.1, and every one appears in the section-2 table except the 11
`*SCHEMA` prefixes, which the table covers as one phrase (R26). Pending 0.

### 10.2 Adequacy verdict (what is and is not proven)

Proven by this derivation: every rule row has its facts expressed as one or more of
the 47 queries (the "Needed by" columns in section 4 are the proof; rows R25, R26
and R32 need none). The five fact clusters of section 2 map one-to-one onto query
groups P, B/G, D and E; no row needed a sixth cluster.

NOT proven and flagged:
1. No query currently answers dataflow or taint (SEC005, PERF008/015-018, PROTO).
   They are DROP/KEEP-with-cut in the v1 notes and this document assumes the
   cuts stand. If any is revived, a `dataflow(src, sink)` query joins group G
   with answer `Bounds`.
2. Q25 (types) is declared optional tier 3 with no adapter delivering it
   (Haskell, Prolog and Verilog examples all degrade through it). If PERF001
   ("list membership in a loop") returns, it needs Q25 or an over-approximation
   statement.
3. Q34 (effects) is the least settled: v1's 167 needle rows are lexical; the
   typed-detector design depends on Q20 and Q26 working per language, which only
   Rust will have at milestone 2.
4. Execution-backed rows (TEST005/016, BUG002/003, dup R6/R7, tailwind, render)
   are `run` side inputs; the IR cannot make them decidable and does not try.
5. Section 6 judgments about notebooks, spreadsheets and HDLs are reasoned from
   the languages' documented semantics, not from implementing those adapters.

### 10.3 Recommended changes to the design documents

- code-model.md section 3: make adapter capability cells per query (section 5)
  and add the `Approximate(bound_kind)` value.
- code-model.md section 5: replace the `IrKind` list with the additions in 4.6;
  make `Artifact` and `Loc` the root types instead of file and byte range.
- rules.md section 2: replace `inputs(graph, docs)` with `needs(Q..)` and a
  `polarity`; add the third fixture (feature-lacking language gives Unresolved).
- rules.md section 1: define `subjects_examined` in the finding envelope and make
  vacuous passes Unresolved.
- code-model.md section 6: give call and import edges the `lo/hi` bound and keep
  `Calls subset-of References`; add `Instantiates`.
- Fix or decide G7, G8 and G9 before the first `frob.lock` is committed by a
  consumer; changing digest inputs later invalidates every ack.
