//! A minimal JSON document with Python `json.dumps(indent=2, sort_keys=True)` output.
//!
//! The exporters emit only strings, string lists and nested objects, so a tiny value type with
//! its own printer gives byte parity with the Python crunk (two-space indent, sorted keys,
//! `ensure_ascii` escapes) without a serializer that can fail.

// frob:ticket 01M43ARZH9F9MCPJCKXM635E0X

use std::collections::BTreeMap;
use std::fmt::Write as _;

/// A JSON value of the shapes the token exports use.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Json {
    /// A string.
    Str(String),
    /// A list of strings.
    List(Vec<String>),
    /// An object; the map keeps keys sorted, which is the output order.
    Map(BTreeMap<String, Json>),
}

impl Json {
    /// Pretty-print like Python's `json.dumps(value, indent=2, sort_keys=True) + "\n"`.
    pub fn to_python_pretty(&self) -> String {
        let mut out = String::new();
        self.write(0, &mut out);
        out.push('\n');
        out
    }

    fn write(&self, depth: usize, out: &mut String) {
        match self {
            Self::Str(s) => write_string(s, out),
            Self::List(items) if items.is_empty() => out.push_str("[]"),
            Self::List(items) => {
                out.push_str("[\n");
                for (i, item) in items.iter().enumerate() {
                    indent(depth + 1, out);
                    write_string(item, out);
                    separator(i + 1 == items.len(), out);
                }
                indent(depth, out);
                out.push(']');
            }
            Self::Map(map) if map.is_empty() => out.push_str("{}"),
            Self::Map(map) => {
                out.push_str("{\n");
                for (i, (key, value)) in map.iter().enumerate() {
                    indent(depth + 1, out);
                    write_string(key, out);
                    out.push_str(": ");
                    value.write(depth + 1, out);
                    separator(i + 1 == map.len(), out);
                }
                indent(depth, out);
                out.push('}');
            }
        }
    }
}

fn indent(depth: usize, out: &mut String) {
    for _ in 0..depth {
        out.push_str("  ");
    }
}

fn separator(last: bool, out: &mut String) {
    out.push_str(if last { "\n" } else { ",\n" });
}

/// Write `s` as a JSON string with every character outside printable ASCII as `\uXXXX`
/// (a surrogate pair above the BMP), exactly like Python's default `ensure_ascii`.
fn write_string(s: &str, out: &mut String) {
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            ' '..='~' => out.push(ch),
            _ => {
                let mut units = [0_u16; 2];
                for unit in ch.encode_utf16(&mut units) {
                    let _ = write!(out, "\\u{unit:04x}");
                }
            }
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-tokens/src/export/json.rs::Json.to_python_pretty
    #[test]
    fn matches_python_dumps_for_nesting_escapes_and_empties() {
        let mut inner = BTreeMap::new();
        inner.insert(
            "b".to_owned(),
            Json::Str("caf\u{e9} \"q\" \u{1f600}\u{7f}".to_owned()),
        );
        inner.insert("a".to_owned(), Json::List(vec!["x".into(), "y z".into()]));
        let mut root = BTreeMap::new();
        root.insert("inner".to_owned(), Json::Map(inner));
        root.insert("empty".to_owned(), Json::Map(BTreeMap::new()));
        root.insert("none".to_owned(), Json::List(Vec::new()));
        let text = Json::Map(root).to_python_pretty();
        let want = "{\n  \"empty\": {},\n  \"inner\": {\n    \"a\": [\n      \"x\",\n      \"y z\"\n    ],\n    \"b\": \"caf\\u00e9 \\\"q\\\" \\ud83d\\ude00\\u007f\"\n  },\n  \"none\": []\n}\n";
        assert_eq!(text, want);
    }
}
