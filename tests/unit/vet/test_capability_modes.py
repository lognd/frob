"""Unit tests for the T-0717 mode-qualified capability vocabulary shared
between `frob.vet` and `frob.strata` (`frob.vet._capability_modes`).
"""

from __future__ import annotations

import logging
from datetime import date

from frob.vet._capability_modes import (
    CAPABILITY_MODE_KINDS,
    LEGACY_CAPABILITY_ALIASES,
    CapabilityModeError,
    _mode_qualified,
    _normalize_observed_kind,
    canonical_declared_kind,
    expand_declared_kind,
    resolve_capability_kind,
)


class TestModeQualified:
    def test_joins_family_and_mode(self):
        assert _mode_qualified("fs", "read") == "fs.read"

    def test_capability_mode_kinds_includes_fs_read_write(self):
        assert "fs.read" in CAPABILITY_MODE_KINDS
        assert "fs.write" in CAPABILITY_MODE_KINDS


class TestExpandDeclaredKind:
    def test_precise_kind_covers_only_itself(self):
        assert expand_declared_kind("fs.read") == frozenset({"fs.read"})

    def test_coarse_fs_covers_union_of_modes(self):
        """Mandate point 2: a coarse `may "fs"` declaration is the UNION of
        fs's modes -- "a coarse declarer answers for everything"."""
        assert expand_declared_kind("fs") == frozenset({"fs.read", "fs.write"})

    def test_unwired_family_stays_coarse(self):
        """`net` has a defined mode set (`FAMILY_MODES`) but is not in
        `WIRED_MODE_FAMILIES` this pass -- a bare `may "net"` must stay
        exactly `{"net"}`, never silently explode into modes no scanner
        can observe yet (module docstring's "wiring status")."""
        assert expand_declared_kind("net") == frozenset({"net"})

    def test_kind_with_no_modes_defined_stays_itself(self):
        assert expand_declared_kind("exec") == frozenset({"exec"})


class TestResolveCapabilityKind:
    def test_precise_kind_passes_through(self):
        assert resolve_capability_kind("fs.write").danger_ok == "fs.write"

    def test_coarse_family_is_never_deprecated(self):
        assert resolve_capability_kind("fs").danger_ok == "fs"

    def test_legacy_alias_in_window_resolves_and_warns(self, caplog):
        """T-0717 acceptance clause 2: a legacy `fs-write` spelling keeps
        working (resolves to its precise target) while inside the sunset
        window, and the WARNING names both the sunset date and the
        migration target."""
        alias = LEGACY_CAPABILITY_ALIASES["fs-write"]
        before_sunset = date.fromisoformat(alias.since)
        with caplog.at_level(logging.WARNING):
            result = resolve_capability_kind("fs-write", today=before_sunset)
        assert result.is_ok
        assert result.danger_ok == "fs.write"
        assert any(
            "fs.write" in record.message
            and LEGACY_CAPABILITY_ALIASES["fs-write"].sunset in record.message
            for record in caplog.records
        )

    def test_legacy_alias_past_sunset_is_gate_error(self):
        """T-0717 acceptance clause 3: once the sunset date has passed, the
        legacy spelling is a gate ERROR, not a silent pass."""
        alias = LEGACY_CAPABILITY_ALIASES["fs-write"]
        past_sunset = date.fromisoformat(alias.sunset).replace(
            year=date.fromisoformat(alias.sunset).year + 1
        )
        result = resolve_capability_kind("fs-write", today=past_sunset)
        assert result.is_err
        assert result.danger_err == CapabilityModeError.AliasSunset

    def test_sunset_date_itself_is_already_expired(self):
        alias = LEGACY_CAPABILITY_ALIASES["fs-read"]
        sunset = date.fromisoformat(alias.sunset)
        result = resolve_capability_kind("fs-read", today=sunset)
        assert result.is_err


class TestCanonicalAndNormalize:
    def test_canonical_declared_kind_resolves_alias_regardless_of_sunset(self):
        """Unlike `resolve_capability_kind`, the pure canonicalization used
        for conformance joins never errors -- the sunset is a separate gate
        finding, never a conformance regression."""
        assert canonical_declared_kind("fs-write") == "fs.write"
        assert canonical_declared_kind("fs-read") == "fs.read"
        assert canonical_declared_kind("fs.write") == "fs.write"
        assert canonical_declared_kind("fs") == "fs"

    def test_normalize_observed_kind_matches_canonical(self):
        assert _normalize_observed_kind("fs-write") == "fs.write"
        assert _normalize_observed_kind("net") == "net"
