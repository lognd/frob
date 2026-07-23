"""
frob gitlog -- summarize git history at configurable detail levels.

Parses conventional commits (feat/fix/chore/refactor/perf/docs/test/ci).
Groups by type and optionally filters to only major changes, only user-visible
changes (feat+fix), or full history.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from frob.process._guard import guarded_subprocess_run

GranularityLevel = Literal["major", "user", "full", "changelog"]

_CC_PATTERN = re.compile(
    r"^(?P<type>feat|fix|chore|refactor|perf|docs|test|ci|build|style|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r":\s*(?P<desc>.+)$",
    re.IGNORECASE,
)

_TYPE_LABELS: dict[str, str] = {
    "feat": "Features",
    "fix": "Bug fixes",
    "perf": "Performance",
    "refactor": "Refactoring",
    "docs": "Documentation",
    "test": "Tests",
    "chore": "Chores",
    "ci": "CI/CD",
    "build": "Build",
    "style": "Style",
    "revert": "Reverts",
}

_USER_VISIBLE = {"feat", "fix", "perf", "revert"}


# frob:doc docs/commands/gitlog.md#public-api
class CommitEntry(BaseModel):
    model_config = {}

    sha: str
    short_sha: str
    type: str
    scope: str | None
    breaking: bool
    description: str
    body: str
    tag: str | None = None
    raw_subject: str = ""


# frob:doc docs/commands/gitlog.md#public-api
class GitLogResult(BaseModel):
    model_config = {}

    root: str
    since: str | None
    granularity: GranularityLevel
    commits: list[CommitEntry]

    @property
    # frob:doc docs/commands/gitlog.md#public-api
    def groups(self) -> dict[str, list[CommitEntry]]:
        """Commits grouped by type, with 'breaking' as a special key."""
        result: dict[str, list[CommitEntry]] = {}
        for c in self.commits:
            if c.breaking:
                result.setdefault("breaking", []).append(c)
            result.setdefault(c.type, []).append(c)
        return result

    # frob:ticket T-0588
    # frob:tests tests/unit/test_gitlog_rendering.py::test_as_json_round_trips_groups
    def as_json(self) -> str:
        # frob:doc docs/commands/gitlog.md#public-api
        d = self.model_dump()
        d["groups"] = {k: [c.model_dump() for c in v] for k, v in self.groups.items()}
        import json

        return json.dumps(d, indent=2)

    def _grouped_by_type(
        self,
    ) -> tuple[dict[str, list[CommitEntry]], list[CommitEntry]]:
        """Commits grouped by type, plus the breaking-change list."""
        groups: dict[str, list[CommitEntry]] = {}
        breaking: list[CommitEntry] = []
        for c in self.commits:
            if c.breaking:
                breaking.append(c)
            groups.setdefault(c.type, []).append(c)
        return groups, breaking

    def _header_line(self) -> str:
        """The `git log (...)  --  N commits` summary line."""
        hdr = f"git log ({self.granularity})"
        if self.since:
            hdr += f" since {self.since}"
        hdr += (
            f"  --  {len(self.commits)} commit{'s' if len(self.commits) != 1 else ''}"
        )
        return hdr

    def _type_section_order(self, groups: dict[str, list[CommitEntry]]) -> list[str]:
        """Type keys in display order: the canonical order, then any leftover types."""
        order = [
            "feat",
            "fix",
            "perf",
            "refactor",
            "docs",
            "test",
            "chore",
            "ci",
            "build",
        ]
        seen = set(order)
        order += [k for k in groups if k not in seen]
        return order

    # frob:ticket T-0588
    # frob:tests tests/unit/test_gitlog_rendering.py::test_as_text_no_commits_short_circuit  # noqa: E501
    def as_text(self) -> str:
        # frob:doc docs/commands/gitlog.md#public-api
        if not self.commits:
            return "no commits found"

        groups, breaking = self._grouped_by_type()
        lines: list[str] = [self._header_line(), ""]

        if breaking:
            lines.append("### BREAKING CHANGES")
            for c in breaking:
                _append_entry(lines, c)
            lines.append("")

        for t in self._type_section_order(groups):
            if t not in groups:
                continue
            label = _TYPE_LABELS.get(t, t)
            lines.append(f"### {label}")
            for c in groups[t]:
                _append_entry(lines, c)
            lines.append("")

        return "\n".join(lines).rstrip()


def _append_entry(lines: list[str], c: CommitEntry) -> None:
    scope = f"({c.scope}) " if c.scope else ""
    bang = "! " if c.breaking else ""
    lines.append(f"  {c.short_sha}  {bang}{scope}{c.description}")
    if c.tag:
        lines[-1] += f"  [{c.tag}]"


def _granularity_keep(e, granularity: GranularityLevel) -> bool:
    """Whether commit `e` survives the granularity filter (`full` keeps all)."""
    if granularity == "major":
        return (
            e.breaking
            or "major" in e.description.lower()
            or (
                e.type == "chore"
                and "bump" in e.description.lower()
                and _is_major_version(e.description)
            )
        )
    if granularity == "user":
        return e.type in _USER_VISIBLE or e.breaking
    if granularity == "changelog":
        return e.type in {"feat", "fix"} or e.breaking
    return True


# frob:doc docs/commands/gitlog.md#public-api
def git_log(
    root: Path | None = None,
    *,
    granularity: GranularityLevel = "user",
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
    include_non_conventional: bool = False,
) -> GitLogResult:
    """
    Fetch and filter git log.

    Granularity levels:
      major     -- only breaking changes and version bump commits
      user      -- feat + fix + perf + revert (user-visible changes)
      full      -- all conventional commit types
      changelog -- grouped release-style output (feat + fix + breaking)
    """
    cwd = str(root) if root else None
    raw = _git_log_raw(cwd, since=since, until=until, limit=limit)
    entries = _parse_commits(raw)

    entries = [e for e in entries if _granularity_keep(e, granularity)]
    if not include_non_conventional:
        entries = [e for e in entries if e.type != "unknown"]

    return GitLogResult(
        root=str(root) if root else ".",
        since=since,
        granularity=granularity,
        commits=entries,
    )


def _git_log_raw(
    cwd: str | None, *, since: str | None, until: str | None, limit: int | None
) -> str:
    # %H = full hash, %h = short, %s = subject, %b = body, %D = refs (tags)
    fmt = "---COMMIT---\n%H\n%h\n%s\n%D\n%b\n---END---"
    cmd = ["git", "log", f"--pretty=format:{fmt}"]
    if since:
        cmd.append(
            f"--since={since}" if not since.startswith("v") else f"{since}..HEAD"
        )
    if until:
        cmd.append(f"--until={until}")
    if limit:
        cmd += ["-n", str(limit)]
    # T-0803: routed through `guarded_subprocess_run` (T-0778's guard) so
    # `FROB_DISABLE_EXEC=1` refuses this git spawn instead of bypassing it
    # -- kept as a direct `guarded_subprocess_run` call rather than
    # `frob.gitio.run_argv` to preserve this call's exact no-timeout,
    # `FileNotFoundError`-tolerant contract (`frob.gitio.run_argv` imposes
    # a default 30s timeout and a different `Result`-based error shape
    # this module's callers do not expect).
    try:
        guarded = guarded_subprocess_run(cmd, capture_output=True, text=True, cwd=cwd)
    except FileNotFoundError:
        return ""
    if guarded.is_err:
        return ""
    return guarded.danger_ok.stdout


def _tag_from_refs(refs: str) -> str | None:
    """The `tag:` ref name in a comma-separated `%D` refs string, if any."""
    for ref in refs.split(","):
        ref = ref.strip()
        if ref.startswith("tag:"):
            return ref[4:].strip()
    return None


def _conventional_commit_entry(
    subject: str, sha: str, short_sha: str, body: str, tag: str | None
) -> CommitEntry:
    """A `CommitEntry` from `subject`'s conventional-commit match, or unknown-typed."""
    m = _CC_PATTERN.match(subject)
    if m is None:
        return CommitEntry(
            sha=sha,
            short_sha=short_sha,
            type="unknown",
            scope=None,
            breaking=False,
            description=subject,
            body=body,
            tag=tag,
            raw_subject=subject,
        )
    gd = m.groupdict()
    return CommitEntry(
        sha=sha,
        short_sha=short_sha,
        type=gd["type"].lower(),
        scope=gd["scope"],
        breaking=bool(gd["breaking"]),
        description=gd["desc"].strip(),
        body=body,
        tag=tag,
        raw_subject=subject,
    )


def _commit_entry_from_block(block: str) -> CommitEntry | None:
    """One raw `%H\\n%h\\n%s\\n%D\\n%b` commit block as a `CommitEntry`, or `None`."""
    lines = block.splitlines()
    if len(lines) < 3:
        return None
    sha = lines[0].strip()
    short_sha = lines[1].strip()
    subject = lines[2].strip()
    refs = lines[3].strip() if len(lines) > 3 else ""
    body = "\n".join(lines[4:]).strip() if len(lines) > 4 else ""
    tag = _tag_from_refs(refs)
    return _conventional_commit_entry(subject, sha, short_sha, body, tag)


def _parse_commits(raw: str) -> list[CommitEntry]:
    entries: list[CommitEntry] = []
    blocks = raw.split("---COMMIT---\n")
    for block in blocks:
        block = block.strip()
        if not block or "---END---" not in block:
            continue
        block = block.split("---END---")[0].strip()
        entry = _commit_entry_from_block(block)
        if entry is not None:
            entries.append(entry)
    return entries


def _is_major_version(desc: str) -> bool:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", desc)
    if m:
        return m.group(1) != "0" and m.group(2) == "0" and m.group(3) == "0"
    return False
