# frob.webapp._websec_bounds -- WEBSEC123-125 resource-exhaustion input-bounds

One sentence: `frob.webapp._websec_bounds.websec_bounds_findings` covers
the T-5141 corpus's resource-exhaustion input-bounds family (unbounded
input length, XML/JSON bomb, unbounded recursion), folded into
`frob.gates._taint_gate.taint_gate`'s own scan alongside T-5307's
`websec_sink_findings` rather than a second gate registration.

This is one of seven sibling web-app-lint story leaves under the T-5140
epic (docs/modules/webapp.md's own scope: framework detection only, not
any individual rule family). A follow-up ticket links all seven family
docs (this one, plus injection/output-encoding, session/CSRF, response
headers, authz, COMPLY, A11Y, SEO/WEBPERF) from webapp.md once all seven
land.

## Framework gating

`websec_bounds_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## Rule catalog

| rule | shape | source language | detection |
| --- | --- | --- | --- |
| WEBSEC123 | a `str`/`list[...]` schema field with no length bound | Python (pydantic `Field`/`constr`/`conlist`), TS/JS (Zod `z.string()`/`z.array(...)`, class-validator `@IsString()`/`@IsArray()`) | Python: stdlib `ast` walk over `BaseModel` subclasses. TS/JS: text-regex over the chained/decorator call shape. |
| WEBSEC124 | a resource-exhaustion parser/body config: an XML parser with no `resolve_entities=False`/`defusedxml`, or a JSON body-parser call with no size `limit` | Python (`xml.etree.ElementTree`/`lxml.etree`/`xml.sax`), TS/JS (Express `bodyParser.json(...)`/`express.json(...)`) | text-regex (no tree-sitter grammar frob has for these parser-config call shapes) |
| WEBSEC125 | a recursive function with no depth/count/limit guard anywhere in its body | Python, TS/JS | Python: stdlib `ast` walk detecting a self-call plus a guard-comparison regex over the unparsed body. TS/JS: named-function-declaration self-call plus the same guard-comparison regex over the brace-matched body. |

Each fires only on a bound-bearing shape (a `Field`/`constr`/`conlist`
call, a Zod chain, a class-validator decorator, an XML parser call, a
body-parser call, or a self-recursive function) -- this is intra-
statement/intra-function text and structure, not resolved cross-file
data-flow, the same disclosed gap SEC005 (T-0781) and WEBSEC101-106
(T-5307) already carry.

## Item 28 (business-logic step-skipping)

The T-5141 corpus's item 28 (a multi-step business-logic flow reachable
out of order, e.g. skipping a payment-authorization step in a checkout
flow) is DYNAMIC-only: no static AST/regex shape distinguishes a
correctly-ordered multi-step handler from one that can be driven out of
order. It is NOT a rule this module ships -- see
`tests/unit/test_websec_bounds.py`'s trailing `frob:todo T-5311` comment
for the exact obligation this leaf's Done report files instead.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/`websec_sink_findings` already follow for a
brand-new structural rule: a real fix-or-waive pass over the first
measured hit set decides whether ERROR is safe later.

## Public API

- `WebsecBoundsFinding` (`src/frob/webapp/_websec_bounds.py`) -- one
  finding: `rule`, `file`, `line`, `message`.
- `websec_bounds_findings(root: Path) -> tuple[WebsecBoundsFinding, ...]`
  -- every WEBSEC123-125 finding under `root`.

`frob.gates._taint_gate.taint_gate` calls `websec_bounds_findings`
alongside its SEC005 and WEBSEC101-106 scans and folds the results into
the same `Violation` tuple it returns -- there is no separate
`websec_bounds_gate` process job.

## Tests and fixtures

`tests/unit/test_websec_bounds.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec1xx/bounds/webesc12{3..5}_{positive,negative}/`,
each carrying a `requirements.txt` framework marker (`fastapi`, so
`detect_frameworks` fires) plus exactly one bound-bearing occurrence.
Positive fixtures plant the unbounded shape; negative fixtures use the
identical shape with the bound/guard present, to prove the rule does not
fire on the clean case.

frob:ticket T-5311
