//! The first-run notice: running the project's Tailwind executes the project's code.
//!
//! Before the helper first runs a given config for a given project on this machine, a prominent
//! notice names the config, the node binary and the opt-outs (security.md section 2.3: the
//! helper is a `runs-repository-code` program). The acknowledgement is recorded under the
//! user's state directory (never inside the repository), so later runs stay quiet until the
//! resolved config path changes.

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

use std::path::{Path, PathBuf};

use gob_walk::Digest;
use serde::{Deserialize, Serialize};

/// Environment variable that suppresses the printed notice (the acknowledgement is still kept).
pub const QUIET_ENV: &str = "CRUNK_QUIET_EXEC_NOTICE";

/// The recorded acknowledgement of one project.
#[derive(Debug, Serialize, Deserialize)]
struct Ack {
    config_path: String,
}

/// The user's crunk state directory: `$XDG_STATE_HOME/crunk`, else `~/.local/state/crunk`, else
/// (Windows) `%LOCALAPPDATA%\crunk`; `None` when none of them is known.
pub fn state_base() -> Option<PathBuf> {
    state_base_from(
        std::env::var_os("XDG_STATE_HOME").map(PathBuf::from),
        std::env::var_os("HOME").map(PathBuf::from),
        std::env::var_os("LOCALAPPDATA").map(PathBuf::from),
    )
}

/// [`state_base`] over explicit inputs (an empty value counts as unset).
pub fn state_base_from(
    xdg_state_home: Option<PathBuf>,
    home: Option<PathBuf>,
    local_app_data: Option<PathBuf>,
) -> Option<PathBuf> {
    let nonempty = |p: Option<PathBuf>| p.filter(|p| !p.as_os_str().is_empty());
    if let Some(xdg) = nonempty(xdg_state_home) {
        return Some(xdg.join("crunk"));
    }
    if let Some(home) = nonempty(home) {
        return Some(home.join(".local").join("state").join("crunk"));
    }
    nonempty(local_app_data).map(|d| d.join("crunk"))
}

/// The notice text for running `config_path` with `node_binary`.
pub fn notice_text(config_path: &Path, node_binary: &str) -> String {
    format!(
        "crunk: running this project's Tailwind config and plugins with node\n  \
         config: {}\n  node:   {node_binary}\n  \
         opt out with --static or `[tailwind] engine = \"static\"`\n  \
         see the security notes before running crunk check on an untrusted repository",
        config_path.display()
    )
}

/// Where the acknowledgement of `project_root` lives under `state`.
fn ack_path(state: &Path, project_root: &Path) -> PathBuf {
    let resolved = gob_exec::canonical(project_root).unwrap_or_else(|_| project_root.to_path_buf());
    let key = Digest::of(resolved.to_string_lossy().as_bytes()).to_string();
    state
        .join("exec-notice")
        .join(format!("{}.json", &key[..16]))
}

/// Decide whether the notice is due for `config_path`, record the acknowledgement, and return
/// the text to show (`None` when already acknowledged for this exact config, or when `quiet`).
///
/// The record is written even when `quiet`, so unsetting the variable later does not replay it.
pub fn first_run(
    state: &Path,
    project_root: &Path,
    config_path: &Path,
    node_binary: &str,
    quiet: bool,
) -> Option<String> {
    let record = ack_path(state, project_root);
    let resolved = gob_exec::canonical(config_path).unwrap_or_else(|_| config_path.to_path_buf());
    let resolved = resolved.to_string_lossy().into_owned();
    let previous = std::fs::read_to_string(&record)
        .ok()
        .and_then(|t| serde_json::from_str::<Ack>(&t).ok());
    if previous.is_some_and(|a| a.config_path == resolved) {
        tracing::debug!(root = %project_root.display(), "exec notice already acknowledged");
        return None;
    }
    let body = serde_json::to_vec(&Ack {
        config_path: resolved,
    });
    match body {
        Ok(bytes) => {
            let written = record
                .parent()
                .map_or(Ok(()), std::fs::create_dir_all)
                .and_then(|()| gob_fs::write_atomic(&record, &bytes));
            match written {
                Ok(()) => tracing::info!(record = %record.display(), "exec notice acknowledged"),
                Err(e) => {
                    tracing::warn!(record = %record.display(), error = %e, "cannot record the exec notice");
                }
            }
        }
        Err(e) => tracing::warn!(error = %e, "cannot encode the exec notice record"),
    }
    if quiet {
        tracing::info!("exec notice suppressed by {QUIET_ENV}=1");
        return None;
    }
    Some(notice_text(config_path, node_binary))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-tailwind/src/runtime/notice.rs::state_base
    #[test]
    fn the_default_state_base_is_under_crunk_when_any_home_is_known() {
        if let Some(base) = state_base() {
            assert_eq!(base.file_name().and_then(|n| n.to_str()), Some("crunk"));
        }
    }

    // frob:tests crates/crunk-tailwind/src/runtime/notice.rs::state_base_from
    #[test]
    fn state_base_prefers_xdg_then_home_then_local_app_data() {
        let p = |s: &str| Some(PathBuf::from(s));
        assert_eq!(state_base_from(p("/x"), p("/h"), p("/l")), p("/x/crunk"));
        assert_eq!(
            state_base_from(None, p("/h"), p("/l")),
            p("/h/.local/state/crunk")
        );
        assert_eq!(state_base_from(p(""), None, p("/l")), p("/l/crunk"));
        assert_eq!(state_base_from(None, None, None), None);
    }

    // frob:tests crates/crunk-tailwind/src/runtime/notice.rs::first_run
    #[test]
    fn the_notice_shows_once_per_config_and_again_when_the_config_changes() {
        let state = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();
        let a = project.path().join("a.config.js");
        let b = project.path().join("b.config.js");
        std::fs::write(&a, "").unwrap();
        std::fs::write(&b, "").unwrap();
        let shown = first_run(state.path(), project.path(), &a, "node", false).unwrap();
        assert!(
            shown.contains("a.config.js") && shown.contains("node") && shown.contains("--static")
        );
        assert!(first_run(state.path(), project.path(), &a, "node", false).is_none());
        assert!(first_run(state.path(), project.path(), &b, "node", false).is_some());
    }

    // frob:tests crates/crunk-tailwind/src/runtime/notice.rs::first_run
    #[test]
    fn quiet_suppresses_the_text_but_still_records_the_acknowledgement() {
        let state = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();
        let a = project.path().join("a.config.js");
        std::fs::write(&a, "").unwrap();
        assert!(first_run(state.path(), project.path(), &a, "node", true).is_none());
        assert!(first_run(state.path(), project.path(), &a, "node", false).is_none());
    }
}
