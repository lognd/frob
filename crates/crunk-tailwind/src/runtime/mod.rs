//! The Tailwind runtime bridge: the project's own `tailwindcss`, run out of process.
//!
//! Tailwind's truth (which classes compile to what, what the merged theme holds) exists only in
//! Tailwind itself, so the bridge runs the project's installed `tailwindcss` (v3) or
//! `@tailwindcss/node` (v4) through `node` and the shipped helper (`node/helper.mjs`). It
//! executes project code, so:
//!
//! - every spawn goes through `gob-exec` with a scrubbed environment, a timeout and an output
//!   cap ([`Options`]);
//! - a first-run notice names the config and the opt-outs ([`notice`]);
//! - without node, without a project install, or in static mode the answer is
//!   [`Evaluation::Unresolved`] with the reason, code [`UNRESOLVED_CODE`]: never clean, never a
//!   crash, never a silent skip.
//!
//! Results are cached per config generation ([`cache`]). Node is the only runtime dependency, and
//! only here.

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

pub mod cache;
pub mod css;
mod doctor;
mod exec;
pub mod model;
pub mod notice;
mod protocol;
pub mod resolve;

use std::collections::BTreeMap;
use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;

use gob_cache::Cache;

pub use doctor::{DoctorReport, Row};
pub use exec::HELPER_SOURCE;
pub use model::{
    AtRuleWrap, ClassDeclaration, ClassResult, ClassStatus, Evaluation, RunResult, TailwindVersion,
    ThemeResult, UNRESOLVED_CODE, Unresolved,
};

use exec::Exec;
use protocol::{Request, Response, path_text};

/// Why the runtime could not produce an answer or an [`Unresolved`] verdict.
///
/// These are real failures of a helper that did run (or could not be started), reported with
/// their cause; a missing node or install is [`Unresolved`], not an error.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[non_exhaustive]
pub enum RuntimeError {
    /// The helper exceeded its wall-clock limit and was killed.
    #[error("the tailwind helper exceeded its {secs}s timeout and was killed")]
    Timeout {
        /// The limit.
        secs: u64,
    },
    /// The helper wrote more than the output cap and was killed.
    #[error("the tailwind helper output exceeded the {limit} byte cap and the helper was killed")]
    OutputCap {
        /// The cap in bytes.
        limit: usize,
    },
    /// The helper could not be started or supervised.
    #[error("cannot run the tailwind helper: {0}")]
    Spawn(String),
    /// The helper ran but crashed or wrote output that is not a response.
    #[error("the tailwind helper failed: {detail}")]
    Crashed {
        /// What was observed.
        detail: String,
    },
    /// The helper ran and reported an error of its own (a bad config, a missing module).
    #[error("the tailwind helper reported an error: {error}")]
    HelperReported {
        /// The helper's message.
        error: String,
    },
    /// The response was valid JSON but not the expected shape.
    #[error("the tailwind helper response is malformed: {0}")]
    BadResponse(String),
    /// A runtime file could not be written.
    #[error("cannot write under {path}: {detail}")]
    Io {
        /// The directory or file.
        path: String,
        /// The OS error.
        detail: String,
    },
    /// The compiled CSS could not be read.
    #[error(transparent)]
    Css(#[from] CssFailure),
}

/// The CSS adapter failed on compiled output (an adapter bug).
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{0}")]
pub struct CssFailure(String);

/// Knobs of a [`Runtime`].
#[derive(Debug, Clone)]
pub struct Options {
    /// Bare node binary name looked up on `PATH`.
    pub node_binary: String,
    /// Wall-clock limit of one helper run.
    pub timeout: Duration,
    /// Cap in bytes on each captured helper stream.
    pub output_cap: usize,
    /// Static mode: never run Tailwind (`--static`, `[tailwind] engine = "static"`).
    pub static_mode: bool,
    /// The state directory (notice record, materialized helper); `None` resolves the user's.
    pub state_dir: Option<PathBuf>,
    /// Suppress the printed notice (`CRUNK_QUIET_EXEC_NOTICE=1`); the record is still kept.
    pub quiet_notice: bool,
}

impl Default for Options {
    /// `node`, 20 s, 8 MiB, node mode, the user's state directory, notice shown.
    fn default() -> Self {
        Self {
            node_binary: "node".to_owned(),
            timeout: Duration::from_secs(20),
            output_cap: 8 * 1024 * 1024,
            static_mode: false,
            state_dir: None,
            quiet_notice: false,
        }
    }
}

/// The project files the helper reads: a v3 JS config and/or the v4 CSS entry.
#[derive(Debug, Clone, Default)]
pub struct Sources {
    /// The v3 config (`tailwind.config.js`), or the JS file an `@config` bridge names.
    pub config_path: Option<PathBuf>,
    /// The v4 CSS entry holding `@import "tailwindcss"`.
    pub css_entry: Option<PathBuf>,
}

/// Receives the first-run notice text.
pub type NoticeSink = Arc<dyn Fn(&str) + Send + Sync>;

/// The Tailwind runtime for one project.
pub struct Runtime {
    project_root: PathBuf,
    options: Options,
    cache: Cache,
    sink: NoticeSink,
}

impl std::fmt::Debug for Runtime {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Runtime")
            .field("project_root", &self.project_root)
            .field("options", &self.options)
            .finish_non_exhaustive()
    }
}

/// The default notice sink: the text on standard error.
fn stderr_sink() -> NoticeSink {
    Arc::new(|text: &str| {
        let mut err = std::io::stderr().lock();
        if let Err(e) = writeln!(err, "{text}") {
            tracing::debug!(error = %e, "cannot write the exec notice to stderr");
        }
    })
}

impl Runtime {
    /// A runtime for `project_root` caching through `cache` (a null cache disables caching).
    pub fn new(project_root: &Path, options: Options, cache: Cache) -> Self {
        Self {
            project_root: project_root.to_path_buf(),
            options,
            cache,
            sink: stderr_sink(),
        }
    }

    /// Send the first-run notice to `sink` instead of standard error.
    #[must_use]
    pub fn with_notice_sink(mut self, sink: NoticeSink) -> Self {
        self.sink = sink;
        self
    }

    fn state_dir(&self) -> PathBuf {
        self.options
            .state_dir
            .clone()
            .or_else(notice::state_base)
            .unwrap_or_else(|| self.project_root.join(".crunk").join("state"))
    }

    fn exec(&self) -> Exec {
        Exec {
            node: self.options.node_binary.clone(),
            timeout: self.options.timeout,
            output_cap: self.options.output_cap,
            work_dir: self.state_dir().join("tailwind-runtime"),
        }
    }

    /// Everything that must hold before the helper can run: version, node.
    fn prepare(&self) -> Result<(TailwindVersion, PathBuf), Unresolved> {
        if self.options.static_mode {
            tracing::info!("tailwind runtime: static mode requested; not running node");
            return Err(Unresolved::StaticMode);
        }
        let dir = resolve::find_tailwindcss_dir(&self.project_root).ok_or_else(|| {
            Unresolved::TailwindMissing {
                project_root: self.project_root.to_string_lossy().into_owned(),
            }
        })?;
        let text = resolve::read_version(&dir)
            .map_err(|detail| Unresolved::VersionUnreadable { detail })?;
        let version = resolve::major_of(&text)
            .and_then(resolve::version_of_major)
            .ok_or_else(|| Unresolved::UnsupportedVersion {
                major: text.clone(),
            })?;
        let node = self
            .exec()
            .resolve_node()
            .ok_or_else(|| Unresolved::NodeMissing {
                binary: self.options.node_binary.clone(),
            })?;
        tracing::debug!(version = ?version, node = %node.display(), "tailwind runtime ready");
        Ok((version, node))
    }

    /// Show the first-run notice for the file the helper will execute, if it is due.
    fn notify(&self, version: TailwindVersion, sources: &Sources) {
        let target = match version {
            TailwindVersion::V3 => sources.config_path.as_deref(),
            TailwindVersion::V4 => sources.css_entry.as_deref(),
        };
        let Some(target) = target else {
            return;
        };
        let shown = notice::first_run(
            &self.state_dir(),
            &self.project_root,
            target,
            &self.options.node_binary,
            self.options.quiet_notice,
        );
        if let Some(text) = shown {
            (self.sink)(&text);
        }
    }

    fn require_css_entry(
        version: TailwindVersion,
        sources: &Sources,
    ) -> Result<Option<String>, Unresolved> {
        match (version, &sources.css_entry) {
            (TailwindVersion::V4, None) => Err(Unresolved::MissingCssEntry),
            (TailwindVersion::V4, Some(p)) => Ok(Some(path_text(p))),
            (TailwindVersion::V3, _) => Ok(None),
        }
    }

    fn cache_sources(sources: &Sources) -> Vec<PathBuf> {
        sources
            .config_path
            .iter()
            .chain(sources.css_entry.iter())
            .cloned()
            .collect()
    }

    /// Compile `candidates` through the project's Tailwind and return typed per-class
    /// declarations, from the cache when every candidate is already known.
    ///
    /// # Errors
    ///
    /// [`RuntimeError`] when the helper ran (or tried to) and failed; node absent, no install
    /// and static mode are `Ok(Evaluation::Unresolved(..))`.
    pub fn evaluate_candidates(
        &self,
        candidates: &[String],
        sources: &Sources,
    ) -> Result<Evaluation<RunResult>, RuntimeError> {
        let (version, _node) = match self.prepare() {
            Ok(ready) => ready,
            Err(u) => return Ok(Evaluation::Unresolved(u)),
        };
        let css_entry = match Self::require_css_entry(version, sources) {
            Ok(entry) => entry,
            Err(u) => return Ok(Evaluation::Unresolved(u)),
        };
        let key = cache::universe_key(version, &Self::cache_sources(sources));
        let mut universe = cache::load(&self.cache, &key);
        let missing: Vec<String> = candidates
            .iter()
            .filter(|c| !universe.classes.contains_key(*c))
            .cloned()
            .collect();
        let mut config_path = None;
        if missing.is_empty() {
            tracing::debug!(
                candidates = candidates.len(),
                "tailwind results served from cache"
            );
        } else {
            self.notify(version, sources);
            let request = match version {
                TailwindVersion::V3 => Request::V3 {
                    project_root: path_text(&self.project_root),
                    config_path: sources.config_path.as_deref().map(path_text),
                    candidates: missing.clone(),
                },
                TailwindVersion::V4 => Request::V4 {
                    project_root: path_text(&self.project_root),
                    css_entry_path: css_entry.unwrap_or_default(),
                    candidates: missing.clone(),
                },
            };
            let response = self.exec().run(&self.project_root, &request)?;
            let response = ok_response(response)?;
            config_path.clone_from(&response.config_path);
            let css_text = response.css.unwrap_or_default();
            let by_candidate = css::parse_declarations_by_candidate(&css_text)
                .map_err(|e| CssFailure(e.to_string()))?;
            for candidate in &missing {
                let declarations = by_candidate.get(candidate).cloned().unwrap_or_default();
                let status = if declarations.is_empty() {
                    ClassStatus::Invalid
                } else {
                    ClassStatus::Valid
                };
                universe.classes.insert(
                    candidate.clone(),
                    ClassResult {
                        candidate: candidate.clone(),
                        status,
                        declarations,
                    },
                );
            }
            cache::store(&self.cache, &key, &universe);
        }
        let results = candidates
            .iter()
            .filter_map(|c| universe.classes.get(c).cloned())
            .collect();
        Ok(Evaluation::Resolved(RunResult {
            version,
            config_path,
            results,
        }))
    }

    /// The project's own contribution to Tailwind's merged theme (v3 `resolveConfig`, v4
    /// `__unstable__loadDesignSystem`), diffed against Tailwind's pure defaults.
    ///
    /// # Errors
    ///
    /// As [`Runtime::evaluate_candidates`].
    pub fn resolve_theme(
        &self,
        sources: &Sources,
    ) -> Result<Evaluation<ThemeResult>, RuntimeError> {
        let (version, _node) = match self.prepare() {
            Ok(ready) => ready,
            Err(u) => return Ok(Evaluation::Unresolved(u)),
        };
        let css_entry = match Self::require_css_entry(version, sources) {
            Ok(entry) => entry,
            Err(u) => return Ok(Evaluation::Unresolved(u)),
        };
        self.notify(version, sources);
        let request = match version {
            TailwindVersion::V3 => Request::V3Theme {
                project_root: path_text(&self.project_root),
                config_path: sources.config_path.as_deref().map(path_text),
            },
            TailwindVersion::V4 => Request::V4Theme {
                project_root: path_text(&self.project_root),
                css_entry_path: css_entry.unwrap_or_default(),
            },
        };
        let response = ok_response(self.exec().run(&self.project_root, &request)?)?;
        let theme: BTreeMap<String, String> = response
            .theme
            .ok_or_else(|| RuntimeError::BadResponse("no `theme` object".to_owned()))?;
        Ok(Evaluation::Resolved(ThemeResult {
            version,
            config_path: response.config_path,
            theme,
        }))
    }

    /// The presence report behind `crunk doctor`: node, the project's tailwindcss, and (when
    /// `sources` name something to probe) whether the helper actually runs.
    pub fn doctor(&self, sources: &Sources) -> DoctorReport {
        doctor::report(self, sources)
    }
}

/// The response when the helper said `ok`, else the helper's own error.
fn ok_response(response: Response) -> Result<Response, RuntimeError> {
    if response.ok {
        Ok(response)
    } else {
        let error = response.error.unwrap_or_else(|| "(no message)".to_owned());
        tracing::warn!(%error, "tailwind helper reported an error");
        Err(RuntimeError::HelperReported { error })
    }
}
