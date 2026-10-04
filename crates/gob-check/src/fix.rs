//! `--fix` tier A: apply the edits of Deterministic fixes.

// frob:ticket 01M42MGPHZVTJWJHEGJWS4WZBD

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::path::Path;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_rules::{Finding, FixKind};
use gob_text::FileInterner;
use gob_walk::{ContentSource, Digest};

use crate::error::CheckError;
use crate::report::AppliedFix;
use gob_fs::write_atomic;

/// One edit resolved to a path and byte range.
struct Edit {
    start: usize,
    end: usize,
    replacement: String,
}

/// Fixes written and fixes dropped for overlapping an earlier one.
#[derive(Debug)]
pub(crate) struct FixRun {
    /// The fixes that were written.
    pub applied: Vec<AppliedFix>,
    /// Fixes skipped because an edit overlapped an accepted one.
    pub skipped_overlap: usize,
    /// Fixes skipped because an edit was out of range for the file.
    pub skipped_invalid: usize,
    /// Fixes dropped because their result no longer parsed.
    pub rolled_back: usize,
}

/// One Deterministic fix resolved to paths and byte ranges.
struct Candidate {
    rule: String,
    title: String,
    edits: Vec<(String, Edit)>,
}

impl Candidate {
    fn touches(&self, files: &BTreeSet<String>) -> bool {
        self.edits.iter().any(|(p, _)| files.contains(p))
    }
}

fn in_range(text: &str, e: &Edit) -> bool {
    e.start <= e.end
        && e.end <= text.len()
        && text.is_char_boundary(e.start)
        && text.is_char_boundary(e.end)
}

/// The text of `old` after applying every accepted edit of `path`.
fn rewritten(path: &str, old: &str, accepted: &[Candidate]) -> String {
    let mut list: Vec<&Edit> = accepted
        .iter()
        .flat_map(|c| c.edits.iter().filter(|(p, _)| p == path).map(|(_, e)| e))
        .collect();
    list.sort_by_key(|e| std::cmp::Reverse(e.start));
    let mut text = old.to_owned();
    for e in list {
        text.replace_range(e.start..e.end, &e.replacement);
    }
    text
}

/// Whether `new` fails to parse in its language while `old` parsed cleanly.
fn breaks_syntax(path: &str, old: &str, new: &str) -> bool {
    let Some(lang) = Language::detect(path) else {
        return false;
    };
    let limits = ParseLimits::default();
    let errors = |text: &str| match parse(lang, text, &limits) {
        ParseResult::Parsed(t) => Some(t.has_errors()),
        ParseResult::Unresolved(_) => None,
    };
    errors(new) == Some(true) && errors(old) == Some(false)
}

fn overlaps(accepted: &[(usize, usize)], start: usize, end: usize) -> bool {
    accepted
        .iter()
        .any(|&(s, e)| start < e.max(s + 1) && s < end.max(start + 1))
}

/// Apply every Deterministic fix among `findings` and write the files.
///
/// A fix is atomic: when any of its edits is out of range, overlaps an edit
/// already accepted for the same file, or leaves its file unparsable, the whole
/// fix is skipped (the next run offers it again). Every touched file is first
/// checked against its digest at analysis (`analysed`); a changed file refuses
/// the run before anything is written. Writes are atomic per file and a failed
/// write restores the files already written.
///
/// # Errors
///
/// [`CheckError::FixStale`] when a file changed since the check;
/// [`CheckError::FixIo`] with `E-CHECK-FIX-IO` when a file cannot be read or written.
pub(crate) fn apply(
    root: &Path,
    findings: &[Finding],
    files: &FileInterner,
    analysed: &HashMap<String, String>,
    raw: &HashMap<String, String>,
) -> Result<FixRun, CheckError> {
    let mut candidates = Vec::new();
    for f in findings {
        let Some(fix) = f.fix.as_ref().filter(|x| x.kind == FixKind::Deterministic) else {
            continue;
        };
        let resolved: Option<Vec<(String, Edit)>> = fix
            .edits
            .iter()
            .map(|e| {
                files.path(e.file).map(|p| {
                    (
                        p.to_owned(),
                        Edit {
                            start: u32::from(e.range.start()) as usize,
                            end: u32::from(e.range.end()) as usize,
                            replacement: e.replacement.clone(),
                        },
                    )
                })
            })
            .collect();
        let Some(edits) = resolved.filter(|r| !r.is_empty()) else {
            tracing::warn!(rule = %f.rule, "fix names an unknown file; skipped");
            continue;
        };
        candidates.push(Candidate {
            rule: f.rule.to_string(),
            title: fix.title.clone(),
            edits,
        });
    }

    let originals = load_checked(root, &candidates, analysed, raw)?;

    let mut accepted: Vec<Candidate> = Vec::new();
    let mut ranges: BTreeMap<String, Vec<(usize, usize)>> = BTreeMap::new();
    let mut skipped_overlap = 0;
    let mut skipped_invalid = 0;
    for c in candidates {
        if c.edits.iter().any(|(p, e)| !in_range(&originals[p], e)) {
            tracing::warn!(rule = %c.rule, title = %c.title, "fix has an out-of-range edit; whole fix skipped");
            skipped_invalid += 1;
            continue;
        }
        if c.edits
            .iter()
            .any(|(p, e)| ranges.get(p).is_some_and(|a| overlaps(a, e.start, e.end)))
        {
            tracing::info!(rule = %c.rule, title = %c.title, "fix overlaps an accepted fix; skipped");
            skipped_overlap += 1;
            continue;
        }
        for (p, e) in &c.edits {
            ranges.entry(p.clone()).or_default().push((e.start, e.end));
        }
        accepted.push(c);
    }

    let mut rolled_back = 0;
    let outputs = loop {
        let touched: BTreeSet<&String> = accepted
            .iter()
            .flat_map(|c| c.edits.iter().map(|(p, _)| p))
            .collect();
        let outputs: BTreeMap<String, String> = touched
            .into_iter()
            .map(|p| (p.clone(), rewritten(p, &originals[p], &accepted)))
            .collect();
        let broken: BTreeSet<String> = outputs
            .iter()
            .filter(|(p, new)| breaks_syntax(p, &originals[*p], new))
            .map(|(p, _)| p.clone())
            .collect();
        if broken.is_empty() {
            break outputs;
        }
        let before = accepted.len();
        accepted.retain(|c| !c.touches(&broken));
        let dropped = before - accepted.len();
        rolled_back += dropped;
        tracing::warn!(files = ?broken, dropped, "fix result no longer parses; fixes rolled back");
    };

    write_all(root, &outputs, &originals)?;

    let mut applied: Vec<AppliedFix> = accepted
        .iter()
        .map(|c| AppliedFix {
            rule: c.rule.clone(),
            file: c.edits[0].0.clone(),
            title: c.title.clone(),
        })
        .collect();
    applied.sort_by(|a, b| (&a.file, &a.rule).cmp(&(&b.file, &b.rule)));
    Ok(FixRun {
        applied,
        skipped_overlap,
        skipped_invalid,
        rolled_back,
    })
}

/// The `E-FIX-STALE` refusal for `path`.
fn stale(path: &str) -> CheckError {
    CheckError::FixStale(path.to_owned())
}

/// Digest the exact raw bytes of every file a Deterministic fix edits (the offsets' basis).
pub(crate) fn raw_digests(
    root: &Path,
    findings: &[Finding],
    files: &FileInterner,
) -> HashMap<String, String> {
    let mut out = HashMap::new();
    for e in findings
        .iter()
        .filter_map(|f| f.fix.as_ref().filter(|x| x.kind == FixKind::Deterministic))
        .flat_map(|f| &f.edits)
    {
        let Some(path) = files.path(e.file) else {
            continue;
        };
        if let Ok(bytes) = std::fs::read(root.join(path)) {
            out.insert(path.to_owned(), Digest::of(&bytes).to_string());
        }
    }
    out
}

/// Read every file the candidates touch and refuse any whose digest is not the analysed one.
fn load_checked(
    root: &Path,
    candidates: &[Candidate],
    analysed: &HashMap<String, String>,
    raw: &HashMap<String, String>,
) -> Result<BTreeMap<String, String>, CheckError> {
    let paths: BTreeSet<&String> = candidates
        .iter()
        .flat_map(|c| c.edits.iter().map(|(p, _)| p))
        .collect();
    let source = ContentSource::locate(root);
    let mut originals = BTreeMap::new();
    for path in paths {
        let now = source
            .with_reader(|r| r.read(path))
            .map_err(|e| CheckError::FixIo(format!("E-CHECK-FIX-IO: read {path}: {e}")))?;
        if analysed.get(path).map(String::as_str) != Some(Digest::of(&now).to_string().as_str()) {
            tracing::warn!(path, "file changed since analysis; --fix refused");
            return Err(stale(path));
        }
        let bytes = std::fs::read(root.join(path))
            .map_err(|e| CheckError::FixIo(format!("E-CHECK-FIX-IO: read {path}: {e}")))?;
        if raw.get(path).map(String::as_str) != Some(Digest::of(&bytes).to_string().as_str()) {
            tracing::warn!(path, "raw bytes changed since analysis; --fix refused");
            return Err(stale(path));
        }
        let text = String::from_utf8(bytes).map_err(|e| {
            CheckError::FixIo(format!("E-CHECK-FIX-IO: read {path}: not UTF-8: {e}"))
        })?;
        originals.insert(path.clone(), text);
    }
    Ok(originals)
}

/// Write every output atomically; on a failure restore the files already written.
fn write_all(
    root: &Path,
    outputs: &BTreeMap<String, String>,
    originals: &BTreeMap<String, String>,
) -> Result<(), CheckError> {
    let mut written: Vec<&String> = Vec::new();
    for (path, text) in outputs {
        if let Err(err) = write_atomic(&root.join(path), text.as_bytes()) {
            for done in &written {
                if let Err(e) = write_atomic(&root.join(done), originals[*done].as_bytes()) {
                    tracing::error!(path = %done, err = %e, "restore after failed fix failed");
                }
            }
            return Err(CheckError::FixIo(format!(
                "E-CHECK-FIX-IO: write {path}: {err}"
            )));
        }
        tracing::info!(path, "fix written");
        written.push(path);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_rules::{Fix, Severity, TextEdit};
    use gob_text::{FileId, TextRange, TextSize};

    struct Fx {
        dir: tempfile::TempDir,
        files: FileInterner,
        analysed: HashMap<String, String>,
        raw: HashMap<String, String>,
    }

    impl Fx {
        fn new(files: &[(&str, &str)]) -> Self {
            let dir = tempfile::tempdir().unwrap();
            let mut interner = FileInterner::new();
            let mut analysed = HashMap::new();
            let mut raw = HashMap::new();
            for (name, text) in files {
                std::fs::write(dir.path().join(name), text).unwrap();
                interner.intern(name);
                analysed.insert((*name).to_owned(), Digest::of(text.as_bytes()).to_string());
                raw.insert((*name).to_owned(), Digest::of(text.as_bytes()).to_string());
            }
            Self {
                dir,
                files: interner,
                analysed,
                raw,
            }
        }

        fn id(&mut self, name: &str) -> FileId {
            self.files.intern(name)
        }

        fn edit(&mut self, name: &str, start: u32, end: u32, with: &str) -> TextEdit {
            TextEdit {
                file: self.id(name),
                range: TextRange::new(TextSize::from(start), TextSize::from(end)),
                replacement: with.to_owned(),
            }
        }

        fn finding(edits: Vec<TextEdit>) -> Finding {
            Finding::new(
                "TOY001".parse().unwrap(),
                Severity::Warn,
                None,
                "fixable",
                "anchor",
            )
            .with_fix(Fix {
                kind: FixKind::Deterministic,
                title: "fix".to_owned(),
                edits,
            })
        }

        fn run(&self, findings: &[Finding]) -> Result<FixRun, CheckError> {
            apply(
                self.dir.path(),
                findings,
                &self.files,
                &self.analysed,
                &self.raw,
            )
        }

        fn read(&self, name: &str) -> String {
            std::fs::read_to_string(self.dir.path().join(name)).unwrap()
        }
    }

    // frob:tests crates/gob-check/src/fix.rs::apply
    #[test]
    fn applies_a_fix_atomically_to_a_fresh_file() {
        let mut fx = Fx::new(&[("a.txt", "hello world")]);
        let f = Fx::finding(vec![fx.edit("a.txt", 0, 5, "howdy")]);
        let out = fx.run(&[f]).unwrap();
        assert_eq!(out.applied.len(), 1);
        assert_eq!(fx.read("a.txt"), "howdy world");
    }

    // frob:tests crates/gob-check/src/fix.rs::apply
    #[test]
    fn refuses_a_file_edited_since_the_check_and_writes_nothing() {
        let mut fx = Fx::new(&[("a.txt", "hello world"), ("b.txt", "other")]);
        let fa = Fx::finding(vec![fx.edit("a.txt", 0, 5, "howdy")]);
        let fb = Fx::finding(vec![fx.edit("b.txt", 0, 5, "OTHER")]);
        std::fs::write(fx.dir.path().join("b.txt"), "other, edited").unwrap();
        let err = fx.run(&[fa, fb]).unwrap_err();
        assert!(
            matches!(&err, CheckError::FixStale(p) if p == "b.txt"),
            "{err}"
        );
        assert!(err.to_string().contains("E-FIX-STALE"));
        assert_eq!(fx.read("a.txt"), "hello world");
        assert_eq!(fx.read("b.txt"), "other, edited");
    }

    // frob:tests crates/gob-check/src/fix.rs::apply
    #[test]
    fn a_line_ending_only_edit_since_the_check_is_refused() {
        let mut fx = Fx::new(&[("a.txt", "one\ntwo\n")]);
        let f = Fx::finding(vec![fx.edit("a.txt", 0, 3, "ONE")]);
        // The walk digest (git-normalised) still matches; only the raw bytes differ.
        std::fs::write(fx.dir.path().join("a.txt"), "one\r\ntwo\r\n").unwrap();
        let mut analysed = fx.analysed.clone();
        analysed.insert(
            "a.txt".to_owned(),
            Digest::of(b"one\r\ntwo\r\n").to_string(),
        );
        let err = apply(fx.dir.path(), &[f], &fx.files, &analysed, &fx.raw).unwrap_err();
        assert!(err.to_string().starts_with("E-FIX-STALE: a.txt"), "{err}");
        assert_eq!(fx.read("a.txt"), "one\r\ntwo\r\n");
    }

    // frob:tests crates/gob-check/src/fix.rs::apply
    #[test]
    fn one_out_of_range_edit_skips_the_whole_fix() {
        let mut fx = Fx::new(&[("a.txt", "hello world")]);
        let bad = Fx::finding(vec![
            fx.edit("a.txt", 0, 5, "howdy"),
            fx.edit("a.txt", 6, 99, "x"),
        ]);
        let out = fx.run(&[bad]).unwrap();
        assert!(out.applied.is_empty());
        assert_eq!(out.skipped_invalid, 1);
        assert_eq!(fx.read("a.txt"), "hello world");
    }

    // frob:tests crates/gob-check/src/fix.rs::apply
    #[test]
    fn a_fix_that_breaks_syntax_is_rolled_back_and_not_applied() {
        let mut fx = Fx::new(&[("a.rs", "fn a() {}\n"), ("b.txt", "keep")]);
        let breaker = Fx::finding(vec![fx.edit("a.rs", 8, 9, "")]);
        let fine = Fx::finding(vec![fx.edit("b.txt", 0, 4, "kept")]);
        let out = fx.run(&[breaker, fine]).unwrap();
        assert_eq!(out.rolled_back, 1);
        assert_eq!(out.applied.len(), 1);
        assert_eq!(fx.read("a.rs"), "fn a() {}\n");
        assert_eq!(fx.read("b.txt"), "kept");
    }

    // frob:tests crates/gob-check/src/fix.rs::write_all
    #[test]
    fn a_failed_second_write_restores_the_first_file() {
        let fx = Fx::new(&[("a.txt", "one"), ("b.txt", "two")]);
        // A directory in place of b.txt makes its rename fail after a.txt was written.
        let outputs: BTreeMap<String, String> = [("a.txt", "ONE"), ("b.txt", "TWO")]
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
            .collect();
        let originals: BTreeMap<String, String> = [("a.txt", "one"), ("b.txt", "two")]
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
            .collect();
        std::fs::remove_file(fx.dir.path().join("b.txt")).unwrap();
        std::fs::create_dir(fx.dir.path().join("b.txt")).unwrap();
        let err = write_all(fx.dir.path(), &outputs, &originals).unwrap_err();
        assert!(matches!(err, CheckError::FixIo(_)));
        assert_eq!(fx.read("a.txt"), "one");
    }
}
