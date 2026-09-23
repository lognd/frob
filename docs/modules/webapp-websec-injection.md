# frob.webapp._websec_sinks -- WEBSEC101-106 injection/output-encoding sinks

One sentence: `frob.webapp._websec_sinks.websec_sink_findings` extends the
SEC005 taint substrate (`frob.vet._taint`, `frob.gates._taint_gate`) with a
second, framework-scoped source/sink family covering the classic DOM/
template XSS sinks the T-5141 corpus names (ASVS 5.0 V1.1.2/V1.2.1,
CWE-79), folded into `frob.gates._taint_gate.taint_gate`'s own scan rather
than a second gate registration.

This is one of seven sibling web-app-lint story leaves under the T-5140
epic (docs/modules/webapp.md's own scope: framework detection only, not
any individual rule family). A follow-up ticket links all seven family
docs (this one, plus session/CSRF, response headers, authz, COMPLY,
A11Y, SEO/WEBPERF) from webapp.md once all seven land.

## Framework gating

`websec_sink_findings(root)` calls `frob.webapp._detect.detect_frameworks`
first and returns `()` immediately for a repo with no detected web
framework -- the same short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF
family uses (T-5302). This module never re-implements framework sniffing.

## Rule catalog

| rule | sink | source language | detection |
| --- | --- | --- | --- |
| WEBSEC101 | `.innerHTML`/`.outerHTML` assignment, `document.write(...)`, `.insertAdjacentHTML(...)` | JS/TS/JSX/TSX | tree-sitter AST via `frob.lang.raw_tree` |
| WEBSEC102 | `dangerouslySetInnerHTML={{__html: X}}` | JSX/TSX | tree-sitter AST via `frob.lang.raw_tree` |
| WEBSEC103 | `v-html="expr"` inside a `.vue` SFC `<template>` block | Vue SFC | text-regex over the `template_element` raw subtree span (T-5300's `_walk_vue.py` names this exact detector as its own future `raw_tree` consumer) |
| WEBSEC104 | `{{ x\|safe }}`, or `autoescape=False` in Python source | Jinja2 template / Python | text-regex (no tree-sitter grammar for Jinja's autoescape config) |
| WEBSEC105 | `django.utils.safestring.mark_safe(x)`, or `{% autoescape off %}` | Python / Django template | text-regex |
| WEBSEC106 | `.html_safe`, `raw(...)` | Ruby/ERB | text-regex |

Each fires only when the flagged value is NOT a plain string literal and
does NOT already pass through a recognized sanitizer-shaped call name
(`DOMPurify`, `sanitize`, `escape`, `htmlspecialchars`, `clean` --
case-insensitive substring match, the same textual-proxy posture
`frob.vet._taint._looks_like_repo_state_read` documents for SEC005's own
validator check). This is intra-statement flow, not resolved data-flow: a
sanitizer call two statements earlier is not seen, the same disclosed gap
SEC005 (T-0781) already carries.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate` already follow for a brand-new structural rule:
a real fix-or-waive pass over the first measured hit set decides whether
ERROR is safe later.

## Public API

- `WebsecSinkFinding` (`src/frob/webapp/_websec_sinks.py`) -- one finding:
  `rule`, `file`, `line`, `message`.
- `websec_sink_findings(root: Path) -> tuple[WebsecSinkFinding, ...]` --
  every WEBSEC101-106 finding under `root`.

`frob.gates._taint_gate.taint_gate` calls `websec_sink_findings` alongside
its own SEC005 scan and folds the results into the same `Violation` tuple
it returns -- there is no separate `websec_gate` process job.

## Tests and fixtures

`tests/unit/test_websec_sinks.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec1xx/webesc10{1..6}_{positive,negative}/`,
each carrying a minimal framework marker (so `detect_frameworks` fires)
plus exactly one sink occurrence. Positive fixtures plant a non-literal,
unsanitized value; negative fixtures use the identical sink shape with
either a literal or a sanitizer-wrapped value, to prove the rule does not
fire on the clean case.

frob:ticket T-5307
