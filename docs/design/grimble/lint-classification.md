# Design lint classification: portable vs language-specific

Ticket 01M6SJHBH2JK72HAE60AFYDFWX. Governing text: docs/design/shared/universal-model.md
section 5 (queries Q01-Q47) and notes/research/lint-requirements.md.

Rule of thumb: a lint is **portable** when everything it asks of the code is a U query
(calls, bindings, flow, effects, comments). It is written once against `gob-ir` through a
`gob-symbols` adapter and must run on every adapter language. A lint is **language-specific**
only where U has no query and the idiom is tied to one engine or language.

## 1. Classification

| Lint | Family | Class | Reads today | Migration status |
|------|--------|-------|-------------|------------------|
| ERR001 empty-error-handler | err | portable | per-language tree-sitter queries (`err.rs`) | pending (follow-up) |
| ERR002 discarded-result | err | portable | per-language tree-sitter queries | pending (follow-up) |
| ERR003 silent-catch-all | err | portable | per-language tree-sitter queries | pending (follow-up) |
| PAIR001 acquire-without-release, React/effect vocabulary | effect | portable | U `apply` nodes for discovery; tree-sitter for return/async/def-use | **partly migrated (this slice)** |
| PAIR001, Unity lifecycle vocabulary | unity | language-specific (vocabulary) over a portable shape | tree-sitter C# | pending; shape portable, vocabulary per language |
| RES001 unpaired-resource-acquisition | res | portable | tree-sitter (`res.rs`) | pending (follow-up) |
| PATH001 absolute-host-path | path | portable | string literals (`path/literal.rs`) | pending (follow-up) |
| PATH002 string-path-separator | path | portable | path-conversion roles, flow (`path/flow.rs`) | pending (follow-up) |
| PATH003 path-in-command-line | path | portable | path-conversion roles, flow | pending (follow-up) |
| TIME001 local-clock-read | time | portable | clock roles, flow (`time/flow.rs`) | pending (follow-up) |
| TIME002 naive-aware-mix | time | portable | clock roles, flow | pending (follow-up) |
| TESTQ001-003 (no assertion, nondeterminism, control flow) | testq | portable | per-language test vocabulary | pending (follow-up) |
| NEAT010 effect ceiling | neat | portable | `effects(unit)` already answered as `gob_ir::Answer`; unit extraction is Rust tree-sitter | pending (follow-up) |
| NEAT031 dispatch-site-owns-logic | neat | portable | Rust tree-sitter (`neat/dispatcher.rs`) | pending (follow-up) |
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

## 3. U queries the rest of PAIR001 and its siblings still need

Reported, not invented. Until these exist the judgement stays on tree-sitter:

1. Return statements of a function body (and the returned expression), including ternary structure.
2. The `async` flag of a function (an `async` effect callback never returns a cleanup).
3. The result name an acquire is bound to (`const id = setInterval(..)`), i.e. a def-use of the handle.
4. Argument text of a call, to compare handler and receiver identity between acquire and release.
5. A `teardown_roots` capability (lint-requirements.md R40): which functions are teardown scope for a class or component.
6. Callee vocabulary per language for PAIR001 (R40), as data rather than code.

## 4. Follow-ups

Remaining families are split into child tickets of 01M6SJHBH2JK72HAE60AFYDFWX, one per family
(err, res, path, time, testq, neat, unity), each scoped to crates/grimble-lints/src/**.
