"""WIRE001 case 3 (T-2348): `_wire001_cli_dest_violations` decides "is this
new CLI `dest=` wired into `_config_external.py`" from an AST-parsed set of
forwarded field names (`_config_external_forwarded_dest_names`), not a raw
substring-membership scan over the file's text. Positive controls for both
failure directions the old text scan had, plus the real-catch case the gate
exists for."""

from __future__ import annotations

from pathlib import Path

from frob.gates._wire import (
    _config_external_forwarded_dest_names,
    _wire001_cli_dest_violations,
)


def _added_lines_with_dest(dest: str) -> dict[str, list[tuple[int, str]]]:
    return {
        "src/frob/_cli_parsers/foo.py": [
            (10, f'parser.add_argument("--bar", dest="{dest}")')
        ]
    }


class TestConfigExternalForwardedDestNames:
    """`_config_external_forwarded_dest_names`: the AST-parsed replacement
    for the old raw text-membership scan."""

    def test_collects_tuple_and_frozenset_literals(self) -> None:
        """Every string literal element of a module-level tuple/list/set/
        `frozenset(...)` assignment is collected -- the six `_apply_*_
        fields` tuples plus `_AD_HOC_FORWARDED_FIELDS`'s shape."""
        text = (
            "_STRING_FIELDS = (\n"
            '    "color",\n'
            '    "explore_command",\n'
            ")\n"
            "_AD_HOC_FORWARDED_FIELDS = frozenset(\n"
            "    {\n"
            '        "subcommand",\n'
            '        "no_color",\n'
            "    }\n"
            ")\n"
        )
        names = _config_external_forwarded_dest_names(text)
        assert names == frozenset(
            {"color", "explore_command", "subcommand", "no_color"}
        )

    def test_comment_and_docstring_mentions_are_not_collected(self) -> None:
        """T-2348's false-negative repro: the OLD text-membership scan
        (`f'"{dest}"' in config_external_text`) would have read a `dest`
        string as "wired" merely because it appears, quoted, anywhere in
        the file -- a comment, an unrelated docstring, dead prose. The
        AST-parsed replacement only ever collects literals that are
        actual elements of a module-level collection literal, so a
        quoted mention outside one of those must NOT be collected."""
        text = (
            '"""A docstring that happens to mention "orphan_dest" for '
            'illustration."""\n'
            "\n"
            '# NOTE: "orphan_dest" used to be forwarded here, no longer is\n'
            "_STRING_FIELDS = (\n"
            '    "color",\n'
            ")\n"
        )
        names = _config_external_forwarded_dest_names(text)
        assert names is not None
        assert "orphan_dest" not in names
        assert names == frozenset({"color"})

    def test_unparseable_text_returns_none(self) -> None:
        """A syntax error in the target file is reported as `None`, not a
        silently empty/wrong set -- the caller's fail-toward-flagging
        posture depends on being able to tell "parsed to nothing" apart
        from "could not parse"."""
        assert _config_external_forwarded_dest_names("def broken(:\n") is None


class TestWire001CliDestViolations:
    """`_wire001_cli_dest_violations`: the WIRE001 case-3 decision itself,
    now driven by the AST-parsed forwarded set."""

    def test_dest_wired_only_through_tuple_structure_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """Positive control (must still pass): a `dest` string present
        ONLY as a literal tuple element -- nowhere else in the file as
        bare text -- is correctly recognized as wired, the real-wiring
        case the old text scan also handled correctly."""
        config_external = tmp_path / "src" / "frob" / "app" / "_config_external.py"
        config_external.parent.mkdir(parents=True)
        config_external.write_text('_STRING_FIELDS = (\n    "bar_dest",\n)\n')
        violations = _wire001_cli_dest_violations(
            tmp_path, _added_lines_with_dest("bar_dest")
        )
        assert violations == []

    def test_dest_mentioned_only_in_a_comment_is_flagged(self, tmp_path: Path) -> None:
        """T-2348's must-fail-before-fix repro, now must-pass-after-fix:
        a `dest` string that appears in `_config_external.py` only inside
        a COMMENT (never inside an actual forwarding tuple) is correctly
        flagged as unwired. Under the old raw substring scan this was a
        false negative -- `f'"{dest}"' in text` matches a quoted mention
        in a comment exactly as readily as a real tuple entry, so the gate
        silently missed a genuinely-dropped CLI flag whose name happened
        to be mentioned in passing prose."""
        config_external = tmp_path / "src" / "frob" / "app" / "_config_external.py"
        config_external.parent.mkdir(parents=True)
        config_external.write_text(
            '# "bar_dest" was considered here but never actually copied\n'
            "_STRING_FIELDS = (\n"
            '    "unrelated_field",\n'
            ")\n"
        )
        violations = _wire001_cli_dest_violations(
            tmp_path, _added_lines_with_dest("bar_dest")
        )
        assert len(violations) == 1
        assert violations[0].rule == "WIRE001"
        assert "bar_dest" in violations[0].message

    def test_dest_not_wired_at_all_is_flagged(self, tmp_path: Path) -> None:
        """A `dest` with no matching entry anywhere in `_config_external.
        py` fires WIRE001 either way (old scan or new) -- the baseline
        real-catch case this gate exists for."""
        config_external = tmp_path / "src" / "frob" / "app" / "_config_external.py"
        config_external.parent.mkdir(parents=True)
        config_external.write_text('_STRING_FIELDS = (\n    "other_field",\n)\n')
        violations = _wire001_cli_dest_violations(
            tmp_path, _added_lines_with_dest("bar_dest")
        )
        assert len(violations) == 1
        assert violations[0].rule == "WIRE001"
