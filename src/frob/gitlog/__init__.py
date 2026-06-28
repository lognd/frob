"""
frob gitlog -- summarize git history at configurable detail levels.

Parses conventional commits (feat/fix/chore/refactor/perf/docs/test/ci).
Groups by type and optionally filters to only major changes, only user-visible
changes (feat+fix), or full history.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

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


class GitLogResult(BaseModel):
    model_config = {}

    root: str
    since: str | None
    granularity: GranularityLevel
    commits: list[CommitEntry]

    @property
    def groups(self) -> dict[str, list[CommitEntry]]:
        """Commits grouped by type, with 'breaking' as a special key."""
        result: dict[str, list[CommitEntry]] = {}
        for c in self.commits:
            if c.breaking:
                result.setdefault("breaking", []).append(c)
            result.setdefault(c.type, []).append(c)
        return result

    def as_json(self) -> str:
        d = self.model_dump()
        d["groups"] = {k: [c.model_dump() for c in v] for k, v in self.groups.items()}
        import json

        return json.dumps(d, indent=2)

    def as_text(self) -> str:
        if not self.commits:
            return "no commits found"

        # Group by type
        groups: dict[str, list[CommitEntry]] = {}
        breaking: list[CommitEntry] = []

        for c in self.commits:
            if c.breaking:
                breaking.append(c)
            groups.setdefault(c.type, []).append(c)

        lines: list[str] = []

        hdr = f"git log ({self.granularity})"
        if self.since:
            hdr += f" since {self.since}"
        hdr += (
            f"  --  {len(self.commits)} commit{'s' if len(self.commits) != 1 else ''}"
        )
        lines.append(hdr)
        lines.append("")

        if breaking:
            lines.append("### BREAKING CHANGES")
            for c in breaking:
                _append_entry(lines, c)
            lines.append("")

        # Order: feat, fix, perf, refactor, then others
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

        for t in order:
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

    # Filter by granularity
    if granularity == "major":
        entries = [
            e
            for e in entries
            if e.breaking
            or "major" in e.description.lower()
            or (
                e.type == "chore"
                and "bump" in e.description.lower()
                and _is_major_version(e.description)
            )
        ]
    elif granularity == "user":
        entries = [e for e in entries if e.type in _USER_VISIBLE or e.breaking]
    elif granularity == "changelog":
        entries = [e for e in entries if e.type in {"feat", "fix"} or e.breaking]
    # "full" keeps all

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
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        return result.stdout
    except FileNotFoundError:
        return ""


def _parse_commits(raw: str) -> list[CommitEntry]:
    entries: list[CommitEntry] = []
    blocks = raw.split("---COMMIT---\n")
    for block in blocks:
        block = block.strip()
        if not block or "---END---" not in block:
            continue
        block = block.split("---END---")[0].strip()
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        sha = lines[0].strip()
        short_sha = lines[1].strip()
        subject = lines[2].strip()
        refs = lines[3].strip() if len(lines) > 3 else ""
        body = "\n".join(lines[4:]).strip() if len(lines) > 4 else ""

        # Extract tag from refs
        tag: str | None = None
        for ref in refs.split(","):
            ref = ref.strip()
            if ref.startswith("tag:"):
                tag = ref[4:].strip()
                break

        m = _CC_PATTERN.match(subject)
        if m:
            gd = m.groupdict()
            entry = CommitEntry(
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
        else:
            entry = CommitEntry(
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
        entries.append(entry)
    return entries


def _is_major_version(desc: str) -> bool:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", desc)
    if m:
        return m.group(1) != "0" and m.group(2) == "0" and m.group(3) == "0"
    return False
