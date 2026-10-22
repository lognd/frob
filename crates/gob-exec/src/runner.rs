//! The bounded runner: spec in, redacted output out.

// frob:ticket 01M4CTDYG696JWM20AZPYFAH0T
use std::io::Read;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use tracing::{debug, info, warn};

use crate::EnvPolicy;
use crate::SpawnCount;
use crate::counter::record;
use crate::semaphore::Semaphore;
use crate::{ExecError, Program};
use crate::{PACK_ENV, ProcessPack};

/// Default cap on captured output per stream: 64 MiB (a knob of the caller's config).
pub const DEFAULT_OUTPUT_CAP: usize = 64 * 1024 * 1024;

/// How often a running child is polled for exit.
const POLL: Duration = Duration::from_millis(5);

/// How long to wait for the output readers once the child is gone; a grandchild that kept the
/// pipe open past this point is abandoned and the partial output returned.
const JOIN_GRACE: Duration = Duration::from_secs(1);

/// Concurrency limits for a [`Runner`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Limits {
    /// Maximum children running at once (`[perf] jobs`); zero is treated as one.
    pub jobs: usize,
}

impl Default for Limits {
    /// One job per available core.
    fn default() -> Self {
        Self {
            jobs: thread::available_parallelism().map_or(1, usize::from),
        }
    }
}

/// One process invocation request.
#[derive(Debug, Clone)]
pub struct Spec {
    /// Allowlisted program to run.
    pub program: Program,
    /// Arguments, passed without shell interpretation.
    pub args: Vec<String>,
    /// Working directory; the current directory when `None`.
    pub cwd: Option<PathBuf>,
    /// Environment additions layered over the child's environment (whatever the policy left).
    pub env: Vec<(String, String)>,
    /// Wall-clock limit after which the child (group) is killed.
    pub timeout: Duration,
    /// Capture stdout and stderr; otherwise they are inherited.
    pub capture: bool,
}

/// How a child ended.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    /// Exited with this status code.
    Exited(i32),
    /// Terminated by a signal (or without a code).
    Signaled,
    /// Killed after exceeding the timeout.
    TimedOut,
}

/// Result of a finished child.
#[derive(Debug, Clone)]
pub struct Output {
    /// How the child ended.
    pub status: Outcome,
    /// Captured stdout with secrets redacted, for transcripts and messages; empty when not captured.
    pub stdout: String,
    /// Captured stdout exactly as the child wrote it (lossy UTF-8), for parsing a tool's payload; empty when not captured.
    ///
    /// Not redacted, so a payload that merely looks like a secret (CSS with `secret=`) stays intact.
    /// Never log or store it; use [`Output::stdout`] for that.
    pub stdout_raw: String,
    /// Captured stderr, redacted; empty when not captured.
    pub stderr: String,
    /// When the child was spawned (after a pool slot was acquired).
    pub started: Instant,
    /// Wall-clock time from spawn to exit.
    pub duration: Duration,
}

/// Bounded process runner; at most `jobs` children run at once.
#[derive(Debug)]
pub struct Runner {
    sem: Semaphore,
    spawned: AtomicU64,
    tools: Option<Vec<String>>,
    output_cap: usize,
}

impl Runner {
    /// Create a runner honouring `limits`.
    pub fn new(limits: Limits) -> Self {
        let jobs = limits.jobs.max(1);
        debug!(jobs, "exec runner created");
        Self {
            sem: Semaphore::new(jobs),
            spawned: AtomicU64::new(0),
            tools: None,
            output_cap: DEFAULT_OUTPUT_CAP,
        }
    }

    /// Restrict `Tool` and `Sibling` programs to these names.
    #[must_use]
    pub fn allow_tools(mut self, names: impl IntoIterator<Item = String>) -> Self {
        self.tools = Some(names.into_iter().collect());
        self
    }

    /// Kill a child whose stdout or stderr passes `bytes` ([`DEFAULT_OUTPUT_CAP`] otherwise).
    #[must_use]
    pub fn output_cap(mut self, bytes: usize) -> Self {
        self.output_cap = bytes;
        self
    }

    /// Spawns performed by this runner so far.
    pub fn spawn_count(&self) -> SpawnCount {
        SpawnCount(self.spawned.load(Ordering::Relaxed))
    }

    /// Run `spec` to completion or timeout, blocking until a pool slot frees.
    ///
    /// # Errors
    /// [`ExecError::NotAllowed`] or [`ExecError::NotFound`] when the program
    /// cannot be used, [`ExecError::Spawn`] when the OS refuses to start it,
    /// [`ExecError::OutputCap`] when it floods past the output cap (it is killed),
    /// and [`ExecError::Wait`] when supervising it fails.
    pub fn run(&self, spec: &Spec) -> Result<Output, ExecError> {
        self.run_with_env(spec, &EnvPolicy::Inherit)
    }

    /// Run a verified [`ProcessPack`]: digest re-checked just before the spawn, scrubbed
    /// environment ([`PACK_ENV`] on top of the baseline), `GIT_CONFIG_NOSYSTEM=1`, stdin closed.
    /// A `-c` argument to `git` is refused (no config passthrough).
    ///
    /// # Errors
    /// [`ExecError::DigestChanged`] when the binary differs from the recorded digest,
    /// [`ExecError::NotAllowed`] for a `-c` argument to `git`, otherwise the errors of [`Runner::run`].
    pub fn run_pack(
        &self,
        pack: &ProcessPack,
        args: Vec<String>,
        cwd: Option<PathBuf>,
        timeout: Duration,
    ) -> Result<Output, ExecError> {
        pack.verify()?;
        if pack.name == "git" && args.iter().any(|a| a == "-c" || a.starts_with("-c=")) {
            warn!(program = %pack.name, "-c passthrough refused for a process pack");
            return Err(ExecError::NotAllowed {
                program: format!("{} -c", pack.name),
            });
        }
        let spec = Spec {
            program: Program::Pack {
                path: pack.path.clone(),
            },
            args,
            cwd,
            env: Vec::new(),
            timeout,
            capture: true,
        };
        self.run_with_env(&spec, &EnvPolicy::scrubbed(PACK_ENV.iter().copied()))
    }

    /// Like [`Runner::run`], with the child environment built by `env`: the parent's whole
    /// environment for [`EnvPolicy::Inherit`], or an empty one plus the allowlisted names for
    /// [`EnvPolicy::Scrub`]. `Spec::env` additions are applied last under either policy.
    ///
    /// # Errors
    /// The errors of [`Runner::run`].
    pub fn run_with_env(&self, spec: &Spec, env: &EnvPolicy) -> Result<Output, ExecError> {
        let label = spec.program.label();
        let span = tracing::info_span!("exec.spawn", program = %label);
        let _enter = span.enter();
        let exe = self.vet(spec)?;
        let _permit = self.sem.acquire();

        let mut cmd = base_command(&exe, spec, env);
        if spec.capture || matches!(spec.program, Program::Pack { .. }) {
            cmd.stdin(Stdio::null())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());
        }
        #[cfg(unix)]
        {
            use std::os::unix::process::CommandExt;
            cmd.process_group(0);
        }
        let started = Instant::now();
        let mut child = cmd.spawn().map_err(ExecError::Spawn)?;
        record(&self.spawned);
        debug!(exe = ?exe, args = ?spec.args, pid = child.id(), "spawned");

        let exceeded = Arc::new(AtomicBool::new(false));
        let cap = self.output_cap;
        let out_t = child.stdout.take().map(|r| drain(r, cap, &exceeded));
        let err_t = child.stderr.take().map(|r| drain(r, cap, &exceeded));
        let status = supervise(&mut child, started, spec.timeout, &exceeded)?;
        if exceeded.load(Ordering::Relaxed) {
            warn!(program = %label, cap, "output cap exceeded; child killed");
            return Err(ExecError::OutputCap { limit: cap });
        }
        let duration = started.elapsed();
        let join_deadline = Instant::now() + JOIN_GRACE;
        // frob:ticket 01M4DYPFE1Z7MXVNG8MJ7N30N5
        let stdout_raw = out_t.map(|d| collect(d, join_deadline)).unwrap_or_default();
        let stdout = gob_log::redact(&stdout_raw).into_owned();
        let stderr = gob_log::redact(&err_t.map(|d| collect(d, join_deadline)).unwrap_or_default())
            .into_owned();
        info!(program = %label, ?status, ?duration, "exec finished");
        Ok(Output {
            status,
            stdout,
            stdout_raw,
            stderr,
            started,
            duration,
        })
    }

    /// Start `spec` detached and return its pid without waiting: stdin, stdout and stderr go to
    /// the null device, the child leads its own process group (unix) so a terminal interrupt
    /// aimed at the caller does not reach it, and neither the pool nor `spec.timeout` applies.
    ///
    /// The child is never reaped by this runner; it is meant for a short-lived caller that
    /// exits soon after (a background refresh), where the OS reparents it.
    ///
    /// # Errors
    /// [`ExecError::NotAllowed`] or [`ExecError::NotFound`] when the program cannot be used and
    /// [`ExecError::Spawn`] when the OS refuses to start it.
    // frob:ticket 01M5D5PZP5BZFRWT9W86STF8MV
    pub fn spawn_detached(&self, spec: &Spec, env: &EnvPolicy) -> Result<u32, ExecError> {
        let label = spec.program.label();
        let span = tracing::info_span!("exec.spawn_detached", program = %label);
        let _enter = span.enter();
        let exe = self.vet(spec)?;
        let mut cmd = base_command(&exe, spec, env);
        cmd.stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        #[cfg(unix)]
        {
            use std::os::unix::process::CommandExt;
            cmd.process_group(0);
        }
        let child = cmd.spawn().map_err(ExecError::Spawn)?;
        record(&self.spawned);
        let pid = child.id();
        info!(program = %label, pid, "spawned detached");
        Ok(pid)
    }

    /// Check `spec` against the tool allowlist and resolve its executable.
    fn vet(&self, spec: &Spec) -> Result<PathBuf, ExecError> {
        let label = spec.program.label();
        if let (Some(allowed), Program::Tool { name } | Program::Sibling { name }) =
            (&self.tools, &spec.program)
            && !allowed.contains(name)
        {
            warn!(program = %label, "program not on allowlist");
            return Err(ExecError::NotAllowed { program: label });
        }
        spec.program
            .resolve()
            .inspect_err(|e| warn!(error = %e, "resolve failed"))
    }
}

/// Build the command for `spec`: args, environment per `env`, pack hardening and cwd.
fn base_command(exe: &std::path::Path, spec: &Spec, env: &EnvPolicy) -> Command {
    let mut cmd = Command::new(exe);
    cmd.args(&spec.args);
    if let Some(kept) = env.resolve(std::env::vars_os()) {
        cmd.env_clear().envs(kept);
    }
    if matches!(spec.program, Program::Pack { .. }) {
        // frob:ticket 01M3ZX7VPGRERTZNVS5VR437JY
        cmd.env("GIT_CONFIG_NOSYSTEM", "1");
    }
    cmd.envs(spec.env.iter().map(|(k, v)| (k, v)));
    if let Some(cwd) = &spec.cwd {
        cmd.current_dir(cwd);
    }
    cmd
}

/// A pipe reader thread plus the bytes it has read so far.
struct Drain {
    /// The reader thread.
    handle: thread::JoinHandle<()>,
    /// Bytes read so far, shared so partial output survives an abandoned thread.
    buf: Arc<Mutex<Vec<u8>>>,
}

/// Read a pipe on a helper thread until its end or past `cap` bytes, which sets `exceeded`.
fn drain(mut r: impl Read + Send + 'static, cap: usize, exceeded: &Arc<AtomicBool>) -> Drain {
    let exceeded = Arc::clone(exceeded);
    let buf = Arc::new(Mutex::new(Vec::new()));
    let shared = Arc::clone(&buf);
    let handle = thread::spawn(move || {
        let mut chunk = [0_u8; 8 * 1024];
        loop {
            match r.read(&mut chunk) {
                Ok(0) => break,
                Ok(n) => {
                    let mut b = shared
                        .lock()
                        .unwrap_or_else(std::sync::PoisonError::into_inner);
                    b.extend_from_slice(&chunk[..n]);
                    if b.len() > cap {
                        exceeded.store(true, Ordering::Relaxed);
                        break;
                    }
                }
                Err(e) if e.kind() == std::io::ErrorKind::Interrupted => {}
                Err(e) => {
                    warn!(error = %e, "reading child output failed");
                    break;
                }
            }
        }
    });
    Drain { handle, buf }
}

/// Wait for a reader until `deadline`, then return what it read as lossy UTF-8 (redaction is the caller's choice).
///
/// A reader still blocked at the deadline (a grandchild holds the pipe open) is detached.
fn collect(d: Drain, deadline: Instant) -> String {
    while !d.handle.is_finished() && Instant::now() < deadline {
        thread::sleep(POLL);
    }
    if d.handle.is_finished() {
        let _ = d.handle.join();
    } else {
        warn!("output reader still blocked after the child ended; abandoning it");
    }
    let bytes = std::mem::take(
        &mut *d
            .buf
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner),
    );
    String::from_utf8_lossy(&bytes).into_owned()
}

/// Poll the child until exit, `timeout` or an exceeded output cap, killing the group on timeout.
fn supervise(
    child: &mut Child,
    started: Instant,
    timeout: Duration,
    exceeded: &AtomicBool,
) -> Result<Outcome, ExecError> {
    loop {
        if exceeded.load(Ordering::Relaxed) {
            kill_group(child);
            child.wait().map_err(ExecError::Wait)?;
            return Ok(Outcome::Signaled);
        }
        if let Some(st) = child.try_wait().map_err(ExecError::Wait)? {
            return Ok(st.code().map_or(Outcome::Signaled, Outcome::Exited));
        }
        if started.elapsed() >= timeout {
            warn!(pid = child.id(), ?timeout, "timeout; killing process group");
            kill_group(child);
            child.wait().map_err(ExecError::Wait)?;
            return Ok(Outcome::TimedOut);
        }
        thread::sleep(POLL);
    }
}

/// Kill the child's whole process tree: its process group plus every descendant, so children
/// that left the group (`setsid`) die too.
#[cfg(unix)]
fn kill_group(child: &mut Child) {
    use nix::sys::signal::{Signal, kill, killpg};
    use nix::unistd::Pid;
    let Ok(pid) = i32::try_from(child.id()) else {
        let _ = child.kill();
        return;
    };
    // Snapshot before killing: orphans are reparented and the tree can no longer be walked.
    let tree = descendants(pid);
    if let Err(e) = killpg(Pid::from_raw(pid), Signal::SIGKILL) {
        warn!(error = %e, "killpg failed; killing child only");
        let _ = child.kill();
    }
    for p in tree {
        // ESRCH just means it already died with the group.
        let _ = kill(Pid::from_raw(p), Signal::SIGKILL);
    }
}

/// Pids of every live descendant of `root` (Linux `/proc`; empty elsewhere).
#[cfg(target_os = "linux")]
fn descendants(root: i32) -> Vec<i32> {
    use gob_path::exact_text;
    let mut parent_of = Vec::new();
    if let Ok(dir) = std::fs::read_dir("/proc") {
        for entry in dir.flatten() {
            let Some(pid) = exact_text(&entry.file_name()).and_then(|n| n.parse::<i32>().ok())
            else {
                continue;
            };
            let Ok(stat) = std::fs::read_to_string(entry.path().join("stat")) else {
                continue;
            };
            // "pid (comm) S ppid ..."; comm may contain spaces and parens, so split at the last ')'.
            let parent = stat
                .rsplit_once(')')
                .and_then(|(_, rest)| rest.split_whitespace().nth(1))
                .and_then(|p| p.parse::<i32>().ok());
            if let Some(parent) = parent {
                parent_of.push((pid, parent));
            }
        }
    }
    let mut found = vec![root];
    let mut i = 0;
    while i < found.len() {
        let cur = found[i];
        found.extend(
            parent_of
                .iter()
                .filter(|&&(_, pp)| pp == cur)
                .map(|&(p, _)| p),
        );
        i += 1;
    }
    found.remove(0);
    found
}

/// Pids of every live descendant of `root` (not implemented off Linux; the group kill applies).
#[cfg(all(unix, not(target_os = "linux")))]
fn descendants(_root: i32) -> Vec<i32> {
    Vec::new()
}

/// Kill the child and its descendants with `taskkill /T` (Windows has no process groups).
#[cfg(not(unix))]
fn kill_group(child: &mut Child) {
    let tree = Command::new("taskkill")
        .args(["/PID", &child.id().to_string(), "/T", "/F"])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status();
    if !tree.is_ok_and(|s| s.success()) {
        warn!("taskkill failed; killing child only");
    }
    let _ = child.kill();
}
