## Done report

Bound src/frob/registry (T-0407 unified registry package: RegistryEntry/
RegistryFile/RegistryAudit models, load_registry_dir/audit_registry_file/
append_entry loaders, consumed by frob.gates._registry_exhaustiveness) into
a new node, registry_model, in design/frob.strata. Distinguished by name
from the pre-existing registry node (the foreign-trust boundary for
third-party package registries, src/frob/vet/_registry.py) to avoid
conflating an internal, trusted model/loader package with the untrusted
network boundary that shares the English word "registry".

may set measured by direct grep of src/frob/registry/**: fs/fs-read (every
module's Path.read_text of the tracked docs/design/registry/*.yaml
manifests) -- no fs-write declared (SYS101 fired when it was: this
scanner's _KIND_MAP normalizes the write-shaped sink to plain fs, matching
every other node/store in this model, none of which declares fs-write on
its own). No eval/exec/net/sql/fetch_url/ffi call exists anywhere under
this package.

Two flows added: f_cli_registry_model (cli -> registry_model, via
src/frob/app/registry_runner.py's direct import) and
f_gates_registry_model (gates -> registry_model, via
src/frob/gates/_registry_exhaustiveness.py's direct import of
frob.registry._models / frob.registry._staleness).

tests/unit/strata/test_selfconform.py::TestRealGateGreen was RED before
this change with 2 SYS102 violations (unmodeled code src/frob/fleet,
src/frob/registry). Binding registry_model alone brought it down to 1
violation (fleet). fleet (src/frob/fleet/**, fleet.toml) is a separate
package that landed on main concurrently with this ticket's dispatch
(T-0578/T-0568/T-0569 at 0.73.0) and was never modeled -- discovered only
while verifying TestRealGateGreen for T-0707, not called out in this
ticket's original body. Since the required edit lay entirely inside this
ticket's own declared design/** scope, and the gate this ticket exists to
turn green could not pass while fleet stayed unmodeled, it was folded in
DIRECTLY here rather than filed as a separate ticket: added a `fleet`
node (code "src/frob/fleet/**", may "exec"/"fs" -- subprocess.run of
fixed argv for git-status/frob-check probes, tomllib.load of the tracked
fleet.toml; no eval/net/sql/fetch_url/ffi anywhere in the package) plus
f_cli_fleet (cli -> fleet, via src/frob/app/fleet_runner.py's import),
f_fleet_tickets (fleet -> tickets_ledger, via frob.fleet.route_ticket's
frob.tickets import), and f_fleet_core (fleet -> core, via
frob.logging.get_logger). No separate ticket was ever filed or dropped
for this -- it is disclosed here as scope this Done report covers, not as
a distinct piece of tracked work.

tests/unit/strata/test_selfconform.py::TestRealGateGreen now PASSES: 0
SYS100/SYS101/SYS102 violations (measured: `selfconform: 1 violation(s)`
before the fs-read/fs-write precision fix on both new nodes, `0
violation(s)` after -- SYS101 fired twice during iteration or fs-write
declared-but-never-observed on registry_model, fs-read declared-but-
never-observed on fleet: this scanner's fs-read/fs-write needles are
narrower than the plain `fs` kind every other node here already uses,
fixed by declaring only `may "fs"`/`may "fs-read"` where genuinely
observed, matching the rest of the model's precision convention).

tests/unit/strata/test_threat.py: full pass, no regression from the two
new nodes/five new flows (verified: no fresh THREAT003 obligation dragged
in -- neither node declares eval/exec-joined-to-a-weakness/net/sql/
fetch_url/deserialize beyond fleet's own "exec", which is a fixed,
non-registry-derived argv, same discharge shape core/vet/tickets_ledger
already carry, so no new assume/assert claim was needed since fleet has
no measured flow FROM the foreign registry node at all).

frob check --ticket T-0707: gate:SYS clean (no more registry SYS102/SYS101
finding); only remaining FAIL is gate:REL (REL001, public API changed
since 0.88.0 -- pre-existing from the concurrent main merge that landed
the fleet/testing/deploy features this session, unrelated to and not
caused by this ticket's design/frob.strata-only change; pyproject.toml is
outside T-0707's declared scope, so not bumped here).

### Changed
```
 design/frob.strata | 105 ++++++++
 tickets.md         | 686 +++++++++++++++++++++++++++++++++++++++++++++++++++--
 2 files changed, 774 insertions(+), 17 deletions(-)
```

### Evidence
(no evidence recorded)
