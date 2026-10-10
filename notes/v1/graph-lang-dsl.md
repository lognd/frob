# frob v1 inventory: obligation graph, language layer, comment DSL, analysis tools

Source of truth: <frob-v1> (read-only, branch experimental, HEAD b10d67a0f).
Purpose: input to a from-scratch Rust redesign (frob v2). ASCII only. No code pastes.
Provenance tags used below: [src] = verified by reading source (or running the v1 parser
on probe files), [doc] = taken from docs/ only, not re-verified against source.
Ticket ids (T-####) are v1 history; they are cited so a reader can find the rationale.

## 0. Universe, coverage, honesty header

Phase-0 denominator (everything in the assigned scope, with size):

| Unit | Location | Size | Read how |
|---|---|---|---|
| graph | src/frob/graph/ (17 files) | 11.8k LOC | dsl.py, lock.py, digest.py, _models.py, _resolve.py, cache.py (schema+fingerprint), derived_state.py read [src]; callgraph/summary/reach/imports/affects read via graph.md [doc] + signatures |
| lang | src/frob/lang/ (22 files) | 8.5k LOC | _extract tables, ext table [src]; walkers via lang.md [doc]; qualname/publicness probed by running parse_file on 11 probe files [src] |
| nodeid, derived_state | 2 files | 49 + 171 LOC | read fully [src] |
| xref, outline, map, docs, exports, bind, cycle | 7 packages | 0.1k-0.35k LOC each | read [src] (bind, cycle, exports, map, xref fully; outline, docs partially) |
| refactor | src/frob/refactor/ (26 files) | 6.9k LOC | docs/design/refactor-verb.md + docs/commands/refactor.md [doc]; file list [src] |
| dup | src/frob/dup/ | 6.0k LOC | dup.md, dup-sota-survey.md [doc]; cache schema, DupConfig [src] |
| frob-core | frob-core/src/*.rs (9 files) | 4.6k LOC | export list from lib.rs [src]; kernels via dup.md [doc] |
| arch | src/frob/arch/ (35 files) | 15.4k LOC | arch.md [doc]; adapter/dispatch grep [src] |
| mutate | src/frob/mutate/ (2 files) | 1.2k LOC | mutate.md [doc] |
| perf | src/frob/perf/ (20 files) | 7.1k LOC | perf.md [doc] |
| docs read | graph.md, lang.md, dup.md, dup-sota-survey.md, bind.md, arch.md, mutate.md, perf.md, comment-dsl-directives.md, refactor-verb.md, language-adapter-tier-decision.md, structural-linter-adversarial-hardening.md, commands/refactor.md (head), testing.md (runner sections), gates.md (rule-table rows only) | | |

Verdict: all 8 requested topic areas covered; 0 nodes blocked. Depth is uneven by design:
arch (15k LOC, ~57 check categories), perf (PERF001-018 rule family) and refactor were
documented from their design docs plus source spot-checks, not line-by-line source reading.
Anything marked [doc] may be stale; Section 9 lists doc/source drift actually found.
Nothing in this file is "pending"; the limit is depth, not unexplored nodes.

## 1. Symbol identity

### 1.1 Symref grammar [src]

| Form | Meaning |
|---|---|
| path | whole file (repo-root-relative, POSIX separators, no leading ./) |
| path::Qual.Name | one symbol; qualname is a dotted path of enclosing containers then the symbol name |
| path#slug | markdown doc anchor (heading slug or explicit anchor id); used as edge src/target for doc nodes |
| path::Qual.Name[case] | pytest-parametrized test id: bracket suffix is opaque text and is never dot-split |
| "quoted title" | frob:tests target for runners whose ids are human titles (vitest): first token must look like a path with an extension, then free text |

- Only the FIRST "::" splits path from qualname (partition). Qualnames use "." for nesting.
- Rust trait impls produce a qualname containing "::" (probe: impl Tr for md::T yields
  md::T.t) so "::" inside a qualname is possible; rust module nesting uses ".".
- nodeid.symref_to_nodeid converts path::a.b to path::a::b (pytest node-id spelling),
  dot-replacing only the part before the first "[". testing/_runners has the same idea
  for pytest ({ids}) and a separate converter for cargo filters (drop path, "." -> "::").
- Resolution (graph/_resolve.resolve): exact symref hit; else a unique qualname match
  across the repo; else a unique ".suffix" match; ambiguity at either stage is
  AmbiguousSymbol; exact-qualname matches are counted before suffix matches.
  Resolution for DESCRIBES targets works even for a bare name with no "::".

### 1.2 How ids are derived per language [src probe + doc]

Identity = file path + qualname produced by a per-language recursive-descent walker over
the tree-sitter tree. Probed results (v1 behavior, including quirks to decide on):

| Language | Qualname rule | Notable behavior |
|---|---|---|
| python | Class.method, nested classes dotted; module-level def; UPPER_CASE module assignment is CONST | decorated_definition unwrapped (decorators stay in sig); closures inside function bodies are NOT symbols; type X = ... deferred |
| typescript/tsx, javascript/jsx | Class.method; function; export const -> CONST; interface/type/enum -> TYPE | export_statement peeled to find inner decl; class members public unless private/protected |
| rust | impl/trait/mod are transparent containers whose Self-type/trait/mod name is pushed: md.T.go, md.free | struct/trait -> CLASS; trait method decl qualname is path-like (md::T.t); pub or PyO3 export attr = public |
| c / cpp / cuda | cpp pushes namespace names (ns.A); methods Class.m | quirk: a free function inside a namespace is classified METHOD (ns.f kind=method); static = private; cuda adds __global__/__device__ rules |
| kotlin | Class.method, top-level fun, object | probe with companion object inside class produced a PARTIAL tree and 0 symbols (silent-salvage hazard; PARSE002 exists for this) |
| csharp | namespace segments pushed (N.M.C.m); property_declaration -> CONST | file-scoped namespaces handled; only literal "public" is public |
| java | Class.Inner.method; static final field -> CONST | package-private is NOT public (J.In private) |
| zig | const S = struct{} -> CLASS S; S.get method | pub is a sibling token before the decl; enum -> TYPE |
| bash | function foo -> FUNCTION; top-level assignment -> CONST | public = no leading underscore (convention) |
| css/scss | rule_set -> CLASS named by whitespace-collapsed selector; $var -> CONST | nested rules not symbols |
| html / vue | top-level element tag#id -> CLASS / the three SFC block kinds -> CLASS | raw_tree used by web lint rules instead of symbols |
| strata | no tree-sitter; strata-core (Rust pyo3 crate) parser lists declared ids, regex scan finds spans | node/store/queue public = (clearance == Public); other constructs public; walker fails closed (Err) if a declared id cannot be located |

Symbol kinds (5): FUNCTION, METHOD, CLASS, CONST, TYPE. Every grammar is collapsed into
these. For rust/ts/c/cpp CLASS, body_tokens is always empty (methods are separate symbols).
CONST and TYPE have no body.

RawSymbol fields [src]: qualname, kind, public, span (1-based inclusive line pair, trailing
newline artifact folded back), sig_tokens, body_tokens, doc_text, body_norm (canonical
cross-grammar node-kind vocabulary tokens, IDENT/LIT/FUNC_KW..., used by dup; empty for
const/type/non-python class/strata). RawComment: text (delimiters stripped), span,
enclosing (narrowest containing symbol qualname), following (earliest symbol starting
strictly after the comment end and within 2 lines). ParsedFile: path, language,
symbols, comments, content_hash.

### 1.3 Facets and digest algorithm [src: graph/digest.py]

| Facet | Input | Meaning |
|---|---|---|
| sig | RawSymbol.sig_tokens | declaration leaves (name, params, types, return type, decorators/attrs, visibility), body byte-range excluded |
| body | RawSymbol.body_tokens | body-subtree leaves, comment nodes and the docstring/leading-doc statement excluded; empty for class/const/type |
| doc | RawSymbol.doc_text | python docstring or contiguous leading comment block (/// , /** */, //, /* */), whitespace-collapsed by split/join |

- Tokens = leaf-node text of the tree-sitter subtree in order. Whitespace is never a node,
  so digests are formatting-insensitive by construction (no pretty-printer).
- Algorithm: each token CRLF/CR normalized to LF, tokens joined with NUL, sha256 hex of the
  UTF-8 bytes (empty token list hashes fine). doc: normalized text sha256. Three
  independent digests per symbol (Digests model: sig, body, doc).
- T-4391: line-ending normalization was added because multi-line string tokens carried
  raw CRLF on Windows and made acks platform-dependent.
- Consequence to preserve: renaming a parameter changes sig only (unless body uses it);
  editing body changes body only; editing a docstring changes doc only. Comments never
  affect sig/body.

### 1.4 frob.lock ack format [src: graph/lock.py, real file inspected]

- Tracked JSON file at repo root, written atomically (temp file + os.replace), keys sorted,
  indent 2, trailing newline. Top-level keys: ack_log (first, alphabetical), entries, version (1).
- entries: list of {ref, facet, digest}, sorted by (ref, facet). One row per acked
  (symbol, facet). ref is a symref. digest is the full sha256 hex.
- ack_log: append-only chronological audit list, never resorted. Entry: ref, facet,
  old_digest (null only for a first-ever ack), new_digest, reason, actor (OS login or
  "unknown"), at (date).
- acknowledge(lock, snapshot, refs, reason, actor): each ref must be an edge endpoint AND
  resolve to a symbol (else UnknownRef). Facets acked = every facet requested by any DESCRIBES
  edge targeting the ref (default sig) UNION always "body" (T-0556: so rewriting a documented
  body trips drift). The body facet is skipped for CLASS/CONST/TYPE (constant digest).
- reason is mandatory; refused when blank or (len < 15 or in a literal boilerplate set:
  ok, okay, fine, done, ack, acked, reviewed, looks good, lgtm, still accurate, still true,
  no change, n/a, na, verified, yes, todo, tbd, fix). Mirrors WAIVE002 discipline.
- Locking covers edge endpoints only, never every symbol (would churn on every commit).
- A missing frob.lock is an empty lock, not an error; only malformed JSON/schema is an error.

## 2. Languages, tiers, test runners

### 2.1 Grammar registry [src: lang/__init__.py _EXTENSION_TABLE, _extract.py]

Dispatch is purely by file extension. Grammars come from the tree-sitter-language-pack
Python package (one dependency, all grammars) plus the tree-sitter runtime.

| Extension(s) | Grammar | ParsedFile.language |
|---|---|---|
| .py | python | python |
| .ts / .tsx | typescript / tsx | typescript |
| .js .jsx | javascript | javascript |
| .rs | rust | rust |
| .c .h | c | c |
| .cpp .hpp .cc .hh .cxx | cpp | cpp |
| .cu .cuh | cuda | cuda |
| .kt .kts | kotlin | kotlin |
| .cs | c-sharp | csharp |
| .java | java | java |
| .zig | zig | zig |
| .sh .bash | bash | bash |
| .css / .scss | css / scss | css / scss |
| .html | html | html |
| .vue | vue | vue |
| .strata | none (strata-core Rust pyo3 crate) | strata |

17 tree-sitter walker keys (python, typescript, tsx, rust, c, cpp, kotlin, bash, csharp,
java, cuda, zig, css, scss, html, javascript, vue) plus strata = 18 labeled grammars,
ParsedFile labels collapse tsx to typescript and jsx to javascript. xref also knows .c++
.hxx .h++ as cpp (not registered in lang). Guards: 8 MiB file-size cap checked via stat
before read; 10 s parse timeout on a daemon thread (the thread is abandoned, not killed);
syntax-error trees are SALVAGED (partial symbols kept) and recorded in a partial-parse list
(PARSE002), a hard failure becomes PARSE001. A process-lifetime parse memo keyed on
(path, sha256 content) is reset at the top of each check run.

### 2.2 What each "tier" provides

v1 has no single tier enum; "tier" is the language-adapter-tier-decision doc's term for
how many facets a language implements. Two registries in lang/_support.py make this
explicit [doc+src]:

FACETS (subsystem integration; each cell IMPLEMENTED / NOT_APPLICABLE-with-reason /
KNOWN_GAP-with-ticket; missing cell or blank reason = LANG001 error):
grammar, capability (frob vet dangerous-op registry), dup (clone detection registry),
arch (structural checks), docblock (fenced-code doc-drift DOC004), refactor.

ADAPTER_CAPABILITIES (what the lang adapter itself implements; REQUIRED vs OPTIONAL):
symbol_walk, publicness, doc_extract, directive_parse (REQUIRED, includes backslash
continuation), call_graph, import_graph, test_discovery (OPTIONAL). LANG004 behaviorally
exercises each IMPLEMENTED cell against a hand-written fixture per language (python and
rust only for test_discovery; typescript/c/cpp/kotlin are structural-only because
exercising them needs npm/cmake/gradle). LANG004 only runs in frob's own repo.

Effective tiers as of source (derived from the registries and walker tables):

| Tier | Languages | Provides |
|---|---|---|
| A full | python | everything: symbols, publicness, docstring directives, call graph, import graph (ast-based file graph + tree-sitter), arch (legacy + normalized adapter), dup R1-R7, capability scan, mutate, refactor, perf, exports/consumers, bind (Rust side), test discovery (pytest) |
| B broad | rust, typescript, c, cpp, kotlin | symbols+publicness+docs+directives, call graph, import graph walkers, test discovery; arch via normalized adapters (ts/rust/kotlin written, cpp legacy) but analyze_project only wires python and cpp branches; dup + capability registered; refactor KNOWN_GAP except kotlin-noted |
| C registered-late | bash, csharp, java, cuda, zig | grammar+walker+import walker; capability/dup/docblock wired (java/cuda/bash/csharp done T-2906/3492/3493; zig pending at doc time); arch KNOWN_GAP (T-0329); csharp has a test collector (NUnit/Unity static parse) |
| D substrate-only | css, scss, html, javascript, vue | thin walkers whose job is to make parse_file succeed so raw_tree-based WEBSEC/A11Y/SEO lint rules can query raw nodes; facet wiring KNOWN_GAP |
| E non-tree-sitter | strata | symbols via strata-core; publicness from clearance; call_graph/import_graph/test_discovery NOT_APPLICABLE; needs native extension else LangError.NativeParserUnavailable |

language-adapter-tier-decision (T-0691): decided NOT to add Go/Java/C# adapters ahead of
real demand ("demand-driven", reopen when an estate repo gains such a tree). That decision
is overtaken: java and csharp adapters shipped later (T-1600/T-1601), plus zig/cuda/web.
LANG002 (error): a tracked file in a candidate language with NO grammar (Swift, Go, Ruby...)
is reported. LANG003: a registered language's KNOWN_GAP/NOT_APPLICABLE cell for a language
present in the repo is WARN if the ticket is open, ERROR if the ticket does not verify.

### 2.3 Per-language extraction tables [src]

- COMMENT_TYPES: per-language set of comment node type names (java: line_comment +
  block_comment; scss adds js_comment; zig doc_comment is separate and only that counts as
  doc text; others use a single comment type). python additionally scans docstrings as
  comments (_DOCSTRING_COMMENT_WALKERS), so a frob: directive inside a python docstring is
  live. strata comments are scanned by its own whole-line // scan.
- _IMPORT_WALKERS (extract_imports): python, c, cpp, typescript, tsx, rust, kotlin, bash,
  csharp, java, cuda, zig. extract_import_edges adds import_time=False for python imports
  inside function/class bodies or TYPE_CHECKING (cycle detection ignores them).
- resolve_local_import: resolves absolute python specifiers against bare root AND every
  pyproject-declared source root, relative specifiers by leading-dot walk (T-2195 fixed a
  src-layout bug that made cycle and layering checks silently vacuous).
- Test-discovery collectors (frob.testing): python (pytest collect), rust (cargo test
  listing), typescript (vitest via npx), c and cpp share one cmake/ctest collector (lists
  an already-configured build dir only), kotlin (reads existing gradle JUnit reports),
  csharp (static parse of NUnit/Unity attributes Test/TestCase/TestCaseSource/UnityTest).
  No collectors for java, zig, bash, cuda, css/html/js/vue, strata.
- Unity: lang/_project_detect detects a Unity root (Assets/ + ProjectSettings/
  ProjectVersion.txt) and excludes Library/Temp/Logs/obj/*.meta.

### 2.4 Test-runner registry [src+doc: testing/_runners.py, frob.toml]

User-declared in frob.toml as repeated [[test.runner]] tables: language, command, all_command,
cwd (default "."), timeout_s (default 900), collector ("", perf, v8, jfr; picks a perf
hot-graph profiler adapter). EXACTLY ONE placeholder must appear in command: {ids} (pytest
node ids), {files} (test file paths), {filters} (cargo name filters), {regex} (alternation
for ctest). Unknown keys flagged by TESTRUNNERSCHEMA001.

| Language | Typical entry | Notes |
|---|---|---|
| python | uv run pytest -q {ids}; all: uv run pytest -q | symref -> node id via dot->"::" before "[" |
| rust | cargo test --lib {filters}, cwd = crate dir | MULTIPLE same-language entries allowed, routed by cwd prefix of the symref path; a rust file under no crate = UnroutedItem error; needs Python>=3.11 + libpython env (PYO3_PYTHON) discovered by frob |
| typescript | npx vitest run {files}, cwd web | quoted-title frob:tests targets |
| c/cpp | ctest --test-dir build -R {regex} | |
| strata | none needed | invoked natively (frob sys audit) |
| bash, csharp, java... | stub entries that route fixture files through bash -c "uv run pytest ..." | a hack so test-shaped fixture files satisfy the one-placeholder rule |

A language with selected tests and no runner is a hard error (NoRunner). Selection algorithm
(testing.md): working diff -> touched symbols -> TESTS edges (either endpoint may be the
test; the test side is picked by is_test_file) -> contract ripple (up to 4 uses-contract
hops) -> touched test files self-select -> fallback for unbound files (package default,
suite, or warn; module-level edits to tracked files force package fallback even under warn).
Native extensions are declared in [[native]] (python import name + build_cmd) so collection
can fingerprint build state.

## 3. The comment DSL

### 3.1 Grammar [src: graph/dsl.py]

- Line form: frob:VERB TARGET [key="value" ...] inside any comment. Comments are extracted
  by frob.lang so # // /* */ are all stripped before dsl.py sees text. A leading "#" left
  over (python docstring lines) is stripped.
- _LINE_RE: ^frob:(verb)(rest)?$ ; attributes: \w+\s*=\s*"([^"]*)" ; NO escape for a literal
  double quote inside a value (a nested quote is refused by name); a quoted TARGET uses the
  same quote grammar and may contain spaces; unquoted target containing a quote is an error.
- Binding of a directive to a symbol (src of the edge): the symbol FOLLOWING the comment
  within 2 lines wins over the ENCLOSING symbol; a gap-free run of stacked comment lines
  inherits the nearest resolved following binding; no symbol at all binds to the bare file path.
- Continuation: a line ending in backslash (after right-strip) folds into the next
  physically adjacent comment line (lineno+1), joined with the EMPTY string; edge line number
  and src are those of the first physical line; dangling backslash is literal; CRLF-safe.
  A break may only fall between tokens (between list entries or between attributes); a break
  inside the bare target token yields a DSL001 "mid-token" error. (C/C++ // comments cannot
  use continuation: the C line-splice rule merges them first.)
- Multi-target: only tests and doc accept comma-separated targets (one Edge each, same
  kind/src); a comma inside quotes is not a separator; empty entry = malformed.
- frob:quote(...) is the mention escape: the whole span is replaced by same-length dots
  before any scanning, in code and markdown and the live-tracker citation scanner.
- Markdown form: HTML comments. Fenced code blocks and same-line inline code spans are
  blanked before matching, so documentation can show syntax. Directive in markdown binds
  to the nearest PRECEDING heading's slug (GitHub-style slugify: lowercase, drop chars other
  than word/hyphen/space, spaces to hyphens one-for-one, empty -> "top"; repeated slugs get
  -1, -2 suffixes). Edge src for doc side is path#slug.
- Every line that starts frob: but fails to parse becomes a MalformedDirective (file, line,
  reason), never dropped (DSL001 family; WAIVE001/DEBT001/DEPR001/TEST010 are verb-specific
  views of the same list).

### 3.2 Verbs that become graph edges (_VERB_TABLE, 22 verbs) [src]

| Verb | Target | Attributes | Semantics / main consumer |
|---|---|---|---|
| doc | path#anchor (multi-target ok) | none | enclosing symbol is described by that doc anchor; COV001 (public symbol needs one), DOC002 (anchor must resolve to heading slug or explicit anchor id), COV007 (private src is an error), AFFECT001 |
| uses-contract | symref | none | symbol depends on the target's signature; a target sig change flags this symbol; reverse-walked by affects(); test-selection contract ripple (4 hops); AFFECT002 |
| invariant | INV-### id, or the word terminates | optional no_import="mod,mod" (dotted module list); establishes="text" (non-empty); kind="time-stable" + horizon="<N><d|w|m|y>" (must come together); for PERF005 terminates form: reason + measure | code anchor of an invariants/INV-###.md statement; INV001 (evidence), INV002 (anchor), INV005 (reach), INV007 (forbidden import), INV008 (needs frob:tests kind=property) |
| ticket | T-#### | none | symbol satisfies ticket (COV002 accepts this or an open ticket whose scope covers the file); live-tracker citation checks |
| todo | T-#### + free-text note | note = remainder, not key=value | deferred work bound to an open ticket; TODO001 flags bare TODO/FIXME; TODO002 flags closed/missing ticket |
| waive | RULE-ID | reason="..." OR preset="name"; until="YYYY-MM-DD" or ticket-closed:T-x / file-absent:path / symbol-absent:path::Sym; ceiling=N (arch metric re-fire) | suppress one gate rule at this site; matching modes: symbol-exact (canonicalized symref), file-scoped, package-prefix (for TEST003/4/7); WAIVE001 (no reason), 002 (rule can never match), 003 (over-broad), 004 (matches zero findings), 005 (until expired); some rules unwaivable (TEST008, SEC003, TICK001/002, EXCL001, ...). Presets in a single table (_waive_presets) |
| debt | RULE | reason + ticket required; optional until (date or X.Y.Z) | TEMPORARY waiver; implicit frob:todo synthesized if none co-located (mismatch with explicit todo = malformed); DEBT002 ticket must be open, DEBT003 past until = error, release REL001 refuses while ANY debt is open |
| deprecated | free-text since | sunset="YYYY-MM-DD" (date only) + ticket required; reason optional | public symbol with dated exit; DEPR003 warn inside window, DEPR004 error after sunset; release blocks only when past sunset |
| tests | symref, or quoted title, or pkg path / system id | kind = unit (default) / integration / e2e / property; integration target = package path, e2e = declared system id | test-side declaration preferred (written on the test, names production symbol); the parser REORIENTS so canonical edge is src=impl, target=test; legacy production-side form is reported redundant. Test-shapedness decided by collector token rule (C# NUnit attrs, pytest names) else lexical path rule; stamped in attrs origin_test_shaped. Consumers: test selection, COV006, TDD001 (commit-order), TEST010, evidence reach |
| decision | AD-### | none | symbol implements a decision record |
| channel / boundary / secret | strata construct id | none | bind code to strata Flow/Boundary/Secret-clearance node (SYS001/002) |
| enforces | concept id | none | rule/detector declares registry concept; cross-checked against docs/design/registry (REG008/009) |
| protocol | name (or inferred) | states="S1,S2" initial=S (must be in states) cleanup=always/on-error/process-exit-ok (default on-error) | typestate machine; also INFERRED for init/deinit, open/close, acquire/release name pairs in one file; protocol with zero binders flagged |
| transition | (attribute-only) | proto, from, to all required; target becomes proto | function performs a state transition (PROTO001-005) |
| requires | (attribute-only) | proto, state required | function callable only in that state |
| acquire / release / escapes | resource name | none | resource-tracking DSL folded into protocol summaries; PROTO005 verifies cleanup |
| enumerates | doc anchor (code side) | none | code side of doc<->collection enumeration; markdown side carries members="a,b,c" and DOCENUM001 AST-diffs it against the real literal (ack-immune) |
| until | T-#### | none | binds a negative-existence claim ("does not exist yet") to the ticket that will build it; NEGEXIST001 |

### 3.3 Edge kinds that exist without a code verb [src: _models.EdgeKind]

- describes: markdown-only. Form frob:describes SYMREF [sig|body|doc] in an HTML comment;
  facet defaults to sig. This is the doc->code direction; the facet selects which digest an
  ack tracks. Not in _VERB_TABLE (a code-side frob:describes would be an unknown-verb
  malformed directive; the only code-side use is a convention in .pyi module docstrings read
  by FFI001 by regex).
- claims-absence: heuristic, emitted from markdown prose matching negative-existence phrases
  (does not exist, not yet built/implemented/wired/supported/available/shipped/landed);
  CHANGELOG.md exempt.
- Markdown also accepts, as real edges: enumerates (with members=), until, ticket (HTML
  comment form), doc.

### 3.4 Markers owned by other subsystems (not graph edges)

Reserved marker verbs (_RESERVED_MARKER_VERBS; parse_line returns None so they are NOT
malformed; consumers scan text with their own regex):

| Marker | Where | Meaning |
|---|---|---|
| frob:raises Type | above a def (python/pyi) | declared propagated exception type (EXHAUST001/002; FFI001 reads the pyi stub side) |
| frob:callee-raises A, B | same-line comment at a call | declared raise set of that callee (may-raise resolver; empty set = honest "raises nothing"); FFI002 demands one at ctypes calls |
| frob:used-by consumer | file | declared consumer for REF001/002; REF003 verifies the consumer references back |
| frob:secret-fake reason="..." | next to fixture | marks a secret-shaped literal as fake (SEC gates) |

Ticket-body directives (parsed from ticket markdown, not source): frob:no-behavior-change
reason="..." (inverts BUG002: the designated repro test must PASS at the parent commit;
bare form without reason is treated as absent), frob:must-still-pass NODE-ID (positive
control; guards fixes that narrow a rule until it matches nothing), frob:env-absent NAMES
and frob:env-absent-unverifiable reason="..." (BUG002 environment declarations),
frob:waive BUG002 reason=... in ticket bodies.

Markdown-side markers: frob:waive RULE reason="..." honored only for REF001, REF002, DOC004,
DOC006, INV003, INV004, BUG002 (any other rule id, or a reason whose closing quote comes
before leftover text, is malformed); frob:invariant (INV-id anchor in markdown); frob:claims
VIEW (DOC003/SYS; unproved claim marker); frob:external-reader dir="x" reason="..." (ROOT
asset-dir exemption); frob:generated-start / frob:generated-end NAME (fenced generated
tables, e.g. cli-commands, DOC005).

Scaffold marker: frob:managed-block BEGIN <id> / END <id> in Makefile, .gitignore, .bat
(comment token # or ::), written by frob scaffold apply; text between markers is frob-owned
and replaced in place, outside untouched; WRAP001-003 drift gates compare managed regions.
Block kinds: "text" (marker pair) and "hook" (whole git-hook file).

### 3.5 Doc-anchor semantics

A doc node is path#slug. COV001: every PUBLIC symbol needs a doc edge (either direction:
frob:doc in code or frob:describes in markdown). COV009: siblings sharing one doc anchor
must all be reviewed when one changes. DOC001: obligated docs must be anchored or reachable
by links. DOC004/DOC006: fenced code / prose pointers into own code surface must resolve.
Markdown scanning covers docs/**/*.md plus top-level *.md except the ticket ledgers.

## 4. Edges, drift, queries, reachability

### 4.1 Graph model [src: _models.py]

GraphSnapshot (frozen pydantic): root, symbols {symref -> SymbolRecord(id(path,qualname),
kind, public, digests, span)}, edges (tuple of Edge(src, kind, target, origin "file:line",
attrs map)), malformed directives, parse_failures, file_hashes, BuildStats(parsed,
cache_hits). All targets (tickets, invariants, anchors) are opaque strings; the graph
never validates them (joins live in frob.gates, to avoid graph->tickets cycles).
Edge kind consumers (summary): DOC/DESCRIBES -> drift, COV001/7/9, AFFECT*, DOC002;
USES_CONTRACT -> affects, test ripple; TESTS -> selection, COV006, TDD001, INV005/008;
WAIVE/DEBT/DEPRECATED -> suppression and expiry gates; TICKET/TODO -> COV002, TODO002;
INVARIANT -> INV001-011; PROTOCOL/TRANSITION/REQUIRES/ACQUIRE/RELEASE/ESCAPES -> PROTO001-005;
CHANNEL/BOUNDARY/SECRET -> SYS001/002; ENFORCES -> REG008/009; ENUMERATES -> DOCENUM001;
UNTIL/CLAIMS_ABSENCE -> NEGEXIST001; DECISION -> DEC gates.

### 4.2 What counts as drift [src: lock.py + gates]

- DRIFT001: an acked (ref, facet) whose current digest differs from the lock digest.
  Facets compared are those recorded in the lock (sig, body, doc). A ref that is no longer
  a symbol is NOT stale (it is dangling instead). StaleItem lists origins of every edge
  touching the ref.
- DRIFT002 (dangling): an edge endpoint that contains "::" and is not in symbols; for
  DESCRIBES the target is resolved through resolve(); both src and target are checked. For
  each dangling edge, rename candidates = symbols whose BODY digest equals any digest the
  lock ever recorded for the vanished ref, plus symbols sharing the vanished qualname.
- Facet semantics in practice: sig drift = contract changed (doc probably wrong); body drift
  = behavior changed under an acked doc (always tracked since T-0556); doc drift = the
  symbol's own docstring changed. Body-only refactor of an undocumented-contract does not
  invalidate a sig-facet ack, but every ack carries body too.
- DOCENUM001 and NEGEXIST001 are content-verified and ack-immune (never read frob.lock).
- Ack remedy is human assertion with required reason; renames re-link by candidates
  (stable ids in comments were explicitly rejected).

### 4.3 affects / why / query [src+doc]

- frob graph query REF: resolve and print stored edges (edges_from/edges_to).
- frob graph why REF: loads frob.lock, computes drift, prints acked facets, STALE rows
  (was/now digests, affected dependents, remedy "frob ack REF --facet F"), DANGLING rows with
  candidates, or "clean"; JSON payload has acked_facets, stale, dangling, is_edge_endpoint.
- frob graph affects REF [--max-depth N --max-nodes N]: affects(snapshot, ref, max_depth=8,
  max_nodes=500) returns AffectedSet(root, dependents, docs, tests, truncated). BFS
  reverse-walks USES_CONTRACT only (cycle-guarded by visited set), and at every visited node
  collects doc/describes anchors (both directions) and TESTS edges. truncated means the
  dependent walk was cut; doc/test sets are exact for visited nodes.
- AFFECT001/002 gate: for symbols the working diff touches, FAIL if a dependent doc anchor's
  file (001) or dependent symbol's file (002) was not also touched.
- caller_dependent_files (T-4553): one hop on the call graph (verify_imports=True) adds
  caller files of changed symbols, capped at 200 with a truncated flag; fails open to
  touched-files-only.
- Scope closure (T-0998, SCOPE002 warn): at ticket-scope declaration time, flag scoped code
  whose doc target / covering test is out of scope (and the reverse), plus private helpers
  outside scope called by scoped code (only_used_by_scope strong case).
- classify_evidence_reach (T-3046): REACHES / DOES_NOT_REACH / UNKNOWN for whether bound test
  evidence calls (by token or via private call-graph closure) a scoped symbol; UNKNOWN when
  scope is a non-Python file. Measured 94.3 percent REACHES on v1's own ledger. Not wired as
  a blocking gate.

### 4.4 Call graph and COV006 limits [src+doc: graph/callgraph.py]

- Edges come from RawSymbol.body_tokens name scanning (token adjacency: identifier followed
  by "("), best effort, no scope/overload resolution. Only calls to PRIVATE (leading
  underscore) or same-file callees become edges; a call to a PUBLIC symbol is never an edge.
  closure(graph, start, max_depth, max_nodes) is a bounded BFS, cycle-guarded, start excluded.
- Cross-file short-name matching is over-inclusive by default; verify_imports=True restricts
  to callee files the caller's file imports (flags exist on build_call_graph,
  build_reference_graph, build_ordered_call_graph; default False; only scope_private_helper_gaps
  and caller_dependent_files use True). build_reference_graph_module_scoped is the attribution
  variant. mark_unresolved=True adds UNRESOLVED_CALLEE sentinel edges (used by PROTO001-005
  poisoning); default False because downstream callers split symrefs on "::".
- CallGraph.degraded_languages self-discloses when a language's call_graph/import_graph cell
  is KNOWN_GAP. bash is a documented gap (bare-word calls cannot be token-detected).
- COV006 (warn): a frob:tests edge to a PRIVATE symbol whose named test has no call-graph
  reachability to it. LIMITS: public targets are skipped (public callees are never edges, so
  reachability is structurally unprovable); a test reaching a private helper only through a
  public same-file entry point is a false positive (partially rescued by a one-hop
  public-wrapper lookahead, T-0506, 98 -> 89 findings); name-based, no dispatch/dynamic
  resolution; Python-oriented (other languages share the token detector but lack private
  naming convention).
- graph/imports.py: ast-based Python-only resolved-import file graph (other languages
  contribute UnresolvedImport "unsupported-language"); dynamic imports and above-root relative
  imports are reported as unresolved, never dropped. Measured on v1: 2522 resolved edges.
- graph/summary.py: Tarjan SCC + bottom-up fixpoint over CallGraph computing requires/
  transitions/acquired/released/escaped sets per function, with monotone poisoning (any
  UNRESOLVED_CALLEE or poisoned callee poisons callers) and not_analyzed/timeout loud
  channels; also a report-only path-confinement census (ROOTED/ESCAPED/UNKNOWN lattice over
  fs.write sites under tests/). The confinement census is a measurement, not a gate.

## 5. Cache and derived state

### 5.1 Files under .frob/ [src+doc]

| File | Owner | Content |
|---|---|---|
| .frob/cache.db | graph/cache.py | the graph snapshot cache (below) |
| .frob/parse-artifacts.db | graph/cache.py (separate file since T-1464 to avoid worker contention) | parsed_artifacts table |
| .frob/dup.db | dup/_cache.py | fingerprints + verdicts |
| .frob/vet.db | vet | capability scan cache |
| .frob/hotgraph_sketches.db | perf/_sketch_store | one sketches table, quantile sketches per section |
| .frob/perf/*.pstats, ratchet_findings.json | perf | content-addressed profiles; ratchet findings |
| .frob/coverage-stamp, .frob/baseline, frob-coverage.lock.json | testing/check | JSON stamps |
| gate result cache (sqlite) | gates/_gate_cache.py | per-gate dependency-tracked results |
| .frob/telemetry.jsonl | telemetry | excluded from integrity manifest |

### 5.2 cache.db schema (schema version 4) [src]

Tables: meta(key PK, value) holding root, schema version, fingerprint; files(path PK,
content_hash, mtime_ns, size); symbols(symref PK, path, qualname, kind, public, span_start,
span_end, digest_sig, digest_body, digest_doc); edges(id autoinc, file, src, kind, target,
origin, attrs JSON text); malformed(id, file, line, reason); parsed_artifacts(content_hash,
fingerprint, payload; PK both) exists in the same schema string but is used in the separate
parse-artifacts.db. Everything is derived and safe to delete.

### 5.3 Incrementality and invalidation keys

- Per-file incrementality: build_graph walks the tree once (prunes excluded dirs before
  descent), checks stored (mtime_ns, size) first (one stat per file, important on WSL/9p),
  reads and content-hashes only on stat mismatch; a touch without edit refreshes stat only;
  changed files re-parse and store_file_data replaces all rows of that file (delete+insert);
  vanished files are pruned. Ingest commits in batches (T-4282) to shorten sqlite exclusive
  windows. load_graph is cache-only: CacheStale if any on-disk hash moved, CacheCorrupt if
  unreadable/never built. get_snapshot = load-or-build, the one entry point consumers use.
- Schema invalidation: on schema-version mismatch or non-sqlite file, wipe and recreate.
- Fingerprint invalidation: meta.fingerprint = "|"-joined "pkg==version" for frob,
  frob-strata, tree-sitter, tree-sitter-language-pack. Mismatch -> derived rows deleted.
- Parse-artifact key: (content_hash, fingerprint), never path. It is opt-in by env var inside
  ProcessPoolExecutor workers; payload is ParsedFile JSON.
- T-4484 parser-identity bug (open, queued, high): fingerprint covers installed package
  versions only (the frob dist version is constant across a dev checkout), so a change to
  frob's own directive-continuation folding (dsl.py) moved neither key. Stale parsed
  artifacts kept answering for unchanged files, yielding 10 local-only TEST010 malformed
  errors that CI (fresh checkout) never saw; only frob clean --deep cleared it. Stated fix:
  key must cover parser identity (digest of dsl/lang modules or an explicit parser-version
  constant bumped on every fold/attr change) or payload must carry it and be rejected on
  mismatch. v2 lesson: the cache key must be a hash of the extraction code/grammar set, not
  a package version; a compiled Rust binary can simply embed its build id.
- Gate result cache: only a closed, hand-audited allowlist of gates is cacheable (pure
  function of snapshot-derived state plus scalars); TrackedSnapshot records which files a gate
  actually touched; the sorted full file-hash key set is folded into every entry (any file
  add/remove invalidates all cacheable gates).
- dup cache: fingerprints keyed (body digest, rung); verdicts keyed (d1, d2, method,
  corpus_epoch) with last_used for LRU eviction beyond cache_entries (default 200k).

### 5.4 Derived-state locking and integrity [src]

- process/_derived_lock.derived_state_lock(root, exclusive) is a cross-process flock keyed on
  the canonical root path. frob check holds it SHARED for the whole run; build_graph takes
  the write (exclusive) lock only around prune + final commit (T-3478; formerly the whole
  parse, causing a ~19 min xdist stall). Same-process reentrancy via a held-count registry;
  worker processes inherit "already held" through env FROB_DERIVED_LOCK_HELD_KEYS stamped by
  the pool owner (fixed a real deadlock, T-0982). dup takes the lock only around individual
  cache writes (T-1224).
- sqlite lock contention: shared _with_lock_retry (2 s poll, 30 s budget) -> CacheLocked ->
  Err(GraphError.CacheLocked); a locked parse-artifact cache degrades to a plain parse.
- seed_disposable_worktree_cache copies the primary cache.db into a fresh land worktree
  (declines if a journal shows a live writer).
- derived_state.py: manifest DERIVED_ARTIFACTS = graph-cache (.frob/cache.db, sqlite),
  dup-cache, vet-cache (sqlite), coverage-stamp, baseline (json), frob-coverage.lock.json.
  verify_derived_state returns per-artifact (present, healthy, sha256 fingerprint, detail);
  sqlite validity = 16-byte magic header; json validity = loads. Absent = healthy. Used by
  frob doctor and frob check to fail early on a corrupt cache.

## 6. Analysis tools

### 6.1 dup (clone detection) [doc + src spot checks]

Rung ladder (all operate on frob.lang token/tree output, so cross-language by design):

| Rung | Technique | Where computed | Status |
|---|---|---|---|
| R1 | exact token hash of whole body | python | default on |
| R2 | alpha-renamed (R2-normalized) token hash | python | default on |
| R1.5 | generalized suffix array + LCP over concatenated R2 token stream of the corpus; maximal exact sub-symbol regions >= region_min_tokens (default 15); region_run_cap 200 bounds O(k^2) pair emission | frob-core exact_regions | opt-in [dup].region_kernel |
| R3 | canonical AST-subtree hash (r3_canonical_hash) | frob-core | opt-in via native_rungs; documented gap: feeds same input as R2 so cannot be distinguished from R2 by any fixture |
| R4 | Moss winnowing k-gram fingerprints + candidate_pairs LSH + Zhang-Shasha APTED tree edit distance (apted_similarity; statement-sequence tree_edit_similarity is only the fallback) | frob-core | opt-in native_rungs |
| R5 | Weisfeiler-Lehman graph hash (wl_hash) over a def-use graph from symbol_tree; co-occurrence proxy graph is the fallback | frob-core | opt-in native_rungs; proven cross-language python<->typescript at 0.88 |
| R6 | observational equivalence: run both pure python functions on generated inputs | python (importlib, NO sandbox) | opt-in --probe; python only |
| R7 | bounded SMT (z3, tiny int/bool straight-line functions) | python, optional dep | opt-in; Err outside subset |

Pipeline: fingerprint per changed file (keyed by body digest in dup.db) -> LSH candidates ->
verify (APTED similarity, statement alignment) -> report/gate. Extras: call-graph-aware
helper inlining before fingerprinting (private callee closure depth 3, 12 nodes) and a
helper-population pass with a lower token floor (8); anti-unification (Plotkin lgg,
frob-core anti_unify) producing a template with $hole_N and a suggested extraction signature
with type-hole classification; exhaustiveness matrix (rung x clone type x language, every
cell claimed by a litmus fixture or excused, drift-locked by a test). Defaults:
threshold 0.85, min_tokens 40, `frob dup --min-lines 6`. Gates: DUP001 (error: diff
introduces a clone of a pre-existing symbol), DUP002 (warn: clones within the diff), DUP003
(frob-core missing while enforce). Legacy Type-1/2 scanner (_legacy*) still backs the
default check stage and CLI for py/cpp/cs.

Design rule worth keeping: no pure-Python fallback for R3+ (CoreUnavailable if the native
module is missing). v2 is native, so the rule becomes moot.

frob-core crate [src]: Rust cdylib+rlib, pyo3 0.22 abi3-py311, tree-sitter 0.25 with grammars
python 0.25, rust 0.24.2, cpp 0.23.4, typescript 0.23.2, 21 pyfunctions, all GIL-releasing.
Clone: r3_canonical_hash, winnow_fingerprints, candidate_pairs, tree_edit_similarity,
apted_similarity, anti_unify, wl_hash, run_exact_regions. Call graph (graph._core):
resolve_call_edges, called_names, ordered_called_names, referenced_names, unresolved_exempt_names
(all five parity-tested but NOT dispatched by default: benchmarked net slower than pure Python
because of PyO3 marshaling). Arch: near_duplicate_indices
(Ratcliff/Obershelp batch clustering; wired as default, 2.6x faster), py_function_metrics
(single-pass python arch metrics). Extraction: extract_tree_python/rust/cpp/typescript (golden
tested vs the Python walkers, NOT wired to any consumer). Capability: scan_python_capabilities.
Lesson: FFI-per-symbol calls lose to pure Python; only batch kernels won.

### 6.2 arch (structural smells + metrics)

`frob arch [path] [--json] [--max-function-lines N --max-class-methods N]`; analyze_project
returns ArchResult(root, suggestions[], files_examined); ArchSuggestion = file, line, category,
severity (warning/suggestion/info/error), message, detail, symref, metric. Only python and
cpp branches exist in analyze_project dispatch [src: __init__.py lines 431/444]; typescript,
rust and kotlin have written LanguageAdapter classes (normalized model) but are not
production-dispatched. Thresholds are keyword args; frob.toml [arch] supplies calibrated
values via load_arch_config (max_function_lines 60, max_class_methods 12, max_local_imports 8,
max_nesting_depth 4, max_file_lines 800, lcom4_min_methods 6, lcom4_min_field_using_methods 4,
god_module_min_exports 10, god_module_min_clusters 3, mixed_concern_min_decision_points 2);
severities per category in frob.toml; waivable per function with reason and ceiling=N.

Metrics actually computed (the core of the ~57 categories):
- long-function: lines > max AND (max nesting >= 3 OR cyclomatic proxy >= 8); cyclomatic
  counts if/for/while/except/boolean-op/conditional-expr (python) or catch/&&/|| (C++);
  match/case and switch/case excluded as flat dispatch; the two inner thresholds are
  constants, deliberately not config.
- god-class (method count), high-coupling (distinct local imports via extract_imports +
  resolve_local_import), deep-nesting, large-file (LARGE001 gate).
- LCOM4 (ARCH101): methods nodes, edge if sharing a self.field, union-find components >= 2.
  god-module (ARCH102): >= 10 exports partitioning into >= 3 naming/usage clusters.
  mixed-concern-function (ARCH103): I/O call + string formatting + >= 2 decision points.
- abstraction-opportunity (3+ functions with same annotated signature, minus dispatch
  families/registries; requires signature specificity or body similarity), design-pattern
  recommender (isinstance chains, state chains, telescoping constructors...).
- SOLID families on the normalized model: OCP (type-dispatch, non-exhaustive enum match), LSP
  (ARCH104-108: override raises NotImplementedError, signature variance, strengthened
  precondition, weakened postcondition, noop override), ISP (fat-interface ARCH109,
  narrow-client ARCH110), DIP layering (frob.toml-declared layers + allowed edges, resolved
  imports; gate id ARCH104 collides with the LSP ARCH104 label in the arch table, T-4663), no-DI construction.
- Type-design, logging discipline, fallibility (unhandled result, swallowed exception),
  misc smells (mutable default, feature envy, data clumps, magic literal, dead private code),
  concurrency hazards (pool-in-pool, fork-after-threads, lock-order cycle, unguarded shared
  write, GIL-bound in threadpool, async hazards), may-raise resolver (python raise sets with
  UNKNOWN/ubiquitous tiers; C++ noexcept analysis).
- Normalized model (_normalized.py): NormalizedModule/Class/Function/Field/Param/Branch/Loop/
  Call/CallArg/FieldAccess/Return/Raise/Catch/Subscript + LanguageAdapter protocol, so a
  check is written once for all languages. This is the one genuinely reusable design idea.
- module-dependency-cycle reuses frob.cycle (below). Hardening principles
  (structural-linter-adversarial-hardening): measure the logical unit not the syntactic one,
  cross-check declarations against extracted ground truth, fail closed on unresolvable
  constructs, bounded reason-required waivers, and gated config (loosening is an audited
  event).

### 6.3 cycle

frob.cycle.graph.DependencyGraph (adjacency sets, add_node/add_edge/neighbors/nodes) and
find_cycles = iterative Tarjan SCC over sorted node order; returns SCCs of size >= 2 or
self-loops. Inputs: file nodes with edges from extract_import_edges filtered to
import_time=True, resolved by resolve_local_import (app/cycle_runner). Logs a WARNING when a
node's language has a KNOWN_GAP import_graph. Gate CYCLE001 scales severity by size (2 nodes
info, 3-5 warning, 6+ error). arch module-dependency-cycle reuses it.

### 6.4 bind

Regex-only (not tree-sitter, not the symbol graph): scan .cpp and .rs for "// BIND: <sig>"
comments (tagged pybind11 / pyo3), scan .h declarations (one regex) and Rust fns after
#[pyfunction]; check() normalizes (lowercase, strip types/refs, collapse spaces), extracts
the function name and reports a Mismatch when no source signature CONTAINS that name
(substring match, so weak). Output: BindingDecl/SourceDecl/Mismatch lists; CLI flags
--json --list-bindings --list-sources. Invariant INV-007. Does not compare parameter
lists or types in practice.

### 6.5 exports

exports_package(pkg_dir): for each non-__init__ .py in ONE directory (non-recursive), run
outline_file and collect public (no leading underscore) functions and classes; render a
generated __init__ block "from pkg.mod import a, b" with duplicate names aliased as
mod_name and an __all__ list; header comment "generated by: frob exports". Python only.
exports_consumers(symbol): runs xref and keeps usages whose line matches a python
import-statement regex (answers "who imports this symbol", T-0858).

### 6.6 xref, outline, map, docs

| Tool | Computes | Inputs | Outputs |
|---|---|---|---|
| xref | definition site + usages of a name | symbol name, root, optional --lang | XrefResult(symbol, definition, usages[file,line,context]); tree-sitter extensions use iter_identifiers (identifier-leaf stream) and RawSymbol definitions; other extensions (and .strata) fall back to plain text search; --cross-file hides same-file hits; paths POSIX |
| outline | per-file module outline | one file | ModuleOutline(path, lines, imports, functions[name,signature,line,doc first line], classes[name,line,methods]); signature rebuilt from sig_tokens; any lang frob.lang parses; private hidden by default |
| map | repo skeleton with size | root, depth | MapResult(files[path, lines, tokens ~ chars/3.5, public symbol names, private count]); _SOURCE_EXTS hard-coded to py/c/cc/cpp/cxx/h/hpp/hxx (stale vs frob.lang) |
| docs | docstring extraction + doc search | file/symbol, docs dir | extract_docstrings (every language via RawSymbol.doc_text; module docstring row python-only), overview, keyword search over docs/*.md headings; also generate docs/commands/<verb>.md pages from the argparse tree (never overwrites existing) |

Sunset note: standalone xref/outline/map porcelain was on a sunset clock (T-0580/T-0802);
exports consumers was kept for the one recurring query.

### 6.7 mutate

frob mutate FILE [--path DIR] [--json] [-- TEST-CMD]. Python only. ast.NodeTransformer
produces point mutations, one per run: comparison op swaps (< <-> >=, == <-> !=), arithmetic
swaps (+ <-> -, * <-> //), and/or swap, bool-constant negation. generate_mutants(source, file,
line_ranges) then run_mutations(root, file, test_argv, timeout_s=300, max_mutants,
line_ranges): write mutant to the real file, run the test command, restore. Score = killed/
total; a timeout counts as killed; exit 1 if any survivor. Safety: crash-safe backup journal
(T-0857) with cross-process lock, PID-reuse-safe liveness, stale-restore with content
verification (so a SIGKILL cannot leave mutated source on disk); MUTATION_RUN_ENV=1 recursion
guard. Consumed by TEST016 (diff-scoped, bounded). Other languages and a score-floor gate
were recorded follow-ons.

### 6.8 perf

- Profile: frob perf profile -- ARGV (cProfile -> content-addressed .frob/perf/<sha>.pstats;
  --tests wraps the python runner). Heat: join pstats rows (file, line, func) onto symbol spans
  of the graph snapshot, rank by cumulative time, --annotate prints per-line gutters, --smells
  intersects hot symbols with PERF findings ("hot AND quadratic").
- Static PERF rules (tree-sitter over frob.lang): PERF001 membership test on list in loop,
  PERF002 index/find/count in loop, PERF003 nested-loop equality join, PERF004 sort in loop,
  PERF005/006 recursion without proven termination / tail recursion (prove via frob:invariant
  terminates reason= measure=, default error, sound-not-complete), PERF007 configured heavy
  call from 2+ top-level symbols without a shared cache, PERF008 loop-invariant spawn/walk
  effect (EffectGraph substrate), PERF009 hot-graph ratchet regression, PERF012 duplicate
  identical subprocess spawn on one path. Up to PERF018 exist.
- Hot-graph: language-neutral SampledStack(SampledFrame(file, line, weight)); python sampler;
  adapters parse_perf_script (Linux perf), parse_v8_cpuprofile (node), parse_jfr_print (JVM,
  class->file map from normalized modules); resolve stream onto Sections (function/loop/branch
  bodies from NormalizedModule); persisted as DDSketch-style log-bucket quantile sketches
  per section in sqlite with decayed merge and LRU size cap; frob perf hot queries it;
  advisories and ratchet (PERF009, default 50 percent relative p50/p90 shift).

### 6.9 refactor

Transactional move / rename / split / move-module of Python symbols and modules (design
T-1135, engine T-1197+). Phases: Resolve -> Plan (full rewrite plan before touching files) ->
Apply (one WIP commit in the caller's worktree) -> Verify (import graph resolves, pytest
--collect-only, frob check --delta identity-aware zero new findings) -> Commit or rollback
via git reset --hard to its own pre-transaction commit. Rewrites: python imports/call sites
and every frob-owned reference: frob:doc/tests/enforces/uses-contract/invariant/ticket/
todo/decision/channel/boundary/secret/protocol/transition/requires/acquire/release/escapes
targets, frob:waive src symrefs (preserving the three match modes), PII012 allowlist keys,
registry handled_by citations, archived ticket evidence node ids, frob.lock acks (same digest
at new symref inherits the ack), plus prose: docstrings, docs/**, heading-slug anchors, with
an explicit "not rewritten, review by hand" report for unresolvable mentions. Split adds a
re-export shim in the source module, chunked transactions (default 5 symbols), and carry-
forward of needed imports. --alias-conflict {error, rename-dest}. Python-only for moving;
directive rewriting is language-agnostic; frob.bind BIND comments are flagged, not rewritten.
Lang facet "refactor" is KNOWN_GAP for every language but python (T-3231 tracks per-language
reference scanners). docs/modules/refactor.md does not exist; the page is docs/commands/refactor.md.

## 7. Cross-language symbolic code binding

How a directive in one language refers to a symbol in another TODAY:

| Mechanism | Direction | How resolved | Weakness |
|---|---|---|---|
| frob:doc / frob:describes | code (any language) <-> markdown anchor | symref path::qualname is language-agnostic text; markdown anchors are language-neutral; any language's symbols can be described | none cross-language by itself; this is the one clean mechanism |
| frob:tests target | test symbol (any lang) -> production symbol (any lang) | target is an opaque string path::qualname; runner chosen by the TEST file's language; a python test can name a rust symbol (T-3005/T-3007 shape), EVIDENCE then REACH is UNKNOWN for non-Python scope | no check that the test actually exercises the other language; pytest ids can only prove python reach |
| frob:channel/boundary/secret | code symbol -> .strata design construct id | joined by gates against the loaded strata model (SYS001/002) | strata vocabulary stays out of graph; binding is by string id; tier-2 `code=<glob>` binding + import conformance is python imports only |
| .pyi module docstring pragma "frob:describes <path>.rs" | stub -> rust source | FFI001 pairs stub with .rs, scans #[pyfunction] bodies for Py*Error::new_err and panic-class sites (unwrap/expect/panic!) and cross-checks against the stub's frob:raises declarations | regex over Rust source, not graph edges; only strata-core and frob-core stubs |
| // BIND: <sig> comment | C++/Rust glue -> native declaration | frob.bind regex name-substring match | not in the graph at all, not symref-based, substring match only |
| FFI002 | ctypes/cffi call site | demands a same-line frob:callee-raises | text regex |
| frob:uses-contract | symbol -> symbol | symref string | works cross-language textually, but digest/sig semantics differ per language grammar |
| frob:used-by | file -> consumer file | file-level, REF003 verifies back-reference | file granularity |
| Test selection | symref -> runner | language of the symref's file picks the [[test.runner]]; rust routed by cwd | python-centric id conversion helpers |

Gaps (v1 did not solve):
1. No first-class edge kind for "implements / binds / wraps" between symbols of different
   languages (PyO3 #[pyfunction] vs its .pyi stub vs the python caller; pybind11 vs C++
   decl). Each pairing uses an ad-hoc regex scanner.
2. Signature drift across languages is not detectable: sig digests are per-grammar token
   hashes and are not comparable across languages; no normalized signature type model.
3. frob.bind does not use the symbol graph, does not compare parameter lists, and covers only
   pybind11/PyO3.
4. Call graph and COV006 reachability are single-language token matching; a Python test
   calling a Rust function through PyO3 is invisible to evidence reach (UNKNOWN by design).
5. refactor cannot move or rewrite across languages (BIND comment flagged only).
6. dup's cross-language claim holds only for R5 (structural WL hash); R1-R4 miss cross-
   language clones because tokens differ; body_norm vocabulary exists but R1-R3 do not use it.
7. Strata binding is import-level python only.

## 8. v2 recommendations

### 8.1 Keep, semantically unchanged

- The symref grammar path::Qual.Name (POSIX repo-relative path, dotted qualname, first "::"
  splits) and path#slug for docs; keep bracket-suffix opacity for parametrized tests.
- Three-facet digests (sig/body/doc) over normalized leaf-token streams with NUL join and
  newline normalization; tree-sitter leaf tokens make formatting-insensitivity free.
- Lock semantics: endpoint-only locking, always-include-body rule, mandatory reason with
  boilerplate refusal, append-only ack_log with old/new digest, sorted deterministic JSON,
  atomic write.
- Drift = stale ack + dangling edge with rename candidates (body-digest and same-qualname).
- Directive grammar (verb target key="value"), backslash continuation with empty-string
  join and first-line reporting, binding rule (following within 2 lines beats enclosing),
  frob:quote mention escape, "never silently drop a malformed frob: line", markdown HTML-
  comment form with code-span blanking and GitHub slugs, test-side frob:tests declaration with
  canonical reorientation.
- Verb semantics: doc, describes (with facet), uses-contract, invariant (+ attrs), ticket,
  todo, waive (reason or preset, until, ceiling), debt, deprecated, tests (kind), enforces,
  enumerates, until. Waiver matching modes (symbol-exact canonicalized, file-scoped, package
  prefix) and the principle that waivers are reasoned, bounded and expire.
- affects() reverse-walk of uses-contract with doc/test collection and truncated flag; why
  output shape (acked/stale/dangling + remedy).
- Content-verified ack-immune checks (DOCENUM, NEGEXIST) as a category separate from acks.
- Fail-loud capability registries: per-language facet cells accounted for (implemented / N/A
  with reason / known gap with ticket) with behavioral conformance fixtures; self-disclosure
  of degraded analyses (degraded_languages).
- Normalized code model + LanguageAdapter protocol (write each check once).
- Cache design: content-addressed, derived-only, delete-safe, per-file incremental with
  stat-then-hash check; shared/exclusive derived-state lock with narrow exclusive window.
- Mutation journal safety; dup's no-fallback native-kernel rule (trivial in Rust);
  per-file size cap and parse timeout; salvage-but-report partial parses.
- Rung ladder R1-R5 + R1.5 conceptually; APTED, winnowing, WL hash, suffix-array regions,
  anti-unification templates are all worth porting (they already live in Rust).

### 8.2 Simplify

- One language registry as data: extension -> grammar -> {walker, publicness rule, comment
  node types, import walker, test collector, runner template} instead of five parallel tables
  (_EXTENSION_TABLE, COMMENT_TYPES, _WALKERS, _IMPORT_WALKERS, _TEST_DISCOVERY_COLLECTORS,
  plus per-subsystem LANGUAGES registries and the FACETS/CAPABILITIES derivation layer). Make
  the facet matrix a build-time-checked struct rather than a runtime-derived pydantic report.
- Replace the verb table + per-verb validator functions + regex tail-checks with a single typed
  directive schema (verb -> required/optional attrs with types and enum values) and one
  parser; generate the docs table and the malformed-directive messages from it. Move
  ticket-body and markdown-only markers into the same schema with an explicit "surface"
  field (code, markdown, ticket-body, scaffold) instead of per-gate ad-hoc regexes (v1 has at
  least 8 independent frob:waive readers).
- Unify qualname rules and fix quirks: cpp namespace free functions classified METHOD,
  rust trait-impl qualnames containing "::", kotlin partial-tree silent zero symbols. Define
  one container model (namespace / type / impl / module) with a documented separator and
  kind rules.
- Fold the three call-graph variants (call, reference, module-scoped, ordered) into one
  resolver with import verification ON by default and explicit confidence on each edge;
  drop name-only over-inclusion unless a consumer asks. Make public callees real edges
  (v1's "public is never an edge" trick is what forced COV006 false positives).
- Make cache keys the hash of (parser build id + grammar versions + schema); drop the
  dev-version fingerprint (T-4484), and consider one sqlite file (v1 split parse artifacts
  out only to dodge worker contention that a single-process Rust parallel parse would not
  have).
- One edge-endpoint model: edges currently mix symrefs, doc anchors, ticket ids, invariant
  ids, rule ids and free text in the same string fields. Use typed endpoints (Symbol, Doc,
  Ticket, Invariant, Rule, Text).
- Treat duplicated per-language sets (test-shaped detection lexical vs token rule) as one
  trait on the language record.
- Docs/code drift in v1 (Section 9) shows hand-maintained prose tables rot; generate them.

### 8.3 Drop (or defer behind a clearly optional layer)

- Python-ecosystem coupling in the core: pytest node-id spelling, ast-based import graph,
  python-only exports/mutate/refactor/R6/R7, src-layout declared-roots hacks. Keep as
  language plugins, not core.
- FFI-per-symbol Rust kernels (called_names, referenced_names, ordered_called_names,
  unresolved_exempt_names, extract_tree_* parked kernels) and the pure-Python duplicates they
  mirror; in v2 the walkers and kernels are one codebase.
- frob.bind as a regex scanner; replace with a real cross-language binding edge (below).
- xref/outline/map/docs porcelain as separate packages: reduce to graph queries
  (symbols, identifier usages, outline) over the same snapshot; map's hard-coded extension
  list and token estimate are cosmetic. Keep exports consumers' question as a query.
- Legacy Type-1/2 dup scanner and the dual DUP/legacy code paths.
- The 57-category arch scanner as a monolith: keep the normalized model plus a small core
  of cheap, high-signal metrics (size, nesting, cyclomatic proxy, LCOM4, coupling, cycles,
  layering contract) and make the SOLID/pattern/hazard families optional rules; none were
  production-wired for typescript/rust/kotlin anyway.
- Confinement census (report-only) and the protocol/typestate DSL (protocol, transition,
  requires, acquire, release, escapes) unless a v2 consumer commits to PROTO001-005;
  v1 has 35 transition + 32 requires + 30 protocol mentions, mostly in its own tests.
- Scaffold-specific managed-block markers belong to the scaffold feature, not the DSL.
- The test-runner stub entries for bash/csharp/java fixtures (hack for the one-placeholder
  rule).

### 8.4 Add (v1 gaps worth closing in v2)

- A first-class cross-language binding edge: binds(symref_a, symref_b, mode) with verbs
  such as frob:binds <path::symbol> [via="pyo3"|"pybind11"|"ctypes"|"wasm"], resolvable by
  the graph, with per-mode adapters that extract the foreign-side signature (PyO3 attrs, .pyi,
  pybind11 def calls) and compare arity/types using a normalized signature model; this
  replaces bind, FFI001 scanning and the ad-hoc .pyi pragma, and lets affects/drift/refactor
  traverse the boundary.
- A normalized cross-language signature (name, params with types, return, visibility) so sig
  digests can be compared across languages, not just within a grammar.
- Typed test evidence per language (runner + collector contract) so cross-language
  frob:tests can be verified, with explicit UNKNOWN state kept.
- Confidence-annotated call edges (certain / import-verified / name-only).
- Parser-identity-keyed caches from day one.
- Self-describing language registry that is test-fixture driven (LANG004 idea, but for every
  language, run in CI for the Rust binary itself).

## 9. Doc vs source drift found while reading (do not trust docs blindly)

| Doc claim | Source reality |
|---|---|
| graph.md: "five grammars", source ext table .py .ts .tsx .rs .c .h .cpp .hpp .cc .hh | graph walk filters by lang.supported_extensions() (all 17+strata); the table in Implementation notes is stale |
| comment-dsl-directives.md: "Current verbs (22)" and 17 walkers | matches _VERB_TABLE count (22) and _WALKERS (17); lists omit describes (markdown-only) and many reserved/ticket-body markers |
| comment-dsl-directives.md says no-behavior-change/managed-block not listed | they exist (ticket-body and scaffold markers) |
| lang.md: "seven tree-sitter grammars", supported_languages example of 7 | registry has 17 walkers plus strata |
| language-adapter-tier-decision.md (T-0691): no Go/Java/C# adapters | java and csharp adapters shipped (T-1600/T-1601); decision file is historical |
| graph.md: directive in markdown "applies from the comment to the next heading of equal or higher level" | source binds each markdown directive to the nearest PRECEDING heading slug only (src = path#slug); no end-of-scope logic |
| dup.md: R3 documented as canonicalizing literals/ordering | doc itself admits R3 receives R2 normalization; no distinct R3 behavior |
| dup-sota-survey.md: "frob dup --probe does not exist, R6 unreachable" | dup.md and CLI doc describe --probe as wired; survey section 0 is older |
| arch.md Scope: "Python and C/C++ today" with 57-row table including rust/ts/kotlin adapters | dispatch matches (python/cpp only); normalized-model checks run python-only in production |
| map._SOURCE_EXTS hard-coded | not derived from frob.lang |
| T-4484 open | cache fingerprint ignores parser source identity (see 5.3) |
| refactor-verb.md describes frob refactor as not-yet-built | engine and CLI wired (docs/commands/refactor.md 940 lines; src 6.9k LOC) |

Generated for frob v2 planning. No Phase-1 items pending; depth limits are stated in Section 0.
