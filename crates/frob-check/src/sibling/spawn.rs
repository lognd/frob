//! Spawning a sibling and validating what it printed (`sibling-contract.md` sections 2, 4 and 6).

use std::path::PathBuf;
use std::time::{Duration, Instant};

use gob_exec::{ExecError, Limits, Outcome, Program, Runner, Spec};

use super::doc::{Doc, Envelope};

/// The contract majors this frob parses (`gob.sibling/<major>`); code, not configuration.
pub const ACCEPTED_SIBLING_MAJORS: &[u32] = &[1];

/// The contract name every sibling document carries.
const CONTRACT: &str = "gob.sibling";

/// The first lockstep release of a sibling that speaks `gob.sibling/1` (changelog 0.532.0); older ones are v1 tools.
pub const SIBLING_CONTRACT_SINCE: [u64; 3] = [0, 532, 0];

/// How long the `--version` probe may take before it is skipped (the document check still decides).
const PROBE_TIMEOUT: Duration = Duration::from_secs(10);

/// How a sibling run failed; one `SIB001` reason code each.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) enum Reason {
    /// Not installed, or not executable.
    Absent,
    /// Unaccepted major, wrong contract or product.
    Incompatible,
    /// Exit 2, 3 or 4, a failure envelope or a spawn error.
    Failed,
    /// `[check] sibling_timeout_secs` elapsed.
    Timeout,
    /// Stdout is not exactly one valid document.
    Malformed,
}

impl Reason {
    /// The kebab-case reason code of the contract table.
    pub(super) fn code(self) -> &'static str {
        match self {
            Self::Absent => "absent",
            Self::Incompatible => "incompatible",
            Self::Failed => "failed",
            Self::Timeout => "timeout",
            Self::Malformed => "malformed",
        }
    }
}

/// A failed sibling: the reason, the detail for the message and the product's own remedy, if any.
#[derive(Debug, Clone)]
pub(super) struct Failure {
    /// Which of the five cases.
    pub reason: Reason,
    /// What went wrong, for the finding message.
    pub detail: String,
    /// The remedy a failure envelope carried.
    pub own_remedy: Option<String>,
}

impl Failure {
    /// A failure of `reason` with `detail`.
    pub(super) fn new(reason: Reason, detail: impl Into<String>) -> Self {
        Self {
            reason,
            detail: detail.into(),
            own_remedy: None,
        }
    }

    /// The exact command that fixes it (section 6 table).
    pub(super) fn remedy(&self, product: &str) -> String {
        match self.reason {
            Reason::Absent => "uv tool install frob".to_owned(),
            Reason::Incompatible => self
                .own_remedy
                .clone()
                .unwrap_or_else(|| "uv tool install --upgrade frob".to_owned()),
            Reason::Failed => self
                .own_remedy
                .clone()
                .unwrap_or_else(|| format!("{product} check --json")),
            Reason::Timeout => {
                format!("raise [check] sibling_timeout_secs or run `{product} check --json` alone")
            }
            Reason::Malformed => format!("{product} check --json | head"),
        }
    }
}

/// What to run: one sibling check.
#[derive(Debug, Clone)]
pub(super) struct Run {
    /// The repository root, the sibling's cwd.
    pub root: PathBuf,
    /// The sibling product name.
    pub product: &'static str,
    /// How to find its binary.
    pub program: Program,
    /// `[check] base` (or `--base`), passed as `--base`.
    pub base: String,
    /// The ticket scope's paths, passed as `--ticket-scope`; `None` for an unscoped run.
    pub scope: Option<Vec<String>>,
    /// `[check] sibling_timeout_secs`.
    pub timeout: Duration,
    /// Frob's own compute digest; a sibling document carrying another one is incompatible.
    pub compute_digest: Option<String>,
    /// `[check] output_cap_bytes`: the runner kills a sibling that prints more.
    pub output_cap: usize,
}

/// A finished run: wall time and the validated document or the failure.
pub(super) struct Spawned {
    /// Wall time of the spawn, reported apart from frob's own budget.
    pub elapsed: Duration,
    /// The document, or why there is none.
    pub result: Result<Doc, Failure>,
}

/// The argv of section 2.
fn args(run: &Run) -> Vec<String> {
    let mut a = vec![
        "check".to_owned(),
        "--json".to_owned(),
        "--base".to_owned(),
        run.base.clone(),
    ];
    for path in run.scope.iter().flatten() {
        a.push("--ticket-scope".to_owned());
        a.push(path.clone());
    }
    a
}

/// Spawn the sibling and validate its document; never panics, never returns an `Err` outside [`Spawned`].
pub(super) fn run(run: &Run) -> Spawned {
    let started = Instant::now();
    let result = exec(run);
    Spawned {
        elapsed: started.elapsed(),
        result,
    }
}

fn exec(run: &Run) -> Result<Doc, Failure> {
    let runner = Runner::new(Limits { jobs: 1 })
        .allow_tools([run.product.to_owned()])
        .output_cap(run.output_cap);
    probe(&runner, run)?;
    let spec = Spec {
        program: run.program.clone(),
        args: args(run),
        cwd: Some(run.root.clone()),
        env: Vec::new(),
        timeout: run.timeout,
        capture: true,
    };
    let output = runner.run(&spec).map_err(|err| match err {
        ExecError::NotFound { .. } | ExecError::NotAllowed { .. } => Failure::new(
            Reason::Absent,
            format!("`{}` was not found next to frob or on PATH", run.product),
        ),
        ExecError::Spawn(e) if e.kind() == std::io::ErrorKind::PermissionDenied => Failure::new(
            Reason::Absent,
            format!("`{}` is not executable: {e}", run.product),
        ),
        ExecError::OutputCap { limit } => Failure::new(
            Reason::Malformed,
            format!("output exceeds the {limit} byte cap; the child was killed"),
        ),
        other => Failure::new(Reason::Failed, other.to_string()),
    })?;
    match output.status {
        Outcome::TimedOut => Err(Failure::new(
            Reason::Timeout,
            format!(
                "no document within {}s; the child was killed",
                run.timeout.as_secs()
            ),
        )),
        Outcome::Signaled => Err(Failure::new(
            Reason::Failed,
            "the sibling was terminated by a signal",
        )),
        Outcome::Exited(code @ (0 | 1)) => {
            tracing::debug!(
                product = run.product,
                code,
                bytes = output.stdout.len(),
                "sibling exited; reading document"
            );
            parse(run.product, run.compute_digest.as_deref(), &output.stdout)
        }
        Outcome::Exited(code) => {
            let mut failure = Failure::new(
                Reason::Failed,
                format!("exited {code}: {}", tail(&output.stderr, &output.stdout)),
            );
            if let Ok(env) = serde_json::from_str::<Envelope>(output.stdout.trim())
                && let Some(err) = env.error
            {
                failure.own_remedy = err.remedy;
                if !err.message.is_empty() {
                    failure.detail = format!("exited {code}: {}", err.message);
                }
            }
            Err(failure)
        }
    }
}

/// Ask the sibling for `--version` before any v2 flag (`--base`) reaches it (`sibling-contract.md` section 4).
///
/// A parsed version older than [`SIBLING_CONTRACT_SINCE`] is a v1 tool and is `Incompatible`; a probe that
/// cannot run or prints something unrecognised is logged and skipped, since the document check still guards.
fn probe(runner: &Runner, run: &Run) -> Result<(), Failure> {
    let spec = Spec {
        program: run.program.clone(),
        args: vec!["--version".to_owned()],
        cwd: Some(run.root.clone()),
        env: Vec::new(),
        timeout: PROBE_TIMEOUT.min(run.timeout),
        capture: true,
    };
    let out = match runner.run(&spec) {
        Ok(out) if out.status == Outcome::Exited(0) => out,
        other => {
            tracing::debug!(product = run.product, result = ?other.map(|o| o.status), "version probe did not answer; continuing");
            return Ok(());
        }
    };
    let line = out.stdout.lines().next().unwrap_or_default().trim();
    let Some(version) = parse_version_line(run.product, line) else {
        tracing::debug!(
            product = run.product,
            line,
            "version probe unrecognised; continuing"
        );
        return Ok(());
    };
    if version >= SIBLING_CONTRACT_SINCE {
        tracing::debug!(product = run.product, line, "version probe accepted");
        return Ok(());
    }
    let found = match &run.program {
        Program::Hook { path } => path.display().to_string(),
        other => other.label(),
    };
    let needed = SIBLING_CONTRACT_SINCE.map(|n| n.to_string()).join(".");
    let mut failure = Failure::new(
        Reason::Incompatible,
        format!(
            "found `{found}` ({line}), which predates the {CONTRACT} contract; this frob needs {CONTRACT}/{} ({} >= {needed})",
            ACCEPTED_SIBLING_MAJORS
                .iter()
                .map(u32::to_string)
                .collect::<Vec<_>>()
                .join(" or "),
            run.product
        ),
    );
    failure.own_remedy = Some(format!("uv tool install --upgrade {}", run.product));
    Err(failure)
}

/// `<product> <major>.<minor>.<patch>[-pre]` as numbers, or `None` for any other line.
fn parse_version_line(product: &str, line: &str) -> Option<[u64; 3]> {
    let rest = line.strip_prefix(product)?.trim();
    let core = rest.split(['-', '+', ' ']).next()?;
    let mut parts = core.split('.');
    let v = [
        parts.next()?.parse().ok()?,
        parts.next()?.parse().ok()?,
        parts.next()?.parse().ok()?,
    ];
    parts.next().is_none().then_some(v)
}

/// The last few hundred characters of stderr (else stdout), for a failure message.
fn tail(stderr: &str, stdout: &str) -> String {
    let t = if stderr.trim().is_empty() {
        stdout
    } else {
        stderr
    }
    .trim();
    let skip = t.chars().count().saturating_sub(300);
    t.chars().skip(skip).collect()
}

/// Validate `stdout`: one envelope, an `ok` run, the accepted contract and major, the asked product.
fn parse(product: &str, expected_digest: Option<&str>, stdout: &str) -> Result<Doc, Failure> {
    let malformed = |why: String| Failure::new(Reason::Malformed, why);
    let env: Envelope = serde_json::from_str(stdout.trim())
        .map_err(|e| malformed(format!("stdout is not exactly one JSON envelope: {e}")))?;
    if !env.ok {
        let mut failure = Failure::new(
            Reason::Failed,
            format!(
                "the sibling reported a failure: {}",
                env.error
                    .as_ref()
                    .map_or("no error body", |e| e.message.as_str())
            ),
        );
        failure.own_remedy = env.error.and_then(|e| e.remedy);
        return Err(failure);
    }
    let data = env
        .data
        .ok_or_else(|| malformed("the envelope has no `data` document".to_owned()))?;
    let declared = data
        .get("schema_version")
        .and_then(serde_json::Value::as_str)
        .ok_or_else(|| malformed("the document has no string `schema_version`".to_owned()))?
        .to_owned();
    check_version(&declared)?;
    let doc: Doc = serde_json::from_value(data)
        .map_err(|e| malformed(format!("the document fails the schema: {e}")))?;
    if doc.product != product {
        return Err(Failure::new(
            Reason::Incompatible,
            format!(
                "asked for `{product}` but the document is from `{}`",
                doc.product
            ),
        ));
    }
    if let Some(expected) = expected_digest
        && doc.compute_digest != expected
    {
        return Err(Failure::new(
            Reason::Incompatible,
            format!(
                "the sibling analysed under compute digest {} but frob's is {expected}; keep the [compute] knobs in one file",
                doc.compute_digest
            ),
        ));
    }
    Ok(doc)
}

/// `gob.sibling/<major>` against [`ACCEPTED_SIBLING_MAJORS`].
fn check_version(declared: &str) -> Result<(), Failure> {
    let incompatible = |why: String| Failure::new(Reason::Incompatible, why);
    let (name, major) = declared
        .split_once('/')
        .ok_or_else(|| incompatible(format!("`{declared}` is not `<contract>/<major>`")))?;
    if name != CONTRACT {
        return Err(incompatible(format!(
            "contract `{name}` is not `{CONTRACT}`"
        )));
    }
    let major: u32 = major
        .parse()
        .map_err(|_| incompatible(format!("major `{major}` is not an integer")))?;
    if ACCEPTED_SIBLING_MAJORS.contains(&major) {
        Ok(())
    } else {
        Err(incompatible(format!(
            "schema major {major} is not accepted (this frob accepts {ACCEPTED_SIBLING_MAJORS:?})"
        )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M4GTQHDX66EA94YZGJMHTP2N
    #[test]
    fn version_lines_parse_only_for_the_asked_product() {
        assert_eq!(parse_version_line("crunk", "crunk 0.1.1"), Some([0, 1, 1]));
        assert_eq!(
            parse_version_line("crunk", "crunk 0.533.0-rc.1"),
            Some([0, 533, 0])
        );
        assert_eq!(parse_version_line("crunk", "grimble 0.532.0"), None);
        assert_eq!(parse_version_line("crunk", "crunk 0.1"), None);
        assert_eq!(parse_version_line("crunk", "crunk 0.1.1.1"), None);
        assert_eq!(parse_version_line("crunk", "{\"ok\":true}"), None);
    }
}
