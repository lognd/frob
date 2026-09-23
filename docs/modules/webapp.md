# frob.webapp / frob.sql -- web-framework detection scaffolding

One sentence: before any WEBSEC/COMPLY/A11Y/SEO/WEBPERF rule (T-5301's
reserved rule ids) runs a single tree-sitter walk, it asks `frob.webapp.
detect_frameworks` one question -- "does this repo look like a web app at
all?" -- and a plain Python CLI repo with no detected framework gets back
the empty set, which every one of those rule families treats as "not
relevant" and short-circuits past entirely (owner directive, verbatim).

## frob.webapp

### FrameworkKind

One recognized web/app framework family (`StrEnum`): `nextjs`, `vite`,
`django`, `flask`, `fastapi`, `rails`, `laravel`, `sveltekit`, `astro`.

### detect_frameworks

`detect_frameworks(root: Path) -> frozenset[FrameworkKind]`
(`src/frob/webapp/_detect.py`) is pure file-presence/content-sniff
detection, no tree-sitter parse, no network, no subprocess: it checks for
a handful of marker files (`next.config.js`, `manage.py`, `artisan`, ...)
and, where a marker alone is ambiguous, a substring sniff of the nearest
manifest (`package.json`, `requirements.txt`, `pyproject.toml`, `Gemfile`,
`composer.json`). Recognized kinds, `FrameworkKind` (`StrEnum`):

- `nextjs`, `vite`, `sveltekit`, `astro` -- JS/TS frameworks, sniffed via
  their own config file plus `package.json`. SvelteKit/Astro/Next.js are
  checked before bare Vite, since all three can embed Vite internally and
  should not also register as a second, generic `vite` hit.
- `django`, `flask`, `fastapi` -- Python web frameworks, sniffed via
  `manage.py` (Django only) plus `requirements.txt`/`pyproject.toml`.
- `rails` -- sniffed via `Gemfile`, or an `application.rb` file inside a
  `config/` directory (illustrative marker path, not a repo file here).
- `laravel` -- sniffed via `artisan` or `composer.json`.

A repo can match more than one kind (e.g. a Next.js app that also embeds
Vite for a secondary build) -- the return type is a `frozenset`, not a
single value.

## frob.sql

`src/frob/sql/__init__.py` is presently an empty package stub. SQL
literal detection lives outside `frob.webapp` on purpose: SQL strings
appear in non-web code (migration scripts, CLI tools, ETL jobs) that has
no web framework to detect, so gating SQL rules behind
`detect_frameworks` would be wrong. The SQL rule-family implementation
itself is a later leaf of the T-5299 epic; this package exists now so
`design/frob.strata` and `[arch.layering]` (`frob.toml`) have a real
node/layer declared ahead of that work, matching this ticket's owner
directive that both packages register in the same leaf that creates
them.

## Fixtures

`tests/fixtures/webapp/<framework>/` holds one positive-control fixture
directory per `FrameworkKind`, plus `plain_python_cli/` (no markers at
all, asserts the empty set) -- `tests/unit/test_webapp_detect.py`
parametrizes over all nine plus the empty case.

## Layering

`[arch.layering]` in `frob.toml` declares `webapp`/`sql` as leaf layers
(no allowed imports of their own) that `gates` and `app` may import from
-- the same "shared leaf" role `lang` already plays for the WEBSEC/COMPLY/
A11Y/SEO/WEBPERF/SQL rule leaves this epic adds.
