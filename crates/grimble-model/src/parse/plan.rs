//! Parsing of the planning items (grmb-spec 11.1): contextual words are recognised by position.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6
// frob:ticket 01M6CFZKEKAJM0YF9FB5820W3Y

use crate::ast::{Ident, RefPath, Spanned};
use crate::keywords::is_planning_word;
use crate::lex::{Punct, Tok};
use crate::plan::{
    Actor, Ambient, Arm, Chain, Debt, DebtKey, Elem, GoalBlock, Handle, Hop, Impl, ImplTarget,
    OneOf, Outcome, PClause, PClauseKind, Page, Pattern, PlanItem, Policy, Realization, ScMember,
    Scenario, Step, System, Tail, Variant, Verified, Waypoint, WaypointMap,
};
use crate::span::{Diagnostic, Span};

use super::{MAX_NESTING, PResult, ParseErr, Parser, fail};

/// The kind of planning body a clause is parsed in.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Host {
    System,
    Actor,
    Variant,
    Step,
    Scenario,
    Impl,
    Page,
    /// The body of an `ambient` or a waypoint: `verified_by` only.
    Leaf,
}

impl Host {
    fn allows_verified(self) -> bool {
        !matches!(self, Self::Actor | Self::Step)
    }

    fn allows_realization(self) -> bool {
        matches!(self, Self::Impl | Self::Page)
    }
}

/// The words every planning body shares: `title`, `verified_by` and the common clauses.
const COMMON_WORDS: [&str; 6] = ["alias", "renamed_from", "attr", "accept", "defer", "hotfix"];

impl Parser<'_> {
    /// Parses one planning item whose head word (already checked) is at the cursor.
    pub(super) fn plan_item(&mut self, word: &str) -> PResult<PlanItem> {
        tracing::trace!(word, "planning item");
        match word {
            "system" => self.system().map(PlanItem::System),
            "actor" => self.actor().map(PlanItem::Actor),
            "goal" => self.goal().map(PlanItem::Goal),
            "step" => self.step().map(PlanItem::Step),
            "scenario" => self.scenario().map(PlanItem::Scenario),
            "impl" => self.impl_item().map(PlanItem::Impl),
            _ => self.page().map(PlanItem::Page),
        }
    }

    fn finish(
        &mut self,
        start: Span,
        end: Span,
        head_end: usize,
        close: Option<usize>,
    ) -> (usize, Span) {
        let id = self.id();
        let span = start.to(end);
        self.register(id, span.start, head_end, span.end, close);
        (id, span)
    }

    /// Either `;` (returns `None`) or a braced body parsed by `body` (returns the close token).
    fn semi_or_body(
        &mut self,
        host: Host,
        out: &mut Vec<PClause>,
    ) -> PResult<(bool, Span, usize, Option<usize>)> {
        if self.at_p(Punct::Semi) {
            let semi = self.bump();
            return Ok((false, semi.span, semi.span.end, None));
        }
        let open = self.expect_p(Punct::LBrace)?;
        self.pclauses(host, out);
        let close = self.expect_p(Punct::RBrace)?;
        Ok((true, close.span, open.span.end, Some(close.span.start)))
    }

    fn system(&mut self) -> PResult<System> {
        let start = self.bump().span;
        if self.depth >= MAX_NESTING {
            return fail(start, format!("systems nest at most {MAX_NESTING} deep"));
        }
        let name = self.name("a system name")?;
        let mut clauses = Vec::new();
        let mut items = Vec::new();
        if self.at_p(Punct::Semi) {
            let semi = self.bump();
            let (id, span) = self.finish(start, semi.span, semi.span.end, None);
            return Ok(System {
                id,
                name,
                braced: false,
                items,
                clauses,
                span,
            });
        }
        let open = self.expect_p(Punct::LBrace)?;
        self.depth += 1;
        while !self.at_p(Punct::RBrace) && !self.at_eof() {
            let pos = self.pos;
            if self.at_system_clause() {
                self.pclause_into(Host::System, &mut clauses);
            } else {
                let item = self.item();
                items.push(item);
            }
            if self.pos == pos && !self.at_eof() {
                self.bump();
            }
        }
        self.depth -= 1;
        let close = self.expect_p(Punct::RBrace)?;
        let (id, span) = self.finish(start, close.span, open.span.end, Some(close.span.start));
        Ok(System {
            id,
            name,
            braced: true,
            items,
            clauses,
            span,
        })
    }

    /// True when the cursor is on a clause of the system itself rather than on an item.
    fn at_system_clause(&self) -> bool {
        matches!(&self.peek().tok, Tok::Ident(w)
            if w == "title" || w == "verified_by" || w == "ambient" || w == "non_goal"
                || COMMON_WORDS.contains(&w.as_str()))
    }

    fn actor(&mut self) -> PResult<Actor> {
        let start = self.bump().span;
        let name = self.name("an actor name")?;
        self.expect_p(Punct::Colon)?;
        let kind = self.any_ident("an actor kind")?;
        let mut clauses = Vec::new();
        let (braced, end, head_end, close) = self.semi_or_body(Host::Actor, &mut clauses)?;
        let (id, span) = self.finish(start, end, head_end, close);
        Ok(Actor {
            id,
            name,
            kind,
            braced,
            clauses,
            span,
        })
    }

    fn goal(&mut self) -> PResult<GoalBlock> {
        let start = self.bump().span;
        let path = self.ref_path("an actor or goal")?;
        let mut key = if self.at_kw("as") {
            let kw = self.bump();
            let key = self.any_ident("a dimension key")?;
            tracing::debug!(span = %kw.span, "bridged `goal P as K` spelling; reporting MDL012");
            self.diags.push(Diagnostic::new(
                "MDL012",
                kw.span.to(key.span),
                format!(
                    "`goal P as {}` is a deprecated spelling; write `attr dimension = {};` in the block (grmb-spec 11.1)",
                    key.text, key.text
                ),
            ));
            Some(key)
        } else {
            None
        };
        let open = self.expect_p(Punct::LBrace)?;
        let mut variants = Vec::new();
        let mut groups = Vec::new();
        while !self.at_p(Punct::RBrace) && !self.at_eof() {
            let pos = self.pos;
            let s = self.peek().span;
            let parsed = if self.at_dimension_attr() {
                // `attr dimension = KEY;` names the dimension (grmb-spec 11.4)
                self.dimension_attr().map(|k| {
                    tracing::debug!(key = %k.text, "goal dimension attr");
                    key = Some(k);
                })
            } else if self.at_one_of() {
                self.one_of().map(|g| groups.push(g))
            } else {
                self.variant().map(|v| variants.push(v))
            };
            match parsed {
                Ok(()) => {}
                Err(e) => {
                    self.hole_diag(&e);
                    if self.pos == pos && self.at_p(Punct::Semi) {
                        self.bump();
                    }
                    self.resync(true);
                    let _ = s;
                }
            }
            if self.pos == pos && !self.at_p(Punct::RBrace) && !self.at_eof() {
                self.bump();
            }
        }
        let close = self.expect_p(Punct::RBrace)?;
        let (id, span) = self.finish(start, close.span, open.span.end, Some(close.span.start));
        Ok(GoalBlock {
            id,
            path,
            key,
            variants,
            groups,
            span,
        })
    }

    /// True on `attr dimension` (the spec spelling of a goal block's dimension key).
    fn at_dimension_attr(&self) -> bool {
        self.at_kw("attr") && matches!(&self.peek_n(1).tok, Tok::Ident(w) if w == "dimension")
    }

    /// `attr dimension = KEY;`
    fn dimension_attr(&mut self) -> PResult<Ident> {
        self.bump();
        self.bump();
        self.expect_p(Punct::Eq)?;
        let key = self.any_ident("a dimension key")?;
        self.expect_p(Punct::Semi)?;
        Ok(key)
    }

    /// True on `one_of` followed by `{` or `exclusive` (a variant may still be named `one_of`).
    fn at_one_of(&self) -> bool {
        self.at_kw("one_of")
            && (self.peek_n(1).tok == Tok::P(Punct::LBrace)
                || matches!(&self.peek_n(1).tok, Tok::Ident(w) if w == "exclusive"))
    }

    /// `one_of [exclusive] { variant ... }`
    fn one_of(&mut self) -> PResult<OneOf> {
        let start = self.bump().span;
        let exclusive = self.eat_kw("exclusive");
        let open = self.expect_p(Punct::LBrace)?;
        let mut variants = Vec::new();
        while !self.at_p(Punct::RBrace) && !self.at_eof() {
            let pos = self.pos;
            match self.variant() {
                Ok(v) => variants.push(v),
                Err(e) => {
                    self.hole_diag(&e);
                    if self.pos == pos && self.at_p(Punct::Semi) {
                        self.bump();
                    }
                    self.resync(true);
                }
            }
            if self.pos == pos && !self.at_p(Punct::RBrace) && !self.at_eof() {
                self.bump();
            }
        }
        let close = self.expect_p(Punct::RBrace)?;
        tracing::debug!(exclusive, variants = variants.len(), "one_of group");
        let (id, span) = self.finish(start, close.span, open.span.end, Some(close.span.start));
        Ok(OneOf {
            id,
            exclusive,
            variants,
            span,
        })
    }

    fn variant(&mut self) -> PResult<Variant> {
        let start = self.peek().span;
        let name = self.name("a goal variant name")?;
        let mut requires = Vec::new();
        if self.eat_kw("requires") {
            loop {
                requires.push(self.ref_path("a goal")?);
                if !self.eat_p(Punct::Comma) {
                    break;
                }
            }
        }
        let mut clauses = Vec::new();
        let (braced, end, head_end, close) = self.semi_or_body(Host::Variant, &mut clauses)?;
        let (id, span) = self.finish(start, end, head_end, close);
        Ok(Variant {
            id,
            name,
            requires,
            braced,
            clauses,
            span,
        })
    }

    fn step(&mut self) -> PResult<Step> {
        let start = self.bump().span;
        let target = self.ref_path("a step name")?;
        let outcome = if self.eat_p(Punct::Colon) {
            // cycle 1: `step S : [closed|open] { .. }` (grmb-spec 11.5)
            if self.eat_kw("open") {
                tracing::debug!("step outcome set marked `open`; the AST has no slot for it yet");
            } else {
                self.eat_kw("closed");
            }
            Some(self.outcome()?)
        } else if self.at_p(Punct::Arrow) {
            let arrow = self.bump();
            tracing::debug!("bridged `step S -> {{ .. }}` spelling");
            self.diags.push(Diagnostic::new(
                "MDL012",
                arrow.span,
                "`step S -> { .. }` is a deprecated spelling; write `step S : { .. }` (grmb-spec 11.1)",
            ));
            Some(self.outcome()?)
        } else {
            None
        };
        while self.eat_kw("idempotent") {
            tracing::debug!("`idempotent` marker; the AST has no slot for it yet");
        }
        let mut clauses = Vec::new();
        let (braced, end, head_end, close) = self.semi_or_body(Host::Step, &mut clauses)?;
        let (id, span) = self.finish(start, end, head_end, close);
        Ok(Step {
            id,
            target,
            outcome,
            braced,
            clauses,
            span,
        })
    }

    fn outcome(&mut self) -> PResult<Vec<Outcome>> {
        self.expect_p(Punct::LBrace)?;
        let mut out = Vec::new();
        while !self.at_p(Punct::RBrace) {
            let name = self.name("an outcome variant")?;
            let payload = if self.eat_p(Punct::LParen) {
                let p = self.ref_path("a contract")?;
                self.expect_p(Punct::RParen)?;
                Some(p)
            } else {
                None
            };
            out.push(Outcome { name, payload });
            if !self.eat_p(Punct::Comma) {
                break;
            }
        }
        self.expect_p(Punct::RBrace)?;
        Ok(out)
    }

    fn scenario(&mut self) -> PResult<Scenario> {
        let start = self.bump().span;
        let name = self.name("a scenario name")?;
        let mut realizes = Vec::new();
        if self.eat_kw("realizes") {
            loop {
                realizes.push(self.ref_path("a goal")?);
                if !self.eat_p(Punct::Comma) {
                    break;
                }
            }
        }
        let fails = if self.eat_kw("fails") {
            self.expect_kw("with")?;
            self.expect_p(Punct::LBrace)?;
            let mut names = Vec::new();
            while !self.at_p(Punct::RBrace) {
                names.push(self.name("an error variant")?);
                if !self.eat_p(Punct::Comma) {
                    break;
                }
            }
            self.expect_p(Punct::RBrace)?;
            Some(names)
        } else {
            None
        };
        // frob:ticket 01M6BYK3QNNF0WHQW2Y0Q2TMVM
        if self.at_kw("sorry") {
            // whole-body hole: the body is one `sorry` terminal chain (grmb-spec 15.3)
            let head_end = self.peek().span.start;
            let (cid, chain) = self.chain_stmt()?;
            let end = chain.span;
            let (id, span) = self.finish(start, end, head_end, None);
            tracing::debug!("whole-body sorry scenario");
            return Ok(Scenario {
                id,
                name,
                realizes,
                fails,
                members: vec![ScMember::Chain(cid, chain)],
                span,
            });
        }
        let open = self.expect_p(Punct::LBrace)?;
        let mut members = Vec::new();
        while !self.at_p(Punct::RBrace) && !self.at_eof() {
            let pos = self.pos;
            let s = self.peek().span;
            self.scenario_member(&mut members);
            let _ = s;
            if self.pos == pos && !self.at_p(Punct::RBrace) && !self.at_eof() {
                self.bump();
            }
        }
        let close = self.expect_p(Punct::RBrace)?;
        let (id, span) = self.finish(start, close.span, open.span.end, Some(close.span.start));
        Ok(Scenario {
            id,
            name,
            realizes,
            fails,
            members,
            span,
        })
    }

    fn scenario_member(&mut self, out: &mut Vec<ScMember>) {
        let word = match &self.peek().tok {
            Tok::Ident(w) => w.clone(),
            _ => String::new(),
        };
        if word == "handle" && self.peek_n(1).tok == Tok::P(Punct::LBrace) {
            let start_pos = self.pos;
            let start = self.peek().span;
            match self.handle() {
                Ok(h) => out.push(ScMember::Handle(h)),
                Err(e) => self.member_hole(start_pos, start, &e),
            }
        } else if word == "title"
            || word == "verified_by"
            || word == "ambient"
            || COMMON_WORDS.contains(&word.as_str())
        {
            let mut cl = Vec::new();
            self.pclause_into(Host::Scenario, &mut cl);
            out.extend(cl.into_iter().map(ScMember::Clause));
        } else {
            let start_pos = self.pos;
            let start = self.peek().span;
            match self.chain_stmt() {
                Ok((id, c)) => out.push(ScMember::Chain(id, c)),
                Err(e) => self.member_hole(start_pos, start, &e),
            }
        }
    }

    /// Reports a broken scenario member and resynchronises inside the scenario block.
    fn member_hole(&mut self, start_pos: usize, _start: Span, e: &ParseErr) {
        self.hole_diag(e);
        if self.pos == start_pos && self.at_p(Punct::Semi) {
            self.bump();
        }
        self.resync(true);
    }

    fn handle(&mut self) -> PResult<Handle> {
        let start = self.bump().span;
        let (arms, close) = self.arms(None)?;
        let id = self.id();
        let span = start.to(close);
        self.register(id, span.start, span.end, span.end, None);
        Ok(Handle { id, arms, span })
    }

    /// `"{" { arm } "}"`, returning the arms and the closing span.
    fn arms(&mut self, matched: Option<&RefPath>) -> PResult<(Vec<Arm>, Span)> {
        if self.depth >= MAX_NESTING {
            return fail(
                self.peek().span,
                format!("arms nest at most {MAX_NESTING} deep"),
            );
        }
        self.expect_p(Punct::LBrace)?;
        self.depth += 1;
        let mut arms = Vec::new();
        while !self.at_p(Punct::RBrace) && !self.at_eof() {
            let pos = self.pos;
            match self.arm(matched) {
                Ok(a) => arms.push(a),
                Err(e) => {
                    self.hole_diag(&e);
                    if self.pos == pos && self.at_p(Punct::Semi) {
                        self.bump();
                    }
                    self.resync(true);
                }
            }
            if self.pos == pos && !self.at_p(Punct::RBrace) && !self.at_eof() {
                self.bump();
            }
        }
        self.depth -= 1;
        let close = self.expect_p(Punct::RBrace)?;
        Ok((arms, close.span))
    }

    fn arm(&mut self, matched: Option<&RefPath>) -> PResult<Arm> {
        let start = self.peek().span;
        let pattern = if matches!(&self.peek().tok, Tok::Ident(w) if w == "_") {
            Pattern::Wild(self.bump().span)
        } else {
            Pattern::Path(self.ref_path("an arm pattern")?)
        };
        if !self.eat_p(Punct::FatArrow) {
            // the bridged `pattern -> chain` spelling
            let arrow = self.expect_p(Punct::Arrow)?;
            tracing::debug!(span = %arrow.span, "bridged arm `p -> c` spelling; reporting MDL012");
            self.diags.push(Diagnostic::new(
                "MDL012",
                arrow.span,
                "arm `p -> c` is a deprecated spelling; write `p => c` (grmb-spec 11.1)",
            ));
        }
        // the default `retry` target: the matched element, or the step part of a handle pattern
        let default = matched.cloned().or_else(|| match &pattern {
            Pattern::Path(p) if p.segments.len() >= 2 => {
                let mut step = p.clone();
                step.segments.pop();
                Some(step)
            }
            _ => None,
        });
        let saved = std::mem::replace(&mut self.retry_default, default);
        let chain = self.chain_stmt();
        self.retry_default = saved;
        let (_, chain) = chain?;
        let id = self.id();
        let span = start.to(chain.span);
        self.register(id, span.start, span.end, span.end, None);
        Ok(Arm {
            id,
            pattern,
            chain,
            span,
        })
    }

    /// A chain with its `;` (optional when the chain ends with `}`).
    fn chain_stmt(&mut self) -> PResult<(usize, Chain)> {
        let c = self.chain()?;
        let mut span = c.span;
        if c.ends_with_brace() {
            if self.at_p(Punct::Semi) {
                span = span.to(self.bump().span);
            }
        } else {
            span = span.to(self.expect_p(Punct::Semi)?.span);
        }
        let id = self.id();
        self.register(id, span.start, span.end, span.end, None);
        Ok((id, c))
    }

    fn chain(&mut self) -> PResult<Chain> {
        let start = self.peek().span;
        let mut links = Vec::new();
        loop {
            if self.at_kw("end") {
                let tail = self.end_tail()?;
                return Ok(self.chain_of(start, links, tail));
            }
            if self.at_kw("retry") {
                let tail = self.retry_tail()?;
                return Ok(self.chain_of(start, links, tail));
            }
            if self.at_kw("sorry") {
                let tail = Tail::Sorry(self.debt()?);
                return Ok(self.chain_of(start, links, tail));
            }
            let elem = self.elem()?;
            if self.eat_p(Punct::Arrow) {
                links.push((elem, Hop::Seq));
            } else if self.eat_p(Punct::TryArrow) {
                links.push((elem, Hop::Try));
            } else if self.eat_p(Punct::FatArrow) {
                let matched = match &elem {
                    Elem::Step(p) | Elem::Include(p) => p.clone(),
                };
                let (arms, _) = self.arms(Some(&matched))?;
                return Ok(self.chain_of(start, links, Tail::Match { elem, arms }));
            } else {
                return Ok(self.chain_of(start, links, Tail::Open(elem)));
            }
        }
    }

    fn chain_of(&self, start: Span, links: Vec<(Elem, Hop)>, tail: Tail) -> Chain {
        Chain {
            links,
            tail,
            span: start.to(Span::new(
                self.prev_end().saturating_sub(1),
                self.prev_end(),
            )),
        }
    }

    fn elem(&mut self) -> PResult<Elem> {
        if self.at_kw("include") {
            self.bump();
            Ok(Elem::Include(self.ref_path("a scenario")?))
        } else {
            Ok(Elem::Step(self.ref_path("a step")?))
        }
    }

    /// `sorry { (because|ticket|until|owner) = value }`
    fn debt(&mut self) -> PResult<Debt> {
        let span = self.bump().span;
        let mut keys = Vec::new();
        while matches!(&self.peek().tok, Tok::Ident(w)
            if matches!(w.as_str(), "because" | "ticket" | "until" | "owner"))
            && self.peek_n(1).tok == Tok::P(Punct::Eq)
        {
            let key = self.any_ident("a debt key")?;
            self.bump();
            let t = self.peek().clone();
            let value = match t.tok {
                Tok::Str(_) => self.string("a debt value")?,
                Tok::Date(d) => {
                    self.bump();
                    Spanned {
                        value: d,
                        span: t.span,
                    }
                }
                Tok::Ident(w) | Tok::RawIdent(w) => {
                    self.bump();
                    Spanned {
                        value: w,
                        span: t.span,
                    }
                }
                _ => return self.unexpected("a string, a date or an identifier"),
            };
            keys.push(DebtKey { key, value });
        }
        tracing::debug!(keys = keys.len(), "sorry hole");
        Ok(Debt { span, keys })
    }

    fn end_tail(&mut self) -> PResult<Tail> {
        let end = self.bump().span;
        if self.at_kw("ok") {
            let ok = self.bump().span;
            return Ok(Tail::EndOk(end.to(ok)));
        }
        self.expect_kw("err")?;
        self.expect_p(Punct::LParen)?;
        let v = self.name("an error variant")?;
        self.expect_p(Punct::RParen)?;
        Ok(Tail::EndErr(v))
    }

    fn retry_tail(&mut self) -> PResult<Tail> {
        let start = self.bump().span;
        let step_written = matches!(&self.peek().tok, Tok::Ident(w)
            if !matches!(w.as_str(), "max" | "within" | "else"));
        let step = if step_written {
            self.ref_path("a step")?
        } else if let Some(d) = self.retry_default.clone() {
            // grmb-spec 12.5: the target defaults to the matched element
            tracing::debug!(step = %d.written(), "retry without a step: using the matched element");
            d
        } else {
            return fail(
                start,
                "`retry` has no matched element to default to; name the step",
            );
        };
        let max = if self.eat_kw("max") {
            match self.peek().tok.clone() {
                Tok::Number(n) => {
                    let span = self.bump().span;
                    Some(Spanned { value: n, span })
                }
                _ => return self.unexpected("a retry bound"),
            }
        } else {
            None
        };
        if self.eat_kw("within") {
            let q = self.quantity()?;
            tracing::debug!(within = %q.number, "retry `within`; the AST has no slot for it yet");
        }
        let otherwise = if self.eat_kw("else") {
            Some(Box::new(self.chain()?))
        } else {
            None
        };
        let span = start.to(Span::new(
            self.prev_end().saturating_sub(1),
            self.prev_end(),
        ));
        Ok(Tail::Retry {
            step,
            max,
            otherwise,
            span,
        })
    }

    fn impl_item(&mut self) -> PResult<Impl> {
        let start = self.bump().span;
        let step = self.ref_path("a step")?;
        self.expect_kw("for")?;
        let target = if self.at_p(Punct::Star) {
            ImplTarget::Any(self.bump().span)
        } else {
            ImplTarget::Scenario(self.ref_path("a scenario")?)
        };
        let mut clauses = Vec::new();
        if self.at_kw("sorry") {
            let head_end = self.peek().span.start;
            let c = self.pclause(Host::Impl)?;
            let end = c.span;
            clauses.push(c);
            let (id, span) = self.finish(start, end, head_end, None);
            tracing::debug!("whole-body sorry impl");
            return Ok(Impl {
                id,
                step,
                target,
                clauses,
                span,
            });
        }
        let open = self.expect_p(Punct::LBrace)?;
        self.pclauses(Host::Impl, &mut clauses);
        let close = self.expect_p(Punct::RBrace)?;
        let (id, span) = self.finish(start, close.span, open.span.end, Some(close.span.start));
        Ok(Impl {
            id,
            step,
            target,
            clauses,
            span,
        })
    }

    fn page(&mut self) -> PResult<Page> {
        let start = self.bump().span;
        let name = self.name("a page name")?;
        let mut clauses = Vec::new();
        if self.at_kw("sorry") {
            let head_end = self.peek().span.start;
            let c = self.pclause(Host::Page)?;
            let end = c.span;
            clauses.push(c);
            let (id, span) = self.finish(start, end, head_end, None);
            tracing::debug!("whole-body sorry page");
            return Ok(Page {
                id,
                name,
                braced: false,
                clauses,
                span,
            });
        }
        let (braced, end, head_end, close) = self.semi_or_body(Host::Page, &mut clauses)?;
        let (id, span) = self.finish(start, end, head_end, close);
        Ok(Page {
            id,
            name,
            braced,
            clauses,
            span,
        })
    }

    // ----- clauses -----

    /// `KIND [NAME] = SELECTOR` (no terminator).
    fn realization(&mut self) -> PResult<Realization> {
        let kind = self.any_ident("a realization kind")?;
        let name = if self.peek().tok.is_word() && self.peek_n(1).tok == Tok::P(Punct::Eq) {
            Some(self.name("a realization name")?)
        } else {
            None
        };
        self.expect_p(Punct::Eq)?;
        let sel = self.selector()?;
        Ok(Realization { kind, name, sel })
    }

    /// `escalate | terminate | (retry|restart) [max N] [within Q] [else POLICY]`
    fn policy(&mut self) -> PResult<Policy> {
        if self.depth >= MAX_NESTING {
            return fail(
                self.peek().span,
                format!("policies nest at most {MAX_NESTING} deep"),
            );
        }
        let action = self.any_ident("a policy action")?;
        if !matches!(
            action.text.as_str(),
            "escalate" | "terminate" | "retry" | "restart"
        ) {
            return fail(
                action.span,
                format!(
                    "`{}` is not a policy; expected `escalate`, `terminate`, `retry` or `restart`",
                    action.text
                ),
            );
        }
        let counted = matches!(action.text.as_str(), "retry" | "restart");
        let max = if counted && self.eat_kw("max") {
            match self.peek().tok.clone() {
                Tok::Number(n) => {
                    let span = self.bump().span;
                    Some(Spanned { value: n, span })
                }
                _ => return self.unexpected("a policy bound"),
            }
        } else {
            None
        };
        let within = if counted && self.eat_kw("within") {
            Some(self.quantity()?)
        } else {
            None
        };
        let otherwise = if self.eat_kw("else") {
            self.depth += 1;
            let p = self.policy();
            self.depth -= 1;
            Some(Box::new(p?))
        } else {
            None
        };
        Ok(Policy {
            action,
            max,
            within,
            otherwise,
        })
    }

    /// `KIND [NAME] = SELECTOR ( ; | { SOURCE {, SOURCE} => NAME ; | verified_by ... } )`
    fn waypoint(&mut self) -> PResult<Waypoint> {
        let start = self.peek().span;
        let real = self.realization()?;
        let mut maps = Vec::new();
        let mut clauses = Vec::new();
        let braced = self.at_p(Punct::LBrace);
        let end = if braced {
            self.bump();
            while !self.at_p(Punct::RBrace) && !self.at_eof() {
                let pos = self.pos;
                if self.at_kw("verified_by") {
                    self.pclause_into(Host::Leaf, &mut clauses);
                } else {
                    match self.waypoint_map() {
                        Ok(m) => maps.push(m),
                        Err(e) => {
                            self.hole_diag(&e);
                            if self.pos == pos && self.at_p(Punct::Semi) {
                                self.bump();
                            }
                            self.resync(true);
                        }
                    }
                }
                if self.pos == pos && !self.at_p(Punct::RBrace) && !self.at_eof() {
                    self.bump();
                }
            }
            self.expect_p(Punct::RBrace)?.span
        } else {
            self.expect_p(Punct::Semi)?.span
        };
        let id = self.id();
        let span = start.to(end);
        self.register(id, span.start, span.end, span.end, None);
        Ok(Waypoint {
            id,
            real,
            braced,
            maps,
            clauses,
            span,
        })
    }

    /// `SOURCE {, SOURCE} => NAME ;`
    fn waypoint_map(&mut self) -> PResult<WaypointMap> {
        let mut sources = Vec::new();
        loop {
            let t = self.peek().clone();
            match t.tok {
                Tok::Ident(w) | Tok::RawIdent(w) => {
                    self.bump();
                    sources.push(Spanned {
                        value: w,
                        span: t.span,
                    });
                }
                Tok::Number(n) => {
                    self.bump();
                    sources.push(Spanned {
                        value: n,
                        span: t.span,
                    });
                }
                _ => return self.unexpected("an exception name, a status number or `_`"),
            }
            if !self.eat_p(Punct::Comma) {
                break;
            }
        }
        self.expect_p(Punct::FatArrow)?;
        let target = self.name("an outcome variant")?;
        self.expect_p(Punct::Semi)?;
        Ok(WaypointMap { sources, target })
    }

    /// Parses clauses up to the closing `}` (not consumed); broken ones become holes.
    fn pclauses(&mut self, host: Host, out: &mut Vec<PClause>) {
        while !self.at_p(Punct::RBrace) && !self.at_eof() {
            let pos = self.pos;
            self.pclause_into(host, out);
            if self.pos == pos && !self.at_p(Punct::RBrace) && !self.at_eof() {
                self.bump();
            }
        }
    }

    /// Parses one clause, pushing it (or a hole) onto `out`.
    fn pclause_into(&mut self, host: Host, out: &mut Vec<PClause>) {
        let pos = self.pos;
        let start = self.peek().span;
        match self.pclause(host) {
            Ok(c) => out.push(c),
            Err(e) => {
                self.hole_diag(&e);
                if self.pos == pos && self.at_p(Punct::Semi) {
                    self.bump();
                }
                self.resync(true);
                let span = Span::new(start.start, self.prev_end().max(start.end));
                let id = self.id();
                self.register(id, span.start, span.end, span.end, None);
                out.push(PClause {
                    id,
                    kind: PClauseKind::Hole(e.message),
                    span,
                });
            }
        }
    }

    #[allow(clippy::too_many_lines)] // one arm per clause keyword
    fn pclause(&mut self, host: Host) -> PResult<PClause> {
        let start = self.peek().span;
        let word = match self.peek().tok.clone() {
            Tok::Ident(w) => w,
            // a raw word is never a clause keyword (grmb-spec 2.2): `r#` keeps it out of every keyword arm
            Tok::RawIdent(w) => format!("r#{w}"),
            _ => return self.unexpected("a clause keyword"),
        };
        if COMMON_WORDS.contains(&word.as_str()) {
            let c = self.clause()?;
            return Ok(PClause {
                id: c.id,
                span: c.span,
                kind: PClauseKind::Common(c),
            });
        }
        if word == "verified_by" && matches!(&self.peek_n(1).tok, Tok::Ident(w) if w == "manual") {
            // `verified_by manual because="R"` is valid on every entity (grmb-spec 4)
            let c = self.clause()?;
            return Ok(PClause {
                id: c.id,
                span: c.span,
                kind: PClauseKind::Common(c),
            });
        }
        let kind = match (word.as_str(), host) {
            ("title", _) => {
                let kw = self.bump().span;
                let t = self.string("a title string")?;
                tracing::debug!(span = %kw, "bridged `title` clause; reporting MDL012");
                self.diags.push(Diagnostic::new(
                    "MDL012",
                    kw.to(t.span),
                    "`title` is a deprecated spelling; write a `///` line (grmb-spec 11.1)",
                ));
                PClauseKind::Title(t)
            }
            ("verified_by", h) if h.allows_verified() => {
                let kw = self.bump();
                if h == Host::System {
                    tracing::debug!(span = %kw.span, "bridged `verified_by` on a system; reporting MDL012");
                    self.diags.push(Diagnostic::new(
                        "MDL012",
                        kw.span,
                        "`verified_by` on a system is a deprecated spelling and is ignored; a system has no status, put the evidence on a step or goal (grmb-spec 11.1, 12.8)",
                    ));
                }
                let sel = self.selector_for()?;
                let pair = if self.eat_kw("for") {
                    Some(self.ref_path("a step variant")?)
                } else {
                    None
                };
                PClauseKind::Verified(Verified { sel, pair })
            }
            ("node", Host::Actor) => {
                let kw = self.bump();
                tracing::debug!(span = %kw.span, "bridged actor `node` clause; reporting MDL012");
                self.diags.push(Diagnostic::new(
                    "MDL012",
                    kw.span,
                    "actor `node N;` is a deprecated spelling; write `in node N;` (grmb-spec 11.1)",
                ));
                PClauseKind::Node(self.ref_path("a node")?)
            }
            ("entry", Host::Page) => {
                self.bump();
                PClauseKind::Entry
            }
            ("from", Host::Page) => {
                self.bump();
                let mut pages = vec![self.ref_path("a page")?];
                while self.eat_p(Punct::Comma) {
                    pages.push(self.ref_path("a page")?);
                }
                PClauseKind::From(pages)
            }
            ("requires" | "on", Host::Impl) => {
                // `on page P` is the spec spelling; `requires page P` is the legacy one (same meaning)
                let kw = self.bump();
                if word == "requires" {
                    tracing::debug!(span = %kw.span, "bridged `requires page` clause; reporting MDL012");
                    self.diags.push(Diagnostic::new(
                        "MDL012",
                        kw.span,
                        "`requires page` is a deprecated spelling; write `on page` (grmb-spec 11.1)",
                    ));
                }
                self.expect_kw("page")?;
                PClauseKind::RequiresPage(self.ref_path("a page")?)
            }
            // frob:ticket 01M6BYK3QNNF0WHQW2Y0Q2TMVM
            ("sorry", Host::Impl | Host::Page) => {
                // whole-body hole: `impl s for t sorry ...;` / `page p sorry ...;`
                PClauseKind::Sorry(self.debt()?)
            }
            ("in", Host::Impl | Host::Actor) => {
                self.bump();
                self.expect_kw("node")?;
                PClauseKind::InNode(self.ref_path("a node")?)
            }
            ("non_goal", Host::System) => {
                self.bump();
                PClauseKind::NonGoal(self.name("a non-goal name")?)
            }
            ("ambient", Host::System | Host::Scenario) => {
                self.bump();
                let policy = self.policy()?;
                let mut clauses = Vec::new();
                let braced = self.at_p(Punct::LBrace);
                let end = if braced {
                    self.bump();
                    self.pclauses(Host::Leaf, &mut clauses);
                    self.expect_p(Punct::RBrace)?.span
                } else {
                    self.expect_p(Punct::Semi)?.span
                };
                let id = self.id();
                let span = start.to(end);
                self.register(id, span.start, span.end, span.end, None);
                tracing::debug!(braced, "ambient policy");
                return Ok(PClause {
                    id,
                    kind: PClauseKind::Ambient(Ambient {
                        policy,
                        braced,
                        clauses,
                    }),
                    span,
                });
            }
            ("chain", Host::Impl) if self.peek_n(1).tok == Tok::P(Punct::LBrace) => {
                self.bump();
                self.bump();
                let mut wps = Vec::new();
                while !self.at_p(Punct::RBrace) && !self.at_eof() {
                    let pos = self.pos;
                    match self.waypoint() {
                        Ok(w) => wps.push(w),
                        Err(e) => {
                            self.hole_diag(&e);
                            if self.pos == pos && self.at_p(Punct::Semi) {
                                self.bump();
                            }
                            self.resync(true);
                        }
                    }
                    if self.pos == pos && !self.at_p(Punct::RBrace) && !self.at_eof() {
                        self.bump();
                    }
                }
                let close = self.expect_p(Punct::RBrace)?;
                let id = self.id();
                let span = start.to(close.span);
                self.register(id, span.start, span.end, span.end, None);
                tracing::debug!(waypoints = wps.len(), "impl chain");
                return Ok(PClause {
                    id,
                    kind: PClauseKind::Chain(wps),
                    span,
                });
            }
            (w, h) if h.allows_realization() && !is_planning_word(w) => {
                PClauseKind::Realization(self.realization()?)
            }
            (w, _) => {
                return fail(
                    start,
                    format!("`{w}` is not a clause of this planning item"),
                );
            }
        };
        let semi = self.expect_p(Punct::Semi)?;
        let id = self.id();
        let span = start.to(semi.span);
        self.register(id, span.start, span.end, span.end, None);
        Ok(PClause { id, kind, span })
    }
}
