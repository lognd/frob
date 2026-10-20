//! Plugin findings name file handles from the call's subject set, never path
//! strings (security.md 2.10, I5, SEC-08).
//!
//! A finding is accepted only when its primary and secondary spans each name a
//! [`FileHandle`] present in the [`SubjectSet`] the plugin was given for that
//! call and carry a byte range inside that file. Anything else is dropped and
//! reported as a [`Dropped`] value; snippets are rendered later from the
//! in-memory snapshot, never from a fresh disk read.

// frob:ticket 01M3ZX8024ZDDKTHWBRB47ADX9

use std::collections::BTreeMap;

/// An opaque handle for one file of a call's subject set.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct FileHandle(pub u32);

/// How a plugin names a file: a handle, or a (refused) path string.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FileRef {
    /// A handle, valid only if it belongs to the subject set.
    Handle(FileHandle),
    /// A path string; always refused, plugins name handles.
    Path(String),
}

/// A byte range `start..end` inside one named file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawSpan {
    /// The file the range is in.
    pub file: FileRef,
    /// First byte of the range.
    pub start: usize,
    /// One past the last byte of the range.
    pub end: usize,
}

/// A finding as a plugin returned it, before validation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawFinding {
    /// The rule or plugin check that produced it.
    pub code: String,
    /// The primary span.
    pub primary: RawSpan,
    /// Secondary spans, only in files the plugin was given.
    pub secondary: Vec<RawSpan>,
}

/// A validated span: a subject-set handle and an in-range byte range.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Span {
    /// The subject-set file.
    pub file: FileHandle,
    /// First byte of the range.
    pub start: usize,
    /// One past the last byte of the range.
    pub end: usize,
}

/// A finding whose every span was validated against the subject set.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    /// The rule or plugin check that produced it.
    pub code: String,
    /// The primary span.
    pub primary: Span,
    /// Secondary spans.
    pub secondary: Vec<Span>,
}

/// Why a finding was dropped.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum Dropped {
    /// The finding named a path string instead of a handle.
    #[error("finding {code}: names path string `{path}`, not a subject-set handle")]
    PathString {
        /// The finding's code.
        code: String,
        /// The string the plugin named.
        path: String,
    },
    /// The handle is not in the subject set of this call.
    #[error("finding {code}: handle {handle} is outside the subject set")]
    UnknownHandle {
        /// The finding's code.
        code: String,
        /// The offending handle.
        handle: u32,
    },
    /// The byte range is inverted or past the end of the file.
    #[error("finding {code}: byte range {start}..{end} is outside file {handle} ({len} bytes)")]
    BadRange {
        /// The finding's code.
        code: String,
        /// The file handle.
        handle: u32,
        /// Range start.
        start: usize,
        /// Range end.
        end: usize,
        /// The file's length in bytes.
        len: usize,
    },
}

/// The files a plugin was given for one call, with their byte lengths.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SubjectSet {
    files: BTreeMap<FileHandle, usize>,
}

impl SubjectSet {
    /// An empty subject set.
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds `handle` with its file length in bytes.
    pub fn insert(&mut self, handle: FileHandle, len: usize) {
        tracing::debug!(handle = handle.0, len, "subject set: file added");
        self.files.insert(handle, len);
    }

    /// Validates one span of finding `code`.
    fn check_span(&self, code: &str, raw: &RawSpan) -> Result<Span, Dropped> {
        let handle = match &raw.file {
            FileRef::Path(path) => {
                return Err(Dropped::PathString {
                    code: code.to_owned(),
                    path: path.clone(),
                });
            }
            FileRef::Handle(h) => *h,
        };
        let Some(&len) = self.files.get(&handle) else {
            return Err(Dropped::UnknownHandle {
                code: code.to_owned(),
                handle: handle.0,
            });
        };
        if raw.start > raw.end || raw.end > len {
            return Err(Dropped::BadRange {
                code: code.to_owned(),
                handle: handle.0,
                start: raw.start,
                end: raw.end,
                len,
            });
        }
        Ok(Span {
            file: handle,
            start: raw.start,
            end: raw.end,
        })
    }

    /// Accepts `raw` only if every span names a subject-set handle with an in-range byte range.
    ///
    /// # Errors
    /// [`Dropped`] for a path string, a handle outside the set, or a bad byte range.
    pub fn accept(&self, raw: &RawFinding) -> Result<Finding, Dropped> {
        let result = (|| {
            let primary = self.check_span(&raw.code, &raw.primary)?;
            let secondary = raw
                .secondary
                .iter()
                .map(|s| self.check_span(&raw.code, s))
                .collect::<Result<Vec<_>, _>>()?;
            Ok(Finding {
                code: raw.code.clone(),
                primary,
                secondary,
            })
        })();
        match &result {
            Ok(_) => tracing::debug!(code = %raw.code, "finding accepted"),
            Err(why) => tracing::warn!(%why, "finding dropped"),
        }
        result
    }

    /// Accepts every valid finding and reports each dropped one.
    pub fn accept_all(&self, raw: &[RawFinding]) -> (Vec<Finding>, Vec<Dropped>) {
        let mut kept = Vec::new();
        let mut dropped = Vec::new();
        for f in raw {
            match self.accept(f) {
                Ok(f) => kept.push(f),
                Err(d) => dropped.push(d),
            }
        }
        (kept, dropped)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn span(file: FileRef, start: usize, end: usize) -> RawSpan {
        RawSpan { file, start, end }
    }

    fn set() -> SubjectSet {
        let mut s = SubjectSet::new();
        s.insert(FileHandle(1), 100);
        s
    }

    fn finding(primary: RawSpan, secondary: Vec<RawSpan>) -> RawFinding {
        RawFinding {
            code: "X001".into(),
            primary,
            secondary,
        }
    }

    #[test]
    fn path_string_outside_subject_set_is_dropped_and_reported() {
        let raw = finding(span(FileRef::Path("/etc/passwd".into()), 0, 1), vec![]);
        let (kept, dropped) = set().accept_all(&[raw]);
        assert!(kept.is_empty());
        assert!(
            matches!(&dropped[..], [Dropped::PathString { path, .. }] if path == "/etc/passwd")
        );
    }

    #[test]
    fn out_of_range_byte_range_on_valid_handle_is_dropped_and_reported() {
        let raw = finding(span(FileRef::Handle(FileHandle(1)), 90, 101), vec![]);
        let (kept, dropped) = set().accept_all(&[raw]);
        assert!(kept.is_empty());
        assert!(matches!(&dropped[..], [Dropped::BadRange { len: 100, .. }]));
    }

    #[test]
    fn valid_finding_is_accepted() {
        let raw = finding(
            span(FileRef::Handle(FileHandle(1)), 0, 100),
            vec![span(FileRef::Handle(FileHandle(1)), 5, 5)],
        );
        let f = set().accept(&raw).unwrap();
        assert_eq!(f.secondary.len(), 1);
    }

    #[test]
    fn secondary_span_in_unknown_file_drops_the_finding() {
        let raw = finding(
            span(FileRef::Handle(FileHandle(1)), 0, 1),
            vec![span(FileRef::Handle(FileHandle(9)), 0, 1)],
        );
        assert!(matches!(
            set().accept(&raw),
            Err(Dropped::UnknownHandle { handle: 9, .. })
        ));
    }

    #[test]
    fn inverted_range_is_dropped() {
        let raw = finding(span(FileRef::Handle(FileHandle(1)), 10, 5), vec![]);
        assert!(matches!(set().accept(&raw), Err(Dropped::BadRange { .. })));
    }
}
