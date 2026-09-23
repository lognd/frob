# frob.webapp._comply_substrate -- COMPLY signal/required-page substrate

One sentence: before any COMPLY rule runs, it asks two questions --
"does this repo's manifest imply a compliance-relevant behavior
(collecting email, running AI on user data, subscriptions, selling or
sharing data, SMS, a session-replay-or-pixel script, health data)?" and
"does this repo publish the privacy/terms/accessibility pages that
behavior implies it should?" -- both answered by pure file-presence/
content-sniff detection, same shallow style as `frob.webapp._detect`
(T-5302), which this module depends on for framework detection and
never re-implements.

## ComplySignal

One recognized repo-behavior signal (`StrEnum`): `email_collection`,
`ai_on_user_data`, `subscriptions`, `data_sale_or_share`, `sms`,
`session_replay_or_pixel`, `health_data`.

## detect_signals

`detect_signals(root: Path) -> frozenset[ComplySignal]`
(`src/frob/webapp/_comply_substrate.py`) sniffs `root`'s manifests
(`package.json`, `requirements.txt`, `pyproject.toml`) for third-party
package names implying each signal -- e.g. `stripe`/`paddle` imply
`subscriptions`, `twilio`/`vonage` imply `sms`, `fullstory`/`hotjar`
imply `session_replay_or_pixel`, `openai`/`anthropic` imply
`ai_on_user_data`. A repo with none of these packages (the `plain`
fixture) returns the empty `frozenset` -- the signal every COMPLY rule
uses to skip a check that is not relevant to this repo.

## RequiredPage

One site-signal page (`StrEnum`): `privacy`, `terms`, `accessibility`.

## detect_required_pages

`detect_required_pages(root: Path, frameworks: frozenset[FrameworkKind])
-> Result[frozenset[RequiredPage], ComplyScanError]`
(`src/frob/webapp/_comply_substrate.py`) takes the `frozenset
[FrameworkKind]` the caller already got from `frob.webapp.
detect_frameworks` (T-5302) and checks presence of each required page,
keyed off that framework's router convention:

- File-based routers (Next.js, SvelteKit, Astro, Vite) check a handful
  of known page-file paths (e.g. `app/privacy/page.tsx`,
  `src/routes/privacy/+page.svelte`).
- Config-based routers (Django, Flask, FastAPI, Rails, Laravel) sniff
  the framework's one route-config file (`urls.py`, `app.py`, `main.py`,
  a `routes.rb` file inside `config/`, or a `web.php` file inside
  `routes/`) for the page's slug.

Returns `Err(ComplyScanError.ROOT_NOT_READABLE)` if `root` is not a
listable directory; otherwise `Ok` with whatever pages were found
present (possibly the empty `frozenset`, including when `frameworks`
itself is empty -- a plain CLI repo has no router to check at all).

### ComplyScanError

`ComplyScanError.ROOT_NOT_READABLE` is the one failure value
`detect_required_pages` returns (as `Err`) when its `root` argument is
not a listable directory at all -- distinct from an honest
`Ok(frozenset())` answer, which means "listable, nothing found".

## Fixtures

`tests/fixtures/webapp/comply1xx/` holds one positive-control fixture
directory per `ComplySignal` (manifest naming that signal's package)
plus per-framework required-page fixtures, and a `plain/` fixture with
none of the above (empty signals, empty required pages) --
`tests/unit/test_webapp_comply_substrate.py` parametrizes over all of
these plus the negative-control cases.
