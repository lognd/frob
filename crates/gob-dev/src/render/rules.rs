//! Rule pages (`docs/reference/rules/<ID>.md`) and their index.

use std::collections::BTreeMap;
use std::path::Path;

use gob_mdtest::{Block, Expect, parse_suite};
use gob_rules::{FixKind, Registry, RuleMeta, Scope, Severity, Tier};

use super::{cell, md_header};
use crate::files::GenFile;

/// One mdtest corpus block shown on a rule page.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Example {
    /// Case name from the corpus headings.
    pub name: String,
    /// Fence language.
    pub language: String,
    /// `fire` or `clean`.
    pub expect: Expect,
    /// Block text.
    pub text: String,
    /// Inline config, if the case sets one.
    pub config: Option<String>,
}

impl From<&Block> for Example {
    fn from(b: &Block) -> Self {
        Self {
            name: b.name.clone(),
            language: b.language.clone(),
            expect: b.expect,
            text: b.text.clone(),
            config: b.config.clone(),
        }
    }
}

/// Lowercase severity name.
pub fn severity_name(s: Severity) -> &'static str {
    match s {
        Severity::Unresolved => "unresolved",
        Severity::Advisory => "advisory",
        Severity::Warn => "warn",
        Severity::Error => "error",
    }
}

/// Lowercase tier name.
pub fn tier_name(t: Tier) -> &'static str {
    match t {
        Tier::Universal => "universal",
        Tier::Lang => "lang",
    }
}

/// Lowercase scope name.
pub fn scope_name(s: Scope) -> &'static str {
    match s {
        Scope::File => "file",
        Scope::Repo => "repo",
    }
}

/// Lowercase fix-kind name.
pub fn fix_name(f: FixKind) -> &'static str {
    match f {
        FixKind::Manual => "manual",
        FixKind::Deterministic => "deterministic",
        FixKind::VerifyCommit => "verify-commit",
        FixKind::FixIt => "fix-it",
    }
}

/// A fence of backticks longer than any run inside `text` (minimum three).
fn fence_for(text: &str) -> String {
    let mut longest = 0;
    let mut run = 0;
    for c in text.chars() {
        if c == '`' {
            run += 1;
            longest = longest.max(run);
        } else {
            run = 0;
        }
    }
    "`".repeat(longest.max(2) + 1)
}

/// Render one rule page from its metadata and corpus examples.
pub fn render_rule_page(meta: &RuleMeta, examples: &[Example]) -> String {
    let mut out = md_header("rules");
    out.push_str(&format!("\n# {}: {}\n\n", meta.id, meta.slug));
    out.push_str("| Field | Value |\n|---|---|\n");
    let rows = [
        ("family", meta.family.to_owned()),
        ("product", meta.product.to_owned()),
        (
            "severity (default)",
            severity_name(meta.severity).to_owned(),
        ),
        ("tier", tier_name(meta.tier).to_owned()),
        ("scope", scope_name(meta.scope).to_owned()),
        ("fix", fix_name(meta.fix).to_owned()),
        ("version", meta.version.to_string()),
        ("since", meta.since.to_owned()),
    ];
    for (k, v) in rows {
        out.push_str(&format!("| {k} | {} |\n", cell(&v)));
    }
    out.push_str(&format!("\n{}\n", meta.explanation.trim()));
    if !examples.is_empty() {
        out.push_str("\n## Examples\n");
        for ex in examples {
            let fence = fence_for(&ex.text);
            out.push_str(&format!("\n### {} ({})\n\n", ex.name, ex.expect));
            if let Some(config) = &ex.config {
                out.push_str(&format!("Config: `{}`\n\n", config.replace('`', "'")));
            }
            out.push_str(&format!("{fence}{}\n{}", ex.language, ex.text));
            if !ex.text.ends_with('\n') {
                out.push('\n');
            }
            out.push_str(&format!("{fence}\n"));
        }
    }
    out
}

/// Render the index table grouped by family.
pub fn render_index(metas: &[&RuleMeta]) -> String {
    let mut by_family: BTreeMap<&str, Vec<&RuleMeta>> = BTreeMap::new();
    for m in metas {
        by_family.entry(m.family).or_default().push(m);
    }
    let mut out = md_header("rules");
    out.push_str("\n# Rules\n");
    for (family, mut rules) in by_family {
        rules.sort_by_key(|m| m.id);
        out.push_str(&format!("\n## {family}\n\n"));
        out.push_str("| Rule | Slug | Severity | Fix | Summary |\n|---|---|---|---|---|\n");
        for m in rules {
            out.push_str(&format!(
                "| [{id}]({id}.md) | {} | {} | {} | {} |\n",
                cell(m.slug),
                severity_name(m.severity),
                fix_name(m.fix),
                cell(m.summary),
                id = m.id,
            ));
        }
    }
    out
}

/// Corpus examples for `id` from `crates/*/tests/mdtest/<lowercase id>.md` under `crates_dir`.
pub fn load_examples(crates_dir: &Path, id: &str) -> Vec<Example> {
    let file = format!("{}.md", id.to_ascii_lowercase());
    let mut crate_dirs: Vec<_> = match std::fs::read_dir(crates_dir) {
        Ok(rd) => rd.filter_map(Result::ok).map(|e| e.path()).collect(),
        Err(e) => {
            tracing::warn!(dir = %crates_dir.display(), error = %e, "cannot list crates dir");
            return Vec::new();
        }
    };
    crate_dirs.sort();
    let mut examples = Vec::new();
    for dir in crate_dirs {
        let path = dir.join("tests").join("mdtest").join(&file);
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        match parse_suite(&text) {
            Ok(blocks) => {
                tracing::debug!(path = %path.display(), blocks = blocks.len(), "corpus parsed");
                examples.extend(
                    blocks
                        .iter()
                        .filter(|b| b.rule.to_string() == id)
                        .map(Example::from),
                );
            }
            Err(e) => {
                tracing::warn!(path = %path.display(), error = %e.message, "corpus unparsable");
            }
        }
    }
    examples
}

/// Every rule page plus the index, for the global registry.
pub fn generate(crates_dir: &Path) -> Vec<GenFile> {
    generate_for(Registry::global().iter().collect(), crates_dir)
}

/// Rule pages plus index for an explicit rule set.
pub fn generate_for(mut metas: Vec<&RuleMeta>, crates_dir: &Path) -> Vec<GenFile> {
    metas.sort_by_key(|m| m.id);
    let mut files: Vec<GenFile> = metas
        .iter()
        .map(|m| GenFile {
            path: format!("docs/reference/rules/{}.md", m.id),
            content: render_rule_page(m, &load_examples(crates_dir, m.id)),
        })
        .collect();
    files.push(GenFile {
        path: "docs/reference/rules/README.md".to_owned(),
        content: render_index(&metas),
    });
    files
}

#[cfg(test)]
mod tests {
    use super::*;

    const FAKE: RuleMeta = RuleMeta {
        id: "FAKE001",
        slug: "fake-rule",
        family: "FAKE",
        product: "frob",
        severity: Severity::Warn,
        summary: "A fake | rule.",
        explanation: "A fake rule.\n\nFix it.\n",
        tier: Tier::Lang,
        scope: Scope::Repo,
        fix: FixKind::VerifyCommit,
        version: 3,
        since: "2.0.0",
        module: "x",
    };

    #[test]
    fn page_has_title_table_explanation_examples() {
        let ex = Example {
            name: "Case / A #1".to_owned(),
            language: "rust".to_owned(),
            expect: Expect::Fire,
            text: "fn a() {}\n".to_owned(),
            config: Some("a = 1".to_owned()),
        };
        let page = render_rule_page(&FAKE, &[ex]);
        assert!(page.starts_with("<!-- generated by cargo dev gen rules; do not edit -->\n"));
        assert!(page.contains("# FAKE001: fake-rule"));
        assert!(page.contains("| severity (default) | warn |"));
        assert!(page.contains("| fix | verify-commit |"));
        assert!(page.contains("| version | 3 |"));
        assert!(page.contains("A fake rule.\n\nFix it."));
        assert!(page.contains("### Case / A #1 (fire)"));
        assert!(page.contains("```rust\nfn a() {}\n```"));
        assert!(page.is_ascii());
    }

    #[test]
    fn page_without_examples_has_no_examples_section() {
        assert!(!render_rule_page(&FAKE, &[]).contains("## Examples"));
    }

    #[test]
    fn fence_grows_past_inner_backticks() {
        assert_eq!(fence_for("a ``` b"), "````");
        assert_eq!(fence_for("plain"), "```");
    }

    #[test]
    fn index_groups_by_family_and_escapes() {
        let idx = render_index(&[&FAKE]);
        assert!(idx.contains("## FAKE"));
        assert!(idx.contains("[FAKE001](FAKE001.md)"));
        assert!(idx.contains("A fake \\| rule."));
    }
}
