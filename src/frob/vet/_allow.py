"""Loads `[vet]`/`[vet.allow]` from frob.toml
(docs/modules/vet.md "Declaration and gates").

MVP note: allow entries are coarse -- `name = true` or `name = ["reason", ...]`;
full per-capability declarations (`name = ["net", "env"]` meaning literal
capability tokens) are 0.2.x, once real capability scanning exists.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/vet/_allow.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.logging import get_logger
from frob.vet._models import VetConfig

_log = get_logger(__name__)


def _parse_allow(allow_raw: object) -> dict[str, tuple[str, ...] | bool]:
    """Coerce a raw `[vet.allow]` table into `{name: bool | (reason, ...)}`,
    logging and dropping entries with an unsupported value shape."""
    allow: dict[str, tuple[str, ...] | bool] = {}
    if not isinstance(allow_raw, dict):
        return allow
    for name, value in allow_raw.items():
        if isinstance(value, bool):
            allow[str(name)] = value
        elif isinstance(value, list):
            allow[str(name)] = tuple(str(v) for v in value)
        else:
            _log.warning(
                "vet: [vet.allow] entry %r has unsupported value %r; ignoring",
                name,
                value,
            )
    return allow


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="docs/modules/vet.md's Public API section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
# frob:waive TEST005 reason="_load_vet_config 82.4% branch cover, debt T-0160"
def _load_vet_config(root: Path) -> VetConfig:
    """Read `frob.toml`'s `[vet]` table; absent table -> `present=False`
    (advisory-only)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        _log.debug("vet: no frob.toml at %s; advisory-only mode", toml_path)
        return VetConfig(present=False)
    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("vet: could not parse %s: %s", toml_path, exc)
        return VetConfig(present=False)

    vet = data.get("vet")
    if not isinstance(vet, dict):
        _log.info("vet: no [vet] section in %s; advisory-only mode", toml_path)
        return VetConfig(present=False)

    return _build_vet_config(vet)


def _build_vet_config(vet: dict[str, object]) -> VetConfig:
    """Assemble a present `VetConfig` from a parsed `[vet]` table and log
    the resulting settings."""
    allow = _parse_allow(vet.get("allow", {}))

    # `[vet]` values arrive from parsed TOML as `object`; narrow each to the
    # field's type, falling back to the default on a wrong-typed value rather
    # than crashing the whole `frob` invocation on a malformed config line.
    raw_days = vet.get("quarantine_days", 14)
    raw_url = vet.get("registry_base_url")

    cfg = VetConfig(
        present=True,
        enforce=bool(vet.get("enforce", False)),
        osv=bool(vet.get("osv", False)),
        quarantine_days=int(raw_days)
        if isinstance(raw_days, (int, float, str))
        else 14,
        registry_base_url=raw_url if isinstance(raw_url, str) else None,
        allow=allow,
    )
    _log.info(
        "vet: loaded [vet] config: enforce=%s osv=%s quarantine_days=%d allow=%d",
        cfg.enforce,
        cfg.osv,
        cfg.quarantine_days,
        len(cfg.allow),
    )
    return cfg


__all__ = ["_load_vet_config"]
