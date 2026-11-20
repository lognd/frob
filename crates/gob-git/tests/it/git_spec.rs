//! The one `git` spec builder, and the ratchet that keeps every other crate on it.
#![allow(
    clippy::disallowed_methods,
    reason = "a workspace-wide source scan reads the disk, not a walked Core"
)]

// frob:ticket 01M7X35W2WATD06TP58JC8MS7H
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::Program;

/// Source files outside gob-git that still build a `Program::Git` spec by hand. Each row is debt:
/// the crate cannot depend on gob-git without pulling gix into a lightweight crate.
const ALLOWED: &[&str] = &[
    // crunk-check does not depend on gob-git (gix) for four one-line probes.
    "crunk-check/src/review.rs",
    // gob-trust sits below gob-git's dependency tier.
    "gob-trust/src/guard.rs",
];

// frob:tests crates/gob-git/src/git_spec.rs::git_spec
#[test]
fn git_spec_is_a_captured_git_run_bounded_by_its_timeout() {
    let spec = gob_git::git_spec(Path::new("work"), ["log", "-1"], Duration::from_secs(7));
    assert_eq!(spec.program, Program::Git);
    assert_eq!(spec.args, ["log", "-1"]);
    assert_eq!(spec.cwd.as_deref(), Some(Path::new("work")));
    assert!(spec.env.is_empty());
    assert_eq!(spec.timeout, Duration::from_secs(7));
    assert!(spec.capture);
}

// frob:tests crates/gob-git/src/git_spec.rs::git_spec
#[test]
fn git_spec_takes_owned_arguments_too() {
    let owned = gob_git::git_spec(Path::new("."), vec!["status".to_owned()], Duration::ZERO);
    assert_eq!(owned.args, ["status"]);
}

fn rust_sources(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            rust_sources(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

/// True when the text builds a spec field `program: [gob_exec::]Program::Git`.
fn builds_git_spec(text: &str) -> bool {
    text.lines().any(|l| {
        let l = l.trim();
        l.starts_with("program: Program::Git") || l.starts_with("program: gob_exec::Program::Git")
    })
}

#[test]
fn no_git_spec_is_built_outside_gob_git() {
    let crates = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let mut offenders = Vec::new();
    let mut seen_allowed = Vec::new();
    for entry in fs::read_dir(&crates).expect("crates dir").flatten() {
        let krate = entry.path();
        if krate.ends_with("gob-git") {
            continue;
        }
        let mut files = Vec::new();
        rust_sources(&krate.join("src"), &mut files);
        for file in files {
            let text = fs::read_to_string(&file).unwrap_or_default();
            if !builds_git_spec(&text) {
                continue;
            }
            let rel = file.strip_prefix(&crates).expect("under crates");
            let allowed = ALLOWED.iter().find(|a| rel.ends_with(a));
            match allowed {
                Some(a) => seen_allowed.push(*a),
                None => offenders.push(rel.to_path_buf()),
            }
        }
    }
    assert!(
        offenders.is_empty(),
        "build the spec with gob_git::git_spec instead: {offenders:?}"
    );
    for a in ALLOWED {
        assert!(
            seen_allowed.contains(a),
            "{a} no longer builds a git spec by hand: delete its row from ALLOWED"
        );
    }
}
