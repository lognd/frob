//! CLAIM005: a secret environment variable that reaches a print, log or HTTP sink unredacted.
//!
//! A deliberately lexical, per-function pass over Python and Rust files: a name assigned from a
//! secret-named environment read is tainted, taint follows plain assignments, and a sink call whose
//! arguments mention a tainted name (or read the secret inline) fires. Routing the value through a
//! symbol a node declares with `provides secret.declassify via SEL` clears it. The pass only runs on
//! models that declare such a boundary, so it is opt-in. It is not a sound dataflow analysis: it
//! sees one file and one function at a time (docs/design/grimble/grmb-spec.md, `CLAIM005`).

// frob:ticket 01M6QA50A5BK89J2G8SCZ4WBPR

use std::collections::BTreeSet;

use gob_rules::Severity;
use gob_symbols::Target;
use gob_walk::{Owner, selects_unit_or_enclosing};

use super::{Cx, Output, line_of, owner_of_use, scan_files, unit_at};
use crate::model::Model;

/// The atom a node provides to mark a symbol as a declassify boundary.
const DECLASSIFY_ATOM: &str = "secret.declassify";

/// Upper-case fragments that make an environment variable name secret.
const SECRET_WORDS: [&str; 6] = ["KEY", "SECRET", "TOKEN", "PASSWORD", "PASSWD", "CREDENTIAL"];

/// Calls that read one environment variable by literal name.
const ENV_READS: [&str; 8] = [
    "os.environ[",
    "os.environ.get(",
    "os.getenv(",
    "environ.get(",
    "getenv(",
    "env::var(",
    "env::var_os(",
    "environ[",
];

/// Print, log and HTTP call prefixes, matched at an identifier boundary.
const SINKS: [&str; 24] = [
    "print(",
    "println!(",
    "eprintln!(",
    "print!(",
    "eprint!(",
    "logging.",
    "logger.",
    "log.",
    "log::",
    "tracing::",
    "info!(",
    "warn!(",
    "error!(",
    "debug!(",
    "trace!(",
    "requests.",
    "httpx.",
    "urlopen(",
    "urllib.request.",
    "reqwest::",
    "ureq::",
    "session.post(",
    "session.get(",
    "client.post(",
];

/// Why CLAIM005 has nothing to judge: no node declares a declassify boundary.
pub fn claim005_inapplicable(model: &Model) -> Option<&'static str> {
    let any = model
        .entities
        .values()
        .any(|e| e.providers.iter().any(|p| p.atom == DECLASSIFY_ATOM));
    (!any).then_some("no node declares a `provides secret.declassify via SEL` boundary")
}

/// CLAIM005: report each secret environment value that reaches a print, log or HTTP sink.
pub fn claim005(cx: &Cx<'_>, out: &mut Output) {
    let declassify = declassify_names(cx);
    tracing::debug!(count = declassify.len(), "declassify symbols resolved");
    let mut scanned = 0usize;
    for path in scan_files(cx) {
        let Some(code) = cx.code.file(path) else {
            continue;
        };
        if !matches!(code.language.as_str(), "python" | "rust") {
            continue;
        }
        let (Some(src), Some(symbols)) = (code.source(), code.symbols()) else {
            continue;
        };
        scanned += 1;
        let file_unit = gob_symbols::Symref::file(path).to_string();
        let python = code.language == "python";
        for hit in scan_source(&src, python, &declassify) {
            let (unit, _) = unit_at(cx, symbols, &file_unit, hit.offset);
            let line = line_of(&src, hit.offset);
            let what = |node: &str| {
                format!(
                    "secret environment value `{}` reaches `{}` unredacted in code `{node}` owns ({path}:{line}); route it through a declassify symbol",
                    hit.source, hit.sink
                )
            };
            match owner_of_use(cx, &unit, path) {
                Some(Owner::Must(node)) => {
                    tracing::info!(file = path, line, sink = %hit.sink, "secret env value reaches a sink");
                    let anchor = format!("taint/{node}/{path}:{line}");
                    out.fire(
                        "CLAIM005",
                        Severity::Error,
                        what(node.as_str()),
                        &anchor,
                        Some((path, (hit.offset, hit.offset + hit.sink.len()))),
                    );
                }
                Some(Owner::May(nodes)) => {
                    let names = nodes.iter().map(|n| n.as_str()).collect::<Vec<_>>().join(", ");
                    let anchor = format!("taint/may/{path}:{line}");
                    out.unresolved(
                        "CLAIM005",
                        crate::types::Reason::MayOnlyOwner,
                        &what(&names),
                        &anchor,
                        Some((path, (hit.offset, hit.offset + hit.sink.len()))),
                    );
                }
                _ => {}
            }
        }
    }
    out.count("CLAIM005", scanned.max(1));
}

/// The last-segment names of every symbol some `provides secret.declassify via SEL` selects.
fn declassify_names(cx: &Cx<'_>) -> BTreeSet<String> {
    let mut names = BTreeSet::new();
    let sels: Vec<_> = cx
        .model
        .entities
        .values()
        .flat_map(|e| &e.providers)
        .filter(|p| p.atom == DECLASSIFY_ATOM)
        .collect();
    if sels.is_empty() {
        return names;
    }
    for path in scan_files(cx) {
        let Some(symbols) = cx.code.file(path).and_then(|c| c.symbols()) else {
            continue;
        };
        for s in &symbols.symbols {
            let Target::Symbol(segs) = s.symref.target() else {
                continue;
            };
            if sels.iter().any(|p| selects_unit_or_enclosing(&p.via, path, segs))
                && let Some(last) = segs.last()
            {
                names.insert(last.clone());
            }
        }
    }
    names
}

/// One secret value reaching a sink: where, which sink, and the environment variable read.
#[derive(Debug, PartialEq, Eq)]
struct Hit {
    /// Byte offset of the sink call in the file.
    offset: usize,
    /// The sink as written (`print(`, `logger.`).
    sink: String,
    /// The secret environment variable name.
    source: String,
}

/// Walk `src` line by line and return every sink call fed by a tainted value.
fn scan_source(src: &str, python: bool, declassify: &BTreeSet<String>) -> Vec<Hit> {
    let mut hits = Vec::new();
    // tainted name -> the environment variable it came from
    let mut tainted: Vec<(String, String)> = Vec::new();
    let mut offset = 0usize;
    for raw in src.split_inclusive('\n') {
        let start = offset;
        offset += raw.len();
        let line = strip_comment(raw, python);
        let trimmed = line.trim_start();
        if starts_function(trimmed, python) {
            tainted.clear();
        }
        let (target, rhs) = split_assignment(trimmed, python);
        let expr = strip_declassified(rhs.unwrap_or(trimmed), declassify);
        let origin = secret_in(&expr, &tainted);
        if let Some((sink, at)) = find_sink(&expr)
            && let Some(source) = origin.as_ref().filter(|_| sink_args_tainted(&expr, at, &tainted))
        {
            let lead = raw.len() - raw.trim_start().len();
            hits.push(Hit {
                offset: start + lead + rhs_shift(trimmed, rhs) + at,
                sink: sink.to_owned(),
                source: source.clone(),
            });
        }
        if let Some(name) = target {
            tainted.retain(|(n, _)| n != name);
            if let Some(source) = origin {
                tracing::debug!(name, %source, "name tainted by a secret environment read");
                tainted.push((name.to_owned(), source));
            }
        }
    }
    hits
}

/// The offset of `rhs` inside `trimmed` (zero when the line is not an assignment).
fn rhs_shift(trimmed: &str, rhs: Option<&str>) -> usize {
    rhs.map_or(0, |r| r.as_ptr() as usize - trimmed.as_ptr() as usize)
}

/// `raw` without its trailing `#` (Python) or `//` (Rust) comment; naive about string contents.
fn strip_comment(raw: &str, python: bool) -> &str {
    let marker = if python { "#" } else { "//" };
    raw.find(marker).map_or(raw, |i| &raw[..i])
}

/// True when `line` opens a function, which starts a fresh taint scope.
fn starts_function(line: &str, python: bool) -> bool {
    if python {
        line.starts_with("def ") || line.starts_with("async def ")
    } else {
        line.starts_with("fn ")
            || line.starts_with("pub fn ")
            || line.starts_with("async fn ")
            || line.starts_with("pub(crate) fn ")
    }
}

/// Split `NAME = RHS` (Python) or `let [mut] NAME[: T] = RHS` (Rust); `(None, None)` otherwise.
fn split_assignment(line: &str, python: bool) -> (Option<&str>, Option<&str>) {
    let Some(eq) = find_assign_eq(line) else {
        return (None, None);
    };
    let mut lhs = line[..eq].trim();
    if !python {
        let Some(rest) = lhs.strip_prefix("let ") else {
            return (None, None);
        };
        lhs = rest.trim_start().strip_prefix("mut ").unwrap_or(rest).trim();
    }
    let name = lhs.split(':').next().unwrap_or(lhs).trim();
    let valid = !name.is_empty() && name.chars().all(|c| c.is_alphanumeric() || c == '_');
    if !valid {
        return (None, None);
    }
    (Some(name), Some(line[eq + 1..].trim_start()))
}

/// The byte index of the first plain `=` that is not part of `==`, `<=`, `>=`, `!=` or `=>`.
fn find_assign_eq(line: &str) -> Option<usize> {
    let b = line.as_bytes();
    (0..b.len()).find(|&i| {
        b[i] == b'='
            && b.get(i + 1) != Some(&b'=')
            && b.get(i + 1) != Some(&b'>')
            && !matches!(i.checked_sub(1).map(|j| b[j]), Some(b'=' | b'<' | b'>' | b'!'))
    })
}

/// Blank every `decl(...)` call of a declassify symbol (balanced parentheses) out of `expr`.
fn strip_declassified(expr: &str, declassify: &BTreeSet<String>) -> String {
    let mut text = expr.to_owned();
    for name in declassify {
        let needle = format!("{name}(");
        let mut from = 0usize;
        while let Some(rel) = text[from..].find(&needle) {
            let at = from + rel;
            let boundary = text[..at]
                .chars()
                .next_back()
                .is_none_or(|c| !(c.is_alphanumeric() || c == '_'));
            if !boundary {
                from = at + needle.len();
                continue;
            }
            let open = at + needle.len() - 1;
            let mut depth = 0i32;
            let mut end = text.len();
            for (i, c) in text[open..].char_indices() {
                match c {
                    '(' => depth += 1,
                    ')' => {
                        depth -= 1;
                        if depth == 0 {
                            end = open + i + 1;
                            break;
                        }
                    }
                    _ => {}
                }
            }
            text.replace_range(at..end, &" ".repeat(end - at));
            from = at;
        }
    }
    text
}

/// The secret environment variable `expr` reads inline, or the origin of a tainted name it uses.
fn secret_in(expr: &str, tainted: &[(String, String)]) -> Option<String> {
    inline_secret(expr).or_else(|| {
        let idents = identifiers(expr);
        tainted
            .iter()
            .find(|(n, _)| idents.iter().any(|i| i == n))
            .map(|(_, s)| s.clone())
    })
}

/// The first secret-named variable read by a literal-name environment call in `expr`.
fn inline_secret(expr: &str) -> Option<String> {
    for read in ENV_READS {
        let mut from = 0usize;
        while let Some(rel) = expr[from..].find(read) {
            let after = from + rel + read.len();
            from = after;
            let rest = expr[after..].trim_start();
            let Some(q) = rest.chars().next().filter(|c| matches!(c, '"' | '\'')) else {
                continue;
            };
            let name: String = rest[1..].chars().take_while(|c| *c != q).collect();
            let upper = name.to_uppercase();
            if SECRET_WORDS.iter().any(|w| upper.contains(w)) {
                return Some(name);
            }
        }
    }
    None
}

/// The identifiers of `expr` outside string literals, plus those inside `{...}` of a string.
fn identifiers(expr: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut quote: Option<char> = None;
    let mut word = String::new();
    let mut braces = 0usize;
    let flush = |word: &mut String, out: &mut Vec<String>| {
        if !word.is_empty() {
            out.push(std::mem::take(word));
        }
    };
    for c in expr.chars() {
        let counts = match quote {
            None => true,
            Some(_) => braces > 0,
        };
        if let Some(q) = quote {
            if c == q {
                flush(&mut word, &mut out);
                quote = None;
                braces = 0;
                continue;
            }
            if c == '{' {
                braces += 1;
            } else if c == '}' {
                braces = braces.saturating_sub(1);
            }
        } else if c == '"' || c == '\'' {
            flush(&mut word, &mut out);
            quote = Some(c);
            continue;
        }
        if counts && (c.is_alphanumeric() || c == '_') {
            word.push(c);
        } else {
            flush(&mut word, &mut out);
        }
    }
    flush(&mut word, &mut out);
    out
}

/// The first sink in `expr` at an identifier boundary, with its byte offset.
fn find_sink(expr: &str) -> Option<(&'static str, usize)> {
    SINKS
        .iter()
        .filter_map(|s| {
            let mut from = 0usize;
            while let Some(rel) = expr[from..].find(s) {
                let at = from + rel;
                let ok = expr[..at]
                    .chars()
                    .next_back()
                    .is_none_or(|c| !(c.is_alphanumeric() || c == '_' || c == '.'));
                if ok {
                    return Some((*s, at));
                }
                from = at + s.len();
            }
            None
        })
        .min_by_key(|(_, at)| *at)
}

/// True when the text after the sink at `at` mentions a tainted name or reads a secret inline.
fn sink_args_tainted(expr: &str, at: usize, tainted: &[(String, String)]) -> bool {
    secret_in(&expr[at..], tainted).is_some()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn decl() -> BTreeSet<String> {
        ["redact".to_owned()].into()
    }

    // frob:tests crates/grimble-bind/src/caps/taint.rs::scan_source
    /// A secret read into a name and printed fires.
    #[test]
    fn python_secret_to_print_fires() {
        let src = "def f():\n    tok = os.environ[\"API_TOKEN\"]\n    print(tok)\n";
        let hits = scan_source(src, true, &decl());
        assert_eq!(hits.len(), 1, "{hits:?}");
        assert_eq!(hits[0].source, "API_TOKEN");
    }

    // frob:tests crates/grimble-bind/src/caps/taint.rs::scan_source
    /// Passing the value through a declassify symbol is clean.
    #[test]
    fn declassified_value_is_clean() {
        let src = "def f():\n    tok = os.getenv(\"API_TOKEN\")\n    logger.info(redact(tok))\n    safe = redact(tok)\n    print(safe)\n";
        assert!(scan_source(src, true, &decl()).is_empty());
    }

    // frob:tests crates/grimble-bind/src/caps/taint.rs::scan_source
    /// Rust inline format arguments and HTTP sinks fire; a non-secret variable does not.
    #[test]
    fn rust_inline_and_http_sinks() {
        let src = "fn f() {\n    let k = std::env::var(\"DB_PASSWORD\").unwrap();\n    println!(\"{k}\");\n    let home = std::env::var(\"HOME\").unwrap();\n    println!(\"{home}\");\n    reqwest::get(k);\n}\n";
        assert_eq!(scan_source(src, false, &decl()).len(), 2);
    }

    // frob:tests crates/grimble-bind/src/caps/taint.rs::scan_source
    /// Taint does not leak across functions and a reassignment clears it.
    #[test]
    fn taint_is_scoped_and_reassignable() {
        let src = "def a():\n    t = os.environ[\"X_SECRET\"]\n    t = \"x\"\n    print(t)\ndef b():\n    print(t)\n";
        assert!(scan_source(src, true, &decl()).is_empty());
    }
}
