//! PROC001: no spawning API outside the configured spawner crates.
//!
//! A repository-local policy (`[check] process_spawners`): only the listed
//! crates may spawn processes. A plain text scan over `crates/*/src/**/*.rs`
//! that matches spawning APIs only (`Command`, `Child`, `Stdio`, ...), never
//! `ExitCode`, `exit`, `abort` or `id`; it moves to a tree-sitter rule when
//! `gob-languages` lands.

use std::path::{Path, PathBuf};

use tracing::debug;
use walkdir::WalkDir;

/// Names under a `process` path that spawn or drive a child process.
const SPAWN_NAMES: [&str; 10] = [
    "Command",
    "CommandExt",
    "Child",
    "ChildStdin",
    "ChildStdout",
    "ChildStderr",
    "Stdio",
    "exec",
    "spawn",
    "*",
];

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

/// Scan `root/crates/*/src/**/*.rs` and report spawning references outside `spawners`.
///
/// An empty `spawners` means the repository declares no policy: nothing is scanned.
pub fn scan(root: &Path, spawners: &[String]) -> Vec<Proc001Hit> {
    if spawners.is_empty() {
        debug!("proc001 not applicable: no process_spawners declared");
        return Vec::new();
    }
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
        if src != "src" || spawners.contains(&krate) {
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

/// Whether `c` can be part of a path segment.
fn is_path_char(c: u8) -> bool {
    c.is_ascii_alphanumeric() || c == b'_' || c == b':'
}

/// Whether the text after a `process::` path names a spawning API.
fn names_spawn(rest: &str) -> bool {
    if let Some(group) = rest.strip_prefix('{') {
        let body = group.split('}').next().unwrap_or(group);
        return body.split(',').any(|item| {
            let name = item.split_whitespace().next().unwrap_or("");
            SPAWN_NAMES.contains(&name.split("::").next().unwrap_or(name))
        });
    }
    let end = rest
        .find(|c: char| !(c.is_ascii_alphanumeric() || c == '_' || c == '*'))
        .unwrap_or(rest.len());
    SPAWN_NAMES.contains(&&rest[..end])
}

/// Scan one file's text, skipping comments; only spawning APIs match.
pub fn scan_text(path: &Path, text: &str) -> Vec<Proc001Hit> {
    let mut in_block = false;
    let code: Vec<String> = text
        .lines()
        .map(|raw| strip_comments(raw, &mut in_block))
        .collect();
    let joined = code.join("\n");
    let bytes = joined.as_bytes();
    let mut hits = Vec::new();
    let mut last_line = 0;
    for (at, _) in joined.match_indices("process::") {
        if !names_spawn(&joined[at + "process::".len()..]) {
            continue;
        }
        let mut start = at;
        while start > 0 && is_path_char(bytes[start - 1]) {
            start -= 1;
        }
        let line = joined[..start].matches('\n').count();
        if line == last_line && !hits.is_empty() {
            continue;
        }
        last_line = line;
        let col = start - joined[..start].rfind('\n').map_or(0, |n| n + 1);
        hits.push(Proc001Hit {
            path: path.to_path_buf(),
            line: line + 1,
            col: col + 1,
            text: text.lines().nth(line).unwrap_or("").trim().to_owned(),
        });
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

    // frob:tests crates/gob-exec/src/proc001.rs::scan_text
    #[test]
    fn flags_code_and_skips_comments() {
        let src = "// std::process::Command here\n/// doc std::process::Command\nuse std::process::Command;\n/* a\nstd::process::Command\n*/ let x = process::Command::new(\"a\");\n";
        let hits = scan_text(Path::new("x.rs"), src);
        let lines: Vec<_> = hits.iter().map(|h| h.line).collect();
        assert_eq!(lines, vec![3, 6]);
        assert_eq!(hits[0].col, 5);
    }

    // frob:tests crates/gob-exec/src/proc001.rs::scan_text
    #[test]
    fn exit_code_and_exit_are_not_spawns() {
        let src = "use std::process::ExitCode;\nuse std::process::{ExitCode, Termination};\nfn f() { std::process::exit(1); std::process::abort(); let _ = std::process::id(); }\nuse std::process;\n";
        assert!(scan_text(Path::new("x.rs"), src).is_empty());
    }

    // frob:tests crates/gob-exec/src/proc001.rs::scan_text
    #[test]
    fn grouped_and_multiline_imports_match_spawn_names() {
        let src = "use std::process::{ExitCode, Command};\nuse std::process::{\n    ExitCode,\n    Stdio,\n};\nuse std::os::unix::process::CommandExt;\nuse std::process::*;\n";
        let lines: Vec<_> = scan_text(Path::new("x.rs"), src)
            .iter()
            .map(|h| h.line)
            .collect();
        assert_eq!(lines, vec![1, 2, 6, 7]);
    }

    // frob:tests crates/gob-exec/src/proc001.rs::scan
    #[test]
    fn scan_fires_outside_spawner_crates() {
        let dir = std::env::temp_dir().join(format!("proc001-{}", std::process::id()));
        for krate in ["gob-exec", "gob-git", "other"] {
            let src = dir.join("crates").join(krate).join("src");
            std::fs::create_dir_all(&src).unwrap();
            std::fs::write(src.join("lib.rs"), "use std::process::Command;\n").unwrap();
        }
        let spawners = ["gob-exec".to_owned(), "gob-git".to_owned()];
        let hits = scan(&dir, &spawners);
        let none = scan(&dir, &[]);
        std::fs::remove_dir_all(&dir).unwrap();
        assert_eq!(hits.len(), 1);
        assert!(hits[0].path.ends_with("other/src/lib.rs"));
        assert_eq!((hits[0].line, hits[0].col), (1, 5));
        assert!(none.is_empty(), "no declared spawners means no policy");
    }
}
