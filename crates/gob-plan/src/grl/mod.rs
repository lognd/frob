//! GRL, the grimble rule language: lexical structure (grl-spec.md section 3).
//!
//! [`lex`] turns source text into [`Token`]s carrying `gob-text` spans, or a
//! located [`LexError`]. Syntax outside strings, snippets and comments is
//! ASCII only. The lexer never panics, whatever the input.
//!
//! # Token kinds
//!
//! | Kind | Example |
//! |---|---|
//! | identifier or keyword | `find`, `max_depth` |
//! | rule id | `TODO001` |
//! | polarity | `P+`, `Pn` |
//! | integer, decimal | `12`, `0.75` |
//! | string | `"remove {d.name}"` |
//! | block string | `"""` ... `"""` |
//! | snippet | `` `dbg!($$$ARGS)` ``, ``rust`$X.unwrap()` ``, ``` ``a `b` c`` ``` |
//! | regex | `/todo/i` |
//! | punctuation | `{ } ( ) [ ] , : . .. = == != < <= > >= ~ \| + - * ->` |
//!
//! Comments (`# ...`) are dropped from the token stream but listed in
//! [`Lexed::comments`] for the formatter. Hyphenated words such as
//! `known-gap` arrive as `known`, `-`, `gap` with adjacent spans; the parser
//! joins them.

pub mod ast;
mod error;
mod lexer;
mod parse;
mod print;
mod snippet;
mod strings;
mod token;

pub use error::{LexError, LexErrorKind};
pub use lexer::{lex, lex_range};
pub use parse::{
    ParseError, ParseErrorKind, ParseWarning, ParseWarningKind, Parsed, parse, parse_tokens,
};
pub use print::{print, print_rule};
pub use token::{
    Block, Comment, Lexed, MetaKind, MetaVar, Regex, Snippet, SnippetLang, StrPart, Token,
    TokenKind,
};
