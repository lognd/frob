# frob.webapp._websec_session_config -- WEBSEC session/CSRF SessionConfig reader

One sentence: every WEBSEC session/CSRF rule (cookie `secure`/`httponly`/
`samesite`, idle/absolute session timeout, CSRF middleware presence)
reads one normalized `SessionConfig` from `read_session_config` instead
of re-parsing Django/Flask/Express/Rails' own session-config file itself
(T-5349).

This module builds on `frob.webapp._detect`'s `FrameworkKind`/
`detect_frameworks` (T-5302, `docs/modules/webapp.md`) -- it never
re-detects a framework, it only reads config for a `FrameworkKind` a
caller already has in hand.

## SessionConfigError

`SessionConfigError(ErrorSet)` (`src/frob/webapp/_websec_session_config.py`)
-- the typani `Result` error channel every fallible operation in this
module returns instead of raising:

- `ConfigFileNotFound` -- no recognized session-config file exists under
  `root` for the requested framework.
- `ParseFailed` -- tree-sitter could not produce a usable tree for the
  config file that was found.
- `UnsupportedFramework` -- the requested `FrameworkKind` has no reader
  registered (`FASTAPI`, `LARAVEL`, `SVELTEKIT`, `ASTRO`, `NEXTJS`: none
  of these has one canonical session-config file this reader can locate
  the way Django/Flask/Rails' can).

## SessionConfig

`SessionConfig(BaseModel)` -- the one normalized shape every WEBSEC
session/CSRF rule reads:

- `framework: FrameworkKind` -- which reader produced this config.
- `source_path: Path` -- the config file that was actually parsed.
- `secure: bool | None`, `httponly: bool | None`, `samesite: str | None`
  -- the session cookie's security flags, `None` when the config file
  never states them (not collapsed into a guessed default -- a rule
  reading `secure is not True` needs to tell "explicitly insecure" apart
  from "the framework's own default applies", and both apart from "not
  present").
- `csrf_middleware_present: bool` -- whether CSRF protection is wired
  (Django `CsrfViewMiddleware` in `MIDDLEWARE`, Flask `CSRFProtect(...)`,
  Express `csurf()`/`csrf()` via `app.use(...)`, Rails
  `protect_from_forgery` in the controller). Defaults `False` (absence is
  not assumed compliant).
- `idle_timeout: int | None`, `absolute_timeout: int | None` -- session
  lifetime in seconds (framework-native units; `maxAge` from Express is
  milliseconds, passed through unconverted since every field here is
  "whatever unit the framework's own config used" rather than a
  normalized time unit -- callers doing cross-framework timeout
  comparisons must know this).

## read_session_config

`read_session_config(root: Path, framework: FrameworkKind) ->
Result[SessionConfig, SessionConfigError]` (`src/frob/webapp/
_websec_session_config.py`) is the one entry point. Per-framework config
file located and parsed:

- `FrameworkKind.DJANGO` -- `settings.py` at `root` or one level under a
  project package directory (`*/settings.py`). Module-level
  `SESSION_COOKIE_SECURE`/`SESSION_COOKIE_HTTPONLY`/
  `SESSION_COOKIE_SAMESITE`/`SESSION_COOKIE_AGE` assignments plus a
  `CsrfViewMiddleware` substring check against the `MIDDLEWARE` list's
  own source text.
- `FrameworkKind.FLASK` -- `app.py` or `wsgi.py` at `root`.
  `app.config['SESSION_COOKIE_*']` subscript assignments plus a
  `CSRFProtect(...)` call anywhere in the module, and
  `PERMANENT_SESSION_LIFETIME` for `idle_timeout`.
- `FrameworkKind.VITE` (Express has no dedicated `FrameworkKind` member;
  T-5302 detects a bare Node server tree as `VITE`) -- `app.js`,
  `server.js`, or `index.js` at `root`. The `app.use(session({...}))`
  call's `cookie` object (`secure`/`httpOnly`/`sameSite`/`maxAge`) plus a
  `csurf()`/`csrf()` call anywhere in the module.
- `FrameworkKind.RAILS` -- `config/initializers/session_store.rb`'s
  `session_store` keyword arguments (`secure`/`httponly`/`same_site`/
  `expire_after`) plus a `protect_from_forgery` call in
  `app/controllers/application_controller.rb`, if that file exists.
- Any other `FrameworkKind` -- `Err(SessionConfigError.UnsupportedFramework)`.

Django/Flask/Express parse through `frob.lang.raw_tree` (T-5302's stated
tree-sitter escape hatch, the same single `get_parser` chokepoint every
other `frob.lang` walker uses -- `docs/modules/lang.md`). Rails' `.rb`
files have no `frob.lang` grammar entry, so parsing them goes through
`tree_sitter_language_pack.get_parser("ruby")` directly, scoped to this
module rather than widening `frob.lang`'s own extension table for a
single consumer.

## Fixtures

`tests/fixtures/webapp/websec2xx/` holds one compliant/violating pair per
framework: `django_compliant`/`django_violating`, `flask_compliant`/
`flask_violating`, `express_compliant`/`express_violating`,
`rails_compliant`/`rails_violating`. Each compliant fixture sets
`secure`/`httponly` true, a `samesite` value, and wires CSRF middleware;
each violating fixture sets them false (or omits `samesite`) and wires no
CSRF middleware -- the positive/negative control pair `tests/unit/
test_webapp_websec_session_config.py` asserts against.
