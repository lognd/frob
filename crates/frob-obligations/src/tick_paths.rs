//! TICK006: hand-written text that links to a ticket-branch path instead of the ticket's ULID.
// frob:ticket 01M3ZX86MA30ABW915Z943BQYB

use frob_ledger::reindex::GENERATED_MARKER_PREFIX;
use frob_ledger::{Layout, Ledger};
use gob_directives::is_full_ulid;
use gob_rules::{Applicability, Finding, Fix, FixKind, TextEdit};
use gob_text::{FileId, Span};

use crate::legacy::Tick006;
use crate::todo::range;
use crate::util::finding;

/// Characters that end a link-like word.
fn is_delim(c: char) -> bool {
    c.is_whitespace() || "()<>[]{}\"'`,|".contains(c)
}

/// The ULID of an old `tickets/<ULID>/ticket.md` form ending `word`, when it is one.
fn old_form_ulid(word: &str) -> Option<&str> {
    let head = word.strip_suffix("/ticket.md")?;
    let (dir, ulid) = head.rsplit_once('/')?;
    let tickets_dir = dir == "tickets" || dir.ends_with("/tickets");
    (tickets_dir && is_full_ulid(ulid)).then_some(ulid)
}

/// The ticket-branch path inside a blob or tree URL on `branch`, `None` for any other URL.
fn branch_url_path<'a>(url: &'a str, branch: &str) -> Option<&'a str> {
    ["blob", "tree"].iter().find_map(|kind| {
        let marker = format!("/{kind}/{branch}/");
        url.find(&marker).map(|at| &url[at + marker.len()..])
    })
}

/// What `word` refers to: the ULID it should read, or a ticket-branch path no ticket sits at.
enum Target {
    /// The ticket is known; the link is replaced by this ULID.
    Fixable(String),
    /// A ticket-branch URL that names no ticket file (a directory, a deleted ticket).
    Unresolved(String),
}

/// Classify one link-like `word`; `None` when it is not a ticket-branch path.
fn classify(word: &str, ledger: Option<&Ledger>) -> Option<Target> {
    if let Some(ulid) = old_form_ulid(word) {
        return Some(Target::Fixable(ulid.to_owned()));
    }
    let ledger = ledger.filter(|l| l.layout() == Layout::Branch)?;
    let lookup = |path: &str| match ledger.ticket_at_path(path) {
        Ok(found) => found,
        Err(err) => {
            tracing::warn!(%err, path, "TICK006 could not read the ticket branch");
            None
        }
    };
    if word.starts_with("http://") || word.starts_with("https://") {
        let path = branch_url_path(word, &ledger.config().branch)?;
        if path.starts_with("indexes/") {
            return None;
        }
        return Some(match lookup(path) {
            Some(id) => Target::Fixable(id.to_string()),
            None => Target::Unresolved(path.to_owned()),
        });
    }
    let path = word.strip_prefix("./").unwrap_or(word);
    let shaped = std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e == "md")
        && path.matches('/').count() == 1
        && frob_ledger::layout::is_branch_ticket_candidate(path);
    if !shaped {
        return None;
    }
    lookup(path).map(|id| Target::Fixable(id.to_string()))
}

/// True when TICK006 can read the ledger for `text`: only a non-generated text mentioning `.md` is classified against it.
pub fn tick006_reads_ledger(text: &str) -> bool {
    !text.starts_with(GENERATED_MARKER_PREFIX) && text.contains(".md")
}

/// TICK006 over one file's text. Generated pages (first line carries the generated marker) are skipped.
pub(crate) fn tick006(
    file: FileId,
    path: &str,
    text: &str,
    ledger: Option<&Ledger>,
) -> Vec<Finding> {
    if !tick006_reads_ledger(text) {
        return Vec::new();
    }
    let mut out = Vec::new();
    let mut start = None;
    for (at, c) in text.char_indices().chain([(text.len(), ' ')]) {
        match (is_delim(c), start) {
            (false, None) => start = Some(at),
            (true, Some(s)) => {
                start = None;
                out.extend(word_finding(file, path, text, s, at, ledger));
            }
            _ => {}
        }
    }
    out
}

/// The finding for the word at `start..end` of `text`, if it is a ticket-branch path.
fn word_finding(
    file: FileId,
    path: &str,
    text: &str,
    start: usize,
    end: usize,
    ledger: Option<&Ledger>,
) -> Option<Finding> {
    let raw = text[start..end].trim_end_matches(['.', ',', ';', ':', '!', '?', '*']);
    let word = raw.split(['#', '?']).next().unwrap_or(raw);
    if !word.contains(".md") && !word.contains("/tree/") {
        return None;
    }
    let target = classify(word, ledger)?;
    let span = Span::new(file, range(start, word.len()));
    let (message, fix) = match &target {
        Target::Fixable(ulid) => (
            format!(
                "{path}: `{word}` is a ticket-branch path, which changes when the ticket is retitled or reparented; \
                 link the ticket by its ULID `{ulid}` (`--fix` rewrites it)"
            ),
            Some(Fix {
                kind: FixKind::Deterministic,
                // frob:ticket 01M3ZX7E968R74N08V8DW4RJVG
                applicability: Applicability::Machine,
                title: "replace the ticket-branch path with the ticket ULID".to_owned(),
                edits: vec![TextEdit {
                    file,
                    range: span.range,
                    replacement: ulid.clone(),
                }],
            }),
        ),
        Target::Unresolved(branch_path) => (
            format!(
                "{path}: `{word}` links the ticket branch path `{branch_path}`, which names no ticket file; \
                 link the ticket by its ULID, or `indexes/by-id/` for a stable page"
            ),
            None,
        ),
    };
    let mut f = finding(&Tick006, Some(span), message, word);
    f.fix = fix;
    Some(f)
}

/// TICK006 over a hand-written file of the ticket branch (`path` is the ledger path), classified against `ledger`.
///
/// The file is not in the working tree, so the findings carry no span and no fix: the link is edited in the
/// ticket (`frob ticket edit`), which writes the ULID.
// frob:ticket 01M4P8M16T2T3Y311ER1Z77KSE
pub fn tick006_ledger_file(path: &str, text: &str, ledger: &Ledger) -> Vec<Finding> {
    let file = gob_text::FileInterner::new().intern(path);
    let mut found = tick006(file, path, text, Some(ledger));
    for f in &mut found {
        f.span = None;
        f.fix = None;
    }
    tracing::debug!(
        path,
        findings = found.len(),
        "TICK006 scanned a ledger file"
    );
    found
}

#[cfg(test)]
mod tests {
    use super::*;

    const ULID: &str = "01M3ZX86MA30ABW915Z943BQYB";

    fn run(text: &str) -> Vec<Finding> {
        let file = gob_text::FileInterner::new().intern("doc.md");
        tick006(file, "doc.md", text, None)
    }

    #[test]
    fn old_ticket_path_form_fires_and_the_fix_rewrites_it_to_the_ulid() {
        // frob:tests crates/frob-obligations/src/tick_paths.rs::tick006
        let text = format!("see tickets/{ULID}/ticket.md for details");
        let found = run(&text);
        assert_eq!(found.len(), 1);
        let edit = &found[0].fix.as_ref().expect("fix").edits[0];
        assert_eq!(edit.replacement, ULID);
        assert_eq!(
            &text[edit.range.to_usize_range()],
            format!("tickets/{ULID}/ticket.md")
        );
    }

    #[test]
    fn generated_pages_and_plain_links_do_not_fire() {
        let generated =
            format!("{GENERATED_MARKER_PREFIX} v1: DO NOT EDIT -->\ntickets/{ULID}/ticket.md\n");
        assert!(run(&generated).is_empty());
        assert!(run("see docs/design/navigation.md and [x](a/b.md) and ../README.md").is_empty());
    }
}
