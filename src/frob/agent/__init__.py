"""frob.agent -- dispatched-agent-facing helpers that are not themselves
CLI wiring (that lives in `frob.app.agent_runner`): today just `_brief`'s
`render_agent_brief`, the `frob agent brief <ticket>` implementation
(T-draft-df99eb2d). Split out of `frob.app.agent_runner` the same way
`frob.tickets` keeps its own composition helpers separate from
`frob.app.ticket_runner`'s CLI plumbing -- this package has no argparse
knowledge and can be imported/tested without going through the CLI at
all.
"""

from __future__ import annotations

from frob.agent._brief import render_agent_brief

__all__ = ["render_agent_brief"]
