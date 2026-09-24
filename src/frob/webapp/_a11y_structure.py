"""A11Y101-115: non-text content, document structure, and form-labeling
rules over the WCAG 2.2 A/AA corpus T-5146 reserved these rule ids for
(docs/modules/webapp-a11y-structure.md).

Every rule here is a pure function of one parsed file's
`frob.webapp._a11y_substrate` query results (T-5313) plus the repo-wide
`frob.webapp._detect.detect_frameworks` frozenset -- this module never
touches a filesystem path or re-parses anything itself; `a11y_findings`
(the module-level hook `src/frob/gates/_a11y_gate.py` discovers via
`pkgutil.iter_modules`, T-5323) is handed an already-parsed
`A11yFileContext` (tree-sitter root node, language label, source bytes,
repo-relative file path) by the gate and returns whatever `Violation`s it
finds in that one file.

RULE INDEX (WCAG 2.2 success criterion in parens):
- A11Y101 -- `<img>`/`<input type="image">` missing `alt` (SC 1.1.1).
- A11Y102 -- `<svg role="img">` missing an accessible name (SC 1.1.1).
- A11Y103 -- heading level skips a level (e.g. `h1` straight to `h3`,
  SC 1.3.1).
- A11Y104 -- more than one `h1` on the page (SC 1.3.1).
- A11Y105 -- `<title>` missing or empty (SC 2.4.2).
- A11Y106 -- `<html>` missing a `lang` attribute (SC 3.1.1).
- A11Y107 -- `<html lang="">` present but empty (SC 3.1.1).
- A11Y108 -- `<a>` with no accessible name (SC 2.4.4).
- A11Y109 -- `<button>` with no accessible name (SC 2.4.4).
- A11Y110 -- `<a>`/`<button>` accessible name is a known generic phrase
  ("click here", "read more", ..., SC 2.4.4).
- A11Y111 -- form input with no associated label (`<label for=...>`,
  `aria-label`, or `aria-labelledby`).
- A11Y112 -- an identity-autofill input (`email`/`tel`/`name`/... type or
  `name` attribute) missing `autocomplete` (SC 1.3.5).
- A11Y113 -- duplicate `id` attribute value in one file.
- A11Y114 -- `role="..."` value that is not a recognized ARIA role.
- A11Y115 -- `aria-*` attribute name that is not a recognized ARIA state
  or property.

Each rule is WARN-tier at first turn-on -- the same T-0688/T-0973
promotion posture every other WEBSEC/COMPLY/SEO first-turn-on gate family
already follows (a real fix-or-waive pass over the first measured hit set
decides whether ERROR is safe).

frob:ticket T-5323
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.webapp._a11y_substrate import (
    ElementMatch,
    all_elements,
    elements_missing_attribute,
    elements_with_attribute,
    heading_sequence,
    html_lang,
)

if TYPE_CHECKING:
    from tree_sitter import Node

    from frob.webapp._detect import FrameworkKind

_log = get_logger(__name__)

__all__ = ["A11yFileContext", "a11y_findings"]

# Tags whose only accessible-name channel is `alt` (A11Y101).
_ALT_REQUIRED_TAGS = frozenset({"img"})

# Interactive elements A11Y108-110's "accessible name" rules apply to.
_LINK_TAGS = frozenset({"a"})
_BUTTON_TAGS = frozenset({"button"})

# Known-generic link/button text (lower-cased, whitespace-collapsed) --
# WCAG 2.2 SC 2.4.4's "Link Purpose (In Context)" failure case F84.
_GENERIC_ACCESSIBLE_NAMES = frozenset(
    {
        "click here",
        "here",
        "read more",
        "more",
        "learn more",
        "link",
        "go",
        "details",
    }
)

# `<input>` types that carry personal-identity data, where autocomplete
# hints matter most (SC 1.3.5 "Identify Input Purpose").
_IDENTITY_INPUT_TYPES = frozenset({"email", "tel", "text", "password"})
_IDENTITY_NAME_HINTS = ("email", "phone", "tel", "name", "address", "username")

# Form-control tags A11Y111/A11Y112 inspect.
_FORM_CONTROL_TAGS = frozenset({"input", "textarea", "select"})

# The WAI-ARIA 1.2 role vocabulary (abstract roles excluded -- those are
# never valid as an author-supplied `role="..."` value).
_KNOWN_ARIA_ROLES = frozenset(
    {
        "alert",
        "alertdialog",
        "application",
        "article",
        "banner",
        "button",
        "cell",
        "checkbox",
        "columnheader",
        "combobox",
        "complementary",
        "contentinfo",
        "definition",
        "dialog",
        "directory",
        "document",
        "feed",
        "figure",
        "form",
        "grid",
        "gridcell",
        "group",
        "heading",
        "img",
        "link",
        "list",
        "listbox",
        "listitem",
        "log",
        "main",
        "marquee",
        "math",
        "menu",
        "menubar",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "navigation",
        "none",
        "note",
        "option",
        "presentation",
        "progressbar",
        "radio",
        "radiogroup",
        "region",
        "row",
        "rowgroup",
        "rowheader",
        "scrollbar",
        "search",
        "searchbox",
        "separator",
        "slider",
        "spinbutton",
        "status",
        "switch",
        "tab",
        "table",
        "tablist",
        "tabpanel",
        "term",
        "textbox",
        "timer",
        "toolbar",
        "tooltip",
        "tree",
        "treegrid",
        "treeitem",
    }
)  # noqa: E501

# The WAI-ARIA 1.2 state/property vocabulary (`aria-*` attribute names).
_KNOWN_ARIA_ATTRIBUTES = frozenset(
    {
        "aria-activedescendant",
        "aria-atomic",
        "aria-autocomplete",
        "aria-busy",
        "aria-checked",
        "aria-colcount",
        "aria-colindex",
        "aria-colspan",
        "aria-controls",
        "aria-current",
        "aria-describedby",
        "aria-details",
        "aria-disabled",
        "aria-dropeffect",
        "aria-errormessage",
        "aria-expanded",
        "aria-flowto",
        "aria-grabbed",
        "aria-haspopup",
        "aria-hidden",
        "aria-invalid",
        "aria-keyshortcuts",
        "aria-label",
        "aria-labelledby",
        "aria-level",
        "aria-live",
        "aria-modal",
        "aria-multiline",
        "aria-multiselectable",
        "aria-orientation",
        "aria-owns",
        "aria-placeholder",
        "aria-posinset",
        "aria-pressed",
        "aria-readonly",
        "aria-relevant",
        "aria-required",
        "aria-roledescription",
        "aria-rowcount",
        "aria-rowindex",
        "aria-rowspan",
        "aria-selected",
        "aria-setsize",
        "aria-sort",
        "aria-valuemax",
        "aria-valuemin",
        "aria-valuenow",
        "aria-valuetext",
    }
)  # noqa: E501


# frob:doc docs/modules/webapp-a11y-structure.md#a11yfilecontext
@dataclass(frozen=True)
class A11yFileContext:
    """One already-parsed file, as `frob.gates._a11y_gate.a11y_gate` hands
    it to every discovered `a11y_findings` hook -- `file` (repo-relative
    POSIX path, for `Violation.file`), `language` (a
    `frob.webapp._a11y_substrate`-supported label), `source` (raw file
    bytes), and `root` (the file's tree-sitter root `Node`). Parsed once
    by the gate and shared across every hook module so no individual A11Y
    rule module re-parses the same file (module docstring).

    frob:ticket T-5323
    """

    file: str
    language: str
    source: bytes
    root: Node


def _accessible_name(attrs: dict[str, str], text: str) -> str:
    """The best-effort accessible name for an element: `aria-label` wins
    over visible text (matches the browser accname computation's own
    precedence for the one-of-several sources this module checks)."""
    return attrs.get("aria-label", "").strip() or text.strip()


def _is_identity_field(tag: str, attrs: dict[str, str]) -> bool:
    """Whether a form-control element is an identity-autofill candidate
    A11Y112 requires `autocomplete` on (SC 1.3.5)."""
    if tag != "input":
        return False
    input_type = attrs.get("type", "text").lower()
    name = attrs.get("name", "").lower()
    if input_type in _IDENTITY_INPUT_TYPES and input_type != "text":
        return True
    return any(hint in name for hint in _IDENTITY_NAME_HINTS)


def _rule101_missing_alt(ctx: A11yFileContext) -> list[Violation]:
    """A11Y101: `<img>` with no `alt` attribute (SC 1.1.1)."""
    result = elements_missing_attribute(
        ctx.root, ctx.language, ctx.source, _ALT_REQUIRED_TAGS, "alt"
    )
    if result.is_err:
        return []
    return [
        Violation(
            rule="A11Y101",
            severity=Severity.WARN,
            file=ctx.file,
            line=match.span[0],
            message=(
                f"A11Y101: {ctx.file}:{match.span[0]} <{match.tag}> has no "
                f'`alt` attribute -- add `alt="..."` describing the image '
                f'(or `alt=""` if it is purely decorative)'
            ),
        )
        for match in result.danger_ok
    ]


def _rule102_svg_missing_name(ctx: A11yFileContext) -> list[Violation]:
    """A11Y102: `<svg role="img">` with no accessible name (SC 1.1.1)."""
    result = elements_with_attribute(
        ctx.root, ctx.language, ctx.source, frozenset({"svg"}), "role"
    )
    if result.is_err:
        return []
    violations = []
    for match in result.danger_ok:
        if match.attributes.get("role") != "img":
            continue
        if match.attributes.get("aria-label") or match.attributes.get(
            "aria-labelledby"
        ):
            continue
        violations.append(
            Violation(
                rule="A11Y102",
                severity=Severity.WARN,
                file=ctx.file,
                line=match.span[0],
                message=(
                    f'A11Y102: {ctx.file}:{match.span[0]} <svg role="img"> '
                    f'has no accessible name -- add `aria-label="..."` or '
                    f'`aria-labelledby="..."`'
                ),
            )
        )
    return violations


def _rule103_104_headings(ctx: A11yFileContext) -> list[Violation]:
    """A11Y103 (skipped heading level) and A11Y104 (more than one `h1`),
    SC 1.3.1."""
    result = heading_sequence(ctx.root, ctx.language, ctx.source)
    if result.is_err:
        return []
    headings = result.danger_ok
    violations: list[Violation] = []
    h1_count = sum(1 for h in headings if h.level == 1)
    if h1_count > 1:
        first_extra = [h for h in headings if h.level == 1][1]
        violations.append(
            Violation(
                rule="A11Y104",
                severity=Severity.WARN,
                file=ctx.file,
                line=first_extra.span[0],
                message=(
                    f"A11Y104: {ctx.file}:{first_extra.span[0]} a second "
                    f"<h1> ({h1_count} total) -- a page must have exactly "
                    f"one top-level heading"
                ),
            )
        )
    previous_level = 0
    for heading in headings:
        if previous_level and heading.level > previous_level + 1:
            violations.append(
                Violation(
                    rule="A11Y103",
                    severity=Severity.WARN,
                    file=ctx.file,
                    line=heading.span[0],
                    message=(
                        f"A11Y103: {ctx.file}:{heading.span[0]} heading level "
                        f"jumps from h{previous_level} to h{heading.level} -- "
                        f"do not skip heading levels"
                    ),
                )
            )
        previous_level = heading.level
    return violations


def _rule105_title(ctx: A11yFileContext) -> list[Violation]:
    """A11Y105: `<title>` missing or empty (SC 2.4.2). html-family only --
    a jsx fragment has no document `<title>` of its own."""
    result = all_elements(ctx.root, ctx.language, ctx.source)
    if result.is_err:
        return []
    titles = [m for m in result.danger_ok if m.tag == "title"]
    head_present = any(m.tag == "head" for m in result.danger_ok)
    if not head_present:
        # No <head> in this file at all -- e.g. a partial/fragment
        # template -- not this rule's concern.
        return []
    if not titles:
        return [
            Violation(
                rule="A11Y105",
                severity=Severity.WARN,
                file=ctx.file,
                line=1,
                message=(
                    f"A11Y105: {ctx.file}:1 no <title> element -- every "
                    f"page needs a descriptive, non-empty <title>"
                ),
            )
        ]
    return []


def _rule107_empty_lang(ctx: A11yFileContext) -> list[Violation]:
    """A11Y107: `<html lang="">` present but empty (SC 3.1.1)."""
    result = html_lang(ctx.root, ctx.language, ctx.source)
    if result.is_err:
        return []
    lang = result.danger_ok
    if lang is None:
        return []
    if lang == "":
        return [
            Violation(
                rule="A11Y107",
                severity=Severity.WARN,
                file=ctx.file,
                line=1,
                message=(
                    f'A11Y107: {ctx.file}:1 <html lang=""> is empty -- set '
                    f'it to a real BCP-47 language tag, e.g. "en"'
                ),
            )
        ]
    return []


def _rule106_missing_lang(ctx: A11yFileContext) -> list[Violation]:
    """A11Y106: `<html>` present with no `lang` attribute at all."""
    result = elements_missing_attribute(
        ctx.root, ctx.language, ctx.source, frozenset({"html"}), "lang"
    )
    if result.is_err:
        return []
    return [
        Violation(
            rule="A11Y106",
            severity=Severity.WARN,
            file=ctx.file,
            line=match.span[0],
            message=(
                f"A11Y106: {ctx.file}:{match.span[0]} <html> has no `lang` "
                f'attribute -- add `lang="en"` (or the page\'s real language)'
            ),
        )
        for match in result.danger_ok
    ]


def _rule108_109_110_accessible_names(ctx: A11yFileContext) -> list[Violation]:
    """A11Y108/A11Y109 (no accessible name) and A11Y110 (generic
    accessible name), SC 2.4.4, over `<a>` and `<button>`."""
    result = all_elements(ctx.root, ctx.language, ctx.source)
    if result.is_err:
        return []
    violations: list[Violation] = []
    for match in result.danger_ok:
        if match.tag not in _LINK_TAGS and match.tag not in _BUTTON_TAGS:
            continue
        text = _text_of_match(ctx, match)
        name = _accessible_name(match.attributes, text)
        rule = "A11Y108" if match.tag in _LINK_TAGS else "A11Y109"
        label = "<a>" if match.tag in _LINK_TAGS else "<button>"
        if not name:
            violations.append(
                Violation(
                    rule=rule,
                    severity=Severity.WARN,
                    file=ctx.file,
                    line=match.span[0],
                    message=(
                        f"{rule}: {ctx.file}:{match.span[0]} {label} has no "
                        f"accessible name -- add visible text, `aria-label`, "
                        f"or `aria-labelledby`"
                    ),
                )
            )
        elif name.lower() in _GENERIC_ACCESSIBLE_NAMES:
            violations.append(
                Violation(
                    rule="A11Y110",
                    severity=Severity.WARN,
                    file=ctx.file,
                    line=match.span[0],
                    message=(
                        f"A11Y110: {ctx.file}:{match.span[0]} {label} "
                        f'accessible name "{name}" is generic -- use text '
                        f"that describes the link/button's destination or "
                        f"action out of context"
                    ),
                )
            )
    return violations


def _text_of_match(ctx: A11yFileContext, match: ElementMatch) -> str:
    """Best-effort text content for `match`, re-derived from its own
    source span (`all_elements` only returns the element's own attribute
    map, not its rendered text) -- a plain byte slice is enough here since
    this only feeds a case-insensitive generic-phrase comparison, never a
    structural decision."""
    start_line, end_line = match.span
    lines = ctx.source.decode("utf-8", errors="ignore").splitlines()
    if start_line - 1 >= len(lines):
        return ""
    span_text = "\n".join(lines[start_line - 1 : end_line])
    # Strip the opening/closing tag markup crudely -- good enough to
    # compare against the short generic phrases this rule flags.
    stripped = re.sub(r"<[^>]*>", " ", span_text)
    return " ".join(stripped.split())


def _rule111_unlabeled_inputs(ctx: A11yFileContext) -> list[Violation]:
    """A11Y111: a form control with no associated label."""
    result = all_elements(ctx.root, ctx.language, ctx.source)
    if result.is_err:
        return []
    elements = result.danger_ok
    label_fors = {
        m.attributes.get("for")
        for m in elements
        if m.tag == "label" and m.attributes.get("for")
    }
    violations = []
    for match in elements:
        if match.tag not in _FORM_CONTROL_TAGS:
            continue
        if match.attributes.get("type", "").lower() in ("hidden", "submit", "button"):
            continue
        has_label = (
            match.attributes.get("id") in label_fors
            or bool(match.attributes.get("aria-label"))
            or bool(match.attributes.get("aria-labelledby"))
        )
        if not has_label:
            violations.append(
                Violation(
                    rule="A11Y111",
                    severity=Severity.WARN,
                    file=ctx.file,
                    line=match.span[0],
                    message=(
                        f"A11Y111: {ctx.file}:{match.span[0]} <{match.tag}> "
                        f"has no associated label -- add a `<label for=...>`, "
                        f"`aria-label`, or `aria-labelledby`"
                    ),
                )
            )
    return violations


def _rule112_missing_autocomplete(ctx: A11yFileContext) -> list[Violation]:
    """A11Y112: identity-autofill input missing `autocomplete` (SC 1.3.5)."""
    result = all_elements(ctx.root, ctx.language, ctx.source)
    if result.is_err:
        return []
    violations = []
    for match in result.danger_ok:
        if not _is_identity_field(match.tag, match.attributes):
            continue
        if "autocomplete" in match.attributes:
            continue
        violations.append(
            Violation(
                rule="A11Y112",
                severity=Severity.WARN,
                file=ctx.file,
                line=match.span[0],
                message=(
                    f"A11Y112: {ctx.file}:{match.span[0]} identity input "
                    f"<{match.tag}> has no `autocomplete` attribute -- set "
                    f'it to the matching token, e.g. `autocomplete="email"`'
                ),
            )
        )
    return violations


def _rule113_duplicate_ids(ctx: A11yFileContext) -> list[Violation]:
    """A11Y113: the same `id` attribute value used more than once."""
    result = all_elements(ctx.root, ctx.language, ctx.source)
    if result.is_err:
        return []
    seen: dict[str, ElementMatch] = {}
    violations = []
    for match in result.danger_ok:
        element_id = match.attributes.get("id")
        if not element_id:
            continue
        if element_id in seen:
            violations.append(
                Violation(
                    rule="A11Y113",
                    severity=Severity.WARN,
                    file=ctx.file,
                    line=match.span[0],
                    message=(
                        f'A11Y113: {ctx.file}:{match.span[0]} id="{element_id}" '
                        f"is already used at line {seen[element_id].span[0]} -- "
                        f"`id` values must be unique per document"
                    ),
                )
            )
        else:
            seen[element_id] = match
    return violations


def _rule114_115_invalid_aria(ctx: A11yFileContext) -> list[Violation]:
    """A11Y114 (unrecognized `role`) and A11Y115 (unrecognized `aria-*`
    attribute name)."""
    result = all_elements(ctx.root, ctx.language, ctx.source)
    if result.is_err:
        return []
    violations = []
    for match in result.danger_ok:
        role = match.attributes.get("role")
        if role and role.lower() not in _KNOWN_ARIA_ROLES:
            violations.append(
                Violation(
                    rule="A11Y114",
                    severity=Severity.WARN,
                    file=ctx.file,
                    line=match.span[0],
                    message=(
                        f'A11Y114: {ctx.file}:{match.span[0]} role="{role}" '
                        f"is not a recognized ARIA role -- see the WAI-ARIA "
                        f"1.2 role list"
                    ),
                )
            )
        for attr_name in match.attributes:
            if not attr_name.startswith("aria-"):
                continue
            if attr_name.lower() not in _KNOWN_ARIA_ATTRIBUTES:
                violations.append(
                    Violation(
                        rule="A11Y115",
                        severity=Severity.WARN,
                        file=ctx.file,
                        line=match.span[0],
                        message=(
                            f"A11Y115: {ctx.file}:{match.span[0]} "
                            f"`{attr_name}` is not a recognized ARIA state "
                            f"or property"
                        ),
                    )
                )
    return violations


# frob:doc docs/modules/webapp-a11y-structure.md#a11y_findings
# frob:ticket T-5323
def a11y_findings(
    ctx: A11yFileContext, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """A11Y101-115 over one already-parsed file (module docstring). The
    `frob.gates._a11y_gate.a11y_gate` discovery hook every
    `frob.webapp._a11y_*` module implements to opt into the A11Y gate
    (T-5323) -- `frameworks` is accepted for parity with the other
    WEBSEC/COMPLY/SEO family hooks and the gate's own no-framework
    short-circuit, unused by these rules directly since document
    structure/labeling applies to any html-family or jsx-family markup
    regardless of which framework produced it.
    """
    if not frameworks:
        _log.debug("a11y_findings: no framework detected, skipping %s", ctx.file)
        return ()
    violations: list[Violation] = []
    violations.extend(_rule101_missing_alt(ctx))
    violations.extend(_rule102_svg_missing_name(ctx))
    violations.extend(_rule103_104_headings(ctx))
    violations.extend(_rule105_title(ctx))
    violations.extend(_rule106_missing_lang(ctx))
    violations.extend(_rule107_empty_lang(ctx))
    violations.extend(_rule108_109_110_accessible_names(ctx))
    violations.extend(_rule111_unlabeled_inputs(ctx))
    violations.extend(_rule112_missing_autocomplete(ctx))
    violations.extend(_rule113_duplicate_ids(ctx))
    violations.extend(_rule114_115_invalid_aria(ctx))
    _log.info("a11y_findings: %d violation(s) in %s", len(violations), ctx.file)
    return tuple(violations)
