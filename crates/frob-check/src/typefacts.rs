//! Checker-derived Python type facts for the snapshot graph build (`[types] trust`).
//!
//! Under `trust = "checked"` an annotation resolves a call exactly only in a file the bound type
//! checker (a `[[check.tool]]` stage with the `ty-gitlab` or `pyright-json` parser) reported nothing
//! on. This module runs that stage once, derives the clean-file set and hands it to the graph build.
//! Any failure degrades to "no clean files", so annotations stay claims (May), never exact.

use std::path::Path;
use std::time::Duration;

use gob_check::{CheckTable, ToolParser, ToolStage, TypesTable, type_facts_from_output};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_symbols::{TypeFacts, TypesTrust};
use gob_walk::FileEntry;

/// The stage whose output is the checker's verdict: the first typed-parser stage with a fixed argv.
fn checker_stage(table: &CheckTable) -> Option<&ToolStage> {
    table.tool.iter().find(|s| {
        matches!(s.parser, ToolParser::TyGitlab | ToolParser::PyrightJson)
            && !s.args.iter().any(|a| a.contains('{'))
    })
}

/// `(path, text)` of every Python file in the walk; unreadable files are left out (never clean).
fn python_sources(root: &Path, entries: &[FileEntry]) -> Vec<(String, String)> {
    entries
        .iter()
        .filter(|e| e.language.tag() == "py")
        .filter_map(|e| match std::fs::read_to_string(root.join(&e.path)) {
            Ok(text) => Some((e.path.clone(), text)),
            Err(err) => {
                tracing::warn!(path = %e.path, %err, "python file unreadable for type facts");
                None
            }
        })
        .collect()
}

/// The [`TypeFacts`] for the graph build: the configured trust, plus clean files when the bound checker runs.
///
/// Never fails: an unreadable `[types]` table, a missing checker, a bad exit or unparseable output
/// is logged and yields facts with no clean file.
// frob:ticket 01M4X64AXQH3HTB6Z9ZGCPFTAD
pub(crate) fn type_facts(
    root: &Path,
    table: &CheckTable,
    entries: &[FileEntry],
    product: &str,
) -> TypeFacts {
    let trust = match TypesTable::load(root, product).and_then(|t| t.trust()) {
        Ok(trust) => trust,
        Err(err) => {
            tracing::warn!(%err, "[types] unreadable; using the default trust");
            TypesTrust::default()
        }
    };
    let none = TypeFacts::new(trust);
    if trust != TypesTrust::Checked {
        tracing::debug!(?trust, "type checker not consulted");
        return none;
    }
    let Some(stage) = checker_stage(table) else {
        tracing::debug!("no ty-gitlab or pyright-json stage; annotations stay claims");
        return none;
    };
    let files = python_sources(root, entries);
    if files.is_empty() {
        return none;
    }
    let runner = Runner::new(Limits::default()).allow_tools([stage.command.clone()]);
    let spec = Spec {
        program: Program::Tool {
            name: stage.command.clone(),
        },
        args: stage.args.clone(),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(stage.timeout_secs),
        capture: true,
    };
    let output = match runner.run(&spec) {
        Ok(o) => o,
        Err(err) => {
            tracing::warn!(stage = %stage.name, %err, "type checker could not run");
            return none;
        }
    };
    // A checker exits 1 when it has findings; anything else is not a verdict.
    if !matches!(output.status, Outcome::Exited(0 | 1)) {
        tracing::warn!(stage = %stage.name, status = ?output.status, "type checker ended abnormally");
        return none;
    }
    match type_facts_from_output(stage.parser, &output.stdout, trust, &files) {
        Ok(facts) => {
            tracing::info!(stage = %stage.name, files = files.len(), "type facts derived");
            facts
        }
        Err(err) => {
            tracing::warn!(stage = %stage.name, %err, "type checker output unreadable");
            none
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_symbols::AnnotationWeight;

    fn walk(root: &Path) -> Vec<FileEntry> {
        let mut out = Vec::new();
        for name in ["clean.py", "dirty.py"] {
            out.push(FileEntry {
                path: name.to_owned(),
                size: 0,
                digest: gob_walk::Digest::of(b"x = 1\n"),
                language: gob_walk::LanguageHint::Other("py".to_owned()),
            });
            std::fs::write(root.join(name), "x = 1\n").expect("write");
        }
        out
    }

    fn table(parser: &str) -> CheckTable {
        let toml = format!(
            "[[tool]]\nname = \"fake\"\ncommand = \"sh\"\nargs = [\"fake.sh\"]\nparser = \"{parser}\"\n"
        );
        toml::from_str(&toml).expect("table")
    }

    const DIRTY: &str = r#"[{"description":"d","check_name":"invalid-assignment","fingerprint":"f","severity":"major","location":{"path":"dirty.py","positions":{"begin":{"line":1,"column":1},"end":{"line":1,"column":2}}}}]"#;

    // frob:tests crates/frob-check/src/typefacts.rs::type_facts
    #[test]
    fn checker_clean_files_are_exact_and_dirty_ones_claimed() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        let entries = walk(root);
        std::fs::write(root.join("fake.sh"), format!("echo '{DIRTY}'\nexit 1\n")).expect("script");
        let facts = type_facts(root, &table("ty-gitlab"), &entries, "frob");
        assert_eq!(facts.weight("clean.py", 1), AnnotationWeight::Exact);
        assert_eq!(facts.weight("dirty.py", 1), AnnotationWeight::Claimed);
    }

    // frob:tests crates/frob-check/src/typefacts.rs::type_facts
    #[test]
    fn no_checker_or_a_broken_one_leaves_every_annotation_a_claim() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        let entries = walk(root);
        let none = type_facts(root, &CheckTable::default(), &entries, "frob");
        assert_eq!(none.weight("clean.py", 1), AnnotationWeight::Claimed);
        std::fs::write(root.join("fake.sh"), "exit 3\n").expect("script");
        let bad = type_facts(root, &table("ty-gitlab"), &entries, "frob");
        assert_eq!(bad.weight("clean.py", 1), AnnotationWeight::Claimed);
    }

    // frob:tests crates/frob-check/src/typefacts.rs::type_facts
    #[test]
    fn trust_annotated_does_not_run_the_checker() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        let entries = walk(root);
        std::fs::write(root.join("frob.toml"), "[types]\ntrust = \"annotated\"\n").expect("cfg");
        std::fs::write(root.join("fake.sh"), "echo '[]'\n").expect("script");
        let facts = type_facts(root, &table("ty-gitlab"), &entries, "frob");
        assert_eq!(facts.weight("clean.py", 1), AnnotationWeight::Claimed);
    }
}
