"""PORT001-PATH/PORT001-IDENT: a gate rule that hardcodes THIS project's
own identity (its package-path prefix, or its own package name used as a
bare path-segment literal) instead of resolving it from the project's
declared config, is itself a finding (T-2388, child of T-2384).

DENOMINATOR RECONCILIATION (2026-08-18, recorded so a future reader does
not re-litigate it): T-2384's body originally read as "22 files
repo-wide / 14 in gates/ contain the exact literal `"src/frob/"`". Two
independently-run greps landed on different numbers -- 3 repo-wide for
the exact 11-character quoted literal `'"src/frob/"'` (closing quote
required immediately), 22 for `'"src/frob/'` (opening quote plus
`src/frob/` with ANY continuation, e.g. `"src/frob/gates/"` also
matches). Both were correct; the epic body's prose just described the
narrower pattern's shape while (unverified) carrying the broader
pattern's number. This module's own AST-based count is a THIRD number,
scoped to `src/frob/gates/**` only -- see `tracked_gate_files` and the
`port_selfcheck_gate: scanned N ...` log line every run emits -- and is
NOT a repo-wide denominator. `_env_var_docs.py`/`_root_asset_dirs.py`
both silently matched NOTHING against a differently-named/laid-out
project (a src-layout repo whose package is `lograder`, not `frob`), the
[[catalogued-is-not-enforced]] failure mode: the gate is present,
listed, and documented, while enforcing nothing off-repo. This module is
the durable meta-check that stops a NEW instance of that same class from
landing silently, the same role LEXCHECK001 (`frob.gates.
_lexical_selfcheck`, T-1662/T-2344) plays for "a gate decides from raw
text with no symref" -- this file mirrors that one's shape deliberately
(allowlisted, AST-scanning, per T-2388's own directive not to invent a
second detector architecture for the same job class).

SCOPE DISCIPLINE (T-2384's coordinator, 2026-08-18): "5" (this module's
own unscoped count against `src/frob/gates/**`) is a true statement about
the scanned subset that becomes a FALSE statement about the repo the
moment it is quoted without its scope -- the silent-zero class from
T-2391 wearing a different hat, a number whose meaning depends on an
unstated denominator. `port_selfcheck_gate` therefore logs its scanned
scope alongside its count on EVERY call, unconditionally (mirroring
RENDER001/WALK001's own "scanned N tracked src/frob .py file(s), M
violation(s)" convention, `_render_lint.py`/`_walk_lint.py`), so the
number can never be read as repo-wide by a caller who only sees the
count. Widening the scanned set past `gates/**` (T-2384's coordinator
found 8 more files repo-wide by the broader pattern: `tickets/_models.py`,
`tickets/_land_merge_zones.py`, `tickets/_new_gate_rule_acceptance.py`,
`app/ticket_runner/_land_cmd.py`, `app/ticket_runner/_new.py`,
`refactor/_repointer.py`, `strata/_packs.py`, `strata/_selfconform.py`)
is deliberately NOT done in T-2388/here -- filed as its own child ticket
with those 8 as the starting set, per the coordinator's explicit
instruction not to widen scope inside this ticket.

T-2405 WIDENING (2026-08-18, this ticket): the "8 more files repo-wide"
list two paragraphs up came from the coordinator's own `git grep` over
the LITERAL PREFIX pattern, not from PORT001's AST detector, and was
seeded only as a starting set to re-verify -- it is NOT this widening's
scope. By the time this ticket ran, T-2466 had already measured and
shipped `frob.gates._detector_scope.DETECTOR_PACKAGE_ROOTS` (`src/frob/
{check,gates,strata,vet}/`) for LEXCHECK001's identical scope problem,
derived by counting `Violation(`-constructing modules per package rather
than guessing; `arch/` was measured and excluded on that same evidence.
PORT001 reuses that SAME declaration (`tracked_gate_files` now filters
with `is_detector_package_file` instead of its old `src/frob/gates/`-only
prefix) rather than inventing a second, separately-drifting scope -- the
exact two-copies-desync failure T-2466's own docstring warns against.
Running PORT001's real AST detector (not a grep) against the
coordinator's 8-file starting set found only 2 of the 8
(`strata/_packs.py`, `strata/_selfconform.py`) even fall inside
`DETECTOR_PACKAGE_ROOTS` -- the other 6 (`tickets/_models.py`,
`tickets/_land_merge_zones.py`, `tickets/_new_gate_rule_acceptance.py`,
`app/ticket_runner/_land_cmd.py`, `app/ticket_runner/_new.py`,
`refactor/_repointer.py`) sit in packages T-2466 measured as containing
zero gate-shaped `Violation(` construction, so they are not part of this
detector's population at all, same reasoning `arch/` was excluded by.
Of the 2 that ARE in scope, only `strata/_selfconform.py` (PORT001-IDENT,
a bare `"frob"` path-segment literal) is a real finding; `strata/
_packs.py` has none. Widening `src/frob/gates/**` (93 tracked files) to
the full `DETECTOR_PACKAGE_ROOTS` set (213 tracked files) added exactly
one new finding beyond that: `vet/_capability_scan.py` (also PORT001-
IDENT). No new PORT001-PATH hits appeared -- the widened scan is a
strict superset of the old one, so the 2 pre-existing PATH hits
(`_env_var_docs.py`, `_root_asset_dirs.py`) still fire unchanged, and the
promotion bar's burn-down target grows by zero PATH-class findings.
`tracked_python_files_for_gate`'s own default pathspec (`git ls-files --
src/frob`) already covers every `DETECTOR_PACKAGE_ROOTS` prefix (they
all sit under `src/frob/`), so no optional pathspec keyword was needed
on that shared helper -- LEXCHECK001 (T-2466) established this same
no-new-keyword reuse first; PORT001 follows the identical pattern rather
than adding a second way to call it.

Detection shape (v1, module-scanning `src/frob/gates/**/*.py`): a string
constant containing THIS repo's own resolved package name as a path
segment, found in one of two AST shapes, each its OWN rule id with its
OWN promotion posture (T-2384's coordinator, 2026-08-18, correcting an
earlier ask to give both a single disposition -- see
`_port001_path_violation`/`_port001_ident_violation` for the full
reasoning):

  (a) PORT001-PATH: `"src/<pkg>/"`-shaped literal passed as the argument
      of a `.startswith(...)` call -- the exact `_env_var_docs.py`/
      `_root_asset_dirs.py` bug shape T-2384 measured. BEHAVIORAL --
      silently matches nothing (or the wrong thing) off-repo. This is
      the class the WARN->ERROR promotion bar applies to, once T-2389's
      burn-down reaches zero.
  (b) PORT001-IDENT: the bare package-name literal (`"frob"`) used as a
      WHOLE `/`-delimited path segment inside a `Tuple`/`List`
      construction or a `JoinedStr` (f-string) constant chunk -- the
      `_pii_structural/_self_match.py`-style tuple-of-literal-path-
      segments shape, generalized past the single `.startswith` call
      shape (a) alone catches. ADVISORY -- most real hits are
      maintainer-facing message text naming this repo's own file for a
      human reader, not path-building logic; misleading at worst, no
      behavior change. Deliberately NOT part of the promotion bar and
      NOT individually waiver-required (an unbounded nag rule gets
      waived wholesale, a lesson this repo has already paid for).

The package name itself is resolved from the scanned repo's own
`pyproject.toml` `[project].name` -- PORT001 does not hardcode "frob" as
the thing it looks for (that would be the exact bug it exists to catch,
one layer up). A repo whose `pyproject.toml` is missing/malformed, or
whose declared name cannot be read, is UNRESOLVED (not a silent skip,
not a clean pass) -- T-2391's fail-loudly doctrine: "cannot determine an
answer" is a different claim than "found nothing".

Whole-FILE finding granularity (not per-function like LEXCHECK001): the
literals this gate flags are as often at module level (a `_SELF_EXCLUDED
_FILES` frozenset, a `_PII_SELF_PATTERN_SUFFIXES` tuple) as inside a
function body, so binding to a single enclosing function is not always
possible -- the same documented exception `_inv003_doc_violations`/
`_inv004_doc_violations` and LARGE001 already carry (LEXCHECK001's own
module docstring cites this same precedent) applies here.

`_ALLOWLIST` is reviewed-with-a-reason, not a structural carve-out (T-2384's
own directive: "an exemption matching the normal case disables the
guard" -- see [[an-exemption-matching-the-normal-case-disables-the-guard]]).
`gates/_pii_structural/_self_match.py` is deliberately, permanently about
THIS repo's own files (a self-match exclusion list for a PII scanner) --
allowlisted by exact relpath with a stated reason, same as LEXCHECK001's
own six entries. `app/_config_meta.py` (a deliberate `project.get("name")
!= "frob"` self-identification check for the version floor) is OUTSIDE
`DETECTOR_PACKAGE_ROOTS` (`app/` never measured as containing a
gate-shaped `Violation(` constructor, T-2466) and so stays out of
PORT001's scanned set even after T-2405's widening -- disclosed here
rather than silently allowlisted for a scope it can never actually
enter. `strata/_compliance.py` (registry DATA, not gate mechanism) DID
enter PORT001's scanned set as of T-2405 (`strata/` is a
`DETECTOR_PACKAGE_ROOTS` member) but scans clean -- no allowlist entry
needed because it produces no hit, not because it is out of scope; if
that ever changes, re-examine it against `_ALLOWLIST` at that point
rather than pre-emptively carving it out now.

WARN tier on arrival for BOTH rule ids (T-2388): the honest scanned-scope
finding count against THIS repo is expected to be nonzero -- the retarget
children (T-2389 and its siblings) fix PORT001-PATH's hits one group at a
time. Promotion to ERROR tier is a SEPARATE, later step, and applies to
PORT001-PATH ONLY once that burn-down reaches zero, mirroring DOC012's
own two-part closure (the exact precedent T-2384's coordinator invoked:
a detector that ships at ERROR tier with nothing wired to fix its
findings just produces noise or a waiver flood, not a real gate).
PORT001-IDENT never enters the promotion bar at all (see its own
violation-builder docstring) -- it stays WARN/advisory permanently by
design, not as an intermediate state on the way to ERROR."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

from frob.gates._detector_scope import DETECTOR_PACKAGE_ROOTS, tracked_gate_files
from frob.gates._models import Severity, Violation
from frob.gates._parse_failures import local_parse001_violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: This module's own file: it is ABOUT hardcoded-identity detection, so its
#: own docstring/detection logic naming "frob"/"src/frob/" as EXAMPLES
#: would otherwise self-flag -- same self-exclusion LEXCHECK001 gives
#: itself for the identical reason.
_SELF_EXCLUDED_FILES = frozenset({"src/frob/gates/_port_selfcheck.py"})

#: (relpath) -> reason, reviewed same as LEXCHECK001's `_ALLOWLIST` --
#: mirror docs/modules/gates.md#port001-t-2388's own table if this list
#: changes, same hand-kept-in-sync posture LEXCHECK001 already discloses.
_ALLOWLIST: dict[str, str] = {
    "src/frob/gates/_pii_structural/_self_match.py": (
        "T-0201/T-1076: this gate's OWN detector-definition self-exclusion "
        "list -- it must name this repo's own package path/module names "
        "to exclude them from PII scanning; the subject genuinely IS this "
        "repo's own identity by design, not a portability bug"
    ),
}


def _project_package_name(root: Path) -> str | None:
    """The scanned repo's own declared package name (`pyproject.toml`
    `[project].name`), or `None` if it cannot be read/parsed -- callers
    must treat `None` as UNRESOLVED, never as "no literal to look for"
    (T-2391 fail-loudly doctrine: a missing denominator is not a clean
    pass)."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return None
    try:
        with pyproject.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project_cfg = data.get("project") if isinstance(data, dict) else None
    name = project_cfg.get("name") if isinstance(project_cfg, dict) else None
    return name if isinstance(name, str) and name else None


def _path_prefix_hit(node: ast.AST, pkg: str) -> ast.Constant | None:
    """PORT001-PATH: a `"src/<pkg>/"`-shaped string constant passed as the
    argument of a `.startswith(...)` call anywhere in `node`'s subtree --
    the exact `_env_var_docs.py`/`_root_asset_dirs.py` bug shape."""
    target = f"src/{pkg}/"
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call) or not isinstance(sub.func, ast.Attribute):
            continue
        if sub.func.attr != "startswith":
            continue
        for arg in sub.args:
            if isinstance(arg, ast.Constant) and arg.value == target:
                return arg
    return None


def _identity_literal_hit(node: ast.AST, pkg: str) -> ast.Constant | None:
    """PORT001-IDENT: a bare `"<pkg>"` string constant used as an element
    of a `Tuple`/`List` literal, or as a `/`-delimited path SEGMENT inside
    a `JoinedStr` (f-string) constant chunk -- the `_self_match.py`-style
    tuple-of-path-segments/`f"src/frob/gates/.../{name}"` shape,
    generalized past a single `.startswith` call.

    Deliberately narrower than "contains the package name as a
    substring": an f-string chunk is only flagged when `pkg` is a WHOLE
    `/`-split segment of it (`"src/frob/gates/"` -> `["src", "frob",
    "gates", ""]`, `pkg="frob"` is a member) -- a first cut that matched
    ANY substring occurrence flagged ordinary prose mentioning this
    project's own CLI by name (`f"frob ticket scope {id} --add ..."`,
    `f"frob:used-by <consumer>"`, `f"frob:decision {target} has no ..."`)
    as if it were a path-building literal, which it plainly is not --
    that shape would have made the honest T-2388 unscoped count almost
    entirely noise rather than signal (measured: 43 raw hits in
    `src/frob/gates/` alone before this narrowing, nearly all false
    positives of exactly this kind; T-2388's own Done report records the
    before/after count). A bare standalone assignment (`_PKG = "frob"`,
    the declared-identity case `_config_meta.py` uses) is deliberately
    NOT matched here -- that shape is a single named constant, reviewable
    at its own declaration, not the repeated/scattered literal this rule
    targets."""
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Tuple, ast.List)):
            for elt in sub.elts:
                if isinstance(elt, ast.Constant) and elt.value == pkg:
                    return elt
        elif isinstance(sub, ast.JoinedStr):
            for value in sub.values:
                if not isinstance(value, ast.Constant) or not isinstance(
                    value.value, str
                ):
                    continue
                if pkg in value.value.split("/"):
                    return value
    return None


# frob:waive DUP001 reason="sibling PORT001-PATH/PORT001-IDENT/PII010-unresolvable \
# violation builders: this module's own docstring states PORT001-IDENT is deliberately \
# a DIFFERENT, non-promoted rule id from PORT001-PATH -- same builder shape, \
# independently-evolving message/severity per rule"
# frob:enforces CHK-GATE-PORT001-PATH
def _port001_path_violation(rel_path: str, lineno: int, pkg: str) -> Violation:
    """PORT001-PATH: a `.startswith("src/<pkg>/")`-shaped hardcode --
    BEHAVIORAL (T-2384's coordinator, 2026-08-18): off a repo whose
    package is not `pkg`, this silently matches nothing (or the wrong
    thing) rather than erroring -- a gate reading clean/false-firing with
    no signal it happened. This is the class the promotion bar (WARN ->
    ERROR once the burn-down reaches zero) applies to."""
    _log.warning(
        "PORT001-PATH: %s:%d hardcodes this repo's own package name %r as "
        "a src/<pkg>/ path prefix",
        rel_path,
        lineno,
        pkg,
    )
    return Violation(
        rule="PORT001-PATH",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"PORT001-PATH: {rel_path}:{lineno} hardcodes this repo's own "
            f"package name {pkg!r} as a src/<pkg>/ path prefix instead of "
            f"resolving it from the project's declared config -- off a "
            f"repo whose package is not named {pkg!r}, this silently "
            f"matches nothing (or matches the wrong thing) rather than "
            f"erroring. Retarget to a resolver reading the project's own "
            f"pyproject.toml (see "
            f"frob.lang._nodes._declared_python_source_roots, T-2195), or "
            f"add (rel_path) to frob.gates._port_selfcheck._ALLOWLIST "
            f"with a one-line reason if this file is genuinely, "
            f"permanently about this repo's own identity -- never "
            f"silently"
        ),
    )


# frob:waive DUP001 reason="sibling PORT001-PATH/PORT001-IDENT/PII010-unresolvable \
# violation builders: this module's own docstring states PORT001-IDENT is deliberately \
# a DIFFERENT, non-promoted rule id from PORT001-PATH -- same builder shape, \
# independently-evolving message/severity per rule"
# frob:enforces CHK-GATE-PORT001-IDENT
def _port001_ident_violation(rel_path: str, lineno: int, pkg: str) -> Violation:
    """PORT001-IDENT: a bare package-name literal used as a path segment
    (tuple/list element, or an f-string chunk) -- ADVISORY, deliberately
    a DIFFERENT rule id than PORT001-PATH and NOT part of the WARN->ERROR
    promotion bar (T-2384's coordinator, 2026-08-18, correcting an
    earlier ask to collapse both into one disposition): most real hits of
    this shape are maintainer-facing message text pointing at this
    repo's own file (`"add them to the order tuple
    (src/frob/gates/__init__.py)"`) -- misleading to a reader at worst,
    but it changes no gate BEHAVIOR the way PORT001-PATH's silent-pass/
    false-fire class does. Making every such string carry an individual
    `frob:waive` would be an unbounded nag that erodes into a wholesale
    waiver the first time someone gets tired of it -- keeping it a
    separate, non-promoted rule id means a fourth message string next
    month costs nobody anything, while a genuine PORT001-IDENT hit inside
    real path-building logic (the `_self_match.py`-style tuple shape)
    still gets caught and is still reviewable."""
    _log.warning(
        "PORT001-IDENT: %s:%d hardcodes this repo's own package name %r "
        "as a bare path-segment literal",
        rel_path,
        lineno,
        pkg,
    )
    return Violation(
        rule="PORT001-IDENT",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"PORT001-IDENT: {rel_path}:{lineno} hardcodes this repo's "
            f"own package name {pkg!r} as a bare path-segment literal "
            f"(a tuple/list element, or an f-string chunk) -- advisory "
            f"only (NOT part of PORT001-PATH's promotion bar): if this is "
            f"real path-building logic, retarget it the same way as "
            f"PORT001-PATH; if it is maintainer-facing message text "
            f"naming this repo's own file for a human reader, no action "
            f"is required"
        ),
    )


def _parse001_violation(rel_path: str, reason: str) -> Violation:
    """PARSE001 for a file this gate's own `ast.parse` could not get
    through -- shares the drive-wide convention, never a silent drop."""
    return local_parse001_violation(
        rel_path, reason, "PORT001 cannot inspect it for a hardcoded identity literal"
    )


# frob:waive DUP001 reason="sibling UNRESOLVED-pkg-name-violation builders: this is \
# PORT001's own, _root_asset_dirs.py's is ROOT001's -- same fail-loudly \
# log-then-UNRESOLVED-Violation shape (T-2391 convention), independently-evolving rule \
# ids for two different gates"
# frob:enforces CHK-GATE-PORT001
def _unresolved_project_name_violation(root: Path) -> Violation:
    """T-2391 fail-loudly: `root`'s `pyproject.toml` `[project].name`
    could not be read/parsed, so PORT001 has no denominator to scan
    for -- UNRESOLVED, never a silent clean pass (a repo with a broken
    pyproject.toml is not the same claim as "no hardcoded literals
    found")."""
    _log.warning(
        "PORT001: %s/pyproject.toml [project].name unreadable -- PORT001 "
        "cannot resolve what package name to look for; reporting "
        "UNRESOLVED, not a clean pass",
        root,
    )
    return Violation(
        rule="PORT001",
        severity=Severity.UNRESOLVED,
        file="pyproject.toml",
        line=0,
        message=(
            "PORT001: could not resolve this project's own declared "
            "package name from pyproject.toml [project].name -- PORT001 "
            "has no denominator to scan for and cannot report a "
            "meaningful pass/fail; fix pyproject.toml's [project] table"
        ),
    )


# frob:ticket T-2388
# frob:doc docs/modules/gates.md#port001-t-2388
# frob:tests tests/unit/gates/test_port_selfcheck.py::TestPort001.test_hardcoded_path_prefix_is_flagged  # noqa: E501
# frob:tests tests/unit/gates/test_port_selfcheck.py::TestPort001.test_allowlisted_self_match_file_is_silent  # noqa: E501
# frob:tests tests/unit/gates/test_port_selfcheck.py::TestPort001.test_unresolved_project_name_is_not_a_clean_pass  # noqa: E501
# frob:tests tests/unit/gates/test_port_selfcheck.py::TestPort001.test_unparseable_file_is_parse001_not_silent  # noqa: E501
# frob:tests tests/unit/gates/test_port_selfcheck.py::TestPort001.test_non_detector_package_code_never_scanned  # noqa: E501
# frob:tests tests/unit/gates/test_port_selfcheck.py::TestPort001.test_strata_and_vet_are_scanned_since_t2405  # noqa: E501
def port_selfcheck_gate(root: Path) -> tuple[Violation, ...]:
    """PORT001: every git-tracked `.py` file under one of
    `DETECTOR_PACKAGE_ROOTS` (`src/frob/{check,gates,strata,vet}/`,
    T-2405 widening past `src/frob/gates/**` alone) that hardcodes this
    repo's own resolved package name as a path prefix
    (`.startswith("src/<pkg>/")`) or as a bare literal path segment
    (a tuple/list/f-string element), unless the file is in `_ALLOWLIST`
    with a stated reason. UNRESOLVED (not a clean pass) if `root`'s own
    `pyproject.toml` `[project].name` cannot be read. A file this gate
    cannot read/parse fires PARSE001 instead of silently dropping out of
    the scan, matching LEXCHECK001/RENDER001's own convention."""
    root = Path(root)
    pkg = _project_package_name(root)
    if pkg is None:
        return (_unresolved_project_name_violation(root),)

    violations: list[Violation] = []
    scanned_files = tracked_gate_files(root, log_prefix="port_gate")
    for rel_path in scanned_files:
        if rel_path in _SELF_EXCLUDED_FILES or rel_path in _ALLOWLIST:
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(text, filename=rel_path)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            violations.append(_parse001_violation(rel_path, str(exc)))
            continue
        path_hit = _path_prefix_hit(tree, pkg)
        if path_hit is not None:
            violations.append(_port001_path_violation(rel_path, path_hit.lineno, pkg))
            continue
        ident_hit = _identity_literal_hit(tree, pkg)
        if ident_hit is not None:
            violations.append(_port001_ident_violation(rel_path, ident_hit.lineno, pkg))
    _log.warning(
        "port_selfcheck_gate: scanned %d tracked file(s) under "
        "DETECTOR_PACKAGE_ROOTS (%s) ONLY (not repo-wide -- see T-2389 "
        "for the wider src/frob/**-and-beyond retarget), %d violation(s)",
        len(scanned_files),
        ", ".join(DETECTOR_PACKAGE_ROOTS),
        len(violations),
    )
    return tuple(violations)


__all__ = ["port_selfcheck_gate"]
