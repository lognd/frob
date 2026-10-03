//! Token types produced by the GRL lexer.

use gob_text::{Span, TextRange};

/// One lexical token and where it came from.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Token {
    /// What the token is.
    pub kind: TokenKind,
    /// Where it sits in the file (byte range).
    pub span: Span,
}

/// A `#` comment; dropped from the token stream, kept for the formatter.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Comment {
    /// The comment including its `#`, excluding the line break.
    pub span: Span,
}

/// The kind of a token, with its decoded payload where it has one.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TokenKind {
    /// A lowercase word `[a-z_][a-z0-9_]*`; keywords are identifiers and the parser classifies them.
    Ident(String),
    /// A rule id `[A-Z]+[0-9]{3}`, such as `TODO001`.
    RuleId(String),
    /// A polarity word: `P+`, `P-`, `P0`, `Pn` or `Pc`.
    Polarity(String),
    /// A whole number.
    Int(u64),
    /// A decimal number, kept as written (for example `0.75`) so no precision is lost.
    Decimal(String),
    /// A `"..."` string split into text and `{expr}` parts.
    Str(Vec<StrPart>),
    /// A `"""..."""` block string with the common indentation removed.
    Block(Block),
    /// A backtick snippet.
    Snippet(Snippet),
    /// A `/.../` regex literal with flags.
    Regex(Regex),
    /// `{`
    LBrace,
    /// `}`
    RBrace,
    /// `(`
    LParen,
    /// `)`
    RParen,
    /// `[`
    LBracket,
    /// `]`
    RBracket,
    /// `,`
    Comma,
    /// `:`
    Colon,
    /// `.`
    Dot,
    /// `..` (ranges)
    DotDot,
    /// `=`
    Eq,
    /// `==`
    EqEq,
    /// `!=`
    Ne,
    /// `<`
    Lt,
    /// `<=`
    Le,
    /// `>`
    Gt,
    /// `>=`
    Ge,
    /// `~` (regex match)
    Tilde,
    /// `|`
    Pipe,
    /// `+`
    Plus,
    /// `-`
    Minus,
    /// `*`
    Star,
    /// `->`
    Arrow,
}

/// One piece of a `"..."` string.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StrPart {
    /// Literal text with escapes decoded.
    Text {
        /// The decoded text.
        value: String,
        /// The source range it was read from (escapes included).
        span: Span,
    },
    /// A `{expr}` interpolation; the span is the expression between the braces.
    Interp {
        /// Range of the expression text, braces excluded; the parser lexes it with [`crate::grl::lex_range`].
        expr: Span,
    },
}

/// A triple-quoted block string.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Block {
    /// The content with the first and last blank lines and the common indentation removed.
    pub value: String,
    /// The raw content range between the quotes.
    pub body: Span,
}

/// A backtick snippet: raw text where only `$` is special.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Snippet {
    /// The language tag written directly before the opening backtick.
    pub lang: Option<SnippetLang>,
    /// Backticks in the delimiter: 1, or 2 when the text may hold single backticks.
    pub ticks: u8,
    /// The raw text between the delimiters, exactly as written (`$$` stays `$$`).
    pub text: String,
    /// The source range of `text`.
    pub body: Span,
    /// Metavariables in the order they appear.
    pub metavars: Vec<MetaVar>,
    /// Ranges of `$$` pairs that stand for a literal dollar.
    pub dollars: Vec<Span>,
}

/// A language tag on a snippet, such as `rust` in ``rust`$X.unwrap()` ``.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SnippetLang {
    /// The language id as written.
    pub name: String,
    /// Where the tag is.
    pub span: Span,
}

/// Whether a metavariable stands for one node or a sequence.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MetaKind {
    /// `$X` or `$_`: exactly one node.
    One,
    /// `$$$XS` or `$$$`: any number of nodes.
    Seq,
}

/// A metavariable found inside a snippet.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MetaVar {
    /// One node or a sequence.
    pub kind: MetaKind,
    /// The name without dollars; `None` for the anonymous `$_` and `$$$`.
    pub name: Option<String>,
    /// The range of the whole metavariable including its dollars.
    pub span: Span,
}

/// A regex literal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Regex {
    /// The pattern text between the slashes, as written (`\/` stays `\/`).
    pub pattern: String,
    /// The `i` flag: ignore case.
    pub ignore_case: bool,
    /// The `m` flag: `^` and `$` match at line breaks.
    pub multi_line: bool,
}

/// The result of lexing: significant tokens and the dropped comments.
///
/// Tokens and comments are each in source order and never overlap; every
/// byte not covered by either is ASCII whitespace.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Lexed {
    /// Significant tokens in source order.
    pub tokens: Vec<Token>,
    /// `#` comments in source order.
    pub comments: Vec<Comment>,
}

impl Lexed {
    /// Every covered range (tokens and comments) in source order.
    pub fn covered(&self) -> Vec<TextRange> {
        let mut all: Vec<TextRange> = self
            .tokens
            .iter()
            .map(|t| t.span.range)
            .chain(self.comments.iter().map(|c| c.span.range))
            .collect();
        all.sort_by_key(|r| (r.start(), r.end()));
        all
    }
}
