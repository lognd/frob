"""T-2646: classify every local branch as merged / done-ticket / stranded.

WHY THIS EXISTS. This repo carries ~900+ local branches against a few
dozen worktrees (measured during T-2629). Most correspond to landed or
abandoned agent work and are never cleaned up, and even a fast scan over
that many branches is itself a performance problem (T-2629's own inline
`frob ticket doable` scan could not complete against this set). T-2646 is
the analysis step, deliberately separate from any deletion: report-only,
mirroring `frob.tickets._unlanded`'s own "read-only, no mutation" posture
for the same reason -- a dead agent's worktree commits survive on its
branch, and a clean-but-unlanded branch is invisible to `frob worktree
sweep` (which only judges the WORKTREE, not orphaned branches with no
worktree at all).

CLASSIFICATION (per branch, excluding `main` itself):

  (a) merged      -- `git merge-base --is-ancestor <branch> main` is true,
                      OR the branch's tree is byte-identical to `main`'s
                      (diverged history, identical content -- e.g. a
                      rebase-in-place). Provably fully contained in main;
                      safe to consider for deletion.
  (b) ticket-done  -- NOT merged, but every ticket id this branch's own
                      changed files signal (a `tickets/T-####/` path, or a
                      `frob:ticket T-####` directive-comment mention in a
                      non-ticket file, same two signals
                      `frob.tickets._unlanded` uses for the live "unlanded
                      leak" detector) resolves to a TERMINAL state
                      (`done`/`dropped`) on `main` -- active OR archived.
                      The ticket's own outcome is recorded on main even
                      though this exact branch never merged; likely safe,
                      but NOT proven byte-identical the way (a) is, so
                      still a human call before deletion.
  (c) stranded     -- NOT merged, and either no ticket signal resolves to
                      terminal on main, or there is no ticket signal at
                      all despite a non-empty diff from main. This is the
                      class that can contain real, never-landed work.
                      NEVER auto-deleted; surfaced individually for a
                      human decision, same posture as `_unlanded`'s own
                      "report-only, nothing lands/requeues/removes"
                      contract.

Deliberately plain `git` subprocess calls (mirroring `scripts/verify_
lands.py`'s own style) rather than importing `frob.tickets._unlanded`'s
private helpers -- this is a standalone audit script, not part of any
gate's call graph, and reuses only the CLASSIFICATION IDEA (T-1934/
T-1948's two signals + terminal-state resolution), not the code.
`_directive_ids_via_real_parser` is the one exception (T-2915): it calls
`frob.lang.parse_file`/`frob.graph.dsl.parse_directives` directly (the
same public-ish machinery `frob.tickets._unlanded`'s own T-2300 helper
uses), imported lazily and defensively (`ImportError` degrades to the
bare-regex fallback, never a crash) since this script is meant to be
runnable standalone even outside a fully-installed frob checkout.

Usage:
    python3 scripts/branch_stranded_work_analysis.py [--ref main]
        [--json OUT.json] [--limit N]

Exit code is always 0 -- this is a report, not a gate; a git failure on
one branch is recorded as an `error` entry for that branch and does not
abort the run.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
#: Repo root, derived from this script's own location (mirrors
#: `scripts/verify_lands.py::REPO`).
REPO = Path(__file__).resolve().parent.parent

#: Same two path/regex shapes `frob.tickets._unlanded` uses to recognize a
#: ticket-ledger path and a directive-comment mention -- duplicated here
#: deliberately (see module docstring: standalone script, not a gate
#: import) rather than importing a private `frob.tickets` symbol.
_TICKET_PATH_RE = re.compile(
    r"^tickets/(T-[0-9A-Za-z][0-9A-Za-z-]*)/(ticket\.md|done-report\.md)$"
)
_TICKET_DIRECTIVE_RE = re.compile(r"frob:ticket\s+(T-[0-9A-Za-z][0-9A-Za-z-]*)")
_STATE_RE = re.compile(r"(?m)^state:\s*(\S+)\s*$")
_TERMINAL_STATES = frozenset({"done", "dropped"})


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch.test_merged_when\
# _ancestor kind="unit"
class BranchResult(BaseModel):
    """One branch's classification -- `class_` is `"merged"`,
    `"ticket-done"`, `"stranded"`, or `"error"` (git failure on this
    branch alone, does not abort the run). A plain `pydantic.BaseModel`
    rather than `@dataclass` -- this repo's own convention (`CLAUDE.md`:
    "PREFER pydantic and typani"), and `@dataclass` additionally breaks
    under `tests/unit/conftest.py::_load_script`'s by-path module import
    (no `sys.modules` entry for `__module__` to resolve against)."""

    model_config = {}

    branch: str
    class_: str
    detail: str
    changed_files: int = 0
    ticket_ids: list[str] = Field(default_factory=list)


def _run(argv: tuple[str, ...]) -> tuple[int, str]:
    """Run `argv` under `REPO`, returning `(returncode, stdout)` -- never
    raises; a spawn failure reports as `(1, "")`."""
    try:
        proc = subprocess.run(
            argv, cwd=REPO, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return proc.returncode, proc.stdout


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestLocalBranches.test_excludes_ref\
# _and_blanks kind="unit"
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestLocalBranches.test_empty_on_git\
# _failure kind="unit"
def local_branches(ref: str) -> list[str]:
    """Every local branch name except `ref` itself, in `git branch`'s own
    order."""
    code, out = _run(("git", "branch", "--format=%(refname:short)"))
    if code != 0:
        return []
    return [
        stripped
        for line in out.splitlines()
        if (stripped := line.strip()) and stripped != ref
    ]


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestIsMerged.test_true_when_ancesto\
# r kind="unit"
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestIsMerged.test_false_when_not_an\
# cestor kind="unit"
def is_merged(branch: str, ref: str) -> bool:
    """True iff `branch` is a git ancestor of `ref` (fully contained)."""
    code, _ = _run(("git", "merge-base", "--is-ancestor", branch, ref))
    return code == 0


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestTreeIdentical.test_true_on_empt\
# y_diff kind="unit"
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestTreeIdentical.test_false_on_rea\
# l_diff kind="unit"
def tree_identical(branch: str, ref: str) -> bool:
    """True iff `branch` and `ref` point at byte-identical trees (diverged
    history via e.g. a rebase-in-place, but zero content difference)."""
    code, out = _run(("git", "diff", "--quiet", f"{ref}...{branch}"))
    # `git diff --quiet` exits 0 for no difference, 1 for a difference;
    # any other code (spawn failure, bad ref) is treated as "not proven
    # identical" -- never silently promoted to class (a).
    return code == 0


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestOwnChangedFiles.test_returns_di\
# ff_against_merge_base kind="unit"
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestOwnChangedFiles.test_empty_when\
# _merge_base_fails kind="unit"
def own_changed_files(branch: str, ref: str) -> list[str]:
    """Paths `branch` itself changed relative to its merge-base with
    `ref` -- the branch's OWN diff, not the union of everything `ref` has
    picked up since divergence (mirrors `frob.tickets._unlanded.
    _branch_own_changed_files`'s definition, reimplemented here for the
    same standalone-script reason the module docstring gives)."""
    code, base = _run(("git", "merge-base", ref, branch))
    base = base.strip()
    if code != 0 or not base:
        return []
    code, out = _run(("git", "diff", "--name-only", f"{base}..{branch}"))
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestBlobText.test_returns_stdout_on\
# _success kind="unit"
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestBlobText.test_none_when_path_do\
# es_not_exist kind="unit"
def blob_text(ref: str, path: str) -> str | None:
    """`git show <ref>:<path>`'s stdout, or `None` if it does not exist."""
    code, out = _run(("git", "show", f"{ref}:{path}"))
    if code != 0:
        return None
    return out


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestTicketStateOnMain.test_reads_ac\
# tive_ledger_state kind="unit"
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestTicketStateOnMain.test_falls_ba\
# ck_to_archive_path kind="unit"
def ticket_state_on_main(ticket_id: str, ref: str) -> str | None:
    """`ticket_id`'s `state:` field on `ref`, checking the active ledger
    path first and the v2-archive path second -- `None` if neither
    resolves (matches `frob.tickets._unlanded._ticket_state_on_main`'s
    own two-path lookup)."""
    for path in (
        f"tickets/{ticket_id}/ticket.md",
        f"tickets/archive/{ticket_id}/ticket.md",
    ):
        text = blob_text(ref, path)
        if text is None:
            continue
        match = _STATE_RE.search(text)
        if match is not None:
            return match.group(1)
    return None


#: T-2915: one reusable scratch file per suffix, mirroring `frob.tickets.
#: _unlanded._scratch_file_for_suffix` (T-2645) exactly -- a fresh
#: `tempfile.NamedTemporaryFile` per candidate is the same per-candidate
#: syscall tax T-2645 measured and fixed there; no reason to reintroduce
#: it here. This script has no threaded/concurrent caller (see the
#: module docstring), so reuse is safe by the same argument T-2645 made.
_SCRATCH_FILE_BY_SUFFIX: dict[str, str] = {}


def _scratch_file_for_suffix(suffix: str) -> str:
    """Return (creating once, lazily, per-process) the reusable temp-file
    path this process uses to feed `suffix`-typed blob content through
    `frob.lang.parse_file` (T-2915, mirrors `frob.tickets._unlanded`'s
    identical T-2645 helper)."""
    import tempfile

    cached = _SCRATCH_FILE_BY_SUFFIX.get(suffix)
    if cached is not None:
        return cached
    fd, path = tempfile.mkstemp(suffix=suffix)
    import os

    os.close(fd)
    _SCRATCH_FILE_BY_SUFFIX[suffix] = path
    return path


def _directive_ids_via_real_parser(text: str, path: str) -> frozenset[str] | None:
    """T-2915: the real-parse path for one blob's directive-comment scan
    -- parse `text` with this repo's own comment-DSL parser
    (`frob.lang.parse_file` + `frob.graph.dsl.parse_directives`, the SAME
    machinery `frob.tickets._unlanded._directive_ids_via_real_parser`
    uses) and return every `frob:ticket T-####` edge's target id, or
    `None` if `path`'s language is unsupported or the blob fails to
    parse at all -- the caller falls back to the bare regex in that case,
    exactly like `_unlanded`'s own T-2300 precedent. This is what
    sharpens the false-positive class the module docstring's "IMPORTANT"
    section documents: a real parse distinguishes a directive-POSITION
    comment from the identical text sitting inside a string literal or
    test fixture (measured: `tests/test_gates.py` alone carries 389
    literal "frob:ticket" occurrences in its own fixtures), which the
    bare regex cannot."""
    try:
        # frob:waive SYS003 reason="one-off scripts_ops measurement script, same \
        # exemption as scripts/measure_evidence_reach.py's frob.graph import: \
        # design/frob.strata Flow declarations are out of this ticket's scope (T-3177 \
        # scopes only this file), so a real Flow entry is not added here"
        from frob.graph import EdgeKind

        # frob:waive SYS003 reason="same one-off measurement-script exemption as the \
        # frob.graph import immediately above"
        from frob.graph.dsl import parse_directives

        # frob:waive SYS003 reason="same one-off measurement-script exemption as the \
        # frob.graph import immediately above"
        from frob.lang import parse_file
    except ImportError:
        return None

    suffix = Path(path).suffix
    scratch_path = _scratch_file_for_suffix(suffix)
    try:
        with open(scratch_path, "w", encoding="utf-8") as tmp:
            tmp.write(text)
        parsed_result = parse_file(Path(scratch_path))
    except OSError:
        return None
    if parsed_result.is_err:
        return None
    edges, _malformed = parse_directives(parsed_result.danger_ok)
    return frozenset(edge.target for edge in edges if edge.kind is EdgeKind.TICKET)


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestTicketIdsOnBranch.test_ledger_p\
# ath_yields_its_own_id kind="unit"
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestTicketIdsOnBranch.test_directiv\
# e_comment_in_non_ticket_file_is_found kind="unit"
def ticket_ids_on_branch(branch: str, changed: list[str]) -> set[str]:
    """Every ticket id `changed` signals for `branch` -- ledger paths plus
    a `frob:ticket T-####` directive-comment mention in the non-ticket
    files. T-2915: tries the REAL comment-DSL parser first
    (`_directive_ids_via_real_parser`) -- it can tell a directive-
    position comment apart from the identical text sitting in a string
    literal or test fixture, which the bare regex fallback below
    structurally cannot (the exact false-positive class this ticket
    exists to shrink). Falls back to the regex only when the real parser
    cannot handle `path` at all (unsupported language, `frob.lang`
    unavailable, or the blob fails to parse) -- narrowing false positives
    must never also narrow coverage for a language this repo's parser
    does not yet support."""
    ids: set[str] = set()
    for path in changed:
        match = _TICKET_PATH_RE.match(path)
        if match is not None:
            ids.add(match.group(1))
            continue
        if path.startswith("tickets/"):
            continue
        text = blob_text(branch, path)
        if text is None:
            continue
        real_ids = _directive_ids_via_real_parser(text, path)
        if real_ids is not None:
            ids.update(real_ids)
        else:
            ids.update(_TICKET_DIRECTIVE_RE.findall(text))
    return ids


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch.test_merged_when\
# _ancestor kind="unit"
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch.test_ticket_done\
# _when_all_ids_terminal kind="unit"
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch.test_stranded_wh\
# en_ticket_not_terminal kind="unit"
def classify_branch(branch: str, ref: str) -> BranchResult:
    """The full (a)/(b)/(c) decision for one branch -- see module
    docstring for the class definitions."""
    if is_merged(branch, ref):
        return BranchResult(branch=branch, class_="merged", detail=f"ancestor of {ref}")
    if tree_identical(branch, ref):
        return BranchResult(
            branch=branch,
            class_="merged",
            detail=f"tree identical to {ref} (diverged history only)",
        )

    changed = own_changed_files(branch, ref)
    if not changed:
        # Diverged history, empty diff against merge-base -- effectively
        # nothing to strand; treat as merged rather than manufacture a
        # class-(c) entry with no content behind it.
        return BranchResult(
            branch=branch, class_="merged", detail="empty diff vs merge-base"
        )

    ticket_ids = sorted(ticket_ids_on_branch(branch, changed))
    if not ticket_ids:
        return BranchResult(
            branch=branch,
            class_="stranded",
            detail=f"{len(changed)} file(s) changed, no ticket signal found",
            changed_files=len(changed),
            ticket_ids=ticket_ids,
        )

    states = {tid: ticket_state_on_main(tid, ref) for tid in ticket_ids}
    non_terminal = {
        tid: state for tid, state in states.items() if state not in _TERMINAL_STATES
    }
    if not non_terminal:
        return BranchResult(
            branch=branch,
            class_="ticket-done",
            detail=(
                f"{len(changed)} file(s) changed; "
                f"ticket(s) {ticket_ids} all terminal on {ref}"
            ),
            changed_files=len(changed),
            ticket_ids=ticket_ids,
        )
    return BranchResult(
        branch=branch,
        class_="stranded",
        detail=(
            f"{len(changed)} file(s) changed; "
            f"ticket(s) not terminal on {ref}: {non_terminal}"
        ),
        changed_files=len(changed),
        ticket_ids=ticket_ids,
    )


# frob:doc docs/audits/branch-stranded-work-2026-08-25.md#method
# frob:tests \
# tests/unit/test_branch_stranded_work_analysis.py::TestMain.test_reports_zero_branches\
# _cleanly kind="unit"
# frob:waive PERF003 reason="results list is bounded by this repo's own local-branch \
# count (in the hundreds, a one-shot CLI report, not a hot path); by_class groups it \
# once via setdefault, no compare-every-pair cross join over two large collections"
def main() -> int:
    """CLI entry: classify every local branch and print/write the report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="main")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    branches = local_branches(args.ref)
    if args.limit is not None:
        branches = branches[: args.limit]

    results: list[BranchResult] = []
    for branch in branches:
        try:
            results.append(classify_branch(branch, args.ref))
        except Exception as exc:  # noqa: BLE001 -- per-branch isolation, keep scanning
            results.append(
                BranchResult(
                    branch=branch, class_="error", detail=f"{type(exc).__name__}: {exc}"
                )
            )

    by_class: dict[str, list[BranchResult]] = {}
    for result in results:
        by_class.setdefault(result.class_, []).append(result)

    # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, same as \
    # scripts/check_summary.py's own identical bare-print waivers -- a one-shot report \
    # script run directly by a human/agent, not part of frob's own gate-rendered \
    # output surface"
    print(f"scanned {len(results)} branch(es) against {args.ref}")
    for class_ in ("merged", "ticket-done", "stranded", "error"):
        # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see above"
        print(f"  {class_}: {len(by_class.get(class_, []))}")
    # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see above"
    print()
    # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see above"
    print("stranded (class c) -- NEVER auto-delete, human review required:")
    for result in by_class.get("stranded", []):
        # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see above"
        print(f"  {result.branch}: {result.detail}")

    if args.json is not None:
        dump = json.dumps([r.model_dump() for r in results], indent=2) + "\n"
        args.json.write_text(dump, encoding="utf-8")
        # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, see above"
        print(f"\nwrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
