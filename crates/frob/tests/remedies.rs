//! Every `frob ...` / `grimble ...` command a remedy or help string names must exist in the CLI registry.
// frob:ticket 01M40YQZF4422S88TN6992AN0Q

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

type Surface = BTreeMap<String, BTreeSet<String>>;

/// One command span found in source: where it is and the text after the product name.
#[derive(Debug)]
struct Span {
    file: PathBuf,
    line: usize,
    product: &'static str,
    text: String,
    /// True when the span opens a string literal (`"frob ...`): prose and log lines look the same, so an unknown first word is not an error.
    weak: bool,
    /// True for tracing messages and bare one-literal lines, which are log text, not remedies.
    log_like: bool,
}

/// Source files whose string literals feed remedies, help lines and rule help.
fn source_files() -> Vec<PathBuf> {
    let crates = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let mut out = Vec::new();
    let mut stack = vec![crates];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir).expect("read dir").flatten() {
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().into_owned();
            if path.is_dir() {
                // Only each crate's src tree; tests and fixtures legitimately name bad commands.
                let in_crates_root = dir.ends_with("..");
                if in_crates_root
                    || name == "src"
                    || dir.components().any(|c| c.as_os_str() == "src")
                {
                    stack.push(path);
                }
            } else if path.extension().is_some_and(|e| e == "rs")
                && dir.components().any(|c| c.as_os_str() == "src")
            {
                out.push(path);
            }
        }
    }
    out.sort();
    out
}

/// Drop everything from the first `#[cfg(test)]` line on: test modules sit at file bottom by convention.
fn production_lines(src: &str) -> Vec<(usize, &str)> {
    let mut out = Vec::new();
    for (i, l) in src.lines().enumerate() {
        if l.trim() == "#[cfg(test)]" {
            break;
        }
        if !l.trim_start().starts_with("//") {
            out.push((i + 1, l));
        }
    }
    out
}

/// Find `frob <word>` / `grimble <word>` occurrences at a word boundary in one line.
fn spans_in(file: &Path, line: usize, text: &str, out: &mut Vec<Span>) {
    for product in ["frob", "grimble"] {
        let needle = format!("{product} ");
        let mut from = 0;
        while let Some(at) = text[from..].find(&needle) {
            let start = from + at;
            from = start + needle.len();
            let lead = &text[..start];
            let command_shaped = lead.ends_with('`')
                || lead.ends_with('"')
                || ["run ", "rerun ", "try ", "use ", "or ", "then "]
                    .iter()
                    .any(|p| lead.ends_with(p));
            if !command_shaped {
                continue;
            }
            let rest = &text[from..];
            if !rest.chars().next().is_some_and(|c| c.is_ascii_lowercase()) {
                continue;
            }
            let end = rest
                .find(['`', '"'])
                .into_iter()
                .chain(rest.find(", "))
                .chain(rest.find("frob "))
                .chain(rest.find("grimble "))
                .min()
                .unwrap_or(rest.len());
            out.push(Span {
                file: file.to_path_buf(),
                line,
                product: if product == "frob" { "frob" } else { "grimble" },
                text: rest[..end].to_owned(),
                weak: lead.ends_with('"'),
                log_like: text.contains("tracing::")
                    || (text.trim().starts_with('"') && text.trim().ends_with('"')),
            });
        }
    }
}

/// Check one span against the product's surface; returns a problem description if wrong.
fn check_span(span: &Span, surface: &Surface) -> Option<String> {
    let mut words = span.text.split_whitespace().peekable();
    let mut path = String::new();
    let mut resolved = false;
    while let Some(w) = words.peek() {
        let w = w.trim_end_matches([')', ',', '.', ';', ':']);
        let cand = if path.is_empty() {
            w.to_owned()
        } else {
            format!("{path} {w}")
        };
        let leaf = surface.contains_key(&cand);
        let prefix = surface.keys().any(|k| k.starts_with(&format!("{cand} ")));
        if !(leaf || prefix) {
            break;
        }
        path = cand;
        words.next();
        if leaf {
            resolved = true;
            break;
        }
    }
    if !resolved {
        let first = span.text.split_whitespace().next().unwrap_or("");
        let known_root = surface.keys().any(|k| k.split(' ').next() == Some(first));
        if span.weak && (!known_root || span.log_like) {
            return None;
        }
        // Prose such as "frob is ..." never reaches here with a verb-shaped word; flag only real misses.
        return Some(format!(
            "{} {} is not a verb path",
            span.product,
            span.text.split_whitespace().next().unwrap_or("")
        ));
    }
    let flags = &surface[&path];
    for w in words {
        if let Some(flag) = w.strip_prefix("--") {
            let name: String = flag
                .chars()
                .take_while(|c| c.is_ascii_alphanumeric() || *c == '-')
                .collect();
            if !name.is_empty() && !flags.contains(&name) {
                return Some(format!("{} {path} has no flag --{name}", span.product));
            }
        }
    }
    None
}

/// Collect every command span in production source and return all problems.
fn problems() -> (usize, Vec<String>) {
    let frob = frob_cli::cli().verb_flags();
    let grimble = grimble::cli().verb_flags();
    let mut spans = Vec::new();
    for file in source_files() {
        let src = std::fs::read_to_string(&file).expect("read source");
        for (line, text) in production_lines(&src) {
            spans_in(&file, line, text, &mut spans);
        }
    }
    let mut bad = Vec::new();
    for s in &spans {
        let surface = if s.product == "frob" { &frob } else { &grimble };
        if let Some(why) = check_span(s, surface) {
            bad.push(format!(
                "{}:{}: {why} (in `{}`)",
                s.file.display(),
                s.line,
                s.text
            ));
        }
    }
    (spans.len(), bad)
}

/// Given every remedy string frob can emit, each frob/grimble command and flag it names exists in the registry.
#[test]
fn remedies_name_only_existing_commands_and_flags() {
    let (n, bad) = problems();
    assert!(n > 50, "expected to find many command spans, found {n}");
    assert!(
        bad.is_empty(),
        "remedies naming unknown commands or flags:\n{}",
        bad.join("\n")
    );
}

/// The registry accessor knows the verbs this ticket's remedy points at.
#[test]
fn registry_has_requeue_and_no_lease_release() {
    let frob = frob_cli::cli().verb_flags();
    assert!(frob["requeue"].contains("reason"));
    assert!(!frob.contains_key("lease release"));
    assert!(frob.contains_key("lease widen"));
}

/// The checker rejects an unknown verb and an unknown flag.
#[test]
fn checker_rejects_bad_spans() {
    let frob = frob_cli::cli().verb_flags();
    let mk = |t: &str| Span {
        file: "x".into(),
        line: 1,
        product: "frob",
        text: t.to_owned(),
        weak: false,
        log_like: false,
    };
    assert!(check_span(&mk("lease release T-1"), &frob).is_some());
    assert!(check_span(&mk("requeue <t> --nope x"), &frob).is_some());
    assert!(check_span(&mk("requeue <t> --reason <why>"), &frob).is_none());
}
