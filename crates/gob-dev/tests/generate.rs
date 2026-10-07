//! Determinism, check-mode and orphan-page tests for the generator.

use std::collections::BTreeSet;
use std::path::Path;

use gob_dev::{Kind, Mode, apply, generate, workspace_root};

fn crates_dir() -> std::path::PathBuf {
    workspace_root().expect("workspace root").join("crates")
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
    apply(
        a.path(),
        &generate(Kind::All, &crates_dir()).expect("generate"),
        Mode::Write,
    )
    .expect("write a");
    apply(
        b.path(),
        &generate(Kind::All, &crates_dir()).expect("generate"),
        Mode::Write,
    )
    .expect("write b");
    let (ta, tb) = (tree(a.path()), tree(b.path()));
    assert!(!ta.is_empty());
    assert_eq!(ta, tb, "two runs must be byte-identical");
    assert!(ta.iter().all(|(_, text)| text.is_ascii()));
    let checked = apply(
        a.path(),
        &generate(Kind::All, &crates_dir()).expect("generate"),
        Mode::Check,
    )
    .expect("check");
    assert_eq!(checked.differing, 0);
}

#[test]
fn check_reports_stale_and_missing_files_without_writing() {
    let dir = tempfile::tempdir().expect("tmp");
    let files = generate(Kind::All, &crates_dir()).expect("generate");
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
    let files = generate(Kind::Rules, &crates_dir()).expect("generate");
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
    let dir = workspace_root()
        .expect("workspace root")
        .join("docs/reference/rules");
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

// frob:ticket 01M3ZBV60QDKMT4S1YV7F60YEN
/// Neither a gate-side mark table nor a second polarity enum may exist outside gob-rules.
#[test]
fn one_required_reason_and_one_polarity() {
    let needles = [
        ["Required", "Marks"].concat(),
        ["enum ", "Polarity"].concat(),
    ];
    let mut hits = Vec::new();
    let mut stack = vec![crates_dir()];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir).expect("read dir") {
            let path = entry.expect("entry").path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().is_some_and(|e| e == "rs")
                && !path.starts_with(crates_dir().join("gob-rules"))
                && let Ok(text) = std::fs::read_to_string(&path)
            {
                for n in &needles {
                    if text.contains(n.as_str()) {
                        hits.push(format!("{} in {}", n, path.display()));
                    }
                }
            }
        }
    }
    assert!(hits.is_empty(), "duplicates outside gob-rules: {hits:?}");
}

// frob:ticket 01M43ARX764095Q4VWABWXXV5H
#[test]
fn crunk_config_reference_and_schema_are_generated_apart_from_frobs() {
    let files = generate(Kind::All, &crates_dir()).expect("generate");
    let get = |path: &str| {
        files
            .iter()
            .find(|f| f.path == path)
            .unwrap_or_else(|| panic!("{path} not generated"))
    };
    assert!(
        get("docs/crunk/config.md")
            .content
            .contains("## `[project]`")
    );
    let schema: serde_json::Value =
        serde_json::from_str(&get("docs/schemas/crunk.json").content).expect("valid json");
    assert!(schema["properties"]["project"].is_object());
    // crunk.toml keys must not leak into frob's own config reference or schema.
    assert!(!get("docs/reference/config.md").content.contains("css_root"));
    assert!(!get("docs/schemas/config.json").content.contains("css_root"));
}
