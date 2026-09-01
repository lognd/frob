"""T-0176: `frob ticket land` -- one-command landing.

Fixture-repo tests reproducing the real incident classes the ticket body
names: a stale-base worktree silently deleting a feature main already
landed, a `tickets.md` both-sides-append textual conflict, and provisional
(draft) id finalization at land time. Uses real git subprocesses (matching
tests/test_tickets_collision.py's style) -- not mocks -- because the whole
point of `land` is real merge/conflict/deletion behavior.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import re
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from typani.result import Err, Ok, Result

import frob.tickets._land as _land_mod
import frob.tickets._land_compose as _land_compose_mod
import frob.tickets._land_finalize as _land_finalize_mod
import frob.tickets._land_git_ops as _land_git_ops_mod
import frob.tickets._land_ledger_merge as _land_ledger_merge_mod
import frob.tickets._land_merge_zones as _land_merge_zones_mod
import frob.tickets._land_release as _land_release_mod
import frob.tickets._land_squash as _land_squash_mod
from frob.gates import PreworkSweep, load_prework, record_prework, scope_digest
from frob.gitio import GitError, ProcResult, run_argv
from frob.graph import build_graph
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    set_done_report,
    transition,
)
from frob.tickets._land import land, splice_ledger
from frob.tickets._land_git_ops import _splice_and_stage_archive
from frob.tickets._models import (
    AcceptanceCriterion,
    DoneReportClaims,
    LandError,
    Ticket,
    render_claims_block,
)
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._store import (
    _serialize_ticket,
    archive_path,
    atomic_write,
    ledger_path,
    load_all,
    load_archive,
    v2_ticket_path,
    write_archive,
    write_ticket,
)
from tests._write_unchecked import _write_ticket_unchecked  # noqa: E402

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
