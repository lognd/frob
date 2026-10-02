//! PROC001: no `std::process` outside `gob-exec` and `gob-git`.
//!
//! A plain text scan over `crates/*/src/**/*.rs`; it moves to a
//! tree-sitter rule when `gob-languages` lands.

use std::path::{Path, PathBuf};

use tracing::debug;
use walkdir::WalkDir;

/// Crates permitted to reference `std::process`.
// `frob` is allowed only so its `main` can call the process-exit function.
pub const ALLOWED_CRATES: [&str; 3] = ["gob-exec", "gob-git", "frob"];

/// Substrings that count as a process reference.
const NEEDLES: [&str; 2] = ["std::process", "process::Command"];

/// One forbidden reference.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Proc001Hit {
    /// File containing the reference.
    pub path: PathBuf,
    /// 1-based line.
    pub line: usize,
    /// 1-based column of the match.
    pub col: usize,
    /// The offending source line, trimmed.
    pub text: String,
}

/// Scan `root/crates/*/src/**/*.rs` and report forbidden references.
pub fn scan(root: &Path) -> Vec<Proc001Hit> {
    let crates = root.join("crates");
    let mut hits = Vec::new();
    for entry in WalkDir::new(&crates)
        .min_depth(1)
        .into_iter()
        .filter_map(Result::ok)
    {
        let path = entry.path();
        if !entry.file_type().is_file() || path.extension().is_none_or(|e| e != "rs") {
            continue;
        }
        let Ok(rel) = path.strip_prefix(&crates) else {
            continue;
        };
        let mut comps = rel
            .components()
            .map(|c| c.as_os_str().to_string_lossy().into_owned());
        let (Some(krate), Some(src)) = (comps.next(), comps.next()) else {
            continue;
        };
        if src != "src" || ALLOWED_CRATES.contains(&krate.as_str()) {
            continue;
        }
        let Ok(text) = std::fs::read_to_string(path) else {
            debug!(path = %path.display(), "unreadable file skipped");
            continue;
        };
        hits.extend(scan_text(path, &text));
    }
    debug!(hits = hits.len(), "proc001 scan done");
    hits
}

/// Scan one file's text, skipping line and block comments.
pub fn scan_text(path: &Path, text: &str) -> Vec<Proc001Hit> {
    let mut hits = Vec::new();
    let mut in_block = false;
    for (i, raw) in text.lines().enumerate() {
        let code = strip_comments(raw, &mut in_block);
        let found = NEEDLES.iter().filter_map(|n| code.find(n)).min();
        if let Some(col) = found {
            hits.push(Proc001Hit {
                path: path.to_path_buf(),
                line: i + 1,
                col: col + 1,
                text: raw.trim().to_owned(),
            });
        }
    }
    hits
}

/// Blank out comment text in `line`, tracking `/* */` state across lines.
///
/// Comment bytes become spaces so columns stay aligned with the source.
fn strip_comments(line: &str, in_block: &mut bool) -> String {
    let b = line.as_bytes();
    let mut out = String::with_capacity(line.len());
    let mut i = 0;
    while i < b.len() {
        if *in_block {
            if b[i..].starts_with(b"*/") {
                *in_block = false;
                out.push_str("  ");
                i += 2;
            } else {
                out.push(' ');
                i += 1;
            }
        } else if b[i..].starts_with(b"/*") {
            *in_block = true;
            out.push_str("  ");
            i += 2;
        } else if b[i..].starts_with(b"//") {
            out.extend(std::iter::repeat_n(' ', b.len() - i));
            break;
        } else {
            let ch = line[i..].chars().next().unwrap_or(' ');
            out.push(ch);
            i += ch.len_utf8();
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn flags_code_and_skips_comments() {
        let src = "// std::process here\n/// doc std::process\nuse std::process::Command;\n/* a\nstd::process\n*/ let x = process::Command::new(\"a\");\n";
        let hits = scan_text(Path::new("x.rs"), src);
        let lines: Vec<_> = hits.iter().map(|h| h.line).collect();
        assert_eq!(lines, vec![3, 6]);
        assert_eq!(hits[0].col, 5);
    }

    #[test]
    fn scan_fires_outside_allowed_crates() {
        let dir = std::env::temp_dir().join(format!("proc001-{}", std::process::id()));
        for krate in ["gob-exec", "gob-git", "other"] {
            let src = dir.join("crates").join(krate).join("src");
            std::fs::create_dir_all(&src).unwrap();
            std::fs::write(src.join("lib.rs"), "use std::process::Command;\n").unwrap();
        }
        let hits = scan(&dir);
        std::fs::remove_dir_all(&dir).unwrap();
        assert_eq!(hits.len(), 1);
        assert!(hits[0].path.ends_with("other/src/lib.rs"));
        assert_eq!((hits[0].line, hits[0].col), (1, 5));
    }
}
