//! Parsing of the planning items (grmb-planning 3): contextual words are recognised by position.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use crate::ast::Spanned;
use crate::keywords::is_planning_word;
use crate::lex::{Punct, Tok};
use crate::plan::{
    Actor, Arm, Chain, Elem, GoalBlock, Handle, Hop, Impl, ImplTarget, Outcome, PClause,
    PClauseKind, Page, Pattern, PlanItem, Realization, ScMember, Scenario, Step, System, Tail,
    Variant, Verified,
};
use crate::span::Span;

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
            if w == "title" || w == "verified_by" || COMMON_WORDS.contains(&w.as_str()))
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
        let key = if self.eat_kw("as") {
            Some(self.any_ident("a dimension key")?)
        } else {
            None
        };
        let open = self.expect_p(Punct::LBrace)?;
        let mut variants = Vec::new();
        while !self.at_p(Punct::RBrace) && !self.at_eof() {
            let pos = self.pos;
            let s = self.peek().span;
            match self.variant() {
                Ok(v) => variants.push(v),
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
        let outcome = if self.eat_p(Punct::Arrow) {
            Some(self.outcome()?)
        } else {
            None
        };
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
        } else if word == "title" || word == "verified_by" || COMMON_WORDS.contains(&word.as_str())
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
        let (arms, close) = self.arms()?;
        let id = self.id();
        let span = start.to(close);
        self.register(id, span.start, span.end, span.end, None);
        Ok(Handle { id, arms, span })
    }

    /// `"{" { arm } "}"`, returning the arms and the closing span.
    fn arms(&mut self) -> PResult<(Vec<Arm>, Span)> {
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
            match self.arm() {
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

    fn arm(&mut self) -> PResult<Arm> {
        let start = self.peek().span;
        let pattern = if matches!(&self.peek().tok, Tok::Ident(w) if w == "_") {
            Pattern::Wild(self.bump().span)
        } else {
            Pattern::Path(self.ref_path("an arm pattern")?)
        };
        self.expect_p(Punct::Arrow)?;
        let (_, chain) = self.chain_stmt()?;
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
            let elem = self.elem()?;
            if self.eat_p(Punct::Arrow) {
                links.push((elem, Hop::Seq));
            } else if self.eat_p(Punct::TryArrow) {
                links.push((elem, Hop::Try));
            } else if self.eat_p(Punct::FatArrow) {
                let (arms, _) = self.arms()?;
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
        let step = self.ref_path("a step")?;
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

    fn pclause(&mut self, host: Host) -> PResult<PClause> {
        let start = self.peek().span;
        let Tok::Ident(word) = self.peek().tok.clone() else {
            return self.unexpected("a clause keyword");
        };
        if COMMON_WORDS.contains(&word.as_str()) {
            let c = self.clause()?;
            return Ok(PClause {
                id: c.id,
                span: c.span,
                kind: PClauseKind::Common(c),
            });
        }
        let kind = match (word.as_str(), host) {
            ("title", _) => {
                self.bump();
                PClauseKind::Title(self.string("a title string")?)
            }
            ("verified_by", h) if h.allows_verified() => {
                self.bump();
                let sel = self.selector_for()?;
                let pair = if self.eat_kw("for") {
                    Some(self.ref_path("a step variant")?)
                } else {
                    None
                };
                PClauseKind::Verified(Verified { sel, pair })
            }
            ("node", Host::Actor) => {
                self.bump();
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
            ("requires", Host::Impl) => {
                self.bump();
                self.expect_kw("page")?;
                PClauseKind::RequiresPage(self.ref_path("a page")?)
            }
            ("in", Host::Impl) => {
                self.bump();
                self.expect_kw("node")?;
                PClauseKind::InNode(self.ref_path("a node")?)
            }
            (w, h) if h.allows_realization() && !is_planning_word(w) => {
                let kind = self.any_ident("a realization kind")?;
                let name = if matches!(self.peek().tok, Tok::Ident(_))
                    && self.peek_n(1).tok == Tok::P(Punct::Eq)
                {
                    Some(self.name("a realization name")?)
                } else {
                    None
                };
                self.expect_p(Punct::Eq)?;
                let sel = self.selector()?;
                PClauseKind::Realization(Realization { kind, name, sel })
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
