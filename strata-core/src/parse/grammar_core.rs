// Parser core: `Parser`/`ModuleAst` definitions and the shared
// token-stream primitives (`expect_*`, `at_*`, `parse_unit`/`parse_quantity`)
// every grammar-family module builds on (docs/strata/surface.md#parser).

// frob:debt LARGE001 reason="T-3044 added parse_vmodel_node/parse_vmodel_edge \
// (V-model H3 grammar), pushing this file from ~795 to 827 lines against the 800-line \
// threshold" ticket="T-3260"
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
    // T-2502: `part of NAME` fragment header -- `None` for a root file
    // (declares `module NAME`, the closure boundary everything else in
    // this module is unchanged for); `Some(NAME)` for a fragment file,
    // which declares no module of its own and stands for nothing loaded
    // alone (docs/strata/surface.md#fragments-t-2502). `name` is left
    // empty for a fragment -- fragments do not name a module, only the
    // root they extend.
    part_of: Option<String>,
    // T-2502: `extend node ID { may "ATOM" via GLOB[, GLOB...]; ... }`
    // statements -- the ONLY statement shape a fragment file may contain.
    // Each entry mirrors `NodeDecl`'s `may_grants` shape narrowly (atom +
    // via only; no `exclusive`/`of`, no `clearance`/`capacity`/any other
    // node field) so a fragment is syntactically incapable of touching
    // anything but an already-existing grant's via-list scope --
    // structural, not documentary, enforcement of "extend-only, never
    // override" (docs/strata/surface.md#fragments-t-2502).
    extends: Vec<serde_json::Value>,
    // T-3006: entity/architecture/configuration (docs/strata/entity_architecture.md)
    // -- VHDL's entity/architecture/configuration split, T-3004 section 5.
    // `entity NAME { may "ATOM"; obligation "text"; }` declares the
    // BEHAVIOUR half (obligations + a may-ceiling, no implementation);
    // `architecture NAME of ENTITY { binds MODULE; }` declares which
    // MODULE's already-parsed node/flow/store body realizes that entity's
    // obligations (the IMPLEMENTATION half -- today's whole `.strata`
    // surface, unchanged); `configuration NAME { entity E; architecture
    // A; }` names which architecture is selected for an entity. Deliberately
    // single-file scope for this first slice: `of ENTITY`/`binds MODULE`
    // resolve only against entities/the module already parsed earlier in
    // THIS file, never across files -- see the module doc for why.
    entities: Vec<serde_json::Value>,
    architectures: Vec<serde_json::Value>,
    configurations: Vec<serde_json::Value>,
    // T-3042 (V-model H1 fix, docs/strata/vmodel.md): a minimal, additive
    // authoring surface for the V-model spec graph strata-core::graph::vmodel
    // already knows how to CHECK but that had no way for a human to WRITE
    // (vmodel_check had zero callers -- the epic could complete without ever
    // checking anything). `vmodel_node NAME kind "..." [level "..."];` and
    // `vmodel_edge kind "..." src NAME dst NAME;` are new, independent
    // top-level statement kinds -- no existing statement's grammar changes.
    // Deliberately NOT validated against cross-file references at parse
    // time (unlike entity/architecture's SYS300/301, which are legitimately
    // single-file): a real V-model spans many files (a requirement in one,
    // its verifying test in another), so `src`/`dst` existence is a GRAPH
    // question the kernel already answers correctly via
    // `Graph::add_node`/`add_edge`'s own `DanglingEndpoint` refusal once
    // frob.gates._vmodel aggregates every file's nodes/edges into one
    // graph -- duplicating that check per-file here would be actively
    // wrong for any legitimate cross-file edge.
    vmodel_nodes: Vec<serde_json::Value>,
    vmodel_edges: Vec<serde_json::Value>,
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

    /// T-2502: `part of NAME` -- a fragment file's ONLY header, declaring
    /// which root `module` it extends. Must be the very first statement
    /// (mirrors `parse_module`'s `seen_module` guard: `seen_module` is
    /// reused as "header already consumed" for both root and fragment
    /// files, so a file can never carry both a `module` and a `part of`
    /// header, nor two of either -- one file is exactly one thing.
    fn parse_part_of(
        &mut self,
        ast: &mut ModuleAst,
        seen_module: &mut bool,
    ) -> Result<(), ParseError> {
        if *seen_module {
            return self.err("duplicate module/part-of header");
        }
        self.advance(); // 'part'
        if !self.at_keyword("of") {
            return self.err("expected 'of' after 'part'");
        }
        self.advance(); // 'of'
        let name = self.expect_ident("root module name")?;
        ast.part_of = Some(name);
        *seen_module = true;
        Ok(())
    }

    /// T-2502: `extend node ID { may "ATOM" via GLOB[, GLOB...]; ... }` --
    /// the only statement a fragment file may contain. Deliberately
    /// accepts NO other node clause: no `clearance`, no `capacity`, no
    /// second `node`/`module` header -- a fragment cannot widen or
    /// override anything but an EXISTING grant's via-list, by
    /// construction of this grammar rule alone (docs/strata/surface.md
    /// #fragments-t-2502). A bare `may "ATOM";` with no `via` is a hard
    /// parse error here (unlike root `node`'s `may`, where a via-less
    /// grant means "whole node") -- an unscoped grant is not a widening
    /// of anything, it is a fresh whole-node bless, exactly what a
    /// fragment must never be able to do.
    fn parse_extend_node(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'extend'
        if !self.at_keyword("node") {
            return self.err("expected 'node' after 'extend' -- fragments may only extend nodes");
        }
        self.advance(); // 'node'
        let id = self.expect_ident("extend node id")?;
        self.expect_symbol('{')?;
        let mut may_grants: Vec<serde_json::Value> = Vec::new();
        loop {
            if self.at_symbol('}') {
                break;
            }
            if self.at_keyword("may") {
                self.advance();
                let atom = self.expect_string("may capability")?;
                let mut via: Vec<String> = Vec::new();
                if self.at_keyword("via") {
                    self.advance();
                    via.push(self.expect_string("may via glob")?);
                    while self.at_symbol(',') {
                        self.advance();
                        via.push(self.expect_string("may via glob")?);
                    }
                }
                if via.is_empty() {
                    return self.err(
                        "extend node may grant requires a via list -- a fragment may only \
                         widen an existing grant's scope, never bless the whole node",
                    );
                }
                may_grants.push(json!({
                    "atom": atom,
                    "via": via,
                    "exclusive": false,
                    "of": [],
                }));
                if self.at_symbol(';') {
                    self.advance();
                }
            } else {
                return self.err(
                    "extend node blocks may only contain 'may \"ATOM\" via ...' clauses -- \
                     clearance, capacity, and every other node field belong to the root \
                     declaration only and can never be widened or overridden by a fragment",
                );
            }
        }
        self.expect_symbol('}')?;
        ast.extends.push(json!({
            "id": id,
            "may_grants": may_grants,
        }));
        Ok(())
    }

    /// T-3006: `entity NAME { may "ATOM"; obligation "text"; }` -- the
    /// BEHAVIOUR half. `may` here is a FLAT ceiling atom (no `via`/`of`
    /// scoping -- that belongs to node-level grants inside an
    /// implementation), and `obligation` is a free-text declarative
    /// requirement: not machine-checkable content, but its EXISTENCE is
    /// what the closure rules in docs/strata/entity_architecture.md
    /// check for (T-3004 section 2: structural closure, not quality).
    fn parse_entity(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'entity'
        let name = self.expect_ident("entity name")?;
        if ast.entities.iter().any(|e| e["name"] == json!(name)) {
            return self.err(format!("duplicate entity {:?}", name));
        }
        self.expect_symbol('{')?;
        let mut may: Vec<String> = Vec::new();
        let mut obligations: Vec<String> = Vec::new();
        while !self.at_symbol('}') {
            if self.at_keyword("may") {
                self.advance();
                may.push(self.expect_string("entity may capability")?);
            } else if self.at_keyword("obligation") {
                self.advance();
                obligations.push(self.expect_string("entity obligation text")?);
            } else {
                return self.err("expected 'may' or 'obligation' inside entity block");
            }
            if self.at_symbol(';') {
                self.advance();
            }
        }
        self.expect_symbol('}')?;
        if obligations.is_empty() {
            return self.err(format!(
                "entity {:?} declares no obligations -- an entity with no obligation is not a \
                 behaviour contract, it is an empty block; declare at least one 'obligation \"...\"'",
                name
            ));
        }
        ast.entities.push(json!({
            "name": name,
            "may": may,
            "obligations": obligations,
        }));
        Ok(())
    }

    /// T-3006: `architecture NAME of ENTITY { binds MODULE; }` -- the
    /// IMPLEMENTATION half. `of ENTITY` must name an entity already
    /// declared earlier in THIS file (SYS300: undeclared entity, single-
    /// file scope for this slice); `binds MODULE` must name THIS file's
    /// own `module` (SYS301: an architecture cannot claim to realize a
    /// module it does not contain -- cross-file binding is future work).
    /// Refuses (SYS302, the shrink-only ratchet carried into this model,
    /// T-2920/T-2922) if any node in the bound module grants a `may` atom
    /// the entity's ceiling never declared -- an architecture may realize
    /// a SUBSET of its entity's ceiling, never exceed it, and this is
    /// never auto-widened.
    fn parse_architecture(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'architecture'
        let name = self.expect_ident("architecture name")?;
        if ast.architectures.iter().any(|a| a["name"] == json!(name)) {
            return self.err(format!("duplicate architecture {:?}", name));
        }
        if !self.at_keyword("of") {
            return self.err("expected 'of ENTITY' after architecture name");
        }
        self.advance(); // 'of'
        let entity_name = self.expect_ident("entity name")?;
        let entity = ast
            .entities
            .iter()
            .find(|e| e["name"] == json!(entity_name))
            .cloned()
            .ok_or_else(|| {
                let t = self.cur();
                ParseError {
                    line: t.line,
                    col: t.col,
                    message: format!(
                        "architecture {:?} references undeclared entity {:?} -- an entity must \
                         be declared earlier in this file before an architecture can bind it \
                         (SYS300)",
                        name, entity_name
                    ),
                }
            })?;
        self.expect_symbol('{')?;
        let mut binds: Option<String> = None;
        while !self.at_symbol('}') {
            if self.at_keyword("binds") {
                self.advance();
                let module_name = self.expect_ident("bound module name")?;
                if module_name != ast.name {
                    return self.err(format!(
                        "architecture {:?} binds module {:?}, but this file's own module is \
                         {:?} -- an architecture may only bind the module declared in its own \
                         file (cross-file binding is not yet supported, SYS301)",
                        name, module_name, ast.name
                    ));
                }
                binds = Some(module_name);
            } else {
                return self.err("expected 'binds MODULE' inside architecture block");
            }
            if self.at_symbol(';') {
                self.advance();
            }
        }
        self.expect_symbol('}')?;
        let binds = binds.ok_or_else(|| {
            let t = self.cur();
            ParseError {
                line: t.line,
                col: t.col,
                message: format!(
                    "architecture {:?} declares no 'binds MODULE' -- an architecture with \
                     nothing bound realizes no implementation",
                    name
                ),
            }
        })?;

        let ceiling: BTreeSet<String> = entity["may"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(|v| v.as_str().map(str::to_string))
            .collect();
        for node in &ast.nodes {
            let node_id = node["id"].as_str().unwrap_or("<unknown>");
            for atom in node["may"].as_array().into_iter().flatten() {
                let atom = atom.as_str().unwrap_or_default();
                if !ceiling.contains(atom) {
                    return self.err(format!(
                        "architecture {:?} (binding module {:?}) grants may \"{}\" on node {:?}, \
                         which exceeds entity {:?}'s may ceiling {:?} -- an architecture may only \
                         realize a SUBSET of its entity's ceiling, never widen it (SYS302, the \
                         shrink-only ratchet, T-2920/T-2922)",
                        name, binds, atom, node_id, entity_name, ceiling
                    ));
                }
            }
        }

        ast.architectures.push(json!({
            "name": name,
            "of_entity": entity_name,
            "binds": binds,
        }));
        Ok(())
    }

    /// T-3006: `configuration NAME { entity E; architecture A; }` -- names
    /// which architecture is currently selected to satisfy which entity.
    /// Refuses if either name is undeclared, or if the named architecture
    /// does not actually bind the named entity (SYS303) -- a configuration
    /// cannot silently pair mismatched halves. Milestone/partial-closure
    /// semantics (T-3004 section 6) are deferred; this is the plain
    /// selection edge they will build on.
    fn parse_configuration(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'configuration'
        let name = self.expect_ident("configuration name")?;
        if ast.configurations.iter().any(|c| c["name"] == json!(name)) {
            return self.err(format!("duplicate configuration {:?}", name));
        }
        self.expect_symbol('{')?;
        let mut entity_name: Option<String> = None;
        let mut arch_name: Option<String> = None;
        while !self.at_symbol('}') {
            if self.at_keyword("entity") {
                self.advance();
                entity_name = Some(self.expect_ident("configuration entity name")?);
            } else if self.at_keyword("architecture") {
                self.advance();
                arch_name = Some(self.expect_ident("configuration architecture name")?);
            } else {
                return self.err("expected 'entity NAME' or 'architecture NAME' inside configuration block");
            }
            if self.at_symbol(';') {
                self.advance();
            }
        }
        self.expect_symbol('}')?;
        let entity_name = match entity_name {
            Some(v) => v,
            None => return self.err("configuration missing 'entity NAME'"),
        };
        let arch_name = match arch_name {
            Some(v) => v,
            None => return self.err("configuration missing 'architecture NAME'"),
        };
        if !ast.entities.iter().any(|e| e["name"] == json!(entity_name)) {
            return self.err(format!(
                "configuration {:?} references undeclared entity {:?}",
                name, entity_name
            ));
        }
        let arch = ast
            .architectures
            .iter()
            .find(|a| a["name"] == json!(arch_name))
            .cloned()
            .ok_or_else(|| {
                let t = self.cur();
                ParseError {
                    line: t.line,
                    col: t.col,
                    message: format!(
                        "configuration {:?} references undeclared architecture {:?}",
                        name, arch_name
                    ),
                }
            })?;
        if arch["of_entity"] != json!(entity_name) {
            return self.err(format!(
                "configuration {:?} pairs architecture {:?} with entity {:?}, but {:?} is \
                 declared 'of {}' -- a configuration cannot pair mismatched halves (SYS303)",
                name, arch_name, entity_name, arch_name, arch["of_entity"]
            ));
        }
        ast.configurations.push(json!({
            "name": name,
            "entity": entity_name,
            "architecture": arch_name,
        }));
        Ok(())
    }

    /// T-3042: `vmodel_node NAME kind "artifact" [level "requirements"];`
    /// -- declares one node of the V-model spec graph
    /// (strata-core::graph::vmodel, docs/strata/vmodel.md). `kind` is a
    /// free-form string here (not validated against
    /// `KIND_ARTIFACT`/`KIND_TEST`/`KIND_DECISION` at parse time -- that
    /// validation is the KERNEL's job, at `Graph::add_node` time, once
    /// `frob.gates._vmodel` builds the real graph; duplicating a schema
    /// check here would drift from the schema's actual source of truth).
    /// `level` is optional (a `decision` node has none). Only a same-file
    /// duplicate NAME is refused here -- see the module-doc note on
    /// `vmodel_nodes`/`vmodel_edges` for why cross-file identity is not
    /// checked at this layer.
    fn parse_vmodel_node(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'vmodel_node'
        let name = self.expect_ident("vmodel_node name")?;
        if ast.vmodel_nodes.iter().any(|n| n["name"] == json!(name)) {
            return self.err(format!("duplicate vmodel_node {:?} in this file", name));
        }
        if !self.at_keyword("kind") {
            return self.err("expected 'kind \"...\"' after vmodel_node name");
        }
        self.advance(); // 'kind'
        let kind = self.expect_string("vmodel_node kind")?;
        let mut level: Option<String> = None;
        if self.at_keyword("level") {
            self.advance();
            level = Some(self.expect_string("vmodel_node level")?);
        }
        // T-3044 H3: `runnable "..."` / `code_ref "..."` are the payload
        // attrs `graph::vmodel` requires on `test`/`artifact` nodes
        // respectively (`graph::vmodel::ATTR_RUNNABLE`/`ATTR_CODE_REF`).
        // Both are optional HERE (this is only the surface grammar -- the
        // KERNEL is what refuses a node missing the one its kind
        // requires, at `frob.gates._vmodel` graph-assembly time); either
        // may appear, in any order, same loop shape as the `level` clause
        // above generalized to zero-or-more.
        let mut attrs = serde_json::Map::new();
        loop {
            if self.at_keyword("runnable") {
                self.advance();
                attrs.insert("runnable".to_string(), json!(self.expect_string("vmodel_node runnable")?));
            } else if self.at_keyword("code_ref") {
                self.advance();
                attrs.insert("code_ref".to_string(), json!(self.expect_string("vmodel_node code_ref")?));
            } else {
                break;
            }
        }
        if self.at_symbol(';') {
            self.advance();
        }
        ast.vmodel_nodes.push(json!({
            "name": name,
            "kind": kind,
            "level": level,
            "attrs": attrs,
        }));
        Ok(())
    }

    /// T-3042: `vmodel_edge kind "satisfies" src NAME dst NAME;` -- one
    /// edge of the V-model spec graph. `src`/`dst` are plain identifiers,
    /// deliberately NOT resolved against `ast.vmodel_nodes` here (a real
    /// V-model spans many files; the kernel's own `DanglingEndpoint`
    /// refusal is what catches a genuinely undeclared endpoint, once
    /// `frob.gates._vmodel` has aggregated every file's declarations into
    /// one graph -- see the `vmodel_nodes` field doc for the full reasoning).
    fn parse_vmodel_edge(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'vmodel_edge'
        if !self.at_keyword("kind") {
            return self.err("expected 'kind \"...\"' after vmodel_edge");
        }
        self.advance(); // 'kind'
        let kind = self.expect_string("vmodel_edge kind")?;
        if !self.at_keyword("src") {
            return self.err("expected 'src NAME' after vmodel_edge kind");
        }
        self.advance(); // 'src'
        let src = self.expect_ident("vmodel_edge src")?;
        if !self.at_keyword("dst") {
            return self.err("expected 'dst NAME' after vmodel_edge src");
        }
        self.advance(); // 'dst'
        let dst = self.expect_ident("vmodel_edge dst")?;
        // T-3044 H3: `reason "..."` is the payload attr `graph::vmodel`
        // requires on `supersedes` edges (`graph::vmodel::ATTR_REASON`) --
        // the change justification T-3004 section 8 asks for. Optional
        // here for the same reason `runnable`/`code_ref` are optional on
        // `vmodel_node` above: the kernel is the enforcement point.
        let mut attrs = serde_json::Map::new();
        if self.at_keyword("reason") {
            self.advance();
            attrs.insert("reason".to_string(), json!(self.expect_string("vmodel_edge reason")?));
        }
        if self.at_symbol(';') {
            self.advance();
        }
        ast.vmodel_edges.push(json!({
            "kind": kind,
            "src": src,
            "dst": dst,
            "attrs": attrs,
        }));
        Ok(())
    }
}
