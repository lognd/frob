//! Byte form of a file's directive records, so a warm run skips the scan.

// frob:ticket 01M41ZSWGC86TY3K0NSA8AMNGF

use gob_symbols::Symref;
use gob_text::{FileId, Span, TextRange};
use serde::{Deserialize, Serialize};

use crate::args::{ArgList, Keyed, Token};
use crate::bind::Binding;
use crate::scan::DirectiveRecord;

/// Bump when the record layout or what a scan yields for the same text changes; part of cache keys.
pub const WIRE_VERSION: u32 = 1;

#[derive(Serialize, Deserialize)]
struct WireToken {
    value: String,
    range: (u32, u32),
    quoted: bool,
}

#[derive(Serialize, Deserialize)]
struct WireKeyed {
    key: String,
    key_range: (u32, u32),
    value: WireToken,
}

#[derive(Serialize, Deserialize)]
struct WireRecord {
    namespace: String,
    verb: String,
    positional: Vec<WireToken>,
    keyed: Vec<WireKeyed>,
    span: (u32, u32),
    /// `None` binds the whole file, `Some` a symref in its display form.
    bound: Option<String>,
    source: Option<String>,
}

fn range_of(r: TextRange) -> (u32, u32) {
    (u32::from(r.start()), u32::from(r.end()))
}

fn range_from((s, e): (u32, u32)) -> TextRange {
    TextRange::new(s.into(), e.into())
}

fn token_to_wire(t: &Token) -> WireToken {
    WireToken {
        value: t.value.clone(),
        range: range_of(t.range),
        quoted: t.quoted,
    }
}

fn token_from_wire(t: WireToken) -> Token {
    Token {
        value: t.value,
        range: range_from(t.range),
        quoted: t.quoted,
    }
}

fn record_to_wire(r: &DirectiveRecord) -> WireRecord {
    WireRecord {
        namespace: r.namespace.clone(),
        verb: r.verb.clone(),
        positional: r.args.positional.iter().map(token_to_wire).collect(),
        keyed: r
            .args
            .keyed
            .iter()
            .map(|k| WireKeyed {
                key: k.key.clone(),
                key_range: range_of(k.key_range),
                value: token_to_wire(&k.value),
            })
            .collect(),
        span: range_of(r.span.range),
        bound: match &r.bound {
            Binding::Symbol(s) => Some(s.to_string()),
            Binding::File => None,
        },
        source: r.source.as_ref().map(ToString::to_string),
    }
}

fn record_from_wire(r: WireRecord, file: FileId) -> Option<DirectiveRecord> {
    let bound = match r.bound {
        Some(s) => Binding::Symbol(s.parse::<Symref>().ok()?),
        None => Binding::File,
    };
    let source = match r.source {
        Some(s) => Some(s.parse::<Symref>().ok()?),
        None => None,
    };
    Some(DirectiveRecord {
        namespace: r.namespace,
        verb: r.verb,
        args: ArgList {
            positional: r.positional.into_iter().map(token_from_wire).collect(),
            keyed: r
                .keyed
                .into_iter()
                .map(|k| Keyed {
                    key: k.key,
                    key_range: range_from(k.key_range),
                    value: token_from_wire(k.value),
                })
                .collect(),
        },
        span: Span::new(file, range_from(r.span)),
        bound,
        source,
    })
}

/// Serializes `records` (all from one file) to bytes; `None` when encoding fails.
pub fn encode_records(records: &[DirectiveRecord]) -> Option<Vec<u8>> {
    let wire: Vec<WireRecord> = records.iter().map(record_to_wire).collect();
    match postcard::to_stdvec(&wire) {
        Ok(b) => Some(b),
        Err(err) => {
            tracing::warn!(%err, "directive records not serializable");
            None
        }
    }
}

/// Rebuilds records from [`encode_records`] bytes, attributing spans to `file`; `None` when undecodable.
pub fn decode_records(bytes: &[u8], file: FileId) -> Option<Vec<DirectiveRecord>> {
    let wire: Vec<WireRecord> = match postcard::from_bytes(bytes) {
        Ok(w) => w,
        Err(err) => {
            tracing::warn!(%err, "cached directive records undecodable");
            return None;
        }
    };
    wire.into_iter()
        .map(|r| record_from_wire(r, file))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_text::FileInterner;

    #[test]
    fn records_round_trip() {
        let file = FileInterner::new().intern("a.rs");
        let rec = DirectiveRecord {
            namespace: "frob".into(),
            verb: "tests".into(),
            args: ArgList {
                positional: vec![Token {
                    value: "a::b".into(),
                    range: range_from((3, 7)),
                    quoted: false,
                }],
                keyed: vec![Keyed {
                    key: "because".into(),
                    key_range: range_from((8, 15)),
                    value: Token {
                        value: "x y".into(),
                        range: range_from((16, 21)),
                        quoted: true,
                    },
                }],
            },
            span: Span::new(file, range_from((2, 30))),
            bound: Binding::Symbol("a.rs#b".parse().expect("symref")),
            source: Some("a.rs#c".parse().expect("symref")),
        };
        let bytes = encode_records(std::slice::from_ref(&rec)).expect("encode");
        let back = decode_records(&bytes, file).expect("decode");
        assert_eq!(back, vec![rec]);
        assert!(decode_records(&[0xff, 0xff, 0xff], file).is_none());
    }
}
