//! Class-list fragments that may contain computed pieces.
//!
//! A template literal such as `` `p-4 z-${n} ${on} flex` `` arrives as segments
//! (`Static("p-4 z-")`, `Dynamic`, `Static(" "`) ...). Whitespace separates tokens; a token that
//! touches a [`Segment::Dynamic`] without whitespace is never guessed at (`z-${n}` is not
//! `z-`), it is reported as a [`DynamicToken`]. Only fully static tokens become candidates.

use crate::candidate::{Candidate, CandidateError, parse_candidate};

/// One piece of a class-list expression.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Segment<'a> {
    /// Literal text, possibly holding several whitespace-separated tokens.
    Static(&'a str),
    /// A computed piece (interpolation, call result, identifier).
    Dynamic,
}

/// A token that has a computed part and so yields no candidate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DynamicToken {
    /// The static text glued to the computed part (empty for a bare interpolation).
    pub partial: String,
}

/// The result of parsing a class-list fragment.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ClassListParse {
    /// Candidates from the fully static, well-formed tokens, in source order.
    pub candidates: Vec<Candidate>,
    /// Tokens with a computed part, in source order.
    pub dynamic: Vec<DynamicToken>,
    /// Static tokens that are not well-formed candidates, with the reason.
    pub invalid: Vec<(String, CandidateError)>,
}

/// Accumulates the token in progress while scanning segments.
struct Scan {
    out: ClassListParse,
    token: String,
    dynamic: bool,
}

impl Scan {
    /// Finish the token in progress, if any.
    fn flush(&mut self) {
        if self.dynamic {
            tracing::debug!(partial = %self.token, "dynamic class token");
            self.out.dynamic.push(DynamicToken {
                partial: std::mem::take(&mut self.token),
            });
        } else if !self.token.is_empty() {
            let token = std::mem::take(&mut self.token);
            match parse_candidate(&token) {
                Ok(c) => self.out.candidates.push(c),
                Err(e) => {
                    tracing::debug!(%token, error = %e, "invalid class token");
                    self.out.invalid.push((token, e));
                }
            }
        }
        self.dynamic = false;
    }
}

/// Parse class-list `segments`: static tokens become candidates, computed ones are reported.
pub fn parse_class_segments(segments: &[Segment<'_>]) -> ClassListParse {
    let mut scan = Scan {
        out: ClassListParse::default(),
        token: String::new(),
        dynamic: false,
    };
    for segment in segments {
        match segment {
            Segment::Dynamic => scan.dynamic = true,
            Segment::Static(text) => {
                for ch in text.chars() {
                    if ch.is_whitespace() {
                        scan.flush();
                    } else {
                        scan.token.push(ch);
                    }
                }
            }
        }
    }
    scan.flush();
    scan.out
}

/// Parse a wholly static class list.
pub fn parse_class_list(text: &str) -> ClassListParse {
    parse_class_segments(&[Segment::Static(text)])
}
