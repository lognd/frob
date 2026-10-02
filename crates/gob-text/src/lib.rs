//! Text primitives (spans, line index, source text) shared by every goblin.
//!
//! # `ruff_text_size` decision
//!
//! `ruff_text_size` (0.0.16 on crates.io) was evaluated. Its API shape is
//! what we want (`u32` newtypes), but it is published as an internal
//! component of Ruff at `0.0.x` with no stability promise, so a Ruff
//! release could break every goblin. We therefore implement small `u32`
//! newtypes ([`TextSize`], [`TextRange`]) with the same core vocabulary.
//!
//! # Overview
//!
//! - [`TextSize`] / [`TextRange`]: byte offsets and half-open byte ranges.
//! - [`LineIndex`]: byte offset to 1-based line/column (and UTF-16 column).
//! - [`SourceText`]: shared source text with a lazily built [`LineIndex`].
//! - [`FileId`] / [`FileInterner`]: interned file identity.
//! - [`Span`]: a [`FileId`] plus a [`TextRange`].
//! - [`Snippet`]: the source line of a span with a caret line beneath it.
//!
//! ```
//! use gob_text::{SourceText, TextRange, render_snippet};
//!
//! let src = SourceText::new("let x = 1;\nlet y = oops;\n").unwrap();
//! let snip = render_snippet(&src, TextRange::at(19u32.into(), 4u32.into())).unwrap();
//! assert_eq!(snip.to_string(), "let y = oops;\n        ^^^^");
//! ```

mod file;
mod line_index;
mod size;
mod snippet;
mod source;

pub use file::{FileId, FileInterner, Span};
pub use line_index::{LineCol, LineIndex};
pub use size::{TextRange, TextSize, TextTooLarge};
pub use snippet::{Snippet, render_snippet};
pub use source::SourceText;
