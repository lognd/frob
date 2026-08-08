// Parser core: `Parser`/`ModuleAst` definitions and the shared
// token-stream primitives (`expect_*`, `at_*`, `parse_unit`/`parse_quantity`)
// every grammar-family module builds on (docs/strata/surface.md#parser).

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

    // frob:waive DUP001 reason="pre-existing code relocated verbatim by T-1099s \
    // module split -- git shows the whole file as newly added since one file split \
    // into six, so the dup scanner treats this small, already-existing helper as \
    // fresh/new and re-flags its structural similarity to unrelated code that was \
    // never a real duplication before the split either; no behavior or code shape \
    // changed"
    // frob:waive DUP002 reason="same T-1099 relocation artifact as DUP001 above -- \
    // this method and its sibling both existed verbatim, side by side, in the \
    // pre-split monolithic parse.rs; the split did not introduce a new duplication, \
    // only a new file boundary the dup scanner reads as 'both new in this diff'"
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

    // frob:waive DUP001 reason="pre-existing code relocated verbatim by T-1099s \
    // module split -- git shows the whole file as newly added since one file split \
    // into six, so the dup scanner treats this small, already-existing helper as \
    // fresh/new and re-flags its structural similarity to unrelated code that was \
    // never a real duplication before the split either; no behavior or code shape \
    // changed"
    // frob:waive DUP002 reason="same T-1099 relocation artifact as DUP001 above -- \
    // this method and its sibling both existed verbatim, side by side, in the \
    // pre-split monolithic parse.rs; the split did not introduce a new duplication, \
    // only a new file boundary the dup scanner reads as 'both new in this diff'"
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
    // frob:waive DUP001 reason="pre-existing code relocated verbatim by T-1099s \
    // module split -- git shows the whole file as newly added since one file split \
    // into six, so the dup scanner treats this small, already-existing helper as \
    // fresh/new and re-flags its structural similarity to unrelated code that was \
    // never a real duplication before the split either; no behavior or code shape \
    // changed"
    // frob:waive DUP002 reason="same T-1099 relocation artifact as DUP001 above -- \
    // this method and its sibling both existed verbatim, side by side, in the \
    // pre-split monolithic parse.rs; the split did not introduce a new duplication, \
    // only a new file boundary the dup scanner reads as 'both new in this diff'"
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

    /// ATTRVAL := (IDENT | STRING) ['=' ((IDENT | STRING) | '[' (IDENT | STRING) (',' (IDENT | STRING))* ','? ']')].
    ///
    /// T-1198: the bracket-list form (`attr interface=[Foo, Bar, Baz];`) is
    /// pure surface-syntax sugar for N individual `key=value` attrs written
    /// on one line instead of N lines -- it expands HERE, at parse time,
    /// into the exact same `"key=value"` strings the single-value form
    /// produces (a trailing comma before `]` is accepted so a generator
    /// never has to special-case the last entry). No downstream consumer
    /// (`_elaborate.py`, `_sync_interface.py`, every gate that reads
    /// `Node.attrs`) needs to know this form exists -- the elaborated
    /// model is byte-for-byte identical either way, which is exactly the
    /// property that let this ship as a pure parser change (design/T-1198
    /// note, docs/strata/surface.md#compact-interface-attrs-t-1198).
    ///
    /// T-1325: `std.compliance`'s opaque-string vocabulary
    /// (`exposure:public-web`, `subject:*`, `jurisdiction:*`) needs `:` and
    /// `-`, which bare IDENT cannot lex (same gap `expect_ident_or_string`
    /// already documents for claim ids, T-0138). Both the attribute NAME
    /// and its VALUE(s) now accept a STRING-quoted alternate surface via
    /// `expect_ident_or_string`, mirroring that precedent exactly -- a
    /// STRING key/value elaborates to the identical `"key=value"` string an
    /// IDENT one would, so no downstream consumer needs to know which
    /// surface form was written. Existing bare-IDENT `.strata` source is
    /// unaffected: `expect_ident_or_string` still accepts IDENT first.
    fn parse_attrval(&mut self) -> Result<Vec<String>, ParseError> {
        let key = self.expect_ident_or_string("attribute name")?;
        if !self.at_symbol('=') {
            return Ok(vec![key]);
        }
        self.advance(); // '='
        if self.at_symbol('[') {
            self.advance(); // '['
            let mut values: Vec<String> = Vec::new();
            loop {
                if self.at_symbol(']') {
                    break;
                }
                let val = self.expect_ident_or_string("attribute value inside [..]")?;
                values.push(format!("{}={}", key, val));
                if self.at_symbol(',') {
                    self.advance();
                    continue;
                }
                break;
            }
            self.expect_symbol(']')?;
            Ok(values)
        } else {
            let val = self.expect_ident_or_string("attribute value after =")?;
            Ok(vec![format!("{}={}", key, val)])
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

    // frob:waive DUP001 reason="pre-existing code relocated verbatim by T-1099s \
    // module split -- git shows the whole file as newly added since one file split \
    // into six, so the dup scanner treats this small, already-existing helper as \
    // fresh/new and re-flags its structural similarity to unrelated code that was \
    // never a real duplication before the split either; no behavior or code shape \
    // changed"
    // frob:waive DUP002 reason="same T-1099 relocation artifact as DUP001 above -- \
    // this method and its sibling both existed verbatim, side by side, in the \
    // pre-split monolithic parse.rs; the split did not introduce a new duplication, \
    // only a new file boundary the dup scanner reads as 'both new in this diff'"
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
}
