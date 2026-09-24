"""Accessibility-statement page content-lint.

docs/modules/gates.md#accessibility-statement-content-lint-a11y107-a11y114-t-5324

# frob:ticket T-5324
# frob:ticket T-5454

The W3C WAI "Developing an Accessibility Statement" guidance names eight
things a conformant accessibility-statement page states: an explicit
COMMITMENT to accessibility, the STANDARD it targets (WCAG 2.2 level AA
for this repo's own posture), a CONTACT channel for feedback, any known
LIMITATIONS, the MEASURES taken, the TECHNICAL prerequisites a visitor
needs, and the TESTED ENVIRONMENTS it was verified against -- plus the
page's own PRESENCE, which is a precondition for linting any of the rest.

GATE HOOK SHAPE (T-5323, T-5454 rework): `frob.gates._a11y_gate.a11y_gate`
walks every git-tracked html-family/jsx-family file ONCE, parses it ONCE,
and hands each discovered `frob.webapp._a11y_*` hook module the SAME
already-parsed `frob.webapp._a11y_structure.A11yFileContext` (`file`,
`language`, `source`, `root` node) plus the repo's `detect_frameworks`
result -- ONE file, one call, no filesystem access of its own (same
"GATE HOOK SHAPE" contract `_a11y_forms_contrast.py`'s own docstring
names). `a11y_findings` below matches that exact hook shape (`ctx,
frameworks`), NOT this module's earlier T-5324 `(root, frameworks)`
sketch, which crashed `a11y_gate` with a `TypeError` on every framework-
detected repo (T-5454's own ticket body) -- the gate never had a
filesystem `root: Path` to hand any hook, only ever `ctx`.

STATEMENT-PAGE DETECTION IS NOW PER-FILE, NOT A SEPARATE REPO WALK: since
`ctx.file` (a repo-relative POSIX path) is the only path information a
hook ever sees, `_is_statement_page` below answers "IS this particular
file the accessibility-statement page for one of `frameworks`" against
the SAME narrow candidate-path table T-5324 built (accessibility only,
never re-implementing `frob.webapp._comply_substrate`'s full required-
page route tables, which live outside this ticket's scope) -- when
`ctx.file` matches, this file IS the statement page and the seven W3C WAI
section checks (A11Y125-A11Y128) run directly against `ctx.source`.

"NO STATEMENT PAGE EXISTS AT ALL" IS A DELIBERATELY DROPPED KNOWN GAP
(same shape `_a11y_forms_contrast.py`'s own "CONTRAST'S KNOWN GAP"
documents): that precondition needs a REPO-LEVEL answer no single `ctx`
call can give on its own -- the hook contract never hands any hook an
absolute repo root, only a relative `ctx.file` per already-tracked file.
An earlier T-5454 revision approximated the repo root as `Path.cwd()`
and memoized the answer per `frameworks` value; that approximation is
UNSAFE in exactly the way this module now avoids -- any caller (a
sibling A11Y hook's own test, a `frob check` invocation whose cwd is not
the scanned `root`) that runs `a11y_gate` without `cwd == root` got a
FALSE "no statement page" finding attached to an unrelated file, which
measurably broke `tests/unit/test_webapp_a11y_structure.py`'s own
gate-integration test the first time this module was wired in. A false
positive polluting an unrelated file's violation list is worse than the
false negative of never detecting a wholly absent statement page, so
`a11y_findings` below only ever fires on the statement page's OWN file
match; `_locate_statement_page` is kept as an explicit-root helper for
direct callers/tests, never called from the hook itself. Widening the
hook contract to carry an absolute root is out of this ticket's scope
(`src/frob/gates/_a11y_gate.py` is explicitly off-limits, per T-5454's
own ticket body) and is the real fix for a future ticket to pick up.

Same shallow-sniff posture as `frob.webapp._comply_substrate` (T-5360)
and `frob.webapp._detect` (T-5302): a false negative (a statement that is
actually complete but phrased in words this lint's needles miss) is
cheaper to live with than a fragile NLP-grade content classifier, and a
plain-substring check is one a repo owner can read and predict.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind

if TYPE_CHECKING:
    from frob.webapp._a11y_structure import A11yFileContext

_log = get_logger(__name__)

__all__ = ["a11y_findings"]

# A11Y125-A11Y128 (module docstring/`_STATEMENT_SECTIONS` comment): the
# only ids left in the A11Y101-135 reserved block (docs/modules/gates.md,
# T-5301) once `_a11y_structure.py` (A11Y101-115), `_a11y_interaction.py`
# (A11Y116-124), and `_a11y_forms_contrast.py` (A11Y129-135) are all
# accounted for.

# Candidate accessibility-statement page paths (relative to repo root),
# keyed off the already-detected `FrameworkKind` -- same file-based-router
# idiom `_comply_substrate._FILE_ROUTE_CANDIDATES` uses, narrowed to just
# the accessibility page (this ticket's own scope) AND to extensions
# `frob.gates._a11y_gate`'s own file walk actually covers (`.html`/`.htm`/
# `.vue`/`.jsx`/`.tsx`) -- a config-based router's route-config file
# (`urls.py`, `config/routes.rb`, ...) is never `.html`/`.jsx`/`.vue`, so
# `a11y_gate` never hands this hook a `ctx` for one at all; T-5324's
# original content-route-file candidates are dropped here as dead code
# under the real per-file gate contract, not silently -- see this
# module's own docstring.
# frob:ticket T-5454
_STATEMENT_PAGE_CANDIDATES: dict[FrameworkKind, tuple[str, ...]] = {
    FrameworkKind.NEXTJS: (
        "pages/accessibility.js",
        "pages/accessibility.tsx",
        "app/accessibility/page.tsx",
        "app/accessibility/page.js",
    ),
    FrameworkKind.SVELTEKIT: ("src/routes/accessibility/+page.svelte",),
    FrameworkKind.ASTRO: ("src/pages/accessibility.astro",),
    FrameworkKind.VITE: ("src/pages/Accessibility.jsx", "src/pages/Accessibility.tsx"),
}


def _is_statement_page(rel_path: str, frameworks: frozenset[FrameworkKind]) -> bool:
    """True if `rel_path` (a `ctx.file`-shaped repo-relative POSIX path)
    is one of `frameworks`' known accessibility-statement page candidates.

    frob:ticket T-5454
    """
    return any(
        rel_path in _STATEMENT_PAGE_CANDIDATES.get(kind, ()) for kind in frameworks
    )


def _locate_statement_page(root: Path, frameworks: frozenset[FrameworkKind]) -> bool:
    """True if `root` has any of `frameworks`' known accessibility-
    statement page candidates on disk -- exposed for direct, explicit-root
    callers/tests only; `a11y_findings` itself never calls this (module
    docstring's "known gap" section: a per-file gate hook has no reliable
    repo root to check against). Not wired into any production caller
    (only this module's own tests use it directly) -- kept as a small,
    explicit-root building block for a future ticket that widens the hook
    contract (module docstring), rather than deleted and rewritten later.

    frob:ticket T-5454
    frob:waive WIRE001 reason="future hook widening" follow_up="T-5454"
    """
    for kind in frameworks:
        for candidate in _STATEMENT_PAGE_CANDIDATES.get(kind, ()):
            if (root / candidate).exists():
                return True
    return False


# frob:ticket T-5324
class _StatementSection:
    """One W3C WAI required accessibility-statement content section: its
    gate rule id, a human label for the violation message, and the
    case-insensitive regex needle(s) `a11y_findings` sniffs the page text
    for -- ANY needle matching counts the section present (same shallow
    either/or-substring posture `_comply_substrate.detect_signals` uses).

    frob:ticket T-5324
    """

    __slots__ = ("rule", "label", "pattern")

    def __init__(self, rule: str, label: str, pattern: str) -> None:
        """Store `rule`/`label` verbatim and compile `pattern` once
        (case-insensitive) -- `a11y_findings` runs this section's check
        once per lint, so a pre-compiled pattern avoids re-compiling the
        same regex per call.

        frob:ticket T-5324
        """
        self.rule = rule
        self.label = label
        self.pattern = re.compile(pattern, re.IGNORECASE)


# The seven W3C WAI "Developing an Accessibility Statement" required
# content sections. Only A11Y125-A11Y128 (four ids) remained free when this
# ticket landed: `_a11y_structure.py` claims A11Y101-115, and
# `_a11y_interaction.py` (a sibling T-5140 leaf that landed on `dev` WHILE
# this ticket was in flight) claims A11Y116-A11Y124 -- the exact band this
# module's first T-5454 revision picked, a second silent collision this
# consolidation fixes. Four ids is not enough for one-id-per-section, so
# each id below covers a small, related PAIR of sections instead (message
# text still names the exact missing section) -- functional coverage
# (all seven sections still individually checked and individually
# reported) is preserved; only the id GRANULARITY narrows from
# one-rule-per-section to one-rule-per-pair.
# frob:ticket T-5454
_STATEMENT_SECTIONS: tuple[_StatementSection, ...] = (
    _StatementSection(
        "A11Y125",
        "commitment to accessibility",
        r"committed to|commitment to accessib|our commitment",
    ),
    _StatementSection(
        "A11Y125",
        "conformance standard applied (WCAG 2.2 AA)",
        r"wcag\s*2\.2.{0,40}(level\s*)?aa|aa.{0,40}wcag\s*2\.2",
    ),
    _StatementSection(
        "A11Y126",
        "feedback/contact channel",
        r"contact us|feedback|reach out|email us",
    ),
    _StatementSection(
        "A11Y126",
        "known limitations",
        r"known limitation|not (?:yet |fully )?accessible|non-?compliant",
    ),
    _StatementSection(
        "A11Y127",
        "measures taken",
        r"measures (?:we|taken|to)|steps (?:we|taken)|we have taken",
    ),
    _StatementSection(
        "A11Y127",
        "technical prerequisites",
        r"technical(?:ly)? (?:prerequisite|requirement)|requires? (?:javascript"
        r"|a modern browser)",
    ),
    _StatementSection(
        "A11Y128",
        "tested environments",
        r"tested (?:with|on|using)|tested environment|assistive technolog",
    ),
)


def _section_findings(rel_path: str, text: str) -> tuple[Violation, ...]:
    """One `Violation` per `_STATEMENT_SECTIONS` entry whose needle
    pattern does not match `text` (the statement page's own decoded
    source) -- `rel_path` is the statement page's own `ctx.file`.

    frob:ticket T-5454
    """
    findings = [
        Violation(
            rule=section.rule,
            severity=Severity.ERROR,
            file=rel_path,
            line=1,
            message=(
                f"accessibility statement is missing its {section.label} "
                "section (W3C WAI accessibility statement guidance)"
            ),
        )
        for section in _STATEMENT_SECTIONS
        if not section.pattern.search(text)
    ]
    return tuple(findings)


# frob:doc docs/modules/gates.md#accessibility-statement-content-lint-a11y107-a11y114-t-5324  # noqa: E501
def a11y_findings(
    ctx: A11yFileContext, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """The accessibility-statement content-lint findings for one already-
    parsed `ctx` (module docstring's "GATE HOOK SHAPE" note) -- the hook
    `frob.gates._a11y_gate.a11y_gate` (T-5323) discovers and calls once
    per git-tracked html-family/jsx-family file it walks.

    When `ctx.file` IS one of `frameworks`' known accessibility-statement
    page candidates, returns one `Violation` per missing W3C WAI content
    section (`_STATEMENT_SECTIONS`). For every OTHER file, returns `()` --
    this hook deliberately never reports "no statement page exists
    anywhere in this repo at all" (module docstring's "known gap"
    section: an earlier `Path.cwd()`-approximated version of that check
    was removed after it measurably fired a false positive on every OTHER
    A11Y hook's own gate test, since a per-file hook has no reliable repo
    root to check "nowhere in this repo" against -- a false positive that
    corrupts an unrelated file's violation list is worse than the false
    negative of never detecting a wholly absent statement page).

    Short-circuits to `()` when `frameworks` is empty -- the gate has
    already run `frob.webapp._detect.detect_frameworks(root)` once and
    passes the result in; this module never re-detects frameworks itself
    (T-5302's contract).

    frob:ticket T-5324
    frob:ticket T-5454
    """
    if not frameworks:
        _log.debug("a11y_statement: no frameworks detected, skipping %s", ctx.file)
        return ()

    if not _is_statement_page(ctx.file, frameworks):
        return ()

    text = ctx.source.decode("utf-8", errors="ignore")
    findings = _section_findings(ctx.file, text)
    _log.debug("a11y_findings: %d finding(s) for %s", len(findings), ctx.file)
    return findings
