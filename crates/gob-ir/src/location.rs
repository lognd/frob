//! Locations: values of an address sort with a total order and containment
//! (universal-model.md 2.5). Locations are not byte offsets.

#![allow(
    clippy::many_single_char_names,
    reason = "paired field bindings in symmetric matches"
)]

use std::cmp::Ordering;
use std::fmt;

use gob_text::{FileId, Span, TextRange};

/// An address of a node inside an artifact.
///
/// ```
/// use gob_ir::Location;
/// use gob_text::FileInterner;
/// let mut files = FileInterner::new();
/// let f = files.intern("a.rs");
/// let outer = Location::text(f, 0, 100);
/// let inner = Location::text(f, 10, 20);
/// assert!(outer.contains(&inner));
/// assert!(outer < Location::text(f, 5, 6));
/// ```
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Location {
    /// A byte range of a text artifact.
    Text {
        /// The artifact.
        file: FileId,
        /// Byte range, half-open.
        range: TextRange,
    },
    /// A cell of a grid (spreadsheet sheet, board).
    Grid {
        /// Interned id of the sheet (for example `book.xlsx#Sheet1`).
        sheet: FileId,
        /// Zero-based row.
        row: u32,
        /// Zero-based column.
        col: u32,
    },
    /// A node (and optionally a port) of a graph document.
    Graph {
        /// The document.
        doc: FileId,
        /// Node id inside the document.
        node: String,
        /// Port of the node, when the address names one.
        port: Option<String>,
    },
    /// An element of a stream artifact.
    Stream {
        /// The artifact.
        artifact: FileId,
        /// Sequence number.
        seq: u64,
    },
    /// A byte range inside a notebook cell.
    Notebook {
        /// The notebook.
        nb: FileId,
        /// Zero-based cell index.
        cell: u32,
        /// Byte range inside the cell source.
        range: TextRange,
    },
    /// A JSON pointer into a structured artifact.
    Pointer {
        /// The artifact.
        artifact: FileId,
        /// RFC 6901 pointer, `""` for the document root.
        json_pointer: String,
    },
}

impl Location {
    /// A text location from raw byte offsets.
    ///
    /// # Panics
    ///
    /// Panics if `start > end` (a programmer bug).
    pub fn text(file: FileId, start: u32, end: u32) -> Self {
        Self::Text {
            file,
            range: TextRange::new(start.into(), end.into()),
        }
    }

    /// The artifact this location addresses.
    pub fn artifact(&self) -> FileId {
        match self {
            Self::Text { file, .. } => *file,
            Self::Grid { sheet, .. } => *sheet,
            Self::Graph { doc, .. } => *doc,
            Self::Stream { artifact, .. } | Self::Pointer { artifact, .. } => *artifact,
            Self::Notebook { nb, .. } => *nb,
        }
    }

    /// The text span, for the text variant only.
    pub fn span(&self) -> Option<Span> {
        match self {
            Self::Text { file, range } => Some(Span::new(*file, *range)),
            _ => None,
        }
    }

    /// Whether `other` lies inside `self` (reflexive; false across address sorts).
    pub fn contains(&self, other: &Self) -> bool {
        match (self, other) {
            (Self::Text { file: a, range: r }, Self::Text { file: b, range: s }) => {
                a == b && r.contains_range(*s)
            }
            (
                Self::Notebook {
                    nb: a,
                    cell: c,
                    range: r,
                },
                Self::Notebook {
                    nb: b,
                    cell: d,
                    range: s,
                },
            ) => a == b && c == d && r.contains_range(*s),
            (
                Self::Graph {
                    doc: a,
                    node: n,
                    port: p,
                },
                Self::Graph {
                    doc: b,
                    node: m,
                    port: q,
                },
            ) => a == b && n == m && (p.is_none() || p == q),
            (
                Self::Pointer {
                    artifact: a,
                    json_pointer: p,
                },
                Self::Pointer {
                    artifact: b,
                    json_pointer: q,
                },
            ) => {
                a == b
                    && (p == q
                        || p.is_empty()
                        || (q.starts_with(p.as_str()) && q[p.len()..].starts_with('/')))
            }
            (a, b) => a == b,
        }
    }

    fn rank(&self) -> u8 {
        match self {
            Self::Text { .. } => 0,
            Self::Grid { .. } => 1,
            Self::Graph { .. } => 2,
            Self::Stream { .. } => 3,
            Self::Notebook { .. } => 4,
            Self::Pointer { .. } => 5,
        }
    }
}

fn range_key(r: TextRange) -> (u32, u32) {
    (r.start().into(), r.end().into())
}

impl Ord for Location {
    /// Address sort first, then artifact, then position; ranges order by start, then wider first.
    fn cmp(&self, other: &Self) -> Ordering {
        let sort = self.rank().cmp(&other.rank());
        if sort != Ordering::Equal {
            return sort;
        }
        match (self, other) {
            (Self::Text { file: a, range: r }, Self::Text { file: b, range: s }) => {
                let (rs, re) = range_key(*r);
                let (ss, se) = range_key(*s);
                a.cmp(b).then(rs.cmp(&ss)).then(se.cmp(&re))
            }
            (
                Self::Grid {
                    sheet: a,
                    row: r,
                    col: c,
                },
                Self::Grid {
                    sheet: b,
                    row: s,
                    col: d,
                },
            ) => a.cmp(b).then(r.cmp(s)).then(c.cmp(d)),
            (
                Self::Graph {
                    doc: a,
                    node: n,
                    port: p,
                },
                Self::Graph {
                    doc: b,
                    node: m,
                    port: q,
                },
            ) => a.cmp(b).then_with(|| n.cmp(m)).then_with(|| p.cmp(q)),
            (
                Self::Stream {
                    artifact: a,
                    seq: s,
                },
                Self::Stream {
                    artifact: b,
                    seq: t,
                },
            ) => a.cmp(b).then(s.cmp(t)),
            (
                Self::Notebook {
                    nb: a,
                    cell: c,
                    range: r,
                },
                Self::Notebook {
                    nb: b,
                    cell: d,
                    range: s,
                },
            ) => {
                let (rs, re) = range_key(*r);
                let (ss, se) = range_key(*s);
                a.cmp(b).then(c.cmp(d)).then(rs.cmp(&ss)).then(se.cmp(&re))
            }
            (
                Self::Pointer {
                    artifact: a,
                    json_pointer: p,
                },
                Self::Pointer {
                    artifact: b,
                    json_pointer: q,
                },
            ) => a.cmp(b).then_with(|| p.cmp(q)),
            _ => Ordering::Equal,
        }
    }
}

impl PartialOrd for Location {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl fmt::Display for Location {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Text { file, range } => write!(f, "{file}:{range}"),
            Self::Grid { sheet, row, col } => write!(f, "{sheet}!r{row}c{col}"),
            Self::Graph { doc, node, port } => match port {
                Some(p) => write!(f, "{doc}/{node}.{p}"),
                None => write!(f, "{doc}/{node}"),
            },
            Self::Stream { artifact, seq } => write!(f, "{artifact}@{seq}"),
            Self::Notebook { nb, cell, range } => write!(f, "{nb}#cell{cell}:{range}"),
            Self::Pointer {
                artifact,
                json_pointer,
            } => write!(f, "{artifact}{{{json_pointer}}}"),
        }
    }
}
