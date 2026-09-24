"""A11Y116-124: keyboard, focus, target-size, and motion checks
(T-5321, extends the T-5313 A11Y substrate -- docs/modules/webapp-a11y-interaction.md).

# frob:ticket T-5321

`frob.gates._a11y_gate` (T-5323) discovers every module in the
`frob.webapp` package whose name starts with the `_a11y_` prefix and
exposes a module-level `a11y_findings(ctx, frameworks) ->
tuple[Violation, ...]` hook, folding the results into one gate. This
leaf owns the "interaction" corner of the reserved `A11Y1xx` block
(`frob.gates._waive._KNOWN_GATE_RULES`): keyboard operability, focus
visibility, pointer target size, and motion-preference respect --
distinct from T-5313's own `alt`/`aria-label`/heading-level/`<html lang>`
substrate, which this module reuses (`frob.webapp._a11y_substrate`) where
the query shape fits (`elements_with_attribute` for `aria-hidden`) but
otherwise does its own scan: most of these checks need either raw
attribute VALUES (a `tabindex` number, an `href` on an anchor) or CSS
declaration text (`outline: none`, a pixel width, `prefers-reduced-
motion`) that the shared substrate's element/heading query shapes do not
carry.

GATE CONTRACT (T-5323): `ctx` is a `frob.webapp._a11y_structure.
A11yFileContext` -- ONE already-parsed file (`file`, `language`, `source`,
`root`), handed to every discovered hook by `frob.gates._a11y_gate.
a11y_gate`'s own single walk-and-parse-once pass over every git-tracked
file its own `_A11Y_EXTENSIONS` tuple names. `frameworks` is likewise
already-detected by the gate (`frob.webapp._detect.detect_frameworks`,
called once per `frob check` run, not once per leaf module). An empty
`frameworks` short-circuits to `()` before `ctx.source` is even decoded.

KNOWN GAP -- CSS IS NOT YET PART OF THE GATE'S OWN FILE WALK: T-5323's
`_a11y_gate._A11Y_EXTENSIONS` covers only html/vue/jsx/tsx -- CSS/SCSS
(`.css`/`.scss`) is not in that tuple, so `a11y_findings` is never
actually invoked with a CSS `ctx` through the real gate today, even
though this leaf's four CSS-declaration rules (A11Y117/120/121/122) are
fully implemented and unit-tested by constructing a CSS `A11yFileContext`
directly (the same shape `frob.gates._a11y_gate`'s own file walk would
hand this hook once CSS is added there). Widening `_A11Y_EXTENSIONS` is a
`src/frob/gates/**` edit outside this ticket's declared scope; T-draft-2c8aa622
is filed to close this gap.

TEXT-REGEX, NOT TREE-SITTER, FOR MOST OF THIS LEAF: `frob.lang` has no
CSS declaration-value grammar (T-5303's `_walk_css.py` walks CSS/SCSS
into `RawSymbol`s for `frob.graph`'s symbol index -- selector text and
opaque token spans, not parsed property/value pairs), and several checks
here (a skip link's own link TEXT, an `outline` declaration's value, a
pixel dimension, `autoplay`/`controls` co-occurrence on one tag) need
exactly that. `frob.webapp._websec_sinks` already sets the precedent
(WEBSEC104-106) for TEXT-REGEX detection where the declared scope is not
a tree-sitter-parseable shape frob has a grammar for; this module follows
the same posture rather than hand-rolling a CSS value parser for nine
rules that are individually simple text patterns -- it operates on
`ctx.source` decoded to text, not `ctx.root`'s tree-sitter node tree.

NINE RULES, EACH WARN-TIER AT FIRST TURN-ON (same T-0688/T-0973 posture
`taint_gate`/`opaque_gate` follow for a brand-new structural rule; a real
fix-or-waive pass over the first measured hit set decides whether ERROR
is safe):

- A11Y116: an html-family page (has a `<body>`) with no skip-link anchor
  (`<a href="#...">` whose own text mentions "skip") -- WCAG SC 2.4.1.
- A11Y117: a `:focus` CSS rule that suppresses the browser focus ring
  (`outline: none`/`outline: 0`) with no `:focus-visible` rule anywhere
  in the same file supplying a real replacement (a non-`none` `outline`
  or a `box-shadow`) -- WCAG SC 2.4.7.
- A11Y118: `tabindex`/`tabIndex` greater than 0 -- WCAG SC 2.4.3 (a
  positive tabindex reorders the natural tab sequence, the classic
  keyboard-trap-adjacent anti-pattern).
- A11Y119: `aria-hidden="true"` on a naturally-focusable element (`a`
  with `href`, `button`, `input`, `select`, `textarea`) -- a focusable
  element hidden from assistive tech is still reachable by keyboard,
  producing an invisible focus stop.
- A11Y120: a `button`/`.btn`/`[role="button"]`-shaped CSS rule declaring
  a width/height (or min-width/min-height) below 24 CSS px -- WCAG SC
  2.5.8 (Target Size, Minimum, AA).
- A11Y121: the same selector family declaring a dimension between 24 and
  44 CSS px -- WCAG SC 2.5.5 (Target Size, Enhanced, AAA); a distinct,
  lower-severity-expectation rule id from A11Y120 rather than one rule
  with two thresholds, so a repo that only wants the AA floor can waive
  A11Y121 alone.
- A11Y122: a CSS/SCSS file declaring `animation`/`transition` with no
  `prefers-reduced-motion` media query anywhere in the file -- WCAG SC
  2.3.3.
- A11Y123: a `<video>`/`<audio>` tag carrying `autoplay` with no
  `controls` attribute on the same tag -- WCAG SC 1.4.2/2.2.2 (a user
  with no way to pause auto-playing media).
- A11Y124: a `<video>` element with no `<track kind="captions">` child
  (or a self-closing `<video/>`, which by construction can have none) --
  WCAG SC 1.2.2.
"""

from __future__ import annotations

import re

from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.webapp._a11y_structure import A11yFileContext
from frob.webapp._detect import FrameworkKind

_log = get_logger(__name__)

__all__ = ["a11y_findings"]

# `A11yFileContext.language` labels this leaf treats as html-family markup
# (module docstring's skip-link/tabindex/aria-hidden/autoplay/captions
# rules) -- the same label set `frob.webapp._a11y_substrate` supports.
_HTML_FAMILY_LANGUAGES = frozenset({"html", "vue", "javascript", "typescript"})

# `A11yFileContext.language` labels this leaf treats as CSS-family
# declarations (module docstring's KNOWN GAP: never actually handed by
# today's `_a11y_gate` file walk, but supported here for when it is).
_CSS_FAMILY_LANGUAGES = frozenset({"css", "scss"})

# Naturally-focusable tags that always accept keyboard focus regardless of
# attributes (module docstring, A11Y119) -- `a` is handled separately
# below since it is only focusable when it carries `href`.
_ALWAYS_FOCUSABLE_TAGS = frozenset({"button", "input", "select", "textarea"})

_SKIP_LINK_RE = re.compile(
    r'<a\b[^>]*href=["\']#[^"\']+["\'][^>]*>((?:(?!</a>).)*)</a>',
    re.IGNORECASE | re.DOTALL,
)
_BODY_TAG_RE = re.compile(r"<body\b", re.IGNORECASE)
_TABINDEX_RE = re.compile(r'tabindex\s*=\s*["\']?(-?\d+)["\']?', re.IGNORECASE)
_FOCUSABLE_TAG_RE = re.compile(
    r"<(a|button|input|select|textarea)\b([^>]*)>", re.IGNORECASE
)
_ARIA_HIDDEN_TRUE_RE = re.compile(r'aria-hidden\s*=\s*["\']true["\']', re.IGNORECASE)
_HREF_ATTR_RE = re.compile(r"\bhref\s*=", re.IGNORECASE)
_MEDIA_TAG_RE = re.compile(r"<(video|audio)\b([^>]*)>", re.IGNORECASE)
_AUTOPLAY_ATTR_RE = re.compile(r"\bautoplay\b", re.IGNORECASE)
_CONTROLS_ATTR_RE = re.compile(r"\bcontrols\b", re.IGNORECASE)
_VIDEO_ELEMENT_RE = re.compile(
    r"<video\b[^>]*?(?:(/>)|>(.*?)</video>)", re.IGNORECASE | re.DOTALL
)
_CAPTIONS_TRACK_RE = re.compile(
    r'<track\b[^>]*\bkind\s*=\s*["\']captions["\']', re.IGNORECASE
)

# A flat (no-nesting) `selector { body }` split -- sufficient for the
# single-level rule sets every fixture in this leaf's corpus uses (module
# docstring: TEXT-REGEX, not a full CSS parser).
_CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_FOCUS_SELECTOR_RE = re.compile(r":focus\b(?!-visible)", re.IGNORECASE)
_FOCUS_VISIBLE_SELECTOR_RE = re.compile(r":focus-visible\b", re.IGNORECASE)
_OUTLINE_NONE_RE = re.compile(r"outline\s*:\s*(none|0)\b", re.IGNORECASE)
_OUTLINE_REPLACEMENT_RE = re.compile(
    r"outline\s*:\s*(?!none\b|0\b)\S|box-shadow\s*:", re.IGNORECASE
)
_INTERACTIVE_SELECTOR_RE = re.compile(
    r'\bbutton\b|\.btn\b|\[role\s*=\s*["\']button["\']\]', re.IGNORECASE
)
_DIMENSION_RE = re.compile(
    r"(?:min-)?(?:width|height)\s*:\s*(\d+(?:\.\d+)?)px", re.IGNORECASE
)
_MOTION_DECL_RE = re.compile(r"\b(animation|transition)\s*:", re.IGNORECASE)
_REDUCED_MOTION_RE = re.compile(r"prefers-reduced-motion", re.IGNORECASE)

_TARGET_SIZE_MINIMUM_PX = 24
_TARGET_SIZE_ENHANCED_PX = 44


def _line_of(source: str, offset: int) -> int:
    """The 1-based line number of byte/char `offset` in `source`."""
    return source.count("\n", 0, offset) + 1


def _violation(rule: str, rel_path: str, line: int, message: str) -> Violation:
    """One WARN-tier `Violation` for this leaf (module docstring: every
    rule here is WARN at first turn-on).

    frob:ticket T-5321
    """
    return Violation(
        rule=rule, severity=Severity.WARN, file=rel_path, line=line, message=message
    )


def _skip_link_findings(source: str, rel_path: str) -> list[Violation]:
    """A11Y116: a page with a `<body>` but no skip-link anchor.

    frob:ticket T-5321
    """
    body_match = _BODY_TAG_RE.search(source)
    if body_match is None:
        return []
    for anchor_match in _SKIP_LINK_RE.finditer(source):
        if "skip" in anchor_match.group(1).lower():
            return []
    return [
        _violation(
            "A11Y116",
            rel_path,
            _line_of(source, body_match.start()),
            'page has no skip-link anchor (<a href="#..."> mentioning '
            '"skip") before its main content (WCAG SC 2.4.1)',
        )
    ]


def _tabindex_findings(source: str, rel_path: str) -> list[Violation]:
    """A11Y118: a positive `tabindex`/`tabIndex`.

    frob:ticket T-5321
    """
    findings: list[Violation] = []
    for match in _TABINDEX_RE.finditer(source):
        if int(match.group(1)) > 0:
            findings.append(
                _violation(
                    "A11Y118",
                    rel_path,
                    _line_of(source, match.start()),
                    f"tabindex={match.group(1)} reorders the natural tab "
                    'sequence (WCAG SC 2.4.3); use tabindex="0" or '
                    "restructure the markup instead",
                )
            )
    return findings


def _aria_hidden_focusable_findings(source: str, rel_path: str) -> list[Violation]:
    """A11Y119: `aria-hidden="true"` on a naturally-focusable element.

    frob:ticket T-5321
    """
    findings: list[Violation] = []
    for match in _FOCUSABLE_TAG_RE.finditer(source):
        tag = match.group(1).lower()
        attrs_text = match.group(2)
        if not _ARIA_HIDDEN_TRUE_RE.search(attrs_text):
            continue
        if tag == "a" and not _HREF_ATTR_RE.search(attrs_text):
            continue
        findings.append(
            _violation(
                "A11Y119",
                rel_path,
                _line_of(source, match.start()),
                f'<{tag}> is focusable but carries aria-hidden="true" -- '
                "a keyboard user can still tab to an element assistive "
                "tech is told to ignore",
            )
        )
    return findings


def _autoplay_without_controls_findings(source: str, rel_path: str) -> list[Violation]:
    """A11Y123: `<video>`/`<audio autoplay>` with no `controls`.

    frob:ticket T-5321
    """
    findings: list[Violation] = []
    for match in _MEDIA_TAG_RE.finditer(source):
        tag = match.group(1).lower()
        attrs_text = match.group(2)
        if _AUTOPLAY_ATTR_RE.search(attrs_text) and not _CONTROLS_ATTR_RE.search(
            attrs_text
        ):
            findings.append(
                _violation(
                    "A11Y123",
                    rel_path,
                    _line_of(source, match.start()),
                    f"<{tag} autoplay> has no controls attribute -- a user "
                    "has no way to pause auto-playing media (WCAG SC "
                    "1.4.2/2.2.2)",
                )
            )
    return findings


def _video_captions_findings(source: str, rel_path: str) -> list[Violation]:
    """A11Y124: a `<video>` with no `<track kind="captions">` child.

    frob:ticket T-5321
    """
    findings: list[Violation] = []
    for match in _VIDEO_ELEMENT_RE.finditer(source):
        self_closing, inner = match.group(1), match.group(2)
        if self_closing is not None or not _CAPTIONS_TRACK_RE.search(inner or ""):
            findings.append(
                _violation(
                    "A11Y124",
                    rel_path,
                    _line_of(source, match.start()),
                    '<video> has no <track kind="captions"> child (WCAG SC 1.2.2)',
                )
            )
    return findings


def _html_family_findings(source: str, rel_path: str) -> list[Violation]:
    """Every A11Y11x/A11Y12x finding this leaf detects from html-family
    (html/jsx/tsx/vue) source text.

    frob:ticket T-5321
    """
    findings: list[Violation] = []
    findings.extend(_skip_link_findings(source, rel_path))
    findings.extend(_tabindex_findings(source, rel_path))
    findings.extend(_aria_hidden_focusable_findings(source, rel_path))
    findings.extend(_autoplay_without_controls_findings(source, rel_path))
    findings.extend(_video_captions_findings(source, rel_path))
    return findings


def _focus_visible_findings(source: str, rel_path: str) -> list[Violation]:
    """A11Y117: a `:focus` rule suppressing the outline with no
    `:focus-visible` replacement anywhere in the file.

    frob:ticket T-5321
    """
    has_replacement = any(
        _FOCUS_VISIBLE_SELECTOR_RE.search(selector)
        and _OUTLINE_REPLACEMENT_RE.search(body)
        for selector, body in _CSS_RULE_RE.findall(source)
    )
    if has_replacement:
        return []
    findings: list[Violation] = []
    for match in _CSS_RULE_RE.finditer(source):
        selector, body = match.group(1), match.group(2)
        if _FOCUS_SELECTOR_RE.search(selector) and _OUTLINE_NONE_RE.search(body):
            findings.append(
                _violation(
                    "A11Y117",
                    rel_path,
                    _line_of(source, match.start()),
                    "outline suppressed on :focus with no :focus-visible "
                    "replacement anywhere in this file (WCAG SC 2.4.7)",
                )
            )
    return findings


def _target_size_findings(source: str, rel_path: str) -> list[Violation]:
    """A11Y120/A11Y121: an interactive-control rule declaring a pixel
    dimension below the 24px minimum or the 44px enhanced threshold.

    frob:ticket T-5321
    """
    findings: list[Violation] = []
    for match in _CSS_RULE_RE.finditer(source):
        selector, body = match.group(1), match.group(2)
        if not _INTERACTIVE_SELECTOR_RE.search(selector):
            continue
        values = [float(v) for v in _DIMENSION_RE.findall(body)]
        if not values:
            continue
        smallest = min(values)
        line = _line_of(source, match.start())
        if smallest < _TARGET_SIZE_MINIMUM_PX:
            findings.append(
                _violation(
                    "A11Y120",
                    rel_path,
                    line,
                    f"{selector.strip()} declares a {smallest:g}px target "
                    f"dimension, below the {_TARGET_SIZE_MINIMUM_PX}px "
                    "minimum (WCAG SC 2.5.8)",
                )
            )
        elif smallest < _TARGET_SIZE_ENHANCED_PX:
            findings.append(
                _violation(
                    "A11Y121",
                    rel_path,
                    line,
                    f"{selector.strip()} declares a {smallest:g}px target "
                    f"dimension, below the {_TARGET_SIZE_ENHANCED_PX}px "
                    "enhanced threshold (WCAG SC 2.5.5)",
                )
            )
    return findings


def _reduced_motion_findings(source: str, rel_path: str) -> list[Violation]:
    """A11Y122: `animation`/`transition` declared with no
    `prefers-reduced-motion` media query anywhere in the file.

    frob:ticket T-5321
    """
    if _REDUCED_MOTION_RE.search(source):
        return []
    match = _MOTION_DECL_RE.search(source)
    if match is None:
        return []
    return [
        _violation(
            "A11Y122",
            rel_path,
            _line_of(source, match.start()),
            "animation/transition declared with no "
            "@media (prefers-reduced-motion: reduce) override anywhere "
            "in this file (WCAG SC 2.3.3)",
        )
    ]


def _css_family_findings(source: str, rel_path: str) -> list[Violation]:
    """Every A11Y117/A11Y120/A11Y121/A11Y122 finding this leaf detects
    from CSS/SCSS source text.

    frob:ticket T-5321
    """
    findings: list[Violation] = []
    findings.extend(_focus_visible_findings(source, rel_path))
    findings.extend(_target_size_findings(source, rel_path))
    findings.extend(_reduced_motion_findings(source, rel_path))
    return findings


# frob:doc docs/modules/webapp-a11y-interaction.md#public-api
# frob:ticket T-5321
def a11y_findings(
    ctx: A11yFileContext, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """A11Y116-124: every keyboard/focus/target-size/motion finding in the
    single already-parsed file `ctx` names (module docstring for the full
    rule list and the gate contract `ctx` follows).

    Short-circuits to `()` when `frameworks` is empty -- the
    `frob.gates._a11y_gate` discovery convention (T-5323) detects
    frameworks once per `frob check` run and passes the result to every
    `_a11y_`-prefixed leaf module in `frob.webapp`, rather than each leaf
    re-detecting.

    frob:ticket T-5321
    """
    if not frameworks:
        _log.debug("a11y_interaction: no framework detected, skipping scan")
        return ()

    source = ctx.source.decode("utf-8", errors="ignore")
    if ctx.language in _HTML_FAMILY_LANGUAGES:
        findings = _html_family_findings(source, ctx.file)
    elif ctx.language in _CSS_FAMILY_LANGUAGES:
        findings = _css_family_findings(source, ctx.file)
    else:
        _log.debug(
            "a11y_interaction: unhandled language=%s for %s", ctx.language, ctx.file
        )
        return ()

    _log.debug("a11y_interaction: %d finding(s) in %s", len(findings), ctx.file)
    return tuple(findings)
