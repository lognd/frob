# frob.webapp._websec_deser -- WEBSEC109-116 code-injection/deserialization sinks

One sentence: `frob.webapp._websec_deser.websec_deser_findings` extends the
SEC005 taint substrate (`frob.vet._taint`, `frob.gates._taint_gate`) with a
third, framework-scoped source/sink family covering code-injection and
unsafe-deserialization sinks (ASVS 5.0 V5.2/V5.3/V5.5, CWE-78/90/95/502/
943/1336), discovered and folded into `frob.gates._taint_gate.taint_gate`'s
own scan via the module-level `websec_findings(root, frameworks)` hook
(T-5311) rather than a hand-edit of the shared gate module or a second
gate registration -- avoiding a lease collision across the sibling WEBSEC
injection tickets that land around the same time.

This is one of seven sibling web-app-lint story leaves under the T-5140
epic (docs/modules/webapp.md's own scope: framework detection only, not
any individual rule family). A follow-up ticket links all seven family
docs from webapp.md once all seven land.

## Framework gating

`websec_deser_findings(root)` calls `frob.webapp._detect.detect_frameworks`
first and returns `()` immediately for a repo with no detected web
framework -- the same short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF
family uses (T-5302). This module never re-implements framework sniffing.

## Rule catalog

| rule | sink | source language | detection |
| --- | --- | --- | --- |
| WEBSEC109 | `render_template_string(x)` / `Template(x).render(...)` | Python | AST |
| WEBSEC110 | `eval(x)` / `exec(x)` | Python | AST |
| WEBSEC110 | `new Function(...)` | JS/TS | text-regex |
| WEBSEC111 | `yaml.load(x)` with no `Loader=yaml.SafeLoader` | Python | AST |
| WEBSEC112 | `pickle.load(...)` / `pickle.loads(x)` on a non-literal `x` | Python | AST |
| WEBSEC113 | `subprocess.*(..., shell=True)` / `os.system(x)` | Python | AST |
| WEBSEC114 | LDAP search filter built by string concatenation/interpolation | Python | AST |
| WEBSEC115 | PyMongo query method called with a raw request-JSON filter | Python | AST |
| WEBSEC116 | LaTeX compiler invocation (`pdflatex`/`xelatex`/`lualatex`) with `--shell-escape` | build script | text-regex |

Each fires only when the flagged value is NOT a plain string literal and
does NOT already pass through a recognized sanitizer/validator-shaped
call name (`sanitize`, `escape`, `validate`, `quote`, `confine`,
`assert_safe` -- case-insensitive substring match, the same
textual-proxy posture `frob.vet._taint._looks_like_repo_state_read` and
`frob.webapp._websec_sinks._SANITIZER_NAME_RE` already document). This is
intra-statement flow, not resolved data-flow: a sanitizer call two
statements earlier is not seen, the same disclosed gap SEC005 (T-0781)
already carries. WEBSEC112 (pickle) and WEBSEC116 (LaTeX --shell-escape)
fire on the sink shape itself (any non-literal `pickle.load(s)` call; any
`--shell-escape` passed to a LaTeX compiler invocation) since both are
inherently dangerous regardless of an apparent sanitizer name nearby.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/`websec_sink_findings` already follow for a brand-new
structural rule: a real fix-or-waive pass over the first measured hit set
decides whether ERROR is safe later.

## Public API

- `WebsecDeserFinding` (`src/frob/webapp/_websec_deser.py`) -- one finding:
  `rule`, `file`, `line`, `message`.
- `websec_deser_findings(root: Path) -> tuple[WebsecDeserFinding, ...]` --
  every WEBSEC109-116 finding under `root`, self-gated by its own
  `detect_frameworks(root)` call.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[Violation, ...]` (T-5311's gate-discovery hook contract) -- the
  same findings as `Violation`s, gated by the CALLER-supplied
  `frameworks` instead of a fresh `detect_frameworks` call.
  `frob.gates._taint_gate.taint_gate` discovers this exact module-level
  name/signature on every `frob.webapp._websec_*` module (T-5307's
  `_websec_sinks` included) and folds each one's result into the same
  `Violation` tuple it returns -- there is no separate `websec_deser_gate`
  process job, and no leaf hand-edits `_taint_gate.py` itself.

## Tests and fixtures

`tests/unit/test_websec_deser.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec1xx/deser/webesc1{09..16}_{positive,negative}/`,
each carrying a Flask marker (`requirements.txt` naming `flask`, so
`detect_frameworks` fires) plus exactly one sink occurrence. Positive
fixtures plant a non-literal, unsanitized value; negative fixtures use the
identical sink shape with either a literal or a sanitizer-wrapped value
(or, for WEBSEC111, an explicit `Loader=yaml.SafeLoader`), to prove the
rule does not fire on the clean case.

frob:ticket T-5309
