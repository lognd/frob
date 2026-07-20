"""Error vocabulary for the render layer (T-0448).

Rendering is almost always infallible (plain text formatting), but a small
number of element constructors validate their input (a status pill's status
name, a ticket-id's shape) -- those return `typani.Result` per repo
convention rather than raising, since a caller building a report line from
untrusted/derived data should be able to recover rather than crash the whole
CLI invocation over a cosmetic label.
"""

from __future__ import annotations

from typani.error_set import ErrorSet


# frob:ticket T-0448
# frob:doc docs/modules/render.md#element-vocabulary
class RenderError(ErrorSet):
    """Failures raised by `frob.render` element constructors."""

    InvalidStatus = "status pill value is not one of ok/warn/error/skip"
    InvalidTicketId = "ticket id does not match the T-#### shape"


__all__ = ["RenderError"]
