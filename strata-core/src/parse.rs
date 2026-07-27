//! Lexer + recursive-descent parser for the strata surface grammar v0
//! (docs/strata/surface.md#parser). Deterministic and fuzz-safe: every
//! malformed input yields an `err` JSON object with line/col instead of
//! panicking (charter D3 as amended: the parser is compute-heavy and
//! lives here; Python only calls `parse_source` and validates the JSON
//! into pydantic AST models).
// frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
// strata-core/src/parse.rs's exclusivity-vocabulary hit is source-level \
// design-rationale/scope-cut prose (a docstring or comment describing \
// already-implemented internal behavior, verifiable by reading the code it \
// annotates) rather than a separate cross-module contract needing its own tracked \
// invariant; disposed as a calibration batch, not claim-by-claim"

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
    secrets: Vec<serde_json::Value>,
    // T-0700: `resource ID { arbitrated_by NODE | lock "NAME" }` -- named
    // shared resources with an optional single arbiter/lease, joined
    // against `access` attrs (`parse_access_attr`) by the Python
    // contention-proof obligation (`src/frob/strata/_access.py`). Unlike
    // `owns`/`acl`/`bin_path`, a resource has no accessor of its own (it
    // is pure arbiter metadata, not a node), so it gets its own top-level
    // `Module.resources` field rather than desugaring into an attr.
    resources: Vec<serde_json::Value>,
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

    /// Claim ids are normally a bare IDENT, but discharge claims that must
    /// name a threat-catalog obligation (e.g. "weakness:CWE-79:web", see
    /// std.cwe/std.threat) need ':' and '-', which IDENT cannot lex. Accept
    /// a STRING-quoted claim id as an alternate surface form here (T-0138,
    /// following the T-0132 precedent for `code`/`may` atoms) -- this is
    /// the *only* place the grammar admits it; no other IDENT position is
    /// loosened.
    fn expect_ident_or_string(&mut self, what: &str) -> Result<String, ParseError> {
        match &self.cur().kind {
            TokKind::Ident(s) => {
                let s = s.clone();
                self.advance();
                Ok(s)
            }
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

    /// T-0700: `access "RESOURCE" mode MODE` -- one node/store's declared
    /// access mode against a named shared resource (docs/strata/
    /// host.md#resource-access-modes-t-0700), the grammar half of the
    /// contention-proof mandate. MODE is a closed vocabulary (`read`,
    /// `append`, `alpha`, `write`, `exclusive` -- the compatibility-matrix
    /// atoms `src/frob/strata/_access.py::AccessMode` mirrors), rejected
    /// at parse time rather than deferred to the elaborator (unlike
    /// `owns` MODE/`acl` RULE's opaque-atom precedent -- this vocabulary
    /// is closed and small enough to validate right here, same discipline
    /// `parse_operation`'s Ok/Err outcome check uses). Desugars STRAIGHT
    /// to an `access=<resource>:<mode>` attr (the `bin_path` T-0629
    /// direct-attr-push shape -- no new `NodeDecl`/`StoreDecl` field, kept
    /// out of `_ast.py`/`_elaborate.py`/`_infra.py` on purpose), so
    /// `_access.py::node_access_declarations` reads it back off the SAME
    /// elaborated `Node.attrs` regardless of which caller (node or store)
    /// produced it. Repeatable: a node/store may access more than one
    /// resource, or the same resource more than once (not de-duplicated
    /// here -- the obligation layer's job).
    fn parse_access_attr(&mut self, attrs: &mut Vec<String>) -> Result<(), ParseError> {
        self.advance(); // 'access'
        let resource = self.expect_string("access resource id")?;
        self.expect_keyword("mode")?;
        let mode = self.expect_ident("access mode (read|append|alpha|write|exclusive)")?;
        match mode.as_str() {
            "read" | "append" | "alpha" | "write" | "exclusive" => {}
            _ => {
                return self.err(
                    "access mode must be one of read|append|alpha|write|exclusive",
                )
            }
        }
        attrs.push(format!("access={}:{}", resource, mode));
        Ok(())
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
        // T-0702: `users NUMBER` (steady population) / `rate NUMBER UNIT`
        // (arrival rate) -- entry-node demand declarations, the source
        // side of the demand-propagation mandate (docs/strata/kernel.md
        // #demand-t-0702). Both optional and independent (a node may
        // declare either, both, or neither); a repeated clause overwrites
        // (mirrors `platform`/`residence`), not accumulates.
        let mut users: Option<f64> = None;
        let mut demand_rate: Option<serde_json::Value> = None;
        let mut errors_total = false;
        let mut panics_contained_by: Option<String> = None;
        let mut observe: Option<serde_json::Value> = None;
        let mut code: Vec<String> = Vec::new();
        let mut may: Vec<String> = Vec::new();
        let mut deploy: Option<serde_json::Value> = None;
        let mut carries: Vec<String> = Vec::new();
        let mut is_managed = false;
        let mut waives: Vec<serde_json::Value> = Vec::new();
        let mut runs_as: Option<String> = None;
        let mut is_unit = false;
        let mut owns: Vec<serde_json::Value> = Vec::new();
        let mut listens: Vec<i64> = Vec::new();
        let mut group: Vec<String> = Vec::new();
        let mut sudoers: Vec<String> = Vec::new();
        // T-0261: std.host windows fields -- Windows analogs of
        // runs_as/unit/owns (docs/strata/host.md#windows-surface-grammar).
        let mut platform: Option<String> = None;
        let mut service_account: Option<String> = None;
        let mut service_account_gmsa = false;
        let mut is_service = false;
        let mut acl: Vec<serde_json::Value> = Vec::new();
        let mut pipes: Vec<String> = Vec::new();
        let mut krb_realm: Option<String> = None;
        let mut krb_is_kdc = false;
        let mut krb_spns: Vec<String> = Vec::new();
        let mut krb_delegation: Option<String> = None;
        let mut krb_delegation_targets: Vec<String> = Vec::new();
        let mut krb_trusts: Vec<serde_json::Value> = Vec::new();
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
                } else if self.at_keyword("realm") {
                    // T-0262: `realm "REALM.NAME"` -- names the Kerberos
                    // realm/AD domain this node participates in or, paired
                    // with `kdc`, represents (docs/strata/krb.md). STRING,
                    // not IDENT, since a realm name commonly carries `.`
                    // (same `runs_as`/`code` precedent). At most one per
                    // node; a repeated clause overwrites, mirroring
                    // `clearance`.
                    self.advance();
                    krb_realm = Some(self.expect_string("realm name")?);
                } else if self.at_keyword("kdc") {
                    // T-0262: bare marker -- this node is the Key
                    // Distribution Center for its `realm` (docs/strata/
                    // krb.md). Mirrors `unit`'s bare-marker shape.
                    self.advance();
                    krb_is_kdc = true;
                } else if self.at_keyword("spn") {
                    // T-0262: `spn "SPN/value@REALM"`+ -- one or more
                    // service principal names bound to this node's
                    // `runs_as` service account (T-0255's principal,
                    // docs/strata/krb.md). STRING, repeatable, same shape
                    // as `code`/`carries`.
                    self.advance();
                    krb_spns.push(self.expect_string("spn value")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        krb_spns.push(self.expect_string("spn value")?);
                    }
                } else if self.at_keyword("delegation") {
                    // T-0262: `delegation none|constrained|rbcd|unconstrained
                    // [target "SPN"]*` -- the crown-jewel lateral-movement
                    // modeling target (docs/strata/krb.md). The kind is an
                    // IDENT drawn from a closed vocabulary (validated at
                    // elaboration time, mirroring how `boundary`'s
                    // endorse/declassify kind is grammar-fixed but other
                    // closed-vocabulary clauses like `observe`'s log
                    // classes defer validation to the elaborator); `target`
                    // is only meaningful for `constrained` but the parser
                    // accepts it unconditionally and leaves that check to
                    // the elaborator (law 2: no silent drop, but also no
                    // parser-level coupling between two clauses' shapes).
                    self.advance();
                    krb_delegation = Some(self.expect_ident("delegation kind")?);
                    while self.at_keyword("target") {
                        self.advance();
                        krb_delegation_targets.push(self.expect_string("delegation target spn")?);
                    }
                } else if self.at_keyword("trusts") {
                    // T-0262: `trusts IDENT [direction "one-way"|"two-way"]
                    // [transitive]` -- a domain trust from this realm node
                    // to another (docs/strata/krb.md). IDENT is the target
                    // realm node's id (a dangling/non-realm reference is an
                    // elaboration-time check, not a parser one, matching
                    // `panics_contained_by`'s precedent). Repeatable: a
                    // realm may trust more than one other realm.
                    self.advance();
                    let target = self.expect_ident("trusts target realm node id")?;
                    let mut direction = "one-way".to_string();
                    if self.at_keyword("direction") {
                        self.advance();
                        direction = self.expect_string("trust direction")?;
                    }
                    let mut transitive = false;
                    if self.at_keyword("transitive") {
                        self.advance();
                        transitive = true;
                    }
                    krb_trusts.push(json!({
                        "target": target,
                        "direction": direction,
                        "transitive": transitive,
                    }));
                } else if self.at_keyword("runs_as") {
                    // T-0255: `runs_as "svc-name"` -- names the dedicated
                    // OS service user the deploy generator creates for
                    // this node (docs/strata/host.md). STRING, not IDENT,
                    // since a service-user name commonly carries `-`
                    // (same `code`/`may` precedent). At most one per node;
                    // a repeated clause overwrites, mirroring `clearance`.
                    self.advance();
                    runs_as = Some(self.expect_string("runs_as service user name")?);
                } else if self.at_keyword("unit") {
                    // T-0255: bare marker -- this node's process is
                    // modeled as a systemd unit (docs/strata/host.md).
                    // Hardening directives are DERIVED by the generator
                    // (T-0256) from the rest of the model (may
                    // capabilities, owns, listens); this marker only
                    // records that the binding applies.
                    self.advance();
                    is_unit = true;
                } else if self.at_keyword("owns") {
                    // T-0255: `owns "PATH" "MODE"` -- a filesystem path
                    // this node's service user owns, with an explicit
                    // octal mode (docs/strata/host.md). Both STRING: PATH
                    // carries `/` (not a valid ident char) and MODE is
                    // quoted for the same "opaque atom" reason `code`/
                    // `may` use STRING. Repeatable: a node may own more
                    // than one path.
                    self.advance();
                    let path = self.expect_string("owns path")?;
                    let mode = self.expect_string("owns mode")?;
                    owns.push(json!({"path": path, "mode": mode}));
                } else if self.at_keyword("listens") {
                    // T-0255: `listens PORT` -- a TCP/UDP port this node's
                    // unit binds a socket to (docs/strata/host.md).
                    // NUMBER, not STRING: a port is a plain integer with
                    // no non-ident characters, matching `capacity`'s
                    // replicas bounds convention. Repeatable.
                    self.advance();
                    listens.push(self.expect_int("listens port")?);
                } else if self.at_keyword("group") {
                    // T-0272: `group "NAME"`+ -- one or more OS groups this
                    // node's service user is a member of (docs/strata/
                    // host.md#surface-grammar). STRING, not IDENT, mirroring
                    // `runs_as`'s "opaque atom" reason (a group name may
                    // carry `-`). Repeatable: a node's service user may
                    // belong to more than one group, same shape as `code`/
                    // `carries`. Desugars to a `group=<name>` attr, one per
                    // entry (owns-adjacent: `_host.py::_host_attrs`).
                    self.advance();
                    group.push(self.expect_string("group name")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        group.push(self.expect_string("group name")?);
                    }
                } else if self.at_keyword("sudoers") {
                    // T-0272: `sudoers "RULE"`+ -- one or more sudoers grant
                    // lines for this node's service user (docs/strata/
                    // host.md#surface-grammar). STRING, since a sudoers rule
                    // is free-form text (e.g. "ALL=(root) NOPASSWD: /bin/
                    // systemctl restart app"), the same "opaque atom"
                    // reasoning as `may`/`carries`. Repeatable: a service
                    // user may hold more than one sudoers grant. Desugars to
                    // a `sudoers=<rule>` attr, one per entry.
                    self.advance();
                    sudoers.push(self.expect_string("sudoers rule")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        sudoers.push(self.expect_string("sudoers rule")?);
                    }
                } else if self.at_keyword("platform") {
                    // T-0261: `platform "windows"` -- the std.host platform
                    // discriminator (docs/strata/host.md#hostmanifest).
                    // STRING, matching `realm`'s "opaque atom" shape. At
                    // most one per node; a repeated clause overwrites,
                    // mirroring `clearance`. Only `"windows"` is a known
                    // value -- an unrecognized platform name fails closed
                    // at `_host.py::host_manifest_for` time, not here
                    // (mirrors `owns` MODE/`listens` PORT deferring
                    // well-formedness checks to the elaborator).
                    self.advance();
                    platform = Some(self.expect_string("platform name")?);
                } else if self.at_keyword("service_account") {
                    // T-0261: `service_account "NAME" [gmsa]` -- names the
                    // dedicated Windows service account (or, with the
                    // trailing bare `gmsa` marker, a group Managed Service
                    // Account for domain-joined hosts) the deploy generator
                    // creates for this node (docs/strata/host.md#windows-
                    // surface-grammar). STRING, the Windows analog of
                    // `runs_as`. At most one per node; a repeated clause
                    // overwrites, mirroring `clearance`.
                    self.advance();
                    service_account = Some(self.expect_string("service account name")?);
                    if self.at_keyword("gmsa") {
                        self.advance();
                        service_account_gmsa = true;
                    }
                } else if self.at_keyword("service") {
                    // T-0261: bare marker -- this node's process is modeled
                    // as a Windows Service Control Manager (SCM) service
                    // (docs/strata/host.md#windows-surface-grammar), the
                    // Windows analog of `unit`. Hardening directives
                    // (service SID type restricted, required-privileges
                    // allowlist, protected-process) are DERIVED by the
                    // generator from the rest of the model, exactly like
                    // `unit`'s hardening derivation -- this marker only
                    // records that the binding applies.
                    self.advance();
                    is_service = true;
                } else if self.at_keyword("acl") {
                    // T-0261: `acl "PATH" "RULE"` -- a Windows NTFS path
                    // this node's service account has an explicit DACL
                    // entry for, RULE an opaque `PRINCIPAL:RIGHTS[:deny]
                    // [:no_inherit]` atom (docs/strata/host.md#windows-
                    // surface-grammar), the Windows analog of `owns` (richer
                    // than a 3-octal mode: expresses per-principal rights,
                    // deny ACEs, and deny-inheritance). Both STRING, same
                    // "opaque atom" reasoning `owns`'s MODE uses --
                    // well-formedness is validated at `_host.py` elaborate
                    // time, not here. Repeatable: a node may declare more
                    // than one ACL entry.
                    self.advance();
                    let path = self.expect_string("acl path")?;
                    let rule = self.expect_string("acl rule")?;
                    acl.push(json!({"path": path, "rule": rule}));
                } else if self.at_keyword("pipe") {
                    // T-0261: `pipe "NAME"`+ -- one or more named pipes this
                    // node's service listens on (docs/strata/host.md
                    // #windows-surface-grammar), additive to the platform-
                    // agnostic `listens` PORT surface (Windows firewall
                    // ports reuse `listens` unchanged -- a bound port is
                    // the same concept on every platform). STRING, since a
                    // pipe name commonly carries `\`. Repeatable.
                    self.advance();
                    pipes.push(self.expect_string("pipe name")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        pipes.push(self.expect_string("pipe name")?);
                    }
                } else if self.at_keyword("bin_path") {
                    // T-0629: `bin_path "PATH" ["ARGS"]` -- the Windows SCM
                    // `binPath`/ImagePath (executable path, plus an optional
                    // trailing arguments string) `sc.exe create` needs to
                    // actually stand up a `service`-marked node's SCM
                    // service, not just harden an already-existing one
                    // (docs/strata/host.md#windows-surface-grammar). Both
                    // STRING, same "opaque atom" reasoning `acl`'s PATH/RULE
                    // use -- a Windows executable path commonly carries `:`
                    // for a drive letter and `\` separators, and the
                    // trailing ARGS string is free-form. Desugars STRAIGHT
                    // to `bin_path=<path>` (+ `bin_path_args=<args>` when
                    // ARGS given) node attrs here, the same direct-attr-push
                    // shape `skew` uses below, rather than threading a new
                    // NodeDecl field through `_ast.py`/`_elaborate.py` (out
                    // of this ticket's scope) -- `_host.py::
                    // _parse_host_attrs` reads the two attrs back
                    // regardless of which caller (node or store) produced
                    // them, same shared-encoding discipline every other
                    // std.host clause uses. At most one per node; a
                    // repeated clause overwrites (mirrors `platform`).
                    self.advance();
                    let path = self.expect_string("bin_path path")?;
                    attrs.retain(|a| {
                        !a.starts_with("bin_path=") && !a.starts_with("bin_path_args=")
                    });
                    attrs.push(format!("bin_path={}", path));
                    if matches!(self.cur().kind, TokKind::Str(_)) {
                        let args = self.expect_string("bin_path args")?;
                        attrs.push(format!("bin_path_args={}", args));
                    }
                } else if self.at_keyword("access") {
                    self.parse_access_attr(&mut attrs)?;
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
                } else if self.at_keyword("users") {
                    // T-0702: `users NUMBER` -- a steady population entry
                    // demand (docs/strata/kernel.md#demand-t-0702).
                    self.advance();
                    users = Some(self.expect_number("users population")?);
                } else if self.at_keyword("rate") {
                    // T-0702: `rate NUMBER UNIT` -- an arrival-rate entry
                    // demand, same QUANTITY shape `flow`'s `rate` clause
                    // and `capacity`'s rate use (docs/strata/kernel.md
                    // #demand-t-0702). Top-level on node/store, distinct
                    // from `capacity`'s own nested rate quantity.
                    self.advance();
                    demand_rate = Some(self.parse_quantity("rate")?);
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
                } else if self.at_keyword("code") {
                    // T-0132: `code GLOB+` -- one or more STRING-quoted
                    // globs (surface.md#grammar-sketch); STRING rather than
                    // IDENT because globs carry `/` and `*`, neither a
                    // valid ident char. Elaborated to `code=<glob>` node
                    // attrs, one per glob (T-0078 attr convention).
                    self.advance();
                    code.push(self.expect_string("code glob")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        code.push(self.expect_string("code glob")?);
                    }
                } else if self.at_keyword("may") {
                    // T-0132: `may CAPABILITY` -- a STRING-quoted
                    // capability atom (e.g. "net.out:stripe.com"); STRING
                    // rather than IDENT because capability atoms carry `.`
                    // and `:`, neither a valid ident char. Repeatable via
                    // multiple `may "...";` statements; lands directly in
                    // `Node.may` (no attr encoding needed, unlike `code`).
                    self.advance();
                    may.push(self.expect_string("may capability")?);
                } else if self.at_keyword("carries") {
                    // T-0154: `carries PII_TAG+` -- one or more STRING-
                    // quoted PII tags (e.g. "identifier.email"), the SAME
                    // STRING-not-IDENT shape T-0132 chose for `code`/`may`
                    // (`.` is not a valid ident char, docs/strata/
                    // surface.md#node-grammar). Elaborated to `pii=<tag>`
                    // node attrs, one per tag (mirrors `code`'s
                    // `code=<glob>` desugar, `_pii.py::_PII_PREFIX`).
                    self.advance();
                    carries.push(self.expect_string("carries pii tag")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        carries.push(self.expect_string("carries pii tag")?);
                    }
                } else if self.at_keyword("on") {
                    // T-0136: `on deploy { canary { ... }; endorsed_by ...;
                    // rollback within QUANTITY }` -- a node's deploy
                    // contract (docs/strata/surface.md#std-deploy, T-0083's
                    // landed kernel construct). `on crash`/`on breach` are
                    // still unimplemented surface syntax (T-0083's own
                    // deferral note), so `deploy` is the only `on` keyword
                    // this parser accepts today; anything else is a parse
                    // error, not a silent no-op (law 2).
                    self.advance();
                    self.expect_keyword("deploy")?;
                    deploy = Some(self.parse_on_deploy_block()?);
                } else if self.at_keyword("panics_contained_by") {
                    // T-0070: names the crash-boundary supervisor node id;
                    // reference validity is an elaboration-time check.
                    self.advance();
                    panics_contained_by = Some(self.expect_ident("panics supervisor id")?);
                } else if self.at_keyword("managed") {
                    // T-0172: bare marker, no argument -- mirrors
                    // `errors_total`'s shape. Marks the node as external,
                    // pure-config infrastructure with no scannable code by
                    // declaration (docs/strata/surface.md#node-grammar,
                    // #key-construct-semantics): tier-2 code-binding
                    // conformance is not required for it, and a fired
                    // weakness obligation on it discharges without the
                    // stricter mitigation-chokepoint (boundary-kind) proof
                    // that a code-modeled node needs -- config evidence or
                    // an `assume` claim stands in (`_threat.py::
                    // _check_one_discharge`).
                    self.advance();
                    is_managed = true;
                } else if self.at_keyword("waive") {
                    // T-0174: `waive RULE reason="..." [ticket="T-XXXX"]` --
                    // an in-design waiver for a `frob sys audit` finding
                    // (SYS100-102/THREAT002-003/LINT004) against THIS node,
                    // the surface analog of `frob:waive` for gate
                    // violations (docs/strata/surface.md#node-grammar,
                    // `frob.strata._waive`). RULE and reason are STRING
                    // (not IDENT) for the same reason `may`/`carries` are:
                    // rule ids and free-text reasons are not valid idents.
                    // `reason` is mandatory at parse time (law 2: no
                    // fabricated/implicit waivers, mirrors `assume`'s
                    // mandatory `owner`/`review` above) -- a `waive` clause
                    // with no reason is a hard parse error, never a silent
                    // pass. Repeatable: a node may waive more than one
                    // rule.
                    self.advance();
                    let rule = self.expect_string("waive rule id")?;
                    self.expect_keyword("reason")?;
                    let reason = self.expect_string("waive reason")?;
                    let mut ticket: Option<String> = None;
                    if self.at_keyword("ticket") {
                        self.advance();
                        ticket = Some(self.expect_string("waive ticket ref")?);
                    }
                    waives.push(json!({
                        "rule": rule,
                        "reason": reason,
                        "ticket": ticket,
                    }));
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
            "users": users,
            "rate": demand_rate,
            "residence": residence,
            "errors_total": errors_total,
            "panics_contained_by": panics_contained_by,
            "observe": observe,
            "code": code,
            "may": may,
            "deploy": deploy,
            "carries": carries,
            "is_managed": is_managed,
            "waives": waives,
            "runs_as": runs_as,
            "is_unit": is_unit,
            "owns": owns,
            "listens": listens,
            "group": group,
            "sudoers": sudoers,
            "platform": platform,
            "service_account": service_account,
            "service_account_gmsa": service_account_gmsa,
            "is_service": is_service,
            "acl": acl,
            "pipes": pipes,
            "krb_realm": krb_realm,
            "krb_is_kdc": krb_is_kdc,
            "krb_spns": krb_spns,
            "krb_delegation": krb_delegation,
            "krb_delegation_targets": krb_delegation_targets,
            "krb_trusts": krb_trusts,
        }));
        Ok(())
    }

    /// deploy_block := "{" deploy_prop (";" deploy_prop)* "}"
    /// deploy_prop  := "canary" "{" canary_stage ("," canary_stage)* "}"
    ///               | "endorsed_by" REF ("," REF)*
    ///               | "rollback" "within" QUANTITY
    /// canary_stage := IDENT "for" QUANTITY
    ///
    /// WHY: `on deploy` desugars straight onto `_models.py::DeployContract`
    /// (T-0083's landed kernel construct, no new primitive here) --
    /// `canary`/`endorsed_by` are optional and default to an empty list
    /// (the elaborator supplies `()`, matching `DeployContract.stages`/
    /// `endorsement_chain`'s own semantics of "no stages/no endorsement
    /// required" rather than a parser default), but `rollback within
    /// QUANTITY` is mandatory -- `DeployContract.rollback_budget` has no
    /// default, and a missing rollback bound is exactly the "half a
    /// containment story" charter law 2 refuses to leave implicit
    /// (docs/strata/surface.md#std-deploy).
    fn parse_on_deploy_block(&mut self) -> Result<serde_json::Value, ParseError> {
        self.expect_symbol('{')?;
        let mut stages: Vec<serde_json::Value> = Vec::new();
        let mut endorsed_by: Vec<String> = Vec::new();
        let mut rollback_budget: Option<serde_json::Value> = None;
        loop {
            if self.at_symbol('}') {
                break;
            }
            if self.at_keyword("canary") {
                self.advance();
                self.expect_symbol('{')?;
                if !self.at_symbol('}') {
                    stages.push(self.parse_canary_stage()?);
                    while self.at_symbol(',') {
                        self.advance();
                        stages.push(self.parse_canary_stage()?);
                    }
                }
                self.expect_symbol('}')?;
            } else if self.at_keyword("endorsed_by") {
                self.advance();
                endorsed_by.push(self.expect_ident("endorsed_by boundary id")?);
                while self.at_symbol(',') {
                    self.advance();
                    endorsed_by.push(self.expect_ident("endorsed_by boundary id")?);
                }
            } else if self.at_keyword("rollback") {
                self.advance();
                self.expect_keyword("within")?;
                rollback_budget = Some(self.parse_quantity("rollback budget")?);
            } else {
                return self.err("unknown deploy property");
            }
            if self.at_symbol(';') {
                self.advance();
            } else {
                break;
            }
        }
        self.expect_symbol('}')?;
        let rollback_budget = match rollback_budget {
            Some(r) => r,
            None => return self.err("on deploy block needs a rollback within QUANTITY clause"),
        };
        Ok(json!({
            "stages": stages,
            "endorsed_by": endorsed_by,
            "rollback_budget": rollback_budget,
        }))
    }

    /// canary_stage := IDENT "for" QUANTITY
    fn parse_canary_stage(&mut self) -> Result<serde_json::Value, ParseError> {
        let level = self.expect_ident("canary stage level")?;
        self.expect_keyword("for")?;
        let bake = self.parse_quantity("canary stage bake duration")?;
        Ok(json!({"level": level, "bake": bake}))
    }

    /// secret := "secret" ID "{" secret_prop (";" secret_prop)* "}"
    /// secret_prop := "issued_by" REF | "audience" "{" REF ("," REF)* "}"
    ///              | "lifetime" QUANTITY | "revoke" QUANTITY
    ///
    /// WHY: mirrors `_secrets.py::SecretSpec` field for field (T-0082's
    /// landed kernel construct, docs/strata/surface.md#std-secrets's
    /// normative sketch: `secret X issued_by Y audience [...] lifetime T
    /// revoke T'`). `revoke` is grammar-optional -- `SecretSpec.revoke` is
    /// `Quantity | None`, and the mandatory-revocation rule is enforced by
    /// `_secrets.py::_validate_secret_bounds` (`MissingRevocation`) at
    /// elaboration time, not here, matching how `code`/`may`'s downstream
    /// validation already lives in the elaborator rather than the parser.
    fn parse_secret(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'secret'
        let id = self.expect_ident("secret id")?;
        self.expect_symbol('{')?;
        let mut issued_by: Option<String> = None;
        let mut audience: Vec<String> = Vec::new();
        let mut lifetime: Option<serde_json::Value> = None;
        let mut revoke: Option<serde_json::Value> = None;
        loop {
            if self.at_symbol('}') {
                break;
            }
            if self.at_keyword("issued_by") {
                self.advance();
                issued_by = Some(self.expect_ident("secret issuing authority")?);
            } else if self.at_keyword("audience") {
                self.advance();
                self.expect_symbol('{')?;
                if !self.at_symbol('}') {
                    audience.push(self.expect_ident("secret audience member")?);
                    while self.at_symbol(',') {
                        self.advance();
                        audience.push(self.expect_ident("secret audience member")?);
                    }
                }
                self.expect_symbol('}')?;
            } else if self.at_keyword("lifetime") {
                self.advance();
                lifetime = Some(self.parse_quantity("secret lifetime")?);
            } else if self.at_keyword("revoke") {
                self.advance();
                revoke = Some(self.parse_quantity("secret revoke SLA")?);
            } else {
                return self.err("unknown secret property");
            }
            if self.at_symbol(';') {
                self.advance();
            } else {
                break;
            }
        }
        self.expect_symbol('}')?;
        let issued_by = match issued_by {
            Some(i) => i,
            None => return self.err("secret needs an issued_by clause"),
        };
        let lifetime = match lifetime {
            Some(l) => l,
            None => return self.err("secret needs a lifetime clause"),
        };
        ast.secrets.push(json!({
            "id": id,
            "issued_by": issued_by,
            "audience": audience,
            "lifetime": lifetime,
            "revoke": revoke,
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
                } else if self.at_keyword("authenticates_via") {
                    // T-0262: `authenticates_via tgt|st` -- marks this flow
                    // as crossing a Kerberos authentication boundary
                    // (ticket-granting or service-ticket exchange,
                    // docs/strata/krb.md). Desugars to a flow attr
                    // "krb_ticket=<kind>" -- no new kernel primitive
                    // (charter law 1); the existing flow/noflow/reach
                    // machinery already walks this edge, the attr just
                    // tags it as a Kerberos crossing for std.krb-aware
                    // obligations (T-0263) to key off later.
                    self.advance();
                    let kind = self.expect_ident("authenticates_via ticket kind")?;
                    attrs.push(format!("krb_ticket={}", kind));
                } else if self.at_keyword("utility") {
                    // T-0226: `utility;` -- marks this flow as a
                    // non-transitive utility/hub hop. Desugars to the bare
                    // flow attr "utility" (no new kernel primitive, charter
                    // law 1) -- `_facts.py::FactBase.reachable` reads it the
                    // SAME way it already reads `krb_no_transit` (T-0282):
                    // the edge's dst is still directly reachable, but the
                    // BFS does not chain past it. This is how a legitimate
                    // `noflow` claim survives an unrelated hub edge (e.g. a
                    // logging import) that would otherwise be treated as
                    // carrying real influence across the hub
                    // (docs/strata/kernel.md#fact-base).
                    self.advance();
                    attrs.push("utility".to_string());
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
    /// surface (clearance/attr/residence/capacity/errors_total/
    /// panics_contained_by/observe/`on deploy`, T-0247) verbatim plus
    /// engine, the immutable/append_only markers the elaborator needs for
    /// the cdn-unlimited-staleness pairing, and `rpo` -- a store's declared
    /// durability/replication lag, the same age-collapse family as cache ttl
    /// (docs/strata/surface.md#std-infra, docs/strata/kernel.md#age-
    /// propagation-semantics). The grammar accepts any unit here; dimension
    /// validation (must be a time unit) is the elaborator's job, matching
    /// how ttl/staleness stay units-only at parse time too. T-0247's four
    /// clauses are the observability/deploy-contract subset of node_prop a
    /// store needed; std.krb's realm/kdc/spn/delegation/trusts remain
    /// node-only (not requested by this ticket, filed separately if still
    /// needed).
    fn parse_store(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'store'
        let id = self.expect_ident("store id")?;
        self.expect_symbol(':')?;
        let trust = self.expect_ident("trust level")?;
        let mut clearance = "Secret".to_string();
        let mut attrs: Vec<String> = Vec::new();
        let mut residence: Option<String> = None;
        let mut capacity: Option<serde_json::Value> = None;
        // T-0702: same `users`/`rate` entry-demand shape as `node`'s --
        // a store is a node too (docs/strata/surface.md#key-construct-
        // semantics), so it can be the demand-declaring endpoint too.
        let mut users: Option<f64> = None;
        let mut demand_rate: Option<serde_json::Value> = None;
        let mut engine: Option<String> = None;
        let mut immutable = false;
        let mut append_only = false;
        let mut rpo: Option<serde_json::Value> = None;
        let mut carries: Vec<String> = Vec::new();
        let mut is_managed = false;
        let mut code: Vec<String> = Vec::new();
        let mut may: Vec<String> = Vec::new();
        let mut waives: Vec<serde_json::Value> = Vec::new();
        let mut runs_as: Option<String> = None;
        let mut is_unit = false;
        let mut owns: Vec<serde_json::Value> = Vec::new();
        let mut listens: Vec<i64> = Vec::new();
        let mut group: Vec<String> = Vec::new();
        let mut sudoers: Vec<String> = Vec::new();
        // T-0261: same std.host windows fields as `node` (parse_node) --
        // a store is a node too.
        let mut platform: Option<String> = None;
        let mut service_account: Option<String> = None;
        let mut service_account_gmsa = false;
        let mut is_service = false;
        let mut acl: Vec<serde_json::Value> = Vec::new();
        let mut pipes: Vec<String> = Vec::new();
        let mut errors_total = false;
        let mut panics_contained_by: Option<String> = None;
        let mut observe: Option<serde_json::Value> = None;
        let mut deploy: Option<serde_json::Value> = None;
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
                } else if self.at_keyword("runs_as") {
                    // T-0255: same shape as `node`'s `runs_as` -- a store
                    // is a node too (docs/strata/surface.md
                    // #key-construct-semantics).
                    self.advance();
                    runs_as = Some(self.expect_string("runs_as service user name")?);
                } else if self.at_keyword("unit") {
                    // T-0255: same bare marker as `node`'s `unit`.
                    self.advance();
                    is_unit = true;
                } else if self.at_keyword("owns") {
                    // T-0255: same `owns "PATH" "MODE"` shape as `node`.
                    self.advance();
                    let path = self.expect_string("owns path")?;
                    let mode = self.expect_string("owns mode")?;
                    owns.push(json!({"path": path, "mode": mode}));
                } else if self.at_keyword("listens") {
                    // T-0255: same `listens PORT` shape as `node`.
                    self.advance();
                    listens.push(self.expect_int("listens port")?);
                } else if self.at_keyword("group") {
                    // T-0272: same `group "NAME"`+ shape as `node`'s clause
                    // -- a store is a node too (docs/strata/surface.md
                    // #key-construct-semantics).
                    self.advance();
                    group.push(self.expect_string("group name")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        group.push(self.expect_string("group name")?);
                    }
                } else if self.at_keyword("sudoers") {
                    // T-0272: same `sudoers "RULE"`+ shape as `node`'s
                    // clause -- a store is a node too.
                    self.advance();
                    sudoers.push(self.expect_string("sudoers rule")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        sudoers.push(self.expect_string("sudoers rule")?);
                    }
                } else if self.at_keyword("platform") {
                    // T-0261: same `platform "windows"` shape as `node`'s
                    // clause -- a store is a node too.
                    self.advance();
                    platform = Some(self.expect_string("platform name")?);
                } else if self.at_keyword("service_account") {
                    // T-0261: same `service_account "NAME" [gmsa]` shape as
                    // `node`'s clause -- a store is a node too.
                    self.advance();
                    service_account = Some(self.expect_string("service account name")?);
                    if self.at_keyword("gmsa") {
                        self.advance();
                        service_account_gmsa = true;
                    }
                } else if self.at_keyword("service") {
                    // T-0261: same bare marker as `node`'s `service`.
                    self.advance();
                    is_service = true;
                } else if self.at_keyword("acl") {
                    // T-0261: same `acl "PATH" "RULE"` shape as `node`'s
                    // clause -- a store is a node too.
                    self.advance();
                    let path = self.expect_string("acl path")?;
                    let rule = self.expect_string("acl rule")?;
                    acl.push(json!({"path": path, "rule": rule}));
                } else if self.at_keyword("pipe") {
                    // T-0261: same `pipe "NAME"`+ shape as `node`'s clause
                    // -- a store is a node too.
                    self.advance();
                    pipes.push(self.expect_string("pipe name")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        pipes.push(self.expect_string("pipe name")?);
                    }
                } else if self.at_keyword("bin_path") {
                    // T-0629: same `bin_path "PATH" ["ARGS"]` shape as
                    // `node`'s clause -- a store is a node too
                    // (docs/strata/surface.md#key-construct-semantics).
                    self.advance();
                    let path = self.expect_string("bin_path path")?;
                    attrs.retain(|a| {
                        !a.starts_with("bin_path=") && !a.starts_with("bin_path_args=")
                    });
                    attrs.push(format!("bin_path={}", path));
                    if matches!(self.cur().kind, TokKind::Str(_)) {
                        let args = self.expect_string("bin_path args")?;
                        attrs.push(format!("bin_path_args={}", args));
                    }
                } else if self.at_keyword("access") {
                    self.parse_access_attr(&mut attrs)?;
                } else if self.at_keyword("code") {
                    // T-0166: `code GLOB+` -- same STRING+ shape T-0132 gave
                    // `node` (parse_node); a store is a node too
                    // (docs/strata/surface.md#key-construct-semantics), so
                    // it binds source the same way a code-modeled node does.
                    self.advance();
                    code.push(self.expect_string("code glob")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        code.push(self.expect_string("code glob")?);
                    }
                } else if self.at_keyword("waive") {
                    // T-0250: `waive RULE reason="..." [ticket="T-XXXX"]` --
                    // same shape and same mandatory-reason rule as
                    // parse_node's T-0174 waive clause; a store is a node
                    // too (docs/strata/surface.md#key-construct-semantics),
                    // so a `frob sys audit` finding against a store
                    // (SYS100-102/THREAT002-003/LINT004) needs the same
                    // in-design waiver escape hatch. `reason` is mandatory
                    // at parse time (law 2: no fabricated/implicit
                    // waivers) -- a `waive` clause with no reason is a hard
                    // parse error, never a silent pass. Repeatable: a store
                    // may waive more than one rule.
                    self.advance();
                    let rule = self.expect_string("waive rule id")?;
                    self.expect_keyword("reason")?;
                    let reason = self.expect_string("waive reason")?;
                    let mut ticket: Option<String> = None;
                    if self.at_keyword("ticket") {
                        self.advance();
                        ticket = Some(self.expect_string("waive ticket ref")?);
                    }
                    waives.push(json!({
                        "rule": rule,
                        "reason": reason,
                        "ticket": ticket,
                    }));
                } else if self.at_keyword("may") {
                    // T-0166: `may CAPABILITY` -- same STRING-quoted
                    // capability atom shape T-0132 gave `node`. Lands
                    // directly in `Node.may` on elaboration, same as node.
                    self.advance();
                    may.push(self.expect_string("may capability")?);
                } else if self.at_keyword("carries") {
                    // T-0154: same `carries PII_TAG+` shape as `node`
                    // (parse_node) -- a store is the most common PII
                    // resting place, so it gets the same declaration.
                    self.advance();
                    carries.push(self.expect_string("carries pii tag")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        carries.push(self.expect_string("carries pii tag")?);
                    }
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
                } else if self.at_keyword("users") {
                    // T-0702: same `users NUMBER` shape as `node`'s clause.
                    self.advance();
                    users = Some(self.expect_number("users population")?);
                } else if self.at_keyword("rate") {
                    // T-0702: same `rate NUMBER UNIT` shape as `node`'s
                    // clause, top-level and distinct from `capacity`'s own
                    // nested rate quantity.
                    self.advance();
                    demand_rate = Some(self.parse_quantity("rate")?);
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
                } else if self.at_keyword("managed") {
                    // T-0172: same bare marker as `node` (parse_node) --
                    // a store is a node too (docs/strata/surface.md
                    // #key-construct-semantics: "component / store: nodes").
                    self.advance();
                    is_managed = true;
                } else if self.at_keyword("errors_total") {
                    // T-0247: same bare marker as `node`'s `errors_total`
                    // (parse_node) -- a store is a node too (docs/strata/
                    // surface.md#key-construct-semantics), so the
                    // errors-total observability claim applies to it
                    // unchanged. The elaborator turns this into the same
                    // `errors_total` node attr `node` gets.
                    self.advance();
                    errors_total = true;
                } else if self.at_keyword("panics_contained_by") {
                    // T-0247: same `panics_contained_by IDENT` shape as
                    // `node`'s clause; reference validity is an
                    // elaboration-time check, mirroring parse_node.
                    self.advance();
                    panics_contained_by = Some(self.expect_ident("panics supervisor id")?);
                } else if self.at_keyword("on") {
                    // T-0247: same `on deploy { ... }` shape as `node`'s
                    // clause (parse_node); `deploy` is still the only `on`
                    // keyword this parser accepts, matching parse_node's
                    // deferral note for `on crash`/`on breach`.
                    self.advance();
                    self.expect_keyword("deploy")?;
                    deploy = Some(self.parse_on_deploy_block()?);
                } else if self.at_keyword("observe") {
                    // T-0247: same `observe { log IDENT (, IDENT)*; to
                    // IDENT }` shape as `node`'s clause (parse_node).
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
            "users": users,
            "rate": demand_rate,
            "residence": residence,
            "engine": engine,
            "immutable": immutable,
            "append_only": append_only,
            "rpo": rpo,
            "carries": carries,
            "is_managed": is_managed,
            "code": code,
            "may": may,
            "waives": waives,
            "runs_as": runs_as,
            "is_unit": is_unit,
            "owns": owns,
            "listens": listens,
            "group": group,
            "sudoers": sudoers,
            "platform": platform,
            "service_account": service_account,
            "service_account_gmsa": service_account_gmsa,
            "is_service": is_service,
            "acl": acl,
            "pipes": pipes,
            "errors_total": errors_total,
            "panics_contained_by": panics_contained_by,
            "observe": observe,
            "deploy": deploy,
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

    /// queue := "queue" ID (":" TRUST)? "{" queue_prop (";" queue_prop)* "}"?
    /// queue_prop := "delivery" IDENT | "ordering" IDENT | "attr" ATTRVAL
    ///             | "clearance" IDENT
    ///
    /// WHY optional TRUST: T-0093 -- queue previously had no TRUST clause at
    /// all and the elaborator hardcoded a `"trusted"` default
    /// (docs/strata/surface.md#std-infra deviation note). The clause is
    /// optional (not mandatory) so every existing `.strata` source without it
    /// keeps parsing identically; the elaborator still defaults to
    /// `"trusted"` when omitted.
    /// resource := "resource" ID ("{" resource_prop (";" resource_prop)* "}")?
    /// resource_prop := "arbitrated_by" ID | "lock" STRING
    ///
    /// WHY: T-0700's shared-resource declaration -- names a resource
    /// `access` clauses (`parse_access_attr`) reference by matching
    /// STRING id, and optionally binds a single arbiter (a node id that
    /// mediates access) or a lease/lock NAME. At most one of
    /// `arbitrated_by`/`lock` may be given -- a resource with both would
    /// leave the contention-proof obligation unable to tell which
    /// mechanism actually discharges it, so this is a parse error rather
    /// than a silent "last one wins" (same discipline `parse_resource`'s
    /// sibling clauses use for at-most-one fields elsewhere in this
    /// file). A bare `resource ID;` (no body) declares the resource
    /// exists with no arbiter -- the contention proof then requires every
    /// accessor to be read/alpha-only (module docstring compatibility
    /// matrix, `src/frob/strata/_access.py`).
    fn parse_resource(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'resource'
        let id = self.expect_ident("resource id")?;
        let mut arbitrated_by: Option<String> = None;
        let mut lock: Option<String> = None;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("arbitrated_by") {
                    if arbitrated_by.is_some() || lock.is_some() {
                        return self.err(
                            "resource may declare at most one of arbitrated_by/lock",
                        );
                    }
                    self.advance();
                    arbitrated_by = Some(self.expect_ident("arbiter node id")?);
                } else if self.at_keyword("lock") {
                    if arbitrated_by.is_some() || lock.is_some() {
                        return self.err(
                            "resource may declare at most one of arbitrated_by/lock",
                        );
                    }
                    self.advance();
                    lock = Some(self.expect_string("lock name")?);
                } else {
                    return self.err("unknown resource property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.resources.push(json!({
            "id": id,
            "arbitrated_by": arbitrated_by,
            "lock": lock,
        }));
        Ok(())
    }

    fn parse_queue(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'queue'
        let id = self.expect_ident("queue id")?;
        let mut trust: Option<String> = None;
        if self.at_symbol(':') {
            self.advance();
            trust = Some(self.expect_ident("trust level")?);
        }
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
            "trust": trust,
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

    /// balancer := "balancer" ID (":" TRUST)? "{" balancer_prop (";" balancer_prop)* "}"?
    /// balancer_prop := "policy" IDENT | "sticky"
    ///
    /// WHY optional TRUST: T-0093, same rationale as `parse_queue` above --
    /// balancer had no TRUST clause and defaulted to `"trusted"` in the
    /// elaborator; the clause is optional to stay backward-compatible with
    /// every existing `.strata` source.
    fn parse_balancer(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'balancer'
        let id = self.expect_ident("balancer id")?;
        let mut trust: Option<String> = None;
        if self.at_symbol(':') {
            self.advance();
            trust = Some(self.expect_ident("trust level")?);
        }
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
            "trust": trust,
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
        // T-0138: claim id accepts bare IDENT or a STRING-quoted id so
        // discharge claims can name catalog obligations containing ':'/'-'.
        let id = self.expect_ident_or_string("claim id")?;
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
                | "scenario" | "secret" | "resource" => {
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
                        "secret" => self.parse_secret(&mut ast)?,
                        // T-0700: shared-resource declaration -- named
                        // arbiter metadata, no accessor of its own.
                        "resource" => self.parse_resource(&mut ast)?,
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
    // frob:ticket T-0148
    fn parses_bare_module() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // frob:tests strata-core/src/parse.rs::parse_source_impl kind="unit"
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
    fn parses_string_quoted_claim_id() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: a discharge claim id naming a catalog obligation
        // ("weakness:CWE-79:web") cannot lex as IDENT ('-'/':' are not
        // ident chars) -- the claim-id position also accepts a
        // STRING-quoted id.
        let v = ok(r#"module m
            assert "weakness:CWE-79:web" noflow evil -> api"#);
        assert_eq!(v["claims"][0]["id"], "weakness:CWE-79:web");
        assert_eq!(v["claims"][0]["kind"], "noflow");
    }

    #[test]
    fn parses_string_quoted_claim_id_on_assume() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: quoted claim id alongside the owner/review assume tail.
        let v = ok(r#"module m
            assume "weakness:CWE-89:web" noflow evil -> api owner alice review "2026-08-01""#);
        assert_eq!(v["claims"][0]["id"], "weakness:CWE-89:web");
        assert_eq!(v["claims"][0]["assumed"], true);
        assert_eq!(v["claims"][0]["owner"], "alice");
        assert_eq!(v["claims"][0]["review"], "2026-08-01");
    }

    #[test]
    fn bare_ident_claim_id_still_parses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: the pre-existing bare-IDENT claim id form must keep
        // working unchanged alongside the new quoted alternate.
        let v = ok(r#"module m
            assert c1 noflow evil -> api"#);
        assert_eq!(v["claims"][0]["id"], "c1");
    }

    #[test]
    fn error_unterminated_string_claim_id() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: an unterminated string in the claim-id position fails
        // at the lexer with a real line/col, not a silent misparse.
        let e = err("module m\nassert \"weakness:CWE-79:web noflow evil -> api");
        assert_eq!(e["line"], 2);
        assert!(e["message"].as_str().unwrap().contains("string"));
    }

    #[test]
    fn error_malformed_claim_id_neither_ident_nor_string() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: a claim id that is neither IDENT nor STRING (e.g. a bare
        // number) is still a parse error at the claim-id position.
        let e = err("module m\nassert 123 noflow evil -> api");
        assert_eq!(e["message"], "expected claim id");
        assert_eq!(e["line"], 2);
    }

    #[test]
    fn parses_node_code_globs_and_may_capabilities() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0132: code=<glob> / may <capability> surface grammar.
        let v = ok(r#"module m
            node api : trusted {
                code "src/frob/**" "tests/frob/**";
                may "net.out:stripe.com";
                may "fs.read:/etc/tls";
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["code"][0], "src/frob/**");
        assert_eq!(n["code"][1], "tests/frob/**");
        assert_eq!(n["may"][0], "net.out:stripe.com");
        assert_eq!(n["may"][1], "fs.read:/etc/tls");
    }

    #[test]
    fn parses_node_without_code_or_may_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0132: pre-existing sources with no code/may statements must
        // still elaborate -- both fields default to an empty list.
        let v = ok("module m\nnode api : trusted");
        let n = &v["nodes"][0];
        assert_eq!(n["code"].as_array().unwrap().len(), 0);
        assert_eq!(n["may"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_code_requires_at_least_one_glob() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0132: `code` is glob+, not glob*; a bare `code;` is a parse
        // error rather than silently binding zero globs (law 2).
        let e = err(r#"module m
            node api : trusted {
                code;
            }"#);
        assert_eq!(e["message"], "expected code glob");
    }

    #[test]
    fn error_may_requires_string_not_ident() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0132: capability atoms are STRING-quoted; a bare ident is
        // rejected rather than silently truncated at the first `.`/`:`.
        let e = err(r#"module m
            node api : trusted {
                may net.out;
            }"#);
        assert_eq!(e["message"], "expected may capability");
    }

    #[test]
    fn parses_node_carries_pii_tags() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0154: `carries PII_TAG+` -- one or more STRING-quoted PII tags
        // on a node, the same STRING+ shape T-0132 established for `code`.
        let v = ok(r#"module m
            node api : trusted {
                carries "identifier.email" "contact.phone";
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["carries"][0], "identifier.email");
        assert_eq!(n["carries"][1], "contact.phone");
    }

    #[test]
    fn parses_store_carries_pii_tags() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0154: `carries` is also legal inside `store` -- the most
        // common PII resting place.
        let v = ok(r#"module m
            store users : trusted {
                carries "identifier.email";
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["carries"][0], "identifier.email");
    }

    #[test]
    fn parses_store_code_globs_and_may_capabilities() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0166: `code`/`may` are also legal inside `store` -- "component
        // / store: nodes" (docs/strata/surface.md#key-construct-semantics),
        // same STRING+ / STRING shape T-0132 gave `node`.
        let v = ok(r#"module m
            store tickets_ledger : trusted {
                code "src/frob/tickets/**";
                may "fs";
                may "exec";
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["code"][0], "src/frob/tickets/**");
        assert_eq!(s["may"][0], "fs");
        assert_eq!(s["may"][1], "exec");
    }

    #[test]
    fn parses_store_without_code_or_may_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0166: pre-existing store sources with no code/may statements
        // must still elaborate -- both fields default to an empty list.
        let v = ok("module m\nstore users : trusted");
        let s = &v["stores"][0];
        assert_eq!(s["code"].as_array().unwrap().len(), 0);
        assert_eq!(s["may"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_store_code_requires_at_least_one_glob() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0166: `code` on a store is glob+, not glob*, same as `node`.
        let e = err(r#"module m
            store users : trusted {
                code;
            }"#);
        assert_eq!(e["message"], "expected code glob");
    }

    #[test]
    fn error_store_may_requires_string_not_ident() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0166: capability atoms on a store are STRING-quoted, same as
        // `node`; a bare ident is rejected.
        let e = err(r#"module m
            store users : trusted {
                may net.out;
            }"#);
        assert_eq!(e["message"], "expected may capability");
    }

    #[test]
    fn parses_node_without_carries_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0154: pre-existing sources with no `carries` statement must
        // still elaborate -- the field defaults to an empty list.
        let v = ok("module m\nnode api : trusted");
        let n = &v["nodes"][0];
        assert_eq!(n["carries"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_carries_requires_at_least_one_tag() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0154: `carries` is tag+, not tag*; a bare `carries;` is a
        // parse error rather than silently binding zero tags (law 2).
        let e = err(r#"module m
            node api : trusted {
                carries;
            }"#);
        assert_eq!(e["message"], "expected carries pii tag");
    }

    #[test]
    fn parses_secret_construct() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `secret ID { issued_by ...; audience { ... }; lifetime
        // ...; revoke ... }` -- surface syntax for `_secrets.py::SecretSpec`.
        let v = ok(r#"module m
            node vault : trusted
            node api : trusted
            secret db_creds {
                issued_by vault;
                audience { api };
                lifetime 24 h;
                revoke 5 min;
            }"#);
        let s = &v["secrets"][0];
        assert_eq!(s["id"], "db_creds");
        assert_eq!(s["issued_by"], "vault");
        assert_eq!(s["audience"][0], "api");
        assert_eq!(s["lifetime"]["value"], 24.0);
        assert_eq!(s["lifetime"]["unit"], "h");
        assert_eq!(s["revoke"]["value"], 5.0);
        assert_eq!(s["revoke"]["unit"], "min");
    }

    #[test]
    fn parses_secret_without_revoke_or_audience() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `revoke`/`audience` are grammar-optional -- the mandatory-
        // revocation rule fails closed in the elaborator
        // (`_secrets.py::_validate_secret_bounds`), not the parser.
        let v = ok(r#"module m
            node vault : trusted
            secret db_creds {
                issued_by vault;
                lifetime 24 h;
            }"#);
        let s = &v["secrets"][0];
        assert_eq!(s["audience"].as_array().unwrap().len(), 0);
        assert!(s["revoke"].is_null());
    }

    #[test]
    fn error_secret_requires_issued_by() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `issued_by` is mandatory -- a credential with no named
        // issuing authority is a dangling promise, never a silent default.
        let e = err(r#"module m
            secret db_creds {
                lifetime 24 h;
            }"#);
        assert_eq!(e["message"], "secret needs an issued_by clause");
    }

    #[test]
    fn parses_on_deploy_block() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `on deploy { canary { ... }; endorsed_by ...; rollback
        // within ... }` -- surface syntax for `_models.py::DeployContract`.
        let v = ok(r#"module m
            node api : trusted {
                on deploy {
                    canary { canary for 10 min, staged for 30 min };
                    endorsed_by review_gate, build_gate;
                    rollback within 5 min;
                }
            }"#);
        let d = &v["nodes"][0]["deploy"];
        assert_eq!(d["stages"][0]["level"], "canary");
        assert_eq!(d["stages"][0]["bake"]["value"], 10.0);
        assert_eq!(d["stages"][1]["level"], "staged");
        assert_eq!(d["endorsed_by"][0], "review_gate");
        assert_eq!(d["endorsed_by"][1], "build_gate");
        assert_eq!(d["rollback_budget"]["value"], 5.0);
        assert_eq!(d["rollback_budget"]["unit"], "min");
    }

    #[test]
    fn parses_node_without_on_deploy_defaults_null() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: pre-existing sources with no `on deploy` block must still
        // elaborate -- `deploy` defaults to null (no contract declared).
        let v = ok("module m\nnode api : trusted");
        assert!(v["nodes"][0]["deploy"].is_null());
    }

    #[test]
    fn error_on_deploy_requires_rollback_budget() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `rollback_budget` has no default on `DeployContract`
        // (mandatory containment bound, charter law 2) -- a deploy block
        // with no rollback clause is a parse error, not an empty default.
        let e = err(r#"module m
            node api : trusted {
                on deploy {
                    endorsed_by review_gate;
                }
            }"#);
        assert_eq!(
            e["message"],
            "on deploy block needs a rollback within QUANTITY clause"
        );
    }

    #[test]
    fn parses_node_managed_marker() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0172: `managed` is a bare marker on `node`, mirroring
        // `errors_total`'s shape -- config-only infra (e.g. a Caddyfile-
        // configured edge) declared with no `code=` glob.
        let v = ok(r#"module m
            node edge : trusted {
                managed;
            }"#);
        assert_eq!(v["nodes"][0]["is_managed"], true);
    }

    #[test]
    fn parses_node_without_managed_defaults_false() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0172: pre-existing sources with no `managed` clause must still
        // elaborate -- `is_managed` defaults to false.
        let v = ok("module m\nnode api : trusted");
        assert_eq!(v["nodes"][0]["is_managed"], false);
    }

    #[test]
    fn parses_store_managed_marker() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0172: `store` is a node too (docs/strata/surface.md
        // #key-construct-semantics) -- same bare `managed` marker.
        let v = ok(r#"module m
            store cache_db : trusted {
                managed;
            }"#);
        assert_eq!(v["stores"][0]["is_managed"], true);
    }

    #[test]
    fn parses_node_host_manifest_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0255: std.host vocabulary -- runs_as/unit/owns/listens on a
        // node (docs/strata/host.md).
        let v = ok(r#"module m
            node api : trusted {
                runs_as "api-svc";
                unit;
                owns "/etc/api" "0644";
                owns "/var/lib/api" "0750";
                listens 8080;
                listens 8443;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["runs_as"], "api-svc");
        assert_eq!(n["is_unit"], true);
        assert_eq!(n["owns"][0]["path"], "/etc/api");
        assert_eq!(n["owns"][0]["mode"], "0644");
        assert_eq!(n["owns"][1]["path"], "/var/lib/api");
        assert_eq!(n["owns"][1]["mode"], "0750");
        assert_eq!(n["listens"][0], 8080);
        assert_eq!(n["listens"][1], 8443);
    }

    #[test]
    fn parses_node_without_host_manifest_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0255: pre-existing sources with no std.host clause must still
        // elaborate -- runs_as null, is_unit false, owns/listens empty.
        let v = ok("module m\nnode api : trusted");
        let n = &v["nodes"][0];
        assert!(n["runs_as"].is_null());
        assert_eq!(n["is_unit"], false);
        assert_eq!(n["owns"].as_array().unwrap().len(), 0);
        assert_eq!(n["listens"].as_array().unwrap().len(), 0);
        assert_eq!(n["group"].as_array().unwrap().len(), 0);
        assert_eq!(n["sudoers"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_node_group_and_sudoers_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0272: std.host OS-group and sudoers-grant vocabulary on a node
        // (docs/strata/host.md) -- HOST001's shared-group and HOST002's
        // sudoers sub-targets read these back instead of always firing.
        let v = ok(r#"module m
            node api : trusted {
                runs_as "api-svc";
                group "deploy";
                group "docker";
                sudoers "ALL=(root) NOPASSWD: /bin/systemctl restart api";
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["group"][0], "deploy");
        assert_eq!(n["group"][1], "docker");
        assert_eq!(
            n["sudoers"][0],
            "ALL=(root) NOPASSWD: /bin/systemctl restart api"
        );
    }

    #[test]
    fn parses_node_windows_host_manifest_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261: std.host Windows vocabulary -- platform/service_account/
        // service/acl/pipe on a node (docs/strata/host.md#windows-surface-
        // grammar).
        let v = ok(r#"module m
            node api : trusted {
                platform "windows";
                service_account "svc-api" gmsa;
                service;
                acl "C:\ProgramData\api" "BUILTIN\Administrators:FullControl";
                pipe "\\.\pipe\api-control";
                listens 8443;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["platform"], "windows");
        assert_eq!(n["service_account"], "svc-api");
        assert_eq!(n["service_account_gmsa"], true);
        assert_eq!(n["is_service"], true);
        assert_eq!(n["acl"][0]["path"], "C:\\ProgramData\\api");
        assert_eq!(n["acl"][0]["rule"], "BUILTIN\\Administrators:FullControl");
        assert_eq!(n["pipes"][0], "\\\\.\\pipe\\api-control");
        assert_eq!(n["listens"][0], 8443);
    }

    #[test]
    fn parses_node_bin_path_clause() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0629: `bin_path "PATH" ["ARGS"]` desugars straight to
        // `bin_path=<path>` (+ `bin_path_args=<args>`) node attrs.
        let v = ok(r#"module m
            node api : trusted {
                platform "windows";
                service;
                bin_path "C:\Program Files\api\api.exe" "--config C:\ProgramData\api\config.yaml";
            }"#);
        let n = &v["nodes"][0];
        let attrs: Vec<&str> = n["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"bin_path=C:\\Program Files\\api\\api.exe"));
        assert!(attrs.contains(&"bin_path_args=--config C:\\ProgramData\\api\\config.yaml"));
    }

    #[test]
    fn parses_node_bin_path_clause_without_args() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0629: ARGS is optional -- `bin_path_args` is absent when omitted.
        let v = ok(r#"module m
            node api : trusted {
                platform "windows";
                service;
                bin_path "C:\Program Files\api\api.exe";
            }"#);
        let n = &v["nodes"][0];
        let attrs: Vec<&str> = n["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"bin_path=C:\\Program Files\\api\\api.exe"));
        assert!(!attrs.iter().any(|a| a.starts_with("bin_path_args=")));
    }

    #[test]
    fn parses_store_bin_path_clause() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0629: `store` accepts the identical `bin_path` clause -- a
        // store is a node too.
        let v = ok(r#"module m
            store api_svc : trusted {
                platform "windows";
                service;
                bin_path "C:\Program Files\api\api.exe" "--serve";
            }"#);
        let n = &v["stores"][0];
        let attrs: Vec<&str> = n["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"bin_path=C:\\Program Files\\api\\api.exe"));
        assert!(attrs.contains(&"bin_path_args=--serve"));
    }

    #[test]
    fn parses_node_without_windows_host_manifest_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261: pre-existing sources with no Windows std.host clause
        // must still elaborate -- platform/service_account null,
        // service_account_gmsa/is_service false, acl/pipes empty.
        let v = ok("module m\nnode api : trusted");
        let n = &v["nodes"][0];
        assert!(n["platform"].is_null());
        assert!(n["service_account"].is_null());
        assert_eq!(n["service_account_gmsa"], false);
        assert_eq!(n["is_service"], false);
        assert_eq!(n["acl"].as_array().unwrap().len(), 0);
        assert_eq!(n["pipes"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_store_windows_host_manifest_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261: same Windows std.host vocabulary on `store` -- a store
        // is a node too (docs/strata/surface.md#key-construct-semantics).
        let v = ok(r#"module m
            store cache_db : trusted {
                platform "windows";
                service_account "svc-cache";
                service;
                acl "D:\data\cache" "svc-cache:Modify";
                pipe "\\.\pipe\cache-control";
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["platform"], "windows");
        assert_eq!(s["service_account"], "svc-cache");
        assert_eq!(s["service_account_gmsa"], false);
        assert_eq!(s["is_service"], true);
        assert_eq!(s["acl"][0]["path"], "D:\\data\\cache");
        assert_eq!(s["acl"][0]["rule"], "svc-cache:Modify");
        assert_eq!(s["pipes"][0], "\\\\.\\pipe\\cache-control");
    }

    #[test]
    fn parses_store_host_manifest_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0255: same std.host vocabulary on `store` -- a store is a
        // node too (docs/strata/surface.md#key-construct-semantics).
        let v = ok(r#"module m
            store cache_db : trusted {
                runs_as "cache-svc";
                unit;
                owns "/var/lib/cache_db" "0700";
                listens 6379;
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["runs_as"], "cache-svc");
        assert_eq!(s["is_unit"], true);
        assert_eq!(s["owns"][0]["path"], "/var/lib/cache_db");
        assert_eq!(s["owns"][0]["mode"], "0700");
        assert_eq!(s["listens"][0], 6379);
        assert_eq!(s["group"].as_array().unwrap().len(), 0);
        assert_eq!(s["sudoers"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_store_group_and_sudoers_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0272: same `group`/`sudoers` shape as `node`'s clauses on a
        // `store` -- a store is a node too.
        let v = ok(r#"module m
            store cache_db : trusted {
                runs_as "cache-svc";
                group "dba";
                sudoers "cache-svc ALL=(root) /usr/bin/systemctl restart cache_db";
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["group"][0], "dba");
        assert_eq!(
            s["sudoers"][0],
            "cache-svc ALL=(root) /usr/bin/systemctl restart cache_db"
        );
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
        assert_eq!(s["errors_total"], false);
        assert_eq!(s["panics_contained_by"], serde_json::Value::Null);
        assert_eq!(s["observe"], serde_json::Value::Null);
        assert_eq!(s["deploy"], serde_json::Value::Null);
    }

    #[test]
    fn parses_store_errors_total_panics_and_observe() {
        // T-0247: store_prop now accepts the same errors_total/
        // panics_contained_by/observe node_prop entries `node` has.
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            store db : trusted {
                errors_total;
                panics_contained_by supervisor;
                observe { log error_paths, crash_events; to obs_sink }
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["errors_total"], true);
        assert_eq!(s["panics_contained_by"], "supervisor");
        assert_eq!(s["observe"]["log"][0], "error_paths");
        assert_eq!(s["observe"]["log"][1], "crash_events");
        assert_eq!(s["observe"]["to"], "obs_sink");
    }

    #[test]
    fn parses_store_on_deploy() {
        // T-0247: store_prop now accepts the same `on deploy { ... }`
        // node_prop entry `node` has.
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            store db : trusted {
                on deploy {
                    canary { authenticated for 10 min };
                    endorsed_by review_gate;
                    rollback within 5 min;
                }
            }"#);
        let d = &v["stores"][0]["deploy"];
        assert_eq!(d["stages"][0]["level"], "authenticated");
        assert_eq!(d["endorsed_by"][0], "review_gate");
        assert_eq!(d["rollback_budget"]["value"], 5.0);
    }

    #[test]
    fn error_store_observe_unknown_log_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nstore db : trusted { observe { bogus x; } }");
        assert_eq!(e["message"], "unknown observe property");
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
    fn parses_queue_with_explicit_trust() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0093: queue may now declare an explicit TRUST clause.
        let v = ok("module m\nqueue q : authenticated { delivery at_least_once; }");
        let q = &v["queues"][0];
        assert_eq!(q["id"], "q");
        assert_eq!(q["trust"], "authenticated");
        assert_eq!(q["delivery"], "at_least_once");
    }

    #[test]
    fn parses_queue_without_trust_defaults_to_null() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0093: omitting TRUST keeps parsing (backward compatible); the
        // elaborator (not the parser) supplies the "trusted" default.
        let v = ok("module m\nqueue q { delivery at_least_once; }");
        assert_eq!(v["queues"][0]["trust"], serde_json::Value::Null);
    }

    #[test]
    fn parses_bare_queue_with_trust() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nqueue q : authenticated");
        assert_eq!(v["queues"][0]["trust"], "authenticated");
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
        assert_eq!(v["balancers"][0]["trust"], serde_json::Value::Null);
    }

    #[test]
    fn parses_balancer_with_explicit_trust() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0093: balancer may now declare an explicit TRUST clause.
        let v = ok("module m\nbalancer b : authenticated { policy round_robin; }");
        let b = &v["balancers"][0];
        assert_eq!(b["id"], "b");
        assert_eq!(b["trust"], "authenticated");
        assert_eq!(b["policy"], "round_robin");
    }

    #[test]
    fn parses_bare_balancer_with_trust() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nbalancer b : authenticated");
        assert_eq!(v["balancers"][0]["trust"], "authenticated");
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
    fn parses_flow_utility() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0226: `utility;` desugars to the bare flow attr "utility".
        let v = ok("module m\nflow f1 : a -> b { utility; }");
        assert_eq!(v["flows"][0]["attrs"][0], "utility");
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

    // T-0700: `access "RESOURCE" mode MODE` node/store clause + `resource
    // ID { arbitrated_by NODE | lock "NAME" }` top-level construct.

    #[test]
    fn parses_node_access_clause() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node writer : trusted {
                access "ledger_db" mode write;
                access "cache_db" mode read;
            }"#);
        let n = &v["nodes"][0];
        let attrs: Vec<&str> = n["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"access=ledger_db:write"));
        assert!(attrs.contains(&"access=cache_db:read"));
    }

    #[test]
    fn parses_store_access_clause() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261 node/store symmetry: same `access` shape on `store`.
        let v = ok(r#"module m
            store ledger_db : trusted {
                access "ledger_db" mode exclusive;
            }"#);
        let s = &v["stores"][0];
        let attrs: Vec<&str> = s["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"access=ledger_db:exclusive"));
    }

    #[test]
    fn parses_all_access_modes() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node n : trusted {
                access "r" mode read;
                access "a" mode append;
                access "al" mode alpha;
                access "w" mode write;
                access "e" mode exclusive;
            }"#);
        let attrs: Vec<&str> = v["nodes"][0]["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        for expect in [
            "access=r:read",
            "access=a:append",
            "access=al:alpha",
            "access=w:write",
            "access=e:exclusive",
        ] {
            assert!(attrs.contains(&expect), "missing {expect:?} in {attrs:?}");
        }
    }

    #[test]
    fn error_access_rejects_unknown_mode() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node n : trusted {
                access "r" mode bogus;
            }"#);
        assert_eq!(
            e["message"],
            "access mode must be one of read|append|alpha|write|exclusive"
        );
    }

    #[test]
    fn error_access_requires_mode_keyword() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node n : trusted {
                access "r" write;
            }"#);
        assert_eq!(e["message"], "expected keyword \"mode\"");
    }

    #[test]
    fn parses_resource_with_arbitrated_by() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node writer : trusted { }
            resource ledger_db {
                arbitrated_by writer;
            }"#);
        let r = &v["resources"][0];
        assert_eq!(r["id"], "ledger_db");
        assert_eq!(r["arbitrated_by"], "writer");
        assert_eq!(r["lock"], serde_json::Value::Null);
    }

    #[test]
    fn parses_resource_with_lock() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            resource ledger_db {
                lock "ledger-lease";
            }"#);
        let r = &v["resources"][0];
        assert_eq!(r["id"], "ledger_db");
        assert_eq!(r["arbitrated_by"], serde_json::Value::Null);
        assert_eq!(r["lock"], "ledger-lease");
    }

    #[test]
    fn parses_bare_resource_with_no_arbiter() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nresource ledger_db");
        let r = &v["resources"][0];
        assert_eq!(r["id"], "ledger_db");
        assert_eq!(r["arbitrated_by"], serde_json::Value::Null);
        assert_eq!(r["lock"], serde_json::Value::Null);
    }

    #[test]
    fn error_resource_rejects_both_arbitrated_by_and_lock() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            resource ledger_db {
                arbitrated_by writer;
                lock "ledger-lease";
            }"#);
        assert_eq!(
            e["message"],
            "resource may declare at most one of arbitrated_by/lock"
        );
    }

    // T-0702: `users NUMBER` / `rate NUMBER UNIT` entry-demand clauses.

    #[test]
    fn parses_node_users_and_rate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node entry_a : trusted {
                users 300000;
                rate 500 req/s;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["users"], 300000.0);
        assert_eq!(n["rate"]["value"], 500.0);
        assert_eq!(n["rate"]["unit"], "req/s");
    }

    #[test]
    fn parses_node_without_users_or_rate_defaults_null() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nnode plain : trusted { }");
        let n = &v["nodes"][0];
        assert_eq!(n["users"], serde_json::Value::Null);
        assert_eq!(n["rate"], serde_json::Value::Null);
    }

    #[test]
    fn parses_node_users_only_no_rate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nnode entry_a : trusted { users 200000; }");
        let n = &v["nodes"][0];
        assert_eq!(n["users"], 200000.0);
        assert_eq!(n["rate"], serde_json::Value::Null);
    }

    #[test]
    fn parses_store_users_and_rate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261 node/store symmetry: same `users`/`rate` shape on `store`.
        let v = ok(r#"module m
            store db : trusted {
                users 500000;
                rate 1000 req/s;
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["users"], 500000.0);
        assert_eq!(s["rate"]["value"], 1000.0);
        assert_eq!(s["rate"]["unit"], "req/s");
    }

    #[test]
    fn parses_node_rate_does_not_collide_with_capacity_rate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // The top-level `rate` (T-0702 demand) and `capacity`'s own
        // nested rate quantity are independent fields.
        let v = ok(r#"module m
            node svc : trusted {
                rate 300 req/s;
                capacity 100 req/s replicas 1..3;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["rate"]["value"], 300.0);
        assert_eq!(n["capacity"]["rate"]["value"], 100.0);
    }
}
