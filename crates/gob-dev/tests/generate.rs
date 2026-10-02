//! Determinism, check-mode and orphan-page tests for the generator.

use std::collections::BTreeSet;
use std::path::Path;

use gob_dev::{Kind, Mode, apply, generate, workspace_root};

fn crates_dir() -> std::path::PathBuf {
    workspace_root().join("crates")
}

fn tree(root: &Path) -> Vec<(String, String)> {
    let mut out = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir).expect("read dir") {
            let path = entry.expect("entry").path();
            if path.is_dir() {
                stack.push(path);
            } else {
                let rel = path
                    .strip_prefix(root)
                    .expect("under root")
                    .to_string_lossy()
                    .replace('\\', "/");
                out.push((rel, std::fs::read_to_string(&path).expect("read")));
            }
        }
    }
    out.sort();
    out
}

#[test]
fn output_is_deterministic_and_check_passes() {
    let a = tempfile::tempdir().expect("tmp");
    let b = tempfile::tempdir().expect("tmp");
    apply(a.path(), &generate(Kind::All, &crates_dir()), Mode::Write).expect("write a");
    apply(b.path(), &generate(Kind::All, &crates_dir()), Mode::Write).expect("write b");
    let (ta, tb) = (tree(a.path()), tree(b.path()));
    assert!(!ta.is_empty());
    assert_eq!(ta, tb, "two runs must be byte-identical");
    assert!(ta.iter().all(|(_, text)| text.is_ascii()));
    let checked = apply(a.path(), &generate(Kind::All, &crates_dir()), Mode::Check).expect("check");
    assert_eq!(checked.differing, 0);
}

#[test]
fn check_reports_stale_and_missing_files_without_writing() {
    let dir = tempfile::tempdir().expect("tmp");
    let files = generate(Kind::All, &crates_dir());
    apply(dir.path(), &files, Mode::Write).expect("write");
    let stale = dir.path().join("docs/reference/directives.md");
    std::fs::write(&stale, "stale\n").expect("stale");
    let missing = dir.path().join("docs/schemas/envelope.json");
    std::fs::remove_file(&missing).expect("remove");
    let r = apply(dir.path(), &files, Mode::Check).expect("check");
    assert_eq!(r.differing, 2);
    assert_eq!(std::fs::read_to_string(&stale).expect("read"), "stale\n");
    assert!(!missing.exists(), "check mode writes nothing");
}

#[test]
fn every_rule_has_a_page_and_every_page_a_rule() {
    let files = generate(Kind::Rules, &crates_dir());
    let pages: BTreeSet<String> = files
        .iter()
        .filter_map(|f| f.path.strip_prefix("docs/reference/rules/"))
        .filter_map(|n| n.strip_suffix(".md"))
        .filter(|n| *n != "README")
        .map(str::to_owned)
        .collect();
    let rules: BTreeSet<String> = gob_rules::Registry::global()
        .iter()
        .map(|m| m.id.to_owned())
        .collect();
    assert!(!rules.is_empty());
    assert_eq!(pages, rules);
}

#[test]
fn committed_pages_have_no_orphans_on_disk() {
    let dir = workspace_root().join("docs/reference/rules");
    let rules: BTreeSet<String> = gob_rules::Registry::global()
        .iter()
        .map(|m| format!("{}.md", m.id))
        .collect();
    for entry in std::fs::read_dir(&dir).expect("rules dir exists once generated") {
        let name = entry
            .expect("entry")
            .file_name()
            .to_string_lossy()
            .into_owned();
        assert!(
            name == "README.md" || rules.contains(&name),
            "orphan page {name}"
        );
    }
}
