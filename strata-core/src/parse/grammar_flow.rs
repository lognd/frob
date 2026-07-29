// Flow/boundary/operation grammar productions: `flow`, `boundary`,
// phase blocks, `operation`, and `refine` constructs (docs/strata/surface.md#parser).
// frob:waive REF002 reason="a T-1099 grammar-family split fragment of parse.rs, \
// imported only by parse/mod.rs's `mod` declaration by design -- the same package \
// structure every sibling parse/grammar_*.rs module has, a second consumer would not \
// be genuine"
// frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: T-1099 split \
// strata-core/src/parse.rs (whose single INV006 calibration-batch waiver, T-0585, is \
// preserved verbatim in parse/mod.rs) into grammar-family fragments; this file \
// inherits some of that same source-level design-rationale/scope-cut prose (a \
// docstring or comment describing already-implemented internal behavior, verifiable \
// by reading the code it annotates) rather than a separate cross-module contract \
// needing its own tracked invariant; disposed as the same calibration batch, not \
// claim-by-claim"

impl Parser {
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
}
