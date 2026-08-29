// V-model surface-grammar productions (T-3042/T-3044, docs/strata/vmodel.md):
// `vmodel_node`/`vmodel_edge` statements -- declares one node/edge of the
// V-model spec graph (strata-core::graph::vmodel). Split out of
// `grammar_core.rs` (T-3260) once that file crossed the LARGE001
// threshold; spliced back into `Parser` via `include!` the same way as
// every other grammar-family fragment (see parse/mod.rs's module doc for
// why include! rather than a real child `mod`).
// frob:waive REF002 reason="a textually-included grammar-family fragment (see parse/mod.rs's own \
// module doc) is by design referenced from exactly one place, its sibling include! line in \
// parse/mod.rs -- same posture every other grammar_*.rs fragment in this directory has"

impl Parser {
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
    // frob:ticket T-3260
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
                attrs.insert(
                    "runnable".to_string(),
                    json!(self.expect_string("vmodel_node runnable")?),
                );
            } else if self.at_keyword("code_ref") {
                self.advance();
                attrs.insert(
                    "code_ref".to_string(),
                    json!(self.expect_string("vmodel_node code_ref")?),
                );
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
    // frob:ticket T-3260
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
            attrs.insert(
                "reason".to_string(),
                json!(self.expect_string("vmodel_edge reason")?),
            );
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
