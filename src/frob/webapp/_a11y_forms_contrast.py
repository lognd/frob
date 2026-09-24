"""A11Y129-135: redundant entry, accessible authentication, and contrast
(T-5322, docs/modules/webapp-a11y-forms-contrast.md).

# frob:ticket T-5322

Three WCAG 2.2 success criteria that share nothing structurally (one
walks markup for a repeated form field, one walks markup for an
authentication step, one walks CSS for a declared color pair) but share
the same shallow-scan posture every WEBSEC/COMPLY/A11Y/SEO/WEBPERF rule
family in the T-5140 epic takes (owner directive, T-5302): a static,
predictable, text/tree-level check, never a live-DOM/browser rendering
pass, because a false negative here is cheaper than a false positive a
repo owner cannot reproduce.

- SC 3.3.7 (Redundant Entry, A11Y129/A11Y130): a multi-step form that
  asks for the SAME piece of information (matched by an `<input>`'s
  `name` attribute recurring) more than once. A11Y129 fires when a
  later occurrence carries no `autocomplete` attribute (nothing tells
  the browser/AT this value was already supplied once in this flow).
  A11Y130 fires when the first occurrence had a literal `value` and a
  later occurrence of the SAME name does not carry one forward (the
  value was not re-displayed/pre-filled either).
- SC 3.3.8 (Accessible Authentication, A11Y131/A11Y132): a CAPTCHA-style
  cognitive-function-test marker with no alternative-method marker
  alongside it (A11Y131), or a password field that blocks paste via an
  `onpaste` handler with no `data-allow-paste="true"` escape hatch
  (A11Y132 -- blocking paste forces the user to re-type/recall a value
  from memory, itself a cognitive function test SC 3.3.8 disallows
  without an exception).
- SC 1.4.3 (Contrast, A11Y133/A11Y134/A11Y135): a CSS rule declaring a
  literal hex/`rgb()` `color`+`background-color` pair below the WCAG
  relative-luminance contrast threshold -- 4.5:1 for normal text
  (A11Y133), 3:1 for large text (A11Y134, >=24px, or >=18.66px AND
  bold -- the WCAG 18pt/14pt-bold large-text definition converted to
  px), and 3:1 for a `border-color`+`background-color` UI-component
  pair (A11Y135). `contrast_ratio` is exposed as a standalone pure
  function (ticket text: T-5147/SEO-WEBPERF needs the identical math)
  so it carries no dependency on this module's markup/CSS scanning at
  all -- a caller with its own two RGB triples never needs to go
  through a `Violation`/file-scan path to get a ratio.

GATE HOOK SHAPE (T-5323, landed after this ticket's own plan was
written): `frob.gates._a11y_gate.a11y_gate` walks every git-tracked
html-family/jsx-family file ONCE, parses it ONCE, and hands each
discovered `frob.webapp._a11y_*` hook module the SAME already-parsed
`frob.webapp._a11y_structure.A11yFileContext` (file, language, source,
root node) plus the repo's `detect_frameworks` result -- one file, one
call, no filesystem access of its own. `a11y_findings` below matches
that exact hook shape (`ctx, frameworks`), not the plan text's earlier
`(root, frameworks)` sketch. Redundant-entry/accessible-authentication
run straight off `ctx.source`'s decoded text (module docstring below:
a shallow regex scan, same posture `_comply_substrate`/`_websec_sinks`
already take) -- no dependency on `ctx.language` being any particular
family, since a `<input ...>` tag reads the same whether the file
landed in the gate's walk as `.html`, `.jsx`, or `.vue`.

CONTRAST'S KNOWN GAP: `a11y_gate`'s own tracked-file walk covers only
`.html`/`.htm`/`.vue`/`.jsx`/`.tsx` (its module's `_A11Y_EXTENSIONS`) --
it never hands this hook a `.css`/`.scss` `ctx`, so A11Y133-135 cannot
fire through the live gate today even though the CSS-walking code below
is correct and fully unit-tested directly. `_contrast_findings_for_root`
below still runs when `ctx.language` is `"css"`/`"scss"` so this keeps
working the moment a future ticket widens `_A11Y_EXTENSIONS` (filed as
a follow-up, out of this ticket's scope: `src/frob/gates/_a11y_gate.py`
is explicitly off-limits here).

MARKUP SCAN IS REGEX, NOT `frob.lang`/`_a11y_substrate` TREE WALKS: the
redundant-entry and accessible-authentication heuristics above key off
raw `<input ...>`/marker-attribute text, the same shallow
text/manifest-scan shape `frob.webapp._comply_substrate`
(`_manifest_mentions`) and `frob.webapp._websec_sinks`
(`_text_regex_findings`) already use for a text-level heuristic that
does not need a parsed tree to answer -- the CSS contrast check DOES
need a real grammar (declared color literals can be `rgb(...)`
call expressions, not just bare hex text) and walks the already-parsed
`ctx.root` tree-sitter node the gate handed in (T-5303's css/scss
grammar, no re-parse of its own).

frob:doc docs/modules/webapp-a11y-forms-contrast.md
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

from frob.findings import Severity, Violation
from frob.logging import get_logger

if TYPE_CHECKING:
    from tree_sitter import Node

    from frob.webapp._a11y_structure import A11yFileContext
    from frob.webapp._detect import FrameworkKind

_log = get_logger(__name__)

__all__ = [
    "ColorTriple",
    "a11y_findings",
    "contrast_ratio",
]

# frob:doc docs/modules/webapp-a11y-forms-contrast.md#public-api
# A named RGB triple, 0-255 per channel -- the shape both this module's
# CSS scan and any external caller (T-5147) hand `contrast_ratio`.
ColorTriple = tuple[int, int, int]

# ---------------------------------------------------------------------------
# Contrast math (reusable pure function -- ticket text: T-5147 shares it)
# ---------------------------------------------------------------------------


def _srgb_channel(channel_255: int) -> float:
    """One sRGB channel (0-255) converted to its linear-light value, the
    per-channel step of the WCAG relative-luminance formula.

    frob:ticket T-5322
    """
    c = channel_255 / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(rgb: ColorTriple) -> float:
    """WCAG relative luminance of `rgb` (the `0.2126 R + 0.7152 G +
    0.0722 B` weighting over each channel's linear-light value).

    frob:ticket T-5322
    """
    r, g, b = rgb
    return (
        0.2126 * _srgb_channel(r)
        + 0.7152 * _srgb_channel(g)
        + 0.0722 * _srgb_channel(b)
    )


# frob:doc docs/modules/webapp-a11y-forms-contrast.md#public-api
def contrast_ratio(rgb_a: ColorTriple, rgb_b: ColorTriple) -> float:
    """The WCAG contrast ratio between two colors, `(L1 + 0.05) / (L2 +
    0.05)` with `L1` the lighter relative luminance -- always `>= 1.0`,
    `21.0` for pure black on pure white.

    A pure function with no dependency on this module's file/tree
    scanning: T-5147 (SEO/WEBPERF) reuses this directly for its own
    contrast checks (ticket text) without going through `a11y_findings`
    at all.

    frob:ticket T-5322
    """
    lum_a = _relative_luminance(rgb_a)
    lum_b = _relative_luminance(rgb_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Small text helper (the gate already walked/read/parsed the file --
# `ctx.source` is raw bytes, this module only needs the decoded text plus
# a byte-offset-to-line-number lookup over it).
# ---------------------------------------------------------------------------


def _line_of(source: str, offset: int) -> int:
    """1-based line number of byte/char `offset` within `source`.

    frob:ticket T-5322
    """
    return source.count("\n", 0, offset) + 1


# ---------------------------------------------------------------------------
# A11Y129/A11Y130: redundant entry
# ---------------------------------------------------------------------------

_INPUT_TAG_RE = re.compile(r"<input\b[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')

# Input `type`s that plausibly collect reusable personal information
# (SC 3.3.7's own scope -- explicitly excludes e.g. `password`, which SC
# 3.3.7 itself exempts).
_REDUNDANT_ENTRY_TYPES = frozenset({"text", "email", "tel", "url"})


def _parse_attrs(tag_text: str) -> dict[str, str]:
    """`tag_text`'s `name="value"` attributes, lower-cased names.

    frob:ticket T-5322
    """
    return {name.lower(): value for name, value in _ATTR_RE.findall(tag_text)}


def _redundant_entry_findings(rel_path: str, source: str) -> list[Violation]:
    """A11Y129/A11Y130 findings in one html/jsx/vue `source` (module
    docstring's SC 3.3.7 heuristic: an `<input>` `name` recurring with no
    `autocomplete`, or without its earlier literal `value` carried
    forward).

    frob:ticket T-5322
    """
    occurrences: dict[str, list[tuple[int, dict[str, str]]]] = {}
    for match in _INPUT_TAG_RE.finditer(source):
        attrs = _parse_attrs(match.group(0))
        input_type = attrs.get("type", "text").lower()
        name = attrs.get("name")
        if input_type not in _REDUNDANT_ENTRY_TYPES or not name:
            continue
        occurrences.setdefault(name, []).append(
            (_line_of(source, match.start()), attrs)
        )

    findings: list[Violation] = []
    for name, occs in occurrences.items():
        if len(occs) < 2:
            continue
        first_line, first_attrs = occs[0]
        for line, attrs in occs[1:]:
            if "autocomplete" not in attrs:
                findings.append(
                    Violation(
                        rule="A11Y129",
                        severity=Severity.WARN,
                        file=rel_path,
                        line=line,
                        message=(
                            f'input name="{name}" repeats a value already collected '
                            f"at line {first_line} with no autocomplete attribute "
                            f'(WCAG SC 3.3.7) -- add autocomplete="{name}" or an '
                            "equivalent token"
                        ),
                    )
                )
            if first_attrs.get("value") and not attrs.get("value"):
                findings.append(
                    Violation(
                        rule="A11Y130",
                        severity=Severity.WARN,
                        file=rel_path,
                        line=line,
                        message=(
                            f'input name="{name}" was entered at line {first_line} '
                            "but is not pre-filled/re-displayed here (WCAG SC 3.3.7) "
                            "-- carry the earlier value forward"
                        ),
                    )
                )
    _log.debug(
        "a11y_forms_contrast: %d redundant-entry finding(s) in %s",
        len(findings),
        rel_path,
    )
    return findings


# ---------------------------------------------------------------------------
# A11Y131/A11Y132: accessible authentication
# ---------------------------------------------------------------------------

_CAPTCHA_RE = re.compile(
    r'(?:class|id|data-[\w-]+)\s*=\s*"[^"]*captcha[^"]*"', re.IGNORECASE
)
_AUTH_ALTERNATIVE_RE = re.compile(
    r'(?:class|id|data-[\w-]+)\s*=\s*"[^"]*(?:auth-alt|alt-auth|alternative)[^"]*"',
    re.IGNORECASE,
)
_PASSWORD_INPUT_RE = re.compile(
    r'<input\b(?=[^>]*\btype\s*=\s*"password")[^>]*>', re.IGNORECASE
)
_ALLOW_PASTE_RE = re.compile(r'data-allow-paste\s*=\s*"true"', re.IGNORECASE)


def _accessible_auth_findings(rel_path: str, source: str) -> list[Violation]:
    """A11Y131/A11Y132 findings in one html/jsx/vue `source` (module
    docstring's SC 3.3.8 heuristic: a CAPTCHA marker with no alternative
    marker, or a password field blocking paste with no explicit escape
    hatch).

    frob:ticket T-5322
    """
    findings: list[Violation] = []

    captcha_match = _CAPTCHA_RE.search(source)
    if captcha_match is not None and _AUTH_ALTERNATIVE_RE.search(source) is None:
        findings.append(
            Violation(
                rule="A11Y131",
                severity=Severity.WARN,
                file=rel_path,
                line=_line_of(source, captcha_match.start()),
                message=(
                    "CAPTCHA-style cognitive-function test with no alternative "
                    "authentication method marker anywhere in this file (WCAG SC "
                    "3.3.8) -- offer an alt-auth path or mark one with a "
                    '"auth-alt" class/data attribute'
                ),
            )
        )

    for match in _PASSWORD_INPUT_RE.finditer(source):
        tag_text = match.group(0)
        if (
            "onpaste" not in _parse_attrs(tag_text)
            and "onpaste" not in tag_text.lower()
        ):
            continue
        if _ALLOW_PASTE_RE.search(tag_text):
            continue
        findings.append(
            Violation(
                rule="A11Y132",
                severity=Severity.WARN,
                file=rel_path,
                line=_line_of(source, match.start()),
                message=(
                    "password field blocks paste (onpaste handler) with no "
                    'data-allow-paste="true" escape hatch, forcing the user to '
                    "re-type/recall the value from memory (WCAG SC 3.3.8)"
                ),
            )
        )

    _log.debug(
        "a11y_forms_contrast: %d accessible-auth finding(s) in %s",
        len(findings),
        rel_path,
    )
    return findings


# ---------------------------------------------------------------------------
# A11Y133/A11Y134/A11Y135: contrast
# ---------------------------------------------------------------------------

# WCAG 1.4.3 thresholds.
_NORMAL_TEXT_THRESHOLD = 4.5
_LARGE_TEXT_THRESHOLD = 3.0
_UI_COMPONENT_THRESHOLD = 3.0

# WCAG "large text": >=18pt (24px), or >=14pt bold (~18.66px) -- both
# already converted to px here since the CSS grammar reports px/pt/em.
_LARGE_TEXT_PX = 24.0
_LARGE_BOLD_TEXT_PX = 18.66


# frob:doc docs/modules/webapp-a11y-forms-contrast.md#colordeclaration
class _ColorDeclaration(BaseModel):
    """One CSS rule's parsed `color`/`background-color`/`border-color`/
    font metadata, ready for `contrast_ratio`.

    frob:ticket T-5322
    """

    selector: str
    line: int
    color: ColorTriple | None
    background_color: ColorTriple | None
    border_color: ColorTriple | None
    is_large_text: bool


def _child_text(node: Node | None, source: bytes) -> str:
    """`node`'s own source text, or "" if `node` is absent.

    frob:ticket T-5322
    """
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")


def _parse_hex_color(text: str) -> ColorTriple | None:
    """A literal `#rgb`/`#rrggbb` hex color as an RGB triple, or `None`
    for anything else (named colors, `var(...)`, etc -- module docstring:
    literal hex/rgb pairs only).

    frob:ticket T-5322
    """
    text = text.lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return None
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return None


def _parse_color_node(node: Node | None, source: bytes) -> ColorTriple | None:
    """A declared color value node (`color_value` hex literal, or an
    `rgb()`/`rgba()` `call_expression` with literal integer args) as an
    RGB triple, or `None` for any other value shape.

    frob:ticket T-5322
    """
    if node is None:
        return None
    if node.type == "color_value":
        return _parse_hex_color(_child_text(node, source))
    if node.type == "call_expression":
        fn_node = next((c for c in node.children if c.type == "function_name"), None)
        fn_name = _child_text(fn_node, source).lower()
        if fn_name not in ("rgb", "rgba"):
            return None
        args_node = next((c for c in node.children if c.type == "arguments"), None)
        if args_node is None:
            return None
        numbers = [c for c in args_node.children if c.type == "integer_value"]
        if len(numbers) < 3:
            return None
        try:
            r, g, b = (int(_child_text(n, source)) for n in numbers[:3])
        except ValueError:
            return None
        return (r, g, b)
    return None


_FONT_SIZE_RE = re.compile(r"([\d.]+)\s*(px|pt|em|rem)?")


def _font_size_px(node: Node | None, source: bytes) -> float | None:
    """A declared `font-size` value node converted to px (`pt` * 96/72,
    `em`/`rem` assumed 16px baseline), or `None` if unparseable.

    frob:ticket T-5322
    """
    if node is None:
        return None
    text = _child_text(node, source)
    match = _FONT_SIZE_RE.match(text)
    if match is None:
        return None
    value = float(match.group(1))
    unit = match.group(2) or "px"
    if unit == "pt":
        return value * 96.0 / 72.0
    if unit in ("em", "rem"):
        return value * 16.0
    return value


def _is_bold(node: Node | None, source: bytes) -> bool:
    """True if a declared `font-weight` value node is `bold` or a numeric
    weight `>= 700`.

    frob:ticket T-5322
    """
    if node is None:
        return False
    text = _child_text(node, source).strip().lower()
    if text == "bold":
        return True
    try:
        return int(text) >= 700
    except ValueError:
        return False


def _is_large_text(font_size_px: float | None, bold: bool) -> bool:
    """WCAG "large text" classification (module constants) from a parsed
    `font-size`/`font-weight` pair.

    frob:ticket T-5322
    """
    if font_size_px is None:
        return False
    if font_size_px >= _LARGE_TEXT_PX:
        return True
    return bold and font_size_px >= _LARGE_BOLD_TEXT_PX


def _selector_text(rule_set: Node, source: bytes) -> str:
    """A `rule_set` node's own selector text, whitespace-collapsed.

    frob:ticket T-5322
    """
    selectors = next((c for c in rule_set.children if c.type == "selectors"), None)
    text = _child_text(selectors, source) if selectors is not None else ""
    return " ".join(text.split()) or "<rule>"


def _iter_rule_sets(node: Node) -> list[Node]:
    """Every `rule_set` under `node`, at any nesting depth (covers rules
    nested inside `@media`/SCSS `&` blocks).

    frob:ticket T-5322
    """
    found: list[Node] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type == "rule_set":
            found.append(current)
        stack.extend(current.children)
    return found


def _declaration_values(rule_set: Node, source: bytes) -> dict[str, Node]:
    """`rule_set`'s own direct `declaration` children as a
    `{property-name: value-node}` map (lower-cased property names; the
    last declaration of a repeated property wins, CSS cascade order).

    frob:ticket T-5322
    """
    block = next((c for c in rule_set.children if c.type == "block"), None)
    if block is None:
        return {}
    values: dict[str, Node] = {}
    for child in block.children:
        if child.type != "declaration":
            continue
        name_node = next((c for c in child.children if c.type == "property_name"), None)
        if name_node is None:
            continue
        name = _child_text(name_node, source).strip().lower()
        value_node = next(
            (c for c in child.children if c.type not in ("property_name", ":", ";")),
            None,
        )
        if value_node is not None:
            values[name] = value_node
    return values


def _color_declaration(rule_set: Node, source: bytes) -> _ColorDeclaration:
    """`rule_set` parsed into a `_ColorDeclaration` (module docstring's
    contrast inputs).

    frob:ticket T-5322
    """
    values = _declaration_values(rule_set, source)
    return _ColorDeclaration(
        selector=_selector_text(rule_set, source),
        line=rule_set.start_point[0] + 1,
        color=_parse_color_node(values.get("color"), source),
        background_color=_parse_color_node(values.get("background-color"), source),
        border_color=_parse_color_node(values.get("border-color"), source),
        is_large_text=_is_large_text(
            _font_size_px(values.get("font-size"), source),
            _is_bold(values.get("font-weight"), source),
        ),
    )


def _contrast_findings_for_declaration(
    rel_path: str, decl: _ColorDeclaration
) -> list[Violation]:
    """A11Y133/A11Y134/A11Y135 findings for one parsed `_ColorDeclaration`.

    frob:ticket T-5322
    """
    findings: list[Violation] = []
    if decl.color is not None and decl.background_color is not None:
        ratio = contrast_ratio(decl.color, decl.background_color)
        threshold = (
            _LARGE_TEXT_THRESHOLD if decl.is_large_text else _NORMAL_TEXT_THRESHOLD
        )
        rule = "A11Y134" if decl.is_large_text else "A11Y133"
        text_kind = "large" if decl.is_large_text else "normal"
        if ratio < threshold:
            findings.append(
                Violation(
                    rule=rule,
                    severity=Severity.WARN,
                    file=rel_path,
                    line=decl.line,
                    message=(
                        f"{decl.selector}: text/background contrast {ratio:.2f}:1 is "
                        f"below the {threshold}:1 WCAG SC 1.4.3 threshold for "
                        f"{text_kind} text"
                    ),
                )
            )
    if decl.border_color is not None and decl.background_color is not None:
        ratio = contrast_ratio(decl.border_color, decl.background_color)
        if ratio < _UI_COMPONENT_THRESHOLD:
            findings.append(
                Violation(
                    rule="A11Y135",
                    severity=Severity.WARN,
                    file=rel_path,
                    line=decl.line,
                    message=(
                        f"{decl.selector}: border/background contrast {ratio:.2f}:1 is "
                        f"below the {_UI_COMPONENT_THRESHOLD}:1 WCAG SC 1.4.3 UI-"
                        "component threshold"
                    ),
                )
            )
    return findings


# CSS/SCSS language labels this hook's contrast branch runs for -- the
# `frob.lang.raw_tree`/`ParsedFile.language` labels T-5303 wired in.
_CSS_FAMILY_LANGUAGES = frozenset({"css", "scss"})


def _contrast_findings_for_root(
    root: Node, source: bytes, rel_path: str
) -> list[Violation]:
    """A11Y133/A11Y134/A11Y135 findings over an already-parsed css/scss
    `root` node (module docstring's "known gap": only reachable today when
    a caller hands this an actual css/scss `ctx`, which the live gate does
    not yet do -- exercised directly by this module's own unit tests).

    frob:ticket T-5322
    """
    findings: list[Violation] = []
    for rule_set in _iter_rule_sets(root):
        decl = _color_declaration(rule_set, source)
        findings.extend(_contrast_findings_for_declaration(rel_path, decl))
    _log.debug(
        "a11y_forms_contrast: %d contrast finding(s) in %s", len(findings), rel_path
    )
    return findings


# ---------------------------------------------------------------------------
# Gate hook (discovered by `frob.gates._a11y_gate`, T-5323 -- see module
# docstring's "GATE HOOK SHAPE" note; matches the `A11yFileContext`
# per-file hook convention `frob.webapp._a11y_structure.a11y_findings`
# itself uses, not the WEBSEC family's direct-import shape)
# ---------------------------------------------------------------------------


# frob:doc docs/modules/webapp-a11y-forms-contrast.md#public-api
# frob:ticket T-5322
def a11y_findings(
    ctx: A11yFileContext, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """A11Y129-135: every redundant-entry/accessible-authentication/
    contrast finding in one already-parsed `ctx` (module docstring's
    "GATE HOOK SHAPE" note) -- the hook `frob.gates._a11y_gate.a11y_gate`
    (T-5323) discovers and calls once per git-tracked file it walks.

    Short-circuits to `()` when `frameworks` is empty -- the gate has
    already run `frob.webapp._detect.detect_frameworks(root)` once and
    passes the result in; this module never re-detects frameworks itself
    (T-5302's contract, same posture `detect_required_pages` already
    takes).

    frob:ticket T-5322
    """
    if not frameworks:
        _log.debug("a11y_forms_contrast: no frameworks detected, skipping %s", ctx.file)
        return ()

    if ctx.language in _CSS_FAMILY_LANGUAGES:
        findings = _contrast_findings_for_root(ctx.root, ctx.source, ctx.file)
    else:
        text = ctx.source.decode("utf-8", errors="ignore")
        findings = _redundant_entry_findings(ctx.file, text)
        findings.extend(_accessible_auth_findings(ctx.file, text))

    _log.info("a11y_forms_contrast: %d finding(s) in %s", len(findings), ctx.file)
    return tuple(findings)
