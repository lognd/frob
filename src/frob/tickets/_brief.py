"""`frob ticket brief` (T-0568): compose the complete agent mission
briefing for one ticket -- body+acceptance, scope+lease status, the
agent-playbook's own hard-rule sections (parsed from its headings, not
hardcoded), best-effort targeted verify commands inferred from scope,
a gate-baseline summary, and the REL/land rules -- so a dispatch prompt
collapses to two lines instead of ~400 hand-typed words
(docs/modules/tickets.md#frob-ticket-brief-t-0568)."""
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.tickets._models import Ticket

# frob:ticket T-0568
_PLAYBOOK_REL = Path("docs/guides/agent-playbook.md")
# frob:ticket T-0568
_SECTION_RE = re.compile(r"^## (\d+[a-z]?)\.\s+(.+)$")


# frob:ticket T-0568
# frob:ticket T-0601
class _PlaybookSection(BaseModel):
    """One numbered hard-rule section of the agent playbook: its number
    (e.g. "1b"), title, and full body text up to the next `## ` heading."""

    model_config = ConfigDict(frozen=True)

    number: str
    title: str
    body: str


# frob:ticket T-0568
# frob:tests tests/test_tickets_brief.py::TestParsePlaybookSections.test_parses_numbered_headings_only  # noqa: E501
# frob:ticket T-0601
def _parse_playbook_sections(text: str) -> tuple[_PlaybookSection, ...]:
    """Parse every numbered `## N[.letter]. Title` heading in `text` into a
    `PlaybookSection` (T-0568): data-driven off the playbook's own
    headings, not a hand-copied list that drifts the moment a section is
    renumbered or added. A non-numbered `## ` heading (e.g. "## See also")
    is not a hard-rule section and is excluded; its body is still
    correctly excluded from the PRECEDING numbered section since any
    `## ` line (numbered or not) ends the current section's body span.
    """
    lines = text.splitlines()
    sections: list[_PlaybookSection] = []
    i = 0
    while i < len(lines):
        match = _SECTION_RE.match(lines[i])
        if match is None:
            i += 1
            continue
        number, title = match.groups()
        body_lines: list[str] = []
        j = i + 1
        while j < len(lines) and not lines[j].startswith("## "):
            body_lines.append(lines[j])
            j += 1
        body = "\n".join(body_lines).strip("\n")
        sections.append(_PlaybookSection(number=number, title=title, body=body))
        i = j
    return tuple(sections)


# frob:ticket T-0568
# frob:tests tests/test_tickets_brief.py::TestLoadPlaybookSections.test_reads_real_file
# frob:ticket T-0601
def _load_playbook_sections(root: Path) -> tuple[_PlaybookSection, ...]:
    """`_parse_playbook_sections` over `root`'s `docs/guides/agent-
    playbook.md`, or empty if the file does not exist (T-0568) -- a repo
    without this playbook (a sibling repo the pattern has not spread to
    yet) gets a briefing with no hard-rule section rather than a hard
    failure; every OTHER section of the brief is still useful on its own.
    """
    path = root / _PLAYBOOK_REL
    if not path.is_file():
        return ()
    return _parse_playbook_sections(path.read_text(encoding="utf-8"))


# frob:ticket T-0568
# frob:tests tests/test_tickets_brief.py::TestInferVerifyCommands.test_scope_naming_tests_dir_is_used_directly  # noqa: E501
# frob:ticket T-0601
def _infer_verify_commands(root: Path, ticket: Ticket) -> tuple[str, ...]:
    """Best-effort exact verify commands for `ticket`'s declared scope
    (T-0568): always the scoped gate check, plus a targeted `pytest`
    invocation over any test files the scope already names directly, or
    (failing that) any test file under `root/tests` whose stem contains a
    scope entry's own stem -- a real filesystem lookup, not a guess from
    naming convention alone."""
    commands: list[str] = [f"uv run frob check --ticket {ticket.id}"]

    test_globs = [
        entry
        for entry in ticket.scope
        if entry.startswith("tests/") or "/tests/" in entry
    ]
    if test_globs:
        joined = " ".join(test_globs)
        commands.append(f'uv run pytest {joined} -q -o addopts=""')
        return tuple(commands)

    tests_dir = root / "tests"
    candidates: set[str] = set()
    if tests_dir.is_dir():
        for entry in ticket.scope:
            stem = Path(entry.rstrip("*/")).stem.lstrip("_")
            if not stem or stem in ("*", "**"):
                continue
            # frob:waive WALK001 reason="tests_dir (root/tests) is a small, \
            # already-scoped test-source subtree with no nested .git/.venv/ \
            # node_modules/build/dist/target to prune -- excludes.walk_pruned \
            # would add a filter that never fires here, not change behavior"
            for test_file in tests_dir.rglob(f"*{stem}*.py"):
                candidates.add(str(test_file.relative_to(root)))
    if candidates:
        joined = " ".join(sorted(candidates))
        commands.append(f'uv run pytest {joined} -q -o addopts=""')
    return tuple(commands)


# frob:ticket T-0568
# frob:tests tests/test_tickets_brief.py::TestGateBaselineSummary.test_missing_baseline
# frob:ticket T-0601
def _gate_baseline_summary(root: Path) -> str:
    """One-line status of `root`'s stamped `frob check` baseline (T-0568) --
    tells the agent whether `--delta` will report only new violations or
    degrade to the full violation set (docs/guides/agent-playbook.md#6)."""
    baseline = root / ".frob" / "baseline"
    if not baseline.is_file():
        return (
            "no baseline stamped -- run `uv run frob check --stamp-baseline` "
            "before starting, then `--delta` reports only NEW violations"
        )
    return (
        f"baseline stamped ({baseline} exists) -- use `uv run frob check "
        "--delta --ticket <id>` to see only violations introduced since it "
        "was stamped; re-stamp if the tree has moved significantly"
    )


# frob:ticket T-0568
# frob:tests tests/test_tickets_brief.py::TestCurrentVersion.test_reads_project_version
# frob:ticket T-0601
def _current_version(root: Path) -> str | None:
    """The `[project].version` string from `root/pyproject.toml`, or
    `None` if the file/key is absent (T-0568) -- degrades the REL/land
    rules text gracefully instead of failing the whole briefing."""
    path = root / "pyproject.toml"
    if not path.is_file():
        return None
    with path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("project", {}).get("version")


# frob:ticket T-0568
_REL_LAND_TEMPLATE = (
    "REL/land rules: a public API change needs a REL001 version bump "
    "(current pyproject.toml version: {version}) plus a CHANGELOG.md "
    "entry before `frob check` goes green. Do NOT push or merge to main "
    "from a worktree -- commit per ticket, write a Done report + record "
    "evidence, then `frob ticket close <id>` (or leave it for the "
    "reviewer in a review-gated flow) -- the coordinator lands via `frob "
    "ticket land`."
)


# frob:ticket T-0568
# frob:ticket T-0601
def _rel_land_rules(root: Path) -> str:
    """`_REL_LAND_TEMPLATE` filled in with `_current_version` (T-0568), or
    "unknown" if `pyproject.toml` could not be read."""
    version = _current_version(root)
    return _REL_LAND_TEMPLATE.format(version=version or "unknown")


# frob:ticket T-0568
# frob:doc docs/modules/tickets.md#frob-ticket-brief-t-0568
# frob:tests tests/test_tickets_brief.py::TestBriefTicket.test_composes_full_briefing
# frob:ticket T-0601
def compose_brief(root: Path, ticket: Ticket, lease_holders: tuple) -> str:
    """Render the complete T-0568 mission briefing for `ticket`: body +
    acceptance, scope + any colliding lease holders (`lease_holders`, the
    `leased_by` result the caller already computed), the playbook's
    hard-rule sections (`_load_playbook_sections`), inferred verify
    commands (`_infer_verify_commands`), the gate-baseline summary
    (`_gate_baseline_summary`), and the REL/land rules (`_rel_land_rules`)
    -- everything a dispatch prompt used to hand-type, in one call."""
    lines: list[str] = [f"# Mission briefing: {ticket.id} -- {ticket.title}", ""]

    lines.append(f"Kind: {ticket.kind.value}  Priority: {ticket.priority.value}")
    lines.append("")
    lines.append("## Description + plan")
    lines.append(ticket.body.strip() or "(no body)")
    lines.append("")

    if ticket.acceptance:
        lines.append("## Acceptance")
        # T-0572: each criterion is a {text, evidence} AcceptanceCriterion,
        # not a bare string -- show its bound-evidence status alongside the
        # text so a dispatch prompt surfaces which criteria still need
        # `frob ticket evidence <id> <node-id> --accepts <index>`.
        for i, item in enumerate(ticket.acceptance):
            status = f"bound({list(item.evidence)})" if item.evidence else "UNBOUND"
            lines.append(f"- [{i}] {status}: {item.text}")
        lines.append("")

    lines.append("## Scope + leases")
    if ticket.scope:
        lines.extend(f"- {glob}" for glob in ticket.scope)
    else:
        lines.append("(no scope declared)")
    if lease_holders:
        lines.append("")
        lines.append("Blocked by an active lease:")
        for holder_id, glob in lease_holders:
            lines.append(f"- {holder_id} holds {glob}")
    lines.append("")

    sections = _load_playbook_sections(root)
    if sections:
        lines.append("## Playbook hard rules")
        for section in sections:
            lines.append(f"### {section.number}. {section.title}")
            lines.append(section.body)
            lines.append("")

    lines.append("## Verify")
    for command in _infer_verify_commands(root, ticket):
        lines.append(f"- `{command}`")
    lines.append("")

    lines.append("## Gate baseline")
    lines.append(_gate_baseline_summary(root))
    lines.append("")

    lines.append(_rel_land_rules(root))

    return "\n".join(lines) + "\n"
