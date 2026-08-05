"""Lightweight, `frob.gates`-independent security primitives (T-1318).

Deliberately outside the `frob.gates` package tree: importing anything
under `frob.gates` (even one private submodule) always executes
`frob/gates/__init__.py` first (ordinary Python package-import semantics),
which eagerly imports that package's entire heavy stage roster as a side
effect. `frob.security` exists so a caller that needs ONLY a small,
well-defined primitive -- today, `frob.app.telemetry`'s secret-redaction
call on every CLI invocation -- never pays that cost. See
`frob.security._redact`'s own module docstring for the specific extraction
this package was created for.
"""

from __future__ import annotations
