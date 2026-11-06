//! Pack detector rows that fire on source structure: import, attribute and GRL pattern rows.
//!
//! A pack's `import` row names modules and expands to the language's import patterns; an
//! `attribute` or `pattern` row carries GRL grammar patterns directly. Every row is run with
//! [`sites`], which returns the byte offset of each place the rows match.

// frob:ticket 01M3Z714QT3QXEAJAK9JDDEB70

use crate::grammar::{GrammarError, Pattern};

/// The grammar patterns that spell an import of `module` in `language`; empty when the language
/// has no import form this build knows (the row then never fires and the cell stays Unknown).
#[must_use]
pub fn import_patterns(language: &str, module: &str) -> Vec<String> {
    match language {
        "python" => vec![
            format!("import {module}"),
            format!("import {module} as $A"),
            format!("from {module} import $$$A"),
        ],
        "rust" => vec![format!("use {module};"), format!("use {module}::$$$A;")],
        "go" => vec![format!("import \"{module}\"")],
        "javascript" | "typescript" | "tsx" | "jsx" => vec![
            format!("import $$$A from \"{module}\""),
            format!("require(\"{module}\")"),
        ],
        _ => Vec::new(),
    }
}

/// Byte offsets, ascending and unique, of every match of any of `patterns` in `source`.
///
/// # Errors
///
/// [`GrammarError`] when a pattern does not compile for `language` or `source` does not parse.
pub fn sites(
    language: &str,
    patterns: &[String],
    source: &str,
) -> Result<Vec<usize>, GrammarError> {
    let mut out = Vec::new();
    for text in patterns {
        let pattern = Pattern::compile(language, text)?;
        out.extend(pattern.find(source)?.into_iter().map(|m| m.range.start));
    }
    out.sort_unstable();
    out.dedup();
    tracing::debug!(
        language,
        patterns = patterns.len(),
        sites = out.len(),
        "structural detector scanned"
    );
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(lang: &str, pats: &[&str], src: &str) -> Vec<usize> {
        let pats: Vec<String> = pats.iter().map(|s| (*s).to_owned()).collect();
        sites(lang, &pats, src).unwrap()
    }

    // frob:tests crates/gob-pattern/src/detector.rs::sites
    #[test]
    fn rust_unsafe_block_pattern_fires_and_clean_is_quiet() {
        assert_eq!(
            run("rust", &["unsafe { $$$A }"], "fn f() { unsafe { g(); } }").len(),
            1
        );
        assert!(run("rust", &["unsafe { $$$A }"], "fn f() { g(); }").is_empty());
    }

    // frob:tests crates/gob-pattern/src/detector.rs::import_patterns
    #[test]
    fn python_import_forms_fire() {
        let pats = import_patterns("python", "ctypes");
        let pats: Vec<&str> = pats.iter().map(String::as_str).collect();
        assert_eq!(run("python", &pats, "import ctypes\n").len(), 1);
        assert_eq!(run("python", &pats, "from ctypes import CDLL\n").len(), 1);
        assert!(run("python", &pats, "import os\n").is_empty());
    }

    // frob:tests crates/gob-pattern/src/detector.rs::sites
    #[test]
    fn keyword_pattern_requires_the_keyword_argument() {
        let p = ["subprocess.run($$$A, shell=True)"];
        assert_eq!(
            run("python", &p, "subprocess.run(c, shell=True)\n").len(),
            1
        );
        assert!(run("python", &p, "subprocess.run(c)\n").is_empty());
        assert!(run("python", &p, "subprocess.run(c, shell=False)\n").is_empty());
    }
}
