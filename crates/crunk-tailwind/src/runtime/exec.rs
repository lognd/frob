//! Running `node helper.mjs <request.json>` in the project root through `gob-exec`.
//!
//! The child gets a scrubbed environment (`PATH`, `HOME`, `NODE_PATH`, `NODE_ENV`; never a
//! secret-shaped variable), the project root as its working directory, a wall-clock timeout and
//! an output cap. The helper script ships inside the binary and is materialized in the state
//! directory under a content-hash name; the request is a short-lived file beside it.

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{EnvPolicy, ExecError, Limits, Outcome, Program, Runner, Spec};
use gob_walk::Digest;

use super::RuntimeError;
use super::protocol::{Request, Response};

/// The helper script, embedded.
pub const HELPER_SOURCE: &str = include_str!("../../node/helper.mjs");

/// Variables besides the baseline that a project's node may legitimately read.
const NODE_ENV_NAMES: [&str; 2] = ["NODE_PATH", "NODE_ENV"];

/// How the helper process is run.
#[derive(Debug, Clone)]
pub(crate) struct Exec {
    /// Bare node binary name.
    pub node: String,
    /// Wall-clock limit.
    pub timeout: Duration,
    /// Cap in bytes on each captured stream.
    pub output_cap: usize,
    /// Directory holding the materialized helper and requests.
    pub work_dir: PathBuf,
}

impl Exec {
    /// The resolved path of the node binary, or `None` when it is not on `PATH`.
    pub fn resolve_node(&self) -> Option<PathBuf> {
        Program::Tool {
            name: self.node.clone(),
        }
        .resolve()
        .inspect_err(|e| tracing::info!(node = %self.node, error = %e, "node not resolvable"))
        .ok()
    }

    /// Run the helper with `request` from `project_root` and parse its response.
    pub fn run(&self, project_root: &Path, request: &Request) -> Result<Response, RuntimeError> {
        let helper = self.materialize_helper()?;
        let request_file = self.write_request(request)?;
        let request_path = request_file.path().to_path_buf();
        let spec = Spec {
            program: Program::Tool {
                name: self.node.clone(),
            },
            args: vec![
                helper.to_string_lossy().into_owned(),
                request_path.to_string_lossy().into_owned(),
            ],
            cwd: Some(project_root.to_path_buf()),
            env: Vec::new(),
            timeout: self.timeout,
            capture: true,
        };
        tracing::info!(cwd = %project_root.display(), node = %self.node, "tailwind helper starting");
        let runner = Runner::new(Limits { jobs: 1 }).output_cap(self.output_cap);
        let policy = EnvPolicy::scrubbed(NODE_ENV_NAMES);
        let ran = runner.run_with_env(&spec, &policy);
        drop(request_file);
        let output = ran.map_err(|e| match e {
            ExecError::OutputCap { limit } => RuntimeError::OutputCap { limit },
            other => RuntimeError::Spawn(other.to_string()),
        })?;
        match output.status {
            Outcome::TimedOut => {
                tracing::warn!(secs = self.timeout.as_secs(), "tailwind helper timed out");
                return Err(RuntimeError::Timeout {
                    secs: self.timeout.as_secs(),
                });
            }
            Outcome::Signaled => {
                return Err(RuntimeError::Crashed {
                    detail: format!("killed by a signal; stderr: {}", excerpt(&output.stderr)),
                });
            }
            Outcome::Exited(_) => {}
        }
        serde_json::from_str::<Response>(output.stdout.trim()).map_err(|e| {
            tracing::warn!(error = %e, stderr = %excerpt(&output.stderr), "unparseable helper output");
            RuntimeError::Crashed {
                detail: format!(
                    "unparseable output ({e}); exit {:?}; stderr: {}",
                    output.status,
                    excerpt(&output.stderr)
                ),
            }
        })
    }

    /// Write the embedded helper under a content-hash name (once per content).
    fn materialize_helper(&self) -> Result<PathBuf, RuntimeError> {
        let key = Digest::of(HELPER_SOURCE.as_bytes()).to_string();
        let path = self.work_dir.join(format!("helper-{}.mjs", &key[..16]));
        if path.is_file() {
            return Ok(path);
        }
        self.write_file(&path, HELPER_SOURCE.as_bytes())?;
        Ok(path)
    }

    /// The request as a temporary file in the work directory, removed when dropped.
    fn write_request(&self, request: &Request) -> Result<tempfile::NamedTempFile, RuntimeError> {
        let body = serde_json::to_vec(request).map_err(|e| RuntimeError::Crashed {
            detail: format!("cannot encode the request: {e}"),
        })?;
        let io = |detail: String| RuntimeError::Io {
            path: self.work_dir.to_string_lossy().into_owned(),
            detail,
        };
        std::fs::create_dir_all(&self.work_dir).map_err(|e| io(e.to_string()))?;
        let mut file = tempfile::Builder::new()
            .prefix("request-")
            .suffix(".json")
            .tempfile_in(&self.work_dir)
            .map_err(|e| io(e.to_string()))?;
        file.write_all(&body)
            .and_then(|()| file.flush())
            .map_err(|e| io(e.to_string()))?;
        Ok(file)
    }

    fn write_file(&self, path: &Path, bytes: &[u8]) -> Result<(), RuntimeError> {
        std::fs::create_dir_all(&self.work_dir)
            .and_then(|()| gob_fs::write_atomic(path, bytes))
            .map_err(|source| {
                tracing::warn!(path = %path.display(), error = %source, "cannot write a runtime file");
                RuntimeError::Io {
                    path: path.to_string_lossy().into_owned(),
                    detail: source.to_string(),
                }
            })
    }
}

/// The first 2000 characters of a stream, for error text.
fn excerpt(text: &str) -> String {
    text.chars().take(2000).collect()
}
