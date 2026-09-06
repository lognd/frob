"""frob.policy -- user-defined rules from `frob.toml`'s `[policy]` table.

(docs/modules/gates.md is authoritative.)

Three rule kinds at alpha: `forbidden-import` (specifiers sourced from
`frob.lang.extract_imports` -- the SAME grammar-driven walk `frob.lang`
and `frob.cycle` already use, per NO-DUPLICATION; see T-3235, T-2996),
`pattern` (a real tree-sitter query compiled against `frob.lang`'s
grammars), and `norm` (diff-shape rules over `frob.gitio.Diff`). Taint
analysis is out of scope for 0.1.0.

`load_policy` eagerly compiles every `pattern` query so a bad query is a
load-time `Err(BadQuery)`, never a silent no-op at scan time.
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

import pathspec
import tree_sitter
from pydantic import ValidationError
from tree_sitter_language_pack import get_language, get_parser
from typani import Err, Ok
from typani.result import Result

from frob.gates._models import Severity, Violation, WaiverRef
from frob.gitio import Diff
from frob.graph import GraphSnapshot
from frob.lang import extract_imports as _lang_extract_imports
from frob.logging import get_logger
from frob.policy._models import PolicyError, PolicyKind, PolicyRule

_log = get_logger(__name__)


# frob:ticket T-4013
# frob:tests \
# tests/test_policy.py::TestRules.test_glob_double_star_matches_file_directly_under_pre\
# fix
# frob:tests \
# tests/test_policy.py::TestRules.test_glob_stays_quiet_outside_matched_directory
@lru_cache(maxsize=None)
def _compiled_glob(pattern: str) -> pathspec.PathSpec:
    """Compile `pattern` under gitwildmatch semantics (cached per pattern).

    T-4013: policy globs previously matched via `fnmatch.fnmatch`, which has
    no zero-or-more-directories `**` -- `app/**/*.py` silently missed files
    directly under `app/` (`fnmatch` degrades `**` to "at least one
    intervening directory") and, independently, `fnmatch.normcase`s both
    sides so the same pattern matches differently on Windows than on Linux.
    `pathspec`'s `gitwildmatch` dialect is what `.gitignore`, ruff, and
    every other modern tool mean by `**`, and it is platform-independent.
    """
    return pathspec.PathSpec.from_lines("gitignore", [pattern])


def _files_under(root: Path, snapshot: GraphSnapshot, pattern: str) -> tuple[str, ...]:
    """Repo-relative paths in `snapshot.file_hashes` matching glob `pattern`
    under gitwildmatch semantics (T-4013: not `fnmatch`, which lacks a
    zero-or-more-directories `**` and is platform-dependent via `normcase`)."""
    spec = _compiled_glob(pattern)
    return tuple(sorted(p for p in snapshot.file_hashes if spec.match_file(p)))


def _load_forbidden_imports(
    policy_tbl: dict,
) -> Result[list[PolicyRule], PolicyError]:
    """Build the FORBIDDEN_IMPORT rules from the `[[policy.forbidden-import]]` table."""
    rules: list[PolicyRule] = []
    for entry in policy_tbl.get("forbidden-import", []):
        try:
            rules.append(
                PolicyRule(
                    id=entry["id"],
                    kind=PolicyKind.FORBIDDEN_IMPORT,
                    module=entry["module"],
                    within=entry["within"],
                    reason=entry.get("reason", ""),
                    severity=entry.get("severity", "error"),
                )
            )
        except (KeyError, ValidationError) as exc:
            _log.error("load_policy: malformed forbidden-import entry: %s", exc)
            return Err(PolicyError.MalformedRule)
    return Ok(rules)


def _load_pattern_rules(
    root: Path, policy_tbl: dict
) -> Result[list[PolicyRule], PolicyError]:
    """Build and validate PATTERN rules from the `[[policy.pattern]]` table."""
    rules: list[PolicyRule] = []
    for entry in policy_tbl.get("pattern", []):
        try:
            rule = PolicyRule(
                id=entry["id"],
                kind=PolicyKind.PATTERN,
                language=entry["language"],
                query=entry.get("query", ""),
                query_file=entry.get("query_file", ""),
                globs=tuple(entry.get("globs", ())),
                reason=entry.get("reason", ""),
                severity=entry.get("severity", "error"),
            )
        except (KeyError, ValidationError) as exc:
            _log.error("load_policy: malformed pattern entry: %s", exc)
            return Err(PolicyError.MalformedRule)
        resolved_query = _resolve_query_text(root, rule)
        if resolved_query is None:
            _log.error("load_policy: no query text for pattern rule %s", rule.id)
            return Err(PolicyError.BadQuery)
        if _compile_query(rule.language, resolved_query) is None:
            _log.error("load_policy: query for %s does not compile", rule.id)
            return Err(PolicyError.BadQuery)
        rules.append(rule)
    return Ok(rules)


def _load_norm_rules(policy_tbl: dict) -> Result[list[PolicyRule], PolicyError]:
    """Build the NORM rules from the `[[policy.norm]]` table."""
    rules: list[PolicyRule] = []
    for entry in policy_tbl.get("norm", []):
        try:
            rules.append(
                PolicyRule(
                    id=entry["id"],
                    kind=PolicyKind.NORM,
                    max_diff_lines=int(entry["max_diff_lines"]),
                    reason=entry.get("reason", ""),
                    severity=entry.get("severity", "error"),
                )
            )
        except (KeyError, ValidationError, ValueError) as exc:
            _log.error("load_policy: malformed norm entry: %s", exc)
            return Err(PolicyError.MalformedRule)
    return Ok(rules)


# frob:doc docs/modules/gates.md#public-api
def load_policy(root: Path) -> Result[tuple[PolicyRule, ...], PolicyError]:
    """Parse `frob.toml`'s `[[policy.*]]` tables; missing file/table is `Ok(())`."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        _log.info("load_policy: no frob.toml at %s", toml_path)
        return Ok(())
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, ValueError) as exc:
        _log.error("load_policy: could not parse %s: %s", toml_path, exc)
        return Err(PolicyError.MalformedRule)

    policy_tbl = doc.get("policy", {})
    rules: list[PolicyRule] = []
    for loaded in (
        _load_forbidden_imports(policy_tbl),
        _load_pattern_rules(root, policy_tbl),
        _load_norm_rules(policy_tbl),
    ):
        if loaded.is_err:
            return Err(loaded.danger_err)
        rules.extend(loaded.danger_ok)

    _log.info("load_policy: loaded %d rule(s) from %s", len(rules), toml_path)
    return Ok(tuple(rules))


def _resolve_query_text(root: Path, rule: PolicyRule) -> str | None:
    """Inline `query`, else `query_file`, else `policy/queries/<id>.scm`,
    else `None`."""
    if rule.query:
        return rule.query
    candidate = rule.query_file or f"policy/queries/{rule.id}.scm"
    path = root / candidate
    if not path.is_file():
        _log.warning("policy: no query file at %s for rule %s", path, rule.id)
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("policy: could not read query file %s: %s", path, exc)
        return None


def _compile_query(language: str, query_text: str) -> tree_sitter.Query | None:
    """Compile `query_text` against `language`'s grammar, `None` on any failure."""
    try:
        lang = get_language(language)  # type: ignore[arg-type]
        return tree_sitter.Query(lang, query_text)
    except (LookupError, ValueError, tree_sitter.QueryError) as exc:
        _log.warning("policy: query compile failed for language=%s: %s", language, exc)
        return None


def _severity(rule: PolicyRule) -> Severity:
    """Map a rule's `severity` string to `Severity`, defaulting to error."""
    return Severity.WARN if rule.severity == "warn" else Severity.ERROR


def _import_violates(imported: str, module: str) -> bool:
    """True if extracted specifier `imported` matches or nests under `module`."""
    return imported == module or imported.startswith(module + ".")


def _line_for_specifier(text: str, imported: str) -> int:
    """1-based line number of `imported`'s first occurrence in `text` (0 if absent).

    Reporting-only lookup over an already grammar-identified specifier
    (`frob.lang.extract_imports` did the actual import-syntax parsing) --
    not a re-implementation of any language's import grammar.
    """
    for lineno, line in enumerate(text.splitlines(), start=1):
        if imported in line:
            return lineno
    return 0


def _forbidden_import_violations(
    rule: PolicyRule, root: Path, snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """Every import in a `within`-matched file that imports `rule.module`.

    T-3235: import specifiers come from `frob.lang.extract_imports`, the
    same grammar-driven walk `frob.cycle` builds its dependency graph
    from, rather than a second, parallel set of per-language regexes --
    two implementations of "what counts as an import" is the exact
    NO-DUPLICATION violation T-2996 measured here.
    """
    violations: list[Violation] = []
    for rel_path in _files_under(root, snapshot, rule.within):
        path = root / rel_path
        result = _lang_extract_imports(path)
        if result.is_err:
            # Unsupported language (or unreadable/unparsable file) for the
            # grammar layer -- nothing for a forbidden-import rule to check.
            continue
        specifiers = result.danger_ok
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("policy: could not read %s: %s", rel_path, exc)
            continue
        for imported in specifiers:
            if not _import_violates(imported, rule.module):
                continue
            lineno = _line_for_specifier(text, imported)
            _log.info(
                "policy: %s violated at %s:%d (imports %s)",
                rule.id,
                rel_path,
                lineno,
                imported,
            )
            violations.append(
                Violation(
                    rule=rule.id,
                    severity=_severity(rule),
                    file=rel_path,
                    line=lineno,
                    message=(
                        f"{rule.id}: {rel_path}:{lineno} imports forbidden "
                        f"module {imported!r} "
                        f"({rule.reason or 'forbidden by policy'}); remove "
                        f"the import or narrow frob.toml's within glob"
                    ),
                )
            )
    return tuple(violations)


def _matching_files(
    root: Path, snapshot: GraphSnapshot, globs: tuple[str, ...]
) -> set[str]:
    """The set of files matching any of `globs` under `root`."""
    candidates: set[str] = set()
    for glob in globs:
        candidates.update(_files_under(root, snapshot, glob))
    return candidates


def _candidate_files(
    root: Path, snapshot: GraphSnapshot, globs: tuple[str, ...]
) -> list[str]:
    """Sorted, de-duplicated files matching any of `globs` under `root`."""
    return sorted(_matching_files(root, snapshot, globs))


def _compile_pattern_query(rule: PolicyRule, query_text: str) -> tuple | None:
    """`(parser, query)` for `rule`'s language/query text, or `None` if unusable."""
    try:
        lang = get_language(rule.language)  # type: ignore[arg-type]
        parser = get_parser(rule.language)  # type: ignore[arg-type]
        query = tree_sitter.Query(lang, query_text)
    except (LookupError, ValueError, tree_sitter.QueryError) as exc:
        _log.warning("policy: %s query unusable at scan time: %s", rule.id, exc)
        return None
    return parser, query


def _file_pattern_violations(
    rule: PolicyRule,
    rel_path: str,
    root: Path,
    parser,
    query,  # noqa: ANN001
) -> list[Violation]:
    """Every match of `query` against one file, as `Violation`s for `rule`."""
    try:
        source = (root / rel_path).read_bytes()
    except OSError as exc:
        _log.warning("policy: could not read %s: %s", rel_path, exc)
        return []
    tree = parser.parse(source)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node)
    violations: list[Violation] = []
    for nodes in captures.values():
        for node in nodes:
            line = node.start_point[0] + 1
            _log.debug("policy: %s matched at %s:%d", rule.id, rel_path, line)
            violations.append(
                Violation(
                    rule=rule.id,
                    severity=_severity(rule),
                    file=rel_path,
                    line=line,
                    message=(
                        f"{rule.id}: {rel_path}:{line} matches banned pattern "
                        f"({rule.reason or 'forbidden by policy'}); "
                        f'add: frob:waive {rule.id} reason="..." if intentional'
                    ),
                )
            )
    return violations


def _pattern_violations(
    rule: PolicyRule, root: Path, snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """Every tree-sitter query match in a `globs`-matched, `language`-typed file."""
    query_text = _resolve_query_text(root, rule)
    if query_text is None:
        return ()
    compiled = _compile_pattern_query(rule, query_text)
    if compiled is None:
        return ()
    parser, query = compiled

    violations: list[Violation] = []
    for rel_path in _candidate_files(root, snapshot, rule.globs or ("**/*",)):
        violations.extend(_file_pattern_violations(rule, rel_path, root, parser, query))
    return tuple(violations)


def _norm_violations(rule: PolicyRule, diff: Diff) -> tuple[Violation, ...]:
    """One violation if the total changed-line count exceeds `max_diff_lines`."""
    total = sum(hunk.span[1] - hunk.span[0] + 1 for hunk in diff.hunks)
    if total <= rule.max_diff_lines:
        return ()
    _log.debug("policy: %s exceeded, %d > %d", rule.id, total, rule.max_diff_lines)
    return (
        Violation(
            rule=rule.id,
            severity=_severity(rule),
            file="<diff>",
            line=0,
            message=(
                f"{rule.id}: diff touches {total} lines, over the "
                f"max_diff_lines={rule.max_diff_lines} limit "
                f"({rule.reason or 'restraint merges'}); split into smaller commits"
            ),
        ),
    )


# frob:doc docs/modules/gates.md#public-api
def policy_gate(
    rules: tuple[PolicyRule, ...], snapshot: GraphSnapshot, diff: Diff
) -> tuple[Violation, ...]:
    """Run every loaded policy rule against `snapshot`/`diff`; pure, no loading."""
    root = Path(snapshot.root)
    violations: list[Violation] = []
    for rule in rules:
        if rule.kind == PolicyKind.FORBIDDEN_IMPORT:
            violations.extend(_forbidden_import_violations(rule, root, snapshot))
        elif rule.kind == PolicyKind.PATTERN:
            violations.extend(_pattern_violations(rule, root, snapshot))
        elif rule.kind == PolicyKind.NORM:
            violations.extend(_norm_violations(rule, diff))
    _log.info("policy_gate: %d rule(s), %d violation(s)", len(rules), len(violations))
    return tuple(violations)


__all__ = [
    "PolicyError",
    "PolicyKind",
    "PolicyRule",
    "WaiverRef",
    "load_policy",
    "policy_gate",
]
