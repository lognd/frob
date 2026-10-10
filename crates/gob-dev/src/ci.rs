//! `cargo dev ci`: run locally exactly the checks `.github/workflows/ci.yml` runs.
//!
//! [`steps`] is the single definition of every CI check (name, argv, environment, platform).
//! `ci.yml` invokes `cargo dev ci --step <name>` for each check and holds no argv of its own;
//! `tests/ci_parity.rs` fails when the workflow and this list disagree, so a check added to one
//! cannot be missing from the other. Process spawning goes through `gob-exec` (PROC001).
//! The `clippy-windows` step is part of the default list and offloadable, so the one documented
//! whole-workspace command (`cargo dev ci`, through goway) catches Windows-only compile breaks.
//! Design: `docs/design/build-test-ci.md`.
// frob:ticket 01M41T8KP0769YYXP8CAHBKXAZ
// frob:ticket 01M41XFSAMMQXYZEKVY0G8QF7V
// frob:ticket 01M41ZSW6DZMBE5QWNGB6VY10G
// frob:ticket 01M42A37XTPF2H1WXQQZWEYXGZ
// frob:ticket 01M43FB0TFBNDFH1AEC1CTNHZG
// frob:ticket 01M44M58PKEM2HMKZF2CANFHAW
// frob:ticket 01M47QV17V1KZ6K50C7H77MRSP
// frob:ticket 01M47QVDTG48F4426J019X37CZ
// frob:ticket 01M47Y1QAY9FZYADME4RRKWM9R

use std::path::Path;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde::Deserialize;

/// Rust target whose clippy run catches Windows-only breakage from a Linux host.
pub const WINDOWS_TARGET: &str = "x86_64-pc-windows-gnu";

/// Pinned pytest requirement the `pytest` step installs with `uv tool install`, so the
/// pytest-backed tests never skip.
pub const PYTEST_REQUIREMENT: &str = "pytest==8.4.2";
/// Environment variable that turns a missing python or pytest from a named skip into a failure.
pub const REQUIRE_PYTHON_TESTS_ENV: &str = "FROB_REQUIRE_PYTHON_TESTS";

/// Wall-clock limit for one step (a cold nextest run is the longest).
const STEP_TIMEOUT: Duration = Duration::from_mins(60);
/// Wall-clock limit for the installed-target query.
const QUERY_TIMEOUT: Duration = Duration::from_mins(2);

/// One CI check, defined once for both `cargo dev ci` and `ci.yml`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Step {
    /// Name used by `--step` and by `ci.yml`.
    pub name: &'static str,
    /// Program to run.
    pub program: Program,
    /// Arguments, exactly as CI passes them.
    pub args: Vec<String>,
    /// Environment additions, exactly as CI sets them.
    pub env: Vec<(String, String)>,
    /// Only the Linux CI job runs it; other hosts report it as skipped.
    pub linux_only: bool,
    /// Prerequisites checked before the step runs; `ci.yml` must install each (parity test).
    pub needs: Vec<Prerequisite>,
    /// Heavy enough to run on a goway host under `--remote`; others always run locally.
    pub offload: bool,
    /// Run with uv's tool bin dir on `PATH`, so pytest installed by the `pytest` step is found.
    pub uv_tools_on_path: bool,
}

/// Something a step needs on the host, checked before it runs and installed by `ci.yml`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Prerequisite {
    /// A rustup target for the active toolchain.
    RustTarget(&'static str),
    /// An executable on `PATH`, with the command that installs it.
    SystemTool {
        /// Executable name looked up on `PATH`.
        tool: &'static str,
        /// Exact install command (Debian/Ubuntu), printed on failure and required in `ci.yml`.
        install: &'static str,
    },
}

impl Prerequisite {
    /// The command that satisfies this prerequisite; `ci.yml` must contain it verbatim.
    #[must_use]
    pub fn install_command(&self) -> String {
        match self {
            Self::RustTarget(t) => format!("rustup target add {t}"),
            Self::SystemTool { install, .. } => (*install).to_owned(),
        }
    }
}

/// MinGW C compiler that `libsqlite3-sys` needs to build for [`WINDOWS_TARGET`] from Linux.
pub const MINGW_GCC: Prerequisite = Prerequisite::SystemTool {
    tool: "x86_64-w64-mingw32-gcc",
    install: "sudo apt-get install -y gcc-mingw-w64-x86-64",
};

/// Why the step list or a run could not proceed.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum CiError {
    /// `frob.toml` is unreadable or lacks a tool stage the CI steps derive their pins from.
    #[error("frob.toml: {0}")]
    Config(String),
    /// `--step` named a check that does not exist.
    #[error("unknown step {name:?}; known steps: {known}")]
    UnknownStep {
        /// Requested name.
        name: String,
        /// Comma-separated valid names.
        known: String,
    },
    /// A required Rust target is not installed.
    #[error("rust target {target} is not installed; run: rustup target add {target}")]
    TargetMissing {
        /// The missing target triple.
        target: String,
    },
    /// A required system tool is not on `PATH`.
    #[error("{tool} is not installed (needed by the {step} step); run: {install}")]
    ToolMissing {
        /// The missing executable.
        tool: String,
        /// Step that needs it.
        step: String,
        /// Command that installs it.
        install: String,
    },
    /// A process could not be run at all.
    #[error("{0}")]
    Spawn(String),
    /// The goway host lacks declared prerequisites: a host setup problem, not a code failure.
    #[error("host {host} lacks: {}", missing.join("; "))]
    HostPrerequisite {
        /// Pool host that was probed.
        host: String,
        /// Each missing item with the command that installs it.
        missing: Vec<String>,
    },
    /// goway itself failed (exit 125: no host, ssh, sync), not the step's command.
    #[error("goway failed: {0}")]
    Goway(String),
}

/// How one step ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StepStatus {
    /// Exited 0.
    Passed,
    /// Failed, with the reason.
    Failed(String),
    /// The goway host lacks a declared prerequisite (named in the reason); the code was not run.
    HostPrerequisite(String),
    /// goway failed before or around the step (exit 125); says nothing about the step itself.
    GowayFailed(String),
    /// Not run on this host, with the reason (never silent).
    Skipped(String),
}

/// A step and how it ended.
#[derive(Debug, Clone, PartialEq)]
pub struct StepResult {
    /// Step name.
    pub name: &'static str,
    /// Outcome.
    pub status: StepStatus,
    /// Wall-clock time spent.
    pub elapsed: Duration,
    /// Where the step ran when goway ran it; `None` for a local step.
    pub remote: Option<Remote>,
}

fn strings(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|s| (*s).to_owned()).collect()
}

fn cargo(name: &'static str, args: &[&str]) -> Step {
    Step {
        name,
        program: Program::Cargo,
        args: strings(args),
        env: Vec::new(),
        linux_only: false,
        needs: Vec::new(),
        offload: false,
        uv_tools_on_path: false,
    }
}

/// Mark `step` as runnable on a goway host under `--remote`.
fn offloaded(mut step: Step) -> Step {
    step.offload = true;
    step
}

/// The string array `key` of the `[[check.tool]]` named `tool` in `frob.toml`.
fn pinned_array(frob_toml: &toml::Table, tool: &str, key: &str) -> Result<Vec<String>, CiError> {
    let bad = |what: &str| CiError::Config(format!("tool {tool}: {what}"));
    let entry = frob_toml
        .get("check")
        .and_then(|c| c.get("tool"))
        .and_then(toml::Value::as_array)
        .and_then(|a| {
            a.iter()
                .filter_map(toml::Value::as_table)
                .find(|t| t.get("name").and_then(toml::Value::as_str) == Some(tool))
        })
        .ok_or_else(|| bad("no [[check.tool]] entry"))?;
    entry
        .get(key)
        .and_then(toml::Value::as_array)
        .ok_or_else(|| bad(&format!("no {key}")))?
        .iter()
        .map(|v| {
            v.as_str()
                .map(str::to_owned)
                .ok_or_else(|| bad(&format!("non-string {key}")))
        })
        .collect()
}

/// `version_args` of the `[[check.tool]]` named `tool` in `frob.toml`: the pinned uvx invocation.
fn pinned_uvx(frob_toml: &toml::Table, tool: &str) -> Result<Vec<String>, CiError> {
    pinned_array(frob_toml, tool, "version_args")
}

/// The `pytest` step: `uv tool install --force` [`PYTEST_REQUIREMENT`] (idempotent, replaces a
/// stray pytest; no pip, which hosts under PEP 668 refuse). Later steps see the executable
/// through [`Step::uv_tools_on_path`].
fn pytest_install() -> Step {
    Step {
        name: "pytest",
        program: Program::Tool {
            name: "uv".to_owned(),
        },
        args: strings(&["tool", "install", "--force", PYTEST_REQUIREMENT]),
        env: Vec::new(),
        linux_only: false,
        needs: Vec::new(),
        offload: false,
        uv_tools_on_path: false,
    }
}

/// Workspace packages whose binaries `frob check` runs as siblings (D87): frob itself plus the
/// goblins it discovers next to its own executable.
pub const SIBLING_PACKAGES: [&str; 3] = ["frob-cli", "grimble", "crunk"];

/// The `check` step: build this workspace's own sibling binaries, then run `frob check` from the
/// same target dir so sibling discovery (next to the frob executable, D87) finds them and never
/// falls back to whatever is on `PATH`. One shell command so a goway host builds and runs on the
/// same machine; the step is Linux-only, so `sh` is always there.
/// frob:ticket 01M4527J4M910ZZBJZXMDZJQZQ
fn sibling_check() -> Step {
    let build: Vec<String> = SIBLING_PACKAGES.iter().map(|p| format!("-p {p}")).collect();
    let script = format!(
        "cargo build {} && exec cargo run -p frob-cli -- check",
        build.join(" ")
    );
    Step {
        program: Program::Tool {
            name: "sh".to_owned(),
        },
        args: vec!["-c".to_owned(), script],
        ..cargo("check", &[])
    }
}

/// Pinned `cargo-insta` version the `snapshots` step needs; `ci.yml` installs exactly this.
pub const CARGO_INSTA_VERSION: &str = "1.48.0";

/// `cargo-insta` on `PATH`, installed by `ci.yml` at [`CARGO_INSTA_VERSION`].
pub const CARGO_INSTA: Prerequisite = Prerequisite::SystemTool {
    tool: "cargo-insta",
    install: "cargo install --locked cargo-insta --version 1.48.0",
};

/// Shell fragment that fails (naming each file) when a `.snap.new` or `.pending-snap` file is
/// left in the tree: an unreviewed snapshot change must never reach CI. `target/` is skipped.
pub const PENDING_SNAPSHOT_GUARD: &str = "pending=$(find . -path ./target -prune -o \\( -name '*.snap.new' -o -name '*.pending-snap' \\) -print); \
if [ -n \"$pending\" ]; then echo \"pending snapshots (review with cargo insta review):\"; echo \"$pending\"; exit 1; fi";

/// The `snapshots` step (build-test-ci.md section 6): a cheap check that no `.snap.new` or
/// `.pending-snap` file is left in the tree. The unreferenced-snapshot check runs inside the
/// `nextest` step (one suite run, like ruff). One shell command; the step is Linux-only.
/// frob:ticket 01M47QV17V1KZ6K50C7H77MRSP
fn snapshots() -> Step {
    Step {
        program: Program::Tool {
            name: "sh".to_owned(),
        },
        args: vec!["-c".to_owned(), PENDING_SNAPSHOT_GUARD.to_owned()],
        linux_only: true,
        ..cargo("snapshots", &[])
    }
}

/// The `nextest` step: the single suite run, driven through cargo-insta.
fn nextest_step(require_python: bool) -> Step {
    // frob:ticket 01M47QV17V1KZ6K50C7H77MRSP
    // The one suite run goes through cargo-insta, which drives nextest with the `ci` profile
    // (junit included), fails on pending (`--check`) and unreferenced snapshots, and skips the
    // doctest pass `cargo nextest run` never made.
    let mut nextest = offloaded(cargo(
        "nextest",
        &[
            "insta",
            "test",
            "--check",
            "--unreferenced",
            "reject",
            "--workspace",
            "--test-runner",
            "nextest",
            "--nextest-profile",
            "ci",
            "--disable-nextest-doctest",
        ],
    ));
    nextest.needs = vec![CARGO_INSTA];
    nextest.uv_tools_on_path = true;
    nextest.env = vec![("INSTA_UPDATE".to_owned(), "no".to_owned())];
    if require_python {
        tracing::info!("nextest requires python and pytest (no skips)");
        nextest
            .env
            .push((REQUIRE_PYTHON_TESTS_ENV.to_owned(), "1".to_owned()));
    }
    nextest
}

/// A Linux-only hygiene step running the binary `tool` with the `args` of its `[[check.tool]]`
/// entry in `frob.toml` (the single pinned definition `frob check` also runs), needing `need` installed.
/// frob:ticket 01M47QVDTG48F4426J019X37CZ
fn hygiene(
    name: &'static str,
    need: Prerequisite,
    frob_toml: &toml::Table,
    tool: &str,
) -> Result<Step, CiError> {
    Ok(Step {
        program: Program::Tool {
            name: tool.to_owned(),
        },
        args: pinned_array(frob_toml, tool, "args")?,
        needs: vec![need],
        linux_only: true,
        ..cargo(name, &[])
    })
}

/// Pinned `cargo-deny` version; `frob.toml` carries the accepted range (checked by a test).
pub const CARGO_DENY_VERSION: &str = "0.19.9";
/// Pinned `cargo-shear` version; `frob.toml` carries the accepted range (checked by a test).
pub const CARGO_SHEAR_VERSION: &str = "1.14.0";
/// Pinned `typos-cli` version; `frob.toml` carries the accepted range (checked by a test).
pub const TYPOS_VERSION: &str = "1.50.3";

/// `cargo-deny` on `PATH`, installed by `ci.yml` at [`CARGO_DENY_VERSION`].
pub const CARGO_DENY: Prerequisite = Prerequisite::SystemTool {
    tool: "cargo-deny",
    install: "cargo install --locked cargo-deny --version 0.19.9",
};
/// `cargo-shear` on `PATH`, installed by `ci.yml` at [`CARGO_SHEAR_VERSION`].
pub const CARGO_SHEAR: Prerequisite = Prerequisite::SystemTool {
    tool: "cargo-shear",
    install: "cargo install --locked cargo-shear --version 1.14.0",
};
/// `typos` on `PATH`, installed by `ci.yml` at [`TYPOS_VERSION`].
pub const TYPOS: Prerequisite = Prerequisite::SystemTool {
    tool: "typos",
    install: "cargo install --locked typos-cli --version 1.50.3",
};

/// True when `rust-version` names the pinned toolchain's own minor series (`1.98` vs `1.98.0`),
/// so an `msrv` check would build the workspace with the compiler clippy already used.
fn msrv_is_the_toolchain(rust_version: &str, channel: &str) -> bool {
    channel == rust_version || channel.starts_with(&format!("{rust_version}."))
}

/// The `msrv` step: install the toolchain named by `[workspace.package] rust-version` (minimal
/// profile) and `cargo check` the whole workspace with it, so code never needs a newer compiler
/// than the manifest promises. One shell command; the step is Linux-only. `None` while
/// `rust-version` is the pinned toolchain's own series: the check would repeat clippy's compile
/// with the same compiler (audit M18), and it returns the moment `rust-version` drops below it.
/// frob:ticket 01M47QVDTG48F4426J019X37CZ
/// frob:ticket 01M4CTE2T943ATA1PKVBN7DCP3
fn msrv(root: &Path) -> Result<Option<Step>, CiError> {
    let read = |file: &str| -> Result<toml::Table, CiError> {
        let text = std::fs::read_to_string(root.join(file)).map_err(|e| {
            tracing::error!(file, error = %e, "unreadable");
            CiError::Config(e.to_string())
        })?;
        text.parse().map_err(|e: toml::de::Error| {
            tracing::error!(file, error = %e, "unparsable");
            CiError::Config(e.to_string())
        })
    };
    let manifest = read("Cargo.toml")?;
    let rv = manifest
        .get("workspace")
        .and_then(|w| w.get("package"))
        .and_then(|p| p.get("rust-version"))
        .and_then(toml::Value::as_str)
        .ok_or_else(|| CiError::Config("Cargo.toml: no [workspace.package] rust-version".into()))?;
    let toolchain = read("rust-toolchain.toml")?;
    let channel = toolchain
        .get("toolchain")
        .and_then(|w| w.get("channel"))
        .and_then(toml::Value::as_str)
        .ok_or_else(|| CiError::Config("rust-toolchain.toml: no [toolchain] channel".into()))?;
    if msrv_is_the_toolchain(rv, channel) {
        tracing::info!(
            rust_version = rv,
            channel,
            "msrv step dropped: same compiler as the pinned toolchain"
        );
        return Ok(None);
    }
    tracing::info!(rust_version = rv, channel, "msrv step toolchain");
    let script = format!(
        "rustup toolchain install {rv} --profile minimal && \
         exec cargo +{rv} check --workspace --all-targets --all-features"
    );
    Ok(Some(Step {
        program: Program::Tool {
            name: "sh".to_owned(),
        },
        args: vec!["-c".to_owned(), script],
        linux_only: true,
        ..cargo("msrv", &[])
    }))
}

/// Every CI check in the order `ci.yml` runs it; zizmor and actionlint pins come from `frob.toml`.
///
/// # Errors
/// [`CiError::Config`] when `frob.toml` cannot supply the pinned tool versions.
pub fn steps(root: &Path) -> Result<Vec<Step>, CiError> {
    // GitHub (and most CI systems) set `CI`; only there is a missing pytest a failure, so a
    // developer machine without pytest still runs `cargo dev ci` with the named skips.
    // frob:ticket 01M44J072TEWFTCB1AFVTN9C8B
    let require_python = std::env::var_os("CI").is_some();
    steps_with(root, require_python)
}

/// [`steps`] with the python requirement explicit (tests pass it without touching the process
/// environment).
///
/// # Errors
/// [`CiError::Config`] when `frob.toml` cannot supply the pinned tool versions.
pub fn steps_with(root: &Path, require_python: bool) -> Result<Vec<Step>, CiError> {
    let text = std::fs::read_to_string(root.join("frob.toml")).map_err(|e| {
        tracing::error!(error = %e, "frob.toml unreadable");
        CiError::Config(e.to_string())
    })?;
    let frob_toml: toml::Table = text.parse().map_err(|e: toml::de::Error| {
        tracing::error!(error = %e, "frob.toml unparsable");
        CiError::Config(e.to_string())
    })?;
    let uvx = |name: &'static str, tool: &str| -> Result<Step, CiError> {
        Ok(Step {
            name,
            program: Program::Tool {
                name: "uvx".to_owned(),
            },
            args: pinned_uvx(&frob_toml, tool)?,
            env: Vec::new(),
            linux_only: true,
            needs: Vec::new(),
            offload: false,
            uv_tools_on_path: false,
        })
    };
    let linux = |mut s: Step| {
        s.linux_only = true;
        s
    };
    let mut clippy_windows = cargo(
        "clippy-windows",
        &[
            "clippy",
            "--all-targets",
            "--all-features",
            "--target",
            WINDOWS_TARGET,
            "--",
            "-D",
            "warnings",
        ],
    );
    clippy_windows.linux_only = true;
    clippy_windows.offload = true;
    clippy_windows.needs = vec![Prerequisite::RustTarget(WINDOWS_TARGET), MINGW_GCC];
    let mut docs = cargo("docs", &["doc", "--no-deps", "--all-features"]);
    docs.env = vec![("RUSTDOCFLAGS".to_owned(), "-D warnings".to_owned())];
    docs.offload = true;
    let nextest = nextest_step(require_python);
    let mut all = vec![
        cargo("fmt", &["fmt", "--all", "--check"]),
        offloaded(cargo(
            "clippy",
            &[
                "clippy",
                "--all-targets",
                "--all-features",
                "--",
                "-D",
                "warnings",
            ],
        )),
        clippy_windows,
        docs,
        pytest_install(),
        snapshots(),
        nextest,
        cargo("gen", &["dev", "gen", "all", "--check"]),
        uvx("zizmor", "zizmor")?,
        uvx("actionlint", "actionlint")?,
        hygiene("deny", CARGO_DENY, &frob_toml, "cargo-deny")?,
        hygiene("shear", CARGO_SHEAR, &frob_toml, "cargo-shear")?,
        hygiene("typos", TYPOS, &frob_toml, "typos")?,
        offloaded(linux(cargo(
            "doctor",
            &["run", "-p", "frob-cli", "--", "doctor"],
        ))),
        offloaded(linux(sibling_check())),
        linux(cargo(
            "test-dry-run",
            &[
                "run",
                "-p",
                "frob-cli",
                "--",
                "test",
                "--base",
                "origin/experimental",
                "--dry-run",
            ],
        )),
    ];
    // msrv sits between the hygiene tools and doctor, where ci.yml lists it.
    if let Some(m) = msrv(root)? {
        let at = all
            .iter()
            .position(|s| s.name == "doctor")
            .unwrap_or(all.len());
        all.insert(at, m);
    }
    Ok(all)
}

/// Executes one step; a trait so tests drive the flow without spawning anything.
pub trait StepRunner {
    /// Run `step` in `root`; `Ok` when it exits 0, carrying where it ran if a goway host ran it.
    ///
    /// # Errors
    /// [`CiError::TargetMissing`] or [`CiError::ToolMissing`] when a prerequisite is absent,
    /// [`CiError::Goway`] when goway itself failed, [`CiError::Spawn`] on any other failure to
    /// run or a non-zero exit.
    fn run(&self, root: &Path, step: &Step) -> Result<Option<Remote>, CiError>;
}

/// The real [`StepRunner`], spawning through `gob-exec`.
#[derive(Debug, Default)]
pub struct ExecRunner;

fn runner() -> Runner {
    Runner::new(Limits { jobs: 1 })
}

/// `PATH` with uv's tool bin dir (`uv tool dir --bin`) in front, or `None` when uv cannot say.
fn path_with_uv_tools(root: &Path) -> Option<String> {
    let query = Spec {
        program: Program::Tool {
            name: "uv".to_owned(),
        },
        args: strings(&["tool", "dir", "--bin"]),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: QUERY_TIMEOUT,
        capture: true,
    };
    let out = match runner().run(&query) {
        Ok(out) if out.status == Outcome::Exited(0) => out,
        other => {
            tracing::warn!(?other, "uv tool dir --bin failed; PATH left unchanged");
            return None;
        }
    };
    let bin = std::path::PathBuf::from(out.stdout.trim());
    let rest = std::env::var_os("PATH").unwrap_or_default();
    let joined =
        std::env::join_paths(std::iter::once(bin.clone()).chain(std::env::split_paths(&rest)));
    tracing::info!(bin = %bin.display(), "uv tool bin dir put on PATH for the step");
    joined.ok()?.into_string().ok()
}

fn spec(root: &Path, step: &Step, timeout: Duration, capture: bool) -> Spec {
    let mut env = step.env.clone();
    if step.uv_tools_on_path
        && let Some(path) = path_with_uv_tools(root)
    {
        env.push(("PATH".to_owned(), path));
    }
    Spec {
        program: step.program.clone(),
        args: step.args.clone(),
        cwd: Some(root.to_path_buf()),
        env,
        timeout,
        capture,
    }
}

/// Fail with the exact `rustup` command when `target` is not installed for the active toolchain.
fn require_target(root: &Path, target: &str) -> Result<(), CiError> {
    let query = Spec {
        program: Program::Tool {
            name: "rustup".to_owned(),
        },
        args: strings(&["target", "list", "--installed"]),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: QUERY_TIMEOUT,
        capture: true,
    };
    let out = runner()
        .run(&query)
        .map_err(|e| CiError::Spawn(format!("rustup target list: {e}")))?;
    if out.status == Outcome::Exited(0) && out.stdout.lines().any(|l| l.trim() == target) {
        Ok(())
    } else {
        tracing::error!(target, "required rust target missing");
        Err(CiError::TargetMissing {
            target: target.to_owned(),
        })
    }
}

/// Fail with the install command when `tool` is not an executable file on `PATH`.
fn require_tool(step: &str, tool: &str, install: &str) -> Result<(), CiError> {
    let found = std::env::var_os("PATH").is_some_and(|path| {
        std::env::split_paths(&path).any(|dir| {
            dir.join(tool).is_file()
                || dir
                    .join(format!("{tool}{}", std::env::consts::EXE_SUFFIX))
                    .is_file()
        })
    });
    if found {
        Ok(())
    } else {
        tracing::error!(tool, step, "required system tool missing");
        Err(CiError::ToolMissing {
            tool: tool.to_owned(),
            step: step.to_owned(),
            install: install.to_owned(),
        })
    }
}

/// Check every prerequisite of `step`, stopping at the first missing one.
fn require_all(root: &Path, step: &Step) -> Result<(), CiError> {
    for need in &step.needs {
        match need {
            Prerequisite::RustTarget(t) => require_target(root, t)?,
            Prerequisite::SystemTool { tool, install } => require_tool(step.name, tool, install)?,
        }
    }
    Ok(())
}

/// Environment variable that opts `cargo dev ci` into running offloadable steps through goway;
/// its value is the goway binary (a bare name or a path). A `--remote` flag will set the same.
pub const REMOTE_ENV: &str = "CARGO_DEV_CI_REMOTE";

/// Run `step` on this host, checking its prerequisites locally first.
fn run_local(root: &Path, step: &Step) -> Result<Option<Remote>, CiError> {
    require_all(root, step)?;
    let out = runner()
        .run(&spec(root, step, STEP_TIMEOUT, false))
        .map_err(|e| CiError::Spawn(format!("{}: {e}", step.name)))?;
    match out.status {
        Outcome::Exited(0) => Ok(None),
        other => Err(CiError::Spawn(format!("ended {other:?}"))),
    }
}

impl StepRunner for ExecRunner {
    fn run(&self, root: &Path, step: &Step) -> Result<Option<Remote>, CiError> {
        match std::env::var(REMOTE_ENV) {
            Ok(bin) if !bin.is_empty() => {
                tracing::info!(goway = %bin, step = step.name, "remote runner selected by env");
                GowayRunner::new(&bin, RemoteOs::default()).run(root, step)
            }
            _ => run_local(root, step),
        }
    }
}

/// Operating system of a goway host. Only Linux is built; Windows (`--remote-os windows`,
/// `goway run --host <windows host>`) adds a variant and its arms here, nowhere else.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum RemoteOs {
    /// A Linux helper.
    #[default]
    Linux,
}

impl RemoteOs {
    /// The `goway run --needs` term that restricts the pool to this OS.
    #[must_use]
    pub fn needs_term(self) -> &'static str {
        match self {
            Self::Linux => "os=linux",
        }
    }

    /// The remote command that lists installed rustup targets, one per line.
    fn target_list(self) -> Vec<String> {
        match self {
            Self::Linux => strings(&["rustup", "target", "list", "--installed"]),
        }
    }

    /// The remote command that exits 0 when `tool` is on the host's `PATH`.
    fn tool_probe(self, tool: &str) -> Vec<String> {
        match self {
            Self::Linux => vec!["which".to_owned(), tool.to_owned()],
        }
    }
}

/// Hardware every offloaded step needs from its host (`goway run --needs`).
pub const REMOTE_NEEDS: [&str; 2] = ["cores>=8", "mem>=2G"];
/// goway's own failure exit code (also "no host"), as opposed to the remote command's.
pub const GOWAY_FAILURE: i32 = 125;
/// How many times a goway failure is retried before it is reported.
const GOWAY_RETRIES: u32 = 5;
/// First wait after a goway failure; doubles each retry up to [`GOWAY_BACKOFF_CAP`].
const GOWAY_BACKOFF: Duration = Duration::from_secs(15);
/// Longest wait between goway retries.
const GOWAY_BACKOFF_CAP: Duration = Duration::from_secs(120);
/// Where the goway run report lands, relative to the workspace root (`target/` is untracked).
const REPORT_PATH: &str = "target/goway-ci-report.json";

/// Where a goway-run step ran, from `goway run --report`.
#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Remote {
    /// Pool host name.
    pub host: String,
    /// Host operating system.
    pub os: String,
    /// Host CPU architecture.
    pub arch: String,
    /// The remote command's exit code.
    pub exit_code: i32,
    /// Remote wall time in seconds.
    pub duration_secs: f64,
}

/// A [`StepRunner`] that sends offloadable steps through `goway run` and runs the rest locally.
///
/// The remote command is the step's own program, args and env (`-e K=V`), so [`steps`] stays the
/// single source. goway ships the work tree with a minimal `.git` (`--with-git`), so the steps
/// that ask git about the repository run remotely too.
#[derive(Debug)]
pub struct GowayRunner {
    goway: Program,
    os: RemoteOs,
    retries: u32,
    backoff: Duration,
}

impl GowayRunner {
    /// Use the goway at `binary`: a bare name looked up on `PATH`, or a path to the executable.
    #[must_use]
    pub fn new(binary: &str, os: RemoteOs) -> Self {
        let goway = if binary.contains(['/', '\\']) {
            Program::Hook {
                path: binary.into(),
            }
        } else {
            Program::Tool {
                name: binary.to_owned(),
            }
        };
        Self::with_retry(goway, os, GOWAY_RETRIES, GOWAY_BACKOFF)
    }

    /// As [`Self::new`] with an explicit program and retry policy (tests use zero backoff).
    #[must_use]
    pub fn with_retry(goway: Program, os: RemoteOs, retries: u32, backoff: Duration) -> Self {
        Self {
            goway,
            os,
            retries,
            backoff,
        }
    }

    /// The `goway run` argv for `command`, pinned to `host` when given.
    fn argv(
        &self,
        root: &Path,
        host: Option<&str>,
        env: &[(String, String)],
        command: &[String],
    ) -> Vec<String> {
        let mut a = strings(&["run", "--with-git"]);
        for need in REMOTE_NEEDS.iter().copied().chain([self.os.needs_term()]) {
            a.extend(["--needs".to_owned(), need.to_owned()]);
        }
        a.extend([
            "--report".to_owned(),
            root.join(REPORT_PATH).display().to_string(),
        ]);
        if let Some(h) = host {
            a.extend(["--host".to_owned(), h.to_owned()]);
        }
        for (k, v) in env {
            a.extend(["-e".to_owned(), format!("{k}={v}")]);
        }
        a.push("--".to_owned());
        a.extend(command.iter().cloned());
        a
    }

    /// Run one goway command, retrying exit 125 with backoff; returns the outcome and report.
    fn invoke(
        &self,
        root: &Path,
        argv: &[String],
        capture: bool,
    ) -> Result<(Outcome, String, Option<Remote>), CiError> {
        let report = root.join(REPORT_PATH);
        let mut wait = self.backoff;
        for attempt in 0..=self.retries {
            // A stale report from an earlier run must never be taken for this one's.
            let _ = std::fs::remove_file(&report);
            if let Some(dir) = report.parent() {
                let _ = std::fs::create_dir_all(dir);
            }
            let out = runner()
                .run(&Spec {
                    program: self.goway.clone(),
                    args: argv.to_vec(),
                    cwd: Some(root.to_path_buf()),
                    env: Vec::new(),
                    timeout: STEP_TIMEOUT,
                    capture,
                })
                .map_err(|e| CiError::Goway(format!("cannot run goway: {e}")))?;
            if out.status != Outcome::Exited(GOWAY_FAILURE) {
                let remote = std::fs::read_to_string(&report)
                    .ok()
                    .and_then(|t| serde_json::from_str::<Remote>(&t).ok());
                if remote.is_none() {
                    tracing::warn!(report = %report.display(), "goway wrote no usable report");
                }
                return Ok((out.status, out.stdout, remote));
            }
            tracing::warn!(attempt, ?wait, "goway exit 125 (no host or goway failure)");
            if attempt < self.retries {
                std::thread::sleep(wait);
                wait = (wait * 2).min(GOWAY_BACKOFF_CAP);
            }
        }
        Err(CiError::Goway(format!(
            "exit {GOWAY_FAILURE} (no host, or goway itself failed) after {} attempts",
            self.retries + 1
        )))
    }

    /// Check `step`'s prerequisites on a goway host; returns that host so the step runs on it.
    fn require_remote(&self, root: &Path, step: &Step) -> Result<Option<String>, CiError> {
        let mut host: Option<String> = None;
        let mut missing = Vec::new();
        for need in &step.needs {
            let (command, probe) = match need {
                Prerequisite::RustTarget(_) => (self.os.target_list(), "rustup target list"),
                Prerequisite::SystemTool { tool, .. } => (self.os.tool_probe(tool), "which"),
            };
            let argv = self.argv(root, host.as_deref(), &[], &command);
            let (status, stdout, remote) = self.invoke(root, &argv, true)?;
            if host.is_none() {
                host = remote.map(|r| r.host);
            }
            let found = match need {
                Prerequisite::RustTarget(t) => {
                    status == Outcome::Exited(0) && stdout.lines().any(|l| l.trim() == *t)
                }
                Prerequisite::SystemTool { .. } => status == Outcome::Exited(0),
            };
            tracing::info!(step = step.name, probe, found, host = ?host, "remote prerequisite");
            if !found {
                missing.push(format!(
                    "{} (run: {})",
                    match need {
                        Prerequisite::RustTarget(t) => format!("rust target {t}"),
                        Prerequisite::SystemTool { tool, .. } => (*tool).to_owned(),
                    },
                    need.install_command()
                ));
            }
        }
        if !missing.is_empty() {
            tracing::error!(step = step.name, ?missing, "goway host lacks prerequisites");
            return Err(CiError::HostPrerequisite {
                host: host.unwrap_or_else(|| "unknown".to_owned()),
                missing,
            });
        }
        Ok(host)
    }
}

/// The program name as the remote shell sees it.
fn remote_program(program: &Program) -> String {
    match program {
        Program::Hook { path } => path.display().to_string(),
        other => other.label(),
    }
}

impl StepRunner for GowayRunner {
    fn run(&self, root: &Path, step: &Step) -> Result<Option<Remote>, CiError> {
        if !step.offload {
            return run_local(root, step);
        }
        let host = self.require_remote(root, step)?;
        let mut command = vec![remote_program(&step.program)];
        command.extend(step.args.iter().cloned());
        let argv = self.argv(root, host.as_deref(), &step.env, &command);
        let (status, _, remote) = self.invoke(root, &argv, false)?;
        let at = remote
            .as_ref()
            .map_or_else(String::new, |r| format!(" on {} ({})", r.host, r.arch));
        match status {
            Outcome::Exited(0) => Ok(remote),
            Outcome::Exited(code) => Err(CiError::Spawn(format!("exit {code}{at}"))),
            other => Err(CiError::Spawn(format!("ended {other:?}{at}"))),
        }
    }
}

/// Whether this host is the Linux CI job's platform.
#[must_use]
pub fn host_is_linux() -> bool {
    cfg!(target_os = "linux")
}

/// Where nextest's `ci` profile writes its junit report, relative to the workspace root.
pub const JUNIT_PATH: &str = "target/nextest/ci/junit.xml";

/// Value of the XML attribute `name` in `tag` (a `<testcase .../>` or `<testsuites ...>` element).
fn attr<'a>(tag: &'a str, name: &str) -> Option<&'a str> {
    let needle = format!(" {name}=\"");
    let start = tag.find(&needle)? + needle.len();
    let len = tag[start..].find('"')?;
    Some(&tag[start..start + len])
}

/// Suite wall time in seconds and every test (`classname name`, seconds), slowest first.
///
/// Reads the junit XML nextest writes; `None` when it has no suite time.
#[must_use]
pub fn junit_report(junit: &str) -> Option<(f64, Vec<(String, f64)>)> {
    let suite = attr(junit.lines().find(|l| l.contains("<testsuites"))?, "time")?
        .parse()
        .ok()?;
    let mut tests: Vec<(String, f64)> = junit
        .lines()
        .filter(|l| l.trim_start().starts_with("<testcase"))
        .filter_map(|l| {
            let secs = attr(l, "time")?.parse().ok()?;
            Some((
                format!("{} {}", attr(l, "classname")?, attr(l, "name")?),
                secs,
            ))
        })
        .collect();
    tests.sort_by(|a, b| b.1.total_cmp(&a.1));
    Some((suite, tests))
}

/// Soft budget: a test slower than this many seconds is reported (never failed) by `cargo dev ci`.
pub const SOFT_TEST_BUDGET_SECS: f64 = 30.0;
/// Soft budget: a nextest suite slower than this many seconds is reported (never failed).
pub const SOFT_SUITE_BUDGET_SECS: f64 = 90.0;

/// Warnings for the soft speed budget; empty when the suite and every test are within it.
///
/// Speed depends on the host, so these warn and never fail; the hang guard is nextest's
/// `terminate-after` (`.config/nextest.toml`).
#[must_use]
pub fn budget_warnings(suite: f64, tests: &[(String, f64)]) -> Vec<String> {
    let mut out = Vec::new();
    if suite > SOFT_SUITE_BUDGET_SECS {
        out.push(format!(
            "warning: nextest suite took {suite:.1}s, over the {SOFT_SUITE_BUDGET_SECS:.0}s soft budget"
        ));
    }
    out.extend(
        tests
            .iter()
            .filter(|(_, secs)| *secs > SOFT_TEST_BUDGET_SECS)
            .map(|(name, secs)| {
                format!(
                    "warning: {name} took {secs:.1}s, over the {SOFT_TEST_BUDGET_SECS:.0}s soft budget"
                )
            }),
    );
    out
}

/// Number of slowest tests `cargo dev ci` lists after the nextest step.
const SLOWEST: usize = 5;

/// Say the nextest suite wall time and the five slowest tests, from the junit report under `root`.
fn report_nextest(root: &Path, say: &mut dyn FnMut(&str)) {
    let path = root.join(JUNIT_PATH);
    let Ok(junit) = std::fs::read_to_string(&path) else {
        tracing::warn!(path = %path.display(), "no nextest junit report to summarise");
        return;
    };
    let Some((suite, slowest)) = junit_report(&junit) else {
        tracing::warn!(path = %path.display(), "nextest junit report is unparsable");
        return;
    };
    say(&format!(
        "   nextest suite wall time {suite:.1}s; slowest tests:"
    ));
    for (name, secs) in slowest.iter().take(SLOWEST) {
        say(&format!("   {secs:>8.1}s  {name}"));
    }
    for w in budget_warnings(suite, &slowest) {
        tracing::warn!("{w}");
        say(&format!("   {w}"));
    }
}

/// Run `selected` in order through `exec`, stopping at the first failure unless `keep_going`.
///
/// `linux` says whether linux-only steps run; they are reported as skipped otherwise. Steps
/// after a stop are not listed.
pub fn run(
    root: &Path,
    selected: &[Step],
    exec: &dyn StepRunner,
    keep_going: bool,
    linux: bool,
    say: &mut dyn FnMut(&str),
) -> Vec<StepResult> {
    let mut results = Vec::new();
    let total = selected.len();
    for (i, step) in selected.iter().enumerate() {
        let started = std::time::Instant::now();
        let mut remote = None;
        let status = if step.linux_only && !linux {
            tracing::warn!(step = step.name, "linux-only step skipped on this host");
            StepStatus::Skipped("linux-only step, this host is not Linux".to_owned())
        } else {
            say(&format!(
                "== [{}/{total}] {}: {} {}",
                i + 1,
                step.name,
                step.program.label(),
                step.args.join(" ")
            ));
            match exec.run(root, step) {
                Ok(at) => {
                    remote = at;
                    StepStatus::Passed
                }
                Err(e @ CiError::HostPrerequisite { .. }) => {
                    tracing::error!(step = step.name, error = %e, "host prerequisite missing");
                    StepStatus::HostPrerequisite(e.to_string())
                }
                Err(e @ CiError::Goway(_)) => {
                    tracing::error!(step = step.name, error = %e, "goway failed");
                    StepStatus::GowayFailed(e.to_string())
                }
                Err(e) => {
                    tracing::error!(step = step.name, error = %e, "ci step failed");
                    StepStatus::Failed(e.to_string())
                }
            }
        };
        let failed = matches!(
            status,
            StepStatus::Failed(_) | StepStatus::GowayFailed(_) | StepStatus::HostPrerequisite(_)
        );
        // The junit report stays on a remote host; reading the local copy would show a stale run.
        if step.name == "nextest" && status == StepStatus::Passed && remote.is_none() {
            report_nextest(root, say);
        }
        results.push(StepResult {
            name: step.name,
            status,
            elapsed: started.elapsed(),
            remote,
        });
        if failed && !keep_going {
            break;
        }
    }
    results
}

/// Select steps by `names` (all when empty), keeping the canonical order.
///
/// # Errors
/// [`CiError::UnknownStep`] when a name matches no step.
pub fn select(all: Vec<Step>, names: &[String]) -> Result<Vec<Step>, CiError> {
    if let Some(bad) = names
        .iter()
        .find(|n| !all.iter().any(|s| s.name == n.as_str()))
    {
        return Err(CiError::UnknownStep {
            name: bad.clone(),
            known: all.iter().map(|s| s.name).collect::<Vec<_>>().join(", "),
        });
    }
    Ok(all
        .into_iter()
        .filter(|s| names.is_empty() || names.iter().any(|n| n == s.name))
        .collect())
}

/// One summary line per result plus a verdict line; true when nothing failed.
#[must_use]
pub fn summary(results: &[StepResult]) -> (Vec<String>, bool) {
    let mut lines = Vec::new();
    for r in results {
        let (mark, note) = match &r.status {
            StepStatus::Passed => ("ok     ", String::new()),
            StepStatus::Failed(why) => ("FAILED ", format!("  {why}")),
            StepStatus::GowayFailed(why) => ("GOWAY  ", format!("  {why}")),
            StepStatus::HostPrerequisite(why) => ("HOSTREQ", format!("  {why}")),
            StepStatus::Skipped(why) => ("skipped", format!("  {why}")),
        };
        let at = r.remote.as_ref().map_or_else(String::new, |h| {
            format!("  on {} ({}/{})", h.host, h.os, h.arch)
        });
        lines.push(format!(
            "{mark} {:<15} {:>7.1}s{at}{note}",
            r.name,
            r.elapsed.as_secs_f64()
        ));
    }
    let ok = !results.iter().any(|r| {
        matches!(
            r.status,
            StepStatus::Failed(_) | StepStatus::GowayFailed(_) | StepStatus::HostPrerequisite(_)
        )
    });
    lines.push(if ok {
        "ci: all steps passed".to_owned()
    } else {
        "ci: FAILED".to_owned()
    });
    (lines, ok)
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;

    use super::*;

    struct Fake {
        fail: &'static str,
        seen: RefCell<Vec<&'static str>>,
    }

    impl StepRunner for Fake {
        fn run(&self, _: &Path, step: &Step) -> Result<Option<Remote>, CiError> {
            self.seen.borrow_mut().push(step.name);
            if step.name == self.fail {
                Err(CiError::Spawn("boom".to_owned()))
            } else {
                Ok(None)
            }
        }
    }

    fn real() -> Vec<Step> {
        let root = crate::find_workspace_root(&std::env::current_dir().unwrap()).unwrap();
        steps(&root).unwrap()
    }

    #[test]
    fn stops_at_first_failure_and_keep_going_continues() {
        let all = real();
        let n = all.len();
        let f = Fake {
            fail: "clippy",
            seen: RefCell::new(Vec::new()),
        };
        let r = run(Path::new("."), &all, &f, false, true, &mut |_| {});
        assert_eq!(r.last().unwrap().name, "clippy");
        assert!(!summary(&r).1);
        let f = Fake {
            fail: "clippy",
            seen: RefCell::new(Vec::new()),
        };
        let r = run(Path::new("."), &all, &f, true, true, &mut |_| {});
        assert_eq!(r.len(), n);
        assert_eq!(f.seen.borrow().len(), n);
    }

    // frob:tests crates/gob-dev/src/ci.rs::junit_report
    #[test]
    fn junit_report_gives_suite_time_and_slowest_tests_first() {
        let xml = concat!(
            "<testsuites name=\"nextest-run\" tests=\"3\" time=\"12.5\">\n",
            "  <testsuite name=\"a::b\">\n",
            "    <testcase name=\"fast\" classname=\"a::b\" time=\"0.1\"/>\n",
            "    <testcase name=\"slow\" classname=\"a::b\" time=\"9.0\"/>\n",
            "    <testcase name=\"mid\" classname=\"a::b\" time=\"3.0\"/>\n",
            "  </testsuite>\n</testsuites>\n"
        );
        let (suite, top) = junit_report(xml).unwrap();
        assert!((suite - 12.5).abs() < 1e-9);
        assert_eq!(top.len(), 3);
        assert_eq!(top[0].0, "a::b slow");
        assert_eq!(top[1].0, "a::b mid");
        assert!(junit_report("not xml").is_none());
    }

    // frob:tests crates/gob-dev/src/ci.rs::budget_warnings
    #[test]
    fn soft_budget_warns_on_slow_tests_and_a_slow_suite_only() {
        let tests = vec![("a slow".to_owned(), 31.0), ("b ok".to_owned(), 30.0)];
        assert!(budget_warnings(90.0, &tests[1..]).is_empty());
        let w = budget_warnings(91.0, &tests);
        assert_eq!(w.len(), 2, "{w:?}");
        assert!(w[0].contains("suite") && w[1].contains("a slow"));
    }

    #[test]
    fn nextest_ci_profile_is_a_hang_guard_not_a_speed_budget() {
        let root = crate::find_workspace_root(&std::env::current_dir().unwrap()).unwrap();
        let text = std::fs::read_to_string(root.join(".config/nextest.toml")).unwrap();
        let cfg: toml::Table = text.parse().unwrap();
        let ci = &cfg["profile"]["ci"];
        let slow = &ci["slow-timeout"];
        let period = slow["period"].as_str().unwrap();
        let after = slow["terminate-after"].as_integer().unwrap();
        assert_eq!(period, "30s");
        assert_eq!(
            after, 4,
            "terminate at 120 s: hangs fail, slow runners do not"
        );
    }

    #[test]
    fn linux_only_steps_are_reported_skipped_elsewhere() {
        let f = Fake {
            fail: "",
            seen: RefCell::new(Vec::new()),
        };
        let r = run(Path::new("."), &real(), &f, false, false, &mut |_| {});
        let skipped: Vec<_> = r
            .iter()
            .filter(|r| matches!(r.status, StepStatus::Skipped(_)))
            .collect();
        assert!(skipped.iter().any(|r| r.name == "clippy-windows"));
        assert!(!f.seen.borrow().contains(&"check"));
    }

    #[test]
    fn docs_step_sets_rustdocflags_and_nextest_uses_ci_profile() {
        let all = real();
        let docs = all.iter().find(|s| s.name == "docs").unwrap();
        assert_eq!(
            docs.env,
            vec![("RUSTDOCFLAGS".to_owned(), "-D warnings".to_owned())]
        );
        let nextest = all.iter().find(|s| s.name == "nextest").unwrap();
        assert!(
            nextest
                .args
                .windows(2)
                .any(|w| w == ["--nextest-profile", "ci"])
        );
    }

    // frob:tests crates/gob-dev/src/ci.rs::host_is_linux
    #[test]
    fn host_platform_matches_the_target_os() {
        assert_eq!(host_is_linux(), std::env::consts::OS == "linux");
    }

    #[test]
    fn unknown_step_names_the_valid_ones() {
        let e = select(real(), &["nope".to_owned()]).unwrap_err();
        assert!(e.to_string().contains("clippy-windows"));
    }

    #[test]
    fn missing_target_error_carries_the_rustup_command() {
        let e = CiError::TargetMissing {
            target: WINDOWS_TARGET.to_owned(),
        };
        assert!(
            e.to_string()
                .contains("rustup target add x86_64-pc-windows-gnu")
        );
    }

    // frob:tests crates/gob-dev/src/ci.rs::ExecRunner
    #[test]
    fn missing_system_tool_fails_before_running_and_names_the_install_command() {
        // Test hook: the prerequisite points at a name that cannot exist; the program is also
        // nonexistent, so a spawn attempt would produce a different error.
        let step = Step {
            name: "needs-ghost",
            program: Program::Tool {
                name: "no-such-program-0g8qf7v".to_owned(),
            },
            args: Vec::new(),
            env: Vec::new(),
            linux_only: false,
            needs: vec![Prerequisite::SystemTool {
                tool: "no-such-tool-0g8qf7v",
                install: "sudo apt-get install -y ghost-pkg",
            }],
            offload: false,
            uv_tools_on_path: false,
        };
        let e = ExecRunner.run(Path::new("."), &step).unwrap_err();
        assert!(matches!(e, CiError::ToolMissing { .. }), "{e}");
        let text = e.to_string();
        assert!(text.contains("no-such-tool-0g8qf7v"), "{text}");
        assert!(text.contains("sudo apt-get install -y ghost-pkg"), "{text}");
    }

    // frob:tests crates/gob-dev/src/ci.rs::PENDING_SNAPSHOT_GUARD
    #[test]
    fn stray_pending_snapshot_fails_the_guard_and_a_clean_tree_passes() {
        let dir = tempfile::tempdir().unwrap();
        let run = || {
            let spec = Spec {
                program: Program::Tool {
                    name: "sh".to_owned(),
                },
                args: vec!["-c".to_owned(), PENDING_SNAPSHOT_GUARD.to_owned()],
                cwd: Some(dir.path().to_path_buf()),
                env: Vec::new(),
                timeout: QUERY_TIMEOUT,
                capture: true,
            };
            runner().run(&spec).unwrap()
        };
        std::fs::write(dir.path().join("a.snap"), "ok").unwrap();
        assert_eq!(run().status, Outcome::Exited(0));
        std::fs::write(dir.path().join("a.snap.new"), "pending").unwrap();
        let out = run();
        assert_eq!(out.status, Outcome::Exited(1));
        assert!(out.stdout.contains("a.snap.new"), "{}", out.stdout);
    }

    // frob:tests crates/gob-dev/src/ci.rs::snapshots
    #[test]
    fn nextest_runs_the_suite_once_through_insta_rejecting_unreferenced_snapshots() {
        let all = real();
        let names: Vec<_> = all.iter().map(|s| s.name).collect();
        let at = |n: &str| names.iter().position(|x| *x == n).unwrap();
        assert!(at("snapshots") < at("nextest"));
        let s = &all[at("snapshots")];
        assert!(s.linux_only && s.args[1] == PENDING_SNAPSHOT_GUARD);
        let n = &all[at("nextest")];
        let joined = n.args.join(" ");
        assert!(
            joined.starts_with("insta test --check --unreferenced reject"),
            "{joined}"
        );
        assert_eq!(n.needs, vec![CARGO_INSTA]);
        assert!(CARGO_INSTA.install_command().contains(CARGO_INSTA_VERSION));
        let want = ("INSTA_UPDATE".to_owned(), "no".to_owned());
        assert!(n.env.contains(&want));
    }

    #[test]
    fn clippy_windows_declares_target_and_mingw() {
        let all = real();
        let s = all.iter().find(|s| s.name == "clippy-windows").unwrap();
        assert!(s.needs.contains(&Prerequisite::RustTarget(WINDOWS_TARGET)));
        assert!(s.needs.contains(&MINGW_GCC));
        assert_eq!(
            MINGW_GCC.install_command(),
            "sudo apt-get install -y gcc-mingw-w64-x86-64"
        );
    }

    /// A Windows-only compile break must be caught by the default `cargo dev ci` run: the step
    /// is in the list, offloadable to goway, Linux-only, and comes before the suite run.
    #[test]
    fn clippy_windows_is_in_the_default_run_before_nextest() {
        let all = real();
        let pos = |n: &str| all.iter().position(|s| s.name == n).unwrap();
        let s = &all[pos("clippy-windows")];
        assert!(s.offload && s.linux_only);
        assert!(s.args.iter().any(|a| a == "--all-targets"));
        assert!(pos("clippy-windows") < pos("nextest"));
    }

    /// Dotted-number comparison of `have` against an inclusive `[min, max]` range.
    fn within(have: &str, min: &str, max: &str) -> bool {
        let v = |s: &str| -> Vec<u64> { s.split('.').map(|p| p.parse().unwrap()).collect() };
        v(min) <= v(have) && v(have) <= v(max)
    }

    // frob:tests crates/gob-dev/src/ci.rs::hygiene
    #[test]
    fn hygiene_steps_exist_pin_installs_inside_the_frob_toml_range_and_msrv_follows_manifest() {
        let all = real();
        let text = std::fs::read_to_string(repo_root().join("frob.toml")).unwrap();
        let toml: toml::Table = text.parse().unwrap();
        for (step, tool, need, version) in [
            ("deny", "cargo-deny", CARGO_DENY, CARGO_DENY_VERSION),
            ("shear", "cargo-shear", CARGO_SHEAR, CARGO_SHEAR_VERSION),
            ("typos", "typos", TYPOS, TYPOS_VERSION),
        ] {
            let s = all.iter().find(|s| s.name == step).unwrap();
            assert!(s.linux_only && s.needs == vec![need.clone()], "{step}");
            assert_eq!(s.args, pinned_array(&toml, tool, "args").unwrap());
            assert!(need.install_command().ends_with(version), "{step}");
            let entry = toml["check"]["tool"]
                .as_array()
                .unwrap()
                .iter()
                .find(|t| t["name"].as_str() == Some(tool))
                .unwrap();
            let (min, max) = (
                entry["min_version"].as_str().unwrap(),
                entry["max_version"].as_str().unwrap(),
            );
            assert!(
                within(version, min, max),
                "{step}: {version} not in {min}..{max}"
            );
        }
        // rust-version is the pinned toolchain's series, so the msrv step is dropped.
        assert!(all.iter().all(|s| s.name != "msrv"));
    }

    // frob:ticket 01M4CTE2T943ATA1PKVBN7DCP3
    // frob:tests crates/gob-dev/src/ci.rs::msrv_is_the_toolchain
    #[test]
    fn msrv_is_dropped_only_when_rust_version_is_the_toolchain_series() {
        assert!(msrv_is_the_toolchain("1.98", "1.98.0"));
        assert!(msrv_is_the_toolchain("1.98.0", "1.98.0"));
        assert!(!msrv_is_the_toolchain("1.97", "1.98.0"));
        assert!(!msrv_is_the_toolchain("1.9", "1.98.0"));
    }

    fn repo_root() -> std::path::PathBuf {
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
    }

    #[test]
    fn pins_come_from_frob_toml() {
        let all = real();
        let z = all.iter().find(|s| s.name == "zizmor").unwrap();
        assert!(z.args[0].starts_with("zizmor@"));
        let a = all.iter().find(|s| s.name == "actionlint").unwrap();
        assert!(a.args.iter().any(|x| x.starts_with("actionlint-py==")));
    }

    /// A fake goway: logs one argv element per line to `log`, writes a report, exits `code`.
    #[cfg(unix)]
    fn fake_goway(dir: &Path, code: i32) -> (GowayRunner, std::path::PathBuf) {
        use std::os::unix::fs::PermissionsExt;
        let log = dir.join("argv.log");
        let bin = dir.join("goway");
        let script = format!(
            "#!/bin/sh\nrep=\nfor a in \"$@\"; do\n  [ \"$prev\" = --report ] && rep=\"$a\"\n  \
             printf '%s\\n' \"$a\" >> '{}'\n  prev=\"$a\"\ndone\n\
             printf '{{\"host\":\"fakehost\",\"os\":\"linux\",\"arch\":\"x86_64\",\
             \"exit_code\":{code},\"duration_secs\":1.5}}' > \"$rep\"\nexit {code}\n",
            log.display()
        );
        std::fs::write(&bin, script).unwrap();
        std::fs::set_permissions(&bin, std::fs::Permissions::from_mode(0o755)).unwrap();
        let runner = GowayRunner::with_retry(
            Program::Hook { path: bin },
            RemoteOs::Linux,
            2,
            Duration::ZERO,
        );
        (runner, log)
    }

    #[cfg(unix)]
    fn step_named(name: &str) -> Step {
        real().into_iter().find(|s| s.name == name).unwrap()
    }

    // frob:tests crates/gob-dev/src/ci.rs::GowayRunner
    #[cfg(unix)]
    #[test]
    fn remote_step_calls_goway_with_the_exact_argv_and_env_and_names_the_host() {
        let dir = tempfile::tempdir().unwrap();
        let (g, log) = fake_goway(dir.path(), 0);
        let docs = step_named("docs");
        let r = run(dir.path(), &[docs], &g, false, true, &mut |_| {});
        assert_eq!(r[0].status, StepStatus::Passed);
        let argv: Vec<String> = std::fs::read_to_string(&log)
            .unwrap()
            .lines()
            .map(str::to_owned)
            .collect();
        let pos = argv.iter().position(|a| a == "--").unwrap();
        assert_eq!(
            &argv[pos + 1..],
            ["cargo", "doc", "--no-deps", "--all-features"]
        );
        assert_eq!(&argv[..2], ["run", "--with-git"]);
        assert!(argv.windows(2).any(|w| w == ["--needs", "cores>=8"]));
        assert!(argv.windows(2).any(|w| w == ["--needs", "os=linux"]));
        assert!(
            argv.windows(2)
                .any(|w| w == ["-e", "RUSTDOCFLAGS=-D warnings"])
        );
        let (lines, ok) = summary(&r);
        assert!(ok);
        assert!(
            lines[0].contains("fakehost") && lines[0].contains("x86_64"),
            "{lines:?}"
        );
    }

    #[cfg(unix)]
    #[test]
    fn goway_exit_125_is_a_goway_failure_after_retries_not_a_test_failure() {
        let dir = tempfile::tempdir().unwrap();
        let (g, log) = fake_goway(dir.path(), GOWAY_FAILURE);
        let r = run(
            dir.path(),
            &[step_named("nextest")],
            &g,
            false,
            true,
            &mut |_| {},
        );
        assert!(
            matches!(r[0].status, StepStatus::GowayFailed(_)),
            "{:?}",
            r[0].status
        );
        let attempts = std::fs::read_to_string(&log)
            .unwrap()
            .lines()
            .filter(|l| *l == "--with-git")
            .count();
        assert_eq!(attempts, 3, "one try plus two retries");
        let (lines, ok) = summary(&r);
        assert!(!ok);
        assert!(
            lines[0].starts_with("GOWAY") && lines[0].contains("goway failed"),
            "{lines:?}"
        );
    }

    #[cfg(unix)]
    #[test]
    fn a_remote_command_failure_is_a_step_failure_naming_the_host() {
        let dir = tempfile::tempdir().unwrap();
        let (g, _) = fake_goway(dir.path(), 1);
        // The fake goway fails every probe too; this test is about the command, not prerequisites.
        let mut nextest = step_named("nextest");
        nextest.needs.clear();
        let r = run(dir.path(), &[nextest], &g, false, true, &mut |_| {});
        let StepStatus::Failed(why) = &r[0].status else {
            panic!("{:?}", r[0].status)
        };
        assert!(why.contains("exit 1") && why.contains("fakehost"), "{why}");
    }

    #[cfg(unix)]
    #[test]
    fn steps_not_marked_offload_stay_local() {
        let dir = tempfile::tempdir().unwrap();
        let (g, log) = fake_goway(dir.path(), 0);
        let local = Step {
            name: "local-true",
            program: Program::Tool {
                name: "true".to_owned(),
            },
            args: Vec::new(),
            env: Vec::new(),
            linux_only: false,
            needs: Vec::new(),
            offload: false,
            uv_tools_on_path: false,
        };
        let r = run(dir.path(), &[local], &g, false, true, &mut |_| {});
        assert_eq!(r[0].status, StepStatus::Passed);
        assert!(r[0].remote.is_none());
        assert!(!log.exists());
    }

    #[cfg(unix)]
    #[test]
    fn remote_prerequisites_are_probed_on_the_host_and_the_step_is_pinned_to_it() {
        let dir = tempfile::tempdir().unwrap();
        let (g, log) = fake_goway(dir.path(), 0);
        // The fake prints no installed targets, so the probe reports the target missing.
        let r = run(
            dir.path(),
            &[step_named("clippy-windows")],
            &g,
            false,
            true,
            &mut |_| {},
        );
        assert!(
            matches!(&r[0].status, StepStatus::HostPrerequisite(w)
                if w.contains("fakehost") && w.contains("rustup target add")),
            "{:?}",
            r[0].status
        );
        let text = std::fs::read_to_string(&log).unwrap();
        assert!(text.lines().any(|l| l == "rustup"), "{text}");
    }

    // frob:ticket 01M4527J4M910ZZBJZXMDZJQZQ
    #[cfg(unix)]
    #[test]
    fn check_step_builds_the_workspace_siblings_before_running_frob() {
        let step = step_named("check");
        let script = step.args.last().expect("script");
        for p in SIBLING_PACKAGES {
            assert!(script.contains(&format!("-p {p}")), "{script}");
        }
        assert!(
            script.find("cargo build") < script.find("cargo run"),
            "{script}"
        );
    }

    #[test]
    fn only_heavy_steps_are_offloadable() {
        let off: Vec<_> = real()
            .iter()
            .filter(|s| s.offload)
            .map(|s| s.name)
            .collect();
        assert_eq!(
            off,
            [
                "clippy",
                "clippy-windows",
                "docs",
                "nextest",
                "doctor",
                "check"
            ]
        );
    }

    #[test]
    fn goway_binary_path_or_bare_name() {
        let by_path = GowayRunner::new("/opt/goway", RemoteOs::Linux);
        assert!(matches!(by_path.goway, Program::Hook { .. }));
        let by_name = GowayRunner::new("goway", RemoteOs::Linux);
        assert!(matches!(by_name.goway, Program::Tool { .. }));
    }
}
