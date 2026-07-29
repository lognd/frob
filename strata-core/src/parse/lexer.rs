// Lexer for the strata surface grammar: tokenizes source text into
// [`Token`]s consumed by the recursive-descent parser in sibling
// `grammar_*` modules (docs/strata/surface.md#parser).
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

// ---------------------------------------------------------------------
// Lexer
// ---------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
enum TokKind {
    Ident(String),
    Number(f64),
    Str(String),
    Symbol(char), // one of : { } ; -> ( ) . .. handled specially below
    Arrow,        // ->
    DotDot,       // ..
    Eof,
}

#[derive(Debug, Clone)]
struct Token {
    kind: TokKind,
    line: usize,
    col: usize,
}

#[derive(Debug, Clone)]
struct ParseError {
    line: usize,
    col: usize,
    message: String,
}

fn is_ident_start(c: char) -> bool {
    c.is_ascii_alphabetic() || c == '_'
}

fn is_ident_cont(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '_'
}

/// Turn source text into a token stream, or the first lexical error found.
///
/// WHY: a flat token vector lets the recursive-descent parser below use
/// simple lookahead without re-scanning characters; `//` comments and all
/// whitespace/newlines are stripped here so the parser never sees them.
fn lex(text: &str) -> Result<Vec<Token>, ParseError> {
    let chars: Vec<char> = text.chars().collect();
    let mut i = 0usize;
    let mut line = 1usize;
    let mut col = 1usize;
    let mut toks: Vec<Token> = Vec::new();

    macro_rules! advance {
        () => {{
            if i < chars.len() {
                if chars[i] == '\n' {
                    line += 1;
                    col = 1;
                } else {
                    col += 1;
                }
                i += 1;
            }
        }};
    }

    while i < chars.len() {
        let c = chars[i];
        if c == ' ' || c == '\t' || c == '\r' || c == '\n' {
            advance!();
            continue;
        }
        if c == '/' && i + 1 < chars.len() && chars[i + 1] == '/' {
            while i < chars.len() && chars[i] != '\n' {
                advance!();
            }
            continue;
        }
        let start_line = line;
        let start_col = col;
        if is_ident_start(c) {
            let mut s = String::new();
            while i < chars.len() && is_ident_cont(chars[i]) {
                s.push(chars[i]);
                advance!();
            }
            toks.push(Token {
                kind: TokKind::Ident(s),
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if c.is_ascii_digit() {
            let mut s = String::new();
            while i < chars.len() && chars[i].is_ascii_digit() {
                s.push(chars[i]);
                advance!();
            }
            if i < chars.len()
                && chars[i] == '.'
                && i + 1 < chars.len()
                && chars[i + 1].is_ascii_digit()
            {
                s.push('.');
                advance!();
                while i < chars.len() && chars[i].is_ascii_digit() {
                    s.push(chars[i]);
                    advance!();
                }
            }
            let value: f64 = s.parse().map_err(|_| ParseError {
                line: start_line,
                col: start_col,
                message: format!("malformed number literal {:?}", s),
            })?;
            toks.push(Token {
                kind: TokKind::Number(value),
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if c == '"' {
            advance!();
            let mut s = String::new();
            while i < chars.len() && chars[i] != '"' {
                if chars[i] == '\n' {
                    return Err(ParseError {
                        line: start_line,
                        col: start_col,
                        message: "unterminated string literal".to_string(),
                    });
                }
                s.push(chars[i]);
                advance!();
            }
            if i >= chars.len() {
                return Err(ParseError {
                    line: start_line,
                    col: start_col,
                    message: "unterminated string literal".to_string(),
                });
            }
            advance!(); // closing quote
            toks.push(Token {
                kind: TokKind::Str(s),
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if c == '-' && i + 1 < chars.len() && chars[i + 1] == '>' {
            advance!();
            advance!();
            toks.push(Token {
                kind: TokKind::Arrow,
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if c == '.' && i + 1 < chars.len() && chars[i + 1] == '.' {
            advance!();
            advance!();
            toks.push(Token {
                kind: TokKind::DotDot,
                line: start_line,
                col: start_col,
            });
            continue;
        }
        if matches!(
            c,
            ':' | '{' | '}' | ';' | '(' | ')' | '%' | '/' | '=' | '<' | '>' | '.' | ','
        ) {
            advance!();
            toks.push(Token {
                kind: TokKind::Symbol(c),
                line: start_line,
                col: start_col,
            });
            continue;
        }
        return Err(ParseError {
            line: start_line,
            col: start_col,
            message: format!("unexpected character {:?}", c),
        });
    }
    toks.push(Token {
        kind: TokKind::Eof,
        line,
        col,
    });
    Ok(toks)
}

