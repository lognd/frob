//! Lexer + recursive-descent parser for the strata surface grammar v0
//! (docs/strata/surface.md#parser). Deterministic and fuzz-safe: every
//! malformed input yields an `err` JSON object with line/col instead of
//! panicking (charter D3 as amended: the parser is compute-heavy and
//! lives here; Python only calls `parse_source` and validates the JSON
//! into pydantic AST models).

use serde::Serialize;
use serde_json::json;

// ---------------------------------------------------------------------
// Lexer
// ---------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
enum TokKind {
    Ident(String),
    Number(f64),
    Str(String),
    Symbol(char), // one of : { } ; -> ( ) . .. handled specially below
    Arrow,        // ->
    DotDot,       // ..
    Eof,
}

#[derive(Debug, Clone)]
struct Token {
    kind: TokKind,
    line: usize,
    col: usize,
}

#[derive(Debug, Clone)]
struct ParseError {
    line: usize,
    col: usize,
    message: String,
}

fn is_ident_start(c: char) -> bool {
    c.is_ascii_alphabetic() || c == '_'
}

fn is_ident_cont(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '_'
}

/// Turn source text into a token stream, or the first lexical error found.
///
/// WHY: a flat token vector lets the recursive-descent parser below use
/// simple lookahead without re-scanning characters; `//` comments and all
/// whitespace/newlines are stripped here so the parser never sees them.
fn lex(text: &str) -> Result<Vec<Token>, ParseError> {
    let chars: Vec<char> = text.chars().collect();
    let mut i = 0usize;
    let mut line = 1usize;
    let mut col = 1usize;
    let mut toks: Vec<Token> = Vec::new();

    macro_rules! advance {
        () => {{
            if i < chars.len() {
                if chars[i] == '\n' {
                    line += 1;
                    col = 1;
                } else {
                    col += 1;
                }
                i += 1;
            }
        }};
    }

    while i < chars.len() {
        let c = chars[i];
        if c == ' ' || c == '\t' || c == '\r' || c == '\n' {
            advance!();
            continue;
        }
        if c == '/' && i + 1 < chars.len() && chars[i + 1] == '/' {
            while i < chars.len() && chars[i] != '\n' {
                advance!();
            }
            continue;
        }
        let start_line = line;
        let start_col = col;
        if is_ident_start(c) {
            let mut s = String::new();
            while i < chars.len() && is_ident_cont(chars[i]) {
                s.push(chars[i]);
                advance!();
            }
            toks.push(Token {
                kind: TokKind::Ident(s),
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if c.is_ascii_digit() {
            let mut s = String::new();
            while i < chars.len() && chars[i].is_ascii_digit() {
                s.push(chars[i]);
                advance!();
            }
            if i < chars.len()
                && chars[i] == '.'
                && i + 1 < chars.len()
                && chars[i + 1].is_ascii_digit()
            {
                s.push('.');
                advance!();
                while i < chars.len() && chars[i].is_ascii_digit() {
                    s.push(chars[i]);
                    advance!();
                }
            }
            let value: f64 = s.parse().map_err(|_| ParseError {
                line: start_line,
                col: start_col,
                message: format!("malformed number literal {:?}", s),
            })?;
            toks.push(Token {
                kind: TokKind::Number(value),
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if c == '"' {
            advance!();
            let mut s = String::new();
            while i < chars.len() && chars[i] != '"' {
                if chars[i] == '\n' {
                    return Err(ParseError {
                        line: start_line,
                        col: start_col,
                        message: "unterminated string literal".to_string(),
                    });
                }
                s.push(chars[i]);
                advance!();
            }
            if i >= chars.len() {
                return Err(ParseError {
                    line: start_line,
                    col: start_col,
                    message: "unterminated string literal".to_string(),
                });
            }
            advance!(); // closing quote
            toks.push(Token {
                kind: TokKind::Str(s),
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if c == '-' && i + 1 < chars.len() && chars[i + 1] == '>' {
            advance!();
            advance!();
            toks.push(Token {
                kind: TokKind::Arrow,
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if c == '.' && i + 1 < chars.len() && chars[i + 1] == '.' {
            advance!();
            advance!();
            toks.push(Token {
                kind: TokKind::DotDot,
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if matches!(c, ':' | '{' | '}' | ';' | '(' | ')' | '%' | '/' | '=' | '<') {
            advance!();
            toks.push(Token {
                kind: TokKind::Symbol(c),
                line: start_line,
                col: start_col,
            });
            continue;
        }
        return Err(ParseError {
            line: start_line,
            col: start_col,
            message: format!("unexpected character {:?}", c),
        });
    }
    toks.push(Token {
        kind: TokKind::Eof,
        line,
        col,
    });
    Ok(toks)
}

// ---------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------

struct Parser {
    toks: Vec<Token>,
    pos: usize,
}

/// A JSON-serializable diagnostic-free AST; every field mirrors the
/// pydantic models in `frob.strata._ast` so json.loads -> model_validate
/// is a straight structural map with no renaming.
#[derive(Serialize, Default)]
struct ModuleAst {
    name: String,
    nodes: Vec<serde_json::Value>,
    flows: Vec<serde_json::Value>,
    boundaries: Vec<serde_json::Value>,
    claims: Vec<serde_json::Value>,
    refines: Vec<serde_json::Value>,
    stores: Vec<serde_json::Value>,
    caches: Vec<serde_json::Value>,
    queues: Vec<serde_json::Value>,
    cdns: Vec<serde_json::Value>,
    balancers: Vec<serde_json::Value>,
}

impl Parser {
    fn new(toks: Vec<Token>) -> Self {
        Parser { toks, pos: 0 }
    }

    fn cur(&self) -> &Token {
        &self.toks[self.pos]
    }

    fn err<T>(&self, message: impl Into<String>) -> Result<T, ParseError> {
        let t = self.cur();
        Err(ParseError {
            line: t.line,
            col: t.col,
            message: message.into(),
        })
    }

    fn advance(&mut self) -> Token {
        let t = self.toks[self.pos].clone();
        if self.pos + 1 < self.toks.len() {
            self.pos += 1;
        }
        t
    }

    fn at_eof(&self) -> bool {
        matches!(self.cur().kind, TokKind::Eof)
    }

    fn peek_ident(&self) -> Option<&str> {
        match &self.cur().kind {
            TokKind::Ident(s) => Some(s.as_str()),
            _ => None,
        }
    }

    fn expect_keyword(&mut self, kw: &str) -> Result<(), ParseError> {
        match self.peek_ident() {
            Some(s) if s == kw => {
                self.advance();
                Ok(())
            }
            _ => self.err(format!("expected keyword {:?}", kw)),
        }
    }

    fn expect_ident(&mut self, what: &str) -> Result<String, ParseError> {
        match &self.cur().kind {
            TokKind::Ident(s) => {
                let s = s.clone();
                self.advance();
                Ok(s)
            }
            _ => self.err(format!("expected {}", what)),
        }
    }

    fn expect_number(&mut self, what: &str) -> Result<f64, ParseError> {
        match self.cur().kind {
            TokKind::Number(n) => {
                self.advance();
                Ok(n)
            }
            _ => self.err(format!("expected {}", what)),
        }
    }

    fn expect_int(&mut self, what: &str) -> Result<i64, ParseError> {
        let n = self.expect_number(what)?;
        Ok(n as i64)
    }

    fn expect_string(&mut self, what: &str) -> Result<String, ParseError> {
        match &self.cur().kind {
            TokKind::Str(s) => {
                let s = s.clone();
                self.advance();
                Ok(s)
            }
            _ => self.err(format!("expected {}", what)),
        }
    }

    fn expect_symbol(&mut self, sym: char) -> Result<(), ParseError> {
        match self.cur().kind {
            TokKind::Symbol(c) if c == sym => {
                self.advance();
                Ok(())
            }
            _ => self.err(format!("expected {:?}", sym)),
        }
    }

    fn at_symbol(&self, sym: char) -> bool {
        matches!(self.cur().kind, TokKind::Symbol(c) if c == sym)
    }

    fn at_keyword(&self, kw: &str) -> bool {
        matches!(&self.cur().kind, TokKind::Ident(s) if s == kw)
    }

    fn expect_arrow(&mut self) -> Result<(), ParseError> {
        match self.cur().kind {
            TokKind::Arrow => {
                self.advance();
                Ok(())
            }
            _ => self.err("expected ->"),
        }
    }

    fn expect_dotdot(&mut self) -> Result<(), ParseError> {
        match self.cur().kind {
            TokKind::DotDot => {
                self.advance();
                Ok(())
            }
            _ => self.err("expected .."),
        }
    }

    /// UNIT := IDENT ('/' IDENT)* | '%'; the next bare IDENT after a
    /// complete unit is never consumed (surface.md: "min" alone, "req/s"
    /// as one unit).
    fn parse_unit(&mut self) -> Result<String, ParseError> {
        if self.at_symbol('%') {
            self.advance();
            return Ok("%".to_string());
        }
        let mut unit = self.expect_ident("unit")?;
        while self.at_symbol('/') {
            self.advance();
            let part = self.expect_ident("unit component after /")?;
            unit.push('/');
            unit.push_str(&part);
        }
        Ok(unit)
    }

    fn parse_quantity(&mut self, what: &str) -> Result<serde_json::Value, ParseError> {
        let value = self.expect_number(what)?;
        let unit = self.parse_unit()?;
        Ok(json!({"value": value, "unit": unit}))
    }

    /// ATTRVAL := IDENT ['=' IDENT], joined as "a=b" when '=' is present.
    fn parse_attrval(&mut self) -> Result<String, ParseError> {
        let key = self.expect_ident("attribute name")?;
        if self.at_symbol('=') {
            self.advance();
            let val = self.expect_ident("attribute value after =")?;
            Ok(format!("{}={}", key, val))
        } else {
            Ok(key)
        }
    }

    fn parse_module(
        &mut self,
        ast: &mut ModuleAst,
        seen_module: &mut bool,
    ) -> Result<(), ParseError> {
        if *seen_module {
            return self.err("duplicate module statement");
        }
        self.advance(); // 'module'
        let name = self.expect_ident("module name")?;
        ast.name = name;
        *seen_module = true;
        Ok(())
    }

    fn parse_node(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'node'
        let id = self.expect_ident("node id")?;
        self.expect_symbol(':')?;
        let trust = self.expect_ident("trust level")?;
        let mut is_abstract = false;
        if self.at_keyword("abstract") {
            self.advance();
            is_abstract = true;
        }
        let mut clearance = "Secret".to_string();
        let mut attrs: Vec<String> = Vec::new();
        let mut residence: Option<String> = None;
        let mut capacity: Option<serde_json::Value> = None;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("clearance") {
                    self.advance();
                    clearance = self.expect_ident("clearance level")?;
                } else if self.at_keyword("attr") {
                    self.advance();
                    attrs.push(self.parse_attrval()?);
                } else if self.at_keyword("residence") {
                    self.advance();
                    residence = Some(self.expect_ident("residence atom")?);
                } else if self.at_keyword("capacity") {
                    self.advance();
                    let rate = self.parse_quantity("capacity rate")?;
                    self.expect_keyword("replicas")?;
                    let lo = self.expect_int("replicas_min")?;
                    self.expect_dotdot()?;
                    let hi = self.expect_int("replicas_max")?;
                    capacity = Some(json!({"rate": rate, "replicas_min": lo, "replicas_max": hi}));
                } else {
                    return self.err("unknown node property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.nodes.push(json!({
            "id": id,
            "trust": trust,
            "is_abstract": is_abstract,
            "clearance": clearance,
            "attrs": attrs,
            "capacity": capacity,
            "residence": residence,
        }));
        Ok(())
    }

    fn parse_flow(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'flow'
        let id = self.expect_ident("flow id")?;
        self.expect_symbol(':')?;
        let src = self.expect_ident("flow src")?;
        self.expect_arrow()?;
        let dst = self.expect_ident("flow dst")?;
        let mut label = "Public".to_string();
        let mut age: Option<serde_json::Value> = None;
        let mut rate: Option<serde_json::Value> = None;
        let mut size: Option<serde_json::Value> = None;
        let mut attrs: Vec<String> = Vec::new();
        let mut transport: Vec<String> = Vec::new();
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("label") {
                    self.advance();
                    label = self.expect_ident("label")?;
                } else if self.at_keyword("age") {
                    self.advance();
                    age = Some(self.parse_quantity("age")?);
                } else if self.at_keyword("rate") {
                    self.advance();
                    rate = Some(self.parse_quantity("rate")?);
                } else if self.at_keyword("size") {
                    self.advance();
                    size = Some(self.parse_quantity("size")?);
                } else if self.at_keyword("attr") {
                    self.advance();
                    attrs.push(self.parse_attrval()?);
                } else if self.at_keyword("transport") {
                    self.advance();
                    transport.push(self.expect_ident("transport atom")?);
                } else {
                    return self.err("unknown flow property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.flows.push(json!({
            "id": id,
            "src": src,
            "dst": dst,
            "label": label,
            "age": age,
            "rate": rate,
            "size": size,
            "attrs": attrs,
            "transport": transport,
        }));
        Ok(())
    }

    fn parse_boundary(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'boundary'
        let id = self.expect_ident("boundary id")?;
        let kind = if self.at_keyword("endorse") {
            self.advance();
            "endorse".to_string()
        } else if self.at_keyword("declassify") {
            self.advance();
            "declassify".to_string()
        } else {
            return self.err("expected endorse or declassify");
        };
        let flow_id = self.expect_ident("boundary flow id")?;
        self.expect_symbol(':')?;
        let from_level = self.expect_ident("from level")?;
        self.expect_arrow()?;
        let to_level = self.expect_ident("to level")?;
        let mut predicate = String::new();
        if self.at_keyword("when") {
            self.advance();
            predicate = self.expect_string("predicate string")?;
        }
        ast.boundaries.push(json!({
            "id": id,
            "kind": kind,
            "flow_id": flow_id,
            "from_level": from_level,
            "to_level": to_level,
            "predicate": predicate,
        }));
        Ok(())
    }

    /// refine := "refine" ID "into" "{" (node_stmt | flow_stmt)* bind "}"
    ///
    /// WHY: decomposes an abstract node into inner nodes/flows plus
    /// exactly one `binds` clause tying the abstraction's external edges
    /// back to a chosen inner node (docs/strata/surface.md#refinement);
    /// zero or two+ binds, or a binds LHS that does not match the refine
    /// target, are parse errors rather than silent defaults (law 2).
    fn parse_refine(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'refine'
        let target = self.expect_ident("refine target id")?;
        self.expect_keyword("into")?;
        self.expect_symbol('{')?;
        let mut nodes: Vec<serde_json::Value> = Vec::new();
        let mut flows: Vec<serde_json::Value> = Vec::new();
        let mut bind_to: Option<String> = None;
        loop {
            if self.at_symbol('}') {
                break;
            }
            if self.at_keyword("node") {
                let mut inner = ModuleAst::default();
                self.parse_node(&mut inner)?;
                nodes.push(inner.nodes.remove(0));
            } else if self.at_keyword("flow") {
                let mut inner = ModuleAst::default();
                self.parse_flow(&mut inner)?;
                flows.push(inner.flows.remove(0));
            } else if self.at_keyword("binds") {
                let tok = self.cur().clone();
                self.advance();
                let lhs = self.expect_ident("binds lhs")?;
                self.expect_symbol('=')?;
                let rhs = self.expect_ident("binds rhs")?;
                if bind_to.is_some() {
                    return Err(ParseError {
                        line: tok.line,
                        col: tok.col,
                        message: "refine block needs exactly one binds clause".to_string(),
                    });
                }
                if lhs != target {
                    return Err(ParseError {
                        line: tok.line,
                        col: tok.col,
                        message: format!(
                            "binds lhs {:?} must equal refine target {:?}",
                            lhs, target
                        ),
                    });
                }
                bind_to = Some(rhs);
            } else {
                return self.err("expected node, flow, or binds inside refine block");
            }
            if self.at_symbol(';') {
                self.advance();
            }
        }
        self.expect_symbol('}')?;
        let bind_to = match bind_to {
            Some(b) => b,
            None => {
                let t = self.cur();
                return Err(ParseError {
                    line: t.line,
                    col: t.col,
                    message: "refine block needs exactly one binds clause".to_string(),
                });
            }
        };
        ast.refines.push(json!({
            "target": target,
            "nodes": nodes,
            "flows": flows,
            "bind_to": bind_to,
        }));
        Ok(())
    }

    /// PERCENT := NUMBER '%'; used by `hit` on cache/cdn (std.infra).
    fn parse_percent(&mut self, what: &str) -> Result<f64, ParseError> {
        let n = self.expect_number(what)?;
        self.expect_symbol('%')?;
        Ok(n)
    }

    /// store := "store" ID ":" TRUST "{" store_prop (";" store_prop)* "}"?
    /// store_prop := node_prop | "engine" IDENT | "immutable" | "append_only"
    ///
    /// WHY: store is std.infra's node-with-extras; it reuses the node_prop
    /// surface (clearance/attr/residence/capacity) verbatim plus engine and
    /// the immutable/append_only markers the elaborator needs for the
    /// cdn-unlimited-staleness pairing (docs/strata/surface.md#std-infra).
    fn parse_store(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'store'
        let id = self.expect_ident("store id")?;
        self.expect_symbol(':')?;
        let trust = self.expect_ident("trust level")?;
        let mut clearance = "Secret".to_string();
        let mut attrs: Vec<String> = Vec::new();
        let mut residence: Option<String> = None;
        let mut capacity: Option<serde_json::Value> = None;
        let mut engine: Option<String> = None;
        let mut immutable = false;
        let mut append_only = false;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("clearance") {
                    self.advance();
                    clearance = self.expect_ident("clearance level")?;
                } else if self.at_keyword("attr") {
                    self.advance();
                    attrs.push(self.parse_attrval()?);
                } else if self.at_keyword("residence") {
                    self.advance();
                    residence = Some(self.expect_ident("residence atom")?);
                } else if self.at_keyword("capacity") {
                    self.advance();
                    let rate = self.parse_quantity("capacity rate")?;
                    self.expect_keyword("replicas")?;
                    let lo = self.expect_int("replicas_min")?;
                    self.expect_dotdot()?;
                    let hi = self.expect_int("replicas_max")?;
                    capacity = Some(json!({"rate": rate, "replicas_min": lo, "replicas_max": hi}));
                } else if self.at_keyword("engine") {
                    self.advance();
                    engine = Some(self.expect_ident("engine name")?);
                } else if self.at_keyword("immutable") {
                    self.advance();
                    immutable = true;
                } else if self.at_keyword("append_only") {
                    self.advance();
                    append_only = true;
                } else {
                    return self.err("unknown store property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.stores.push(json!({
            "id": id,
            "trust": trust,
            "clearance": clearance,
            "attrs": attrs,
            "capacity": capacity,
            "residence": residence,
            "engine": engine,
            "immutable": immutable,
            "append_only": append_only,
        }));
        Ok(())
    }

    /// cache := "cache" ID "of" ID "{" cache_prop (";" cache_prop)* "}"?
    /// cache_prop := "keyed_by" IDENT | "ttl" QUANTITY | "staleness" QUANTITY
    ///             | "hit" PERCENT | "policy" IDENT | "invalidate_on" IDENT
    ///
    /// WHY: `invalidate_on` is repeatable (a cache may be invalidated by
    /// several write flows), collected in declaration order so the
    /// elaborator's mandatory-invalidation check can report every declared
    /// edge (docs/strata/surface.md#std-infra).
    fn parse_cache(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'cache'
        let id = self.expect_ident("cache id")?;
        self.expect_keyword("of")?;
        let of = self.expect_ident("cache source-of-truth id")?;
        let mut keyed_by: Option<String> = None;
        let mut ttl: Option<serde_json::Value> = None;
        let mut staleness: Option<serde_json::Value> = None;
        let mut hit: Option<f64> = None;
        let mut policy: Option<String> = None;
        let mut invalidate_on: Vec<String> = Vec::new();
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("keyed_by") {
                    self.advance();
                    keyed_by = Some(self.expect_ident("keyed_by field")?);
                } else if self.at_keyword("ttl") {
                    self.advance();
                    ttl = Some(self.parse_quantity("ttl")?);
                } else if self.at_keyword("staleness") {
                    self.advance();
                    staleness = Some(self.parse_quantity("staleness")?);
                } else if self.at_keyword("hit") {
                    self.advance();
                    hit = Some(self.parse_percent("hit ratio")?);
                } else if self.at_keyword("policy") {
                    self.advance();
                    policy = Some(self.expect_ident("cache policy")?);
                } else if self.at_keyword("invalidate_on") {
                    self.advance();
                    invalidate_on.push(self.expect_ident("invalidate_on flow id")?);
                } else {
                    return self.err("unknown cache property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.caches.push(json!({
            "id": id,
            "of": of,
            "keyed_by": keyed_by,
            "ttl": ttl,
            "staleness": staleness,
            "hit": hit,
            "policy": policy,
            "invalidate_on": invalidate_on,
        }));
        Ok(())
    }

    /// queue := "queue" ID "{" queue_prop (";" queue_prop)* "}"?
    /// queue_prop := "delivery" IDENT | "ordering" IDENT | "attr" ATTRVAL
    ///             | "clearance" IDENT
    fn parse_queue(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'queue'
        let id = self.expect_ident("queue id")?;
        let mut delivery: Option<String> = None;
        let mut ordering: Option<String> = None;
        let mut attrs: Vec<String> = Vec::new();
        let mut clearance: Option<String> = None;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("delivery") {
                    self.advance();
                    delivery = Some(self.expect_ident("delivery mode")?);
                } else if self.at_keyword("ordering") {
                    self.advance();
                    ordering = Some(self.expect_ident("ordering mode")?);
                } else if self.at_keyword("attr") {
                    self.advance();
                    attrs.push(self.parse_attrval()?);
                } else if self.at_keyword("clearance") {
                    self.advance();
                    clearance = Some(self.expect_ident("clearance level")?);
                } else {
                    return self.err("unknown queue property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.queues.push(json!({
            "id": id,
            "delivery": delivery,
            "ordering": ordering,
            "attrs": attrs,
            "clearance": clearance,
        }));
        Ok(())
    }

    /// cdn := "cdn" ID "of" ID "{" cdn_prop (";" cdn_prop)* "}"?
    /// cdn_prop := "provider" IDENT ":" TRUST | "staleness" (QUANTITY | "unlimited")
    ///           | "hit" PERCENT | "tls_terminates_at_provider"
    fn parse_cdn(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'cdn'
        let id = self.expect_ident("cdn id")?;
        self.expect_keyword("of")?;
        let of = self.expect_ident("cdn source-of-truth id")?;
        let mut provider: Option<String> = None;
        let mut provider_trust: Option<String> = None;
        let mut staleness: Option<serde_json::Value> = None;
        let mut staleness_unlimited = false;
        let mut hit: Option<f64> = None;
        let mut tls_terminates_at_provider = false;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("provider") {
                    self.advance();
                    provider = Some(self.expect_ident("provider name")?);
                    self.expect_symbol(':')?;
                    provider_trust = Some(self.expect_ident("provider trust level")?);
                } else if self.at_keyword("staleness") {
                    self.advance();
                    if self.at_keyword("unlimited") {
                        self.advance();
                        staleness_unlimited = true;
                    } else {
                        staleness = Some(self.parse_quantity("staleness")?);
                    }
                } else if self.at_keyword("hit") {
                    self.advance();
                    hit = Some(self.parse_percent("hit ratio")?);
                } else if self.at_keyword("tls_terminates_at_provider") {
                    self.advance();
                    tls_terminates_at_provider = true;
                } else {
                    return self.err("unknown cdn property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.cdns.push(json!({
            "id": id,
            "of": of,
            "provider": provider,
            "provider_trust": provider_trust,
            "staleness": staleness,
            "staleness_unlimited": staleness_unlimited,
            "hit": hit,
            "tls_terminates_at_provider": tls_terminates_at_provider,
        }));
        Ok(())
    }

    /// balancer := "balancer" ID "{" balancer_prop (";" balancer_prop)* "}"?
    /// balancer_prop := "policy" IDENT | "sticky"
    fn parse_balancer(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'balancer'
        let id = self.expect_ident("balancer id")?;
        let mut policy: Option<String> = None;
        let mut sticky = false;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("policy") {
                    self.advance();
                    policy = Some(self.expect_ident("balancer policy")?);
                } else if self.at_keyword("sticky") {
                    self.advance();
                    sticky = true;
                } else {
                    return self.err("unknown balancer property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.balancers.push(json!({
            "id": id,
            "policy": policy,
            "sticky": sticky,
        }));
        Ok(())
    }

    fn parse_metric(&mut self) -> Result<String, ParseError> {
        let m = self.expect_ident("metric")?;
        match m.as_str() {
            "age" | "rate" | "latency" | "size" | "utilization" => Ok(m),
            _ => self.err(format!("unknown metric {:?}", m)),
        }
    }

    /// claim_body := noflow ID -> ID | reach ID -> ID | bound METRIC ID <= NUMBER UNIT
    fn parse_claim_body(&mut self) -> Result<(String, serde_json::Value), ParseError> {
        if self.at_keyword("noflow") {
            self.advance();
            let src = self.expect_ident("noflow src")?;
            self.expect_arrow()?;
            let dst = self.expect_ident("noflow dst")?;
            Ok(("noflow".to_string(), json!({"src": src, "dst": dst})))
        } else if self.at_keyword("reach") {
            self.advance();
            let src = self.expect_ident("reach src")?;
            self.expect_arrow()?;
            let dst = self.expect_ident("reach dst")?;
            Ok(("reach".to_string(), json!({"src": src, "dst": dst})))
        } else if self.at_keyword("bound") {
            self.advance();
            let metric = self.parse_metric()?;
            let target = self.expect_ident("bound target")?;
            // '<=' is lexed as two Symbol('<')/Symbol('=')? not declared --
            // spec uses '<=' verbatim; lex '<' as unexpected otherwise, so
            // handle here as two chars via raw symbol checks.
            self.expect_le()?;
            let limit = self.parse_quantity("bound limit")?;
            Ok((
                "bound".to_string(),
                json!({"metric": metric, "target": target, "limit": limit}),
            ))
        } else {
            self.err("expected noflow, reach, or bound")
        }
    }

    fn expect_le(&mut self) -> Result<(), ParseError> {
        // '<=' is two raw chars neither of which is in the lexer's symbol
        // set; recognize them here off the *unconsumed* source is not
        // possible post-lex, so '<' and '=' must be lexed. See lex(): '='
        // is a Symbol; '<' needs handling too -- added there.
        match self.cur().kind {
            TokKind::Symbol('<') => {
                self.advance();
                self.expect_symbol('=')
            }
            _ => self.err("expected <="),
        }
    }

    fn parse_claim(&mut self, ast: &mut ModuleAst, kind: &str) -> Result<(), ParseError> {
        self.advance(); // 'assert' or 'assume'
        let id = self.expect_ident("claim id")?;
        let (body_kind, body) = self.parse_claim_body()?;
        let mut owner: Option<String> = None;
        let mut review: Option<String> = None;
        if kind == "assume" {
            self.expect_keyword("owner")?;
            owner = Some(self.expect_ident("owner")?);
            self.expect_keyword("review")?;
            review = Some(self.expect_string("review date")?);
        }
        ast.claims.push(json!({
            "id": id,
            "kind": body_kind,
            "src": body.get("src").cloned(),
            "dst": body.get("dst").cloned(),
            "metric": body.get("metric").cloned(),
            "target": body.get("target").cloned(),
            "limit": body.get("limit").cloned(),
            "assumed": kind == "assume",
            "owner": owner,
            "review": review,
        }));
        Ok(())
    }

    fn parse_program(&mut self) -> Result<ModuleAst, ParseError> {
        let mut ast = ModuleAst::default();
        let mut seen_module = false;
        while !self.at_eof() {
            let kw = match self.peek_ident() {
                Some(s) => s.to_string(),
                None => return self.err("expected a statement keyword"),
            };
            match kw.as_str() {
                "module" => self.parse_module(&mut ast, &mut seen_module)?,
                "node" | "flow" | "boundary" | "assert" | "assume" | "refine" | "store"
                | "cache" | "queue" | "cdn" | "balancer" => {
                    if !seen_module {
                        return self.err("statement before module declaration");
                    }
                    match kw.as_str() {
                        "node" => self.parse_node(&mut ast)?,
                        "flow" => self.parse_flow(&mut ast)?,
                        "boundary" => self.parse_boundary(&mut ast)?,
                        "assert" => self.parse_claim(&mut ast, "assert")?,
                        "assume" => self.parse_claim(&mut ast, "assume")?,
                        "refine" => self.parse_refine(&mut ast)?,
                        "store" => self.parse_store(&mut ast)?,
                        "cache" => self.parse_cache(&mut ast)?,
                        "queue" => self.parse_queue(&mut ast)?,
                        "cdn" => self.parse_cdn(&mut ast)?,
                        "balancer" => self.parse_balancer(&mut ast)?,
                        _ => unreachable!(),
                    }
                }
                _ => return self.err(format!("unknown keyword {:?}", kw)),
            }
        }
        if !seen_module {
            return self.err("missing module statement");
        }
        Ok(ast)
    }
}

/// Parse strata surface source text into a JSON-encoded AST or diagnostic.
///
/// WHY: the parser is compute-heavy (charter D3, amended 2026-07-17) so it
/// lives in Rust; JSON is the narrowest possible interface back to Python,
/// keeping the grammar's only home in this file instead of duplicated in
/// pydantic validators.
pub(crate) fn parse_source_impl(text: &str) -> String {
    // frob:doc docs/strata/surface.md#parser
    // frob:tests strata-core/src/parse.rs::parse_source_impl kind="unit"
    match lex(text).and_then(|toks| Parser::new(toks).parse_program()) {
        Ok(module) => json!({ "ok": module }).to_string(),
        Err(e) => json!({
            "err": {"line": e.line, "col": e.col, "message": e.message}
        })
        .to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn ok(text: &str) -> Value {
        let s = parse_source_impl(text);
        let v: Value = serde_json::from_str(&s).unwrap();
        v.get("ok")
            .unwrap_or_else(|| panic!("expected ok, got {}", s))
            .clone()
    }

    fn err(text: &str) -> Value {
        let s = parse_source_impl(text);
        let v: Value = serde_json::from_str(&s).unwrap();
        v.get("err")
            .unwrap_or_else(|| panic!("expected err, got {}", s))
            .clone()
    }

    #[test]
    fn parses_bare_module() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module payments");
        assert_eq!(v["name"], "payments");
        assert_eq!(v["nodes"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_node_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node api : trusted abstract {
                clearance Secret;
                attr idempotent;
                attr region=us;
                residence us_east;
                capacity 100 req/s replicas 1..8;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["id"], "api");
        assert_eq!(n["trust"], "trusted");
        assert_eq!(n["is_abstract"], true);
        assert_eq!(n["clearance"], "Secret");
        assert_eq!(n["attrs"][0], "idempotent");
        assert_eq!(n["attrs"][1], "region=us");
        assert_eq!(n["residence"], "us_east");
        assert_eq!(n["capacity"]["rate"]["value"], 100.0);
        assert_eq!(n["capacity"]["rate"]["unit"], "req/s");
        assert_eq!(n["capacity"]["replicas_min"], 1);
        assert_eq!(n["capacity"]["replicas_max"], 8);
    }

    #[test]
    fn parses_flow_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            flow f1 : a -> b {
                label Pii;
                age 250 ms;
                rate 5 req/s;
                size 4 KiB;
                attr delivery=at_least_once;
                transport tls;
            }"#);
        let f = &v["flows"][0];
        assert_eq!(f["src"], "a");
        assert_eq!(f["dst"], "b");
        assert_eq!(f["label"], "Pii");
        assert_eq!(f["age"]["value"], 250.0);
        assert_eq!(f["age"]["unit"], "ms");
        assert_eq!(f["rate"]["unit"], "req/s");
        assert_eq!(f["size"]["unit"], "KiB");
        assert_eq!(f["attrs"][0], "delivery=at_least_once");
        assert_eq!(f["transport"][0], "tls");
    }

    #[test]
    fn parses_percent_unit() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            assert c1 bound utilization api <= 80 %"#);
        assert_eq!(v["claims"][0]["limit"]["unit"], "%");
    }

    #[test]
    fn parses_boundary() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified""#);
        let b = &v["boundaries"][0];
        assert_eq!(b["kind"], "endorse");
        assert_eq!(b["flow_id"], "f1");
        assert_eq!(b["from_level"], "foreign");
        assert_eq!(b["to_level"], "authenticated");
        assert_eq!(b["predicate"], "jwt_verified");
    }

    #[test]
    fn parses_assert_noflow_and_reach() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            assert c1 noflow evil -> api
            assert c2 reach audit -> log"#);
        assert_eq!(v["claims"][0]["kind"], "noflow");
        assert_eq!(v["claims"][1]["kind"], "reach");
    }

    #[test]
    fn parses_assume_with_owner_and_review() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            assume c1 noflow evil -> api owner alice review "2026-08-01""#);
        assert_eq!(v["claims"][0]["assumed"], true);
        assert_eq!(v["claims"][0]["owner"], "alice");
        assert_eq!(v["claims"][0]["review"], "2026-08-01");
    }

    #[test]
    fn error_module_missing() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("node a : trusted");
        assert_eq!(e["message"], "statement before module declaration");
    }

    #[test]
    fn error_duplicate_module() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nmodule b");
        assert_eq!(e["message"], "duplicate module statement");
        assert_eq!(e["line"], 2);
        assert_eq!(e["col"], 1);
    }

    #[test]
    fn error_unknown_keyword() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nbogus x");
        assert_eq!(e["message"], "unknown keyword \"bogus\"");
        assert_eq!(e["line"], 2);
        assert_eq!(e["col"], 1);
    }

    #[test]
    fn error_unknown_node_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nnode n : trusted { bogus x; }");
        assert_eq!(e["message"], "unknown node property");
    }

    #[test]
    fn error_unknown_metric() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nassert c1 bound zorp x <= 1 s");
        assert!(e["message"].as_str().unwrap().contains("unknown metric"));
    }

    #[test]
    fn error_on_empty_input_never_panics() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("");
        assert_eq!(e["message"], "missing module statement");
    }

    #[test]
    fn error_reports_accurate_line_col() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nnode n : trusted {\n  clearance ;\n}");
        assert_eq!(e["line"], 3);
    }

    #[test]
    fn unit_slash_continues_but_stops_at_bare_ident() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nflow f1 : a -> b { rate 5 req/s; }");
        assert_eq!(v["flows"][0]["rate"]["unit"], "req/s");
        let v2 = ok("module m\nnode n : trusted { capacity 1 min replicas 1..1; }");
        assert_eq!(v2["nodes"][0]["capacity"]["rate"]["unit"], "min");
    }

    #[test]
    fn round_trip_small_design() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module payments
            node api : trusted { clearance Pii; capacity 100 req/s replicas 1..8; }
            node evil : foreign
            flow f1 : evil -> api { label Pii; rate 5 req/s; transport tls; }
            boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified"
            assert c1 noflow evil -> api
            assume c2 bound age api <= 30 s owner alice review "2026-09-01""#);
        assert_eq!(v["nodes"].as_array().unwrap().len(), 2);
        assert_eq!(v["flows"].as_array().unwrap().len(), 1);
        assert_eq!(v["boundaries"].as_array().unwrap().len(), 1);
        assert_eq!(v["claims"].as_array().unwrap().len(), 2);
    }

    #[test]
    fn parses_refine_happy_path() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node api : trusted abstract
            refine api into {
                node inner : trusted
                flow f1 : inner -> inner
                binds api = inner
            }"#);
        let r = &v["refines"][0];
        assert_eq!(r["target"], "api");
        assert_eq!(r["bind_to"], "inner");
        assert_eq!(r["nodes"][0]["id"], "inner");
        assert_eq!(r["flows"][0]["id"], "f1");
    }

    #[test]
    fn error_refine_zero_binds() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node api : trusted abstract
            refine api into {
                node inner : trusted
            }"#);
        assert_eq!(e["message"], "refine block needs exactly one binds clause");
    }

    #[test]
    fn error_refine_two_binds() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node api : trusted abstract
            refine api into {
                node inner : trusted
                binds api = inner
                binds api = inner
            }"#);
        assert_eq!(e["message"], "refine block needs exactly one binds clause");
    }

    #[test]
    fn error_refine_binds_lhs_mismatch() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node api : trusted abstract
            refine api into {
                node inner : trusted
                binds wrong = inner
            }"#);
        assert!(e["message"]
            .as_str()
            .unwrap()
            .contains("must equal refine target"));
    }

    #[test]
    fn error_refine_before_module() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("refine api into { binds api = inner }");
        assert_eq!(e["message"], "statement before module declaration");
    }

    #[test]
    fn parses_store_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            store db : trusted {
                clearance Pii;
                attr region=us;
                residence us_east;
                capacity 100 req/s replicas 1..4;
                engine postgres;
                immutable;
                append_only;
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["id"], "db");
        assert_eq!(s["trust"], "trusted");
        assert_eq!(s["clearance"], "Pii");
        assert_eq!(s["attrs"][0], "region=us");
        assert_eq!(s["residence"], "us_east");
        assert_eq!(s["capacity"]["replicas_max"], 4);
        assert_eq!(s["engine"], "postgres");
        assert_eq!(s["immutable"], true);
        assert_eq!(s["append_only"], true);
    }

    #[test]
    fn parses_bare_store() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nstore db : trusted");
        let s = &v["stores"][0];
        assert_eq!(s["engine"], serde_json::Value::Null);
        assert_eq!(s["immutable"], false);
        assert_eq!(s["append_only"], false);
    }

    #[test]
    fn error_unknown_store_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nstore db : trusted { bogus x; }");
        assert_eq!(e["message"], "unknown store property");
    }

    #[test]
    fn parses_cache_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            cache c of db {
                keyed_by user_id;
                staleness 30 s;
                hit 90 %;
                policy lru;
                invalidate_on f1;
                invalidate_on f2;
            }"#);
        let c = &v["caches"][0];
        assert_eq!(c["id"], "c");
        assert_eq!(c["of"], "db");
        assert_eq!(c["keyed_by"], "user_id");
        assert_eq!(c["staleness"]["value"], 30.0);
        assert_eq!(c["staleness"]["unit"], "s");
        assert_eq!(c["hit"], 90.0);
        assert_eq!(c["policy"], "lru");
        assert_eq!(c["invalidate_on"][0], "f1");
        assert_eq!(c["invalidate_on"][1], "f2");
    }

    #[test]
    fn parses_cache_ttl() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\ncache c of db { ttl 60 s; }");
        assert_eq!(v["caches"][0]["ttl"]["value"], 60.0);
    }

    #[test]
    fn error_unknown_cache_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\ncache c of db { bogus x; }");
        assert_eq!(e["message"], "unknown cache property");
    }

    #[test]
    fn parses_queue_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            queue q {
                delivery at_least_once;
                ordering fifo;
                attr region=us;
                clearance Internal;
            }"#);
        let q = &v["queues"][0];
        assert_eq!(q["id"], "q");
        assert_eq!(q["delivery"], "at_least_once");
        assert_eq!(q["ordering"], "fifo");
        assert_eq!(q["attrs"][0], "region=us");
        assert_eq!(q["clearance"], "Internal");
    }

    #[test]
    fn error_unknown_queue_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nqueue q { bogus x; }");
        assert_eq!(e["message"], "unknown queue property");
    }

    #[test]
    fn parses_cdn_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            cdn c of origin {
                provider fastly : authenticated;
                staleness 5 min;
                hit 95 %;
                tls_terminates_at_provider;
            }"#);
        let c = &v["cdns"][0];
        assert_eq!(c["id"], "c");
        assert_eq!(c["of"], "origin");
        assert_eq!(c["provider"], "fastly");
        assert_eq!(c["provider_trust"], "authenticated");
        assert_eq!(c["staleness"]["value"], 5.0);
        assert_eq!(c["staleness_unlimited"], false);
        assert_eq!(c["hit"], 95.0);
        assert_eq!(c["tls_terminates_at_provider"], true);
    }

    #[test]
    fn parses_cdn_unlimited_staleness() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            cdn c of origin { provider fastly : authenticated; staleness unlimited; }"#);
        assert_eq!(v["cdns"][0]["staleness_unlimited"], true);
        assert_eq!(v["cdns"][0]["staleness"], serde_json::Value::Null);
    }

    #[test]
    fn error_unknown_cdn_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\ncdn c of origin { bogus x; }");
        assert_eq!(e["message"], "unknown cdn property");
    }

    #[test]
    fn parses_balancer_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nbalancer b { policy round_robin; sticky; }");
        let b = &v["balancers"][0];
        assert_eq!(b["id"], "b");
        assert_eq!(b["policy"], "round_robin");
        assert_eq!(b["sticky"], true);
    }

    #[test]
    fn parses_bare_balancer() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nbalancer b");
        assert_eq!(v["balancers"][0]["policy"], serde_json::Value::Null);
        assert_eq!(v["balancers"][0]["sticky"], false);
    }

    #[test]
    fn error_unknown_balancer_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nbalancer b { bogus x; }");
        assert_eq!(e["message"], "unknown balancer property");
    }

    #[test]
    fn fuzz_safe_random_bytes_never_panic() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let samples = [
            "\0\0\0",
            "module",
            "{{{{",
            "module m node",
            "assert c bound age x <= ",
            "\"unterminated",
            "module m\n// comment only\n",
        ];
        for s in samples {
            let out = parse_source_impl(s);
            assert!(serde_json::from_str::<Value>(&out).is_ok());
        }
    }
}
