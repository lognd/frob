# frob.webapp._comply_privacy -- COMPLY101-108 privacy-policy content

One sentence: `comply_privacy_findings` content-lints a repo's
privacy-policy page against CCPA/CalOPPA requirements -- required page
presence, four required sections, a `last_updated` frontmatter recency
date, and two signal-gated sections (Do-Not-Sell, categories sold or
shared) -- built entirely on top of `frob.webapp._comply_substrate`
(T-5360) for page/signal detection.

## Relationship to `frob.webapp._comply_substrate` (T-5360)

`_comply_substrate.py` answers two questions this module reuses and
never re-implements: whether a `/privacy` page is present at all
(`detect_required_pages`, `RequiredPage.PRIVACY`) and whether the repo's
manifest implies a `session_replay_or_pixel` or `data_sale_or_share`
behavior (`detect_signals`). The substrate's page-presence answer is a
boolean only -- it never exposes which file the page lives at, since its
own per-framework route-candidate tables are private implementation
detail -- so this module keeps its own small, disclosed-as-v1 candidate
search (`_locate_privacy_page`, a tracked-file name-stem scan for
"privacy") to find the actual file to content-lint, the same "own tiny
candidate table" posture `frob.webapp._a11y_statement.
_locate_statement_page`'s module docstring documents for the identical
problem in the accessibility-statement leaf.

## The eight rule ids

- **COMPLY101** -- no `/privacy` page found (`RequiredPage.PRIVACY` not
  in the substrate's `detect_required_pages` result, or the substrate
  reports it present via a route-config slug mention with no matching
  file this module's own candidate search can locate).
- **COMPLY102** -- the privacy page has no "categories collected"-shaped
  section (CalOPPA Cal. Bus. & Prof. Code 22575(b)).
- **COMPLY103** -- no "effective date"-shaped section (CalOPPA 22575(b)).
- **COMPLY104** -- no "do not track"-shaped section (CalOPPA
  22575(b)(5)).
- **COMPLY105** -- no `last_updated` YAML-frontmatter date at all (CCPA
  Cal. Civ. Code 1798.130(a)(5)).
- **COMPLY106** -- `last_updated` present but more than 366 days (~12
  months) old (CCPA 1798.130(a)(5)'s own review cadence).
- **COMPLY107** -- `ComplySignal.SESSION_REPLAY_OR_PIXEL` detected but no
  "do not sell"/"do not sell or share"-shaped section (CCPA
  1798.135(a)).
- **COMPLY108** -- `ComplySignal.DATA_SALE_OR_SHARE` detected but no
  "categories sold/shared"-shaped section, distinct from COMPLY102's
  categories-COLLECTED section (CCPA 1798.130(a)(5)'s second list).

## Public API

### ComplyPrivacyFinding

`@dataclass(frozen=True)`: `rule: str`, `file: str`, `line: int`,
`message: str` -- one COMPLY101-108 finding.

### comply_privacy_findings

`comply_privacy_findings(root: Path) -> tuple[ComplyPrivacyFinding, ...]`

Short-circuits to `()` when `frob.webapp._detect.detect_frameworks(root)`
reports no web framework at all (T-5302's contract, same posture every
sibling WEBSEC/COMPLY family follows).

### websec_findings

`websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) -> tuple[Violation, ...]`

`frob.webapp._comply_substrate`'s own doc defines no comply-specific
gate-discovery hook or convention (no COMPLY leaf had landed before this
one). This leaf instead reuses `frob.gates._taint_gate`'s existing
`websec_findings(root, frameworks)` discovery CONVENTION (T-5308) rather
than inventing a second mechanism; `_taint_gate.py`'s discovery prefix
was widened from `_websec_` alone to also match `_comply_` so this hook
is actually discovered and called, not merely convention-shaped. WARN-
tier at first turn-on (T-0688/T-0973 promotion posture, same as every
sibling WEBSEC/COMPLY family).

## Fixtures

`tests/fixtures/webapp/comply1xx/privacy/` -- a shared `compliant`
fixture (full content, both signals present and satisfied, a recent
`last_updated`) serves as the negative control for every rule id at
once, plus one positive-control directory per rule id
(`missing_page`, `missing_categories`, `missing_effective_date`,
`missing_do_not_track`, `missing_last_updated`, `stale_last_updated`,
`missing_do_not_sell`, `missing_categories_sold`). Separate from T-5360's
own `tests/fixtures/webapp/comply1xx/` substrate fixtures (`signal_*`,
`pages_*`, `plain`), which remain that ticket's scope, and from sibling
leaves' `comply1xx/gdpr/**`, `comply1xx/sector/**`, `comply1xx/commerce/**`.
