//! The evidence and land crates write events only through `Ledger::append`.

use std::path::Path;

fn sources(crate_dir: &str) -> Vec<(String, String)> {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join(crate_dir)
        .join("src");
    let mut out = Vec::new();
    let mut stack = vec![dir];
    while let Some(d) = stack.pop() {
        for entry in std::fs::read_dir(&d).expect("read_dir") {
            let path = entry.expect("entry").path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().is_some_and(|e| e == "rs") {
                let text = std::fs::read_to_string(&path).expect("read");
                out.push((path.display().to_string(), text));
            }
        }
    }
    assert!(!out.is_empty(), "no sources under {crate_dir}");
    out
}

// frob:ticket 01M3WYJ81430D3D5QSNCFM8QB0
#[test]
fn evidence_and_land_never_call_commit_paths() {
    for krate in ["frob-evidence", "frob-land"] {
        for (path, text) in sources(krate) {
            assert!(
                !text.contains("commit_paths"),
                "{path} calls commit_paths directly; use Ledger::append"
            );
        }
    }
}
