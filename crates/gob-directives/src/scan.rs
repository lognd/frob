//! The scanner: comments to directive records and PARSE/DSL findings.

use std::collections::BTreeMap;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_rules::{Finding, RuleId, RuleMeta};
use gob_symbols::{FileSymbols, Symref};
use gob_text::{FileId, FileInterner, LineIndex, Span, TextRange};

use crate::args::{ArgList, Token};
use crate::bind::{Binding, Site, bind, is_test_item};
use crate::comments::{Segment, segments};
use crate::config::DirectivesConfig;
use crate::lex::{is_word, range_at, tokenize};
use crate::meta::{DirectiveEntry, entries};
use crate::rules::{Dsl001, Dsl002, Parse001};
use crate::ulid::{is_full_ulid, is_v1_alias, looks_like_ticket_ref};

/// The verb whose binding is reoriented to its named target inside a test item.
pub const REORIENT_VERB: &str = "tests";

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
/// The message for a directive with no item to attach to.
pub const NOT_ATTACHED: &str = "directive is not attached to an item: put it directly above the function or heading it describes";

/// Which namespaces a [`Scanner`] honours and which product it reports as.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScanConfig {
    /// Honoured namespaces; comments in any other namespace are ignored.
    pub namespaces: Vec<String>,
    /// Product the PARSE and DSL findings are emitted under (D32).
    pub product: String,
}

impl ScanConfig {
    /// A scan configuration honouring the namespaces of `[directives]`, reporting as `product`.
    pub fn from_config(config: &DirectivesConfig, product: &str) -> Self {
        tracing::debug!(namespaces = ?config.namespaces, product, "scan config from [directives]");
        Self {
            namespaces: config.namespaces.clone(),
            product: product.to_owned(),
        }
    }
}

impl Default for ScanConfig {
    fn default() -> Self {
        Self {
            namespaces: vec!["frob".to_owned()],
            product: "frob".to_owned(),
        }
    }
}

/// One directive found in a file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DirectiveRecord {
    /// Namespace (`frob`).
    pub namespace: String,
    /// Verb (`ticket`).
    pub verb: String,
    /// The raw arguments; turn into a typed directive with `Directive::parse_args`.
    pub args: ArgList,
    /// Where the directive text sits (marker prefix and suffix excluded).
    pub span: Span,
    /// What the directive is bound to.
    pub bound: Binding,
    /// For a reoriented `tests` directive, the enclosing test item it was written in.
    pub source: Option<Symref>,
}

/// Everything one scan produced.
#[derive(Debug, Clone, Default)]
pub struct ScanResult {
    /// Well-formed directives in source order.
    pub directives: Vec<DirectiveRecord>,
    /// PARSE001, DSL001 and DSL002 findings in source order.
    pub findings: Vec<Finding>,
}

/// Extracts directives of the honoured namespaces from file text.
#[derive(Debug)]
pub struct Scanner {
    namespaces: Vec<String>,
    product: String,
    verbs: BTreeMap<(String, String), &'static DirectiveEntry>,
}

fn rule_finding(meta: &RuleMeta, span: Span, message: String, anchor: &str) -> Finding {
    let id: RuleId = meta
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("derive validated rule id {}: {e}", meta.id));
    Finding::new(id, meta.severity, Some(span), message, anchor)
}

impl Scanner {
    /// Build a scanner over the registered directives of `config.namespaces`.
    pub fn new(config: &ScanConfig) -> Self {
        let verbs: BTreeMap<(String, String), &'static DirectiveEntry> = entries()
            .into_iter()
            .filter(|((ns, _), _)| config.namespaces.iter().any(|n| n == ns))
            .map(|((ns, v), e)| ((ns.to_owned(), v.to_owned()), e))
            .collect();
        tracing::debug!(
            product = %config.product,
            namespaces = ?config.namespaces,
            verbs = verbs.len(),
            "directive scanner built"
        );
        Self {
            namespaces: config.namespaces.clone(),
            product: config.product.clone(),
            verbs,
        }
    }

    /// The product findings are reported under.
    pub fn product(&self) -> &str {
        &self.product
    }

    /// Scan `text` of `language`; spans use the file id of `symbols.path` in a fresh interner.
    pub fn scan(&self, language: Language, text: &str, symbols: &FileSymbols) -> ScanResult {
        let file = FileInterner::new().intern(&symbols.path);
        self.scan_in(file, language, text, symbols)
    }

    // frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
    /// Scan `text` of `language`, attributing spans to `file`.
    pub fn scan_in(
        &self,
        file: FileId,
        language: Language,
        text: &str,
        symbols: &FileSymbols,
    ) -> ScanResult {
        let mut result = ScanResult::default();
        let Ok(index) = LineIndex::new(text) else {
            tracing::warn!(path = %symbols.path, "file too large to scan for directives");
            return result;
        };
        let tree = match language {
            Language::Toml | Language::Yaml => None,
            _ => match parse(language, text, &ParseLimits::default()) {
                ParseResult::Parsed(t) => Some(t),
                ParseResult::Unresolved(u) => {
                    tracing::warn!(
                        path = %symbols.path,
                        reason = %u.reason,
                        "no syntax tree; scanning comments as plain text"
                    );
                    None
                }
            },
        };
        let ctx = Ctx {
            file,
            language,
            text,
            index: &index,
            symbols,
        };
        for seg in segments(language, text, tree.as_ref()) {
            self.handle(&ctx, &seg, &mut result);
        }
        tracing::debug!(
            path = %symbols.path,
            directives = result.directives.len(),
            findings = result.findings.len(),
            "directive scan done"
        );
        result
    }

    fn handle(&self, ctx: &Ctx<'_>, seg: &Segment<'_>, out: &mut ScanResult) {
        let Some(colon) = seg.text.find(':') else {
            return;
        };
        let ns = &seg.text[..colon];
        if !is_word(ns, false) || !self.namespaces.iter().any(|n| n == ns) {
            return;
        }
        let whole = ctx.span(range_at(seg.offset, 0, seg.text.len()));
        let after = &seg.text[colon + 1..];
        let verb_len = after.find(char::is_whitespace).unwrap_or(after.len());
        let verb = &after[..verb_len];
        let verb_span = ctx.span(range_at(seg.offset, colon + 1, colon + 1 + verb_len));
        let mut emit = |meta: &RuleMeta, span: Span, message: String| {
            tracing::debug!(rule = meta.id, %message, "directive finding");
            out.findings
                .push(rule_finding(meta, span, message, &ctx.symbols.path));
        };
        if verb.is_empty() {
            emit(
                &Parse001::META,
                ctx.span(range_at(seg.offset, 0, colon + 1)),
                format!("`{ns}:` is missing a verb"),
            );
            return;
        }
        if !is_word(verb, true) {
            emit(
                &Parse001::META,
                verb_span,
                format!("malformed verb `{verb}`; expected lowercase letters, digits, `_` and `-`"),
            );
            return;
        }
        let Some(entry) = self.verbs.get(&(ns.to_owned(), verb.to_owned())) else {
            emit(
                &Dsl001::META,
                verb_span,
                self.unknown_verb_message(ns, verb),
            );
            return;
        };
        let tail_at = colon + 1 + verb_len;
        let args = match tokenize(&seg.text[tail_at..], seg.offset + tail_at) {
            Ok(a) => a,
            Err(e) => {
                emit(
                    &Parse001::META,
                    ctx.span(e.range),
                    format!("`{ns}:{verb}`: {}", e.message),
                );
                return;
            }
        };
        if let Err(e) = (entry.validate)(&args) {
            let span = e.range().map_or(whole, |r| ctx.span(r));
            emit(&Parse001::META, span, format!("`{ns}:{verb}`: {e}"));
            return;
        }
        if let Some((meta, span, message)) = check_ticket_refs(ctx, entry, &args, ns, verb) {
            emit(meta, span, message);
            return;
        }
        if let Some(rec) = Self::record(ctx, seg, (ns, verb), args, whole, &mut emit) {
            out.directives.push(rec);
        }
    }

    // frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
    // frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
    /// Build the record, binding it and reorienting `tests` inside a test item.
    ///
    /// A Rust `tests` directive that attaches to no item is reported (PARSE001)
    /// and dropped: it has nothing to cover and would only be misreported as an
    /// unknown symref downstream. Other verbs may legitimately bind the file.
    fn record(
        ctx: &Ctx<'_>,
        seg: &Segment<'_>,
        (ns, verb): (&str, &str),
        args: ArgList,
        span: Span,
        emit: &mut impl FnMut(&RuleMeta, Span, String),
    ) -> Option<DirectiveRecord> {
        let site = Site {
            start: seg.offset,
            end: seg.offset + seg.text.len(),
            allow_following: !seg.inner_doc && ctx.language != Language::Markdown,
            hash_comments: matches!(
                ctx.language,
                Language::Toml | Language::Yaml | Language::Python
            ),
        };
        let sym = bind(ctx.index, ctx.text, &ctx.symbols.symbols, site);
        if sym.is_none()
            && verb == REORIENT_VERB
            && site.allow_following
            && ctx.language == Language::Rust
        {
            tracing::debug!(?span, "unattached tests directive dropped");
            emit(&Parse001::META, span, NOT_ATTACHED.to_owned());
            return None;
        }
        let mut bound = sym.map_or(Binding::File, |s| Binding::Symbol(s.symref.clone()));
        let mut source = None;
        if verb == REORIENT_VERB
            && let (Some(sym), Some(target)) = (sym, args.positional.first())
            && is_test_item(ctx.index, ctx.text, sym)
        {
            match Symref::parse(&target.value) {
                Ok(t) => {
                    tracing::debug!(test = %sym.symref, target = %t, "tests directive reoriented");
                    source = Some(sym.symref.clone());
                    bound = Binding::Symbol(t);
                }
                Err(e) => emit(
                    &Parse001::META,
                    ctx.span(target.range),
                    format!("`{ns}:{verb}` target is not a symref: {e}"),
                ),
            }
        }
        Some(DirectiveRecord {
            namespace: ns.to_owned(),
            verb: verb.to_owned(),
            args,
            span,
            bound,
            source,
        })
    }

    fn unknown_verb_message(&self, ns: &str, verb: &str) -> String {
        let known: Vec<&str> = self
            .verbs
            .keys()
            .filter(|(n, _)| n == ns)
            .map(|(_, v)| v.as_str())
            .collect();
        let best = known
            .iter()
            .map(|k| (strsim::levenshtein(verb, k), *k))
            .min();
        match best {
            Some((d, k)) if d <= 2.max(verb.len() / 3) => {
                format!("unknown directive `{ns}:{verb}`; did you mean `{ns}:{k}`?")
            }
            _ if known.is_empty() => {
                format!("unknown directive `{ns}:{verb}`; namespace `{ns}` declares no verbs")
            }
            _ => format!(
                "unknown directive `{ns}:{verb}`; known verbs: {}",
                known.join(", ")
            ),
        }
    }
}

/// Per-scan shared state.
struct Ctx<'a> {
    file: FileId,
    language: Language,
    text: &'a str,
    index: &'a LineIndex,
    symbols: &'a FileSymbols,
}

impl Ctx<'_> {
    fn span(&self, range: TextRange) -> Span {
        Span::new(self.file, range)
    }
}

/// The first ticket-id argument that is not a full ULID, as a finding.
fn check_ticket_refs<'m>(
    ctx: &Ctx<'_>,
    entry: &'m DirectiveEntry,
    args: &ArgList,
    ns: &str,
    verb: &str,
) -> Option<(&'m RuleMeta, Span, String)> {
    let mut positional = 0usize;
    for a in entry.meta.args {
        let token: Option<&Token> = if a.list {
            None
        } else if a.positional {
            positional += 1;
            args.positional.get(positional - 1)
        } else {
            a.key.and_then(|k| args.get(k))
        };
        let Some(t) = token.filter(|_| a.ticket_ref) else {
            continue;
        };
        if is_full_ulid(&t.value) || is_v1_alias(&t.value) {
            continue;
        }
        let span = ctx.span(t.range);
        return Some(if looks_like_ticket_ref(&t.value) {
            (
                &Dsl002::META,
                span,
                format!(
                    // frob:ticket 01M40YQZF4422S88TN6992AN0Q
                    "`{ns}:{verb}` carries abbreviated ticket id `{}`; only full 26-char ULIDs persist (D24), replace it with the full id from `frob ticket show <handle>`",
                    t.value
                ),
            )
        } else {
            (
                &Parse001::META,
                span,
                format!("`{ns}:{verb}`: `{}` is not a ticket id", t.value),
            )
        });
    }
    None
}

#[cfg(test)]
mod python_tests {
    use super::*;
    use crate::Binding;
    use gob_symbols::extract_file;
    use gob_walk::{Digest, FileEntry, LanguageHint};

    // frob:tests crates/gob-directives/src/scan.rs::Scanner.scan_in
    #[test]
    fn stacked_python_directives_bind_to_the_next_def() {
        let path = "pkg/a.py";
        let text = "# frob:ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2\n# frob:ticket 01J9QKX3M8Z4T7N2V5B6C0D1E3\n@deco\ndef target():\n    pass\n";
        let entry = FileEntry {
            path: path.to_owned(),
            size: text.len() as u64,
            digest: Digest::of(text.as_bytes()),
            language: LanguageHint::from_path(path),
        };
        let syms = extract_file(&entry, text);
        let r = Scanner::new(&ScanConfig::default()).scan(Language::Python, text, &syms);
        assert!(r.findings.is_empty(), "{:?}", r.findings);
        assert_eq!(r.directives.len(), 2);
        for d in &r.directives {
            assert_eq!(
                d.bound,
                Binding::Symbol("pkg/a.py::target".parse().expect("symref"))
            );
        }
    }

    // frob:tests crates/gob-directives/src/scan.rs::Scanner.scan_in
    #[test]
    fn csharp_directives_come_from_comments_not_strings() {
        let text = "var s = \"// frob:ticket 01J9QKX3M8Z4T7N2V5B6C0D1E9\";\n// frob:ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2\nclass A {}\n";
        let syms = gob_symbols::FileSymbols {
            path: "A.cs".to_owned(),
            ..Default::default()
        };
        let r = Scanner::new(&ScanConfig::default()).scan(Language::CSharp, text, &syms);
        assert!(r.findings.is_empty(), "{:?}", r.findings);
        assert_eq!(r.directives.len(), 1);
    }

    /// A downstream product's waiver, registered the way crunk registers its own.
    #[derive(Debug, gob_macros::Directive)]
    #[directive(namespace = "crunk", verb = "waive")]
    #[allow(dead_code)]
    struct CrunkWaive {
        /// The waived rule.
        #[arg(positional)]
        rule: String,
        /// Why the waiver exists.
        #[arg(key = "reason")]
        reason: String,
    }

    // frob:tests crates/gob-directives/src/scan.rs::Scanner.scan_in
    #[test]
    fn css_waiver_is_found_in_the_crunk_namespace_with_its_span() {
        let text = "/* crunk:waive COLOR001 reason=\"brand\" */\na { color: #f00 }\n";
        let syms = gob_symbols::FileSymbols {
            path: "site.css".to_owned(),
            ..Default::default()
        };
        let cfg = ScanConfig {
            namespaces: vec!["crunk".to_owned()],
            product: "crunk".to_owned(),
        };
        let r = Scanner::new(&cfg).scan(Language::Css, text, &syms);
        assert!(r.findings.is_empty(), "{:?}", r.findings);
        assert_eq!(r.directives.len(), 1);
        let d = &r.directives[0];
        assert_eq!((d.namespace.as_str(), d.verb.as_str()), ("crunk", "waive"));
        assert_eq!(d.span.range.start(), gob_text::TextSize::new(3));
    }
}
