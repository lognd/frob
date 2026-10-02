//! The recursive-descent parser with `hole` recovery (grmb-spec 2-4 and 9.2).
//!
//! Hand-written rather than tree-sitter: a syntax error must produce a `hole` node
//! that resynchronizes at the next `;` or at the `}` closing the current block, with
//! exact byte spans, and the whole file must keep parsing around it. The grammar is
//! small and LL(1), so a hand-written parser gives that recovery without the cost of
//! a generated grammar, a C toolchain dependency and an ABI to pin.

use std::collections::BTreeMap;

use gob_walk::Selector;

use crate::ast::{
    Atom, Attachments, ClaimWhat, Clause, ClauseKind, Direction, Entity, EntityKind, Evidence,
    ExcKind, Exception, Excuses, FileStatus, Header, Ident, Include, Item, KeyVal, Link, LinkKind,
    May, ModuleDecl, ModuleKind, Namespace, ParsedFile, QuantKey, Quantity, RefPath, Sel, Spanned,
    TopException, Value, VersionHeader, Versioning,
};
use crate::keywords::is_keyword;
use crate::lex::{Comment, CommentKind, Punct, Tok, Token, lex};
use crate::span::{Diagnostic, Span};

/// The only language major this crate reads (grmb-spec 3.4).
pub const SUPPORTED_MAJOR: &str = "2";

struct ParseErr {
    span: Span,
    message: String,
}

type PResult<T> = Result<T, ParseErr>;

struct Target {
    id: usize,
    start: usize,
    head_end: usize,
    end: usize,
    close: Option<usize>,
}

fn fail<T>(span: Span, message: impl Into<String>) -> PResult<T> {
    Err(ParseErr {
        span,
        message: message.into(),
    })
}

struct Parser<'a> {
    src: &'a str,
    toks: Vec<Token>,
    pos: usize,
    diags: Vec<Diagnostic>,
    next_id: usize,
    targets: Vec<Target>,
    holes: usize,
}

/// Checks the encoding rules of grmb-spec 2.1; `Err` is the opaque reason.
fn check_encoding(bytes: &[u8]) -> Result<&str, (&'static str, &'static str)> {
    if bytes.starts_with(&[0xEF, 0xBB, 0xBF]) {
        return Err(("not-utf8", "a byte-order mark is not allowed"));
    }
    let Ok(text) = std::str::from_utf8(bytes) else {
        return Err(("not-utf8", "the file is not valid UTF-8"));
    };
    if bytes.contains(&0) {
        return Err(("not-utf8", "the file contains a NUL byte"));
    }
    let mut it = bytes.iter().peekable();
    while let Some(&b) = it.next() {
        if b == b'\r' && it.peek().is_none_or(|&&n| n != b'\n') {
            return Err(("binary", "a bare CR is not a line terminator"));
        }
    }
    Ok(text)
}

/// Parses one .grmb file from raw bytes; total (never fails).
pub fn parse_file(path: &str, bytes: &[u8]) -> ParsedFile {
    let mut file = ParsedFile {
        path: path.to_owned(),
        text: String::new(),
        raw: Vec::new(),
        size: bytes.len(),
        status: FileStatus::Parsed,
        version: None,
        module: None,
        items: Vec::new(),
        comments: Vec::new(),
        attachments: Attachments::default(),
        diags: Vec::new(),
        holes: 0,
        lex_holes: Vec::new(),
    };
    let text = match check_encoding(bytes) {
        Ok(t) => t,
        Err((reason, msg)) => {
            tracing::warn!(path, reason, "grmb file is opaque");
            file.status = FileStatus::Opaque(reason);
            file.raw = bytes.to_vec();
            file.diags
                .push(Diagnostic::new("MDL000", Span::new(0, bytes.len()), msg));
            return file;
        }
    };
    text.clone_into(&mut file.text);
    let lexed = lex(text);
    file.lex_holes = lexed
        .tokens
        .iter()
        .filter(|t| t.tok == Tok::Bad)
        .map(|t| t.span)
        .collect();
    file.diags.extend(lexed.diags);
    file.comments = lexed.comments;
    let toks: Vec<Token> = lexed
        .tokens
        .into_iter()
        .filter(|t| t.tok != Tok::Bad)
        .collect();
    let mut p = Parser {
        src: text,
        toks,
        pos: 0,
        diags: Vec::new(),
        next_id: 0,
        targets: Vec::new(),
        holes: file.lex_holes.len(),
    };
    p.file(&mut file);
    file.diags.append(&mut p.diags);
    file.holes = p.holes;
    if file.status == FileStatus::Parsed {
        file.attachments = attach(&p.targets, &p.toks, &file.comments, text);
    }
    tracing::debug!(
        path,
        items = file.items.len(),
        holes = file.holes,
        diags = file.diags.len(),
        "grmb file parsed"
    );
    file
}

impl Parser<'_> {
    fn id(&mut self) -> usize {
        self.next_id += 1;
        self.next_id
    }

    fn peek(&self) -> &Token {
        &self.toks[self.pos.min(self.toks.len() - 1)]
    }

    fn peek_n(&self, n: usize) -> &Token {
        &self.toks[(self.pos + n).min(self.toks.len() - 1)]
    }

    fn bump(&mut self) -> Token {
        let t = self.peek().clone();
        if self.pos < self.toks.len() - 1 {
            self.pos += 1;
        }
        t
    }

    fn prev_end(&self) -> usize {
        self.toks[self.pos.saturating_sub(1)].span.end
    }

    fn at_eof(&self) -> bool {
        self.peek().tok == Tok::Eof
    }

    fn at_p(&self, p: Punct) -> bool {
        self.peek().tok == Tok::P(p)
    }

    fn at_kw(&self, kw: &str) -> bool {
        matches!(&self.peek().tok, Tok::Ident(s) if s == kw)
    }

    fn eat_p(&mut self, p: Punct) -> bool {
        let hit = self.at_p(p);
        if hit {
            self.bump();
        }
        hit
    }

    fn eat_kw(&mut self, kw: &str) -> bool {
        let hit = self.at_kw(kw);
        if hit {
            self.bump();
        }
        hit
    }

    fn unexpected<T>(&self, expected: &str) -> PResult<T> {
        let t = self.peek();
        fail(
            t.span,
            format!("unexpected {}, expected {expected}", t.tok.describe()),
        )
    }

    fn expect_p(&mut self, p: Punct) -> PResult<Token> {
        if self.at_p(p) {
            Ok(self.bump())
        } else {
            self.unexpected(&format!("`{}`", p.text()))
        }
    }

    fn expect_kw(&mut self, kw: &str) -> PResult<Token> {
        if self.at_kw(kw) {
            Ok(self.bump())
        } else {
            self.unexpected(&format!("`{kw}`"))
        }
    }

    /// Any identifier, keyword or not.
    fn any_ident(&mut self, what: &str) -> PResult<Ident> {
        match &self.peek().tok {
            Tok::Ident(s) => {
                let id = Ident {
                    text: s.clone(),
                    span: self.peek().span,
                };
                self.bump();
                Ok(id)
            }
            _ => self.unexpected(what),
        }
    }

    /// A name: an identifier that is not a keyword (a keyword is reported and kept).
    fn name(&mut self, what: &str) -> PResult<Ident> {
        let id = self.any_ident(what)?;
        if is_keyword(&id.text) {
            self.diags.push(Diagnostic::new(
                "MDL000",
                id.span,
                format!(
                    "`{}` is a reserved word and cannot be used as {what}",
                    id.text
                ),
            ));
        }
        Ok(id)
    }

    fn string(&mut self, what: &str) -> PResult<Spanned<String>> {
        let start = self.peek().span;
        let Tok::Str(first) = self.peek().tok.clone() else {
            return self.unexpected(what);
        };
        self.bump();
        let mut value = first;
        let mut span = start;
        while let Tok::Str(more) = self.peek().tok.clone() {
            value.push_str(&more);
            span = span.to(self.peek().span);
            self.bump();
        }
        Ok(Spanned { value, span })
    }

    fn ref_path(&mut self, what: &str) -> PResult<RefPath> {
        let start = self.peek().span;
        let rooted = self.eat_p(Punct::ColonColon);
        let first = self.name(what)?;
        let mut segments = vec![first.text];
        let mut span = start.to(first.span);
        while self.at_p(Punct::Dot) && matches!(self.peek_n(1).tok, Tok::Ident(_)) {
            self.bump();
            let seg = self.name(what)?;
            span = span.to(seg.span);
            segments.push(seg.text);
        }
        Ok(RefPath {
            rooted,
            segments,
            span,
        })
    }

    fn atom(&mut self) -> PResult<Atom> {
        let first = self.any_ident("a capability atom")?;
        let mut span = first.span;
        let (pack, head) = if self.at_p(Punct::ColonColon) {
            self.bump();
            let h = self.any_ident("an atom name after `::`")?;
            span = span.to(h.span);
            (Some(first.text), h.text)
        } else {
            (None, first.text)
        };
        let mut name = head;
        while self.at_p(Punct::Dot) && matches!(self.peek_n(1).tok, Tok::Ident(_)) {
            self.bump();
            let seg = self.any_ident("an atom segment")?;
            span = span.to(seg.span);
            name.push('.');
            name.push_str(&seg.text);
        }
        Ok(Atom { pack, name, span })
    }

    fn quantity(&mut self) -> PResult<Quantity> {
        let t = self.peek().clone();
        match t.tok {
            Tok::Quantity { number, unit } => {
                self.bump();
                Ok(Quantity {
                    number,
                    unit,
                    span: t.span,
                })
            }
            Tok::Number(number) => {
                self.bump();
                Ok(Quantity {
                    number,
                    unit: String::new(),
                    span: t.span,
                })
            }
            _ => self.unexpected("a quantity such as `30 s`"),
        }
    }

    fn value(&mut self) -> PResult<Spanned<Value>> {
        let t = self.peek().clone();
        let v = match t.tok {
            Tok::Str(_) => {
                let s = self.string("a string")?;
                return Ok(Spanned {
                    value: Value::Str(s.value),
                    span: s.span,
                });
            }
            Tok::Number(n) => Value::Number(n),
            Tok::Quantity { number, unit } => Value::Quantity(Quantity {
                number,
                unit,
                span: t.span,
            }),
            Tok::Date(d) => Value::Date(d),
            Tok::Ident(i) => Value::Ident(i),
            Tok::P(Punct::LBracket) => {
                self.bump();
                let mut items = Vec::new();
                let mut span = t.span;
                while !self.at_p(Punct::RBracket) {
                    let item = self.value()?;
                    if matches!(item.value, Value::List(_)) {
                        return fail(item.span, "lists do not nest");
                    }
                    items.push(item.value);
                    if !self.eat_p(Punct::Comma) {
                        break;
                    }
                }
                let close = self.expect_p(Punct::RBracket)?;
                span = span.to(close.span);
                return Ok(Spanned {
                    value: Value::List(items),
                    span,
                });
            }
            _ => return self.unexpected("a value"),
        };
        self.bump();
        Ok(Spanned {
            value: v,
            span: t.span,
        })
    }

    fn key_vals(&mut self) -> PResult<Vec<KeyVal>> {
        let mut out = Vec::new();
        while matches!(self.peek().tok, Tok::Ident(_)) && !self.at_kw("on") {
            let key = self.any_ident("an attribute key")?;
            if !self.at_p(Punct::Eq) {
                if key.text == "because" {
                    return fail(
                        key.span.to(self.peek().span),
                        "a bare `because \"...\"` is not accepted; write `because=\"...\"`",
                    );
                }
                return self.unexpected("`=`");
            }
            self.bump();
            let value = self.value()?;
            out.push(KeyVal { key, value });
        }
        Ok(out)
    }

    /// Slices a selector from the token stream (up to the `;` at depth 0) and parses it.
    fn selector(&mut self) -> PResult<Sel> {
        let first = self.peek().clone();
        if matches!(first.tok, Tok::P(Punct::Semi | Punct::RBrace) | Tok::Eof) {
            return fail(first.span, "expected a selector");
        }
        let mut depth = 0usize;
        let mut last = first.span;
        loop {
            let t = self.peek();
            match &t.tok {
                Tok::Eof | Tok::P(Punct::RBrace | Punct::LBrace) => break,
                Tok::P(Punct::Semi) if depth == 0 => break,
                Tok::P(Punct::LParen) => depth += 1,
                Tok::P(Punct::RParen) => depth = depth.saturating_sub(1),
                _ => {}
            }
            last = t.span;
            self.bump();
        }
        let span = first.span.to(last);
        let text = span.slice(self.src).to_owned();
        let parsed = Selector::parse_at(&text, span.start);
        if let Err(errs) = &parsed {
            for e in errs {
                self.diags.push(Diagnostic::new(
                    "MDL009",
                    Span::new(e.span.start, e.span.end),
                    format!("selector: {}", e.message),
                ));
            }
        }
        Ok(Sel { text, span, parsed })
    }

    fn register(
        &mut self,
        id: usize,
        start: usize,
        head_end: usize,
        end: usize,
        close: Option<usize>,
    ) {
        self.targets.push(Target {
            id,
            start,
            head_end,
            end,
            close,
        });
    }

    // ----- file level -----

    fn file(&mut self, file: &mut ParsedFile) {
        if !self.header(file) {
            return;
        }
        self.module_decl(file);
        while !self.at_eof() {
            let item = self.item();
            file.items.push(item);
        }
    }

    /// Reads `grimble = "N";`; false when the file is refused whole.
    fn header(&mut self, file: &mut ParsedFile) -> bool {
        let start = self.peek().span;
        let ok = self.at_kw("grimble")
            && self.peek_n(1).tok == Tok::P(Punct::Eq)
            && matches!(self.peek_n(2).tok, Tok::Str(_))
            && self.peek_n(3).tok == Tok::P(Punct::Semi);
        if !ok {
            file.status = FileStatus::Refused("missing-version");
            file.diags.push(Diagnostic::new(
                "MDL007",
                start,
                "the file must start with the version header `grimble = \"2\";`",
            ));
            return false;
        }
        self.bump();
        self.bump();
        let Tok::Str(value) = self.bump().tok else {
            unreachable!("checked above");
        };
        let semi = self.bump();
        file.version = Some(VersionHeader {
            value: value.clone(),
            span: start.to(semi.span),
        });
        if value != SUPPORTED_MAJOR {
            file.status = FileStatus::Refused("unsupported-version");
            file.diags.push(Diagnostic::new(
                "MDL007",
                start.to(semi.span),
                format!("language major `{value}` is not read by this binary (it reads `{SUPPORTED_MAJOR}`)"),
            ));
            return false;
        }
        true
    }

    fn module_decl(&mut self, file: &mut ParsedFile) {
        let start = self.peek().span;
        let kind = if self.at_kw("module") {
            ModuleKind::Module
        } else if self.at_kw("part") {
            ModuleKind::PartOf
        } else {
            file.diags.push(Diagnostic::new(
                "MDL000",
                start,
                "expected `module NAME;` or `part of NAME;` after the version header",
            ));
            return;
        };
        let r = (|| -> PResult<ModuleDecl> {
            self.bump();
            if kind == ModuleKind::PartOf {
                self.expect_kw("of")?;
            }
            let name = self.name("a module name")?;
            let semi = self.expect_p(Punct::Semi)?;
            let id = self.id();
            let span = start.to(semi.span);
            self.register(id, span.start, span.end, span.end, None);
            Ok(ModuleDecl {
                id,
                kind,
                name,
                span,
            })
        })();
        match r {
            Ok(m) => file.module = Some(m),
            Err(e) => {
                self.hole_diag(&e);
                self.resync(false);
            }
        }
    }

    fn hole_diag(&mut self, e: &ParseErr) {
        self.holes += 1;
        self.diags
            .push(Diagnostic::new("MDL000", e.span, e.message.clone()));
    }

    /// Skips to the end of a broken statement: past a `;`, past a balanced `}` or before
    /// the `}` that closes the enclosing block (`in_block`).
    fn resync(&mut self, in_block: bool) {
        let mut depth = 0usize;
        loop {
            match &self.peek().tok {
                Tok::Eof => return,
                Tok::P(Punct::Semi) if depth == 0 => {
                    self.bump();
                    return;
                }
                Tok::P(Punct::LBrace) => {
                    depth += 1;
                    self.bump();
                }
                Tok::P(Punct::RBrace) => {
                    if depth == 0 {
                        if !in_block {
                            self.bump();
                        }
                        return;
                    }
                    depth -= 1;
                    self.bump();
                    if depth == 0 {
                        return;
                    }
                }
                _ => {
                    self.bump();
                }
            }
        }
    }

    fn item(&mut self) -> Item {
        let start_pos = self.pos;
        let start = self.peek().span;
        let Tok::Ident(word) = self.peek().tok.clone() else {
            return self.item_hole(start_pos, start, false, None);
        };
        let r = match word.as_str() {
            "include" => self.include().map(Item::Include),
            "namespace" => self.namespace().map(Item::Namespace),
            "extend" => self.extend().map(Item::Entity),
            "accept" | "defer" | "hotfix" => self.top_exception().map(Item::Exception),
            "baseline" => fail(
                start,
                "`baseline` is never written in a .grmb file; pools live in the ratchet lock",
            ),
            w => match EntityKind::from_keyword(w) {
                Some(k) => self.entity(k).map(Item::Entity),
                None => fail(start, format!("unexpected `{w}`, expected an item")),
            },
        };
        match r {
            Ok(item) => item,
            Err(e) => self.item_hole(start_pos, start, false, Some(e)),
        }
    }

    fn item_hole(
        &mut self,
        start_pos: usize,
        start: Span,
        in_block: bool,
        e: Option<ParseErr>,
    ) -> Item {
        let e = e.unwrap_or_else(|| ParseErr {
            span: start,
            message: format!(
                "unexpected {}, expected an item",
                self.peek().tok.describe()
            ),
        });
        self.hole_diag(&e);
        if self.pos == start_pos {
            // Guarantee progress on a token that no item can start with.
            if self.at_p(Punct::RBrace) || self.at_p(Punct::Semi) {
                self.bump();
            }
        }
        self.resync(in_block);
        let end = self.prev_end().max(start.end);
        let id = self.id();
        let span = Span::new(start.start, end);
        self.register(id, span.start, span.end, span.end, None);
        Item::Hole {
            id,
            message: e.message,
            span,
        }
    }

    fn include(&mut self) -> PResult<Include> {
        let start = self.bump().span;
        let path = self.string("an include path string")?;
        let mount = if self.eat_kw("as") {
            Some(self.ref_path("a mount prefix")?)
        } else {
            None
        };
        let semi = self.expect_p(Punct::Semi)?;
        let id = self.id();
        let span = start.to(semi.span);
        self.register(id, span.start, span.end, span.end, None);
        Ok(Include {
            id,
            path,
            mount,
            span,
        })
    }

    fn namespace(&mut self) -> PResult<Namespace> {
        let start = self.bump().span;
        let name = self.name("a namespace name")?;
        let open = self.expect_p(Punct::LBrace)?;
        let mut items = Vec::new();
        while !self.at_p(Punct::RBrace) && !self.at_eof() {
            let item_start_pos = self.pos;
            let item_start = self.peek().span;
            let item = self.item();
            if self.pos == item_start_pos && !self.at_eof() {
                // `item` always consumes; this is a belt-and-braces progress guard.
                let _ = item_start;
                self.bump();
            }
            items.push(item);
        }
        let close = self.expect_p(Punct::RBrace)?;
        let id = self.id();
        let span = start.to(close.span);
        self.register(
            id,
            span.start,
            open.span.end,
            span.end,
            Some(close.span.start),
        );
        Ok(Namespace {
            id,
            name,
            items,
            span,
        })
    }

    fn top_exception(&mut self) -> PResult<TopException> {
        let start = self.peek().span;
        let exception = self.exception()?;
        let semi = self.expect_p(Punct::Semi)?;
        let id = self.id();
        let span = start.to(semi.span);
        self.register(id, span.start, span.end, span.end, None);
        Ok(TopException {
            id,
            exception,
            span,
        })
    }

    fn exception(&mut self) -> PResult<Exception> {
        let kw = self.bump();
        let Tok::Ident(word) = &kw.tok else {
            unreachable!("caller checked the keyword");
        };
        let kind = match word.as_str() {
            "accept" => ExcKind::Accept,
            "defer" => ExcKind::Defer,
            _ => ExcKind::Hotfix,
        };
        let rule = self.any_ident("a rule id")?;
        if !is_rule_token(&rule.text) {
            self.diags.push(Diagnostic::new(
                "MDL000",
                rule.span,
                format!(
                    "`{}` is not a rule id; rule ids are written in their id form such as `SYS004`, never as slug aliases",
                    rule.text
                ),
            ));
        }
        let on = if self.eat_kw("on") {
            Some(self.ref_path("an entity name")?)
        } else {
            None
        };
        let attrs = self.key_vals()?;
        Ok(Exception {
            kind,
            rule,
            on,
            attrs,
        })
    }

    // ----- entities -----

    fn entity(&mut self, kind: EntityKind) -> PResult<Entity> {
        let start = self.bump().span;
        let name = self.name("an entity name")?;
        let header = self.header_of(kind)?;
        let mut clauses = Vec::new();
        let (head_end, close_at, end);
        if kind == EntityKind::Boundary && self.at_p(Punct::Semi) {
            let semi = self.bump();
            head_end = semi.span.end;
            close_at = None;
            end = semi.span.end;
        } else {
            let open = self.expect_p(Punct::LBrace)?;
            head_end = open.span.end;
            self.clauses(&mut clauses);
            let close = self.expect_p(Punct::RBrace)?;
            close_at = Some(close.span.start);
            end = close.span.end;
        }
        let id = self.id();
        let span = Span::new(start.start, end);
        self.register(id, span.start, head_end, end, close_at);
        Ok(Entity {
            id,
            kind,
            extension: false,
            target: RefPath {
                rooted: false,
                segments: vec![name.text.clone()],
                span: name.span,
            },
            name,
            header,
            clauses,
            span,
        })
    }

    fn header_of(&mut self, kind: EntityKind) -> PResult<Header> {
        match kind {
            EntityKind::Node => {
                if self.eat_p(Punct::Colon) {
                    let trust = self.any_ident("a trust level")?;
                    Ok(Header::Node { trust: Some(trust) })
                } else {
                    Ok(Header::Node { trust: None })
                }
            }
            EntityKind::Flow => {
                self.expect_p(Punct::Colon)?;
                let from = self.ref_path("a node name")?;
                self.expect_p(Punct::Arrow)?;
                let to = self.ref_path("a node name")?;
                Ok(Header::Flow { from, to })
            }
            EntityKind::Boundary => {
                let direction = if self.eat_kw("endorse") {
                    Direction::Endorse
                } else if self.eat_kw("declassify") {
                    Direction::Declassify
                } else {
                    return self.unexpected("`endorse` or `declassify`");
                };
                let flow = self.ref_path("a flow name")?;
                self.expect_p(Punct::Colon)?;
                let from = self.any_ident("a lattice element")?;
                self.expect_p(Punct::Arrow)?;
                let to = self.any_ident("a lattice element")?;
                let when = if self.eat_kw("when") {
                    Some(self.string("a predicate string")?)
                } else {
                    None
                };
                Ok(Header::Boundary {
                    direction,
                    flow,
                    from,
                    to,
                    when,
                })
            }
            _ => Ok(Header::None),
        }
    }

    fn extend(&mut self) -> PResult<Entity> {
        let start = self.bump().span;
        let kw = self.any_ident("an entity kind keyword")?;
        let Some(kind) = EntityKind::from_keyword(&kw.text) else {
            return fail(kw.span, format!("`{}` is not an entity kind", kw.text));
        };
        let target = self.ref_path("an entity name")?;
        let open = self.expect_p(Punct::LBrace)?;
        let mut clauses = Vec::new();
        self.clauses(&mut clauses);
        let close = self.expect_p(Punct::RBrace)?;
        let id = self.id();
        let span = start.to(close.span);
        self.register(
            id,
            span.start,
            open.span.end,
            span.end,
            Some(close.span.start),
        );
        let last = target.segments.last().cloned().unwrap_or_default();
        Ok(Entity {
            id,
            kind,
            extension: true,
            name: Ident {
                text: last,
                span: target.span,
            },
            target,
            header: Header::None,
            clauses,
            span,
        })
    }

    fn clauses(&mut self, out: &mut Vec<Clause>) {
        while !self.at_p(Punct::RBrace) && !self.at_eof() {
            let start_pos = self.pos;
            let start = self.peek().span;
            match self.clause() {
                Ok(c) => out.push(c),
                Err(e) => {
                    self.hole_diag(&e);
                    if self.pos == start_pos && self.at_p(Punct::Semi) {
                        self.bump();
                    }
                    self.resync(true);
                    let span = Span::new(start.start, self.prev_end().max(start.end));
                    let id = self.id();
                    self.register(id, span.start, span.end, span.end, None);
                    out.push(Clause {
                        id,
                        kind: ClauseKind::Hole(e.message),
                        span,
                    });
                }
            }
            if self.pos == start_pos && !self.at_p(Punct::RBrace) && !self.at_eof() {
                self.bump();
            }
        }
    }

    fn clause(&mut self) -> PResult<Clause> {
        let start = self.peek().span;
        let Tok::Ident(word) = self.peek().tok.clone() else {
            return self.unexpected("a clause keyword");
        };
        let kind = self.clause_kind(&word, start)?;
        let semi = self.expect_p(Punct::Semi)?;
        let id = self.id();
        let span = start.to(semi.span);
        self.register(id, span.start, span.end, span.end, None);
        Ok(Clause { id, kind, span })
    }

    #[allow(
        clippy::too_many_lines,
        reason = "a flat dispatch with one arm per clause keyword (grmb-spec 4)"
    )]
    fn clause_kind(&mut self, word: &str, start: Span) -> PResult<ClauseKind> {
        if let Some(kind) = LinkKind::ALL.into_iter().find(|k| k.keyword() == word) {
            self.bump();
            let target = self.ref_path("a vmodel name")?;
            let because = self.because_opt()?;
            return Ok(ClauseKind::Link(Link {
                kind,
                target,
                because,
            }));
        }
        self.bump();
        Ok(match word {
            "alias" => ClauseKind::Alias(self.name("an alias")?),
            "renamed_from" => ClauseKind::RenamedFrom(self.name("a former name")?),
            "attr" => {
                let key = self.name("an attribute key")?;
                let value = if self.eat_p(Punct::Eq) {
                    Some(self.value()?)
                } else {
                    None
                };
                ClauseKind::Attr { key, value }
            }
            "accept" | "defer" | "hotfix" => {
                self.pos -= 1;
                ClauseKind::Exception(self.exception()?)
            }
            "kind" => ClauseKind::Kind(self.any_ident("a kind")?),
            "clearance" => ClauseKind::Clearance(self.any_ident("a label")?),
            "owns" => ClauseKind::Owns(self.selector()?),
            "surface" => ClauseKind::Surface(self.selector()?),
            "may" => ClauseKind::May(self.may()?),
            "excuses" => {
                let atom = self.atom()?;
                let attrs = self.key_vals()?;
                ClauseKind::Excuses(Excuses { atom, attrs })
            }
            "label" => ClauseKind::Label(self.any_ident("a label")?),
            "rate" => ClauseKind::Quantity(QuantKey::Rate, self.quantity()?),
            "age" => ClauseKind::Quantity(QuantKey::Age, self.quantity()?),
            "size" => ClauseKind::Quantity(QuantKey::Size, self.quantity()?),
            "fanout" => {
                let t = self.peek().clone();
                let Tok::Number(n) = t.tok else {
                    return self.unexpected("a number");
                };
                self.bump();
                ClauseKind::Fanout(Spanned {
                    value: n,
                    span: t.span,
                })
            }
            "growth" => ClauseKind::Growth(self.quantity()?),
            "transport" => {
                let mut atoms = vec![self.atom()?];
                while self.eat_p(Punct::Comma) {
                    atoms.push(self.atom()?);
                }
                ClauseKind::Transport(atoms)
            }
            "condition" => ClauseKind::Condition(self.any_ident("`on_ok` or `on_err`")?),
            "producer" => ClauseKind::Producer(self.selector()?),
            "consumer" => ClauseKind::Consumer(self.selector()?),
            "contract" => ClauseKind::Contract(self.ref_path("a contract name")?),
            "shape" => ClauseKind::Shape(self.selector()?),
            "versioning" => ClauseKind::Versioning(Versioning {
                attrs: self.key_vals()?,
            }),
            "noflow" | "reach" => {
                let a = self.ref_path("a node name")?;
                self.expect_p(Punct::Arrow)?;
                let b = self.ref_path("a node name")?;
                ClauseKind::What(if word == "noflow" {
                    ClaimWhat::Noflow(a, b)
                } else {
                    ClaimWhat::Reach(a, b)
                })
            }
            "bound" => {
                let metric = self.any_ident("a metric")?;
                let target = self.ref_path("a node or flow name")?;
                self.expect_p(Punct::Le)?;
                let limit = self.quantity()?;
                ClauseKind::What(ClaimWhat::Bound {
                    metric,
                    target,
                    limit,
                })
            }
            "proof" => ClauseKind::Proof(self.any_ident("a proof level")?),
            "assumed" => ClauseKind::Assumed(self.key_vals()?),
            "evidence" => {
                if self.eat_kw("tests") {
                    ClauseKind::Evidence(Evidence::Tests(self.selector()?))
                } else if self.eat_kw("ref") {
                    ClauseKind::Evidence(Evidence::Ref(self.string("a symref string")?))
                } else {
                    return self.unexpected("`tests` or `ref`");
                }
            }
            "level" => ClauseKind::Level(self.any_ident("a level")?),
            "ref" => ClauseKind::Ref(self.string("a symref string")?),
            "runnable" => ClauseKind::Runnable(self.selector()?),
            "version" => ClauseKind::Version(self.string("a version string")?),
            "digest" => ClauseKind::Digest(self.string("a digest string")?),
            "baseline" => {
                return fail(
                    start,
                    "`baseline` is never written in a .grmb file; pools live in the ratchet lock",
                );
            }
            other => {
                return fail(start, format!("unexpected `{other}`, expected a clause"));
            }
        })
    }

    fn because_opt(&mut self) -> PResult<Option<Spanned<String>>> {
        if !self.at_kw("because") {
            return Ok(None);
        }
        let kv = self.key_vals()?;
        match kv.into_iter().next() {
            Some(KeyVal {
                value:
                    Spanned {
                        value: Value::Str(s),
                        span,
                    },
                ..
            }) => Ok(Some(Spanned { value: s, span })),
            _ => self.unexpected("`because=\"...\"`"),
        }
    }

    fn may(&mut self) -> PResult<May> {
        let atom = self.atom()?;
        let mut args = Vec::new();
        if self.eat_p(Punct::LParen) {
            while !self.at_p(Punct::RParen) {
                args.push(self.string("a string argument")?);
                if !self.eat_p(Punct::Comma) {
                    break;
                }
            }
            self.expect_p(Punct::RParen)?;
        }
        let at = if self.eat_kw("at") {
            Some(self.selector()?)
        } else {
            None
        };
        Ok(May { atom, args, at })
    }
}

/// True for a rule token `[A-Z]+[0-9]+`.
pub fn is_rule_token(s: &str) -> bool {
    let letters = s.bytes().take_while(u8::is_ascii_uppercase).count();
    letters > 0 && letters < s.len() && s.bytes().skip(letters).all(|b| b.is_ascii_digit())
}

/// Rule 2 of grmb-spec 8.1: the item whose `;` or opening `{` ends closest before `c` on its line.
fn trailing_target(targets: &[Target], c: &Comment, src: &str) -> Option<usize> {
    let mut best: Option<(usize, usize)> = None;
    for t in targets {
        for anchor in [t.end, t.head_end] {
            let same_line = src
                .get(anchor..c.span.start)
                .is_some_and(|gap| !gap.contains('\n'));
            if anchor <= c.span.start && same_line && best.is_none_or(|(a, _)| anchor > a) {
                best = Some((anchor, t.id));
            }
        }
    }
    best.map(|(_, id)| id)
}

/// Rules 1 and 3 of grmb-spec 8.1: the outermost item starting at the next token, or the
/// entity whose closing `}` is the next token.
fn leading_target(targets: &[Target], next: &Token) -> Option<usize> {
    targets
        .iter()
        .filter(|t| t.start == next.span.start)
        .max_by_key(|t| t.end)
        .map(|t| t.id)
        .or_else(|| {
            (next.tok == Tok::P(Punct::RBrace))
                .then(|| targets.iter().find(|t| t.close == Some(next.span.start)))
                .flatten()
                .map(|t| t.id)
        })
}

/// Binds comments to targets by the rules of grmb-spec 8.1.
fn attach(targets: &[Target], toks: &[Token], comments: &[Comment], src: &str) -> Attachments {
    let mut out = Attachments::default();
    let mut by: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    for (ci, c) in comments.iter().enumerate() {
        let mut bound = if c.kind == CommentKind::Doc {
            None
        } else {
            trailing_target(targets, c, src)
        };
        if bound.is_none()
            && let Some(next) = toks.iter().find(|t| t.span.start >= c.span.end)
        {
            bound = leading_target(targets, next);
        }
        // Inside a statement: the innermost enclosing target.
        if bound.is_none() {
            bound = targets
                .iter()
                .filter(|t| t.start < c.span.start && c.span.end <= t.end)
                .min_by_key(|t| t.end - t.start)
                .map(|t| t.id);
        }
        match bound {
            Some(id) => by.entry(id).or_default().push(ci),
            None => out.file.push(ci),
        }
    }
    out.by_target = by;
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse(src: &str) -> ParsedFile {
        parse_file("t.grmb", src.as_bytes())
    }

    #[test]
    fn minimal_model_parses() {
        let f = parse("grimble = \"2\";\nmodule m;\nnode a : trusted { owns \"x/**\"; }\n");
        assert!(f.diags.is_empty(), "{:?}", f.diags);
        assert_eq!(f.items.len(), 1);
    }

    #[test]
    fn syntax_error_becomes_hole_and_parsing_continues() {
        let f = parse(
            "grimble = \"2\";\nmodule m;\nnode a : trusted { owns ; label X; owns \"y\"; }\nnode b : trusted {}\n",
        );
        assert_eq!(f.holes, 1);
        let Item::Entity(e) = &f.items[0] else {
            panic!("entity");
        };
        assert_eq!(e.clauses.len(), 3);
        assert!(matches!(e.clauses[0].kind, ClauseKind::Hole(_)));
        assert_eq!(f.items.len(), 2);
    }

    #[test]
    fn missing_header_refuses_the_file() {
        let f = parse("module m;\n");
        assert!(matches!(f.status, FileStatus::Refused(_)));
        assert_eq!(f.diags[0].rule, "MDL007");
    }

    #[test]
    fn bare_cr_and_bom_are_opaque() {
        assert!(matches!(
            parse_file("a", b"grimble = \"2\";\rmodule m;").status,
            FileStatus::Opaque("binary")
        ));
        assert!(matches!(
            parse_file("a", b"\xEF\xBB\xBFgrimble = \"2\";").status,
            FileStatus::Opaque("not-utf8")
        ));
    }

    #[test]
    fn comments_bind_by_rule() {
        let src = "// file\ngrimble = \"2\";\nmodule m;\n// lead\nnode a : trusted { // trail\n  // before clause\n  owns \"x\"; // after clause\n  // closer\n}\n";
        let f = parse(src);
        let Item::Entity(e) = &f.items[0] else {
            panic!("entity");
        };
        assert_eq!(f.attachments.file.len(), 1);
        let texts = |id| {
            f.attachments
                .of(id)
                .iter()
                .map(|&i| f.comments[i].text.clone())
                .collect::<Vec<_>>()
        };
        assert_eq!(texts(e.id), ["// lead", "// trail", "// closer"]);
        assert_eq!(
            texts(e.clauses[0].id),
            ["// before clause", "// after clause"]
        );
    }
}
