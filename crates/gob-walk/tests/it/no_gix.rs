//! The read-only analysis crates stay free of gix; only gob-git and its callers carry it.

// frob:ticket 01M4CTE0GYDX0XW64JRNF2ZMQG

use std::process::Command;

// frob:tests crates/gob-walk/src/content.rs::ContentBackend
#[test]
fn analysis_crates_have_no_gix_or_gob_git_in_their_normal_tree() {
    let cargo = std::env::var("CARGO").unwrap_or_else(|_| "cargo".into());
    for pkg in ["gob-walk", "gob-ir", "gob-symbols", "grimble-model"] {
        let out = Command::new(&cargo)
            .args(["tree", "-p", pkg, "-e", "normal", "--prefix", "none"])
            .current_dir(env!("CARGO_MANIFEST_DIR"))
            .output()
            .expect("cargo tree runs");
        assert!(out.status.success(), "cargo tree -p {pkg} failed");
        let text = String::from_utf8_lossy(&out.stdout);
        let bad: Vec<&str> = text
            .lines()
            .filter(|l| l.starts_with("gix") || l.starts_with("gob-git"))
            .collect();
        assert!(bad.is_empty(), "{pkg} still depends on {bad:?}");
    }
}
