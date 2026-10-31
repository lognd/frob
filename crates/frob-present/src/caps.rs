//! Capability detection: a pure function over an injected environment and stream facts.

use std::collections::BTreeMap;

use tracing::debug;

const DEFAULT_WIDTH: u16 = 80;

/// An injected snapshot of environment variables.
#[derive(Debug, Clone, Default)]
pub struct EnvSnapshot {
    vars: BTreeMap<String, String>,
}

impl EnvSnapshot {
    /// Build from explicit pairs (tests and callers with their own source).
    pub fn from_pairs<K: Into<String>, V: Into<String>>(
        pairs: impl IntoIterator<Item = (K, V)>,
    ) -> Self {
        Self {
            vars: pairs
                .into_iter()
                .map(|(k, v)| (k.into(), v.into()))
                .collect(),
        }
    }

    /// Snapshot the relevant variables of the running process.
    pub fn from_process() -> Self {
        const KEYS: [&str; 7] = [
            "NO_COLOR",
            "CLICOLOR_FORCE",
            "FORCE_COLOR",
            "TERM",
            "CI",
            "COLUMNS",
            "FROB_ASCII",
        ];
        Self::from_pairs(
            KEYS.iter()
                .filter_map(|k| std::env::var(k).ok().map(|v| (*k, v))),
        )
    }

    fn get(&self, key: &str) -> Option<&str> {
        self.vars.get(key).map(String::as_str)
    }

    fn non_empty(&self, key: &str) -> bool {
        self.get(key).is_some_and(|v| !v.is_empty())
    }

    fn truthy(&self, key: &str) -> bool {
        self.get(key).is_some_and(|v| !v.is_empty() && v != "0")
    }
}

/// Which streams are terminals, judged separately (the caller asks `IsTerminal`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct StreamFacts {
    /// Stdout is a terminal.
    pub stdout_tty: bool,
    /// Stderr is a terminal.
    pub stderr_tty: bool,
    /// Terminal width in columns if the caller measured it.
    pub width: Option<u16>,
}

/// What one stream may do.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct StreamCaps {
    /// The stream is a terminal.
    pub tty: bool,
    /// Escape-sequence colour is allowed.
    pub color: bool,
}

/// Derived capabilities for both streams.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Capabilities {
    /// Stdout facts.
    pub stdout: StreamCaps,
    /// Stderr facts.
    pub stderr: StreamCaps,
    /// Stderr may redraw a live widget (TTY, not dumb, not CI).
    pub interactive: bool,
    /// Running under CI.
    pub ci: bool,
    /// Use ASCII glyphs.
    pub ascii: bool,
    /// Columns available.
    pub width: u16,
}

impl Capabilities {
    /// Detect capabilities from an environment snapshot and stream facts.
    pub fn detect(env: &EnvSnapshot, streams: StreamFacts) -> Self {
        let dumb = env.get("TERM").map_or(cfg!(unix), |t| t == "dumb");
        let no_color = env.non_empty("NO_COLOR");
        let forced = env.truthy("CLICOLOR_FORCE") || env.truthy("FORCE_COLOR");
        let ci = env.get("CI").is_some_and(|v| v != "0" && v != "false");
        let color_for = |tty: bool| !no_color && !dumb && (tty || forced);
        let width = streams
            .width
            .or_else(|| env.get("COLUMNS").and_then(|c| c.parse().ok()))
            .unwrap_or(DEFAULT_WIDTH);
        let caps = Self {
            stdout: StreamCaps {
                tty: streams.stdout_tty,
                color: color_for(streams.stdout_tty),
            },
            stderr: StreamCaps {
                tty: streams.stderr_tty,
                color: color_for(streams.stderr_tty),
            },
            interactive: streams.stderr_tty && !dumb && !ci,
            ci,
            ascii: env.non_empty("FROB_ASCII"),
            width,
        };
        debug!(?caps, dumb, no_color, forced, "capabilities detected");
        caps
    }
}
