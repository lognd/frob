//! The bounded runner: spec in, redacted output out.

use std::io::Read;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, Instant};

use tracing::{debug, info, warn};

use crate::SpawnCount;
use crate::counter::record;
use crate::semaphore::Semaphore;
use crate::{ExecError, Program};

/// Default cap on captured output per stream: 64 MiB (a knob of the caller's config).
pub const DEFAULT_OUTPUT_CAP: usize = 64 * 1024 * 1024;

/// How often a running child is polled for exit.
const POLL: Duration = Duration::from_millis(5);

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
    /// Environment additions layered over the inherited environment.
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
    /// Captured stdout, redacted; empty when not captured.
    pub stdout: String,
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
        let label = spec.program.label();
        let span = tracing::info_span!("exec.spawn", program = %label);
        let _enter = span.enter();
        if let (Some(allowed), Program::Tool { name } | Program::Sibling { name }) =
            (&self.tools, &spec.program)
            && !allowed.contains(name)
        {
            warn!(program = %label, "program not on allowlist");
            return Err(ExecError::NotAllowed { program: label });
        }
        let exe = spec
            .program
            .resolve()
            .inspect_err(|e| warn!(error = %e, "resolve failed"))?;
        let _permit = self.sem.acquire();

        let mut cmd = Command::new(&exe);
        cmd.args(&spec.args)
            .envs(spec.env.iter().map(|(k, v)| (k, v)));
        if let Some(cwd) = &spec.cwd {
            cmd.current_dir(cwd);
        }
        if spec.capture {
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
        debug!(exe = %exe.display(), args = ?spec.args, pid = child.id(), "spawned");

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
        let stdout = out_t.map(collect).unwrap_or_default();
        let stderr = err_t.map(collect).unwrap_or_default();
        info!(program = %label, ?status, ?duration, "exec finished");
        Ok(Output {
            status,
            stdout,
            stderr,
            started,
            duration,
        })
    }
}

/// Read a pipe on a helper thread until its end or past `cap` bytes, which sets `exceeded`.
fn drain(
    mut r: impl Read + Send + 'static,
    cap: usize,
    exceeded: &Arc<AtomicBool>,
) -> thread::JoinHandle<Vec<u8>> {
    let exceeded = Arc::clone(exceeded);
    thread::spawn(move || {
        let mut buf = Vec::new();
        let mut chunk = [0_u8; 8 * 1024];
        loop {
            match r.read(&mut chunk) {
                Ok(0) => break,
                Ok(n) => {
                    buf.extend_from_slice(&chunk[..n]);
                    if buf.len() > cap {
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
        buf
    })
}

/// Join a drain thread and return redacted lossy UTF-8.
fn collect(h: thread::JoinHandle<Vec<u8>>) -> String {
    let bytes = h.join().unwrap_or_default();
    gob_log::redact(&String::from_utf8_lossy(&bytes)).into_owned()
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

/// Kill the child's whole process group (child only on non-unix).
#[cfg(unix)]
fn kill_group(child: &mut Child) {
    use nix::sys::signal::{Signal, killpg};
    use nix::unistd::Pid;
    let Ok(pid) = i32::try_from(child.id()) else {
        let _ = child.kill();
        return;
    };
    if let Err(e) = killpg(Pid::from_raw(pid), Signal::SIGKILL) {
        warn!(error = %e, "killpg failed; killing child only");
        let _ = child.kill();
    }
}

/// Kill the child (no process groups on this platform).
#[cfg(not(unix))]
fn kill_group(child: &mut Child) {
    let _ = child.kill();
}
