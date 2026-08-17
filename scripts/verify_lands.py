"""Verify that claimed land commits are genuinely ancestors of main.

WHY THIS EXISTS. An agent's Done report is not evidence. Several land
reports in this repo have claimed `verified=True` while the work was NOT on
main -- in one case a ticket read `done` with its entire deliverable absent,
four separate times. The only trustworthy check is
`git merge-base --is-ancestor <sha> <ref>`, and running it by hand invites
the other failure this guards against: a mistyped short sha reports MISSING
for work that actually landed, which happened twice.

Pass full shas when you have them; this script reports a bad/unknown sha as
UNKNOWN-SHA rather than MISSING, so a typo is never mistaken for lost work.

T-2220: a ticket id (`T-####`) is also accepted, resolved via that ticket's
own persisted `land_commit` field (`frob.tickets._models.Ticket.land_commit`
-- written by the land path itself, never lexically guessed from a commit
subject: standing directive, token/grammar not text match). A `--plan` land
carries no ticket id in its own commit subject at all
(`chore(tickets): land --plan`), which is exactly why a ticket id can no
longer be resolved by grepping git history the way an id-titled `land <id>`
commit subject could be -- see `Ticket.land_commit`'s docstring for who
writes it. A ticket id that resolves to no ticket at all, and one that
resolves to a ticket never landed (`land_commit` still `None`), are reported
as two DISTINCT outcomes -- never conflated with each other or with
UNKNOWN-SHA, same "two outcomes must stay lexically distinct" discipline
`resolve`/`is_ancestor` already apply to a plain sha.

Usage:
    python3 scripts/verify_lands.py <sha-or-ticket-id> [...] [--ref main]
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

# frob:doc docs/guides/coordinator-scripts.md#verify_lands-constants
#: Repo root, derived from this script's own location.
REPO = Path(__file__).resolve().parent.parent

# frob:ticket T-2220
#: Shape of a real (non-draft) ticket id -- deliberately permissive on
#: digit count (frob.tickets._store._TICKET_ID_RE pins `T-\d{4}`, but this
#: script only needs to tell "looks like a ticket id" apart from "looks like
#: a sha" for a CLI argument, not validate an id against the ledger's own
#: allocator -- `_load_land_commit` below does the real existence check).
_TICKET_ID_RE = re.compile(r"^T-[0-9]+$")


# frob:doc docs/guides/coordinator-scripts.md#load_land_commit
# frob:ticket T-2220
# frob:tests tests/unit/test_coordinator_scripts.py::TestLoadLandCommit.test_returns_land_commit_for_a_landed_ticket  # noqa: E501
# frob:tests tests/unit/test_coordinator_scripts.py::TestLoadLandCommit.test_returns_none_for_an_unlanded_ticket  # noqa: E501
# frob:tests tests/unit/test_coordinator_scripts.py::TestLoadLandCommit.test_returns_missing_for_an_unknown_ticket_id  # noqa: E501
def load_land_commit(ticket_id: str) -> str | None | Exception:
    """`ticket_id`'s persisted `land_commit` field: a sha string if it
    landed, `None` if the ticket exists but was never landed (or predates
    this field), or a `KeyError` INSTANCE (never raised -- returned, so the
    caller can print a distinct message) if no such ticket exists at all.
    Imports `frob.tickets` lazily so a plain-sha invocation of this script
    never pays for it."""
    from frob.tickets import _load_one

    loaded = _load_one(REPO, ticket_id)
    if loaded.is_err:
        return KeyError(ticket_id)
    return loaded.danger_ok.land_commit


def _git(args: list[str]) -> subprocess.CompletedProcess:
    """Run git in the repo root, never raising on non-zero exit."""
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


# frob:doc docs/guides/coordinator-scripts.md#resolve
# frob:ticket T-1863
# frob:tests tests/unit/test_coordinator_scripts.py::TestResolve.test_resolves_full_sha
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestResolve.test_unknown_sha_returns_none
def resolve(sha: str) -> str | None:
    """Full commit id for `sha`, or None when git cannot resolve it."""
    done = _git(["rev-parse", "--verify", f"{sha}^{{commit}}"])
    return done.stdout.strip() if done.returncode == 0 else None


# frob:doc docs/guides/coordinator-scripts.md#is_ancestor
# frob:ticket T-1863
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestIsAncestor.test_true_when_ancestor
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestIsAncestor.test_false_when_not_ancestor
def is_ancestor(sha: str, ref: str) -> bool:
    """True when `sha` is an ancestor of `ref` (i.e. it really landed)."""
    return _git(["merge-base", "--is-ancestor", sha, ref]).returncode == 0


# frob:doc docs/guides/coordinator-scripts.md#subject
# frob:ticket T-1863
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestSubject.test_returns_commit_subject
def subject(sha: str) -> str:
    """One-line subject for `sha`, for eyeballing that it is the right commit."""
    return _git(["log", "-1", "--format=%s", sha]).stdout.strip()


# frob:doc docs/guides/coordinator-scripts.md#verify_lands-main
# frob:ticket T-1863
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain.test_distinguishes_unknow\
# n_from_missing
def main() -> int:
    """Check every sha/ticket-id against `ref`; exit 1 if any is missing,
    unknown, or (T-2220) an unrecognized/never-landed ticket id."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "shas", nargs="+", help="commit sha(s) and/or ticket id(s) (T-####)"
    )
    parser.add_argument("--ref", default="HEAD")
    args = parser.parse_args()

    bad = 0
    for arg in args.shas:
        sha = arg
        label = arg
        if _TICKET_ID_RE.match(arg):
            # frob:ticket T-2220
            land_commit = load_land_commit(arg)
            if isinstance(land_commit, Exception):
                print(f"UNKNOWN-TICKET {arg}  (no such ticket in this repo)")
                bad += 1
                continue
            if land_commit is None:
                print(
                    f"NOT-LANDED     {arg}  (ticket exists, land_commit not "
                    "recorded -- never landed, or landed before T-2220)"
                )
                bad += 1
                continue
            sha = land_commit
            label = f"{arg} ({sha[:12]})"

        full = resolve(sha)
        if full is None:
            print(f"UNKNOWN-SHA {label}  (typo? not a commit in this repo)")
            bad += 1
        elif is_ancestor(full, args.ref):
            print(f"ON {args.ref:9} {full[:12]}  {subject(full)[:80]}")
        else:
            print(f"MISSING    {full[:12]}  NOT an ancestor of {args.ref}")
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
