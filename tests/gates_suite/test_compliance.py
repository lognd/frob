import subprocess
from pathlib import Path

from frob.gates import (
    Severity,
    compliance_gate,
    known_gate_rule_ids,
)
from frob.gates._pii_structural import pii_structural_gate
from frob.strata import CMPL_REGISTRY_UNIT_IDS
from tests.conftest import (
    _by_rule,
    _git_init,
    _write,
)


# frob:ticket T-0762
class TestPiiStructuralCrossLanguage:
    """T-0352: PII010/SEC110 field-shape and env-access equivalents over
    TypeScript/Rust source (`frob.gates._pii_structural`'s Python-only
    T-0207 scan extended to the other two `frob.lang`-supported grammars
    named in the ticket body). Every fixture is a real git-tracked file
    parsed via `frob.lang.raw_tree` (the ticket's "reuse the existing
    tree-sitter parses" mandate) -- not a hand-rolled second parser."""

    def _write(self, root: Path, rel: str, text: str) -> None:
        """Write `text` to `root/rel`, creating parent dirs as needed."""
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_interface_email_field_fires  # noqa: E501
    def test_ts_interface_email_field_fires(self, tmp_path: Path) -> None:
        """A TS `interface` field named `email` is the field-shape
        equivalent of a pydantic `BaseModel` field -- fires PII010."""
        self._write(
            tmp_path,
            "user.ts",
            "interface User {\n  email: string;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("email" in v.message and "user.ts" in v.file for v in pii010)

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_type_alias_password_field_fires  # noqa: E501
    def test_ts_type_alias_password_field_fires(self, tmp_path: Path) -> None:
        """A TS `type` alias object-type field named `password` fires
        PII010 -- the `type_alias_declaration`/`object_type` equivalent of
        an interface field."""
        self._write(
            tmp_path,
            "profile.ts",
            "type Profile = {\n  password: string;\n};\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("password" in v.message and "profile.ts" in v.file for v in pii010)

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_class_field_token_fires  # noqa: E501
    def test_ts_class_field_token_fires(self, tmp_path: Path) -> None:
        """A TS `class` field named `token` fires PII010 -- the class-body
        `public_field_definition` equivalent."""
        self._write(
            tmp_path,
            "account.ts",
            "class Account {\n  token: string;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("token" in v.message and "account.ts" in v.file for v in pii010)

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_clean_interface_is_silent  # noqa: E501
    def test_ts_clean_interface_is_silent(self, tmp_path: Path) -> None:
        """A TS interface with no PII-shaped field names fires nothing."""
        self._write(
            tmp_path,
            "widget.ts",
            "interface Widget {\n  width: number;\n  height: number;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not _by_rule(violations, "PII010")

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_index_signature_reported_not_skipped  # noqa: E501
    def test_ts_index_signature_reported_not_skipped(self, tmp_path: Path) -> None:
        """T-0352 NO-FAIL-SILENT: a TS index signature (`[key: string]: T`)
        has no statically-readable field name -- it must be REPORTED as an
        unresolvable field shape, never silently dropped from the scan."""
        self._write(
            tmp_path,
            "dynamic.ts",
            "interface Weird {\n  [key: string]: string;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("unresolvable" in v.message for v in pii010)

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_proc\
    # ess_env_fires
    def test_ts_process_env_fires(self, tmp_path: Path) -> None:
        """`process.env.SECRET_KEY` fires SEC110 -- the TS equivalent of
        `os.environ[...]`/`os.getenv(...)`."""
        self._write(
            tmp_path,
            "config.ts",
            "const key = process.env.SECRET_KEY;\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any("process.env" in v.message and "config.ts" in v.file for v in sec110)

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_process_env_subscript_fires  # noqa: E501
    def test_ts_process_env_subscript_fires(self, tmp_path: Path) -> None:
        """`process.env["API_TOKEN"]` (subscript form) fires SEC110."""
        self._write(
            tmp_path,
            "config2.ts",
            'const key = process.env["API_TOKEN"];\n',
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any("API_TOKEN" in v.message and "config2.ts" in v.file for v in sec110)

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_impo\
    # rt_meta_env_fires
    def test_ts_import_meta_env_fires(self, tmp_path: Path) -> None:
        """`import.meta.env.VITE_SECRET` (Vite-style bundler env access)
        fires SEC110 -- the ticket-named `import.meta.env` equivalent."""
        self._write(
            tmp_path,
            "vite.ts",
            "const key = import.meta.env.VITE_SECRET;\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any(
            "import.meta.env" in v.message and "vite.ts" in v.file for v in sec110
        )

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_dynamic_env_key_still_fires  # noqa: E501
    def test_ts_dynamic_env_key_still_fires(self, tmp_path: Path) -> None:
        """T-0352 NO-FAIL-SILENT: `process.env[someDynamicKey]` (a
        non-literal subscript key) cannot be statically named -- it must
        still fire SEC110 rather than be silently skipped for lack of a
        resolvable name, mirroring `_scan_python_env_access`'s existing
        posture for a dynamic `os.environ[key]`."""
        self._write(
            tmp_path,
            "dynamic_env.ts",
            "const someDynamicKey = 'X';\nconst key = process.env[someDynamicKey];\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any("dynamic_env.ts" in v.file for v in sec110)

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_allowlisted_env_var_is_silent  # noqa: E501
    def test_ts_allowlisted_env_var_is_silent(self, tmp_path: Path) -> None:
        """`process.env.PATH` is an allowlisted, definitionally-non-secret
        var (`_ENV_VAR_ALLOWLIST`, shared table) -- silent."""
        self._write(tmp_path, "clean_env.ts", "const p = process.env.PATH;\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any("clean_env.ts" in v.file for v in _by_rule(violations, "SEC110"))

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_rust_struct_ssn_field_fires  # noqa: E501
    def test_rust_struct_ssn_field_fires(self, tmp_path: Path) -> None:
        """A Rust `struct` named field `ssn` fires PII010 -- the
        `field_declaration_list` equivalent of a Python dataclass field."""
        self._write(
            tmp_path,
            "user.rs",
            "struct User {\n    ssn: String,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("ssn" in v.message and "user.rs" in v.file for v in pii010)

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_rust_clean_struct_is_silent  # noqa: E501
    def test_rust_clean_struct_is_silent(self, tmp_path: Path) -> None:
        """A Rust struct with no PII-shaped field names fires nothing."""
        self._write(
            tmp_path,
            "widget.rs",
            "struct Widget {\n    width: i32,\n    height: i32,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not _by_rule(violations, "PII010")

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_rust_en\
    # v_var_fires
    def test_rust_env_var_fires(self, tmp_path: Path) -> None:
        """`std::env::var("API_KEY")` fires SEC110 -- the Rust equivalent
        of `os.getenv(...)`."""
        self._write(
            tmp_path,
            "config.rs",
            'fn main() {\n    let k = std::env::var("API_KEY").unwrap();\n}\n',
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any(
            "std::env::var" in v.message and "config.rs" in v.file for v in sec110
        )

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_rust_unqualified_env_var_fires  # noqa: E501
    def test_rust_unqualified_env_var_fires(self, tmp_path: Path) -> None:
        """`env::var("SECRET")` (direct-import form, no `std::` prefix)
        fires SEC110 too -- mirrors `_scan_python_env_access`'s
        direct-import `getenv(...)` handling."""
        self._write(
            tmp_path,
            "config2.rs",
            'fn main() {\n    let k = env::var("SECRET").unwrap();\n}\n',
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any("config2.rs" in v.file for v in sec110)

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_rust_allowlisted_env_var_is_silent  # noqa: E501
    def test_rust_allowlisted_env_var_is_silent(self, tmp_path: Path) -> None:
        """`std::env::var("PATH")` is allowlisted -- silent."""
        self._write(
            tmp_path,
            "clean_env.rs",
            'fn main() {\n    let p = std::env::var("PATH").unwrap();\n}\n',
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any("clean_env.rs" in v.file for v in _by_rule(violations, "SEC110"))

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_rust_tuple_struct_field_not_matched  # noqa: E501
    def test_rust_tuple_struct_field_not_matched(self, tmp_path: Path) -> None:
        """Adversarial: a Rust TUPLE struct (`Point(i32, i32)`) has no
        source field names at all -- `_rust_struct_field_names` only reads
        `field_declaration_list` (named) bodies, so a tuple struct is
        silent regardless of its type names (no name to match against
        `FIELD_SIGNATURES` in the first place, not a false negative on a
        real PII field)."""
        self._write(tmp_path, "point.rs", "struct Point(i32, i32);\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any("point.rs" in v.file for v in _by_rule(violations, "PII010"))

    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_and_rust_findings_joined_against_declared_surface  # noqa: E501
    def test_ts_and_rust_findings_joined_against_declared_surface(
        self, tmp_path: Path
    ) -> None:
        """T-0351's std.pii/std.secrets join applies identically to a
        TS/Rust finding -- `_load_declared_surface` is keyed on rel_path
        alone, language-agnostic, so a design directory with no models at
        all still leaves both languages' findings firing exactly as if
        T-0351 never ran (empty-surface degrade, shared code path)."""
        self._write(tmp_path, "user.ts", "interface User {\n  email: string;\n}\n")
        self._write(tmp_path, "user.rs", "struct User {\n    email: String,\n}\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010_files = {v.file for v in _by_rule(violations, "PII010")}
        assert "user.ts" in pii010_files
        assert "user.rs" in pii010_files

    # frob:ticket T-0762
    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_secret_wrapper_type_field_fires  # noqa: E501
    def test_ts_secret_wrapper_type_field_fires(self, tmp_path: Path) -> None:
        """T-0762: a TS field typed as a known secret-wrapper type
        (`SecretString`) fires PII010 even though its own NAME (`apiKey`)
        does not itself contain a name-kind keyword token."""
        self._write(
            tmp_path,
            "creds.ts",
            "interface Creds {\n  wrapped: SecretString;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("SecretString" in v.message and "creds.ts" in v.file for v in pii010)

    # frob:ticket T-0762
    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_branded_email_type_field_fires  # noqa: E501
    def test_ts_branded_email_type_field_fires(self, tmp_path: Path) -> None:
        """T-0762: a TS field typed as a branded/nominal `Email` type fires
        PII010 -- the TYPE-kind signal, independent of the field's own
        NAME."""
        self._write(
            tmp_path,
            "contact.ts",
            "interface Contact {\n  primary: Email;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("Email" in v.message and "contact.ts" in v.file for v in pii010)

    # frob:ticket T-0762
    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_ts_plain_string_field_type_does_not_fire  # noqa: E501
    def test_ts_plain_string_field_type_does_not_fire(self, tmp_path: Path) -> None:
        """Adversarial (T-0762 acceptance): a plain `string`-typed field
        with a non-PII-shaped name does not fire -- TYPE-kind matching
        must not over-fire on the ordinary built-in type."""
        self._write(
            tmp_path,
            "clean_type.ts",
            "interface Widget {\n  label: string;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any(
            "clean_type.ts" in v.file for v in _by_rule(violations, "PII010")
        )

    # frob:ticket T-0762
    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_rust_secrecy_secretstring_type_field_fires  # noqa: E501
    def test_rust_secrecy_secretstring_type_field_fires(self, tmp_path: Path) -> None:
        """T-0762: a Rust field typed `secrecy::SecretString` fires PII010
        -- the ticket-named `secrecy` crate wrapper, matched via the scoped
        type-identifier walk regardless of the field's own NAME."""
        self._write(
            tmp_path,
            "vault.rs",
            "struct Vault {\n    wrapped: secrecy::SecretString,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("SecretString" in v.message and "vault.rs" in v.file for v in pii010)

    # frob:ticket T-0762
    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_rust_secret_newtype_type_field_fires  # noqa: E501
    def test_rust_secret_newtype_type_field_fires(self, tmp_path: Path) -> None:
        """T-0762: a Rust field typed `secrecy::Secret<String>` fires
        PII010 -- a generic-wrapped scoped type name still surfaces its
        inner identifier to the type-identifier walk."""
        self._write(
            tmp_path,
            "vault2.rs",
            "struct Vault2 {\n    wrapped: secrecy::Secret<String>,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("vault2.rs" in v.file for v in pii010)

    # frob:ticket T-0762
    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_rust_plain_string_field_type_does_not_fire  # noqa: E501
    def test_rust_plain_string_field_type_does_not_fire(self, tmp_path: Path) -> None:
        """Adversarial (T-0762 acceptance): a plain `String`-typed Rust
        field with a non-PII-shaped name does not fire."""
        self._write(
            tmp_path,
            "clean_type.rs",
            "struct Widget {\n    label: String,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any(
            "clean_type.rs" in v.file for v in _by_rule(violations, "PII010")
        )

    # frob:ticket T-0897
    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_unparseable_python_file_fires_parse001  # noqa: E501
    def test_unparseable_python_file_fires_parse001(self, tmp_path: Path) -> None:
        """A `.py` file with a syntax error fires PARSE001 instead of
        being silently dropped from the PII010/SEC110 scan with zero
        Violation (T-0897)."""
        self._write(tmp_path, "broken.py", "class C(:\n    pass\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        hits = _by_rule(violations, "PARSE001")
        offender_hits = [v for v in hits if v.file == "broken.py"]
        assert len(offender_hits) == 1
        assert offender_hits[0].severity == Severity.ERROR

    # frob:ticket T-0897
    # frob:tests tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage.test_unparseable_file_under_graph_exclude_is_silent  # noqa: E501
    def test_unparseable_file_under_graph_exclude_is_silent(
        self, tmp_path: Path
    ) -> None:
        """A `.py` file under a `[graph].exclude` glob (frob.toml) that is
        deliberately, permanently unparseable (the `tests/fixtures/**`
        posture: kept out of frob's own obligation surface, module
        docstrings across the repo document this) does NOT fire PARSE001
        -- only files frob's own graph would otherwise obligate do
        (T-0897)."""
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["tests/fixtures/**"]\n'
        )
        self._write(tmp_path, "tests/fixtures/broken.py", "class C(:\n    pass\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        hits = [v for v in _by_rule(violations, "PARSE001") if "broken.py" in v.file]
        assert hits == []
# frob:ticket T-0788
class TestComplianceGate:
    """COMPLIANCE005 (T-0788): `compliance_gate` is the `frob check`
    dispatch of `frob.strata._compliance.check_cmpl_registry` (built by
    T-0607, which could not register or dispatch it -- out of that
    ticket's declared scope). Verifies the rule id is a real, registered
    gate rule and that the dispatch wiring fires/stays silent on the
    right dispositions, mirroring `tests/unit/strata/test_compliance.py`'s
    `TestCmplRegistry` fixture shapes at the gate layer."""

    # frob:ticket T-0788
    def _write_compliance_yaml(self, tmp_path: Path, entries_yaml: str) -> Path:
        """A minimal `docs/design/registry/compliance.yaml` under `tmp_path`
        with `entries_yaml` spliced into its `entries:` list."""
        registry_dir = tmp_path / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "compliance.yaml").write_text(
            "entries:\n" + entries_yaml, encoding="utf-8"
        )
        return registry_dir

    # frob:ticket T-0788
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance005_registered_in_known_gate_rules  # noqa: E501
    def test_compliance005_registered_in_known_gate_rules(self) -> None:
        """COMPLIANCE005 is in the live `_KNOWN_GATE_RULES` union -- the
        exact gap T-0607 disclosed (the rule existed in code but was not a
        real, registered gate rule id anywhere `frob check` consults)."""
        assert "COMPLIANCE005" in known_gate_rule_ids()

    # frob:ticket T-0788
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance005_fires_on_deferred_disposition  # noqa: E501
    def test_compliance005_fires_on_deferred_disposition(self, tmp_path: Path) -> None:
        """A `CMPL_REGISTRY_UNIT_IDS` member left `deferred:*` fires
        COMPLIANCE005 through the real `frob check` dispatch path, not
        just the underlying strata check called directly."""
        entry_id = sorted(CMPL_REGISTRY_UNIT_IDS)[0]
        registry_dir = self._write_compliance_yaml(
            tmp_path,
            f'  - id: "{entry_id}"\n'
            '    title: "t"\n'
            '    disposition: "deferred:T-0001"\n',
        )
        violations = compliance_gate(tmp_path, registry_dir)
        cmpl005 = [v for v in violations if v.rule == "COMPLIANCE005"]
        assert len(cmpl005) == 1
        assert entry_id in cmpl005[0].message
        assert cmpl005[0].severity == Severity.ERROR

    # frob:ticket T-0788
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance005_silent_on_handled_by_and_out_of_scope  # noqa: E501
    def test_compliance005_silent_on_handled_by_and_out_of_scope(
        self, tmp_path: Path
    ) -> None:
        """`handled_by:*` and `out_of_scope:*` are both accepted --
        COMPLIANCE005 does not fire through the gate dispatch either."""
        ids = sorted(CMPL_REGISTRY_UNIT_IDS)
        registry_dir = self._write_compliance_yaml(
            tmp_path,
            f'  - id: "{ids[0]}"\n'
            '    title: "t"\n'
            '    disposition: "handled_by:COMPLIANCE005"\n'
            f'  - id: "{ids[1]}"\n'
            '    title: "t"\n'
            '    disposition: "out_of_scope:reason text"\n',
        )
        violations = compliance_gate(tmp_path, registry_dir)
        assert not any(v.rule == "COMPLIANCE005" for v in violations)

    # frob:ticket T-0788
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance005_missing_registry_dir_is_silent  # noqa: E501
    def test_compliance005_missing_registry_dir_is_silent(self, tmp_path: Path) -> None:
        """No `compliance.yaml` at all (a repo with no compliance
        registry) makes no COMPLIANCE005 claim -- matches `registry_gate`'s
        own missing-directory posture, not a false-positive load error."""
        violations = compliance_gate(tmp_path)
        assert violations == ()

    # frob:ticket T-0788
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance005_real_repo_registry_passes  # noqa: E501
    def test_compliance005_real_repo_registry_passes(self) -> None:
        """The honest "real repo scan" smoke test (T-0813/T-0820
        precedent): runs `compliance_gate` over this repo's OWN live
        `docs/design/registry/compliance.yaml` -- every one of the 17
        `CMPL_REGISTRY_UNIT_IDS` units T-0607 re-dispositioned must still
        carry a `handled_by`/`out_of_scope` disposition, so this must be
        silent (0 COMPLIANCE005 findings) against real repo state."""
        root = Path(__file__).resolve().parents[2]
        violations = compliance_gate(root)
        assert not any(v.rule == "COMPLIANCE005" for v in violations)

    # frob:ticket T-1244
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance007_registered_in_known_gate_rules  # noqa: E501
    def test_compliance007_registered_in_known_gate_rules(self) -> None:
        """COMPLIANCE007 (T-1244) is a real, registered gate rule id, same
        requirement COMPLIANCE005 already carries."""
        assert "COMPLIANCE007" in known_gate_rule_ids()

    # frob:ticket T-1244
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance007_fires_warn_on_self_referential_handled_by  # noqa: E501
    def test_compliance007_fires_warn_on_self_referential_handled_by(
        self, tmp_path: Path
    ) -> None:
        """A CMPL unit still riding the vacuous `handled_by:COMPLIANCE005`
        self-reference fires COMPLIANCE007 through the real gate dispatch,
        at WARN (not ERROR) severity -- re-dispositioning it is the
        sibling triage tickets' job, not a hard gate failure."""
        entry_id = sorted(CMPL_REGISTRY_UNIT_IDS - {"CMPL-FROB-CATALOG-ENTRIES"})[0]
        registry_dir = self._write_compliance_yaml(
            tmp_path,
            f'  - id: "{entry_id}"\n'
            '    title: "t"\n'
            '    disposition: "handled_by:COMPLIANCE005"\n',
        )
        violations = compliance_gate(tmp_path, registry_dir)
        cmpl007 = [v for v in violations if v.rule == "COMPLIANCE007"]
        assert len(cmpl007) == 1
        assert entry_id in cmpl007[0].message
        assert cmpl007[0].severity == Severity.WARN

    # frob:ticket T-1244
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance007_silent_on_frob_catalog_entries_self_reference  # noqa: E501
    def test_compliance007_silent_on_frob_catalog_entries_self_reference(
        self, tmp_path: Path
    ) -> None:
        """`CMPL-FROB-CATALOG-ENTRIES`'s `handled_by:COMPLIANCE005` is the
        one legitimate self-reference (it counts `COMPLIANCE_CATALOG`'s
        own real entries) -- COMPLIANCE007 must not flag it."""
        registry_dir = self._write_compliance_yaml(
            tmp_path,
            '  - id: "CMPL-FROB-CATALOG-ENTRIES"\n'
            '    title: "t"\n'
            '    disposition: "handled_by:COMPLIANCE005"\n',
        )
        violations = compliance_gate(tmp_path, registry_dir)
        assert not any(v.rule == "COMPLIANCE007" for v in violations)

    # frob:ticket T-1244
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance007_real_repo_registry_surfaces_known_gap  # noqa: E501
    def test_compliance007_real_repo_registry_surfaces_known_gap(self) -> None:
        """The honest "real repo scan" smoke test for COMPLIANCE007: this
        repo's OWN `compliance.yaml` once had 16 CMPL units riding the
        vacuous self-reference; T-1245..T-1249 re-dispositioned every one
        (landed 2026-07-29), so the real-repo scan is now clean -- and
        this assertion LOCKS it clean, so a future vacuous handled_by row
        resurfaces as a test failure, not silent registry rot."""
        root = Path(__file__).resolve().parents[2]
        violations = compliance_gate(root)
        cmpl007 = [v for v in violations if v.rule == "COMPLIANCE007"]
        assert cmpl007 == []
        assert all(v.severity == Severity.WARN for v in cmpl007)

    # frob:ticket T-0894
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance006_silent_on_never_adopted_registry  # noqa: E501
    def test_compliance006_silent_on_never_adopted_registry(
        self, tmp_path: Path
    ) -> None:
        """A `tmp_path` git repo that never committed `compliance.yaml` at
        all stays silent -- COMPLIANCE006 must not fire on a genuinely
        never-adopted registry, only on one that existed and was deleted."""
        _git_init(tmp_path)
        violations = compliance_gate(tmp_path)
        assert not any(v.rule == "COMPLIANCE006" for v in violations)

    # frob:ticket T-0894
    # frob:tests tests/gates_suite/test_compliance.py::TestComplianceGate.test_compliance006_fires_on_deleted_registry_after_adoption  # noqa: E501
    def test_compliance006_fires_on_deleted_registry_after_adoption(
        self, tmp_path: Path
    ) -> None:
        """T-0894: `compliance.yaml` committed once, then deleted, must
        fire COMPLIANCE006 (unwaivable) rather than silently degrading to
        the "never adopted" empty-tuple posture COMPLIANCE005 alone gives
        it."""
        _git_init(tmp_path)
        registry_dir = self._write_compliance_yaml(
            tmp_path,
            "  - id: CMPL-TEST-1\n    disposition: 'handled_by:SEC003'\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "adopt compliance registry"],
            cwd=tmp_path,
            check=True,
        )
        (registry_dir / "compliance.yaml").unlink()

        from frob.gates import _UNWAIVABLE_RULES

        violations = compliance_gate(tmp_path)
        assert any(v.rule == "COMPLIANCE006" for v in violations)
        assert "COMPLIANCE006" in _UNWAIVABLE_RULES
# frob:ticket T-0688
# frob:ticket T-2543
class TestExhaustiveHandlingGate:
    """T-0688 (EXHAUST001/EXHAUST002), narrowed T-1402 (EXHAUST003):
    frob.gates._exhaustive_handling.exhaustive_handling_gate over
    frob.arch._mayraise.compute_may_raise's per-function may-raise sets. A
    function is a "boundary" only once it has at least one except clause
    of its own. A boundary that leaks Unknown with no catch-all fires
    EXHAUST001 ONLY when the Unknown traces to the function's own
    ambiguous bare re-raise (a real in-source construct); when it traces
    only to an unresolved callee (a call-graph resolution gap, not a
    confirmed unhandled error) it fires the quieter EXHAUST003 instead. A
    boundary that leaks a named type not declared via `# frob:raises
    <Type>` fires EXHAUST002."""

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate.test_partial_cat\
    # ch_of_named_type_fires_exhaust002
    def test_partial_catch_of_named_type_fires_exhaust002(self, tmp_path: Path) -> None:
        """`boundary` catches only ValueError but `risky` (which it calls)
        raises TypeError -- the leaked TypeError is named in EXHAUST002."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def risky():\n"
                "    raise TypeError('bad')\n"
                "\n"
                "def boundary():\n"
                "    try:\n"
                "        risky()\n"
                "    except ValueError:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        found = _by_rule(violations, "EXHAUST002")
        assert found
        assert any(v.symref == "mod.py::boundary" for v in found)
        assert any("TypeError" in v.message for v in found)

    # frob:ticket T-2543
    def test_subscript_only_leak_fires_exhaust004_not_exhaust002(
        self, tmp_path: Path
    ) -> None:
        """T-2543 (A4): a named leak whose ONLY source is the resolver's
        unresolved-shape subscript rule is the quieter EXHAUST004, not
        EXHAUST002 -- the same confidence split T-1402 made between
        EXHAUST001 and EXHAUST003."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def lookup(d, k):\n"
                "    return d[k]\n"
                "\n"
                "def boundary(d, k):\n"
                "    try:\n"
                "        return lookup(d, k)\n"
                "    except OSError:\n"
                "        return None\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        assert not [
            v
            for v in _by_rule(violations, "EXHAUST002")
            if v.symref.endswith("boundary")
        ]
        found = _by_rule(violations, "EXHAUST004")
        assert any(v.symref == "mod.py::boundary" for v in found)
        # A2: the resolver names the type it actually knows -- a lookup may
        # fail -- instead of picking the dict-shaped child.
        assert any("LookupError" in v.message for v in found)

    # frob:ticket T-2543
    def test_confirmed_and_subscript_leaks_split_across_both_rules(
        self, tmp_path: Path
    ) -> None:
        """T-2543 (A4): a function leaking BOTH a confirmed type and a
        subscript-only one gets one finding of each rule, rather than the
        whole function being demoted because one type is low-confidence."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def risky():\n"
                "    raise TypeError('bad')\n"
                "\n"
                "def lookup(d, k):\n"
                "    return d[k]\n"
                "\n"
                "def boundary(d, k):\n"
                "    try:\n"
                "        risky()\n"
                "        return lookup(d, k)\n"
                "    except OSError:\n"
                "        return None\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        confirmed = [
            v
            for v in _by_rule(violations, "EXHAUST002")
            if v.symref == "mod.py::boundary"
        ]
        subscript = [
            v
            for v in _by_rule(violations, "EXHAUST004")
            if v.symref == "mod.py::boundary"
        ]
        assert confirmed and "TypeError" in confirmed[0].message
        assert "LookupError" not in confirmed[0].message
        assert subscript and "LookupError" in subscript[0].message

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate.test_unknown_wit\
    # hout_catch_all_fires_exhaust001
    def test_unknown_without_catch_all_fires_exhaust001(self, tmp_path: Path) -> None:
        """T-0688 original name kept in place (T-0685/T-0688's own Done-
        report evidence cites this exact node id) -- T-1402 UPDATES what it
        asserts, in place, rather than orphaning that historical evidence:
        `boundary` calls an unresolvable function (contributes Unknown) and
        only catches ValueError -- this is now a call-graph resolution gap,
        not a confirmed unhandled error path, so as of T-1402 it fires the
        quieter EXHAUST003 and NOT EXHAUST001 (the precision fix this
        ticket makes: 69/69 pre-fix EXHAUST001 findings in this repo's own
        source were exactly this shape). See
        `test_unresolvable_callee_fires_exhaust003_not_exhaust001` below for
        the same assertion under a name that describes current behavior."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def boundary():\n"
                "    try:\n"
                "        some_unresolved_call()\n"
                "    except ValueError:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        assert not _by_rule(violations, "EXHAUST001")
        found = _by_rule(violations, "EXHAUST003")
        assert found
        assert any(v.symref == "mod.py::boundary" for v in found)

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate.test_unresolvabl\
    # e_callee_fires_exhaust003_not_exhaust001
    def test_unresolvable_callee_fires_exhaust003_not_exhaust001(
        self, tmp_path: Path
    ) -> None:
        """T-1402's own name for the same assertion
        `test_unknown_without_catch_all_fires_exhaust001` above now makes
        (kept a second, descriptively-named copy alongside the
        historically-evidenced original rather than only renaming it, so
        this ticket's own `frob:tests` directive names something that
        describes current behavior)."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def boundary():\n"
                "    try:\n"
                "        some_unresolved_call()\n"
                "    except ValueError:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        assert not _by_rule(violations, "EXHAUST001")
        found = _by_rule(violations, "EXHAUST003")
        assert found
        assert any(v.symref == "mod.py::boundary" for v in found)

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate.test_ambiguous_b\
    # are_reraise_still_fires_exhaust001
    def test_ambiguous_bare_reraise_still_fires_exhaust001(
        self, tmp_path: Path
    ) -> None:
        """T-1402 regression: `boundary`'s own bare `raise` (re-raise, no
        preceding catch at all -- a real, in-source construct, not an
        unresolved callee) still fires EXHAUST001 exactly as before the
        precision fix -- this is the case the narrowing must NOT silence."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def boundary(flag):\n"
                "    if flag:\n"
                "        raise\n"
                "    try:\n"
                "        pass\n"
                "    except ValueError:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        found = _by_rule(violations, "EXHAUST001")
        assert found
        assert any(v.symref == "mod.py::boundary" for v in found)
        assert not _by_rule(violations, "EXHAUST003")

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate.test_catch_all_o\
    # f_unknown_does_not_fire_exhaust001
    def test_catch_all_of_unknown_does_not_fire_exhaust001(
        self, tmp_path: Path
    ) -> None:
        """Same shape as above but the boundary's own catch is a real
        catch-all (`except Exception:`) -- Unknown is discharged, no
        EXHAUST001."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def boundary():\n"
                "    try:\n"
                "        some_unresolved_call()\n"
                "    except Exception:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        assert not _by_rule(violations, "EXHAUST001")

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate.test_declared_fr\
    # ob_raises_directive_discharges_exhaust002
    def test_declared_frob_raises_directive_discharges_exhaust002(
        self, tmp_path: Path
    ) -> None:
        """A `# frob:raises TypeError` directive directly above `boundary`
        declares the leaked TypeError as intentional propagation -- no
        EXHAUST002, unlike the undeclared case above."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def risky():\n"
                "    raise TypeError('bad')\n"
                "\n"
                "# frob:raises TypeError\n"
                "def boundary():\n"
                "    try:\n"
                "        risky()\n"
                "    except ValueError:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        assert not _by_rule(violations, "EXHAUST002")

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate.test_function_wi\
    # th_no_catches_is_not_a_boundary
    def test_function_with_no_catches_is_not_a_boundary(self, tmp_path: Path) -> None:
        """`caller` calls `risky` (which raises TypeError) but has no
        `except` clause of its own -- it is plain propagation, not a
        declared boundary, so neither EXHAUST001 nor EXHAUST002 fires."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def risky():\n"
                "    raise TypeError('bad')\n"
                "\n"
                "def caller():\n"
                "    risky()\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        assert not _by_rule(violations, "EXHAUST001")
        assert not _by_rule(violations, "EXHAUST002")
# frob:ticket T-0690
class TestFfiBoundaryGate:
    """T-0690: frob.gates._ffi_boundary.ffi_boundary_gate -- FFI001 cross-
    checks a pyo3 `.pyi` stub's declared `frob:raises` against the Rust
    source's own observed raised-type set (paired via a `frob:describes
    <path>.rs` pragma in the stub's module docstring); FFI002 demands a
    `# frob:callee-raises` declaration on every call made through a
    ctypes-loaded library handle."""

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestFfiBoundaryGate.test_pyo3_drift_fires_f\
    # fi001
    def test_pyo3_drift_fires_ffi001(self, tmp_path: Path) -> None:
        """The Rust side constructs PyValueError but the `.pyi` stub's
        `frob:raises` omits it -- FFI001 names both sides."""
        from frob.gates._ffi_boundary import ffi_boundary_gate

        (tmp_path / "crate").mkdir()
        _write(
            tmp_path,
            "crate/lib.rs",
            (
                "#[pyfunction]\n"
                "fn foo(x: i64) -> PyResult<i64> {\n"
                "    if x < 0 {\n"
                '        return Err(PyValueError::new_err("bad"));\n'
                "    }\n"
                "    Ok(x)\n"
                "}\n"
            ),
        )
        _write(
            tmp_path,
            "crate.pyi",
            (
                '"""Stub.\n'
                "\n"
                "frob:describes crate/lib.rs\n"
                '"""\n'
                "\n"
                "def foo(x: int) -> int: ...\n"
            ),
        )
        violations = ffi_boundary_gate(tmp_path, tmp_path)
        found = _by_rule(violations, "FFI001")
        assert found
        assert any("ValueError" in v.message for v in found)
        assert any(v.symref == "crate.pyi::foo" for v in found)

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestFfiBoundaryGate.test_pyo3_declared_matc\
    # hes_no_drift
    def test_pyo3_declared_matches_no_drift(self, tmp_path: Path) -> None:
        """Same Rust side, but the `.pyi` stub declares `# frob:raises
        ValueError` above `def foo` -- no FFI001."""
        from frob.gates._ffi_boundary import ffi_boundary_gate

        (tmp_path / "crate").mkdir()
        _write(
            tmp_path,
            "crate/lib.rs",
            (
                "#[pyfunction]\n"
                "fn foo(x: i64) -> PyResult<i64> {\n"
                "    if x < 0 {\n"
                '        return Err(PyValueError::new_err("bad"));\n'
                "    }\n"
                "    Ok(x)\n"
                "}\n"
            ),
        )
        _write(
            tmp_path,
            "crate.pyi",
            (
                '"""Stub.\n'
                "\n"
                "frob:describes crate/lib.rs\n"
                '"""\n'
                "\n"
                "# frob:raises ValueError\n"
                "def foo(x: int) -> int: ...\n"
            ),
        )
        violations = ffi_boundary_gate(tmp_path, tmp_path)
        assert not _by_rule(violations, "FFI001")

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestFfiBoundaryGate.test_ctypes_call_withou\
    # t_declaration_fires_ffi002
    def test_ctypes_call_without_declaration_fires_ffi002(self, tmp_path: Path) -> None:
        """A call through a ctypes.CDLL-loaded handle with no callee-raises
        comment (`# frob` + `:callee-raises`) on its own line fires
        FFI002."""
        from frob.gates._ffi_boundary import ffi_boundary_gate

        _write(
            tmp_path,
            "mod.py",
            ('import ctypes\nlib = ctypes.CDLL("libfoo.so")\nlib.do_thing(1)\n'),
        )
        violations = ffi_boundary_gate(tmp_path, tmp_path)
        found = _by_rule(violations, "FFI002")
        assert found
        assert any("do_thing" in v.message for v in found)

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestFfiBoundaryGate.test_ctypes_call_with_e\
    # mpty_declaration_clean
    def test_ctypes_call_with_empty_declaration_clean(self, tmp_path: Path) -> None:
        """The same call, but with a bare `# frob:callee-raises` comment
        (the valid "raises nothing, errno convention" declaration) on its
        own line -- no FFI002."""
        from frob.gates._ffi_boundary import ffi_boundary_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "import ctypes\n"
                'lib = ctypes.CDLL("libfoo.so")\n'
                "lib.do_thing(1)  # frob:callee-raises\n"
            ),
        )
        violations = ffi_boundary_gate(tmp_path, tmp_path)
        assert not _by_rule(violations, "FFI002")
class TestErrorsAsValuesAdvisory:
    """T-0688: frob.arch._exceptions.check_errors_as_values -- a PUBLIC
    function/method whose recoverable may-raise set (computed via
    frob.arch._mayraise.compute_may_raise) has no same-module caller
    visibly handling it recommends a typani Result[T, E], the raise sites
    named as the sketch."""

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestErrorsAsValuesAdvisory.test_public_rais\
    # er_with_no_handling_caller_recommends_result
    def test_public_raiser_with_no_handling_caller_recommends_result(
        self,
    ) -> None:
        from frob.arch._exceptions import check_errors_as_values
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        risky = NormalizedFunction(
            name="risky",
            line=1,
            body_line_count=2,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        caller = NormalizedFunction(
            name="caller",
            line=5,
            body_line_count=2,
            calls=[NormalizedCall(callee="risky", line=6)],
        )
        module = NormalizedModule(
            path="mod.py", language="python", functions=[risky, caller]
        )
        suggestions = check_errors_as_values(module)
        matches = [
            s for s in suggestions if s.category == "errors-as-values-recommended"
        ]
        assert matches
        assert any(s.symref == "mod.py::risky" for s in matches)

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestErrorsAsValuesAdvisory.test_public_rais\
    # er_with_handling_caller_not_flagged
    def test_public_raiser_with_handling_caller_not_flagged(self) -> None:
        from frob.arch._exceptions import check_errors_as_values
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        risky = NormalizedFunction(
            name="risky",
            line=1,
            body_line_count=2,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        caller = NormalizedFunction(
            name="caller",
            line=5,
            body_line_count=4,
            calls=[NormalizedCall(callee="risky", line=7)],
            catches=[NormalizedCatch(line=8, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="mod.py", language="python", functions=[risky, caller]
        )
        suggestions = check_errors_as_values(module)
        assert not any(
            s.category == "errors-as-values-recommended" for s in suggestions
        )

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestErrorsAsValuesAdvisory.test_private_rai\
    # ser_not_flagged
    def test_private_raiser_not_flagged(self) -> None:
        from frob.arch._exceptions import check_errors_as_values
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        risky = NormalizedFunction(
            name="_risky",
            line=1,
            body_line_count=2,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        module = NormalizedModule(path="mod.py", language="python", functions=[risky])
        suggestions = check_errors_as_values(module)
        assert not any(
            s.category == "errors-as-values-recommended" for s in suggestions
        )

    # frob:tests \
    # tests/gates_suite/test_compliance.py::TestErrorsAsValuesAdvisory.test_only_ubiqui\
    # tous_or_unknown_raises_not_flagged
    def test_only_ubiquitous_or_unknown_raises_not_flagged(self) -> None:
        """`risky` calls an unresolvable function only (contributes solely
        `UNKNOWN`, no `_RECOVERABLE_EXCEPTION_TYPES` member) -- never
        flagged, since this advisory never recommends a Result signature
        off an unidentified failure mode alone."""
        from frob.arch._exceptions import check_errors_as_values
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        risky = NormalizedFunction(
            name="risky",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="some_unresolved_call", line=2)],
        )
        module = NormalizedModule(path="mod.py", language="python", functions=[risky])
        suggestions = check_errors_as_values(module)
        assert not any(
            s.category == "errors-as-values-recommended" for s in suggestions
        )
