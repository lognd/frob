//! Checker-derived Python type facts for the snapshot graph build (`[types] trust`).
//!
//! Under `trust = "checked"` an annotation resolves a call exactly only in a file the bound type
//! checker (a `[[check.tool]]` stage with the `ty-gitlab`, `pyright-json` or, run with `--strict`, `tsc-text` parser) reported nothing
//! on. This module runs that stage once, derives the clean-file set and hands it to the graph build.
//! Any failure degrades to "no clean files", so annotations stay claims (May), never exact.

use std::path::Path;
use std::time::Duration;

use gob_check::{
    CheckTable, ToolParser, ToolStage, TypesTable, is_strict_checker, type_facts_from_output,
};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_symbols::{TypeFacts, TypesTrust};
use gob_walk::FileEntry;

/// The language family a typed-checker parser covers.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Family {
    /// Python (`ty-gitlab`, `pyright-json`).
    Python,
    /// TypeScript and JavaScript (`tsc-text`).
    TypeScript,
}

impl Family {
    /// The family of `parser`, or `None` when it is not a type checker.
    fn of(parser: ToolParser) -> Option<Self> {
        match parser {
            ToolParser::TyGitlab | ToolParser::PyrightJson => Some(Self::Python),
            ToolParser::TscText => Some(Self::TypeScript),
            _ => None,
        }
    }

    /// Whether the walked file `e` belongs to this family.
    fn covers(self, e: &FileEntry) -> bool {
        match self {
            Self::Python => e.language.tag() == "py",
            Self::TypeScript => gob_symbols::is_typescript_path(&e.path),
        }
    }
}

/// The stages whose output is a checker verdict: the first strict typed-parser stage with a fixed argv per language family.
fn checker_stages(table: &CheckTable) -> Vec<(Family, &ToolStage)> {
    let mut out: Vec<(Family, &ToolStage)> = Vec::new();
    for s in &table.tool {
        let Some(family) = Family::of(s.parser) else {
            continue;
        };
        if s.args.iter().any(|a| a.contains('{')) || out.iter().any(|(f, _)| *f == family) {
            continue;
        }
        if !is_strict_checker(s) {
            tracing::debug!(stage = %s.name, "type checker is not run strict; its verdict is ignored");
            continue;
        }
        out.push((family, s));
    }
    out
}

/// Reads the walked text of a repo-relative path (the snapshot content API).
pub(crate) type TextReader<'a> = dyn Fn(&str) -> std::io::Result<String> + 'a;

/// `(path, text)` of every file of `family` in the walk; unreadable files are left out (never clean).
fn sources(family: Family, read: &TextReader<'_>, entries: &[FileEntry]) -> Vec<(String, String)> {
    entries
        .iter()
        .filter(|e| family.covers(e))
        .filter_map(|e| match read(&e.path) {
            Ok(text) => Some((e.path.clone(), text)),
            Err(err) => {
                tracing::warn!(path = %e.path, %err, "file unreadable for type facts");
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
    read: &TextReader<'_>,
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
    let stages = checker_stages(table);
    if stages.is_empty() {
        tracing::debug!("no strict type-checker stage; annotations stay claims");
        return none;
    }
    let mut facts = none;
    for (family, stage) in stages {
        let files = sources(family, read, entries);
        if files.is_empty() {
            continue;
        }
        if let Some(found) = run_checker(root, stage, trust, &files) {
            facts.merge(found);
        }
    }
    facts
}

/// Runs one checker stage and derives its facts; `None` (logged) when it cannot give a verdict.
fn run_checker(
    root: &Path,
    stage: &ToolStage,
    trust: TypesTrust,
    files: &[(String, String)],
) -> Option<TypeFacts> {
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
            return None;
        }
    };
    // A checker exits nonzero when it has findings (tsc: 1 or 2); anything else is not a verdict.
    let verdict = match stage.parser {
        ToolParser::TscText => matches!(output.status, Outcome::Exited(0..=2)),
        _ => matches!(output.status, Outcome::Exited(0 | 1)),
    };
    if !verdict {
        tracing::warn!(stage = %stage.name, status = ?output.status, "type checker ended abnormally");
        return None;
    }
    match type_facts_from_output(stage.parser, &output.stdout, trust, files) {
        Ok(facts) => {
            tracing::info!(stage = %stage.name, files = files.len(), "type facts derived");
            Some(facts)
        }
        Err(err) => {
            tracing::warn!(stage = %stage.name, %err, "type checker output unreadable");
            None
        }
    }
}

#[cfg(test)]
#[allow(
    clippy::disallowed_methods,
    reason = "a test writes and reads a scratch repository"
)]
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
        let facts = type_facts(root, &table("ty-gitlab"), &entries, "frob", &|p| {
            std::fs::read_to_string(root.join(p))
        });
        assert_eq!(facts.weight("clean.py", 1), AnnotationWeight::Exact);
        assert_eq!(facts.weight("dirty.py", 1), AnnotationWeight::Claimed);
    }

    // frob:tests crates/frob-check/src/typefacts.rs::type_facts
    #[test]
    fn tsc_strict_stage_marks_unreported_typescript_clean() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        let mut entries = Vec::new();
        for name in ["clean.ts", "dirty.ts"] {
            entries.push(FileEntry {
                path: name.to_owned(),
                size: 0,
                digest: gob_walk::Digest::of(b"x"),
                language: gob_walk::LanguageHint::Other("ts".to_owned()),
            });
            std::fs::write(root.join(name), "x.run();\n").expect("write");
        }
        std::fs::write(
            root.join("fake.sh"),
            "echo \"dirty.ts(1,1): error TS2339: nope.\"\nexit 2\n",
        )
        .expect("script");
        let read = |p: &str| std::fs::read_to_string(root.join(p));
        let strict = |args: &str| -> CheckTable {
            toml::from_str(&format!(
                "[[tool]]\nname = \"tsc\"\ncommand = \"sh\"\nargs = [{args}]\nparser = \"tsc-text\"\n"
            ))
            .expect("table")
        };
        let facts = type_facts(
            root,
            &strict("\"fake.sh\", \"--strict\""),
            &entries,
            "frob",
            &read,
        );
        assert_eq!(facts.weight("clean.ts", 1), AnnotationWeight::Exact);
        assert_eq!(facts.weight("dirty.ts", 1), AnnotationWeight::Claimed);
        let lax = type_facts(root, &strict("\"fake.sh\""), &entries, "frob", &read);
        assert_eq!(lax.weight("clean.ts", 1), AnnotationWeight::Claimed);
    }

    // frob:tests crates/frob-check/src/typefacts.rs::type_facts
    #[test]
    fn no_checker_or_a_broken_one_leaves_every_annotation_a_claim() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        let entries = walk(root);
        let none = type_facts(root, &CheckTable::default(), &entries, "frob", &|p| {
            std::fs::read_to_string(root.join(p))
        });
        assert_eq!(none.weight("clean.py", 1), AnnotationWeight::Claimed);
        std::fs::write(root.join("fake.sh"), "exit 3\n").expect("script");
        let bad = type_facts(root, &table("ty-gitlab"), &entries, "frob", &|p| {
            std::fs::read_to_string(root.join(p))
        });
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
        let facts = type_facts(root, &table("ty-gitlab"), &entries, "frob", &|p| {
            std::fs::read_to_string(root.join(p))
        });
        assert_eq!(facts.weight("clean.py", 1), AnnotationWeight::Claimed);
    }
}
