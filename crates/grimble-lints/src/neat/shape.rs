//! Syntax-only NEAT rules: size, nesting, flags, magic values, section comments, hidden state,
//! ambient calls, undeclared effects, thin hooks and parameter-object candidates.

// frob:ticket 01M59QKE60PDB1GDWTDEBAQ4JG

use std::collections::BTreeSet;

use tree_sitter::Node;

use super::unit::{Claim, Unit};
use super::{Options, Rule, effects};

/// One shape finding before it is given a range: the rule, the node it points at, the message.
pub struct Raw<'t> {
    /// The rule that fired.
    pub rule: Rule,
    /// The node the finding points at.
    pub node: Node<'t>,
    /// What to do about it.
    pub message: String,
}

const BRANCHES: [&str; 5] = [
    "if_expression",
    "match_expression",
    "for_expression",
    "while_expression",
    "loop_expression",
];

const LOOPS: [&str; 3] = ["for_expression", "while_expression", "loop_expression"];

/// Interior-mutability type names that make a `static` a hidden mutable global.
const MUTABLE_TYPES: [&str; 8] = [
    "Mutex", "RwLock", "Atomic", "RefCell", "Cell", "OnceLock", "OnceCell", "LazyLock",
];

/// Comment openers that label a phase of a body.
const SECTION_WORDS: [&str; 5] = ["step ", "phase ", "section ", "part ", "stage "];

fn descendants(root: Node<'_>) -> Vec<Node<'_>> {
    let mut out = Vec::new();
    let mut stack = vec![root];
    while let Some(n) = stack.pop() {
        out.push(n);
        let mut cur = n.walk();
        stack.extend(n.children(&mut cur));
    }
    out.sort_by_key(Node::start_byte);
    out
}

fn is_else_if(n: Node<'_>) -> bool {
    n.kind() == "if_expression" && n.parent().is_some_and(|p| p.kind() == "else_clause")
}

/// Every parameter node of the unit, `self` excluded.
fn param_nodes<'t>(unit: &Unit<'t>) -> Vec<Node<'t>> {
    let Some(list) = unit.node.child_by_field_name("parameters") else {
        return Vec::new();
    };
    let mut cur = list.walk();
    list.children(&mut cur)
        .filter(|p| p.kind() == "parameter")
        .collect()
}

/// The `(name, type)` text pairs of the unit's parameters.
fn param_pairs(unit: &Unit<'_>, src: &str) -> BTreeSet<(String, String)> {
    param_nodes(unit)
        .into_iter()
        .filter_map(|p| {
            let name = p.child_by_field_name("pattern")?;
            let ty = p.child_by_field_name("type")?;
            Some((
                src[name.byte_range()].to_owned(),
                src[ty.byte_range()].to_owned(),
            ))
        })
        .collect()
}

/// Deepest branch nesting under `n` and the node that reaches it.
fn deepest(n: Node<'_>, depth: usize) -> (usize, Node<'_>) {
    let here = if BRANCHES.contains(&n.kind()) && !is_else_if(n) {
        depth + 1
    } else {
        depth
    };
    let mut best = (here, n);
    let mut cur = n.walk();
    for c in n.children(&mut cur) {
        let found = deepest(c, here);
        if found.0 > best.0 {
            best = found;
        }
    }
    best
}

/// Sonar-style cognitive complexity of `n` at nesting `level`.
fn cognitive(n: Node<'_>, src: &str, level: usize) -> usize {
    let mut total = 0;
    let mut next = level;
    match n.kind() {
        k if BRANCHES.contains(&k) => {
            total += if is_else_if(n) { 1 } else { 1 + level };
            next = level + 1;
        }
        "else_clause"
            if n.named_child(0)
                .is_some_and(|c| c.kind() != "if_expression") =>
        {
            total += 1;
        }
        "binary_expression" => {
            let op = n
                .child_by_field_name("operator")
                .map(|o| &src[o.byte_range()]);
            if matches!(op, Some("&&" | "||")) {
                let same_parent = n.parent().is_some_and(|p| {
                    p.kind() == "binary_expression"
                        && p.child_by_field_name("operator")
                            .map(|o| &src[o.byte_range()])
                            == op
                });
                total += usize::from(!same_parent);
            }
        }
        _ => {}
    }
    let mut cur = n.walk();
    for c in n.children(&mut cur) {
        total += cognitive(c, src, next);
    }
    total
}

fn statements(body: Node<'_>) -> usize {
    descendants(body)
        .into_iter()
        .filter(|n| matches!(n.kind(), "expression_statement" | "let_declaration"))
        .count()
}

fn section_comment(text: &str) -> bool {
    let body = text.trim_start_matches('/').trim().to_lowercase();
    let rule_line = !body.is_empty()
        && body
            .chars()
            .all(|c| matches!(c, '-' | '=' | '#' | '*' | ' '));
    let banner = body.starts_with("---") || body.starts_with("===");
    rule_line || banner || SECTION_WORDS.iter().any(|w| body.starts_with(w))
}

/// Names of the file's hidden mutable globals: `static mut` and interior-mutable statics.
pub fn mutable_globals(root: Node<'_>, src: &str) -> BTreeSet<String> {
    descendants(root)
        .into_iter()
        .filter(|n| n.kind() == "static_item")
        .filter_map(|n| {
            let name = &src[n.child_by_field_name("name")?.byte_range()];
            let ty = &src[n.child_by_field_name("type")?.byte_range()];
            let mutable = n
                .children(&mut n.walk())
                .any(|c| c.kind() == "mutable_specifier")
                || MUTABLE_TYPES.iter().any(|t| ty.contains(t));
            mutable.then(|| name.to_owned())
        })
        .collect()
}

/// True when the unit is a hook: marked, or named with a configured hook prefix.
fn is_hook(unit: &Unit<'_>, options: &Options) -> bool {
    unit.claims.contains(&Claim::Hook)
        || options
            .hook_prefixes
            .iter()
            .any(|p| unit.name.starts_with(p.as_str()))
}

/// The per-unit shape findings (every rule except `NEAT008`, which needs all units).
pub fn unit_findings<'t>(
    unit: &Unit<'t>,
    src: &str,
    options: &Options,
    globals: &BTreeSet<String>,
) -> Vec<Raw<'t>> {
    let mut out = Vec::new();
    let name = &unit.name;
    let params = param_nodes(unit);
    if params.len() > options.max_params {
        out.push(Raw {
            rule: Rule::TooManyParams,
            node: unit.node,
            message: format!(
                "`{name}` takes {} parameters (limit {}); group related ones into a type",
                params.len(),
                options.max_params
            ),
        });
    }
    for p in &params {
        if p.child_by_field_name("type")
            .is_some_and(|t| &src[t.byte_range()] == "bool")
        {
            out.push(Raw {
                rule: Rule::BooleanFlagParam,
                node: *p,
                message: format!(
                    "`{name}` takes a boolean flag `{}`; split it or use an enum",
                    &src[p.byte_range()]
                ),
            });
        }
    }
    if options.require_effects
        && unit.claims.is_empty()
        && unit
            .node
            .children(&mut unit.node.walk())
            .any(|c| c.kind() == "visibility_modifier")
    {
        out.push(Raw {
            rule: Rule::EffectsUndeclared,
            node: unit.node,
            message: format!("public `{name}` declares no effects claim"),
        });
    }
    if is_hook(unit, options)
        && let Some(body) = unit.node.child_by_field_name("body")
    {
        let n = statements(body);
        if n > options.hook_statements {
            out.push(Raw {
                rule: Rule::ThinHook,
                node: unit.node,
                message: format!(
                    "hook `{name}` holds {n} statements (limit {}); delegate to a named unit",
                    options.hook_statements
                ),
            });
        }
    }
    if let Some(body) = unit.node.child_by_field_name("body") {
        body_findings(unit, body, src, options, globals, &mut out);
    }
    out
}

/// `NEAT001`: functions longer than `max_fn_lines`.
fn length_finding<'t>(unit: &Unit<'t>, options: &Options) -> Option<Raw<'t>> {
    let lines = unit.node.end_position().row - unit.node.start_position().row + 1;
    (options.max_fn_lines > 0 && lines > options.max_fn_lines).then(|| Raw {
        rule: Rule::FunctionTooLong,
        node: unit.node,
        message: format!(
            "`{}` spans {lines} lines (limit {})",
            unit.name, options.max_fn_lines
        ),
    })
}

/// `NEAT004`: bodies nested deeper than `max_depth`.
fn depth_finding<'t>(unit: &Unit<'t>, body: Node<'t>, options: &Options) -> Option<Raw<'t>> {
    let (depth, at) = deepest(body, 0);
    (depth > options.max_depth).then(|| Raw {
        rule: Rule::NestingTooDeep,
        node: at,
        message: format!(
            "`{}` nests {depth} levels deep (limit {}); use early returns or extract",
            unit.name, options.max_depth
        ),
    })
}

/// `NEAT005`: bodies whose cognitive complexity exceeds `max_cognitive`.
fn cognitive_finding<'t>(
    unit: &Unit<'t>,
    body: Node<'t>,
    src: &str,
    options: &Options,
) -> Option<Raw<'t>> {
    let score = cognitive(body, src, 0);
    (options.max_cognitive > 0 && score > options.max_cognitive).then(|| Raw {
        rule: Rule::CognitiveComplexity,
        node: unit.node,
        message: format!(
            "`{}` has cognitive complexity {score} (limit {})",
            unit.name, options.max_cognitive
        ),
    })
}

/// `NEAT009`: a numeric literal other than the trivial ones.
fn magic_value<'t>(n: Node<'t>, src: &str, name: &str) -> Option<Raw<'t>> {
    let text = src[n.byte_range()].replace('_', "");
    let digits: String = text
        .chars()
        .take_while(|c| c.is_ascii_digit() || *c == '.')
        .collect();
    if matches!(digits.as_str(), "0" | "1" | "2" | "0.0" | "1.0") {
        return None;
    }
    Some(Raw {
        rule: Rule::MagicValue,
        node: n,
        message: format!(
            "magic value `{}` in `{name}`; give it a name",
            &src[n.byte_range()]
        ),
    })
}

/// Walks a unit body for the token-level rules (loops, comments, globals, ambient calls).
fn body_findings<'t>(
    unit: &Unit<'t>,
    body: Node<'t>,
    src: &str,
    options: &Options,
    globals: &BTreeSet<String>,
    out: &mut Vec<Raw<'t>>,
) {
    let name = &unit.name;
    out.extend(length_finding(unit, options));
    out.extend(depth_finding(unit, body, options));
    out.extend(cognitive_finding(unit, body, src, options));
    if unit.is_shell() {
        return;
    }
    let all = descendants(body);
    let mut sections = Vec::new();
    for n in &all {
        match n.kind() {
            k if LOOPS.contains(&k) && options.raw_loop_statements > 0 => {
                let size = n.child_by_field_name("body").map_or(0, statements);
                if size > options.raw_loop_statements {
                    out.push(Raw {
                        rule: Rule::RawLoop,
                        node: *n,
                        message: format!("loop in `{name}` holds {size} statements (limit {}); name it as a unit", options.raw_loop_statements),
                    });
                }
            }
            "line_comment" | "block_comment" if section_comment(&src[n.byte_range()]) => {
                sections.push(*n);
            }
            "integer_literal" | "float_literal" if options.magic_values => {
                out.extend(magic_value(*n, src, name));
            }
            "identifier" if globals.contains(&src[n.byte_range()]) => out.push(Raw {
                rule: Rule::HiddenStateRead,
                node: *n,
                message: format!(
                    "`{name}` touches the mutable global `{}`; pass it in",
                    &src[n.byte_range()]
                ),
            }),
            _ => {}
        }
    }
    if sections.len() >= 2 {
        out.push(Raw {
            rule: Rule::SectionComment,
            node: sections[0],
            message: format!(
                "`{name}` labels {} phases with comments; extract each into a named unit",
                sections.len()
            ),
        });
    }
    if unit.ceiling().is_none() {
        for (node, atom) in effects::direct_hits(unit, src, options) {
            out.push(Raw {
                rule: Rule::AmbientSourceCall,
                node,
                message: format!(
                    "`{name}` calls an ambient {} source; inject it or mark the unit `frob:shell`",
                    atom.word()
                ),
            });
        }
    }
}

/// `NEAT008`: units that repeat the same `min` or more `(name, type)` parameters.
pub fn param_object_candidates<'t>(units: &[Unit<'t>], src: &str, min: usize) -> Vec<Raw<'t>> {
    let pairs: Vec<_> = units.iter().map(|u| param_pairs(u, src)).collect();
    let mut out = Vec::new();
    for (i, u) in units.iter().enumerate() {
        let twin = pairs
            .iter()
            .enumerate()
            .find(|(j, p)| *j != i && min > 0 && p.intersection(&pairs[i]).count() >= min);
        if let Some((j, _)) = twin {
            out.push(Raw {
                rule: Rule::ParamObjectCandidate,
                node: u.node,
                message: format!(
                    "`{}` repeats {min}+ parameters of `{}`; group them into a type",
                    u.name, units[j].name
                ),
            });
        }
    }
    out
}
