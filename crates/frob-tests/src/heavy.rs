//! The heavy-command profile: commands that telemetry shows run long or grow the disk a lot.
//!
//! `frob agent heavy` appends one `kind=command` row per run to `.frob/telemetry.jsonl` (wall time and
//! peak disk growth). `frob agent profile` folds those rows into `heavy-profile.toml`, a committed file
//! the `pre-bash` hook reads and `TEST002` checks. The fold is deterministic: the worst observed value per
//! command key, sorted keys, no timestamps, so the same rows always give the same bytes.

// frob:ticket 01M4P2N1XMDZAGS1EAZPR6WQMQ

use gob_path::Shown;
use std::collections::BTreeMap;
use std::path::Path;

use serde::{Deserialize, Serialize};

/// File name of the committed profile, at the repository root.
pub const PROFILE_FILE: &str = "heavy-profile.toml";

/// Path of the local telemetry log, relative to the repository root.
pub const TELEMETRY_FILE: &str = ".frob/telemetry.jsonl";

/// Why the profile could not be read, derived or written.
#[derive(Debug, thiserror::Error)]
pub enum HeavyError {
    /// A file could not be read or written.
    #[error("{path}: {source}")]
    Io {
        /// The file involved.
        path: String,
        /// The underlying error.
        source: std::io::Error,
    },
    /// The profile file is not valid TOML of the expected shape.
    #[error("{PROFILE_FILE} is not a valid heavy profile: {0}")]
    Parse(String),
    /// The profile could not be rendered as TOML.
    #[error("cannot render the heavy profile: {0}")]
    Render(String),
    /// There are no command rows to derive a profile from.
    #[error("no command rows in {TELEMETRY_FILE}; run commands through `frob agent heavy` first")]
    NoTelemetry,
}

/// The limits above which a command counts as heavy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Thresholds {
    /// Wall time in milliseconds.
    pub wall_ms: u64,
    /// Peak disk growth in bytes.
    pub disk_bytes: u64,
}

/// The worst observed cost of one command key.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Cost {
    /// Longest wall time seen, in milliseconds.
    pub wall_ms: u64,
    /// Largest disk growth seen, in bytes.
    pub disk_bytes: u64,
}

/// The committed profile: the thresholds it was derived with and each heavy command key.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Profile {
    /// The limits the commands were judged against.
    pub thresholds: Thresholds,
    /// Heavy command keys (`cargo test`), with their worst observed cost.
    #[serde(default)]
    pub commands: BTreeMap<String, Cost>,
}

/// One `kind=command` telemetry row.
#[derive(Debug, Clone, Deserialize)]
struct Row {
    kind: String,
    #[serde(default)]
    command: String,
    #[serde(default)]
    wall_ms: u64,
    #[serde(default)]
    disk_bytes: u64,
}

/// The key a command is profiled under: its first word plus its first non-flag second word.
#[must_use]
pub fn command_key(words: &[String]) -> String {
    let mut it = words.iter().map(String::as_str);
    let first = it.next().unwrap_or_default();
    match it.next().filter(|w| !w.starts_with('-')) {
        Some(second) => format!("{first} {second}"),
        None => first.to_owned(),
    }
}

/// The worst cost per command key among the rows of `text`; unparsable lines are skipped.
fn fold(text: &str) -> BTreeMap<String, Cost> {
    let mut worst: BTreeMap<String, Cost> = BTreeMap::new();
    for line in text.lines() {
        let Ok(row) = serde_json::from_str::<Row>(line) else {
            continue;
        };
        if row.kind != "command" || row.command.is_empty() {
            continue;
        }
        let cost = worst.entry(row.command).or_insert(Cost {
            wall_ms: 0,
            disk_bytes: 0,
        });
        cost.wall_ms = cost.wall_ms.max(row.wall_ms);
        cost.disk_bytes = cost.disk_bytes.max(row.disk_bytes);
    }
    worst
}

/// The profile telemetry `text` implies under `limits`, or `None` when it holds no command rows.
#[must_use]
pub fn derive(text: &str, limits: Thresholds) -> Option<Profile> {
    let worst = fold(text);
    if worst.is_empty() {
        return None;
    }
    let commands = worst
        .into_iter()
        .filter(|(_, c)| c.wall_ms > limits.wall_ms || c.disk_bytes > limits.disk_bytes)
        .collect();
    Some(Profile {
        thresholds: limits,
        commands,
    })
}

/// Read the local telemetry text under `root`; an absent log is empty text.
fn read_telemetry(root: &Path) -> Result<String, HeavyError> {
    let path = root.join(TELEMETRY_FILE);
    match std::fs::read_to_string(&path) {
        Ok(t) => Ok(t),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(String::new()),
        Err(source) => Err(HeavyError::Io {
            path: Shown::of(&path).to_string(),
            source,
        }),
    }
}

/// Load the committed profile under `root`; `Ok(None)` when none exists.
///
/// # Errors
///
/// [`HeavyError`] when the file exists but cannot be read or parsed.
pub fn load(root: &Path) -> Result<Option<Profile>, HeavyError> {
    let path = root.join(PROFILE_FILE);
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(source) => {
            return Err(HeavyError::Io {
                path: Shown::of(&path).to_string(),
                source,
            });
        }
    };
    toml::from_str(&text)
        .map(Some)
        .map_err(|e| HeavyError::Parse(e.to_string()))
}

/// Derive the profile from local telemetry under `limits` and write it to `heavy-profile.toml`.
///
/// # Errors
///
/// [`HeavyError::NoTelemetry`] when there are no command rows, or an I/O or render error.
pub fn refresh(root: &Path, limits: Thresholds) -> Result<Profile, HeavyError> {
    let text = read_telemetry(root)?;
    let profile = derive(&text, limits).ok_or(HeavyError::NoTelemetry)?;
    let body = toml::to_string_pretty(&profile).map_err(|e| HeavyError::Render(e.to_string()))?;
    let path = root.join(PROFILE_FILE);
    std::fs::write(&path, body).map_err(|source| HeavyError::Io {
        path: Shown::of(&path).to_string(),
        source,
    })?;
    tracing::info!(commands = profile.commands.len(), "heavy profile refreshed");
    Ok(profile)
}

/// Why `profile` is stale, or `None` when it is current.
///
/// Stale means the thresholds differ from `limits`, or local telemetry exists and implies a different
/// set of heavy command keys. Telemetry is local state, so a clean checkout without it is never stale
/// on the second count.
#[must_use]
pub fn staleness(profile: &Profile, telemetry: &str, limits: Thresholds) -> Option<String> {
    if profile.thresholds != limits {
        return Some(format!(
            "thresholds {:?} differ from the configured {:?}",
            profile.thresholds, limits
        ));
    }
    let fresh = derive(telemetry, limits)?;
    let have: Vec<&String> = profile.commands.keys().collect();
    let want: Vec<&String> = fresh.commands.keys().collect();
    (have != want).then(|| format!("profile lists {have:?} but telemetry implies {want:?}"))
}

/// Why the profile under `root` is stale against `limits`; `Ok(None)` when current or absent.
///
/// # Errors
///
/// [`HeavyError`] when the profile or telemetry cannot be read.
pub fn check(root: &Path, limits: Option<Thresholds>) -> Result<Option<String>, HeavyError> {
    let Some(profile) = load(root)? else {
        return Ok(None);
    };
    let telemetry = read_telemetry(root)?;
    Ok(staleness(
        &profile,
        &telemetry,
        limits.unwrap_or(profile.thresholds),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    const LIMITS: Thresholds = Thresholds {
        wall_ms: 1000,
        disk_bytes: 1_000_000,
    };

    fn rows() -> String {
        [
            r#"{"kind":"command","command":"cargo test","wall_ms":5000,"disk_bytes":10}"#,
            r#"{"kind":"command","command":"cargo test","wall_ms":200,"disk_bytes":10}"#,
            r#"{"kind":"command","command":"ls","wall_ms":5,"disk_bytes":0}"#,
            r#"{"kind":"command","command":"cargo build","wall_ms":10,"disk_bytes":9000000}"#,
            r#"{"kind":"guard","guard":"pre-read"}"#,
        ]
        .join("\n")
    }

    // frob:tests crates/frob-tests/src/heavy.rs::derive
    #[test]
    fn derive_lists_commands_over_either_threshold() {
        let p = derive(&rows(), LIMITS).expect("rows");
        let keys: Vec<&str> = p.commands.keys().map(String::as_str).collect();
        assert_eq!(keys, ["cargo build", "cargo test"]);
        assert_eq!(p.commands["cargo test"].wall_ms, 5000);
    }

    // frob:tests crates/frob-tests/src/heavy.rs::derive
    #[test]
    fn derive_is_deterministic_for_reordered_rows() {
        let text = rows();
        let mut lines: Vec<&str> = text.lines().collect();
        let a = derive(&lines.join("\n"), LIMITS);
        lines.reverse();
        assert_eq!(a, derive(&lines.join("\n"), LIMITS));
    }

    // frob:tests crates/frob-tests/src/heavy.rs::derive
    #[test]
    fn derive_without_command_rows_is_none() {
        assert_eq!(derive(r#"{"kind":"guard"}"#, LIMITS), None);
    }

    // frob:tests crates/frob-tests/src/heavy.rs::command_key
    #[test]
    fn command_key_is_program_and_subcommand() {
        let w = |s: &str| s.split(' ').map(str::to_owned).collect::<Vec<_>>();
        assert_eq!(command_key(&w("cargo test -p frob")), "cargo test");
        assert_eq!(command_key(&w("cargo --version")), "cargo");
    }

    // frob:tests crates/frob-tests/src/heavy.rs::refresh
    #[test]
    fn refresh_writes_a_profile_that_loads_back() {
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::create_dir_all(dir.path().join(".frob")).expect("mkdir");
        std::fs::write(dir.path().join(TELEMETRY_FILE), rows()).expect("telemetry");
        let written = refresh(dir.path(), LIMITS).expect("refresh");
        assert_eq!(load(dir.path()).expect("load"), Some(written));
    }

    // frob:tests crates/frob-tests/src/heavy.rs::refresh
    #[test]
    fn refresh_refuses_when_there_is_no_telemetry() {
        let dir = tempfile::tempdir().expect("tempdir");
        assert!(matches!(
            refresh(dir.path(), LIMITS),
            Err(HeavyError::NoTelemetry)
        ));
    }

    // frob:tests crates/frob-tests/src/heavy.rs::staleness
    #[test]
    fn staleness_flags_a_command_set_that_telemetry_disagrees_with() {
        let mut p = derive(&rows(), LIMITS).expect("rows");
        assert_eq!(staleness(&p, &rows(), LIMITS), None);
        p.commands.remove("cargo build");
        assert!(staleness(&p, &rows(), LIMITS).is_some());
    }

    // frob:tests crates/frob-tests/src/heavy.rs::staleness
    #[test]
    fn staleness_flags_changed_thresholds_without_telemetry() {
        let p = derive(&rows(), LIMITS).expect("rows");
        let other = Thresholds {
            wall_ms: 1,
            ..LIMITS
        };
        assert!(staleness(&p, "", other).is_some());
        assert_eq!(staleness(&p, "", LIMITS), None);
    }
}
