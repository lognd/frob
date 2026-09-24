# frob.webapp._websec_xss -- WEBSEC107-108 output-encoding/template-sink refinements

One sentence: `frob.webapp._websec_xss.websec_xss_findings` claims the two
reserved rule ids (T-5301) directly above the T-5307 substrate's
WEBSEC101-106 block, covering two sink shapes that substrate's own six
finders leave out (ASVS 5.0 V1.1.2/V1.2.1, CWE-79), folded into
`frob.gates._taint_gate.taint_gate`'s own scan alongside
`frob.webapp._websec_sinks.websec_sink_findings` rather than a second
gate registration.

This is a leaf of the T-5140 web-app-lint epic's WEBSEC injection/
output-encoding story (T-5141), landing after T-5307's substrate. See
docs/modules/webapp-websec-injection.md for WEBSEC101-106.

## Why these two ids do not duplicate WEBSEC101-106

`frob.webapp._websec_sinks` already owns Rails' `.html_safe`/`raw(...)`
regex pair as WEBSEC106. WEBSEC107 here is a DIFFERENT Rails ERB shape --
the explicit unescaped-output tag `<%== expr %>` (as opposed to the
ordinary, auto-escaping `<%= expr %>` tag) -- never matched by the
WEBSEC106 regex pair, so this is a genuinely new finder rather than a
second finder re-emitting an already-claimed id. WEBSEC108 covers PHP
`echo`/`print`/short-echo (`<?= ... ?>`) of a raw superglobal, a language
T-5307's substrate never reads at all (`.php` is not in its tracked-file
suffix list).

## Framework gating

`websec_xss_findings(root)` calls `frob.webapp._detect.detect_frameworks`
first and returns `()` immediately for a repo with no detected web
framework -- the same short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF
family uses (T-5302). This module never re-implements framework sniffing.

## Rule catalog

| rule | sink | source language | detection |
| --- | --- | --- | --- |
| WEBSEC107 | `<%== expr %>` (Rails' explicit unescaped-output ERB tag) | Ruby/ERB | text-regex |
| WEBSEC108 | `echo`/`print`/`<?= ... ?>` of `$_GET`/`$_POST`/`$_REQUEST`/`$_COOKIE`/`$_SERVER`/`$_FILES` with no `htmlspecialchars(...)` wrap | PHP | text-regex |

Each fires only when the flagged value is NOT a plain string literal and
does NOT already pass through a recognized sanitizer-shaped call name
(`DOMPurify`, `sanitize`, `escape`, `htmlspecialchars`, `clean` --
case-insensitive substring match, the same textual-proxy posture
`frob.webapp._websec_sinks._is_sanitized` documents). This is
intra-statement flow, not resolved data-flow: a sanitizer call two
statements earlier is not seen, the same disclosed gap SEC005 (T-0781)
and WEBSEC101-106 already carry.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`opaque_gate`/`websec_sink_findings` already follow for a
brand-new structural rule: a real fix-or-waive pass over the first
measured hit set decides whether ERROR is safe later.

## Public API

- `WebsecXssFinding` (`src/frob/webapp/_websec_xss.py`) -- one finding:
  `rule`, `file`, `line`, `message`.
- `websec_xss_findings(root: Path) -> tuple[WebsecXssFinding, ...]` --
  every WEBSEC107-108 finding under `root`.

- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[Violation, ...]` -- the discovery-hook entry point (T-5311's
  discovery convention: `frob.gates._taint_gate.taint_gate` detects
  frameworks ONCE and calls this exact module-level name/signature on
  every `frob.webapp._websec_*` module that exposes it, instead of each
  module re-running `detect_frameworks` and each family needing its own
  gate-wiring edit). Returns `()` immediately for an empty `frameworks`.

`frob.gates._taint_gate.taint_gate` discovers and calls `websec_findings`
alongside `websec_sink_findings`/`websec_bounds_findings` and its own
SEC005 scan, folding all result sets into the same `Violation` tuple it
returns -- there is no separate `websec_xss_gate` process job.

## Tests and fixtures

`tests/unit/test_websec_xss.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec1xx/xss/webesc10{7,8}_{positive,negative}/`,
each carrying a minimal framework marker (`Gemfile` naming `rails` for
WEBSEC107, `composer.json` naming `laravel/framework` for WEBSEC108, so
`detect_frameworks` fires) plus exactly one sink occurrence. Positive
fixtures plant a non-literal, unsanitized value; negative fixtures use
the identical sink shape with either a literal or a sanitizer-wrapped
value, to prove the rule does not fire on the clean case.

## Scope note: fixture directory split from WEBSEC101-106

T-5306's declared scope is narrowed to
`tests/fixtures/webapp/websec1xx/xss/**` (a subdirectory of the shared
`tests/fixtures/webapp/websec1xx/` root T-5307 and its sibling leaves
also touch) so this ticket's fixture leases stay disjoint from the other
concurrent WEBSEC1xx leaves' own fixture subdirectories.

frob:ticket T-5306
