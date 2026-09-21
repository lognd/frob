// T-5125: module-system grammar -- `import a.b as c;` and
// `export { node X; channel Y; label Z; }`. Parse-only (docs/strata/
// surface.md#module-system): the AST carries these records through
// unchanged; nothing resolves or checks them here (that is
// T-draft-9d041fdf's elaborator/resolver job).
// frob:ticket T-5125

impl Parser {
    /// `layer N;` -- D-M9's hierarchy-position declaration (owner ruling
    /// 2026-09-19 19:30, tickets/T-draft-0bcabfa4): a module names its rank
    /// in the explicit module hierarchy, a plain integer where a LOWER
    /// number is HIGHER (`platform` is layer 0). At most one per file --
    /// the caller passes `seen_layer` and refuses a second declaration,
    /// same "one closure root" shape `parse_module`'s own `seen_module`
    /// guard already uses. Import-direction/accepts-direction enforcement
    /// against this value is T-draft-27d3ece1's linker job, not this
    /// parser's: parse-only means the number is carried through and
    /// nothing more.
    fn parse_layer(&mut self, ast: &mut ModuleAst, seen_layer: &mut bool) -> Result<(), ParseError> {
        if *seen_layer {
            return self.err("duplicate layer statement");
        }
        self.advance(); // 'layer'
        let n = self.expect_int("layer rank")?;
        ast.layer = Some(n);
        *seen_layer = true;
        if self.at_symbol(';') {
            self.advance();
        }
        Ok(())
    }

    /// D-M9: `accepts FLOW from MODULE` names its peer BY REFERENCE, never
    /// by an import alias -- the whole point of `accepts` is that the
    /// upper module can name a lower one without importing it, so writing
    /// an alias there (naming THIS file's own local import binding
    /// instead of the real module path) would silently couple `accepts`
    /// to whether an import happens to exist, defeating the rule. This
    /// walks every parsed `accepts` clause after the whole file is parsed
    /// (imports may be declared anywhere relative to node bodies in this
    /// grammar, so the check cannot run any earlier than "the file is
    /// done") and refuses any `from` target that exactly matches one of
    /// THIS file's own import aliases.
    fn check_accepts_are_not_aliases(&self, ast: &ModuleAst) -> Result<(), ParseError> {
        let aliases: std::collections::BTreeSet<&str> = ast
            .imports
            .iter()
            .filter_map(|i| i.get("alias").and_then(|v| v.as_str()))
            .collect();
        for node in &ast.nodes {
            let Some(accepts) = node.get("accepts").and_then(|v| v.as_array()) else {
                continue;
            };
            for entry in accepts {
                if let Some(from) = entry.get("from").and_then(|v| v.as_str()) {
                    if aliases.contains(from) {
                        return self.err(format!(
                            "accepts \"{}\" from \"{}\" names an import alias, not a module \
                             path -- accepts must reference the peer module by its real \
                             dotted path, never by an alias bound in this file's own import",
                            entry.get("flow").and_then(|v| v.as_str()).unwrap_or(""),
                            from
                        ));
                    }
                }
            }
        }
        Ok(())
    }

    /// `import a.b as c;` -- one dotted module path bound to a mandatory
    /// local alias. No wildcard form exists anywhere in this grammar: `*`
    /// is not a lexable character at all (see `parse_dotted_path`'s doc),
    /// so `import a.*` fails at the lexer, and there is no re-export
    /// spelling either -- an alias names only this file's own local
    /// binding, never a name other files can see through it.
    fn parse_import(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'import'
        let path = self.parse_dotted_path("import module path")?;
        self.expect_keyword("as")?;
        let alias = self.expect_ident("import alias")?;
        ast.imports.push(json!({
            "path": path,
            "alias": alias,
        }));
        // Top-level statements in this grammar are not semicolon-terminated
        // (`module`/`node`/`flow` all omit a trailing `;`, docs/strata/
        // surface.md#grammar-sketch) but a trailing `;` after `import ...
        // as c` reads naturally and appears in the ticket's own examples,
        // so it is accepted and discarded here if present -- optional,
        // never required, matching the top-level dispatch loop's total
        // silence on `;` for every other construct.
        if self.at_symbol(';') {
            self.advance();
        }
        Ok(())
    }

    /// `export { node X; channel Y; label Z; }` -- the module's export
    /// surface, one entry per exported symbol. An absent or empty block is
    /// legal and means a fully private module (D-M1): this production is
    /// only reached when the `export` keyword itself is present, so the
    /// "absent" case is simply this function never being called, and the
    /// "empty" case is the `{}` loop below producing zero entries -- both
    /// leave `ast.exports` at its `Vec::new()` default.
    fn parse_export(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'export'
        self.expect_symbol('{')?;
        loop {
            if self.at_symbol('}') {
                break;
            }
            let kind = match self.peek_ident() {
                Some("node") | Some("channel") | Some("label") => {
                    self.peek_ident().unwrap().to_string()
                }
                _ => {
                    return self.err(
                        "export block entries must start with 'node', 'channel', or 'label'",
                    )
                }
            };
            self.advance(); // kind keyword
            let name = self.expect_ident("export entry name")?;
            ast.exports.push(json!({
                "kind": kind,
                "name": name,
            }));
            if self.at_symbol(';') {
                self.advance();
            }
        }
        self.expect_symbol('}')?;
        Ok(())
    }
}
