//! `frob init`: materialize config, ignore `.frob/`, install the ledger merge driver.

// frob:ticket 01M4FD03W4D4XZZ3XBP32Q9XFQ

use gob_path::Shown;
use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_ledger::layout::{self, Layout};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_exec::{Arg, Limits, Outcome as ExecOutcome, Program, Runner, Shell, Spec, command_line};
use gob_git::Repo;
use schemars::JsonSchema;
use serde::Serialize;

mod freshness_hooks;

use crate::PRODUCT;
use crate::config::RefModeKnob;
use crate::config_cmd::{SyncData, sync_config};
use crate::ticket::branch_cmd::ensure_ticket_branch;
use crate::workspace::Located;

/// Merge driver arguments (`%O` ancestor, `%A` ours, `%B` theirs, `%P` path), after the program.
/// The arguments after the program in the driver command; git substitutes the `%` placeholders.
const DRIVER_ARGS: [&str; 5] = ["merge-driver", "%O", "%A", "%B", "%P"];
/// The portable program name, used when `frob` on `PATH` is the running executable.
const BARE_PROGRAM: &str = "frob";
/// The git config key holding the ledger merge driver command.
pub(crate) const DRIVER_KEY: &str = "merge.frob-ledger.driver";
/// Human label stored in git config next to the driver.
const DRIVER_NAME: &str = "frob ledger union-and-refold";
/// Attribute name selecting the driver in `.gitattributes`.
const DRIVER_ATTR: &str = frob_ledger::layout::MERGE_DRIVER_ATTR;
/// Lines that already ignore the cache directory.
const IGNORE_FORMS: [&str; 4] = [".frob/", ".frob", "/.frob/", "/.frob"];
/// The `[[check.tool]]` stage `frob init` adds to a pyproject repository (ruff, pinned with a trusted version range).
// frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
const RUFF_STAGE: &str = r#"
# ruff is bound through `uvx` (pinned); its rule codes map to DEAD, ERR, CONC, TESTQ and LOGIC ids.
# The version range makes a ruff outside it an Unresolved finding instead of a violation.
[[check.tool]]
name = "ruff"
command = "uvx"
args = ["ruff@0.14.1", "check", "--output-format=json", "--no-cache", "."]
parser = "ruff-json"
version_args = ["ruff@0.14.1", "--version"]
min_version = "0.14.0"
max_version = "0.14.99"
inputs = ["**/*.py", "pyproject.toml", "ruff.toml", ".ruff.toml"]
"#;
/// The `[[check.tool]]` stages `frob init` adds to a repository whose `package.json` names eslint: the syntax stage and the separate type-aware stage.
// frob:ticket 01M4D91DTERJHX4TGJVV4KM7K8
const ESLINT_STAGES: &str = r#"
# eslint runs the repository's own config (jsx-a11y, react-hooks, react, typescript-eslint syntax rules); jsx-a11y maps to A11Y, react to REACT.
[[check.tool]]
name = "eslint"
command = "npx"
args = ["--no-install", "eslint", "-f", "json", "."]
parser = "eslint-json"
version_args = ["--no-install", "eslint", "--version"]
inputs = ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "package.json", "eslint.config.*"]

# The type-aware typescript-eslint rules (no-floating-promises -> CONC, no-explicit-any and no-unsafe-* -> TYPING) cost a type check,
# so they are a separate stage with their own config; like every tool stage it is timed apart from the check budget, and `train` keeps it out of quick runs.
[[check.tool]]
name = "eslint-typed"
command = "npx"
args = ["--no-install", "eslint", "-c", "eslint.typed.config.mjs", "-f", "json", "."]
parser = "eslint-json"
version_args = ["--no-install", "eslint", "--version"]
tier = "train"
optional = true
inputs = ["**/*.ts", "**/*.tsx", "tsconfig*.json", "package.json", "eslint.typed.config.*"]
"#;
/// The `[[check.tool]]` stage `frob init` adds to a repository with a root `.sln` or `.csproj`: `dotnet build` with the Roslyn error log on stdout.
// frob:ticket 01M4D94X9ESER47HCP4DTW2X7C
const DOTNET_STAGE: &str = r#"
# dotnet build writes the Roslyn SARIF error log (CA, IDE, VSTHRD and Microsoft.Unity.Analyzers ids); UNT* map to UNITY101, unused-code ids to DEAD001, VSTHRD* to CONC001.
# Reference Microsoft.Unity.Analyzers (its USP suppressors keep engine-called messages and serialized fields out of IDE0051/IDE0052) and
# Microsoft.VisualStudio.Threading.Analyzers as PackageReferences; the log is one file, so a multi-project build keeps the last project's.
[[check.tool]]
name = "dotnet"
command = "sh"
args = ["-c", "mkdir -p .frob && rm -f .frob/dotnet.sarif && dotnet build -nologo -v:q -p:EnforceCodeStyleInBuild=true -p:EnableNETAnalyzers=true '-p:ErrorLog=.frob/dotnet.sarif%2Cversion=2.1' >&2; cat .frob/dotnet.sarif"]
parser = "roslyn-sarif"
version_args = ["-c", "dotnet --version"]
inputs = ["**/*.cs", "**/*.csproj", "**/*.sln", "**/*.asmdef", ".editorconfig", "Directory.Build.props"]
"#;
/// Time a `git config` call may take.
const GIT_TIMEOUT: Duration = Duration::from_secs(10);

/// Write frob.toml knobs, ignore .frob/, and install the ledger merge driver; safe to repeat.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "init",
    product = "frob",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct Init {
    /// Exact merge driver command to write, overriding the resolved one.
    driver_command: Option<String>,
    /// Rewrite an existing driver that points at a different frob.
    fix_driver: bool,
    /// Ledger ref to write as `[tickets] ref` instead of the detected default branch.
    ledger_ref: Option<String>,
    /// Remove the freshness git hooks instead of installing them.
    remove_hooks: bool,
    /// Also write the project's `.claude/settings.json` (frob MCP server, read-verb allowlist).
    agent: bool,
}

/// One file-or-config step of init.
#[derive(Debug, Serialize, JsonSchema)]
pub struct Step {
    /// What the step touches (a path or a git config key).
    pub target: String,
    /// True when the step changed (or, in a dry run, would change) something.
    pub changed: bool,
}

/// Output of `init`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct InitData {
    /// Repository root initialized.
    pub root: String,
    /// The materialized config file.
    pub config: SyncData,
    /// The `.gitignore` entry.
    pub gitignore: Step,
    /// The `merge.frob-ledger.driver` git config.
    pub merge_driver: Step,
    /// Which driver command is configured and why.
    pub driver: DriverInfo,
    /// The `.gitattributes` lines (tickets, milestones, cycles).
    pub gitattributes: Step,
    /// The `tickets/** text eol=lf` pin, present when `core.autocrlf=true`; its target is the attribute line.
    pub eol_pin: Option<Step>,
    /// The local ticket branch created from origin or fresh (orphan mode only); absent otherwise.
    pub ticket_branch: Option<Step>,
    /// The `post-checkout` and `post-merge` freshness hooks (installed, or removed by `--remove-hooks`).
    pub freshness_hooks: Step,
    /// The project `.claude/settings.json` (only with `--agent`).
    pub agent_settings: Option<Step>,
}

/// The merge driver command init settled on and the reason, in the output.
#[derive(Debug, Serialize, JsonSchema)]
pub struct DriverInfo {
    /// The driver command now configured (or, in a dry run, that would be).
    pub command: String,
    /// Why this command: PATH resolution, an override, or an existing config kept.
    pub reason: String,
    /// What init did: `installed`, `updated`, `kept`, `override` or `mismatch-left`.
    pub action: String,
}

/// Short name of the checked-out branch; an unborn branch counts (its ref exists after the first commit).
///
/// Shared by every init step that needs the working branch (the ledger ref, and the `[check] base` detection of ~VA936C5).
///
/// # Errors
/// A refusal on a detached `HEAD` (no branch to name; check one out or write the knob by hand) and an internal error when `HEAD` is unreadable.
pub(crate) fn checked_out_branch(repo: &Repo) -> Result<String, CliError> {
    match repo.current_branch() {
        Ok(Some(branch)) => {
            tracing::debug!(branch, "checked-out branch detected");
            Ok(branch)
        }
        Ok(None) => {
            tracing::warn!("HEAD is detached; no branch to name");
            Err(Refusal::new(
                "E-DETACHED-HEAD",
                RefusalClass::GuardNeedsAction,
                "HEAD is detached, so frob init cannot tell which branch holds the ticket ledger",
            )
            .with_remedy("git switch <branch>, or set [tickets] ref in frob.toml, then rerun")
            .into())
        }
        Err(e) => Err(CliError::internal(e)),
    }
}

/// The ledger ref (`refs/heads/<branch>`) of the repository's default branch.
///
/// A detached `HEAD` is still refused, so a bare checkout never guesses; otherwise the ledger belongs to the
/// base branch (the remote default, or `main`), not to whichever feature branch init happens to run on.
fn ledger_ref_of_default_branch(repo: &Repo, root: &Path) -> Result<String, CliError> {
    checked_out_branch(repo)?;
    Ok(format!("refs/heads/{}", default_branch(repo, root)?))
}

/// The repository's default branch: the remote HEAD of `origin` when present, else a local `main`, else the checked-out branch.
///
/// # Errors
/// A refusal on a detached `HEAD` when there is no `origin` HEAD to fall back on.
pub(crate) fn default_branch(repo: &Repo, root: &Path) -> Result<String, CliError> {
    let runner = Runner::new(Limits { jobs: 1 });
    let (code, out) = git(
        &runner,
        root,
        &["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
    )?;
    if code == 0
        && let Some(branch) = out.strip_prefix("origin/").filter(|b| !b.is_empty())
    {
        tracing::info!(branch, "default branch from origin HEAD");
        return Ok(branch.to_owned());
    }
    let (main_code, _) = git(
        &runner,
        root,
        &["rev-parse", "--verify", "--quiet", "refs/heads/main"],
    )?;
    if main_code == 0 {
        tracing::info!("default branch from the local main branch");
        return Ok("main".to_owned());
    }
    let branch = checked_out_branch(repo)?;
    tracing::info!(branch, "default branch from the checked-out branch");
    Ok(branch)
}

/// The detected default of the absent knob `key` (`tickets.ref`, `check.base`, `evidence.attesters`), or `None` for knobs without detection.
///
/// # Errors
/// The refusal of the underlying detection (a detached `HEAD`).
pub(crate) fn detected_default(
    repo: &Repo,
    root: &Path,
    key: &str,
) -> Result<Option<toml::Value>, CliError> {
    let text = |s: String| Some(toml::Value::String(s));
    match key {
        "tickets.ref" => ledger_ref_of_default_branch(repo, root).map(text),
        "check.base" => default_branch(repo, root).map(text),
        "evidence.attesters" => Ok(owner_attesters(repo)),
        _ => Ok(None),
    }
}

/// The repository owner as the one attester: git `user.email`, or `None` (the knob stays empty, so nobody may attest) when none is set.
fn owner_attesters(repo: &Repo) -> Option<toml::Value> {
    match repo.config_user() {
        Some((_, email)) if !email.trim().is_empty() => {
            tracing::info!(email, "repository owner detected as the attester");
            Some(toml::Value::Array(vec![toml::Value::String(email)]))
        }
        _ => {
            tracing::warn!("no git user.email; [evidence] attesters stays empty");
            None
        }
    }
}

// frob:ticket 01M4D94X9ESER47HCP4DTW2X7C
/// Append `stages` to `frob.toml` unless a tool stage whose name starts with `prefix` exists; returns whether it changed.
fn append_tool_stages(
    root: &Path,
    dry_run: bool,
    prefix: &str,
    stages: &str,
) -> Result<bool, CliError> {
    let path = root.join("frob.toml");
    let existing = read_or_empty(&path)?;
    let present = existing
        .parse::<toml::Table>()
        .ok()
        .and_then(|t| {
            t.get("check")?.get("tool")?.as_array().map(|list| {
                list.iter().any(|s| {
                    s.get("name")
                        .and_then(toml::Value::as_str)
                        .is_some_and(|n| n.starts_with(prefix))
                })
            })
        })
        .unwrap_or(false);
    if present {
        tracing::debug!(prefix, "tool stage already configured");
        return Ok(false);
    }
    if !dry_run {
        let mut text = existing;
        if !text.is_empty() && !text.ends_with('\n') {
            text.push('\n');
        }
        text.push_str(stages);
        std::fs::write(&path, text)
            .map_err(|e| CliError::internal(format!("cannot write {}: {e}", Shown::of(&path))))?;
    }
    tracing::info!(path = %Shown::of(&path), dry_run, prefix, "tool stages added");
    Ok(true)
}

// frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
/// Append the ruff stage to `frob.toml` when the repository has a `pyproject.toml` and no ruff stage yet; returns whether it changed.
fn ensure_python_stage(root: &Path, dry_run: bool) -> Result<bool, CliError> {
    if !root.join("pyproject.toml").is_file() {
        tracing::debug!("no pyproject.toml; no python stage");
        return Ok(false);
    }
    append_tool_stages(root, dry_run, "ruff", RUFF_STAGE)
}

// frob:ticket 01M4D91DTERJHX4TGJVV4KM7K8
/// Append the eslint stages to `frob.toml` when `package.json` names eslint and no eslint stage exists yet; returns whether it changed.
fn ensure_web_stages(root: &Path, dry_run: bool) -> Result<bool, CliError> {
    let package = root.join("package.json");
    if !package.is_file() || !read_or_empty(&package)?.contains("eslint") {
        tracing::debug!("no package.json naming eslint; no web stages");
        return Ok(false);
    }
    append_tool_stages(root, dry_run, "eslint", ESLINT_STAGES)
}

// frob:ticket 01M4D94X9ESER47HCP4DTW2X7C
/// Whether `root` holds a `.sln` or `.csproj` file (a .NET or generated Unity solution).
fn has_dotnet_project(root: &Path) -> bool {
    std::fs::read_dir(root).is_ok_and(|entries| {
        entries.flatten().any(|e| {
            e.path()
                .extension()
                .is_some_and(|x| x == "sln" || x == "csproj")
        })
    })
}

// frob:ticket 01M4D94X9ESER47HCP4DTW2X7C
/// Append the dotnet stage to `frob.toml` when the root has a `.sln` or `.csproj` and no dotnet stage exists yet; returns whether it changed.
fn ensure_dotnet_stage(root: &Path, dry_run: bool) -> Result<bool, CliError> {
    if !has_dotnet_project(root) {
        tracing::debug!("no .sln or .csproj at the root; no dotnet stage");
        return Ok(false);
    }
    append_tool_stages(root, dry_run, "dotnet", DOTNET_STAGE)
}

/// Ensure `.frob/` is ignored; returns whether the file changed.
fn ensure_gitignore(root: &Path, dry_run: bool) -> Result<Step, CliError> {
    let path = root.join(".gitignore");
    let existing = read_or_empty(&path)?;
    let present = existing.lines().any(|l| IGNORE_FORMS.contains(&l.trim()));
    if !present && !dry_run {
        append_line(&path, &existing, ".frob/")?;
    }
    Ok(Step {
        target: Shown::of(&path).to_string(),
        changed: !present,
    })
}

// frob:ticket 01M4FD43P9VMJC9BE0KGEKVBBH
/// Attribute words pinning ledger files to LF checkouts, whatever `core.autocrlf` says.
const EOL_ATTRS: &str = "text eol=lf";
/// Glob suffix selecting everything under the ledger directory.
const ALL_BELOW: &str = "**";
/// The git config key whose `true` value rewrites checkouts to CRLF.
const AUTOCRLF_KEY: &str = "core.autocrlf";

// frob:ticket 01M5PC8M49F53YSPKKT7XXMDFH
/// The `.gitattributes` line pinning every file under `tickets_dir` to LF endings.
fn eol_line(tickets_dir: &str) -> String {
    // Gitattributes globs always use `/`, so never route this through a host `Path` join.
    let dir = tickets_dir.trim_end_matches(['/', '\\']).replace('\\', "/");
    format!("{dir}/{ALL_BELOW} {EOL_ATTRS}")
}

/// True when git is configured to check files out with CRLF endings (`core.autocrlf=true`).
///
/// `input` and `false` never produce CRLF in the working tree, so they need no pin.
fn autocrlf_enabled(root: &Path) -> Result<bool, CliError> {
    let runner = Runner::new(Limits { jobs: 1 });
    let (code, value) = git(&runner, root, &["config", "--get", AUTOCRLF_KEY])?;
    let enabled = code == 0 && value.eq_ignore_ascii_case("true");
    tracing::info!(value, enabled, "core.autocrlf probed");
    Ok(enabled)
}

/// Append `line` to `text` unless a line with the same words is present; true when appended.
fn add_line_once(text: &mut String, line: &str, path: &Path) -> bool {
    let present = text
        .lines()
        .any(|l| l.split_whitespace().eq(line.split_whitespace()));
    if !present {
        if !text.is_empty() && !text.ends_with('\n') {
            text.push('\n');
        }
        text.push_str(line);
        text.push('\n');
        tracing::info!(path = %Shown::of(path), line, "attribute line added");
    }
    !present
}

/// Ensure the attribute lines of `layout` (tickets, milestones, cycles) are in `.gitattributes`.
///
/// With `pin_eol` the `tickets/** text eol=lf` line is added too, and the second step reports it.
fn ensure_gitattributes(
    root: &Path,
    layout: Layout,
    tickets_dir: &str,
    pin_eol: bool,
    dry_run: bool,
) -> Result<(Step, Option<Step>), CliError> {
    let path = root.join(".gitattributes");
    let mut text = read_or_empty(&path)?;
    let mut changed = false;
    for line in layout::attribute_patterns(layout, tickets_dir, DRIVER_ATTR) {
        changed |= add_line_once(&mut text, &line, &path);
    }
    let eol = pin_eol.then(|| {
        let line = eol_line(tickets_dir);
        let added = add_line_once(&mut text, &line, &path);
        Step {
            target: line,
            changed: added,
        }
    });
    changed |= eol.as_ref().is_some_and(|s| s.changed);
    if changed && !dry_run {
        std::fs::write(&path, text)
            .map_err(|e| CliError::internal(format!("cannot write {}: {e}", Shown::of(&path))))?;
    }
    let step = Step {
        target: Shown::of(&path).to_string(),
        changed,
    };
    Ok((step, eol))
}

fn read_or_empty(path: &Path) -> Result<String, CliError> {
    match std::fs::read_to_string(path) {
        Ok(t) => Ok(t),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(String::new()),
        Err(e) => Err(CliError::internal(format!(
            "cannot read {}: {e}",
            Shown::of(path)
        ))),
    }
}

fn append_line(path: &Path, existing: &str, line: &str) -> Result<(), CliError> {
    let mut text = existing.to_owned();
    if !text.is_empty() && !text.ends_with('\n') {
        text.push('\n');
    }
    text.push_str(line);
    text.push('\n');
    std::fs::write(path, text)
        .map_err(|e| CliError::internal(format!("cannot write {}: {e}", Shown::of(path))))?;
    tracing::info!(path = %Shown::of(path), line, "line appended");
    Ok(())
}

/// Run `git <args>` in `root`, returning its exit code and trimmed stdout.
fn git(runner: &Runner, root: &Path, args: &[&str]) -> Result<(i32, String), CliError> {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: GIT_TIMEOUT,
        capture: true,
    };
    let out = runner.run(&spec).map_err(CliError::internal)?;
    match out.status {
        ExecOutcome::Exited(code) => Ok((code, out.stdout.trim().to_owned())),
        other => Err(CliError::internal(format!(
            "git {args:?} ended abnormally: {other:?}"
        ))),
    }
}

/// The running executable, canonical when possible.
fn running_exe() -> Result<PathBuf, CliError> {
    let exe = std::env::current_exe()
        .map_err(|e| CliError::internal(format!("cannot locate the running executable: {e}")))?;
    Ok(gob_exec::canonical(&exe).unwrap_or(exe))
}

/// The version line a frob prints for `--version`, as the running one would.
fn running_version_line() -> String {
    format!("{PRODUCT} {}", env!("FROB_BUILD_VERSION"))
}

/// First stdout line of `<path> --version`, or `None` when it cannot run.
fn version_line_of(path: &Path) -> Option<String> {
    let spec = Spec {
        program: Program::Hook {
            path: path.to_path_buf(),
        },
        args: vec!["--version".to_owned()],
        cwd: None,
        env: Vec::new(),
        timeout: GIT_TIMEOUT,
        capture: true,
    };
    match Runner::new(Limits { jobs: 1 }).run(&spec) {
        Ok(out) if out.status == ExecOutcome::Exited(0) => {
            out.stdout.lines().next().map(|l| l.trim().to_owned())
        }
        other => {
            tracing::warn!(path = %Shown::of(path), result = ?other.map(|o| o.status), "version probe failed");
            None
        }
    }
}

/// True when `path` is the running frob: the same canonical file, or else the same version line.
fn is_running_frob(path: &Path, exe: &Path) -> bool {
    let canon = gob_exec::canonical(path).unwrap_or_else(|_| path.to_path_buf());
    if canon == exe {
        return true;
    }
    let same = version_line_of(&canon).is_some_and(|v| v == running_version_line());
    tracing::debug!(path = %Shown::of(&canon), same, "different path; compared versions");
    same
}

/// The first word of a driver command, unquoted the way a POSIX shell would (single quotes and backslashes).
pub(crate) fn driver_program(command: &str) -> Option<String> {
    let mut word = String::new();
    let mut quoted = false;
    let mut chars = command.trim_start().chars();
    while let Some(c) = chars.next() {
        match (quoted, c) {
            (false, '\'') => quoted = true,
            (true, '\'') => quoted = false,
            (false, '\\') => word.extend(chars.next()),
            (false, c) if c.is_whitespace() => break,
            (_, c) => word.push(c),
        }
    }
    Some(word).filter(|w| !w.is_empty())
}

/// Resolve a driver program: a path must exist, a bare name is looked up on `PATH` (never through a shell).
fn resolve_program(program: &str) -> Option<PathBuf> {
    if program.contains('/') || (cfg!(windows) && program.contains('\\')) {
        return Path::new(program).is_file().then(|| PathBuf::from(program));
    }
    Program::Tool {
        name: program.to_owned(),
    }
    .resolve()
    .ok()
}

/// How a configured driver command relates to the running frob.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum DriverVerdict {
    /// It resolves to the running frob.
    Same,
    /// It resolves to a different frob (the resolved path).
    Other(String),
    /// It resolves to nothing (the reason).
    Unresolvable(String),
}

/// Judge `command` against the running executable.
pub(crate) fn judge_driver(command: &str) -> Result<DriverVerdict, CliError> {
    let exe = running_exe()?;
    let Some(program) = driver_program(command) else {
        return Ok(DriverVerdict::Unresolvable(
            "the command is empty".to_owned(),
        ));
    };
    Ok(match resolve_program(&program) {
        None => DriverVerdict::Unresolvable(format!("`{program}` does not resolve to a file")),
        Some(p) if is_running_frob(&p, &exe) => DriverVerdict::Same,
        Some(p) => DriverVerdict::Other(Shown::with_home(&p, None).to_string()),
    })
}

/// The shell git runs a driver command through: the bundled `sh` on Windows, `sh` elsewhere.
fn driver_shell() -> Shell {
    if cfg!(windows) {
        Shell::GitForWindowsSh
    } else {
        Shell::Posix
    }
}

/// The `\\` root of a UNC path, spelled from parts so this file holds no literal host path.
const UNC_ROOT: &str = concat!(r"\", r"\");
/// The `\\?\` verbatim prefix.
const VERBATIM: &str = concat!(r"\", r"\?\");
/// The `\\?\UNC\` verbatim UNC prefix.
const VERBATIM_UNC: &str = concat!(r"\", r"\?\UNC\");

// frob:ticket 01M41RK1G648EJJNRK4G5RJY40
/// The form of an executable path written into a driver command on Windows: forward slashes, no `\\?\` verbatim prefix.
///
/// `D:/a/frob.exe` is understood by git's `sh` and by the Windows loader alike; quoting is
/// `gob_exec::command_line`'s job. This string rewrite is the one path-to-text bridge left here and
/// moves to `gob-path` (paths.md section 1) unchanged.
pub(crate) fn windows_shell_path(path: &str) -> String {
    let plain = if let Some(unc) = path.strip_prefix(VERBATIM_UNC) {
        format!("{UNC_ROOT}{unc}")
    } else {
        path.strip_prefix(VERBATIM).unwrap_or(path).to_owned()
    };
    plain.replace('\\', "/")
}

/// The executable path as written into a driver command: Windows paths are made `sh`-safe, others are untouched.
fn exe_for_shell(exe: &Path) -> String {
    let text = Shown::with_home(exe, None).to_string();
    if cfg!(windows) {
        windows_shell_path(&text)
    } else {
        text
    }
}

/// The driver command for `program` (a bare name or an absolute path).
fn driver_command_for(program: &str) -> String {
    // git expands `%` itself before the shell runs, so a literal one in the path is doubled.
    let mut argv = vec![Arg::from(program.replace('%', "%%"))];
    argv.extend(DRIVER_ARGS.iter().map(|a| Arg::from(*a)));
    command_line(driver_shell(), &argv)
}

/// The command that fixes a wrong driver, runnable without trusting `PATH`.
pub(crate) fn fix_command() -> String {
    let exe = running_exe().map_or_else(|_| BARE_PROGRAM.to_owned(), |p| exe_for_shell(&p));
    command_line(
        driver_shell(),
        &[Arg::from(exe), Arg::from("init"), Arg::from("--fix-driver")],
    )
}

/// The driver command for this machine and why: bare `frob` only when `PATH` resolves to the running executable.
fn default_driver() -> Result<(String, String), CliError> {
    let exe = running_exe()?;
    let abs = driver_command_for(&exe_for_shell(&exe));
    Ok(match resolve_program(BARE_PROGRAM) {
        Some(p) if is_running_frob(&p, &exe) => (
            driver_command_for(BARE_PROGRAM),
            format!(
                "`frob` on PATH ({}) is the running executable",
                Shown::of(&p)
            ),
        ),
        Some(p) => (
            abs,
            format!(
                "`frob` on PATH ({}) is a different frob than the running {}",
                Shown::of(&p),
                Shown::of(&exe)
            ),
        ),
        None => (
            abs,
            format!("no `frob` on PATH; using the running {}", Shown::of(&exe)),
        ),
    })
}

/// The configured driver command in the local git config, when set.
pub(crate) fn configured_driver(root: &Path) -> Result<Option<String>, CliError> {
    let runner = Runner::new(Limits { jobs: 1 });
    let (code, current) = git(&runner, root, &["config", "--local", "--get", DRIVER_KEY])?;
    Ok((code == 0).then_some(current))
}

/// What to configure: the command, the reason, the action label, and a warning when a mismatch is left.
struct DriverChoice {
    command: String,
    reason: String,
    action: &'static str,
    warning: Option<String>,
}

/// Decide the driver command from the override, the existing config and PATH resolution.
fn choose_driver(
    current: Option<&str>,
    override_cmd: Option<&str>,
    fix: bool,
) -> Result<DriverChoice, CliError> {
    if let Some(cmd) = override_cmd {
        return Ok(DriverChoice {
            command: cmd.to_owned(),
            reason: "set by --driver-command".to_owned(),
            action: "override",
            warning: None,
        });
    }
    let fresh = |action| -> Result<DriverChoice, CliError> {
        let (command, reason) = default_driver()?;
        Ok(DriverChoice {
            command,
            reason,
            action,
            warning: None,
        })
    };
    let Some(cur) = current else {
        return fresh("installed");
    };
    match judge_driver(cur)? {
        DriverVerdict::Same => Ok(DriverChoice {
            command: cur.to_owned(),
            reason: "the existing driver resolves to the running frob".to_owned(),
            action: "kept",
            warning: None,
        }),
        DriverVerdict::Unresolvable(why) => {
            tracing::warn!(
                current = cur,
                why,
                "existing driver resolves to nothing; replacing"
            );
            fresh("updated")
        }
        DriverVerdict::Other(resolved) if fix => {
            tracing::warn!(
                current = cur,
                resolved,
                "existing driver is a different frob; replacing"
            );
            fresh("updated")
        }
        DriverVerdict::Other(resolved) => {
            let warning = format!(
                "merge driver `{cur}` resolves to {resolved}, a different frob than the running one; fix: {}",
                fix_command()
            );
            tracing::warn!(
                current = cur,
                resolved,
                "different-frob driver left in place"
            );
            Ok(DriverChoice {
                command: cur.to_owned(),
                reason: format!(
                    "resolves to a different frob ({resolved}); left unchanged without --fix-driver"
                ),
                action: "mismatch-left",
                warning: Some(warning),
            })
        }
    }
}

/// Ensure `merge.frob-ledger.driver` (and its name) are set in the local git config.
fn ensure_merge_driver(
    root: &Path,
    dry_run: bool,
    override_cmd: Option<&str>,
    fix: bool,
) -> Result<(Step, DriverInfo, Option<String>), CliError> {
    let runner = Runner::new(Limits { jobs: 1 });
    let current = configured_driver(root)?;
    let choice = choose_driver(current.as_deref(), override_cmd, fix)?;
    let present = current.as_deref() == Some(choice.command.as_str());
    if !present && !dry_run {
        for (k, v) in [
            (DRIVER_KEY, choice.command.as_str()),
            ("merge.frob-ledger.name", DRIVER_NAME),
        ] {
            let (code, _) = git(&runner, root, &["config", "--local", k, v])?;
            if code != 0 {
                return Err(CliError::internal(format!("git config {k} exited {code}")));
            }
        }
        tracing::info!(command = %choice.command, reason = %choice.reason, "merge driver installed");
    }
    let action = if present && choice.action != "mismatch-left" && choice.action != "override" {
        "kept"
    } else {
        choice.action
    };
    Ok((
        Step {
            target: DRIVER_KEY.to_owned(),
            changed: !present,
        },
        DriverInfo {
            command: choice.command,
            reason: choice.reason,
            action: action.to_owned(),
        },
        choice.warning,
    ))
}

/// `Init` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct InitArgs {
    #[arg(
        long = "driver-command",
        value_name = "TEXT",
        help = "Write this exact merge driver command instead of the resolved one"
    )]
    driver_command: Option<String>,
    #[arg(
        long = "ledger-ref",
        value_name = "REF",
        help = "Write this ref (refs/heads/<branch>) as [tickets] ref instead of the default branch"
    )]
    ledger_ref: Option<String>,
    #[arg(
        long = "fix-driver",
        help = "Rewrite an existing merge driver that points at a different frob"
    )]
    fix_driver: bool,
    #[arg(
        long = "remove-hooks",
        help = "Remove the freshness git hooks init installs instead of installing them"
    )]
    remove_hooks: bool,
    #[arg(
        long = "agent",
        help = "Also write .claude/settings.json: the frob MCP server and an allowlist for read verbs"
    )]
    agent: bool,
}

impl Command for Init {
    type Data = InitData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<InitArgs>(cmd)
    }

    fn from_matches(matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<InitArgs>(matches)?;
        Ok(Self {
            driver_command: a.driver_command,
            fix_driver: a.fix_driver,
            ledger_ref: a.ledger_ref,
            remove_hooks: a.remove_hooks,
            agent: a.agent,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<InitData> {
        let located = Located::discover(&ctx.cwd);
        let repo = located.require_repo()?;
        let root = &located.root;
        // frob:ticket 01M42H140A7Y1AMEQJ0YVTYZDE
        frob_ledger::redact::RuleSet::mention_local_files(repo.common_dir());
        let cfg = crate::workspace::load_config(root)?;
        if let Some(r) = self.ledger_ref.as_deref()
            && r.strip_prefix("refs/heads/").is_none_or(str::is_empty)
        {
            return Err(CliError::Usage(format!(
                "--ledger-ref `{r}` must name a branch as refs/heads/<branch>"
            )));
        }
        let config = sync_config(
            root,
            ctx.dry_run,
            Some(&|key| match (key, self.ledger_ref.as_deref()) {
                ("tickets.ref", Some(r)) => Ok(Some(toml::Value::String(r.to_owned()))),
                _ => detected_default(repo, root, key),
            }),
        )?;
        let python_stage = ensure_python_stage(root, ctx.dry_run)?;
        let web_stages = ensure_web_stages(root, ctx.dry_run)?;
        let dotnet_stage = ensure_dotnet_stage(root, ctx.dry_run)?;
        let gitignore = ensure_gitignore(root, ctx.dry_run)?;
        let (merge_driver, driver, driver_warning) = ensure_merge_driver(
            root,
            ctx.dry_run,
            self.driver_command.as_deref(),
            self.fix_driver,
        )?;
        // The ticket branch carries its own `.gitattributes`; the code branch holds no ledger files.
        let (gitattributes, eol_pin) = if cfg.tickets.ref_mode == RefModeKnob::Orphan {
            tracing::info!(
                "ledger lives on the ticket branch; no ledger attributes on the code branch"
            );
            let step = Step {
                target: Shown::of(&root.join(".gitattributes")).to_string(),
                changed: false,
            };
            (step, None)
        } else {
            let pin_eol = autocrlf_enabled(root)?;
            ensure_gitattributes(root, Layout::Dir, &cfg.tickets.dir, pin_eol, ctx.dry_run)?
        };
        let ticket_branch = ensure_ticket_branch(repo, &cfg, ctx.dry_run)?.map(|branch| Step {
            target: format!("refs/heads/{branch}"),
            changed: true,
        });
        let hooks_dir = repo.common_dir().join("hooks");
        let hook_paths = if self.remove_hooks {
            freshness_hooks::remove(&hooks_dir, ctx.dry_run)
        } else {
            freshness_hooks::install(&hooks_dir, ctx.dry_run)
        }
        .map_err(CliError::internal)?;
        let freshness = Step {
            target: Shown::of(&hooks_dir).to_string(),
            changed: !hook_paths.is_empty(),
        };
        let agent_settings = if self.agent {
            let changed = crate::agent::project::configure(root, ctx.dry_run)
                .map_err(|e| crate::agent_cmd::agent_refusal(&e))?;
            Some(Step {
                target: Shown::of(&root.join(crate::agent::project::PROJECT_SETTINGS)).to_string(),
                changed,
            })
        } else {
            None
        };
        let already = config.added.is_empty()
            && !freshness.changed
            && ticket_branch.is_none()
            && !python_stage
            && !web_stages
            && !dotnet_stage
            && !gitignore.changed
            && !merge_driver.changed
            && !gitattributes.changed
            && !agent_settings.as_ref().is_some_and(|s| s.changed);
        tracing::info!(already, dry_run = ctx.dry_run, "init finished");
        let payload = Payload::new(InitData {
            root: Shown::of(root).to_string(),
            config,
            gitignore,
            merge_driver,
            driver,
            gitattributes,
            eol_pin,
            ticket_branch,
            freshness_hooks: freshness,
            agent_settings,
        })
        .with_already(already);
        Ok(match driver_warning {
            Some(w) => payload.with_warning(w),
            None => payload,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
    // frob:tests crates/frob/src/init.rs::ensure_python_stage
    #[test]
    fn a_pyproject_repository_gets_one_pinned_ruff_stage() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        std::fs::write(root.join("frob.toml"), "[check]\nbase = \"main\"\n").expect("write");
        assert!(!ensure_python_stage(root, false).expect("no pyproject"));
        std::fs::write(root.join("pyproject.toml"), "[project]\nname = \"x\"\n").expect("write");
        assert!(ensure_python_stage(root, true).expect("dry run"));
        assert!(ensure_python_stage(root, false).expect("first"));
        assert!(!ensure_python_stage(root, false).expect("second is a no-op"));
        let table: toml::Table = std::fs::read_to_string(root.join("frob.toml"))
            .expect("read")
            .parse()
            .expect("valid toml");
        let stage = &table["check"]["tool"][0];
        assert_eq!(stage["parser"].as_str(), Some("ruff-json"));
        assert_eq!(stage["min_version"].as_str(), Some("0.14.0"));
        assert_eq!(stage["max_version"].as_str(), Some("0.14.99"));
    }

    // frob:ticket 01M4D91DTERJHX4TGJVV4KM7K8
    // frob:tests crates/frob/src/init.rs::ensure_web_stages
    #[test]
    fn an_eslint_repository_gets_a_syntax_stage_and_a_separate_type_aware_stage() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        std::fs::write(root.join("frob.toml"), "[check]\nbase = \"main\"\n").expect("write");
        std::fs::write(root.join("package.json"), "{}").expect("write");
        assert!(!ensure_web_stages(root, false).expect("no eslint named"));
        std::fs::write(
            root.join("package.json"),
            "{\"devDependencies\":{\"eslint\":\"9.0.0\"}}",
        )
        .expect("write");
        assert!(ensure_web_stages(root, true).expect("dry run"));
        assert!(ensure_web_stages(root, false).expect("first"));
        assert!(!ensure_web_stages(root, false).expect("second is a no-op"));
        let table: toml::Table = std::fs::read_to_string(root.join("frob.toml"))
            .expect("read")
            .parse()
            .expect("valid toml");
        let stages = table["check"]["tool"].as_array().expect("stages");
        assert_eq!(stages.len(), 2);
        assert_eq!(stages[0]["parser"].as_str(), Some("eslint-json"));
        assert_eq!(stages[1]["name"].as_str(), Some("eslint-typed"));
        assert_eq!(stages[1]["tier"].as_str(), Some("train"));
    }

    // frob:ticket 01M4D94X9ESER47HCP4DTW2X7C
    // frob:tests crates/frob/src/init.rs::ensure_dotnet_stage
    // frob:tests crates/frob/src/init.rs::append_tool_stages
    #[test]
    fn a_dotnet_repository_gets_one_roslyn_sarif_stage() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        std::fs::write(root.join("frob.toml"), "[check]\nbase = \"main\"\n").expect("write");
        assert!(!ensure_dotnet_stage(root, false).expect("no project"));
        std::fs::write(root.join("Game.sln"), "").expect("write");
        assert!(ensure_dotnet_stage(root, true).expect("dry run"));
        assert!(ensure_dotnet_stage(root, false).expect("first"));
        assert!(!ensure_dotnet_stage(root, false).expect("second is a no-op"));
        let table: toml::Table = std::fs::read_to_string(root.join("frob.toml"))
            .expect("read")
            .parse()
            .expect("valid toml");
        let stages = table["check"]["tool"].as_array().expect("stages");
        assert_eq!(stages.len(), 1);
        assert_eq!(stages[0]["name"].as_str(), Some("dotnet"));
        assert_eq!(stages[0]["parser"].as_str(), Some("roslyn-sarif"));
    }

    // frob:ticket 01M41RK1G648EJJNRK4G5RJY40
    // frob:tests crates/frob/src/init.rs::windows_shell_path
    #[test]
    // frob:accept PATH001 because="Windows shell path conversion is tested on literal Windows paths not creatable on this host"
    fn windows_paths_become_forward_slash_sh_words() {
        assert_eq!(
            windows_shell_path(r"D:\a\frob\frob\target\debug\frob.exe"),
            "D:/a/frob/frob/target/debug/frob.exe"
        );
        // The mixed form assert_cmd and cargo produce, and the verbatim prefix canonicalize adds.
        assert_eq!(
            windows_shell_path(r"D:\a\frob\target\debug/frob.exe"),
            "D:/a/frob/target/debug/frob.exe"
        );
        assert_eq!(
            windows_shell_path(r"\\?\C:\Users\Run Ner\frob.exe"),
            "C:/Users/Run Ner/frob.exe"
        );
        assert_eq!(
            windows_shell_path(r"\\?\UNC\host\share\frob.exe"),
            "//host/share/frob.exe"
        );
        assert_eq!(windows_shell_path("/usr/bin/frob"), "/usr/bin/frob");
    }

    // frob:ticket 01M41RK1G648EJJNRK4G5RJY40
    // frob:tests crates/frob/src/init.rs::driver_command_for
    #[test]
    // frob:accept PATH001 because="Windows shell path conversion is tested on literal Windows paths not creatable on this host"
    fn the_driver_command_is_built_by_command_line_and_keeps_git_placeholders() {
        let line = driver_command_for(&windows_shell_path(r"C:\Program Files\frob\frob.exe"));
        let argv: Vec<Arg> = [
            "C:/Program Files/frob/frob.exe",
            "merge-driver",
            "%O",
            "%A",
            "%B",
            "%P",
        ]
        .into_iter()
        .map(Arg::from)
        .collect();
        assert_eq!(line, command_line(driver_shell(), &argv));
        assert!(line.ends_with(" merge-driver %O %A %B %P"), "{line}");
        assert_eq!(
            driver_program(&line).as_deref(),
            Some("C:/Program Files/frob/frob.exe")
        );
        assert!(driver_command_for("/opt/50%/frob").contains("50%%"));
    }
}
