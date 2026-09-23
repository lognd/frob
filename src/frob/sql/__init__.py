"""frob.sql -- SQL rule-family package stub (docs/modules/webapp.md#frob-sql).

# frob:ticket T-5302

Intentionally empty for now: the SQL literal-detection and SQL-rule
substrate (T-5301 reserved its rule ids) lands in a later leaf of the
T-5299 epic. This package exists so `design/frob.strata` and
`[arch.layering]` in `frob.toml` have a real node/layer to declare ahead
of that work, and so sibling leaves that will import `frob.sql` are not
blocked on a module that does not exist yet. SQL lives outside
`frob.webapp` on purpose: SQL literals appear in non-web code (migration
scripts, CLI tools, ETL) that has no web framework to detect.
"""

from __future__ import annotations
