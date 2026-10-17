//! PROC001: no spawning API outside the configured spawner crates.
//!
//! A repository-local policy (`[check] process_spawners`): only the listed
//! crates may spawn processes. A plain text scan over `crates/*/src/**/*.rs`
//! that matches spawning APIs only (`Command`, `Child`, `Stdio`, ...), never
//! `ExitCode`, `exit`, `abort` or `id`; it moves to a tree-sitter rule when
//! `gob-languages` lands. The scan lives here beside the declaration; the repo group in
//! `crate::repo` turns each [`Proc001Hit`] into a finding.

// frob:ticket 01M48R03ZFTPSDD33HMJBD7STD

use std::path::{Path, PathBuf};

use gob_rules::{Finding, Out, RepoRule, Severity, rule};
use gob_text::{FileInterner, Span, TextRange, TextSize};
use tracing::debug;
use walkdir::WalkDir;

use crate::host::CheckHost;

/// A crate outside the repository's declared spawners uses a process-spawning API.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PROC001",
    slug = "process-outside-exec",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CheckHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Proc001;

gob_rules::list_in_registry!(Proc001, "frob");

impl<P: ?Sized + CheckHost> RepoRule<P> for Proc001 {
    /// The verdict is computed by the repo group in `crate::repo` from [`scan`]; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

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

/// Byte offset of the start of 1-based `line` in `text`.
fn line_start(text: &str, line: usize) -> usize {
    text.split_inclusive('\n')
        .take(line.saturating_sub(1))
        .map(str::len)
        .sum()
}

/// One `PROC001` finding per spawning reference outside `spawners` (the repo group's verdict).
pub(crate) fn findings(root: &Path, spawners: &[String], files: &mut FileInterner) -> Vec<Finding> {
    let id = crate::ids::rule_id::<Proc001>();
    let mut out = Vec::new();
    for hit in scan(root, spawners) {
        let rel = hit
            .path
            .strip_prefix(root)
            .unwrap_or(&hit.path)
            .to_string_lossy()
            .replace('\\', "/");
        let text = std::fs::read_to_string(&hit.path).unwrap_or_default();
        let start = line_start(&text, hit.line) + hit.col.saturating_sub(1);
        let line_end = line_start(&text, hit.line + 1).min(text.len());
        let end = line_end.max(start);
        let to_size = |n: usize| TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
        let span = Span::new(
            files.intern(&rel),
            TextRange::new(to_size(start), to_size(end)),
        );
        out.push(Finding::new(
            id.clone(),
            Severity::Error,
            Some(span),
            format!(
                "`{}` uses a process-spawning API outside {}; spawn through gob_exec::Runner",
                hit.text,
                spawners.join(", ")
            ),
            &rel,
        ));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Fixture text with `proc_` spelled out as `process`, so this file never matches its own scan.
    fn src_text(s: &str) -> String {
        s.replace("proc_", "process")
    }

    // frob:tests crates/gob-check/src/rules/proc001.rs::scan_text
    #[test]
    fn flags_code_and_skips_comments() {
        let src = src_text(
            "// std::proc_::Command here\n/// doc std::proc_::Command\nuse std::proc_::Command;\n/* a\nstd::proc_::Command\n*/ let x = proc_::Command::new(\"a\");\n",
        );
        let hits = scan_text(Path::new("x.rs"), &src);
        let lines: Vec<_> = hits.iter().map(|h| h.line).collect();
        assert_eq!(lines, vec![3, 6]);
        assert_eq!(hits[0].col, 5);
    }

    // frob:tests crates/gob-check/src/rules/proc001.rs::scan_text
    #[test]
    fn exit_code_and_exit_are_not_spawns() {
        let src = src_text(
            "use std::proc_::ExitCode;\nuse std::proc_::{ExitCode, Termination};\nfn f() { std::proc_::exit(1); std::proc_::abort(); let _ = std::proc_::id(); }\nuse std::proc_;\n",
        );
        assert!(scan_text(Path::new("x.rs"), &src).is_empty());
    }

    // frob:tests crates/gob-check/src/rules/proc001.rs::scan_text
    #[test]
    fn grouped_and_multiline_imports_match_spawn_names() {
        let src = src_text(
            "use std::proc_::{ExitCode, Command};\nuse std::proc_::{\n    ExitCode,\n    Stdio,\n};\nuse std::os::unix::proc_::CommandExt;\nuse std::proc_::*;\n",
        );
        let lines: Vec<_> = scan_text(Path::new("x.rs"), &src)
            .iter()
            .map(|h| h.line)
            .collect();
        assert_eq!(lines, vec![1, 2, 6, 7]);
    }

    // frob:tests crates/gob-check/src/rules/proc001.rs::scan
    #[test]
    fn scan_fires_outside_spawner_crates() {
        let dir = std::env::temp_dir().join(format!("proc001-{}", std::process::id()));
        for krate in ["gob-exec", "gob-git", "other"] {
            let src = dir.join("crates").join(krate).join("src");
            std::fs::create_dir_all(&src).unwrap();
            std::fs::write(src.join("lib.rs"), src_text("use std::proc_::Command;\n")).unwrap();
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

    // frob:ticket 01M48R03ZFTPSDD33HMJBD7STD
    // frob:tests crates/gob-check/src/rules/proc001.rs::findings
    #[test]
    fn findings_keep_the_pre_migration_id_severity_message_and_span() {
        let dir = std::env::temp_dir().join(format!("proc001-find-{}", std::process::id()));
        let src = dir.join("crates").join("other").join("src");
        std::fs::create_dir_all(&src).unwrap();
        std::fs::write(
            src.join("lib.rs"),
            src_text("fn a() {}\nuse std::proc_::Command;\n"),
        )
        .unwrap();
        let spawners = ["gob-exec".to_owned(), "gob-git".to_owned()];
        let mut files = FileInterner::default();
        let found = findings(&dir, &spawners, &mut files);
        std::fs::remove_dir_all(&dir).unwrap();
        assert_eq!(found.len(), 1);
        let f = &found[0];
        assert_eq!(f.rule.to_string(), "PROC001");
        assert_eq!(f.severity, Severity::Error);
        assert_eq!(
            f.message,
            "`use std::proc".replace("proc", "process")
                + "::Command;` uses a process-spawning API outside gob-exec, gob-git; spawn through gob_exec::Runner"
        );
        let span = f.span.expect("spanned");
        assert_eq!(u32::from(span.range.start()), 10 + 4, "line 2, col 5");
    }
}
