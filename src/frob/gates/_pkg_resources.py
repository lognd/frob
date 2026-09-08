# frob:waive REF002 reason="single-anchor by design, wired only from run_gates's \
# dispatch table -- see T-4219 for the full justification"
"""frob.gates._pkg_resources -- PKG001/PKG002/PKG003 (T-4219): a relative
embedded-resource reference in markdown breaks on a renderer with no
repository context.

WHY THIS EXISTS. The package index (PyPI, and any index like it) renders a
project's declared long-description file with no repository context at all
-- a relative `src="docs/assets/banner.svg"` has nothing to resolve against
there, so it renders as a broken-image box on the one surface most people
meet the project through for the first time. This repo's own README hit
exactly that (T-4219): its banner image used a repository-relative path,
which resolves fine on the forge and renders broken on the index. The forge
and the index disagree, and nothing before this gate could tell the two
apart.

SCOPE, NARROWED BY THE OWNER MID-TICKET (T-4219's own body is the record):
this gate flags embedded RESOURCES only -- an image source, in HTML `<img
src=...>` or markdown `![alt](src)` form -- never link targets. A relative
link that does not navigate on the index is a minor inconvenience and a
common, deliberate convention (a link to a repository file, a relative
`#anchor`); flagging it would be noise on nearly every project. A relative
IMAGE renders as a visibly broken box, which is the only case worth an
error. `strip_code_spans` (frob.gates._markdown_scan) exempts illustrative
examples inside code spans/fences from all three rules the same way every
other prose-scanning gate does.

THREE RULES:

  PKG001  ERROR    a relative image source in the file the project manifest
                    declares as its long description (`[project].readme` in
                    pyproject.toml, string or `{file = ...}` table form).
  PKG002  WARN     the same finding in any OTHER tracked markdown file --
                    still worth flagging (some other renderer might serve it
                    with no repository context too) but never a hard gate,
                    since most non-declared docs are read on the forge only.
  PKG003  UNRESOLVED  the project declares no long-description file at all
                    (no `[project].readme` key, or a `pyproject.toml` this
                    reader cannot parse) -- an explicit "cannot say" outcome
                    rather than a silent pass, per this repo's own doctrine
                    that a check must never let "found nothing to check"
                    read the same as "checked, found nothing" (Severity's
                    own UNRESOLVED docstring, `frob.findings`).

The remedy this gate's own message states is an ABSOLUTE URL naming a host,
owner, repo, and branch -- four facts the gate cannot invent (T-4219: "a
naive auto-fix would guess them"). When `[project.urls]` already declares a
`Homepage`/`Repository`/`Source` pointing at a recognized forge, the message
derives and shows the concrete raw-content URL; otherwise it states only the
remedy's SHAPE, never fabricating a host/owner/repo/branch it cannot read
from the manifest. Either way the message notes that pinning a branch name
means the asset moves if the branch is later renamed -- a tradeoff for the
project author to accept explicitly, not a silent gate choice."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from frob.gates._doclink_docanchor import _line_index
from frob.gates._markdown_scan import strip_code_spans as _strip_code_spans
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:ticket T-4219
# A markdown image (`![alt](target)`), capturing the target so a fragment-
# only or absolute one can be told apart from a relative one. Deliberately
# does NOT match a plain link (`[text](target)` with no leading `!`) --
# links are out of scope entirely per the owner's narrowed request.
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\s*\)")

# frob:ticket T-4219
# An HTML `<img src="...">` (or `<img ... src='...'>`) tag -- README banners
# in this repo's own ecosystem commonly use the HTML form (for `width=`/
# `align=` attributes markdown image syntax cannot express), so a scan that
# only understood markdown image syntax would miss the exact case T-4219
# was filed over.
_HTML_IMG_SRC_RE = re.compile(
    r"<img\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE
)

# frob:ticket T-4219
# A URL scheme prefix (`https:`, `http:`, `data:`, ...) or a protocol-
# relative reference (`//host/...`) -- either means the target is already
# absolute and out of scope for this gate no matter which regex matched it.
_ABSOLUTE_TARGET_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.\-]*:|//)")


# frob:ticket T-4219
def _is_relative_resource_target(target: str) -> bool:
    """`True` if `target` (an image `src`) is a repository-relative path
    that will not resolve where the document is rendered without
    repository context -- `False` for an absolute URL, a protocol-relative
    reference, or a bare fragment (`#foo`, which is a link concern, not an
    embedded-resource one, and cannot appear as an image `src` in practice
    but is excluded defensively)."""
    target = target.strip()
    if not target or target.startswith("#"):
        return False
    return not _ABSOLUTE_TARGET_RE.match(target)


# frob:ticket T-4219
def _scan_markdown_for_relative_images(text: str) -> list[tuple[int, str]]:
    """Every `(1-based line, target)` pair for a relative embedded-image
    reference in `text` (markdown `![]()` or HTML `<img src=...>`), code
    spans/fences already blanked by the caller so an illustrative example
    never fires."""
    line_of = _line_index(text)
    findings: list[tuple[int, str]] = []
    for regex in (_MD_IMAGE_RE, _HTML_IMG_SRC_RE):
        for match in regex.finditer(text):
            target = match.group(1)
            if _is_relative_resource_target(target):
                findings.append((line_of(match.start()), target))
    findings.sort()
    return findings


# frob:ticket T-4219
# frob:waive EXHAUST003 reason="resolution-coverage gap on tomllib.load, same shape as \
# frob.gates.__init__._pyproject_project_field's own T-1402 waiver"
def _pyproject_readme_file(root: Path) -> str | None:
    """The path (relative to `root`) of the file `[project].readme` names
    in `root/pyproject.toml`, handling both the plain-string form
    (`readme = "README.md"`) and the PEP 621 table form (`readme = {file =
    "README.md", content-type = "..."}`) -- `None` if the manifest is
    missing/unparseable or declares no `readme` key at all, which the
    caller (`pkg_resources_gate`) turns into the explicit PKG003
    unresolved outcome rather than silently skipping the check."""
    toml_path = root / "pyproject.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    readme = data.get("project", {}).get("readme")
    if isinstance(readme, str):
        return readme
    if isinstance(readme, dict):
        file_field = readme.get("file")
        if isinstance(file_field, str):
            return file_field
    return None


# frob:ticket T-4219
_FORGE_RAW_URL_TEMPLATES = {
    "github.com": "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}",
    "gitlab.com": "https://gitlab.com/{owner}/{repo}/-/raw/{branch}/{path}",
}

# frob:ticket T-4219
_FORGE_URL_RE = re.compile(
    r"^https?://(?P<host>github\.com|gitlab\.com)/(?P<owner>[^/]+)/(?P<repo>[^/]+?)"
    r"(?:\.git)?/?$"
)


# frob:ticket T-4219
# frob:waive EXHAUST003 reason="resolution-coverage gap on tomllib.load, same shape as \
# frob.gates.__init__._pyproject_project_field's own T-1402 waiver"
def _pyproject_repo_url(root: Path) -> str | None:
    """`[project.urls]`'s `Homepage`/`Repository`/`Source` value from
    `root/pyproject.toml`, whichever is present first, or `None` -- used
    only to DERIVE a concrete raw-content URL for the remedy message when
    the manifest already states one; never guessed when absent."""
    toml_path = root / "pyproject.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    urls = data.get("project", {}).get("urls")
    if not isinstance(urls, dict):
        return None
    for key in ("Repository", "Source", "Homepage"):
        value = urls.get(key)
        if isinstance(value, str) and value:
            return value
    return None


# frob:ticket T-4219
def _remedy_message(root: Path, target: str) -> str:
    """The PKG001/PKG002 message's remedy clause: a concrete raw-content
    URL derived from `[project.urls]` when the manifest names a recognized
    forge (github.com/gitlab.com) repository, or -- when it doesn't --
    only the remedy's SHAPE, per T-4219's explicit instruction that a
    naive auto-fix must never guess a host/owner/repo/branch it cannot
    read from the manifest. Either branch notes the branch-pinning
    tradeoff (the asset moves if that branch is later renamed) so it is a
    decision the project author makes, not one this gate makes silently."""
    repo_url = _pyproject_repo_url(root)
    branch_note = (
        "pinning a branch name means this link moves if that branch is later renamed"
    )
    if repo_url:
        match = _FORGE_URL_RE.match(repo_url.strip())
        if match:
            template = _FORGE_RAW_URL_TEMPLATES[match.group("host")]
            raw_url = template.format(
                owner=match.group("owner"),
                repo=match.group("repo"),
                branch="main",
                path=target.lstrip("/"),
            )
            return (
                f"replace {target!r} with an absolute URL so it resolves with no "
                f"repository context, e.g. {raw_url!r} (derived from "
                f"[project.urls] in pyproject.toml, branch guessed as 'main' -- "
                f"{branch_note})"
            )
    return (
        f"replace {target!r} with an absolute URL naming a host, owner, "
        f"repository, and branch (e.g. a raw-content URL on the project's "
        f"forge) -- pyproject.toml declares no [project.urls] entry this "
        f"gate can derive one from, so state the URL explicitly; {branch_note}"
    )


# frob:ticket T-4219
def _violations_for_doc(
    root: Path, doc_rel: str, *, severity: Severity, rule: str
) -> list[Violation]:
    """Every PKG001/PKG002 `Violation` for relative embedded-image
    references in `root/doc_rel`, at the given `rule`/`severity`."""
    text = (root / doc_rel).read_text(encoding="utf-8", errors="replace")
    text = _strip_code_spans(text)
    violations = []
    for line, target in _scan_markdown_for_relative_images(text):
        violations.append(
            Violation(
                rule=rule,
                severity=severity,
                file=doc_rel,
                line=line,
                message=(
                    f"{rule}: {doc_rel}:{line} embeds {target!r} as an image "
                    f"source using a repository-relative path -- a renderer "
                    f"with no repository context (a package index rendering "
                    f"the long description, for instance) shows this as a "
                    f"broken image; {_remedy_message(root, target)}"
                ),
            )
        )
    return violations


# frob:ticket T-4219
def _pkg003_violation(root: Path) -> Violation:
    """PKG003: the project declares no `[project].readme` (or
    `pyproject.toml` itself is unreadable) -- reported UNRESOLVED rather
    than silently skipping PKG001, so "nothing to check" never reads the
    same as "checked, found nothing" (Severity.UNRESOLVED's own contract,
    `frob.findings`)."""
    return Violation(
        rule="PKG003",
        severity=Severity.UNRESOLVED,
        file="pyproject.toml",
        line=1,
        message=(
            "PKG003: pyproject.toml declares no [project].readme (or is "
            "missing/unparseable) -- PKG001 cannot identify a declared "
            "long-description file to gate, so no image-resource check ran "
            "against one; declare [project].readme if this project has a "
            "long description, or waive PKG003 if it deliberately has none"
        ),
    )


# frob:ticket T-4219
# frob:doc docs/modules/gates.md#rule-catalog
# frob:enforces CHK-GATE-PKG001
# frob:enforces CHK-GATE-PKG002
# frob:enforces CHK-GATE-PKG003
# frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
# frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg001DeclaredLongDescription.test_relative_markdown_image_in_declared_readme_fires_error  # noqa: E501
# frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
# frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg002NonDeclaredMarkdown.test_relative_image_in_other_markdown_warns_not_errors  # noqa: E501
# frob:waive FMT001 reason="single unwrappable frob:tests node id, T-4219"
# frob:tests tests/unit/gates/test_pkg_resources.py::TestPkg003NoDeclaredLongDescription.test_no_readme_key_reports_unresolved_not_a_crash_or_silent_pass  # noqa: E501
def pkg_resources_gate(root: Path) -> tuple[Violation, ...]:
    """PKG001/PKG002/PKG003 (T-4219): a relative embedded-image reference
    in a tracked markdown file mis-renders on a consumer with no
    repository context. ERROR when the file is the manifest's declared
    long description (`[project].readme`), WARN for every other tracked
    `.md` file, UNRESOLVED when no long-description file is declared at
    all. Relative LINK targets are never flagged -- see this module's
    docstring for the owner's explicit narrowing (T-4219)."""
    root = Path(root)
    readme_rel = _pyproject_readme_file(root)
    violations: list[Violation] = []
    if readme_rel is None:
        violations.append(_pkg003_violation(root))
    elif (root / readme_rel).is_file():
        violations.extend(
            _violations_for_doc(
                root, readme_rel, severity=Severity.ERROR, rule="PKG001"
            )
        )
    # frob:waive WALK001 reason="anchored '**/*.md' with explicit dir excludes below, \
    # T-4219 -- see this ticket for the full justification"
    exclude_dirs = {".git", ".venv", "node_modules", ".claude"}
    for md_path in sorted(root.rglob("*.md")):
        if any(part in exclude_dirs for part in md_path.parts):
            continue
        doc_rel = md_path.relative_to(root).as_posix()
        if doc_rel == readme_rel:
            continue
        violations.extend(
            _violations_for_doc(root, doc_rel, severity=Severity.WARN, rule="PKG002")
        )
    _log.info("pkg_resources: readme=%r, %d violation(s)", readme_rel, len(violations))
    return tuple(violations)


__all__ = ["pkg_resources_gate"]
