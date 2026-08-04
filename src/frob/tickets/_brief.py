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

from frob.tickets._models import Ticket, TicketQueue, TicketState, TicketTier

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
            # node_modules/build/dist/target to prune -- excludes.walk_pruned would \
            # add a filter that never fires here, not change behavior"
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


# frob:ticket T-1347
_CONCURRENCY_HAZARDS = (
    "- Commit any new/changed test BEFORE running `frob ticket land` -- a "
    "land killed mid-auto-fix can garble a source file, and the obvious "
    "`git checkout -- <file>` recovery then silently discards uncommitted "
    "work in OTHER files too (T-1338).",
    "- A transient DirtyMain refusal from `frob ticket land` under "
    "concurrency is EXPECTED (a sibling agent's land is in flight) -- "
    "wait and retry; never touch main by hand to clear it.",
)


# frob:ticket T-1347
# frob:tests tests/test_tickets_brief.py::TestConcurrentLeases.test_lists_others
# frob:waive DUP001 reason="the DUP001 hits here are all rung=r2 95%-similar matches \
# against unrelated modules (strata compliance-catalog test fixtures, \
# frob.gates._coverage._module_join_fraction, frob.gates._refs._native_stub_pairs, \
# frob.vet._containment._finding_for_pair) that share only the generic \
# filter-then-format-a-list-of-lines shape, not this function's actual concern \
# (rendering one ticket's do-not-touch scope entries); extracting a shared helper \
# across those unrelated domains would not improve cohesion, it would just add an \
# indirection with no real shared behavior"
def _concurrent_leases_section(
    ticket: Ticket, concurrent: tuple[Ticket, ...]
) -> tuple[str, ...]:
    """Lines for a "Concurrent leases (do NOT touch)" section (T-1347)
    listing every OTHER in-progress ticket's id, title, and scope globs,
    resolved live at brief time -- the one piece of a dispatch briefing a
    coordinator otherwise had to hand-write per wave. Excludes `ticket`
    itself; returns an empty tuple (no section) if `concurrent` is empty."""
    others = tuple(t for t in concurrent if t.id != ticket.id)
    if not others:
        return ()
    lines: list[str] = ["## Concurrent leases (do NOT touch)"]
    for other in others:
        globs = ", ".join(other.scope) if other.scope else "(no scope declared)"
        lines.append(f"- {other.id} -- {other.title}: {globs}")
    lines.append("")
    return tuple(lines)


# frob:ticket T-1347
def _scope_and_leases_section(ticket: Ticket, lease_holders: tuple) -> tuple[str, ...]:
    """Lines for `compose_brief`'s "Scope + leases" section (T-1347 split,
    behavior unchanged): the declared scope globs, plus any active
    `leased_by` collision against `ticket`'s own scope."""
    lines: list[str] = ["## Scope + leases"]
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
    return tuple(lines)


# frob:ticket T-1347
def _playbook_hard_rules_section(root: Path) -> tuple[str, ...]:
    """Lines for `compose_brief`'s "Playbook hard rules" section (T-1347
    split, behavior unchanged): every parsed playbook section verbatim, or
    empty if `root` has no playbook at all."""
    sections = _load_playbook_sections(root)
    if not sections:
        return ()
    lines: list[str] = ["## Playbook hard rules"]
    for section in sections:
        lines.append(f"### {section.number}. {section.title}")
        lines.append(section.body)
        lines.append("")
    return tuple(lines)


# frob:ticket T-0568
# frob:ticket T-1347
# frob:doc docs/modules/tickets.md#frob-ticket-brief-t-0568
# frob:tests tests/test_tickets_brief.py::TestBriefTicket.test_composes_full_briefing
# frob:tests tests/test_tickets_brief.py::TestBriefTicket.test_concurrent_leases
# frob:ticket T-0601
def compose_brief(
    root: Path,
    ticket: Ticket,
    lease_holders: tuple,
    concurrent: tuple[Ticket, ...] = (),
) -> str:
    """Render the complete T-0568 mission briefing for `ticket`: body +
    acceptance, scope + any colliding lease holders (`lease_holders`, the
    `leased_by` result the caller already computed), a "Concurrent leases
    (do NOT touch)" section listing every OTHER in-progress ticket's id,
    title, and scope globs (`concurrent`, T-1347 -- the single most
    important thing a dispatched agent needs under concurrency), the
    playbook's hard-rule sections (`_load_playbook_sections`), inferred
    verify commands (`_infer_verify_commands`), the gate-baseline summary
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

    lines.extend(_scope_and_leases_section(ticket, lease_holders))
    lines.extend(_concurrent_leases_section(ticket, concurrent))

    lines.append("## Concurrency hazards")
    lines.extend(_CONCURRENCY_HAZARDS)
    lines.append("")

    lines.extend(_playbook_hard_rules_section(root))

    lines.append("## Verify")
    for command in _infer_verify_commands(root, ticket):
        lines.append(f"- `{command}`")
    lines.append("")

    lines.append("## Gate baseline")
    lines.append(_gate_baseline_summary(root))
    lines.append("")

    lines.append(_rel_land_rules(root))

    return "\n".join(lines) + "\n"


# frob:ticket T-1243
def _cluster_open_blockers(queue: TicketQueue, t: Ticket) -> tuple[str, ...]:
    """`t`'s blockers not yet DONE/DROPPED (T-1243) -- the same open-
    blocker rule `frob.tickets._doable._open_blockers` applies, duplicated
    here (rather than imported) only because `_doable.py` late-imports
    `_open_blockers` from this package's `__init__` at call time, and this
    module is loaded BEFORE `__init__` finishes assembling it (the same
    load-order constraint several other split-module helpers already work
    around by late-importing instead; this one instead just keeps its own
    tiny copy, since the rule itself is one line of real logic)."""
    return tuple(
        blocker_id
        for blocker_id in t.blocked_by
        if queue.tickets.get(blocker_id) is None
        or queue.tickets[blocker_id].state
        not in (TicketState.DONE, TicketState.DROPPED)
    )


# frob:ticket T-1243
def _topo_order_cluster(
    dispatchable: list[Ticket],
) -> tuple[Ticket, ...]:
    """Kahn's-algorithm topological order over `dispatchable`'s INTERNAL
    (intra-cluster) `blocked_by` edges (T-1243), ties broken by the same
    priority/age order `doable` uses (`_doable_sort_key`) -- a heap keyed
    by that same tuple instead of re-`sorted()`ing the whole frontier list
    per emitted ticket (PERF004: the naive re-sort-every-iteration shape
    this replaces). Any leftover (a `blocked_by` CYCLE among cluster
    members -- should never happen in a well-formed ledger, but never
    silently drop work) is appended, priority/age ordered, after every
    resolvable ticket."""
    import heapq

    from frob.tickets import _doable_sort_key

    by_id = {t.id: t for t in dispatchable}
    remaining_blockers: dict[str, set[str]] = {
        t.id: {b for b in _cluster_open_blockers_of(t, by_id)} for t in dispatchable
    }
    heap: list[tuple] = [
        (_doable_sort_key(t), t.id)
        for t in dispatchable
        if not remaining_blockers[t.id]
    ]
    heapq.heapify(heap)

    ordered: list[Ticket] = []
    placed: set[str] = set()
    while heap:
        _key, ticket_id = heapq.heappop(heap)
        ticket = by_id[ticket_id]
        ordered.append(ticket)
        placed.add(ticket_id)
        for tid, blockers in remaining_blockers.items():
            if tid in placed or ticket_id not in blockers:
                continue
            blockers.discard(ticket_id)
            if not blockers:
                heapq.heappush(heap, (_doable_sort_key(by_id[tid]), tid))

    leftover = sorted(
        (t for t in dispatchable if t.id not in placed), key=_doable_sort_key
    )
    ordered.extend(leftover)
    return tuple(ordered)


# frob:ticket T-1243
def _cluster_open_blockers_of(t: Ticket, by_id: dict) -> tuple[str, ...]:
    """The subset of `t.blocked_by` that names another cluster MEMBER
    (`by_id`, T-1243) -- an EXTERNAL blocker is not this function's
    concern (`cluster_descendants` already filtered those out before
    calling `_topo_order_cluster`); this only isolates the intra-cluster
    edges the topological sort itself needs to sequence."""
    return tuple(b for b in t.blocked_by if b in by_id)


# frob:ticket T-1243
# frob:doc docs/modules/tickets.md#frob-ticket-brief---cluster-t-1243
# frob:tests tests/test_tickets_brief.py::TestClusterDescendants.test_dependency_order_respects_intra_cluster_blocked_by  # noqa: E501
# frob:tests tests/test_tickets_brief.py::TestClusterDescendants.test_excludes_leaf_blocked_from_outside_the_cluster  # noqa: E501
# frob:tests tests/test_tickets_brief.py::TestClusterDescendants.test_unknown_cluster_returns_empty  # noqa: E501
def cluster_descendants(queue: TicketQueue, cluster_id: str) -> tuple[Ticket, ...]:
    """Dependency-ordered, currently-dispatchable LEAF descendants of the
    epic/story `cluster_id` (T-1243): every `TicketTier.TICKET` descendant
    (`epic_rollup`'s parent-chain walk, any depth) still in {queued,
    planned} whose open blockers (if any) are ALL other members of this
    same cluster -- a leaf blocked by something OUTSIDE the cluster is not
    yet dispatchable as part of this mission and is excluded, matching
    `frob.tickets._doable._doable_candidates`'s own no-open-external-
    blocker rule. Ordered by `_topo_order_cluster`'s Kahn's-algorithm walk
    over the INTERNAL (intra-cluster) `blocked_by` edges, so a dependent
    ticket never precedes the dependency it needs. Returns an empty tuple
    if `cluster_id` does not resolve or has no dispatchable leaf
    descendants yet."""
    from frob.tickets import epic_rollup

    rollup = epic_rollup(queue, cluster_id)
    if rollup.is_err:
        return ()
    descendant_ids = {t.id for t in rollup.danger_ok.descendants}
    leaves = [
        t
        for t in rollup.danger_ok.descendants
        if t.tier is TicketTier.TICKET
        and t.state in (TicketState.QUEUED, TicketState.PLANNED)
    ]
    dispatchable = [
        t
        for t in leaves
        if all(b in descendant_ids for b in _cluster_open_blockers(queue, t))
    ]
    return _topo_order_cluster(dispatchable)


# frob:ticket T-1243
# frob:doc docs/modules/tickets.md#frob-ticket-brief---cluster-t-1243
# frob:tests tests/test_tickets_brief.py::TestClusterUnionScope.test_deduplicates_and_preserves_first_seen_order  # noqa: E501
def cluster_union_scope(members: tuple[Ticket, ...]) -> tuple[str, ...]:
    """The deduplicated, order-preserving union of every member ticket's
    declared `scope` globs (T-1243) -- the single lease a `frob ticket work
    --cluster` mission acquires across every ticket it leases into one
    worktree."""
    seen: list[str] = []
    seen_set: set[str] = set()
    for t in members:
        for glob in t.scope:
            if glob not in seen_set:
                seen_set.add(glob)
                seen.append(glob)
    return tuple(seen)


# frob:ticket T-1243
# frob:doc docs/modules/tickets.md#frob-ticket-brief---cluster-t-1243
# frob:tests tests/test_tickets_brief.py::TestClusterBrief.test_composes_one_briefing_for_the_whole_cluster  # noqa: E501
def compose_cluster_brief(
    root: Path,
    cluster: Ticket,
    members: tuple[Ticket, ...],
) -> str:
    """Render the T-1243 cluster mission briefing for `cluster` (an epic or
    story): the playbook hard-rule sections and REL/land rules ONCE (not
    once per member, the whole point of a cluster brief over N separate
    `compose_brief` calls), the union scope lease (`cluster_union_scope`)
    the mission acquires, then each `members` ticket's own body+acceptance+
    scope in `cluster_descendants`' dependency order, plus an explicit land-
    cadence reminder: ONE `frob ticket land` per member ticket as it closes,
    never one mega-land for the whole cluster."""
    lines: list[str] = [
        f"# Cluster mission briefing: {cluster.id} -- {cluster.title}",
        "",
        f"Kind: {cluster.kind.value}  Tier: {cluster.tier.value}",
        f"{len(members)} dispatchable member ticket(s), dependency-ordered below.",
        "",
    ]

    lines.append("## Union scope lease")
    union_scope = cluster_union_scope(members)
    if union_scope:
        lines.extend(f"- {glob}" for glob in union_scope)
    else:
        lines.append("(no scope declared across any member)")
    lines.append("")

    lines.extend(_playbook_hard_rules_section(root))

    lines.append("## Land cadence")
    lines.append(
        "Land ONE ticket at a time, in the order below, as each closes -- "
        "never one mega-land for the whole cluster. The union scope lease "
        "above is held by this single worktree for the whole mission; each "
        "member's own scope releases individually the moment that ticket "
        "closes, exactly like an ordinary single-ticket lease."
    )
    lines.append("")

    for i, ticket in enumerate(members, start=1):
        lines.append(f"## Member {i}/{len(members)}: {ticket.id} -- {ticket.title}")
        lines.append(f"Kind: {ticket.kind.value}  Priority: {ticket.priority.value}")
        lines.append("")
        lines.append(ticket.body.strip() or "(no body)")
        lines.append("")
        if ticket.acceptance:
            lines.append("### Acceptance")
            for idx, item in enumerate(ticket.acceptance):
                status = f"bound({list(item.evidence)})" if item.evidence else "UNBOUND"
                lines.append(f"- [{idx}] {status}: {item.text}")
            lines.append("")
        lines.append("### Scope")
        if ticket.scope:
            lines.extend(f"- {glob}" for glob in ticket.scope)
        else:
            lines.append("(no scope declared)")
        lines.append("")

    lines.append(_rel_land_rules(root))

    return "\n".join(lines) + "\n"
