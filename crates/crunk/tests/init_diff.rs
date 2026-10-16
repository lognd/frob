//! `crunk diff OTHER`: added, removed and changed tokens between two spec directories.

// frob:ticket 01M43ATD7ZGTNCY5036AYEJR7P

use std::path::Path;

use gob_cli::run_for_test;

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

fn spec(dir: &Path, name: &str, palette: &str, font: &str) {
    let d = dir.join(name);
    std::fs::create_dir_all(&d).expect("dir");
    let text = format!(
        "[project]\ncss_root = \"styles\"\ntokens_file = \"tokens.css\"\nroot_font_size = 16\n\n\
         [palette]\n{palette}\n[scales]\nspacing = [0, 8]\nfont_sizes = [16]\nradii = [0]\n\n\
         [typography]\nfamilies = [\"{font}\"]\nweights = [400]\n\n[org]\nbuckets = [\"base\"]\n"
    );
    std::fs::write(d.join("crunk.toml"), text).expect("spec");
}

// frob:tests crates/crunk/src/diff.rs::Diff
#[test]
fn diff_lists_added_removed_and_changed_tokens() {
    let dir = tempfile::tempdir().expect("tempdir");
    spec(
        dir.path(),
        "a",
        "ink = \"#111111\"\nold = \"#222222\"\n",
        "Inter",
    );
    spec(
        dir.path(),
        "b",
        "ink = \"#111111\"\nnew = \"#333333\"\n",
        "Mono",
    );
    let (code, out, err) = crunk(&dir.path().join("a"), &["diff", "../b", "--format", "text"]);
    assert_eq!(code, 0, "{out} {err}");
    assert!(out.contains("+ --color-new #333333"), "{out}");
    assert!(out.contains("- --color-old #222222"), "{out}");
    assert!(out.contains("~ --font-family-base"), "{out}");
    assert!(out.contains("Inter") && out.contains("-> Mono"), "{out}");
    assert!(
        !out.contains("--color-ink"),
        "unchanged token listed: {out}"
    );
}

// frob:tests crates/crunk/src/diff.rs::diff
#[test]
fn identical_specs_report_no_differences() {
    let dir = tempfile::tempdir().expect("tempdir");
    spec(dir.path(), "a", "ink = \"#111111\"\n", "Inter");
    spec(dir.path(), "b", "ink = \"#111111\"\n", "Inter");
    let (code, out, _) = crunk(&dir.path().join("a"), &["diff", "../b", "--format", "text"]);
    assert_eq!(code, 0);
    assert!(out.contains("no differences"), "{out}");
}
