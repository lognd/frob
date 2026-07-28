"""`frob deploy generate` windows target: compile `std.host` (T-0255/T-0261)
`HostManifest` windows fields into idempotent PowerShell install/status/
uninstall scripts (T-0264, deploy epic T-0254), the same check-then-apply
contract `_generate.py`'s bash target establishes for `HostPlatform.
LINUX_SYSTEMD`.

Only entries whose `HostManifest.platform == HostPlatform.WINDOWS` are
rendered here (`windows_entries`) -- a linux-only model never produces
`install.ps1`/`status.ps1`/`uninstall.ps1` at all (`_generate.py::
generate_all` only calls into this module when at least one windows
entry exists), mirroring how a windows-only model produces no bash.

- **install.ps1**: check-then-apply per step, same idempotency posture as
  `install.sh` -- a re-run performs zero mutating commands and exits 0.
  Creates one service account per distinct `service_account` (a local
  account, or `Install-ADServiceAccount` for a `gmsa`-marked one), applies
  NTFS ACLs exactly from each declared `acl` entry (`icacls`), opens the
  declared firewall ports (`New-NetFirewallRule`) for every node's
  `listens` ports, and -- when a `std.krb` manifest
  (`frob.strata.krb_manifest_for`, NOT redefined here) is present on the
  same node -- registers its `spns` (`setspn`) and applies its
  `delegation` setting. `service`-marked nodes get their SCM service
  IDEMPOTENTLY CREATED (T-0629: `sc.exe create` with the declared
  `bin_path`/`bin_path_args` ImagePath) when absent and `bin_path` is
  declared, then hardened (SID type, required-privilege set) via
  `sc.exe config` -- a `service`-marked node with no `bin_path` declared
  falls back to the pre-T-0629 posture: hardening-only IF the service
  already exists, and a plain skip message (not a fabricated placeholder
  binary path) when it is absent.
- **status.ps1**: per `service`-marked node, `sc.exe query` state plus a
  firewall-rule-present probe per declared `listens` port and a named-pipe
  existence probe per declared `pipe` -- one line per unit, machine-
  parseable, same `key=value ...` shape `status.sh` uses.
- **uninstall.ps1**: removes EXACTLY the manifest's own set -- firewall
  rules, ACL grants, SCM service hardening/service (when present), SPN
  registrations, service accounts -- nothing else, same artifact-freeness
  contract `uninstall.sh` documents.

Every generated script's header carries the SAME `DIGEST_HEADER_PREFIX`
line (`frob.deploy._generate.manifest_digest`, computed over ALL entries
of every platform) that `_generate.py`'s bash scripts carry -- one digest,
one `DEPLOY001` drift lock, covering both platforms' generated output
(`_drift.py`'s `_GENERATED_FILENAMES` lists all six filenames).

Depends only on in-box Windows tools (`sc.exe`, `icacls`, `setspn.exe`,
`New-NetFirewallRule`/`Get-NetFirewallRule` from the in-box
`NetSecurity` module) -- EXCEPT `Install-ADServiceAccount`/
`Set-ADAccountControl`/`Set-ADUser` (gMSA creation and Kerberos delegation
flags), which require the `ActiveDirectory` RSAT module on a domain-joined
host; this mirrors the linux target's own honestly-documented dependency
posture (e.g. `useradd`/`systemctl` assumed present) rather than adding a
scope-cut fiction.

v0 scope cuts, inherited honestly from the linux target's own precedent:
required-privilege sets default to the empty (most-restrictive) set
(`_REQUIRED_PRIVS`, mirroring `_generate.py::_CAP_KIND_MAP`'s coarse `may`
join) since `std.host` has no windows privilege vocabulary yet; deny-logon
rights (`SeDenyInteractiveLogonRight` etc.) have no in-box, idempotently-
checkable primitive without RSAT's `secedit` INF round-trip and are
deferred rather than fabricated (documented inline, `_DENY_LOGON_NOTE`);
RBCD delegation (`KrbDelegationKind.RBCD`) is likewise documented-deferred
(`_RBCD_NOTE`) since it needs `PrincipalsAllowedToDelegateToAccount`
plumbing beyond this ticket's scope.
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"

from __future__ import annotations

from frob.logging import get_logger
from frob.strata import HostPlatform, KernelModel, KrbDelegationKind
from frob.strata._host import HostAcl
from frob.strata._krb import krb_manifest_for

from ._generate import (
    DIGEST_HEADER_PREFIX,
    ManifestEntry,
    manifest_digest,
    sorted_manifest_entries,
)

_log = get_logger(__name__)

#: `acl` RULE RIGHTS token -> `icacls` right-letters. Unmapped tokens are
#: passed through verbatim (icacls also accepts raw letters, e.g. an
#: operator already spelling `"F"`) -- coarse, documented mapping, same
#: honesty posture `_generate.py::_CAP_KIND_MAP` established for `may`
#: capability kinds.
_ACL_RIGHTS_MAP: dict[str, str] = {
    "FullControl": "F",
    "Modify": "M",
    "Write": "W",
    "Read": "R",
    "ReadAndExecute": "RX",
}

#: `std.host` has no windows privilege vocabulary yet (module docstring):
#: every `service`-marked node gets the empty (most restrictive) required-
#: privilege set, mirroring `_CAP_KIND_MAP`'s unmapped-kind default.
_REQUIRED_PRIVS = ""

#: Deny-logon rights (module docstring scope cut): documented inline in
#: every generated `install.ps1` rather than fabricated, since there is
#: no in-box, idempotently-checkable primitive without RSAT's `secedit`
#: INF round-trip.
_DENY_LOGON_NOTE = (
    "# NOTE: deny-logon rights (e.g. SeDenyInteractiveLogonRight) are not\n"
    "# configured by this script -- std.host has no windows logon-rights\n"
    "# vocabulary yet, and there is no in-box, idempotently-checkable\n"
    "# primitive for them without the RSAT secedit INF round-trip. See\n"
    "# docs/modules/deploy.md#scope-and-honesty-notes-generate-windows.\n"
)

#: RBCD delegation (module docstring scope cut): documented inline rather
#: than fabricating `PrincipalsAllowedToDelegateToAccount` plumbing.
_RBCD_NOTE = (
    "# NOTE: resource-based constrained delegation (RBCD) is not configured\n"
    "# by this script -- it needs PrincipalsAllowedToDelegateToAccount\n"
    "# plumbing beyond this generator's current scope. See\n"
    "# docs/modules/deploy.md#scope-and-honesty-notes-generate-windows.\n"
)

#: One comment banner every windows script opens with -- same wording
#: `_generate.py::_GENERATED_BANNER` uses for the bash target, PowerShell
#: comments use the same `#` syntax so no re-spelling was needed.
_GENERATED_BANNER = (
    "# GENERATED by `frob deploy generate` -- DO NOT EDIT BY HAND.\n"
    "# Re-run `frob deploy generate` to regenerate after a design change.\n"
)


# frob:doc docs/modules/deploy.md#windows-generation
def windows_entries(entries: tuple[ManifestEntry, ...]) -> tuple[ManifestEntry, ...]:
    """Every entry in `entries` whose `HostManifest.platform` is
    `HostPlatform.WINDOWS` -- the ONE filter every renderer below shares,
    so `install.ps1`/`status.ps1`/`uninstall.ps1` can never disagree on
    which nodes they cover, and so `_generate.py::generate_all` can decide
    whether to emit windows output at all without re-deriving this walk."""
    return tuple(e for e in entries if e.manifest.platform == HostPlatform.WINDOWS)


def _krb_manifest_by_node_id(model: KernelModel) -> dict:
    """`node.id -> KrbManifest | None` for every node/store in `model`,
    the ONE lookup `_install_krb_block` uses -- `ManifestEntry` (T-0257)
    does not itself carry a `KrbManifest`, so this is computed once per
    render, keyed by the same node id `ManifestEntry.node_id` carries,
    rather than re-parsed per entry."""
    return {node.id: krb_manifest_for(node) for node in model.nodes}


# frob:waive DUP001 reason="dup grouped this with _generate.py::_header -- see that \
# function's own DUP001 waiver for full reasoning (T-0861)"
def _header(model: KernelModel, title: str) -> str:
    """The shared banner + digest header every generated windows script
    opens with -- same digest (`manifest_digest`, computed over every
    platform's entries) `_generate.py::_header` uses for bash, so ONE
    `DEPLOY001` drift lock covers both platforms' generated output."""
    digest = manifest_digest(model)
    return (
        f"# {title}\n"
        f"{_GENERATED_BANNER}"
        f"{DIGEST_HEADER_PREFIX}{digest}\n"
        "$ErrorActionPreference = 'Stop'\n"
        "\n"
    )


def _service_name(node_id: str) -> str:
    """SCM service name for `node_id` -- `FrobDeploy-<id>`, the ONE naming
    rule every windows renderer uses so a service configured by
    `install.ps1` is always the exact one `status.ps1` queries and
    `uninstall.ps1` deletes."""
    return f"FrobDeploy-{node_id}"


def _distinct_service_accounts(
    entries: tuple[ManifestEntry, ...],
) -> tuple[tuple[str, bool], ...]:
    """Every distinct `(service_account, gmsa)` identity declared across
    `entries`, in first-seen order -- the windows analog of `_generate.py::
    _distinct_runs_as` (T-0281 item 5's same dedup rationale: a service
    account shared by more than one node/store is created/removed once,
    not once per node)."""
    seen: dict[str, bool] = {}
    for entry in entries:
        name = entry.manifest.service_account
        if name is not None and name not in seen:
            seen[name] = entry.manifest.service_account_gmsa
    return tuple(seen.items())


# frob:waive DUP001 reason="dup grouped this with _uninstall_service_account_block on \
# the shared check-then-apply PowerShell template shape -- install vs uninstall are \
# intentional mirror-image operations (different cmdlets, different messages) \
# generated side-by-side for readability of the emitted script; unifying them would \
# obscure the emitted PowerShell rather than clarify it (T-0861)"
def _install_service_account_block(name: str, gmsa: bool) -> str:
    """Check-then-apply service-account creation: `Install-ADServiceAccount`
    for a `gmsa`-marked identity, `New-LocalUser` otherwise -- gated so a
    re-run performs zero commands when the account already exists."""
    if gmsa:
        return (
            f'if (-not (Get-ADServiceAccount -Identity "{name}" '
            "-ErrorAction SilentlyContinue)) {\n"
            f'    Install-ADServiceAccount -Identity "{name}"\n'
            f'    Write-Output "installed gMSA {name}"\n'
            "} else {\n"
            f'    Write-Output "gMSA {name} already present, skipping"\n'
            "}\n"
        )
    return (
        f'if (-not (Get-LocalUser -Name "{name}" '
        "-ErrorAction SilentlyContinue)) {\n"
        f'    New-LocalUser -Name "{name}" -NoPassword -AccountNeverExpires '
        "-PasswordNeverExpires -UserMayNotChangePassword | Out-Null\n"
        f'    Write-Output "created service account {name}"\n'
        "} else {\n"
        f'    Write-Output "service account {name} already present, skipping"\n'
        "}\n"
    )


# frob:waive DUP001 reason="dup grouped this with _install_service_account_block -- \
# see that function's own DUP001 waiver for full reasoning (T-0861)"
def _uninstall_service_account_block(name: str, gmsa: bool) -> str:
    """Check-then-apply service-account removal, mirroring
    `_install_service_account_block`'s gate."""
    if gmsa:
        return (
            f'if (Get-ADServiceAccount -Identity "{name}" '
            "-ErrorAction SilentlyContinue) {\n"
            f'    Uninstall-ADServiceAccount -Identity "{name}"\n'
            f'    Write-Output "removed gMSA {name}"\n'
            "}\n"
        )
    return (
        f'if (Get-LocalUser -Name "{name}" -ErrorAction SilentlyContinue) {{\n'
        f'    Remove-LocalUser -Name "{name}"\n'
        f'    Write-Output "removed service account {name}"\n'
        "}\n"
    )


def _acl_rights_letters(rule: str) -> str:
    """`icacls`-shaped right letters for one `HostAcl.rule`'s RIGHTS
    token (`_ACL_RIGHTS_MAP`), or the RIGHTS token itself when unmapped."""
    _principal, _, rest = rule.partition(":")
    rights, *_flags = rest.split(":")
    return _ACL_RIGHTS_MAP.get(rights, rights)


def _install_acl_block(acl: HostAcl) -> str:
    """Check-then-apply NTFS ACL grant for one declared `acl` entry:
    `icacls` is queried first, and `/grant`/`/deny` is only issued when
    the exact principal:rights grant is not already present -- a re-run
    over an already-correct ACL issues no mutating command."""
    principal, _, rest = acl.rule.partition(":")
    flags = rest.split(":")[1:]
    letters = _acl_rights_letters(acl.rule)
    verb = "/deny" if "deny" in flags else "/grant"
    grant = f"{principal}:({letters})"
    inherit_line = ""
    if "no_inherit" in flags:
        inherit_line = f'    icacls "{acl.path}" /inheritance:r | Out-Null\n'
    return (
        f'$currentAcl = (icacls "{acl.path}") -join "`n"\n'
        f'if ($currentAcl -notmatch [regex]::Escape("{grant}")) {{\n'
        f"{inherit_line}"
        f'    icacls "{acl.path}" {verb} "{grant}" | Out-Null\n'
        f'    Write-Output "applied acl {grant} on {acl.path}"\n'
        "} else {\n"
        f'    Write-Output "acl {grant} on {acl.path} already present"\n'
        "}\n"
    )


def _uninstall_acl_block(acl: HostAcl) -> str:
    """Remove EXACTLY one declared `acl` entry's grant -- `/remove` for
    the declared principal only, never a broader ACL reset."""
    principal, _, _rest = acl.rule.partition(":")
    return (
        f'if (Test-Path "{acl.path}") {{\n'
        f'    icacls "{acl.path}" /remove "{principal}" | Out-Null\n'
        f'    Write-Output "removed acl for {principal} on {acl.path}"\n'
        "}\n"
    )


def _firewall_rule_name(node_id: str, port: int) -> str:
    """Firewall rule display name for one node's declared `listens` port --
    the ONE naming rule install/status/uninstall share."""
    return f"FrobDeploy-{node_id}-{port}"


# frob:waive DUP001 reason="dup grouped this with _uninstall_firewall_block on the \
# shared check-then-apply PowerShell template shape -- install vs uninstall are \
# intentional mirror-image operations generated side-by-side for readability of the \
# emitted script, same convention as _install_service_account_block's own waiver \
# (T-0861)"
def _install_firewall_block(entry: ManifestEntry) -> str:
    """Check-then-apply firewall rule per declared `listens` port:
    `Get-NetFirewallRule` gates `New-NetFirewallRule` so a re-run issues
    no command for an already-open port."""
    lines: list[str] = []
    for port in entry.manifest.listens:
        name = _firewall_rule_name(entry.node_id, port)
        lines.append(
            f'if (-not (Get-NetFirewallRule -DisplayName "{name}" '
            "-ErrorAction SilentlyContinue)) {\n"
            f'    New-NetFirewallRule -DisplayName "{name}" -Direction Inbound '
            f"-Protocol TCP -LocalPort {port} -Action Allow | Out-Null\n"
            f'    Write-Output "opened firewall port {port} ({name})"\n'
            "} else {\n"
            f'    Write-Output "firewall port {port} ({name}) already open"\n'
            "}\n"
        )
    return "".join(lines)


# frob:waive DUP001 reason="dup grouped this with _install_firewall_block -- see that \
# function's own DUP001 waiver for full reasoning (T-0861)"
def _uninstall_firewall_block(entry: ManifestEntry) -> str:
    """Remove EXACTLY the firewall rules `_install_firewall_block` created
    for this node's declared `listens` ports."""
    lines: list[str] = []
    for port in entry.manifest.listens:
        name = _firewall_rule_name(entry.node_id, port)
        lines.append(
            f'if (Get-NetFirewallRule -DisplayName "{name}" '
            "-ErrorAction SilentlyContinue) {\n"
            f'    Remove-NetFirewallRule -DisplayName "{name}" | Out-Null\n'
            f'    Write-Output "removed firewall rule {name}"\n'
            "}\n"
        )
    return "".join(lines)


def _service_image_path(entry: ManifestEntry) -> str | None:
    """The `sc.exe create binPath=` ImagePath string for one declared
    `service`-marked entry -- `bin_path`, plus `bin_path_args` joined with
    a space when present (the ONE image path `sc.exe` itself expects:
    `"<exe> <args>"`), or `None` when no `bin_path` is declared (T-0629)."""
    bin_path = entry.manifest.bin_path
    if bin_path is None:
        return None
    if entry.manifest.bin_path_args:
        return f"{bin_path} {entry.manifest.bin_path_args}"
    return bin_path


def _install_service_hardening_block(entry: ManifestEntry) -> str:
    """Check-then-apply SCM service creation + hardening for a
    `service`-marked node (T-0629): when the service is absent AND a
    `bin_path` is declared, `sc.exe create` stands it up with that
    ImagePath before hardening runs -- idempotent, since creation only
    fires inside the `sc.exe query` failure branch. SID type
    (unrestricted) and required-privilege set (`_REQUIRED_PRIVS`, module
    docstring's coarse default) are applied via `sc.exe config` whenever
    the service is (or was just made) present; a `service`-marked node
    with no `bin_path` declared and no pre-existing service falls back to
    the pre-T-0629 skip message rather than fabricating a placeholder
    binary path."""
    if not entry.manifest.is_service:
        return ""
    name = _service_name(entry.node_id)
    image_path = _service_image_path(entry)
    harden = (
        f'    sc.exe sidtype "{name}" unrestricted | Out-Null\n'
        f'    sc.exe privs "{name}" "{_REQUIRED_PRIVS}" | Out-Null\n'
        f'    Write-Output "hardened service {name}"\n'
    )
    if image_path is not None:
        absent_branch = (
            f'    sc.exe create "{name}" binPath= "{image_path}" '
            "start= auto | Out-Null\n"
            f'    Write-Output "created service {name}"\n'
            f"{harden}"
        )
    else:
        absent_branch = (
            f'    Write-Output "service {name} not present -- no bin_path '
            "declared, skipping creation (see docs/modules/deploy.md"
            '#scope-and-honesty-notes-generate-windows)"\n'
        )
    return (
        f'$svc = sc.exe query "{name}" 2>&1\n'
        "if ($LASTEXITCODE -eq 0) {\n"
        f"{harden}"
        "} else {\n"
        f"{absent_branch}"
        "}\n"
    )


def _uninstall_service_block(entry: ManifestEntry) -> str:
    """Stop+delete exactly this node's own SCM service, when present --
    check-then-apply, same idempotent-uninstall posture `_generate.py::
    _uninstall_unit_block` establishes for systemd units."""
    if not entry.manifest.is_service:
        return ""
    name = _service_name(entry.node_id)
    return (
        f'$svc = sc.exe query "{name}" 2>&1\n'
        "if ($LASTEXITCODE -eq 0) {\n"
        f'    sc.exe stop "{name}" | Out-Null\n'
        f'    sc.exe delete "{name}" | Out-Null\n'
        f'    Write-Output "removed service {name}"\n'
        "}\n"
    )


def _install_krb_block(entry: ManifestEntry, krb_by_node: dict) -> str:
    """Check-then-apply SPN registration and delegation flags read from
    the SAME node's `std.krb` manifest (`krb_by_node`, `_krb_manifest_by_
    node_id`) when present -- `setspn -L` gates `setspn -A` per declared
    `spn` so a re-run registers nothing already bound, and
    `KrbDelegationKind.CONSTRAINED`/`UNCONSTRAINED` map to
    `Set-ADAccountControl` flags (`KrbDelegationKind.NONE`/no krb manifest
    issue no commands; `RBCD` is documented-deferred, `_RBCD_NOTE`,
    module docstring)."""
    account = entry.manifest.service_account
    if account is None:
        return ""
    krb = krb_by_node.get(entry.node_id)
    if krb is None:
        return ""
    lines: list[str] = []
    for spn in krb.spns:
        lines.append(
            f'$existing = setspn -L "{account}" 2>&1\n'
            f'if ($existing -notmatch [regex]::Escape("{spn}")) {{\n'
            f'    setspn -A "{spn}" "{account}" | Out-Null\n'
            f'    Write-Output "registered spn {spn} on {account}"\n'
            "} else {\n"
            f'    Write-Output "spn {spn} already registered on {account}"\n'
            "}\n"
        )
    if krb.delegation == KrbDelegationKind.CONSTRAINED:
        targets = " ".join(f'"{t}"' for t in krb.delegation_targets)
        lines.append(
            f'Set-ADAccountControl -Identity "{account}" '
            "-TrustedToAuthForDelegation $true\n"
        )
        if targets:
            lines.append(
                f'Set-ADUser -Identity "{account}" -Add '
                f"@{{'msDS-AllowedToDelegateTo'=@({targets})}}\n"
            )
    elif krb.delegation == KrbDelegationKind.UNCONSTRAINED:
        lines.append(
            f'Set-ADAccountControl -Identity "{account}" -TrustedForDelegation $true\n'
        )
    elif krb.delegation == KrbDelegationKind.RBCD:
        lines.append(_RBCD_NOTE)
    return "".join(lines)


# frob:doc docs/modules/deploy.md#windows-generation
# frob:tests tests/unit/deploy/test_generate_windows.py::TestInstall.test_idempotent kind="unit"  # noqa: E501
def generate_windows_install_script(model: KernelModel) -> str:
    """Render `install.ps1`: check-then-apply, one block per windows entry
    in `windows_entries(sorted_manifest_entries(model))` order -- service
    accounts, then per-node ACL/firewall/service-hardening/SPN-delegation
    (module docstring)."""
    entries = windows_entries(sorted_manifest_entries(model))
    krb_by_node = _krb_manifest_by_node_id(model)
    return _render_windows_install_script(model, entries, krb_by_node)


def _render_windows_install_script(
    model: KernelModel,
    entries: tuple[ManifestEntry, ...],
    krb_by_node: dict,
) -> str:
    """`generate_windows_install_script`'s body, taking an already-computed
    windows-only `entries` walk and `krb_by_node` lookup -- shared by
    `_generate.py::generate_all` so the windows walk is computed once per
    invocation, same discipline as the bash renderers (`_generate.py::
    _render_install_script`'s docstring, T-0281 item 4)."""
    parts = [_header(model, "frob deploy install.ps1"), _DENY_LOGON_NOTE]
    if not entries:
        parts.append(
            'Write-Output "no windows host manifests declared, nothing to install"\n'
        )
        return "".join(parts)
    parts.append('Write-Output "--- service accounts ---"\n')
    for name, gmsa in _distinct_service_accounts(entries):
        parts.append(_install_service_account_block(name, gmsa))
    for entry in entries:
        parts.append(f'Write-Output "--- {entry.node_id} ---"\n')
        parts.append(_install_service_hardening_block(entry))
        for acl in entry.manifest.acl:
            parts.append(_install_acl_block(acl))
        parts.append(_install_firewall_block(entry))
        parts.append(_install_krb_block(entry, krb_by_node))
    parts.append('Write-Output "install complete"\n')
    return "".join(parts)


def _status_service_block(entry: ManifestEntry) -> str:
    """One `service`-marked node's status line: `sc.exe query` state plus
    a firewall-rule-present probe per declared `listens` port and a
    named-pipe existence probe per declared `pipe`."""
    if not entry.manifest.is_service:
        return ""
    name = _service_name(entry.node_id)
    lines = [
        f'$svc = sc.exe query "{name}" 2>&1\n'
        "if ($LASTEXITCODE -eq 0) {\n"
        "    $state = ($svc | Select-String 'STATE').ToString().Trim()\n"
        "} else {\n"
        "    $state = 'not_installed'\n"
        "}\n"
        f'Write-Output "service={name} node={entry.node_id} state=$state"\n'
    ]
    for port in entry.manifest.listens:
        rule_name = _firewall_rule_name(entry.node_id, port)
        lines.append(
            f'if (Get-NetFirewallRule -DisplayName "{rule_name}" '
            "-ErrorAction SilentlyContinue) {\n"
            f'    Write-Output "service={name} port={port}=open"\n'
            "} else {\n"
            f'    Write-Output "service={name} port={port}=closed"\n'
            "}\n"
        )
    for pipe in entry.manifest.pipes:
        lines.append(
            f'if (Test-Path "\\\\.\\pipe\\{pipe}") {{\n'
            f'    Write-Output "service={name} pipe={pipe}=present"\n'
            "} else {\n"
            f'    Write-Output "service={name} pipe={pipe}=absent"\n'
            "}\n"
        )
    return "".join(lines)


# frob:doc docs/modules/deploy.md#windows-generation
# frob:tests tests/unit/deploy/test_generate_windows.py::TestStatus.test_one_line kind="unit"  # noqa: E501
def generate_windows_status_script(model: KernelModel) -> str:
    """Render `status.ps1`: per `service`-marked windows node, SCM state
    plus a listen-port firewall probe and a named-pipe probe (module
    docstring)."""
    entries = windows_entries(sorted_manifest_entries(model))
    return _render_windows_status_script(model, entries)


def _render_windows_status_script(
    model: KernelModel, entries: tuple[ManifestEntry, ...]
) -> str:
    """`generate_windows_status_script`'s body, taking an already-computed
    windows-only `entries` walk."""
    parts = [_header(model, "frob deploy status.ps1")]
    service_entries = [e for e in entries if e.manifest.is_service]
    if not service_entries:
        parts.append('Write-Output "no windows services declared"\n')
        return "".join(parts)
    for entry in service_entries:
        parts.append(_status_service_block(entry))
    return "".join(parts)


# frob:doc docs/modules/deploy.md#windows-generation
# frob:tests tests/unit/deploy/test_generate_windows.py::TestUninstall.test_removes kind="unit"  # noqa: E501
def generate_windows_uninstall_script(model: KernelModel) -> str:
    """Render `uninstall.ps1`: services stopped+deleted, firewall rules
    removed, ACL grants removed, service accounts removed -- EXACTLY the
    manifest set, reverse order of install (module docstring's artifact-
    freeness requirement, same posture `uninstall.sh` documents)."""
    entries = windows_entries(sorted_manifest_entries(model))
    return _render_windows_uninstall_script(model, entries)


def _render_windows_uninstall_script(
    model: KernelModel, entries: tuple[ManifestEntry, ...]
) -> str:
    """`generate_windows_uninstall_script`'s body, taking an already-
    computed windows-only `entries` walk."""
    parts = [_header(model, "frob deploy uninstall.ps1")]
    if not entries:
        parts.append(
            'Write-Output "no windows host manifests declared, nothing to uninstall"\n'
        )
        return "".join(parts)
    for entry in entries:
        parts.append(f'Write-Output "--- {entry.node_id} ---"\n')
        parts.append(_uninstall_service_block(entry))
        parts.append(_uninstall_firewall_block(entry))
        for acl in entry.manifest.acl:
            parts.append(_uninstall_acl_block(acl))
    parts.append('Write-Output "--- service accounts ---"\n')
    for name, gmsa in _distinct_service_accounts(entries):
        parts.append(_uninstall_service_account_block(name, gmsa))
    parts.append('Write-Output "uninstall complete"\n')
    return "".join(parts)


__all__ = [
    "generate_windows_install_script",
    "generate_windows_status_script",
    "generate_windows_uninstall_script",
    "windows_entries",
]
