"""Single-source dangerous-operations registry (T-0158): one authoritative
enumeration of every reserved capability kind, plus the structured
dangerous-operation entries `frob.vet._capability` compiles into its
per-language needle tables. Every consumer of "what capability kinds
exist" -- `frob.vet._capability`, `frob.strata._threat`'s `CWE_CATALOG`/
`CWE_TOP_25_CATALOG`/`DEFAULT_BENIGN_CAPABILITIES`, `frob.strata._effects`'s
`_KIND_MAP`, the surface grammar's `may` atoms -- imports `CAPABILITY_KINDS`
from HERE so the vocabulary cannot fork (extends the T-0150 drift-lock:
`_validate_registry_kinds` fails loudly if any consumer uses a kind absent
from this tuple).

Addendum 1 (2026-07-18) promotes every `_PATTERNS` needle into a
`_DangerousOperation`: {language, library, function_or_pattern,
capability_kind, cwe_links, rationale, safer_alternative, severity} --
audit findings then name the registry entry instead of a bare kind label.

Addendum 2 (2026-07-18) demands EXHAUSTIVE, CLOSED-WORLD coverage: every
stdlib module that can touch process/fs/net/env/dynamic-code is curated
here (see `NO_CAPABILITY_MODULES` for the pure side of that curation), and
`CAPABILITY_MATRIX_EXCUSES` replaces the old blanket C/C++ "honestly-
empty" exemption with a per-(kind, language) decision: every cell is
EITHER patterned (>=1 `_DangerousOperation`) OR excused with a specific
written reason (`OutOfScopeEntry`-style discipline, docs/modules/vet.md
"Coverage matrix").

T-0181 (addendum 2 remainder, 2026-07-18) drains the addendum 2 priority
survey list -- python (pydantic/fastapi/numpy/cryptography/jinja2/
python-dotenv/uvicorn/sqlalchemy/asyncpg/alembic/redis/boto3/stripe/
anthropic/argon2-cffi/aiosmtpd/playwright/Pillow), npm (react/react-dom/
vite/vitest/playwright/openapi-typescript/eslint tooling), and cargo
(pyo3/serde/serde_json/tracing/libloading/wasm-bindgen/crossbeam/
thiserror) -- against each library's real API surface: each library ends
as either new `_DangerousOperation` entries below or is a pure library with
no dangerous surface (documented in docs/modules/vet.md "Third-party
library survey (T-0181)", not silently dropped).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from frob.vet._capability_registry._kinds import CAPABILITY_KINDS, LANGUAGES
from frob.vet._capability_registry._matrix import (
    CAPABILITY_MATRIX_EXCUSES,
    DANGEROUS_OPERATIONS,
    NO_CAPABILITY_MODULES,
    _MatrixCell,
    _unexcused_empty_cells,
    _validate_registry_kinds,
    capability_matrix,
)
from frob.vet._capability_registry._opaque import (
    OPAQUE_SOURCE_INVISIBLE,
    RUNTIME_OPAQUE_CONSTRUCTS,
    RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS,
)
from frob.vet._capability_registry._schemas import (
    _DangerousOperation,
    _MatrixExcuse,
    _OpaqueConstruct,
    _OpaqueStructuralConstruct,
)

__all__ = [
    "CAPABILITY_KINDS",
    "CAPABILITY_MATRIX_EXCUSES",
    "DANGEROUS_OPERATIONS",
    "LANGUAGES",
    "NO_CAPABILITY_MODULES",
    "OPAQUE_SOURCE_INVISIBLE",
    "RUNTIME_OPAQUE_CONSTRUCTS",
    "RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS",
    "_DangerousOperation",
    "_MatrixCell",
    "_MatrixExcuse",
    "_OpaqueConstruct",
    "_OpaqueStructuralConstruct",
    "capability_matrix",
    "_unexcused_empty_cells",
    "_validate_registry_kinds",
]
