//! Deterministic generators for the B1 fixture: Rust and Markdown files of known shape.

use std::fmt::Write as _;

/// A ULID-shaped ticket id used in the generated bound markers.
const ULID: &str = "01J9QKX3M8Z4T7N2V5B6C0D1E2";

/// Lines one generated Rust unit occupies (see [`rust_file`]).
const RUST_UNIT_LINES: usize = 12;

/// One generated source file: its repository path and text.
pub struct SourceFile {
    /// Repository-relative path.
    pub path: String,
    /// File text.
    pub text: String,
}

/// A Rust file of about `lines` lines: public and private functions, bare, owned, bound and
/// in-string work markers, and a `#[cfg(test)]` module that calls every third public function.
pub fn rust_file(index: usize, lines: usize) -> SourceFile {
    let units = lines.saturating_sub(10) / RUST_UNIT_LINES;
    let mut s = String::with_capacity(lines * 40);
    for k in 0..units {
        let i = index;
        let _ = writeln!(s, "/// Item {k} of file {i}.");
        let _ = writeln!(s, "pub fn f{i}_{k}(x: i32) -> i32 {{");
        let _ = writeln!(s, "    let y = x + {k};");
        match k % 5 {
            0 => s.push_str("    // TODO bare marker nobody owns\n"),
            1 => {
                let _ = writeln!(s, "    // TODO({ULID}) owned marker");
            }
            _ => s.push_str("    // plain remark\n"),
        }
        if k % 4 == 1 {
            let _ = writeln!(s, "    p{i}_{}(y)", k - 1);
        } else {
            s.push_str("    y * 2\n");
        }
        s.push_str("}\n");
        match k % 5 {
            2 => {
                let _ = writeln!(s, "// frob:todo {ULID}");
                s.push_str("/* FIXME bound by the line above */\n");
            }
            3 => {
                s.push_str("/* HACK bare block marker */\n");
                s.push_str("// unrelated line\n");
            }
            _ => s.push_str("// nothing to see\n// still nothing\n"),
        }
        let _ = writeln!(s, "fn p{i}_{k}(x: i32) -> i32 {{ f{i}_{k}(x) }}");
        let _ = writeln!(
            s,
            "fn s{i}_{k}() -> &'static str {{ \"TODO inside a string\" }}"
        );
        s.push('\n');
    }
    s.push_str("#[cfg(test)]\nmod tests {\n    use super::*;\n");
    for k in (0..units).step_by(3) {
        let _ = writeln!(
            s,
            "    #[test]\n    fn t{k}() {{ let _ = f{index}_{k}(1); }}"
        );
    }
    s.push_str("}\n");
    SourceFile {
        path: format!("src/m{index}.rs"),
        text: s,
    }
}

/// A Markdown file of about `lines` lines under `docs/`: headings, links to itself with valid
/// and invalid anchors, links to missing files, and external links.
pub fn markdown_file(index: usize, lines: usize) -> SourceFile {
    let path = format!("docs/doc{index}.md");
    let sections = lines / 8;
    let mut s = format!("# Document {index}\n\n");
    for k in 0..sections {
        let _ = writeln!(s, "## Section {k}\n");
        let _ = writeln!(
            s,
            "Prose for section {k} with a [good link](doc{index}.md#section-{k})."
        );
        let _ = writeln!(
            s,
            "A [bad anchor](doc{index}.md#nope-{k}) and a [gone](missing{k}.md)."
        );
        let _ = writeln!(
            s,
            "An [outside](https://example.com/{k}) link and a [sibling](../README.md)."
        );
        s.push('\n');
        s.push('\n');
    }
    SourceFile { path, text: s }
}

/// The 100k-line fixture: `rust_files` Rust files of `rust_lines` lines and `md_files`
/// Markdown files of `md_lines` lines.
pub fn corpus(
    rust_files: usize,
    rust_lines: usize,
    md_files: usize,
    md_lines: usize,
) -> (Vec<SourceFile>, Vec<SourceFile>) {
    (
        (0..rust_files).map(|i| rust_file(i, rust_lines)).collect(),
        (0..md_files).map(|i| markdown_file(i, md_lines)).collect(),
    )
}
