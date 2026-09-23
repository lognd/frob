# frob.webapp -- WEBSEC401 authz route/handler substrate (T-5356)

One sentence: `scan_python_handlers`/`scan_rails_controller` walk
Flask/FastAPI/Django route handlers and Rails controller actions for an
ORM lookup/filter call that is never correlated, anywhere in the same
handler body, with the authenticated user's own identity -- a documented
heuristic, not a sound analysis (same posture as PERF008's loop-
invariant-effect heuristic, `src/frob/perf/_cache_effects.py`).

## Why this module takes a parsed `Node`, not a `Path`

`[arch.layering]` (`frob.toml`) makes `webapp` a leaf layer with no
allowed imports of its own (the same table T-5302 left `_detect.py` in,
and T-5313's `_a11y_substrate.py` documents identically) -- this module
never imports `frob.lang` or `frob.gates` itself. The eventual
`WEBSEC401` gate rule (a later leaf under `frob.gates`, which IS allowed
to import both `lang` and `webapp`) calls `frob.lang.raw_tree` itself and
hands this module the resulting `tree_sitter.Node` root plus the parsed
`language` label (`scan_python_handlers`) or the raw source TEXT
(`scan_rails_controller`, Rails has no tree-sitter grammar in this repo
at all). This module only ever walks what it is given, and returns its
own `AuthzFinding` model -- the `Violation`/`rule`/`severity` wrapping is
that later gate leaf's job, not this one's.

## scan_python_handlers

`scan_python_handlers(path: str, root: Node, source: bytes, language:
str) -> Result[tuple[AuthzFinding, ...], AuthzSubstrateError]`
(`src/frob/webapp/_websec_authz_substrate.py`) walks an already-parsed
python tree and flags every route/view handler whose body reaches an ORM
lookup/filter call with no auth-identifier token anywhere in that body.
`Err(UnsupportedLanguage)` for any `language` other than `"python"`.

### Detection shape

- **Handler candidacy**: a python `function_definition` counts as a
  handler if it carries a route-shaped decorator (`@app.route(...)`,
  `@app.get/post/put/patch/delete(...)`, `@bp....`, `@router....`) OR its
  first parameter is named `request` (`self, request` for a Django class-
  based view, or bare `request` for a function-based one). This keeps the
  rule off ordinary helper functions the walker would otherwise flag by
  accident.
- **Owner correlation**: within that handler's body (its leading
  docstring statement, if any, excluded -- prose mentioning the auth
  vocabulary must not silently suppress a real finding), an ORM
  lookup/filter call (`.get(`, `.filter(`, `.filter_by(`, `.where(`,
  `.find(`, `.find_by(`, `get_object_or_404(`) reached while the auth-
  identifier vocabulary (`current_user`, `request.user`, `g.user`,
  `AUTH_IDENTIFIER_NAMES`) is ABSENT anywhere in that body is a finding.
  The heuristic does not attempt to prove the auth identifier is actually
  threaded INTO the lookup call's arguments -- presence anywhere in the
  body is enough, matching PERF017/018's own "textual, best-effort,
  over-recall by design" posture. A handler whose owner check lives
  behind a decorator or a base-class hook the walker cannot see will
  false-positive; the remedy is a reasoned `frob:waive WEBSEC401
  reason="..."`, not a smarter parser.

## scan_rails_controller

`scan_rails_controller(path: str, text: str) -> tuple[AuthzFinding,
...]` -- no tree-sitter grammar covers `.rb` in this repo (`frob.lang`'s
extension table, T-0077), so Rails controller actions (`class
FooController < ApplicationController` ... `def <action>`) are matched
with a text-regex split on `def`/next-`def` boundaries instead of a real
parse -- the same "text rule over a file a real grammar cannot reach"
posture T-5307's Jinja/ERB sink rules already use. `()` for any file
whose text does not match a `...Controller` class declaration at all.

## Known scope boundary: Express

T-5356's ticket body names Express alongside Flask/FastAPI/Django/Rails,
but `frob.webapp._detect.FrameworkKind` (T-5302) has no `EXPRESS` member
(`nextjs/vite/django/flask/fastapi/rails/laravel/sveltekit/astro` only) --
adding one is a `frob.webapp._detect` change outside this ticket's
declared scope (`src/frob/webapp/_websec_authz_substrate.py`,
`tests/fixtures/webapp/websec4xx/**`), not something this leaf widens
into silently. See T-5356's done-report for the filed follow-up.

## Fixtures

`tests/fixtures/webapp/websec4xx/<framework>/` (flask, fastapi, django,
rails) each hold one clean handler/action (owner filter present) and one
planted-finding handler/action (owner filter absent) --
`tests/unit/test_webapp_websec_authz_substrate.py` exercises both the
positive and negative control per framework, driving each entry point
directly with a caller-parsed tree/text the same way the eventual
`frob.gates` rule module will.
