//! The canonical printer: one spelling per selector, so `parse(print(s)) == s`.

// frob:ticket 01M3Z713RETBN30XBC6CK11FBF

use std::fmt::{self, Write};

use super::{Expr, Node, Value};

/// Binding strength: `|` 0, `&` 1, `!` 2, atoms 3.
fn prec(e: &Expr) -> u8 {
    match e {
        Expr::Or(_) => 0,
        Expr::And(_) => 1,
        Expr::Not(_) => 2,
        _ => 3,
    }
}

fn write_str_lit(f: &mut fmt::Formatter<'_>, s: &str) -> fmt::Result {
    f.write_char('"')?;
    for c in s.chars() {
        match c {
            '"' => f.write_str("\\\"")?,
            '\\' => f.write_str("\\\\")?,
            '\n' => f.write_str("\\n")?,
            '\t' => f.write_str("\\t")?,
            '\r' => f.write_str("\\r")?,
            c if c.is_control() => write!(f, "\\u{{{:x}}}", u32::from(c))?,
            c => f.write_char(c)?,
        }
    }
    f.write_char('"')
}

fn write_value(f: &mut fmt::Formatter<'_>, v: &Value) -> fmt::Result {
    match v {
        Value::Str(s) => write_str_lit(f, s),
        Value::Number(n) | Value::Ident(n) => f.write_str(n),
        Value::Quantity { number, unit } if unit.starts_with('%') => write!(f, "{number}{unit}"),
        Value::Quantity { number, unit } => write!(f, "{number} {unit}"),
    }
}

/// Writes `node`, parenthesised when it binds looser than `min`.
pub(super) fn write_node(f: &mut fmt::Formatter<'_>, node: &Node, min: u8) -> fmt::Result {
    let paren = prec(&node.expr) < min;
    if paren {
        f.write_char('(')?;
    }
    match &node.expr {
        Expr::Glob(g) => write_str_lit(f, &g.text())?,
        Expr::Lang(l) => write!(f, "lang({l})")?,
        Expr::Kind(ks) => write!(f, "kind({})", ks.join(", "))?,
        Expr::Attr(a) => {
            write!(f, "attr({}", a.name)?;
            if let Some((cmp, v)) = &a.test {
                write!(f, " {} ", cmp.symbol())?;
                write_value(f, v)?;
            }
            f.write_char(')')?;
        }
        Expr::Not(inner) => {
            f.write_char('!')?;
            write_node(f, inner, 2)?;
        }
        Expr::And(ops) => join(f, ops, " & ", 2)?,
        Expr::Or(ops) => join(f, ops, " | ", 1)?,
    }
    if paren {
        f.write_char(')')?;
    }
    Ok(())
}

fn join(f: &mut fmt::Formatter<'_>, ops: &[Node], sep: &str, min: u8) -> fmt::Result {
    for (i, op) in ops.iter().enumerate() {
        if i > 0 {
            f.write_str(sep)?;
        }
        write_node(f, op, min)?;
    }
    Ok(())
}
