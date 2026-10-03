//! Every tracked path must be checkable-out on Windows: no reserved device name, no reserved character.
// frob:ticket 01M41MWVAZM5SVK5A91M4WWW00

use std::path::Path;
use std::process::Command;

const RESERVED_CHARS: &[char] = &['<', '>', ':', '"', '|', '?', '*'];

/// Whether `component` is a Windows device name (`CON`, `NUL`, `COM1`..`LPT9`, ...), ignoring case and any extension.
fn is_reserved_name(component: &str) -> bool {
    let stem = component.split('.').next().unwrap_or(component);
    let stem = stem.to_ascii_uppercase();
    matches!(stem.as_str(), "CON" | "PRN" | "AUX" | "NUL")
        || ["COM", "LPT"].iter().any(|p| {
            stem.strip_prefix(p)
                .is_some_and(|n| matches!(n, "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"))
        })
}

/// The reason `path` cannot exist on Windows, if any.
fn violation(path: &str) -> Option<String> {
    if let Some(c) = path.chars().find(|c| RESERVED_CHARS.contains(c)) {
        return Some(format!("reserved character `{c}`"));
    }
    path.split('/')
        .find(|part| is_reserved_name(part))
        .map(|part| format!("reserved device name `{part}`"))
}

#[test]
fn no_tracked_path_uses_a_windows_reserved_name_or_character() {
    // frob:tests crates/grimble-model/tests/tracked_paths.rs::violation
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let out = Command::new("git")
        .args(["ls-files", "-z"])
        .current_dir(&root)
        .output()
        .expect("run git ls-files");
    assert!(out.status.success(), "git ls-files failed");
    let listing = String::from_utf8(out.stdout).expect("utf-8 paths");
    let bad: Vec<String> = listing
        .split('\0')
        .filter(|p| !p.is_empty())
        .filter_map(|p| violation(p).map(|why| format!("{p}: {why}")))
        .collect();
    assert!(
        bad.is_empty(),
        "paths invalid on Windows:\n{}",
        bad.join("\n")
    );
}

#[test]
fn the_detector_catches_the_known_bad_shapes() {
    // frob:tests crates/grimble-model/tests/tracked_paths.rs::violation
    for bad in [
        "a/nul.grmb",
        "CON",
        "x/Aux.txt",
        "lpt9.md",
        "com1.rs",
        "a/b?.txt",
        "a:b",
    ] {
        assert!(violation(bad).is_some(), "{bad}");
    }
    for ok in [
        "a/nul-byte.grmb",
        "console.rs",
        "com10.rs",
        "com0.rs",
        "a/b.txt",
    ] {
        assert!(violation(ok).is_none(), "{ok}");
    }
}
