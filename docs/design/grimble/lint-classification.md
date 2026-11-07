# Design lint classification: portable vs language-specific

Status: draft
Owner: grimble

Ticket 01M6SJHBH2JK72HAE60AFYDFWX. Governing text: docs/design/shared/universal-model.md
section 5 (queries Q01-Q47) and notes/research/lint-requirements.md.

Rule of thumb: a lint is **portable** when everything it asks of the code is a U query
(calls, bindings, flow, effects, comments). It is written once against `gob-ir` through a
`gob-symbols` adapter and must run on every adapter language. A lint is **language-specific**
only where U has no query and the idiom is tied to one engine or language.

## 1. Classification

| Lint | Family | Class | Reads today | Migration status |
|------|--------|-------|-------------|------------------|
| ERR001 empty-error-handler | err | portable | U `Adapter` handler nodes and `Bind`/`Apply`; text for catch-all and rethrow judgements | **migrated (ASQ6BMN)** |
| ERR002 discarded-result | err | portable | U `Bind`/`Apply`/`Phase` spans; text for the signature `Result` check | **migrated (ASQ6BMN)** |
| ERR003 silent-catch-all | err | portable | U `Bind`/`Apply`/`Phase` spans; text for the signature `Result` check | **migrated (ASQ6BMN)** |
| PAIR001 acquire-without-release, React/effect vocabulary | effect | portable | U `apply` nodes for discovery; tree-sitter for return/async/def-use | **partly migrated (this slice)** |
| PAIR001, Unity lifecycle vocabulary | unity | language-specific (vocabulary) over a portable shape | tree-sitter C# | pending; shape portable, vocabulary per language |
| RES001 unpaired-resource-acquisition | res | portable | U `Apply`/`Unit`/`Anon` spans and parent chain; scope text for handle use | **migrated (SEME5JK)** |
| PATH001 absolute-host-path | path | portable | U `lit` / adapter string nodes and their byte span; tree-sitter for test context | **migrated (MP46BP8)** |
| PATH002 string-path-separator | path | portable | path-conversion roles, flow (`path/flow.rs`) | pending: needs U def-use and call-argument queries (section 3) |
| PATH003 path-in-command-line | path | portable | path-conversion roles, flow | pending: needs U def-use and call-argument queries (section 3) |
| TIME001 local-clock-read | time | portable | U `unit(function/method)` spans for scopes; clock roles and flow stay on tree-sitter (`time/flow.rs`) | **partly migrated (H0R1VGM)**; flow pending, needs U def-use and call-argument queries (section 3) |
| TIME002 naive-aware-mix | time | portable | U `unit(function/method)` spans for scopes; clock roles and flow stay on tree-sitter | **partly migrated (H0R1VGM)**; flow pending, needs U def-use and call-argument queries (section 3) |
| TESTQ001-003 (no assertion, nondeterminism, control flow) | testq | portable | U `unit(function/method)` and `anon(function)` spans gate test discovery; attribute vocabulary, helper resolution and body roles stay on tree-sitter | **partly migrated (H3W82PE)**; rest pending, needs the section 2f queries |
| NEAT010 effect ceiling | neat | portable | U `unit(function/method)` spans gate unit discovery; claims, callee vocabulary and `effects(unit)` stay on tree-sitter | **partly migrated (KM8C4P3)**; rest pending, needs the section 2g queries |
| NEAT031 dispatch-site-owns-logic | neat | portable | U `unit(function/method)` spans gate unit discovery; dispatcher weighing stays on tree-sitter (`neat/dispatcher.rs`) | **partly migrated (KM8C4P3)**; rest pending, needs the section 2g queries |
| UNITY201 lookup-in-hot-code | unity | language-specific | Unity hot-method idioms | stays; revisit if U gains engine roles |
| UNITY202 allocation-in-hot-code | unity | language-specific | Unity hot-method idioms | stays |
| UNITY301 legacy-input-under-input-system | unity | language-specific | Unity input API | stays |
| UNITY302 physics-force-outside-fixed-update | unity | language-specific | Unity physics API | stays |

## 2. What this slice migrated (EFFECT family)

`effect::scan` now discovers effect hooks and acquires from the file's universal term
(`gob_symbols::model_of_source_at`): every `apply` node of kind `call`, `method` or `new`
is classified by its head `ref` (`useEffect`, `React.useEffect`, `.subscribe`, `new WebSocket`).
`PAIRS` is matched against that head, so a global receiver such as `window.setInterval` is not
mistaken for a bare `setInterval`. The scan runs on every `Language::ALL` variant: the
JS-family languages (TypeScript, TSX, JavaScript, JSX) fold through the TypeScript adapter and
all other languages yield no sites.

The cleanup-pairing judgement (what the effect returns, whether the callback is `async`, which
handle a release clears) still reads the tree-sitter node whose byte span the term node names.

## 2b. What the err slice migrated (ERR001-003)

`err::scan` builds the file's universal term (`gob_symbols::model_of_source_at`) and reads
sites from it: Python and TypeScript/C# handlers are the `except_clause` / `catch_clause`
adapter nodes, Rust discards are `Bind` nodes (`let _ = ..`, `if let Err(_) = ..`) whose
right-hand side is an `apply` (call or method), a macro `Phase`, or an awaited expression.
Function declarations come from `Unit{function|method}`. The tree-sitter query layer, and the
parse/query `ScanError` variants, are gone.

Judgements the model cannot express stay textual, read from the byte span the node names:
catch-all type and handler header, body emptiness and rethrow-or-log, and the `-> Result`
return type of a signature.

## 2c. What the res slice migrated (RES001)

`res::scan` builds the file's universal term (`gob_symbols::model_of_source_at`, JS-family
languages through the TypeScript adapter; every other `Language::ALL` variant yields no sites)
and reads calls from `apply` nodes of kind `call`, `method` and `new`, classified by their head
`ref`. A method call's receiver is the first child after the head. The enclosing class and
function scopes are the `unit(class)`, `unit(function|method)` and `anon(function)` ancestors,
found through a parent map built from the term's children. A test-framework exemption is an
ancestor `call` whose head is `it`, `describe`, and so on. The bound name is read from the
enclosing `variable_declarator`, `assignment_expression` or field node (value right after the
`=` literal), or, for a top-level `const`, from the `unit(const)` name and value groups.

Judgements that stay textual: whether the handle is used elsewhere in scope (a word count over
the scope's byte span), and receiver identity (normalised receiver text).

## 2d. What the path slice migrated (PATH001)

`path::scan` builds the file's universal term (`gob_symbols::model_of_source_at`; the TypeScript
family through `effect::model_path`, Rust, Python and C# by extension) and reads string literals
by node kind and byte span: Rust `string_literal` / `raw_string_literal` adapter nodes, Python
`string` lits and adapter nodes (a docstring folds to a `str` lit and so is never a candidate),
TypeScript `str` lits that open with a quote and the `template` op lit, and the C# string lit
kinds. The literal is decoded from its source slice and judged as before. PATH002 and PATH003 stay
on tree-sitter, as does the in-test judgement (attribute and name checks).

## 2e. What the time slice migrated (TIME001, TIME002)

`time::scan` builds the file's universal term (`gob_symbols::model_of_source_at`, `time.rs` /
`time.py`) and takes the function and method scopes from the `unit(function|method)` nodes by
byte span; each span is mapped back to its tree function node (a decorated Python function's span
starts at its decorator, so the node is found among descendants ending at the span end). Import
aliases, the callee vocabulary, binding classification and the naive/aware judgement stay on
tree-sitter. Rust and Python are the only languages with clock roles; every other language stays
Unresolved without building a model.

## 2f. What the testq slice migrated (TESTQ001-003)

`testq::scan` builds the file's universal term (`gob_symbols::model_of_source_at`; `testq.rs`,
`testq.py`, `testq.cs`, the TypeScript family through `effect::model_path`) and collects the
byte spans of `unit(function|method)` and `anon(function)` nodes. A tree-sitter test candidate
(Rust `#[test]` fn, Python `test*` def, JS/TS `it(..)` callback, C# `[Fact]` method) is kept only
when a model span ends where it ends and starts at or before it (a decorated Python unit starts
at its decorator). Test marks, skip and exemption rules, same-file helper resolution, and the
assertion, nondeterminism and control-flow roles stay on tree-sitter. Languages without test
roles stay Unresolved without building a model.

Missing universal-model queries (reported, not invented), continuing section 3:

19. (testq) Attributes, decorators and annotations of a unit as typed accessors (`#[test]`,
    `@pytest.mark.skip`, `[Fact(Skip=..)]`), to identify tests and skips without text.
20. (testq) A call-graph or callee-by-name query within a file, for the same-file helper
    resolution of TESTQ001.
21. (testq) Structured control-flow node kinds (`if`, loop, `match`, `switch`, `try`, ternary)
    in a unit body without descending into nested functions, for TESTQ003.
22. (testq) A call-chain accessor (root name and modifiers such as `it.skip.each`) for JS/TS
    test and suite declarations.

## 2g. What the neat slice migrated (NEAT010, NEAT031)

`neat::scan_at` builds the Rust file's universal term (`gob_symbols::model_of_source_at`, path
`neat.rs`) and collects the byte spans of `unit(function|method)` and `anon(function)` nodes
through the shared `fn_spans` helper (also used by testq). A tree-sitter `function_item` is a
unit only when a model span ends where it ends and starts at or before it. `frob:` claim
comments, the callee vocabulary, `effects(unit)`, the dispatcher test and the condition weighing
stay on tree-sitter. Languages other than Rust have no detectors and build no model.

Missing universal-model queries (reported, not invented), continuing section 3:

23. (neat) Comments and doc comments attached to a unit as typed accessors, to read `frob:`
    claims without scanning sibling nodes.
24. (neat) A unit's parameter list (names, patterns, mutability) as typed accessors, for the
    dispatcher test.
25. (neat) A match/branch node over a named parameter, with its scrutinee expression, for
    NEAT031's dispatcher detection.
26. (neat) Branch-condition expression nodes with call, closure and identifier-reference counts,
    plus local `let` initializers (def-use), for the NEAT031 condition weight.
27. (neat) A within-file call-graph query resolving a callee to its unit, for the transitive
    `effects(unit)` closure of NEAT010.

## 3. U queries the rest of PAIR001 and its siblings still need

Reported, not invented. Until these exist the judgement stays on tree-sitter:

1. Return statements of a function body (and the returned expression), including ternary structure.
2. The `async` flag of a function (an `async` effect callback never returns a cleanup).
3. The result name an acquire is bound to (`const id = setInterval(..)`), i.e. a def-use of the handle.
4. Argument text of a call, to compare handler and receiver identity between acquire and release.
5. A `teardown_roots` capability (lint-requirements.md R40): which functions are teardown scope for a class or component.
6. Callee vocabulary per language for PAIR001 (R40), as data rather than code.
7. (err) Handler catch-all type and header, and whether a handler body is empty or rethrows/logs.
8. (err) A function's name and declared return type (the `Result` check parses signature text).
9. (err) The callee of a macro invocation (`Phase` carries only text such as `callee()`).
10. (res) The binding a value flows into as a query: today it is rebuilt from adapter node
    names (`variable_declarator`, `assignment_expression`, field definitions) and from the
    `unit(const)` fold of a top-level `const`, which differ in shape from the in-function form.
11. (res) A parent / enclosing-scope accessor on `Term`; the scan builds its own parent map.
12. (res) The arguments and receiver of a call as typed accessors rather than positional children.
13. (path) A string literal as one node kind with a decoded value: today the shape varies per
    adapter (Rust adapter nodes over `string_content`, Python `string` lit or adapter node, TS
    `str` lit with the quotes in the span, TS template as `op`, C# per-kind lits).
14. (path) Def-use by name and the callee/arguments of a call, for the PATH002/PATH003 taint flow
    over path-conversion roles (`to_str`, `display`, `os.fspath`, ...).
15. (path) A test-context accessor (a `#[test]` / `#[cfg(test)]` item, a `test_` function).
16. (time) Def-use by name (the last assignment to a binding in a scope) and typed call
    accessors (callee path with import aliases resolved, positional and keyword arguments), for
    the datetime naive/aware classification.
17. (time) Binary and comparison operators as one node kind with operator and operands as typed
    accessors, for the TIME002 mix check.
18. (time) Import resolution (`from m import n as a`, `use p as a`) as a query on the term.

## 4. Follow-ups

Remaining families are split into child tickets of 01M6SJHBH2JK72HAE60AFYDFWX, one per family
(err, res, path, time, testq, neat, unity), each scoped to crates/grimble-lints/src/**.
