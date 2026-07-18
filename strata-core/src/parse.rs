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
        if matches!(
            c,
            ':' | '{' | '}' | ';' | '(' | ')' | '%' | '/' | '=' | '<' | '>' | '.' | ','
        ) {
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
    policies: Vec<serde_json::Value>,
    operations: Vec<serde_json::Value>,
    scenarios: Vec<serde_json::Value>,
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
        let mut errors_total = false;
        let mut panics_contained_by: Option<String> = None;
        let mut observe: Option<serde_json::Value> = None;
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
                } else if self.at_keyword("skew") {
                    // skew := "skew" "zipf" NUMBER; desugars straight to a
                    // node attr "skew=<alpha>" (docs/strata/kernel.md
                    // #capacity-semantics) -- no dedicated kernel field.
                    self.advance();
                    self.expect_keyword("zipf")?;
                    let alpha = self.expect_number("skew zipf exponent")?;
                    attrs.push(format!("skew={}", alpha));
                } else if self.at_keyword("errors_total") {
                    // T-0070: bare marker; the elaborator turns this into a
                    // node attr "errors_total" and requires an observe block.
                    self.advance();
                    errors_total = true;
                } else if self.at_keyword("panics_contained_by") {
                    // T-0070: names the crash-boundary supervisor node id;
                    // reference validity is an elaboration-time check.
                    self.advance();
                    panics_contained_by = Some(self.expect_ident("panics supervisor id")?);
                } else if self.at_keyword("observe") {
                    // T-0070: observe { log IDENT (, IDENT)* ; to IDENT }
                    self.advance();
                    self.expect_symbol('{')?;
                    let mut log: Vec<String> = Vec::new();
                    let mut to: Option<String> = None;
                    loop {
                        if self.at_symbol('}') {
                            break;
                        }
                        if self.at_keyword("log") {
                            self.advance();
                            log.push(self.expect_ident("observe log class")?);
                            while self.at_symbol(',') {
                                self.advance();
                                log.push(self.expect_ident("observe log class")?);
                            }
                        } else if self.at_keyword("to") {
                            self.advance();
                            to = Some(self.expect_ident("observe target id")?);
                        } else {
                            return self.err("unknown observe property");
                        }
                        if self.at_symbol(';') {
                            self.advance();
                        } else {
                            break;
                        }
                    }
                    self.expect_symbol('}')?;
                    let to = match to {
                        Some(t) => t,
                        None => return self.err("observe block needs a to IDENT"),
                    };
                    observe = Some(json!({"log": log, "to": to}));
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
            "errors_total": errors_total,
            "panics_contained_by": panics_contained_by,
            "observe": observe,
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
                } else if self.at_keyword("fanout") {
                    // fanout := "fanout" NUMBER; desugars to a flow attr
                    // "fanout=<float>" (docs/strata/kernel.md#capacity-
                    // semantics) -- multiplies demand propagated along
                    // this flow. No dedicated kernel field (charter law 1).
                    self.advance();
                    let n = self.expect_number("fanout multiplier")?;
                    attrs.push(format!("fanout={}", n));
                } else if self.at_keyword("growth") {
                    // growth := "growth" NUMBER "%"; desugars to a flow
                    // attr "growth=<pct_per_month>" -- no new claim form
                    // (charter law 1); UTILIZATION bound claims read it for
                    // saturation-horizon diagnostics.
                    self.advance();
                    let n = self.expect_number("growth percent")?;
                    self.expect_symbol('%')?;
                    attrs.push(format!("growth={}", n));
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
        let mut phases: Option<serde_json::Value> = None;
        if self.at_symbol('{') {
            phases = Some(self.parse_phase_block()?);
        }
        ast.boundaries.push(json!({
            "id": id,
            "kind": kind,
            "flow_id": flow_id,
            "from_level": from_level,
            "to_level": to_level,
            "predicate": predicate,
            "phases": phases,
        }));
        Ok(())
    }

    /// FRAMETARGET := IDENT ['(' IDENT ')'], joined as "Balance(from)" when
    /// the parenthesized entity-selector is present (docs/strata/boundary.md
    /// operation example); the paren form is purely a display convention --
    /// the elaborator treats the whole string as one frame target id.
    fn parse_frame_target(&mut self) -> Result<String, ParseError> {
        let base = self.expect_ident("frame target")?;
        if self.at_symbol('(') {
            self.advance();
            let arg = self.expect_ident("frame target argument")?;
            self.expect_symbol(')')?;
            Ok(format!("{}({})", base, arg))
        } else {
            Ok(base)
        }
    }

    /// frame_prop := "frame" "{" FRAMETARGET (',' FRAMETARGET)* "}"
    ///             | "frame" "{" "}"
    fn parse_frame_prop(&mut self) -> Result<Vec<String>, ParseError> {
        self.expect_keyword("frame")?;
        self.expect_symbol('{')?;
        let mut targets: Vec<String> = Vec::new();
        if !self.at_symbol('}') {
            targets.push(self.parse_frame_target()?);
            while self.at_symbol(',') {
                self.advance();
                targets.push(self.parse_frame_target()?);
            }
        }
        self.expect_symbol('}')?;
        Ok(targets)
    }

    /// phase_block := "{" (admit_phase | parse_phase | judge_phase | effect_phase
    ///                    | record_phase | refuse_phase)* "}"
    ///
    /// Each of the six phase keywords may appear at most once
    /// (docs/strata/boundary.md#the-six-phases, T-0069 v0); a repeated
    /// phase keyword is a parse error rather than last-write-wins, since
    /// silently dropping one phase's declaration would be a security-
    /// relevant default (charter law 2).
    fn parse_phase_block(&mut self) -> Result<serde_json::Value, ParseError> {
        self.expect_symbol('{')?;
        let mut admit: Option<serde_json::Value> = None;
        let mut parse_phase: Option<serde_json::Value> = None;
        let mut judge = false;
        let mut effect: Option<serde_json::Value> = None;
        let mut record: Option<serde_json::Value> = None;
        let mut refuse: Option<serde_json::Value> = None;
        loop {
            if self.at_symbol('}') {
                break;
            }
            let tok = self.cur().clone();
            if self.at_keyword("admit") {
                if admit.is_some() {
                    return Err(ParseError {
                        line: tok.line,
                        col: tok.col,
                        message: "duplicate admit phase".to_string(),
                    });
                }
                self.advance();
                self.expect_symbol('{')?;
                let mut rate_limit: Option<serde_json::Value> = None;
                let mut max_size: Option<serde_json::Value> = None;
                loop {
                    if self.at_symbol('}') {
                        break;
                    }
                    if self.at_keyword("rate_limit") {
                        self.advance();
                        rate_limit = Some(self.parse_quantity("rate_limit")?);
                    } else if self.at_keyword("max_size") {
                        self.advance();
                        max_size = Some(self.parse_quantity("max_size")?);
                    } else {
                        return self.err("unknown admit property");
                    }
                    if self.at_symbol(';') {
                        self.advance();
                    } else {
                        break;
                    }
                }
                self.expect_symbol('}')?;
                admit = Some(json!({"rate_limit": rate_limit, "max_size": max_size}));
            } else if self.at_keyword("parse") {
                if parse_phase.is_some() {
                    return Err(ParseError {
                        line: tok.line,
                        col: tok.col,
                        message: "duplicate parse phase".to_string(),
                    });
                }
                self.advance();
                self.expect_symbol('{')?;
                let mut time: Option<String> = None;
                let mut frame: Vec<String> = Vec::new();
                loop {
                    if self.at_symbol('}') {
                        break;
                    }
                    if self.at_keyword("time") {
                        self.advance();
                        time = Some(self.expect_ident("parse time bound")?);
                    } else if self.at_keyword("frame") {
                        frame = self.parse_frame_prop()?;
                    } else {
                        return self.err("unknown parse property");
                    }
                    if self.at_symbol(';') {
                        self.advance();
                    } else {
                        break;
                    }
                }
                self.expect_symbol('}')?;
                parse_phase = Some(json!({"time": time, "frame": frame}));
            } else if self.at_keyword("judge") {
                if judge {
                    return Err(ParseError {
                        line: tok.line,
                        col: tok.col,
                        message: "duplicate judge phase".to_string(),
                    });
                }
                self.advance();
                self.expect_symbol('{')?;
                self.expect_symbol('}')?;
                judge = true;
            } else if self.at_keyword("effect") {
                if effect.is_some() {
                    return Err(ParseError {
                        line: tok.line,
                        col: tok.col,
                        message: "duplicate effect phase".to_string(),
                    });
                }
                self.advance();
                self.expect_symbol('{')?;
                let frame = self.parse_frame_prop()?;
                if self.at_symbol(';') {
                    self.advance();
                }
                self.expect_symbol('}')?;
                effect = Some(json!({"frame": frame}));
            } else if self.at_keyword("record") {
                if record.is_some() {
                    return Err(ParseError {
                        line: tok.line,
                        col: tok.col,
                        message: "duplicate record phase".to_string(),
                    });
                }
                self.advance();
                self.expect_symbol('{')?;
                self.expect_keyword("audit")?;
                self.expect_keyword("to")?;
                let audit_to = self.expect_ident("audit target id")?;
                if self.at_symbol(';') {
                    self.advance();
                }
                self.expect_symbol('}')?;
                record = Some(json!({"audit_to": audit_to}));
            } else if self.at_keyword("refuse") {
                if refuse.is_some() {
                    return Err(ParseError {
                        line: tok.line,
                        col: tok.col,
                        message: "duplicate refuse phase".to_string(),
                    });
                }
                self.advance();
                self.expect_symbol('{')?;
                self.expect_keyword("respond")?;
                let respond = self.expect_ident("response label")?;
                if self.at_symbol(';') {
                    self.advance();
                }
                let mut frame: Vec<String> = Vec::new();
                if self.at_keyword("frame") {
                    frame = self.parse_frame_prop()?;
                    if self.at_symbol(';') {
                        self.advance();
                    }
                }
                self.expect_symbol('}')?;
                refuse = Some(json!({"respond": respond, "frame": frame}));
            } else {
                return self.err("unknown phase keyword");
            }
        }
        self.expect_symbol('}')?;
        Ok(json!({
            "admit": admit,
            "parse": parse_phase,
            "judge": judge,
            "effect": effect,
            "record": record,
            "refuse": refuse,
        }))
    }

    /// operation := "operation" ID "on" IDENT "{" operation_prop* "}"
    /// operation_prop := "modifies" "{" FRAMETARGET (',' FRAMETARGET)* "}"? "on" IDENT
    ///                  | "atomic" "via" IDENT
    ///
    /// WHY "on" IDENT rather than a fixed Ok/Err pair: the outcome name is
    /// validated against the kernel `Outcome` enum at elaboration time (case-
    /// insensitively -- docs/strata/boundary.md writes `on Ok`/`on Err`, the
    /// kernel's `Outcome` values are lowercase), not the parser, matching
    /// how boundary `kind` and claim `kind` are grammar-open, elaborator-
    /// closed elsewhere in this file.
    fn parse_operation(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'operation'
        let id = self.expect_ident("operation id")?;
        self.expect_keyword("on")?;
        let on = self.expect_ident("operation store id")?;
        self.expect_symbol('{')?;
        let mut modifies_ok: Vec<String> = Vec::new();
        let mut modifies_err: Vec<String> = Vec::new();
        let mut atomic_via: Option<String> = None;
        loop {
            if self.at_symbol('}') {
                break;
            }
            if self.at_keyword("modifies") {
                self.advance();
                self.expect_symbol('{')?;
                let mut targets: Vec<String> = Vec::new();
                if !self.at_symbol('}') {
                    targets.push(self.parse_frame_target()?);
                    while self.at_symbol(',') {
                        self.advance();
                        targets.push(self.parse_frame_target()?);
                    }
                }
                self.expect_symbol('}')?;
                self.expect_keyword("on")?;
                let outcome = self.expect_ident("modifies outcome (Ok/Err)")?;
                match outcome.to_lowercase().as_str() {
                    "ok" => modifies_ok = targets,
                    "err" => modifies_err = targets,
                    _ => return self.err("modifies outcome must be Ok or Err"),
                }
            } else if self.at_keyword("atomic") {
                self.advance();
                self.expect_keyword("via")?;
                atomic_via = Some(self.expect_ident("atomic coordinator id")?);
            } else {
                return self.err("unknown operation property");
            }
            if self.at_symbol(';') {
                self.advance();
            } else {
                break;
            }
        }
        self.expect_symbol('}')?;
        let atomic_via = match atomic_via {
            Some(a) => a,
            None => return self.err("operation needs an atomic via clause"),
        };
        ast.operations.push(json!({
            "id": id,
            "on": on,
            "modifies_ok": modifies_ok,
            "modifies_err": modifies_err,
            "atomic_via": atomic_via,
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
    ///             | "rpo" QUANTITY
    ///
    /// WHY: store is std.infra's node-with-extras; it reuses the node_prop
    /// surface (clearance/attr/residence/capacity) verbatim plus engine, the
    /// immutable/append_only markers the elaborator needs for the
    /// cdn-unlimited-staleness pairing, and `rpo` -- a store's declared
    /// durability/replication lag, the same age-collapse family as cache ttl
    /// (docs/strata/surface.md#std-infra, docs/strata/kernel.md#age-
    /// propagation-semantics). The grammar accepts any unit here; dimension
    /// validation (must be a time unit) is the elaborator's job, matching
    /// how ttl/staleness stay units-only at parse time too.
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
        let mut rpo: Option<serde_json::Value> = None;
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
                } else if self.at_keyword("rpo") {
                    self.advance();
                    rpo = Some(self.parse_quantity("rpo")?);
                } else if self.at_keyword("skew") {
                    self.advance();
                    self.expect_keyword("zipf")?;
                    let alpha = self.expect_number("skew zipf exponent")?;
                    attrs.push(format!("skew={}", alpha));
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
            "rpo": rpo,
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

    fn expect_ge(&mut self) -> Result<(), ParseError> {
        // '>=' is two raw chars, both lexed as individual Symbols; SCOPESPEC
        // ("trust >= IDENT", "label >= IDENT") is the only user (parse.md
        // #policy T-0067), same pairing trick as expect_le for '<='.
        match self.cur().kind {
            TokKind::Symbol('>') => {
                self.advance();
                self.expect_symbol('=')
            }
            _ => self.err("expected >="),
        }
    }

    /// DOTTEDIDENT := IDENT ('.' IDENT)*, collapsed into one dotted string so
    /// call/import targets like `importlib.import_module` round-trip as a
    /// single atom (docs/strata/policy.md#the-five-forms, T-0067).
    fn parse_dotted_ident(&mut self, what: &str) -> Result<String, ParseError> {
        let mut s = self.expect_ident(what)?;
        while self.at_symbol('.') {
            self.advance();
            let part = self.expect_ident("dotted identifier component")?;
            s.push('.');
            s.push_str(&part);
        }
        Ok(s)
    }

    /// IDENTLIST := DOTTEDIDENT (',' DOTTEDIDENT)*
    fn parse_dotted_ident_list(&mut self, what: &str) -> Result<Vec<String>, ParseError> {
        let mut list = vec![self.parse_dotted_ident(what)?];
        while self.at_symbol(',') {
            self.advance();
            list.push(self.parse_dotted_ident(what)?);
        }
        Ok(list)
    }

    /// SCOPESPEC := "component" IDENT | "trust" ">=" IDENT | "label" ">=" IDENT
    fn parse_scope_spec(&mut self) -> Result<serde_json::Value, ParseError> {
        if self.at_keyword("component") {
            self.advance();
            let name = self.expect_ident("component name")?;
            Ok(json!({"kind": "component", "value": name}))
        } else if self.at_keyword("trust") {
            self.advance();
            self.expect_ge()?;
            let level = self.expect_ident("trust level")?;
            Ok(json!({"kind": "trust", "value": level}))
        } else if self.at_keyword("label") {
            self.advance();
            self.expect_ge()?;
            let level = self.expect_ident("label level")?;
            Ok(json!({"kind": "label", "value": level}))
        } else {
            self.err("expected component, trust >=, or label >= scope")
        }
    }

    /// policy_rule := "forbid" ("call" | "import") IDENTLIST
    ///              | "confine" "use" DOTTEDIDENT "to" STRING
    ///              | "at" "call" DOTTEDIDENT "require" "arg" IDENT
    ///              | "mediate" DOTTEDIDENT "via" STRING
    ///              | "enables" IDENT
    ///              | "rationale" STRING
    fn parse_policy_rule(&mut self) -> Result<serde_json::Value, ParseError> {
        if self.at_keyword("forbid") {
            self.advance();
            if self.at_keyword("call") {
                self.advance();
                let idents = self.parse_dotted_ident_list("forbidden call target")?;
                Ok(json!({"kind": "forbid_call", "idents": idents}))
            } else if self.at_keyword("import") {
                self.advance();
                let idents = self.parse_dotted_ident_list("forbidden import target")?;
                Ok(json!({"kind": "forbid_import", "idents": idents}))
            } else {
                self.err("expected call or import after forbid")
            }
        } else if self.at_keyword("confine") {
            self.advance();
            self.expect_keyword("use")?;
            let ident = self.parse_dotted_ident("confined symbol")?;
            self.expect_keyword("to")?;
            let home = self.expect_string("confinement home path")?;
            Ok(json!({"kind": "confine_use", "ident": ident, "home": home}))
        } else if self.at_keyword("at") {
            self.advance();
            self.expect_keyword("call")?;
            let ident = self.parse_dotted_ident("call site target")?;
            self.expect_keyword("require")?;
            self.expect_keyword("arg")?;
            let arg = self.expect_ident("required argument name")?;
            Ok(json!({"kind": "at_call_require_arg", "ident": ident, "arg": arg}))
        } else if self.at_keyword("mediate") {
            self.advance();
            let ident = self.parse_dotted_ident("mediated capability")?;
            self.expect_keyword("via")?;
            let mediator = self.expect_string("mediator reference")?;
            Ok(json!({"kind": "mediate", "ident": ident, "mediator": mediator}))
        } else if self.at_keyword("enables") {
            self.advance();
            let atom = self.expect_ident("enabled atom")?;
            Ok(json!({"kind": "enables", "atom": atom}))
        } else if self.at_keyword("rationale") {
            self.advance();
            let text = self.expect_string("rationale text")?;
            Ok(json!({"kind": "rationale", "text": text}))
        } else {
            self.err("unknown policy rule")
        }
    }

    /// policy := "policy" IDENT "on" SCOPESPEC "{" policy_rule (";" policy_rule)* ";"? "}"
    fn parse_policy(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'policy'
        // dotted so pack ids like `std.policy.analyzable` are legal policy
        // ids (docs/strata/policy.md#packs, T-0068)
        let id = self.parse_dotted_ident("policy id")?;
        self.expect_keyword("on")?;
        let scope = self.parse_scope_spec()?;
        self.expect_symbol('{')?;
        let mut rules: Vec<serde_json::Value> = Vec::new();
        loop {
            if self.at_symbol('}') {
                break;
            }
            rules.push(self.parse_policy_rule()?);
            if self.at_symbol(';') {
                self.advance();
            } else {
                break;
            }
        }
        self.expect_symbol('}')?;
        ast.policies.push(json!({
            "id": id,
            "scope": scope,
            "rules": rules,
        }));
        Ok(())
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

    fn expect_coloneq(&mut self) -> Result<(), ParseError> {
        // ':=' is two raw Symbol chars, same pairing trick as expect_le;
        // scenario's `trust IDENT := IDENT` reassignment is the only user
        // (docs/strata/kernel.md#scenario, T-0073).
        match self.cur().kind {
            TokKind::Symbol(':') => {
                self.advance();
                self.expect_symbol('=')
            }
            _ => self.err("expected :="),
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

    /// scenario := "scenario" IDENT "{" rewrite* claim* "}"
    /// rewrite := "remove" IDENT
    ///          | "scale" IDENT "by" NUMBER
    ///          | "trust" IDENT ":=" IDENT
    /// claim reuses the assert/assume productions verbatim (parse_claim) so
    /// a scenario's nested claims are re-checked under the rewritten fact
    /// base with the exact same claim vocabulary (docs/strata/kernel.md
    /// #scenario, T-0073).
    fn parse_scenario(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'scenario'
        let id = self.expect_ident("scenario id")?;
        self.expect_symbol('{')?;
        let mut rewrites: Vec<serde_json::Value> = Vec::new();
        let mut claims: Vec<serde_json::Value> = Vec::new();
        loop {
            if self.at_symbol('}') {
                break;
            }
            if self.at_keyword("remove") {
                self.advance();
                let node_id = self.expect_ident("remove target node id")?;
                rewrites.push(json!({"kind": "remove", "node_id": node_id}));
            } else if self.at_keyword("scale") {
                self.advance();
                let flow_id = self.expect_ident("scale target flow id")?;
                self.expect_keyword("by")?;
                let factor = self.expect_number("scale factor")?;
                rewrites.push(json!({"kind": "scale", "flow_id": flow_id, "factor": factor}));
            } else if self.at_keyword("trust") {
                self.advance();
                let node_id = self.expect_ident("trust target node id")?;
                self.expect_coloneq()?;
                let level = self.expect_ident("trust level")?;
                rewrites.push(json!({"kind": "trust", "node_id": node_id, "level": level}));
            } else if self.at_keyword("assert") {
                let mut inner = ModuleAst::default();
                self.parse_claim(&mut inner, "assert")?;
                claims.push(inner.claims.remove(0));
            } else if self.at_keyword("assume") {
                let mut inner = ModuleAst::default();
                self.parse_claim(&mut inner, "assume")?;
                claims.push(inner.claims.remove(0));
            } else {
                return self.err(
                    "expected remove, scale, trust, assert, or assume inside scenario block",
                );
            }
            if self.at_symbol(';') {
                self.advance();
            }
        }
        self.expect_symbol('}')?;
        ast.scenarios.push(json!({
            "id": id,
            "rewrites": rewrites,
            "claims": claims,
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
                | "cache" | "queue" | "cdn" | "balancer" | "policy" | "operation"
                | "scenario" => {
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
                        "policy" => self.parse_policy(&mut ast)?,
                        "operation" => self.parse_operation(&mut ast)?,
                        "scenario" => self.parse_scenario(&mut ast)?,
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
    fn parses_store_rpo() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            store db : trusted {
                rpo 5 min;
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["rpo"]["value"], 5.0);
        assert_eq!(s["rpo"]["unit"], "min");
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
    fn parses_node_skew() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nnode n : trusted { skew zipf 1.2; }");
        assert_eq!(v["nodes"][0]["attrs"][0], "skew=1.2");
    }

    #[test]
    fn parses_store_skew() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nstore db : trusted { skew zipf 0.9; }");
        assert_eq!(v["stores"][0]["attrs"][0], "skew=0.9");
    }

    #[test]
    fn parses_flow_fanout() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nflow f1 : a -> b { fanout 2.5; }");
        assert_eq!(v["flows"][0]["attrs"][0], "fanout=2.5");
    }

    #[test]
    fn parses_flow_growth() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nflow f1 : a -> b { growth 5 %; }");
        assert_eq!(v["flows"][0]["attrs"][0], "growth=5");
    }

    #[test]
    fn error_skew_requires_zipf_keyword() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nnode n : trusted { skew 1.2; }");
        assert_eq!(e["message"], "expected keyword \"zipf\"");
    }

    #[test]
    fn error_growth_requires_percent() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nflow f1 : a -> b { growth 5; }");
        assert_eq!(e["message"], "expected \'%\'");
    }

    #[test]
    fn error_unknown_balancer_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nbalancer b { bogus x; }");
        assert_eq!(e["message"], "unknown balancer property");
    }

    #[test]
    fn parses_policy_forbid_call_and_import() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy NoDynamicCode on trust >= trusted {
                forbid call eval, exec, importlib.import_module;
                forbid import ctypes
            }"#);
        let p = &v["policies"][0];
        assert_eq!(p["id"], "NoDynamicCode");
        assert_eq!(p["scope"]["kind"], "trust");
        assert_eq!(p["scope"]["value"], "trusted");
        assert_eq!(p["rules"][0]["kind"], "forbid_call");
        assert_eq!(p["rules"][0]["idents"][2], "importlib.import_module");
        assert_eq!(p["rules"][1]["kind"], "forbid_import");
        assert_eq!(p["rules"][1]["idents"][0], "ctypes");
    }

    #[test]
    fn parses_policy_confine_use() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy DbConfine on component Api {
                confine use psycopg to "src/api/db.py"
            }"#);
        let r = &v["policies"][0]["rules"][0];
        assert_eq!(r["kind"], "confine_use");
        assert_eq!(r["ident"], "psycopg");
        assert_eq!(r["home"], "src/api/db.py");
    }

    #[test]
    fn parses_policy_at_call_require_arg() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy TimeoutRequired on component Api {
                at call subprocess.run require arg timeout
            }"#);
        let r = &v["policies"][0]["rules"][0];
        assert_eq!(r["kind"], "at_call_require_arg");
        assert_eq!(r["ident"], "subprocess.run");
        assert_eq!(r["arg"], "timeout");
    }

    #[test]
    fn parses_policy_mediate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy DbChokepoint on component Api {
                mediate db.write via "db.py::TenantScopedSession"
            }"#);
        let r = &v["policies"][0]["rules"][0];
        assert_eq!(r["kind"], "mediate");
        assert_eq!(r["ident"], "db.write");
        assert_eq!(r["mediator"], "db.py::TenantScopedSession");
    }

    #[test]
    fn parses_policy_enables_and_rationale() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy NoDynamicCode on trust >= trusted {
                forbid call eval;
                enables extraction_soundness;
                rationale "static closure requires no dynamic dispatch"
            }"#);
        let rules = v["policies"][0]["rules"].as_array().unwrap();
        assert_eq!(rules[1]["kind"], "enables");
        assert_eq!(rules[1]["atom"], "extraction_soundness");
        assert_eq!(rules[2]["kind"], "rationale");
        assert_eq!(
            rules[2]["text"],
            "static closure requires no dynamic dispatch"
        );
    }

    #[test]
    fn parses_policy_label_scope() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy NoPiiInLogs on label >= Pii {
                forbid call logging.info
            }"#);
        assert_eq!(v["policies"][0]["scope"]["kind"], "label");
        assert_eq!(v["policies"][0]["scope"]["value"], "Pii");
    }

    #[test]
    fn parses_policy_bare_no_rules() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\npolicy Empty on component Api {}");
        assert_eq!(v["policies"][0]["rules"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_policy_unknown_scope_keyword() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\npolicy P on bogus X { forbid call eval }");
        assert_eq!(e["message"], "expected component, trust >=, or label >= scope");
    }

    #[test]
    fn error_policy_trust_scope_missing_ge() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\npolicy P on trust trusted { forbid call eval }");
        assert_eq!(e["message"], "expected >=");
    }

    #[test]
    fn error_policy_unknown_rule() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\npolicy P on component Api { bogus x }");
        assert_eq!(e["message"], "unknown policy rule");
    }

    #[test]
    fn error_policy_forbid_missing_call_or_import() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\npolicy P on component Api { forbid eval }");
        assert_eq!(e["message"], "expected call or import after forbid");
    }

    #[test]
    fn dotted_ident_list_round_trips_multiple_dots() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy P on component Api {
                forbid call a.b.c, d
            }"#);
        let idents = v["policies"][0]["rules"][0]["idents"].as_array().unwrap();
        assert_eq!(idents[0], "a.b.c");
        assert_eq!(idents[1], "d");
    }

    #[test]
    fn parses_boundary_with_phases() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node gw : authenticated
            node audit_log : trusted { attr append_only; }
            node view : trusted
            flow f1 : gw -> gw
            boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified" {
                admit { rate_limit 20 req/min; max_size 64 KiB; }
                parse { time linear; frame {} }
                judge {}
                effect { frame { gw } }
                record { audit to audit_log }
                refuse { respond Public; frame { audit_log } }
            }"#);
        let phases = &v["boundaries"][0]["phases"];
        assert_eq!(phases["admit"]["max_size"]["value"], 64.0);
        assert_eq!(phases["parse"]["time"], "linear");
        assert_eq!(phases["judge"], true);
        assert_eq!(phases["effect"]["frame"][0], "gw");
        assert_eq!(phases["record"]["audit_to"], "audit_log");
        assert_eq!(phases["refuse"]["respond"], "Public");
        assert_eq!(phases["refuse"]["frame"][0], "audit_log");
    }

    #[test]
    fn parses_boundary_without_phases_is_still_legal() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            boundary b1 endorse f1 : foreign -> authenticated"#);
        assert!(v["boundaries"][0]["phases"].is_null());
    }

    #[test]
    fn parses_operation_with_ok_and_err_frames() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            operation Transfer on LedgerDb {
                modifies { Balance(from), Balance(to) } on Ok;
                modifies {} on Err;
                atomic via LedgerDb
            }"#);
        let op = &v["operations"][0];
        assert_eq!(op["id"], "Transfer");
        assert_eq!(op["on"], "LedgerDb");
        assert_eq!(op["modifies_ok"][0], "Balance(from)");
        assert_eq!(op["modifies_ok"][1], "Balance(to)");
        assert_eq!(op["modifies_err"].as_array().unwrap().len(), 0);
        assert_eq!(op["atomic_via"], "LedgerDb");
    }

    #[test]
    fn parses_node_with_errors_total_panics_and_observe() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node api : trusted {
                errors_total;
                panics_contained_by supervisor;
                observe { log error_paths, boundary_crossings; to obs_sink }
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["errors_total"], true);
        assert_eq!(n["panics_contained_by"], "supervisor");
        assert_eq!(n["observe"]["log"][0], "error_paths");
        assert_eq!(n["observe"]["log"][1], "boundary_crossings");
        assert_eq!(n["observe"]["to"], "obs_sink");
    }

    #[test]
    fn parses_bare_node_defaults_observability_fields() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\n            node api : trusted");
        let n = &v["nodes"][0];
        assert_eq!(n["errors_total"], false);
        assert!(n["panics_contained_by"].is_null());
        assert!(n["observe"].is_null());
    }

    #[test]
    fn duplicate_phase_keyword_is_a_parse_error() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            boundary b1 endorse f1 : foreign -> authenticated {
                judge {}
                judge {}
            }"#);
        assert!(e["message"].as_str().unwrap().contains("duplicate judge"));
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

    #[test]
    fn parses_scenario_with_all_rewrite_kinds_and_nested_claims() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            scenario node_loss {
                remove n1;
                scale f1 by 3.0;
                trust n2 := foreign;
                assert c1 noflow n1 -> n2;
                assume c2 bound rate f1 <= 10 req/s owner alice review "2026-01-01";
            }"#);
        let s = &v["scenarios"][0];
        assert_eq!(s["id"], "node_loss");
        assert_eq!(s["rewrites"][0]["kind"], "remove");
        assert_eq!(s["rewrites"][0]["node_id"], "n1");
        assert_eq!(s["rewrites"][1]["kind"], "scale");
        assert_eq!(s["rewrites"][1]["flow_id"], "f1");
        assert_eq!(s["rewrites"][1]["factor"], 3.0);
        assert_eq!(s["rewrites"][2]["kind"], "trust");
        assert_eq!(s["rewrites"][2]["node_id"], "n2");
        assert_eq!(s["rewrites"][2]["level"], "foreign");
        assert_eq!(s["claims"][0]["id"], "c1");
        assert_eq!(s["claims"][0]["kind"], "noflow");
        assert_eq!(s["claims"][1]["id"], "c2");
        assert_eq!(s["claims"][1]["assumed"], true);
        // scenario-local claims never leak into the module's top-level list
        assert_eq!(v["claims"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_bare_scenario_with_no_rewrites_or_claims() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nscenario s { }");
        let s = &v["scenarios"][0];
        assert_eq!(s["id"], "s");
        assert_eq!(s["rewrites"].as_array().unwrap().len(), 0);
        assert_eq!(s["claims"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_scenario_rejects_unknown_statement() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nscenario s { bogus x; }");
        assert_eq!(
            e["message"],
            "expected remove, scale, trust, assert, or assume inside scenario block"
        );
    }

    #[test]
    fn error_scenario_trust_requires_coloneq() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nscenario s { trust n1 = foreign; }");
        assert_eq!(e["message"], "expected :=");
    }
}
