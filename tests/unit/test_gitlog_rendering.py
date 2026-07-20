# frob:ticket T-0160
"""Unit tests for `frob.gitlog`'s pure rendering/parsing helpers.

Constructs `CommitEntry`/`GitLogResult` directly (no git subprocess) so
`.groups`/`.as_json`/`.as_text`'s branch combinations -- breaking-change
section, multiple type groups, empty-commit short-circuit, tag/scope
rendering -- are each reachable without needing a real repo, and drives
the module-level parsing helpers (`_granularity_keep`, `_is_major_version`,
`_tag_from_refs`, `_commit_entry_from_block`, `_parse_commits`) directly
against crafted input strings.
"""

from __future__ import annotations

import json

from frob.gitlog import CommitEntry, GitLogResult
from frob.gitlog import _commit_entry_from_block as commit_entry_from_block
from frob.gitlog import _granularity_keep as granularity_keep
from frob.gitlog import _is_major_version as is_major_version
from frob.gitlog import _parse_commits as parse_commits
from frob.gitlog import _tag_from_refs as tag_from_refs


def _entry(
    *,
    type: str = "feat",
    scope: str | None = None,
    breaking: bool = False,
    description: str = "did a thing",
    tag: str | None = None,
    sha: str = "abc123def",
) -> CommitEntry:
    """One `CommitEntry` with sensible defaults, overridable per test."""
    return CommitEntry(
        sha=sha,
        short_sha=sha[:7],
        type=type,
        scope=scope,
        breaking=breaking,
        description=description,
        body="",
        tag=tag,
    )


# frob:tests tests/unit/test_gitlog_rendering.py::test_groups_puts_breaking_commit_under_both_keys
def test_groups_puts_breaking_commit_under_both_keys() -> None:
    """A breaking commit lands under both its own type AND `"breaking"`."""
    result = GitLogResult(
        root=".", since=None, granularity="full", commits=[_entry(breaking=True)]
    )
    grouped = result.groups
    assert "breaking" in grouped
    assert "feat" in grouped
    assert grouped["breaking"] == grouped["feat"]


# frob:tests tests/unit/test_gitlog_rendering.py::test_groups_non_breaking_only_own_type
def test_groups_non_breaking_only_own_type() -> None:
    """A non-breaking commit lands only under its own type key."""
    result = GitLogResult(
        root=".", since=None, granularity="full", commits=[_entry(type="fix")]
    )
    grouped = result.groups
    assert "breaking" not in grouped
    assert "fix" in grouped


# frob:tests tests/unit/test_gitlog_rendering.py::test_as_json_round_trips_groups
def test_as_json_round_trips_groups() -> None:
    """`as_json` is valid JSON carrying both `commits` and a `groups` key."""
    result = GitLogResult(
        root=".", since="v1.0.0", granularity="user", commits=[_entry(scope="core")]
    )
    payload = json.loads(result.as_json())
    assert "commits" in payload
    assert "groups" in payload
    assert "feat" in payload["groups"]


# frob:tests tests/unit/test_gitlog_rendering.py::test_as_text_no_commits_short_circuit
def test_as_text_no_commits_short_circuit() -> None:
    """`as_text` on an empty commit list returns the fixed no-commits message."""
    result = GitLogResult(root=".", since=None, granularity="full", commits=[])
    assert result.as_text() == "no commits found"


# frob:tests tests/unit/test_gitlog_rendering.py::test_as_text_renders_breaking_section_and_labels
def test_as_text_renders_breaking_section_and_labels() -> None:
    """`as_text` renders a BREAKING CHANGES section plus type-labeled
    sections (canonical order first, then unrecognized leftover types),
    with scope/tag/singular-commit-count all showing up in the output."""
    result = GitLogResult(
        root=".",
        since="v1.0.0",
        granularity="full",
        commits=[
            _entry(type="feat", breaking=True, description="big rewrite", tag="v2.0.0"),
            _entry(type="fix", scope="core", description="fix bug"),
            _entry(type="mystery", description="an unrecognized type"),
        ],
    )
    text = result.as_text()
    assert "### BREAKING CHANGES" in text
    assert "### Features" in text
    assert "### Bug fixes" in text
    assert "### mystery" in text  # leftover type falls back to its raw name
    assert "(core) fix bug" in text
    assert "[v2.0.0]" in text
    assert "since v1.0.0" in text
    assert "3 commits" in text


# frob:tests tests/unit/test_gitlog_rendering.py::test_as_text_singular_commit_count
def test_as_text_singular_commit_count() -> None:
    """The header pluralizes "commit(s)" correctly for exactly one commit."""
    result = GitLogResult(root=".", since=None, granularity="full", commits=[_entry()])
    assert "1 commit  --" not in result.as_text()  # sanity: not zero-padded oddly
    assert "1 commit\n" in result.as_text() or "1 commit  " not in result.as_text()
    header = result.as_text().splitlines()[0]
    assert header.endswith("1 commit")


# frob:tests tests/unit/test_gitlog_rendering.py::test_granularity_keep_major
def test_granularity_keep_major() -> None:
    """`major` granularity keeps breaking changes, "major"-mentioning
    commits, and major-version-bump chores; drops everything else."""
    assert granularity_keep(_entry(breaking=True), "major") is True
    assert granularity_keep(_entry(description="a major overhaul"), "major") is True
    assert (
        granularity_keep(_entry(type="chore", description="bump to 2.0.0"), "major")
        is True
    )
    assert (
        granularity_keep(_entry(type="chore", description="bump to 1.2.3"), "major")
        is False
    )
    assert (
        granularity_keep(_entry(type="fix", description="small fix"), "major") is False
    )


# frob:tests tests/unit/test_gitlog_rendering.py::test_granularity_keep_user
def test_granularity_keep_user() -> None:
    """`user` granularity keeps feat/fix/perf/revert and any breaking change."""
    assert granularity_keep(_entry(type="feat"), "user") is True
    assert granularity_keep(_entry(type="docs"), "user") is False
    assert granularity_keep(_entry(type="docs", breaking=True), "user") is True


# frob:tests tests/unit/test_gitlog_rendering.py::test_granularity_keep_changelog
def test_granularity_keep_changelog() -> None:
    """`changelog` granularity keeps feat/fix and any breaking change only."""
    assert granularity_keep(_entry(type="feat"), "changelog") is True
    assert granularity_keep(_entry(type="chore"), "changelog") is False
    assert granularity_keep(_entry(type="chore", breaking=True), "changelog") is True


# frob:tests tests/unit/test_gitlog_rendering.py::test_granularity_keep_full_keeps_everything
def test_granularity_keep_full_keeps_everything() -> None:
    """`full` granularity is the identity filter -- everything survives."""
    assert granularity_keep(_entry(type="style"), "full") is True


# frob:tests tests/unit/test_gitlog_rendering.py::test_is_major_version
def test_is_major_version() -> None:
    """Only an X.0.0 bump (X != 0) counts as a major version string."""
    assert is_major_version("bump to 2.0.0") is True
    assert is_major_version("bump to 0.5.0") is False
    assert is_major_version("bump to 1.2.3") is False
    assert is_major_version("no version here") is False


# frob:tests tests/unit/test_gitlog_rendering.py::test_tag_from_refs
def test_tag_from_refs() -> None:
    """`_tag_from_refs` finds the `tag: <name>` entry in a comma-separated
    refs string, or `None` if there isn't one."""
    assert tag_from_refs("HEAD -> main, tag: v1.2.3, origin/main") == "v1.2.3"
    assert tag_from_refs("HEAD -> main, origin/main") is None
    assert tag_from_refs("") is None


# frob:tests tests/unit/test_gitlog_rendering.py::test_commit_entry_from_block_too_short_is_none
def test_commit_entry_from_block_too_short_is_none() -> None:
    """A malformed block with fewer than 3 lines (sha/short_sha/subject
    minimum) is rejected rather than raising an IndexError."""
    assert commit_entry_from_block("onlyonelinehere") is None
    assert commit_entry_from_block("line1\nline2") is None


# frob:tests tests/unit/test_gitlog_rendering.py::test_commit_entry_from_block_with_refs_and_body
def test_commit_entry_from_block_with_refs_and_body() -> None:
    """A well-formed block with a tag ref and a multi-line body parses into
    a full `CommitEntry`."""
    block = "deadbeef\ndeadbee\nfeat(core)!: add thing\ntag: v3.0.0\nbody line 1\nbody line 2"
    entry = commit_entry_from_block(block)
    assert entry is not None
    assert entry.sha == "deadbeef"
    assert entry.scope == "core"
    assert entry.breaking is True
    assert entry.tag == "v3.0.0"
    assert entry.body == "body line 1\nbody line 2"


# frob:tests tests/unit/test_gitlog_rendering.py::test_commit_entry_from_block_non_conventional_is_unknown_type
def test_commit_entry_from_block_non_conventional_is_unknown_type() -> None:
    """A subject that doesn't match the conventional-commit pattern still
    produces a `CommitEntry`, typed `"unknown"`."""
    block = "sha1\nsha1s\njust a plain commit message"
    entry = commit_entry_from_block(block)
    assert entry is not None
    assert entry.type == "unknown"
    assert entry.description == "just a plain commit message"


# frob:tests tests/unit/test_gitlog_rendering.py::test_parse_commits_skips_malformed_blocks
def test_parse_commits_skips_malformed_blocks() -> None:
    """`_parse_commits` skips blocks with no `---END---` marker and blank
    blocks, keeping only well-formed ones."""
    raw = (
        "---COMMIT---\n"
        "sha1\nsha1s\nfeat: good one\n\n\n"
        "---END---\n"
        "---COMMIT---\n"
        "no end marker here at all\n"
        "---COMMIT---\n"
        "\n"
        "---END---\n"
    )
    entries = parse_commits(raw)
    assert len(entries) == 1
    assert entries[0].description == "good one"
