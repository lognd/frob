//! The C# field-write graph: which files assign which names (the input of UNITY004).
//!
//! The scan is lexical and name based: a local or parameter of the same name counts as a writer, which
//! only ever hides a report, never invents one. The graph keeps the writing files per name so a rule
//! can tell where a field is assigned, not just that it is.

// frob:ticket 01M5FRZGDQ88QYMF8R547WNTP3

use std::collections::{BTreeMap, BTreeSet, HashSet};

fn is_ident(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_'
}

/// Names that `text` writes: `x =`, `x += 1`, `x++`, `--x`, `ref x`, `out x`, object initializers.
///
/// The scan is lexical and name-based: a local or parameter of the same name counts as a writer, which
/// only ever hides a report, never invents one. Line comments and string literals are skipped.
pub fn written_names(text: &str) -> HashSet<&str> {
    const COMPOUND: [&str; 11] = [
        "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=", "??=",
    ];
    let b = text.as_bytes();
    let mut out = HashSet::new();
    let mut i = 0;
    while i < b.len() {
        match b[i] {
            b'/' if b.get(i + 1) == Some(&b'/') => {
                while i < b.len() && b[i] != b'\n' {
                    i += 1;
                }
            }
            b'"' => {
                i += 1;
                while i < b.len() && b[i] != b'"' && b[i] != b'\n' {
                    i += usize::from(b[i] == b'\\') + 1;
                }
                i += 1;
            }
            c if is_ident(c) && !c.is_ascii_digit() => {
                let start = i;
                while i < b.len() && is_ident(b[i]) {
                    i += 1;
                }
                let after = text[i..].trim_start_matches([' ', '\t']);
                let before = text[..start].trim_end_matches([' ', '\t']);
                let assigns = (after.starts_with('=')
                    && !after.starts_with("==")
                    && !after.starts_with("=>"))
                    || COMPOUND.iter().any(|op| after.starts_with(op))
                    || after.starts_with("++")
                    || after.starts_with("--")
                    || before.ends_with("++")
                    || before.ends_with("--")
                    || before.ends_with(" ref")
                    || before.ends_with(" out")
                    || before.ends_with("(ref")
                    || before.ends_with("(out");
                if assigns {
                    out.insert(&text[start..i]);
                }
            }
            _ => i += 1,
        }
    }
    out
}

/// Write edges from assigned names to the files that assign them.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct FieldWrites {
    by_name: BTreeMap<String, BTreeSet<String>>,
}

impl FieldWrites {
    /// Records every name `text` (the contents of `path`) assigns.
    pub fn scan_file(&mut self, path: &str, text: &str) {
        let names = written_names(text);
        tracing::debug!(path, writes = names.len(), "field writes scanned");
        for n in names {
            self.by_name
                .entry(n.to_owned())
                .or_default()
                .insert(path.to_owned());
        }
    }

    /// True when some scanned file assigns `name`.
    pub fn is_written(&self, name: &str) -> bool {
        self.by_name.contains_key(name)
    }

    /// The sorted files that assign `name`.
    pub fn writers(&self, name: &str) -> impl Iterator<Item = &str> {
        self.by_name
            .get(name)
            .into_iter()
            .flat_map(|s| s.iter().map(String::as_str))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests written_names
    #[test]
    fn written_names_sees_assignments_and_skips_comments_and_equality() {
        let w = written_names(
            "a = 1; b += 2; c++; --d; Foo(ref e); if (f == 1) {} g => 2; // h = 3\nvar s = \"i = 4\"; new X { j = 1 };",
        );
        for n in ["a", "b", "c", "d", "e", "j", "s"] {
            assert!(w.contains(n), "{n} in {w:?}");
        }
        for n in ["f", "g", "h", "i"] {
            assert!(!w.contains(n), "{n} in {w:?}");
        }
    }

    // frob:tests FieldWrites.scan_file
    // frob:tests FieldWrites.is_written
    // frob:tests FieldWrites.writers
    #[test]
    fn graph_keeps_the_writing_files_per_name() {
        let mut g = FieldWrites::default();
        g.scan_file("A.cs", "x = 1; y++;");
        g.scan_file("B.cs", "x = 2;");
        assert!(g.is_written("x") && g.is_written("y") && !g.is_written("z"));
        assert_eq!(g.writers("x").collect::<Vec<_>>(), ["A.cs", "B.cs"]);
        assert_eq!(g.writers("z").count(), 0);
    }
}
