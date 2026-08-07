"""Shared observational-transparency property harness (T-1519, INV-050):
`check(S, C) == check(S, empty)` for every persistent cache under `.frob/`.

`test_gate_cache.py::TestColdDiffOracle` proved this pointwise for the gate
cache; this module lifts the same "arbitrary edit sequence, assert cold and
warm agree at every step" shape into one reusable driver so a new cache does
not need to reinvent the random-walk plumbing to get the same guarantee.

frob:tests tests/test_gate_cache.py::TestColdDiffOracle.test_cache_agrees_with_cold_across_random_edits
"""
# frob:ticket T-1519

from __future__ import annotations

import random
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

_log_prefix = "cache-transparency"

# frob:ticket T-1519
Fingerprint = TypeVar("Fingerprint")

# frob:ticket T-1519
#: The edit-kind vocabulary every parameterized transparency sweep below
#: draws from -- touch/rename/delete/revert/content-change, matching the
#: ticket's own enumeration. Not every driver needs every kind; callers pass
#: whichever subset makes sense for the surface under test.
EDIT_KINDS = ("edit", "add", "remove", "rename", "revert")


# frob:ticket T-1519
# frob:waive DUP001 reason="the git-init/commit/write trio is the established \
# real-git-fixture idiom this test module family repeats (tests/test_gates.py, \
# tests/test_ticket_land.py, tests/test_ticket_work_and_land_finish.py and siblings \
# all carry equivalent copies, several under this same verbatim waiver) -- extracting \
# one repo-wide shared conftest helper is a real, independent cleanup outside this \
# ticket's scope, not something to fold into its land"
def git_init(root: Path) -> None:
    """A minimal git repo, matching `tests/test_gate_cache.py::_git_init` --
    kept as a byte-for-byte duplicate rather than an import to avoid making
    this shared module depend on a single test file's private helper."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    if not any(root.iterdir()):
        (root / ".gitkeep").write_text("")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "base", "--allow-empty"], cwd=root, check=True
    )


# frob:ticket T-1519
# frob:waive DUP001 reason="the git-init/commit/write trio is the established \
# real-git-fixture idiom this test module family repeats (tests/test_gates.py, \
# tests/test_ticket_land.py, tests/test_ticket_work_and_land_finish.py and siblings \
# all carry equivalent copies, several under this same verbatim waiver) -- extracting \
# one repo-wide shared conftest helper is a real, independent cleanup outside this \
# ticket's scope, not something to fold into its land"
def git_commit_all(root: Path, message: str = "edit") -> None:
    """Stage and commit every working-tree change -- the mutation drivers
    below call this after each simulated edit so digest-keyed caches see a
    real, committed content change to key off of."""
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", message, "--allow-empty"], cwd=root, check=True
    )


# frob:ticket T-1519
def run_cold_warm_sweep(
    rng: random.Random,
    rounds: int,
    mutate: Callable[[random.Random, int], None],
    cold_fingerprint: Callable[[], Fingerprint],
    warm_fingerprint: Callable[[], Fingerprint],
) -> None:
    """Drive `rounds` arbitrary mutations via `mutate(rng, round_index)`,
    asserting `cold_fingerprint() == warm_fingerprint()` after every single
    round -- the observational-transparency theorem INV-050 states, checked
    the same way `TestColdDiffOracle` already checks it for the gate cache:
    a persistent, stale-but-present cache must never change what a caller
    observes versus a from-scratch (`empty` cache) evaluation.

    `mutate` is responsible for whatever filesystem/git side effects the
    cache under test keys off of (a content edit, a rename, a delete, a
    revert to a prior committed state, or a no-op round) -- this driver only
    owns the compare-and-assert loop, not the mutation vocabulary, so each
    cache's test module can express edits in its own natural terms."""
    for round_ in range(rounds):
        mutate(rng, round_)
        cold = cold_fingerprint()
        warm = warm_fingerprint()
        assert cold == warm, (
            f"{_log_prefix}: round {round_} disagreement -- cold={cold!r} warm={warm!r}"
        )
