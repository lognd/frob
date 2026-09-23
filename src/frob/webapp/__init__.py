"""frob.webapp -- web-framework detection substrate (docs/modules/webapp.md).

# frob:ticket T-5302

Scaffolding for the WEBSEC/COMPLY/A11Y/SEO/WEBPERF rule families (T-5301
wired their rule ids and severities; this leaf gives them the one thing
they all need first): `detect_frameworks` sniffs a repo root for known
markers of Next.js, Vite, Django, Flask, FastAPI, Rails, Laravel,
SvelteKit, and Astro, returning a `frozenset[FrameworkKind]` -- empty for
a plain Python CLI repo, which every downstream rule in those families
treats as "not relevant" and short-circuits past (owner directive, verbatim:
a CLI repo with no detected framework runs none of this work). SQL
literal detection lives in the sibling `frob.sql` package rather than
here, since SQL strings show up in non-web code too (migrations, CLI
tools, ETL scripts) and should not require a web framework to be present.

See `frob.webapp._detect` for the detector implementations.
"""

from __future__ import annotations

from frob.webapp._detect import FrameworkKind, detect_frameworks

__all__ = ["FrameworkKind", "detect_frameworks"]
