# Land profiles

<!-- frob:describes src/frob/doctor.py::profile_recommendation -->
<!-- frob:describes src/frob/app/doctor_runner.py::_print_profile_recommendation -->
<!-- frob:describes src/frob/app/scaffold_runner.py::_print_profile_recommendation -->

## Land profiles: rapid vs standard (T-4416)

`frob.toml`'s `[profile] profile = "..."` selects one of two live
profiles (`rapid` / `standard`; `fortress` is reserved with no
behavioral wiring yet -- see `frob.tickets._profile`'s module
docstring). T-1575 originally framed `rapid` as a small-repo ceremony
discount and `standard` as "today's unchanged behavior." T-4413's
scoped rapid-land check changed what `rapid` actually does on the land
path, and this section documents that CURRENT behavior -- the OLDER
`docs/modules/tickets-verify-sweep.md#development-profiles-frobtoml-profile-t-1575`
section still describes the pre-T-4413 mechanics
(evidence/mutation-check relaxation, the deferred-sweep/baseline-thread
skip, the ratchet) and is not restated here; this section is additive,
describing the land-time CHECK SCOPE each profile runs, which is
orthogonal to those older relaxations.

### rapid = scoped-synchronous

Since T-4413, a `rapid`-profile land runs its synchronous `frob check`
SCOPED, not skipped: `frob.app.ticket_runner._land_cmd`'s
`_rapid_check_scope_files` passes `frob check --files` the set of
diff-touched files plus their DIRECT dependents (one hop out through
the callgraph/import graph, not a transitive closure) -- not the whole
repo. This is the "scoped" half of "scoped-synchronous": the land's own
foreground check is bounded by what the land actually touched, which is
why its wall-clock time does not grow with total repo size the way an
unscoped check does.

The land is still SYNCHRONOUS on that scoped result: a scoped-check
failure still blocks the land exactly as a full check failure would --
`rapid` narrows WHAT is checked synchronously, never WHETHER the
synchronous result gates the land. What `rapid` defers is the REPO-WIDE
sweep: T-4414 batches the post-land unscoped sweep (previously a
per-land detached process, T-1684) so it runs on an accumulated backlog
of commits rather than once per land, and T-4415 declared CI the
authoritative source for the full-repo unscoped result -- a rapid land
never blocks on, or claims to have produced, a complete unscoped
verdict; CI's next run is what does.

### standard = unscoped-synchronous

`standard` runs the full, unscoped `frob check` synchronously on the
land path -- every file `frob.excludes.iter_files` would enumerate under
the repo root, not just the diff and its dependents. This is
"unscoped-synchronous": no scoping narrows what the synchronous check
covers, so its result is a complete verdict on its own, but its
wall-clock cost scales with total repo size (see "Measured cost" below).
This remains the default whenever `[profile]` or `frob.toml` itself is
absent, matching `frob.tickets._profile.configured_profile`'s documented
fail-to-`standard` posture -- upgrading `frob` never silently relaxes an
existing repo.

### Measured cost and the doctor/scaffold recommendation (T-4416)

An unscoped `standard` check measures 25-45 minutes on this repo's own
scale (~4200 tickets, ~1400 tracked source files); T-4408's land (a
comparable scale) measured 50+ minutes single-threaded. `rapid`'s
scoped-synchronous check does not carry that cost, because it is bounded
by the diff, not the repo.

`frob.doctor.profile_recommendation(root)` measures `root` against
`frob.doctor._PROFILE_RECOMMEND_THRESHOLD` (ticket count and file count,
either axis tripping is enough) and returns a human-readable
recommendation string once EITHER axis is exceeded, citing these same
measured numbers -- `None` below threshold. This is ADVISORY ONLY: it
never writes `frob.toml`, never fails a check, and never affects `frob
doctor`'s `healthy` verdict (`DoctorReport.profile_recommendation`).
Below threshold it recommends nothing at all, leaving `standard` as a
reasonable default for a small project -- the recommendation exists to
be told about the cost once it is real, not to nudge every repo toward
`rapid` on principle.

Two surfaces read it:

- `frob doctor` (`frob.app.doctor_runner._print_profile_recommendation`)
  prints it whenever present, on both the healthy and unhealthy report
  paths (orthogonal to overall health, unlike the self-healing/
  already-covered findings gated on `report.healthy` above it).
- `frob scaffold new` (`frob.app.scaffold_runner._print_profile_
  recommendation`), after writing a freshly scaffolded project's
  `frob.toml`, measures the new project directory the same way and
  prints the recommendation if already tripped -- in practice a brand
  new scaffold is essentially always under threshold, so this covers the
  rarer case of scaffolding into an already-large existing tree.

`_PROFILE_RECOMMEND_THRESHOLD` (ticket_count=4200, file_count=1400) is
DELIBERATELY DISTINCT from `frob.tickets._profile`'s own
`_THRESHOLD_FILE_COUNT`/`_THRESHOLD_TICKET_COUNT` (300/200): that older
pair drives a one-way ratchet AWAY from `rapid` under `rapid`'s
pre-T-4413 meaning (ceremony-light, riskier at scale); this pair drives
an advisory recommendation TOWARD `rapid` under its post-T-4413 meaning
(scoped-synchronous, the profile that scales). Reconciling the two
numeric axes into one coherent threshold is out of this ticket's scope
-- see this ticket's Done report for the filed follow-up.
