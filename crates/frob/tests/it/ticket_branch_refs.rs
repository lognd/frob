//! Orphan-mode readiness: goway must sync the ticket branch once `ref_mode = "orphan"` (DT04).
// frob:ticket 01M5CY4615SPGHB682NX2S3S24

use std::path::PathBuf;

/// The repository root, two levels above this crate.
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// Value of `key` in the `[tickets]` table of `frob.toml` text, if set.
fn tickets_value(toml: &str, key: &str) -> Option<String> {
    let mut in_tickets = false;
    for line in toml.lines().map(str::trim) {
        if line.starts_with('[') {
            in_tickets = line == "[tickets]";
        } else if in_tickets
            && let Some((k, v)) = line.split_once('=')
            && k.trim() == key
        {
            return Some(v.trim().trim_matches('"').to_owned());
        }
    }
    None
}

#[test]
fn goway_syncs_the_ticket_branch_in_orphan_mode() {
    let root = repo_root();
    let frob = std::fs::read_to_string(root.join("frob.toml")).expect("frob.toml");
    if tickets_value(&frob, "ref_mode").as_deref() != Some("orphan") {
        return;
    }
    let branch = tickets_value(&frob, "branch").unwrap_or_else(|| "frob-tickets".to_owned());
    let goway = std::fs::read_to_string(root.join("goway.toml")).expect("goway.toml");
    for want in [
        format!("refs/heads/{branch}"),
        format!("refs/remotes/origin/{branch}"),
    ] {
        assert!(
            goway.contains(&format!("\"{want}\"")),
            "goway.toml with_refs must list {want} in orphan mode"
        );
    }
}

#[test]
fn tickets_value_reads_the_tickets_table_only() {
    let toml = "[other]\nbranch = \"x\"\n[tickets]\nbranch = \"t\"\n";
    assert_eq!(tickets_value(toml, "branch").as_deref(), Some("t"));
    assert_eq!(tickets_value(toml, "ref_mode"), None);
}
