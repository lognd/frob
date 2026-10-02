//! Recursive-descent parser for the grmb-spec 6.1 grammar.

use std::fmt;

use super::lex::{StrLit, Tok, Token, lex};
use super::{AttrPred, Cmp, Expr, Glob, Node, Value};

/// A byte range in the source text (offset-corrected by the caller's base).
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug, Default)]
pub struct Span {
    /// First byte.
    pub start: usize,
    /// One past the last byte.
    pub end: usize,
}

impl Span {
    fn to(self, other: Self) -> Self {
        Self {
            start: self.start,
            end: other.end,
        }
    }
}

impl fmt::Display for Span {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}..{}", self.start, self.end)
    }
}

/// A selector syntax error with the exact span of the offending text.
#[derive(Clone, PartialEq, Eq, Debug, thiserror::Error)]
#[error("E-SEL-SYNTAX: {message} at bytes {span}")]
pub struct SyntaxError {
    /// Where the problem is, in file coordinates.
    pub span: Span,
    /// What is wrong and what was expected.
    pub message: String,
}

type R<T> = Result<T, SyntaxError>;

/// The closed unit table of grmb-spec 2.2.
const TIME: [&str; 7] = ["ns", "us", "ms", "s", "min", "h", "d"];
const SIZE: [&str; 5] = ["B", "KiB", "MiB", "GiB", "TiB"];
const COUNT: [&str; 4] = ["req", "msg", "evt", "op"];

fn unit_is_valid(unit: &str) -> bool {
    match unit.split_once('/') {
        None => {
            TIME.contains(&unit) || SIZE.contains(&unit) || COUNT.contains(&unit) || unit == "%"
        }
        Some((num, den)) => {
            (COUNT.contains(&num) || SIZE.contains(&num) || num == "%") && TIME.contains(&den)
        }
    }
}

struct Parser {
    toks: Vec<Token>,
    pos: usize,
}

pub(super) fn parse(text: &str, base: usize) -> Result<Node, Vec<SyntaxError>> {
    let toks = lex(text, base).map_err(|e| vec![e])?;
    let mut p = Parser { toks, pos: 0 };
    let node = p.or().map_err(|e| vec![e])?;
    let t = p.peek();
    if t.tok != Tok::Eof {
        return Err(vec![SyntaxError {
            span: t.span,
            message: format!(
                "unexpected {}, expected `|`, `&` or end of selector",
                t.tok.describe()
            ),
        }]);
    }
    Ok(node)
}

impl Parser {
    fn peek(&self) -> &Token {
        &self.toks[self.pos.min(self.toks.len() - 1)]
    }

    fn next(&mut self) -> Token {
        let t = self.peek().clone();
        if self.pos < self.toks.len() - 1 {
            self.pos += 1;
        }
        t
    }

    fn expect(&mut self, want: &Tok, what: &str) -> R<Token> {
        let t = self.next();
        if &t.tok == want {
            Ok(t)
        } else {
            Err(SyntaxError {
                span: t.span,
                message: format!("unexpected {}, expected {what}", t.tok.describe()),
            })
        }
    }

    fn ident(&mut self, what: &str) -> R<(String, Span)> {
        let t = self.next();
        match t.tok {
            Tok::Ident(s) => Ok((s, t.span)),
            other => Err(SyntaxError {
                span: t.span,
                message: format!("unexpected {}, expected {what}", other.describe()),
            }),
        }
    }

    fn or(&mut self) -> R<Node> {
        let mut ops = vec![self.and()?];
        while self.peek().tok == Tok::Pipe {
            self.next();
            ops.push(self.and()?);
        }
        Ok(join(ops, Expr::Or))
    }

    fn and(&mut self) -> R<Node> {
        let mut ops = vec![self.unary()?];
        while self.peek().tok == Tok::Amp {
            self.next();
            ops.push(self.unary()?);
        }
        Ok(join(ops, Expr::And))
    }

    fn unary(&mut self) -> R<Node> {
        if self.peek().tok == Tok::Bang {
            let bang = self.next();
            let inner = self.unary()?;
            let span = bang.span.to(inner.span);
            return Ok(Node {
                expr: Expr::Not(Box::new(inner)),
                span,
            });
        }
        self.primary()
    }

    fn primary(&mut self) -> R<Node> {
        let t = self.next();
        match t.tok {
            Tok::Str(lit) => glob_node(&lit, t.span),
            Tok::LParen => {
                let inner = self.or()?;
                self.expect(&Tok::RParen, "`)`")?;
                Ok(inner)
            }
            Tok::Ident(name) => self.predicate(&name, t.span),
            other => Err(SyntaxError {
                span: t.span,
                message: format!(
                    "unexpected {}, expected a glob string, `lang`, `kind`, `attr`, `!` or `(`",
                    other.describe()
                ),
            }),
        }
    }

    fn predicate(&mut self, name: &str, head: Span) -> R<Node> {
        if !matches!(name, "lang" | "kind" | "attr") {
            return Err(SyntaxError {
                span: head,
                message: format!("unknown predicate `{name}`, expected `lang`, `kind` or `attr`"),
            });
        }
        self.expect(&Tok::LParen, "`(`")?;
        let expr = match name {
            "lang" => Expr::Lang(self.ident("a language tag")?.0),
            "kind" => {
                let mut kinds = vec![self.ident("a unit kind")?.0];
                while self.peek().tok == Tok::Comma {
                    self.next();
                    kinds.push(self.ident("a unit kind")?.0);
                }
                Expr::Kind(kinds)
            }
            _ => Expr::Attr(self.attr()?),
        };
        let close = self.expect(&Tok::RParen, "`)`")?;
        Ok(Node {
            expr,
            span: head.to(close.span),
        })
    }

    fn attr(&mut self) -> R<AttrPred> {
        let (name, _) = self.ident("an attribute name")?;
        let cmp = match self.peek().tok {
            Tok::Eq => Cmp::Eq,
            Tok::Ne => Cmp::Ne,
            Tok::Tilde => Cmp::Match,
            Tok::Le => Cmp::Le,
            _ => return Ok(AttrPred { name, test: None }),
        };
        self.next();
        let (value, span) = self.value()?;
        let ok = match cmp {
            Cmp::Eq | Cmp::Ne => true,
            Cmp::Match => matches!(value, Value::Str(_)),
            Cmp::Le => matches!(value, Value::Number(_) | Value::Quantity { .. }),
        };
        if !ok {
            let need = if cmp == Cmp::Match {
                "a string"
            } else {
                "a number or quantity"
            };
            return Err(SyntaxError {
                span,
                message: format!("`{}` needs {need} on its right", cmp.symbol()),
            });
        }
        Ok(AttrPred {
            name,
            test: Some((cmp, value)),
        })
    }

    fn value(&mut self) -> R<(Value, Span)> {
        let t = self.next();
        match t.tok {
            Tok::Str(lit) => Ok((Value::Str(lit.value), t.span)),
            Tok::Ident(s) => Ok((Value::Ident(s), t.span)),
            Tok::Number(number) => self.quantity_tail(number, t.span),
            other => Err(SyntaxError {
                span: t.span,
                message: format!(
                    "unexpected {}, expected a string, number, quantity or identifier",
                    other.describe()
                ),
            }),
        }
    }

    /// After a number: an optional unit from the closed table makes it a quantity.
    fn quantity_tail(&mut self, number: String, start: Span) -> R<(Value, Span)> {
        let (head, mut end) = match self.peek().tok.clone() {
            Tok::Ident(u) => (u, self.next().span),
            Tok::Percent => ("%".to_owned(), self.next().span),
            _ => return Ok((Value::Number(number), start)),
        };
        let mut unit = head;
        if self.peek().tok == Tok::Slash {
            self.next();
            let (den, sp) = self.ident("a time unit after `/`")?;
            unit = format!("{unit}/{den}");
            end = sp;
        }
        let span = start.to(end);
        if !unit_is_valid(&unit) {
            return Err(SyntaxError {
                span: Span {
                    start: span.start + number.len(),
                    end: span.end,
                },
                message: format!("unit `{unit}` is not in the closed unit table"),
            });
        }
        Ok((Value::Quantity { number, unit }, span))
    }
}

fn join(mut ops: Vec<Node>, make: fn(Vec<Node>) -> Expr) -> Node {
    if ops.len() == 1 {
        return ops.remove(0);
    }
    let span = ops[0].span.to(ops[ops.len() - 1].span);
    Node {
        expr: make(ops),
        span,
    }
}

fn glob_node(lit: &StrLit, span: Span) -> R<Node> {
    match Glob::parse(&lit.value) {
        Ok(g) => Ok(Node {
            expr: Expr::Glob(g),
            span,
        }),
        Err(e) => {
            let at = lit.map.get(e.offset).copied().unwrap_or(span.end - 1);
            Err(SyntaxError {
                span: Span {
                    start: at,
                    end: (at + 1).min(span.end),
                },
                message: e.message,
            })
        }
    }
}
