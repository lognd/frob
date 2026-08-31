"""T-3190: this repo's own `[tickets].default_milestone` in `frob.toml`
must never re-conflate "shipping" with "1.0.0" -- the owner-recorded
milestone decision (docs/modules/tickets-lifecycle.md#adopting-real-
milestones-t-3190) names an earlier real milestone, "0.530.0" (a green
three-platform CI matrix plus a working PyPI install), while
`default_milestone` stays the terminal fallback for everything else.

Reads `frob.toml` via `frob.tickets._doable._default_milestone` (already
declared `fs.read` for its own node, T-2576) rather than a raw
`Path.read_text` in this test file, so this regression check needs no
new `design/frob.strata` capability declaration of its own.
"""

from __future__ import annotations

from pathlib import Path

from frob.tickets._doable import _default_milestone

_REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDefaultMilestoneDoesNotConflateShippingWithOnePointZero:
    """T-3190 acceptance 1: `default_milestone` no longer conflates
    shipping with `1.0.0`."""

    # frob:tests tests/test_config_frob_toml_milestone.py::TestDefaultMilestoneDoesNotConflateShippingWithOnePointZero.test_default_milestone_is_configured  # noqa: E501
    def test_default_milestone_is_configured(self) -> None:
        """`default_milestone` must stay set -- removing it before the
        `0.530.0` blocking set is confirmed would turn every undeclared
        ticket into a MILE003 ERROR at once (frob.toml's own T-3190
        comment)."""
        assert _default_milestone(_REPO_ROOT) is not None, (
            "[tickets].default_milestone was removed from frob.toml -- "
            "every ticket without an explicit milestone would now fail "
            "MILE003 (unresolvable effective milestone) at once"
        )

    # frob:tests tests/test_config_frob_toml_milestone.py::TestDefaultMilestoneDoesNotConflateShippingWithOnePointZero.test_default_milestone_is_not_the_publish_milestone  # noqa: E501
    def test_default_milestone_is_not_the_publish_milestone(self) -> None:
        """The `0.530.0` publish-blocking milestone (T-3190's owner
        decision) must stay a real, EARLIER, explicitly-declared value --
        never the catch-all default. If a future edit sets `default_
        milestone = "0.530.0"`, every ticket in the queue would silently
        become "publish-blocking" again, exactly the conflation this
        ticket exists to remove."""
        assert _default_milestone(_REPO_ROOT) != "0.530.0", (
            "[tickets].default_milestone must not equal the publish "
            "milestone (0.530.0) -- that would make every undeclared "
            "ticket publish-blocking again, the exact conflation T-3190 "
            "removed"
        )
