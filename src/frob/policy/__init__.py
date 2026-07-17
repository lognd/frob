"""frob.policy -- user-defined rules from `frob.toml`'s `[policy]` table.

(docs/gates.md is authoritative.)

Three rule kinds at alpha: `forbidden-import` (regex over import syntax,
documented duplicate of language-specific import grammar rather than a
second tree-sitter query per language), `pattern` (a real tree-sitter
query compiled against `frob.lang`'s grammars), and `norm` (diff-shape
rules over `frob.gitio.Diff`). Taint analysis is out of scope for 0.1.0.

`load_policy` eagerly compiles every `pattern` query so a bad query is a
load-time `Err(BadQuery)`, never a silent no-op at scan time.
"""

from __future__ import annotations

import fnmatch
import re
import tomllib
from pathlib import Path

import tree_sitter
from pydantic import ValidationError
from tree_sitter_language_pack import get_language, get_parser
from typani import Err, Ok
from typani.result import Result

from frob.gates._models import Severity, Violation, WaiverRef
from frob.gitio import Diff
from frob.graph import GraphSnapshot
from frob.logging import get_logger
from frob.policy._models import PolicyError, PolicyKind, PolicyRule

_log = get_logger(__name__)

# Documented duplicate of frob.lang._EXTENSION_TABLE's extension -> language label
# mapping (same posture as frob.graph._SOURCE_EXTENSIONS and
# frob.testing._select._EXTENSION_LANGUAGE): frob.lang exposes only
# supported_languages(), not the extension map itself.
_EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".hh": "cpp",
}

# Import-syntax regexes, one per language label; deliberately line-based rather
# than tree-sitter (a second grammar-driven pass per forbidden-import rule was
# judged unnecessary complexity for a check this shallow).
_IMPORT_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^\s*(?:import\s+([\w.]+)|from\s+([\w.]+)\s+import)"),
    "typescript": re.compile(
        r"""(?:from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\))"""
    ),
    "rust": re.compile(r"^\s*use\s+([\w:]+)"),
    "c": re.compile(r'^\s*#include\s*[<"]([^">]+)[">]'),
    "cpp": re.compile(r'^\s*#include\s*[<"]([^">]+)[">]'),
}


def _files_under(root: Path, snapshot: GraphSnapshot, pattern: str) -> tuple[str, ...]:
    """Repo-relative paths in `snapshot.file_hashes` matching glob `pattern`."""
    return tuple(sorted(p for p in snapshot.file_hashes if fnmatch.fnmatch(p, pattern)))


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


# frob:doc docs/gates.md#public-api
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


def _first_group(match) -> str:
    """The first non-empty capture group of a regex match (`""` if none)."""
    return next((g for g in match.groups() if g), "")


def _import_violations_in_file(
    rule: PolicyRule, rel_path: str, text: str, pattern
) -> list[Violation]:
    """Forbidden-import violations for the lines of one already-read file."""
    violations: list[Violation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = pattern.match(line) or pattern.search(line)
        if match is None:
            continue
        imported = _first_group(match)
        if imported == rule.module or imported.startswith(rule.module + "."):
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
    return violations


def _forbidden_import_violations(
    rule: PolicyRule, root: Path, snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """Every import line in a `within`-matched file that imports `rule.module`."""
    violations: list[Violation] = []
    for rel_path in _files_under(root, snapshot, rule.within):
        language = _EXTENSION_LANGUAGE.get(Path(rel_path).suffix.lower())
        pattern = _IMPORT_PATTERNS.get(language or "")
        if pattern is None:
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("policy: could not read %s: %s", rel_path, exc)
            continue
        violations.extend(_import_violations_in_file(rule, rel_path, text, pattern))
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


def _pattern_violations(
    rule: PolicyRule, root: Path, snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """Every tree-sitter query match in a `globs`-matched, `language`-typed file."""
    query_text = _resolve_query_text(root, rule)
    if query_text is None:
        return ()
    lang = None
    parser = None
    try:
        lang = get_language(rule.language)  # type: ignore[arg-type]
        parser = get_parser(rule.language)  # type: ignore[arg-type]
        query = tree_sitter.Query(lang, query_text)
    except (LookupError, ValueError, tree_sitter.QueryError) as exc:
        _log.warning("policy: %s query unusable at scan time: %s", rule.id, exc)
        return ()

    violations: list[Violation] = []
    for rel_path in _candidate_files(root, snapshot, rule.globs or ("**/*",)):
        try:
            source = (root / rel_path).read_bytes()
        except OSError as exc:
            _log.warning("policy: could not read %s: %s", rel_path, exc)
            continue
        tree = parser.parse(source)
        cursor = tree_sitter.QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        for _name, nodes in captures.items():
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


# frob:doc docs/gates.md#public-api
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
