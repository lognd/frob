"""Unit-level coverage for `std.host`'s attr-desugar/read-back pair
(T-0255, `src/frob/strata/_host.py`): `_host_attrs` (desugar) and
`host_manifest_for` (read-back) against hand-built values, mirroring the
`_pii.py::node_pii_tags` precedent's unit-test shape. End-to-end
parse -> elaborate coverage lives in `test_litmus_host.py`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from frob.strata._host import (
    HostAcl,
    HostManifest,
    HostOwns,
    HostPlatform,
    _host_attrs,
    host_manifest_for,
)
from frob.strata._models import Node


class TestHostAttrs:
    # frob:tests src/frob/strata/_host.py::_host_attrs kind="unit"
    def test_desugars(self):
        attrs = _host_attrs(
            runs_as="api-svc",
            is_unit=True,
            owns=(("/etc/api", "0644"), ("/var/lib/api", "0750")),
            listens=(8080, 8443),
        )
        assert attrs == (
            "runs_as=api-svc",
            "unit",
            "owns=/etc/api:0644",
            "owns=/var/lib/api:0750",
            "listens=8080",
            "listens=8443",
        )

    # frob:tests src/frob/strata/_host.py::_host_attrs kind="unit"
    def test_no_clauses_desugars_to_empty(self):
        attrs = _host_attrs(runs_as=None, is_unit=False, owns=(), listens=())
        assert attrs == ()

    # frob:tests src/frob/strata/_host.py::_host_attrs kind="unit"
    def test_desugars_windows_fields(self):
        """T-0261: platform/service_account/service/acl/pipe desugar to
        their own attrs, in declaration order after owns/listens/group/
        sudoers (same convention `_host_attrs` uses throughout)."""
        attrs = _host_attrs(
            runs_as=None,
            is_unit=False,
            owns=(),
            listens=(8443,),
            platform="windows",
            service_account="svc-api",
            service_account_gmsa=True,
            is_service=True,
            acl=(("C:\\ProgramData\\api", "BUILTIN\\Administrators:FullControl"),),
            pipes=("\\\\.\\pipe\\api-control",),
        )
        assert attrs == (
            "listens=8443",
            "platform=windows",
            "service_account=svc-api",
            "service_account_gmsa",
            "service",
            "acl=C:\\ProgramData\\api|BUILTIN\\Administrators:FullControl",
            "pipe=\\\\.\\pipe\\api-control",
        )

    # frob:tests src/frob/strata/_host.py::_host_attrs kind="unit"
    def test_desugars_bin_path(self):
        """T-0629: `bin_path`/`bin_path_args` desugar to `bin_path=`/
        `bin_path_args=` attrs, appended after `pipes` (same declaration-
        order convention `_host_attrs` uses throughout)."""
        attrs = _host_attrs(
            runs_as=None,
            is_unit=False,
            owns=(),
            listens=(),
            bin_path="C:\\Program Files\\api\\api.exe",
            bin_path_args="--config C:\\ProgramData\\api\\config.yaml",
        )
        assert attrs == (
            "bin_path=C:\\Program Files\\api\\api.exe",
            "bin_path_args=--config C:\\ProgramData\\api\\config.yaml",
        )

    # frob:tests src/frob/strata/_host.py::_host_attrs kind="unit"
    def test_desugars_group_and_sudoers(self):
        """T-0272: `group`/`sudoers` desugar to `group=`/`sudoers=` attrs,
        one per entry, appended after owns/listens (same declaration-order
        convention `_host_attrs` uses throughout)."""
        attrs = _host_attrs(
            runs_as="api-svc",
            is_unit=False,
            owns=(),
            listens=(),
            group=("deploy", "docker"),
            sudoers=("ALL=(root) NOPASSWD: /bin/systemctl restart api",),
        )
        assert attrs == (
            "runs_as=api-svc",
            "group=deploy",
            "group=docker",
            "sudoers=ALL=(root) NOPASSWD: /bin/systemctl restart api",
        )


class TestHostManifest:
    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_reads(self):
        node = Node(
            id="api",
            trust="trusted",
            attrs=(
                "runs_as=api-svc",
                "unit",
                "owns=/etc/api:0644",
                "listens=8080",
            ),
        )
        manifest = host_manifest_for(node)
        assert manifest is not None
        assert manifest.platform is HostPlatform.LINUX_SYSTEMD
        assert manifest.runs_as == "api-svc"
        assert manifest.is_unit is True
        assert manifest.owns == (HostOwns(path="/etc/api", mode="0644"),)
        assert manifest.listens == (8080,)
        assert manifest.group == ()
        assert manifest.sudoers == ()

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_node_with_no_host_attrs_returns_none(self):
        node = Node(id="api", trust="trusted", attrs=("code=src/**",))
        assert host_manifest_for(node) is None

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_reads_group_and_sudoers(self):
        """T-0272: `group=`/`sudoers=` attrs read back into
        `HostManifest.group`/`.sudoers`."""
        node = Node(
            id="api",
            trust="trusted",
            attrs=(
                "runs_as=api-svc",
                "group=deploy",
                "group=docker",
                "sudoers=ALL=(root) NOPASSWD: /bin/systemctl restart api",
            ),
        )
        manifest = host_manifest_for(node)
        assert manifest is not None
        assert manifest.group == ("deploy", "docker")
        assert manifest.sudoers == ("ALL=(root) NOPASSWD: /bin/systemctl restart api",)

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_group_only_declares_manifest(self):
        """A node declaring ONLY `group` (no runs_as/unit/owns/listens)
        still yields a manifest -- `declared` tracks any std.host attr,
        not just the pre-T-0272 four."""
        node = Node(id="api", trust="trusted", attrs=("group=deploy",))
        manifest = host_manifest_for(node)
        assert manifest is not None
        assert manifest.group == ("deploy",)


class TestHostManifestWindows:
    """T-0261: Windows-platform read-back coverage."""

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_reads_windows_fields(self):
        node = Node(
            id="api",
            trust="trusted",
            attrs=(
                "listens=8443",
                "platform=windows",
                "service_account=svc-api",
                "service_account_gmsa",
                "service",
                "acl=C:\\ProgramData\\api|BUILTIN\\Administrators:FullControl",
                "pipe=\\\\.\\pipe\\api-control",
            ),
        )
        manifest = host_manifest_for(node)
        assert manifest is not None
        assert manifest.platform is HostPlatform.WINDOWS
        assert manifest.service_account == "svc-api"
        assert manifest.service_account_gmsa is True
        assert manifest.is_service is True
        assert manifest.acl == (
            HostAcl(
                path="C:\\ProgramData\\api",
                rule="BUILTIN\\Administrators:FullControl",
            ),
        )
        assert manifest.pipes == ("\\\\.\\pipe\\api-control",)
        assert manifest.listens == (8443,)

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_reads_bin_path(self):
        """T-0629: `bin_path=`/`bin_path_args=` attrs read back into
        `HostManifest.bin_path`/`.bin_path_args`."""
        node = Node(
            id="api",
            trust="trusted",
            attrs=(
                "platform=windows",
                "service",
                "bin_path=C:\\Program Files\\api\\api.exe",
                "bin_path_args=--config C:\\ProgramData\\api\\config.yaml",
            ),
        )
        manifest = host_manifest_for(node)
        assert manifest is not None
        assert manifest.bin_path == "C:\\Program Files\\api\\api.exe"
        assert manifest.bin_path_args == "--config C:\\ProgramData\\api\\config.yaml"

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_bin_path_defaults_none(self):
        """A `service`-marked node with no `bin_path` declared keeps
        `HostManifest.bin_path`/`.bin_path_args` at their `None` default
        (backward compatible with every pre-T-0629 manifest)."""
        node = Node(id="api", trust="trusted", attrs=("platform=windows", "service"))
        manifest = host_manifest_for(node)
        assert manifest is not None
        assert manifest.bin_path is None
        assert manifest.bin_path_args is None

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_no_platform_attr_defaults_to_linux_systemd(self):
        node = Node(id="api", trust="trusted", attrs=("runs_as=api-svc",))
        manifest = host_manifest_for(node)
        assert manifest is not None
        assert manifest.platform is HostPlatform.LINUX_SYSTEMD

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_unknown_platform_value_raises(self):
        node = Node(id="api", trust="trusted", attrs=("platform=macos",))
        with pytest.raises(ValueError, match="not a recognized HostPlatform"):
            host_manifest_for(node)


class TestHostAclRuleValidation:
    """T-0261: `acl` RULE well-formedness (mirrors `TestHostOwnsModeValidation`)."""

    # frob:tests src/frob/strata/_host.py::HostAcl._validate_rule kind="unit"
    def test_valid_rule_accepted(self):
        assert (
            HostAcl(path="C:\\api", rule="Everyone:FullControl").rule
            == "Everyone:FullControl"
        )

    # frob:tests src/frob/strata/_host.py::HostAcl._validate_rule kind="unit"
    def test_deny_and_no_inherit_flags_accepted(self):
        assert (
            HostAcl(path="C:\\api", rule="svc-api:Modify:deny:no_inherit").rule
            == "svc-api:Modify:deny:no_inherit"
        )

    # frob:tests src/frob/strata/_host.py::HostAcl._validate_rule kind="unit"
    def test_missing_rights_rejected(self):
        with pytest.raises(ValidationError):
            HostAcl(path="C:\\api", rule="Everyone:")

    # frob:tests src/frob/strata/_host.py::HostAcl._validate_rule kind="unit"
    def test_unknown_flag_rejected(self):
        with pytest.raises(ValidationError):
            HostAcl(path="C:\\api", rule="Everyone:FullControl:bogus")

    # frob:tests src/frob/strata/_host.py::HostAcl._validate_rule kind="unit"
    def test_no_colon_rejected(self):
        with pytest.raises(ValidationError):
            HostAcl(path="C:\\api", rule="FullControl")


class TestHostOwnsModeValidation:
    """T-0270 (deferred from T-0255): `owns` MODE well-formedness."""

    # frob:tests src/frob/strata/_host.py::HostOwns._validate_mode kind="unit"
    def test_valid_octal_mode_accepted(self):
        assert HostOwns(path="/etc/api", mode="0644").mode == "0644"
        assert HostOwns(path="/var/lib/api", mode="0755").mode == "0755"

    # frob:tests src/frob/strata/_host.py::HostOwns._validate_mode kind="unit"
    def test_setuid_four_digit_mode_accepted(self):
        assert HostOwns(path="/usr/bin/x", mode="4755").mode == "4755"

    # frob:tests src/frob/strata/_host.py::HostOwns._validate_mode kind="unit"
    def test_non_octal_mode_rejected(self):
        with pytest.raises(ValidationError):
            HostOwns(path="/etc/api", mode="rwx")

    # frob:tests src/frob/strata/_host.py::HostOwns._validate_mode kind="unit"
    def test_out_of_range_digit_mode_rejected(self):
        with pytest.raises(ValidationError):
            HostOwns(path="/etc/api", mode="999")

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_bad_mode_in_manifest_attrs_raises(self):
        node = Node(
            id="api",
            trust="trusted",
            attrs=("owns=/etc/api:999",),
        )
        with pytest.raises(ValidationError):
            host_manifest_for(node)


class TestHostManifestListensValidation:
    """T-0270 (deferred from T-0255): `listens` PORT well-formedness."""

    # frob:tests src/frob/strata/_host.py::HostManifest._validate_listens kind="unit"
    def test_valid_port_accepted(self):
        manifest = HostManifest(platform=HostPlatform.LINUX_SYSTEMD, listens=(8080,))
        assert manifest.listens == (8080,)

    # frob:tests src/frob/strata/_host.py::HostManifest._validate_listens kind="unit"
    def test_out_of_range_port_rejected(self):
        with pytest.raises(ValidationError):
            HostManifest(platform=HostPlatform.LINUX_SYSTEMD, listens=(70000,))

    # frob:tests src/frob/strata/_host.py::HostManifest._validate_listens kind="unit"
    def test_zero_port_rejected(self):
        with pytest.raises(ValidationError):
            HostManifest(platform=HostPlatform.LINUX_SYSTEMD, listens=(0,))

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_bad_port_in_manifest_attrs_raises(self):
        node = Node(id="api", trust="trusted", attrs=("listens=70000",))
        with pytest.raises(ValidationError):
            host_manifest_for(node)

    # frob:tests src/frob/strata/_host.py::host_manifest_for kind="unit"
    def test_non_numeric_port_in_manifest_attrs_raises(self):
        node = Node(id="api", trust="trusted", attrs=("listens=abc",))
        with pytest.raises(ValueError, match="not a valid integer"):
            host_manifest_for(node)
