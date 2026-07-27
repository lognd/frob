"""Unit-level coverage for `frob.deploy._generate_windows` (T-0264): the
windows PowerShell install/status/uninstall renderers, against hand-built
`KernelModel`s -- mirrors `test_generate.py`'s hand-built-value shape.
"""

from __future__ import annotations

from frob.deploy._generate import sorted_manifest_entries
from frob.deploy._generate_windows import (
    generate_windows_install_script,
    generate_windows_status_script,
    generate_windows_uninstall_script,
    windows_entries,
)
from frob.strata._models import KernelModel, Node


def _windows_model() -> KernelModel:
    return KernelModel(
        nodes=(
            Node(
                id="winapi",
                trust="trusted",
                attrs=(
                    "platform=windows",
                    "service_account=svc-api",
                    "service",
                    "acl=C:\\ProgramData\\api|BUILTIN\\Administrators:FullControl",
                    "acl=C:\\ProgramData\\api|Everyone:Write:deny:no_inherit",
                    "listens=443",
                    "pipe=frobpipe",
                ),
            ),
            Node(id="linux-db", trust="trusted", attrs=("runs_as=db-svc", "unit")),
        )
    )


def _gmsa_model() -> KernelModel:
    return KernelModel(
        nodes=(
            Node(
                id="winsvc",
                trust="trusted",
                attrs=(
                    "platform=windows",
                    "service_account=gmsa-svc$",
                    "service_account_gmsa",
                    "service",
                ),
            ),
        )
    )


class TestWindowsEntries:
    # frob:tests tests/unit/deploy/test_generate_windows.py::TestWindowsEntries.test_filters_to_windows_only  # noqa: E501
    def test_filters_to_windows_only(self):
        entries = windows_entries(sorted_manifest_entries(_windows_model()))
        assert [e.node_id for e in entries] == ["winapi"]


class TestInstall:
    # frob:tests tests/unit/deploy/test_generate_windows.py::TestInstall.test_idempotent
    def test_idempotent(self):
        """install.ps1 has ONE `New-LocalUser` per distinct service
        account, gated by `Get-LocalUser`, so a re-run against an
        already-created account issues no re-creation command -- the
        script itself is check-then-apply, same idempotency contract
        `_generate.py::generate_install_script` establishes for bash."""
        script = generate_windows_install_script(_windows_model())
        assert script.count('New-LocalUser -Name "svc-api"') == 1
        assert 'if (-not (Get-LocalUser -Name "svc-api"' in script

    def test_empty_model_no_windows_entries(self):
        model = KernelModel(
            nodes=(Node(id="db", trust="trusted", attrs=("runs_as=db-svc", "unit")),)
        )
        script = generate_windows_install_script(model)
        assert "no windows host manifests declared" in script

    def test_acl_grant_and_deny_flags(self):
        script = generate_windows_install_script(_windows_model())
        assert '/grant "BUILTIN\\Administrators:(F)"' in script
        assert '/deny "Everyone:(W)"' in script
        assert "/inheritance:r" in script

    def test_firewall_rule_opened(self):
        script = generate_windows_install_script(_windows_model())
        assert "New-NetFirewallRule" in script
        assert "-LocalPort 443" in script

    def test_gmsa_account_uses_ad_service_account_cmdlets(self):
        script = generate_windows_install_script(_gmsa_model())
        assert "Install-ADServiceAccount" in script
        assert "New-LocalUser" not in script

    def test_service_not_present_notes_missing_bin_path(self):
        """A `service`-marked node with no `bin_path` declared (T-0629)
        -- when the SCM service does not already exist, install.ps1 says
        so rather than fabricating a creation command."""
        script = generate_windows_install_script(_windows_model())
        assert "no bin_path declared, skipping creation" in script

    def test_deny_logon_scope_cut_is_documented(self):
        script = generate_windows_install_script(_windows_model())
        assert "deny-logon rights" in script

    # frob:tests tests/unit/deploy/test_generate_windows.py::TestInstall.test_creates_service_when_bin_path_declared  # noqa: E501
    def test_creates_service_when_bin_path_declared(self):
        """T-0629: a `service`-marked node declaring `bin_path` gets an
        `sc.exe create` with that ImagePath, inside the same `sc.exe
        query` failure branch the pre-T-0629 skip message used -- the
        creation only fires when the service does not already exist, then
        hardening runs against the now-created service."""
        model = KernelModel(
            nodes=(
                Node(
                    id="winapi",
                    trust="trusted",
                    attrs=(
                        "platform=windows",
                        "service",
                        "bin_path=C:\\Program Files\\api\\api.exe",
                        "bin_path_args=--config C:\\ProgramData\\api\\config.yaml",
                    ),
                ),
            )
        )
        script = generate_windows_install_script(model)
        assert (
            'sc.exe create "FrobDeploy-winapi" binPath= '
            '"C:\\Program Files\\api\\api.exe --config '
            'C:\\ProgramData\\api\\config.yaml" start= auto' in script
        )
        assert 'sc.exe sidtype "FrobDeploy-winapi" unrestricted' in script
        assert "no bin_path declared" not in script

    # frob:tests tests/unit/deploy/test_generate_windows.py::TestInstall.test_creates_service_without_args  # noqa: E501
    def test_creates_service_without_args(self):
        """T-0629: `bin_path_args` is optional -- the ImagePath is just
        the bare executable path when omitted."""
        model = KernelModel(
            nodes=(
                Node(
                    id="winapi",
                    trust="trusted",
                    attrs=(
                        "platform=windows",
                        "service",
                        "bin_path=C:\\Program Files\\api\\api.exe",
                    ),
                ),
            )
        )
        script = generate_windows_install_script(model)
        assert (
            'sc.exe create "FrobDeploy-winapi" binPath= '
            '"C:\\Program Files\\api\\api.exe" start= auto' in script
        )


class TestStatus:
    # frob:tests tests/unit/deploy/test_generate_windows.py::TestStatus.test_one_line
    def test_one_line(self):
        script = generate_windows_status_script(_windows_model())
        assert "service=FrobDeploy-winapi node=winapi state=$state" in script
        assert "port=443" in script
        assert "pipe=frobpipe" in script

    def test_no_service_declared(self):
        model = KernelModel(
            nodes=(
                Node(
                    id="winacl",
                    trust="trusted",
                    attrs=("platform=windows", "acl=C:\\x|Everyone:Read"),
                ),
            )
        )
        script = generate_windows_status_script(model)
        assert "no windows services declared" in script


class TestUninstall:
    # frob:tests tests/unit/deploy/test_generate_windows.py::TestUninstall.test_removes
    def test_removes(self):
        script = generate_windows_uninstall_script(_windows_model())
        assert 'sc.exe delete "FrobDeploy-winapi"' in script
        assert 'Remove-NetFirewallRule -DisplayName "FrobDeploy-winapi-443"' in script
        assert '/remove "BUILTIN\\Administrators"' in script
        assert '/remove "Everyone"' in script
        assert 'Remove-LocalUser -Name "svc-api"' in script

    def test_empty_model_no_windows_entries(self):
        model = KernelModel(
            nodes=(Node(id="db", trust="trusted", attrs=("runs_as=db-svc", "unit")),)
        )
        script = generate_windows_uninstall_script(model)
        assert "no windows host manifests declared" in script

    def test_gmsa_uninstall_uses_ad_service_account_cmdlets(self):
        script = generate_windows_uninstall_script(_gmsa_model())
        assert "Uninstall-ADServiceAccount" in script
        assert "Remove-LocalUser" not in script


class TestKrbIntegration:
    """T-0264: SPN registration + delegation flags, sourced from the SAME
    node's `std.krb` manifest (`frob.strata.krb_manifest_for`)."""

    def _model_with_krb(self, delegation_attr: str | None) -> KernelModel:
        attrs = [
            "platform=windows",
            "service_account=svc-api",
            "service",
            "krb_spn=HTTP/api.example.com",
        ]
        if delegation_attr is not None:
            attrs.append(delegation_attr)
        return KernelModel(
            nodes=(Node(id="winapi", trust="trusted", attrs=tuple(attrs)),)
        )

    def test_spn_registered(self):
        script = generate_windows_install_script(self._model_with_krb(None))
        assert 'setspn -A "HTTP/api.example.com" "svc-api"' in script

    def test_constrained_delegation_sets_flags(self):
        model = self._model_with_krb("krb_delegation=constrained")
        script = generate_windows_install_script(model)
        assert "-TrustedToAuthForDelegation $true" in script

    def test_unconstrained_delegation_sets_flag(self):
        model = self._model_with_krb("krb_delegation=unconstrained")
        script = generate_windows_install_script(model)
        assert "-TrustedForDelegation $true" in script

    def test_rbcd_delegation_is_documented_deferred(self):
        model = self._model_with_krb("krb_delegation=rbcd")
        script = generate_windows_install_script(model)
        assert "resource-based constrained delegation (RBCD)" in script
        assert "PrincipalsAllowedToDelegateToAccount" in script

    def test_no_krb_manifest_issues_no_krb_commands(self):
        script = generate_windows_install_script(_windows_model())
        assert "setspn" not in script
