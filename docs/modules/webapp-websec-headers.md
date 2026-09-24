<!-- frob:waive REF002 reason="a new T-5325 leaf doc anchored from src/frob/webapp/_websec_headers.py's frob:doc directives by design -- a second consumer would not be genuine yet; T-5326 (blocked_by=['T-5325']) is the sibling ticket that will add a second anchor once it wires the gate rule ids, same posture as ci_report.md/ghio.md's identical single-anchor waivers" -->

# frob.webapp._websec_headers -- WEBSEC response-header lint engine

One sentence: `lint_response_headers` answers, for each of
`REQUIRED_HEADERS`, whether a repo's in-repo evidence sets it, is
missing it from a recognized security surface, or has no in-repo
evidence at all -- the last case a WARN advisory rather than a false
ERROR, since the header may still be set at the CDN/edge layer
(Cloudflare, Fastly dashboards, ...) outside the repo entirely (owner
directive, T-5325).

## Required headers

`REQUIRED_HEADERS: tuple[str, ...]` (`src/frob/webapp/_websec_headers.py`):
`Strict-Transport-Security`, `X-Content-Type-Options`,
`X-Frame-Options`, `Content-Security-Policy`, `Referrer-Policy`.

## Public API

### lint_response_headers

`lint_response_headers(root: Path) -> Result[tuple[HeaderFinding, ...], WebsecHeadersError]`

Combines two kinds of evidence, both plain-text line scans (not a
`frob.lang`/tree-sitter walk -- `frob.lang`'s identifier walker has no
javascript/typescript entry yet, so a uniform scan idiom is used
instead of mixing a real AST walk for Python with a text scan for JS):

- **(a) app-code lint** -- every `settings.py` under a repo
  `detect_frameworks` reports as Django, matched against the
  `SECURE_HSTS_SECONDS` / `SECURE_CONTENT_TYPE_NOSNIFF` /
  `X_FRAME_OPTIONS` / `CSP_DEFAULT_SRC` / `SECURE_REFERRER_POLICY`
  settings; and every `.js`/`.jsx`/`.ts`/`.tsx` file, matched against a
  `helmet(` call-site (the Express `helmet()` middleware call), which
  sets helmet's own default header set (HSTS, X-Content-Type-Options,
  X-Frame-Options, Referrer-Policy -- CSP is opt-in and not guessed at).
  Does not re-detect frameworks itself; the Django settings scan is
  gated purely on `detect_frameworks`'s own result.
- **(b) config-file line parser** -- every `nginx.conf`
  (`add_header <Name> ...;` directives) and `Caddyfile`
  (`header <Name> "<value>"`, both the single-line form and each line
  inside a `header { ... }` block) found under the repo root.

For each required header: evidence found -> PRESENT (with the
`HeaderSourceKind`/path/line it came from). No evidence for that header,
but SOME recognized security surface exists in the repo (an nginx.conf,
Caddyfile, Django settings.py under a detected Django project, or a
`helmet()` call) -> MISSING, an actionable ERROR-grade finding. No
recognized security surface exists in the repo at ALL -> **(c) ADVISORY**,
the documented CDN/edge-layer gap: a plain repo terminating TLS at a
managed edge (Cloudflare, Fastly, ...) with headers configured entirely
in that dashboard has no in-repo evidence to find, and reporting that as
an ERROR would be a false positive against a legitimately-configured
deployment; `HeaderFinding.message` says to confirm at the edge instead.

`Err(WebsecHeadersError.ROOT_NOT_A_DIRECTORY)` if `root` is not an
existing directory.

### HeaderSourceKind

`StrEnum`: `app_django`, `app_helmet`, `app_manual` (reserved for a
future manual `response.headers[...] =` assignment lint), `nginx`,
`caddy`.

### HeaderStatus

`StrEnum`: `present`, `missing`, `advisory` -- see `lint_response_headers`
above for the exact decision rule between the three.

### HeaderFinding

Pydantic model: `header: str`, `status: HeaderStatus`,
`source: HeaderSourceKind | None`, `path: Path | None`,
`line: int | None`, `message: str`. `source`/`path`/`line` are `None`
for an ADVISORY finding, which by definition has no in-repo evidence.

### WebsecHeadersError

`StrEnum`: `root_not_a_directory` -- the fallible-operation error
`lint_response_headers` returns when `root` is missing or not a directory.

## Fixtures

`tests/fixtures/webapp/websec3xx/` (one directory per case, positive
and negative controls per source):

- `nginx_full` / `nginx_missing_csp` -- nginx `add_header` evidence,
  full set vs. one header dropped.
- `caddy_full` / `caddy_missing_hsts` -- Caddyfile `header { }` block
  evidence, full set vs. one header dropped.
- `django_full` / `django_missing_xfo` -- a detected Django project
  (`manage.py` + `requirements.txt` per `frob.webapp._detect`'s own
  markers) with a `settings.py` setting the full mapping vs. one
  setting dropped.
- `express_helmet` -- a bare `helmet()` call; asserts helmet's default
  four headers PRESENT and CSP (not in the default set) ADVISORY.
- `no_evidence` -- a plain Python CLI fixture with no security surface
  at all; every header reports ADVISORY, none MISSING.

## Relationship to sibling WEBSEC substrates

This module implements the response-header engine; it does not
wire a gate rule id (`WEBSEC101`-family ids remain reserved,
`docs/design/registry/check-coverage.yaml`, T-5301/T-5140 epic) or
register in `docs/modules/webapp.md`, which a follow-up ticket links
out to this doc and its six WEBSEC-family siblings from (T-5302's
fan-out, `SUBSTRATE-FANOUT.md`).
