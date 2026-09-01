"""T-0176: `frob ticket land` -- one-command landing.

Fixture-repo tests reproducing the real incident classes the ticket body
names: a stale-base worktree silently deleting a feature main already
landed, a `tickets.md` both-sides-append textual conflict, and provisional
(draft) id finalization at land time. Uses real git subprocesses (matching
tests/test_tickets_collision.py's style) -- not mocks -- because the whole
point of `land` is real merge/conflict/deletion behavior.
"""

from __future__ import annotations

import pytest

# frob:ticket T-2099
#: This module's 275 tests spawn real `git`/subprocesses against real temp
#: repos (module docstring above). Under the repo default `-n auto
#: --dist=loadgroup` they scatter across xdist workers and contend rather
#: than parallelise -- measured exceeding the 540s foreground budget where
#: the same file finishes serially in well under it. `heavy_subprocess`
#: (registered in `pyproject.toml`, consumed by `tests/conftest.py`'s
#: `pytest_collection_modifyitems`) puts every test in this module into
#: one `xdist_group` keyed on this module's own name, so xdist runs them
#: serially on a single worker instead of scattering them -- while still
#: leaving that worker free to run in parallel with every OTHER file.
pytestmark = pytest.mark.heavy_subprocess
