//! Mermaid renderings of the planning model (grmb-spec 17.7): per scenario a sequence diagram and
//! an activity diagram, per system a use-case diagram.
//!
//! The renderer re-reads the `.grmb` files, lowers every scenario chain to a small flow tree and
//! prints that tree twice, so the two scenario views can never disagree about an arm or a retry
//! bound. Output is deterministic: files, systems and scenarios print in sorted order.

// frob:ticket 01M4FDBG95B8D1NERFERXC0PXF

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::path::Path;

use grimble_model::ModelFiles;
use grimble_model::ast::{FileStatus, Item, Quantity, RefPath, Spanned};
use grimble_model::model::load_roots;
use grimble_model::plan::{
    Arm, Chain, Elem, GoalBlock, Hop, PlanItem, ScMember, Scenario, Tail, Variant,
};

use crate::{CheckError, GrimbleTable, read_models, walk_repo};

/// One lowered chain element or control construct of a scenario.
#[derive(Clone, Debug)]
enum Flow {
    /// A step (or included scenario) with the hop that led into it.
    Step {
        path: String,
        include: bool,
        hop: Option<Hop>,
    },
    /// A `=>` match or `handle` block: one labelled branch per arm.
    Alt {
        handle: bool,
        arms: Vec<(String, Vec<Flow>)>,
    },
    /// A bounded retry of `step`, with the optional `else` chain.
    Retry {
        step: String,
        bound: String,
        otherwise: Option<Vec<Flow>>,
    },
    /// A terminal: `end ok`, `end err(v)` or `sorry`.
    Term(String),
}

/// Everything gathered from one model root.
#[derive(Default)]
struct Plan {
    /// Actors by system (name, kind).
    actors: BTreeMap<String, BTreeSet<(String, String)>>,
    /// Goal edges by system: (from, to, label); an empty `from` means the system boundary.
    goals: BTreeMap<String, BTreeSet<(String, String, String)>>,
    /// Scenarios by system: name -> (realizes, flows).
    scenarios: BTreeMap<String, BTreeMap<String, (Vec<String>, Vec<Flow>)>>,
    /// Step outcome names by step path.
    outcomes: BTreeMap<String, Vec<String>>,
}

/// Render `max N [within Q]` the way the model wrote it.
fn bound_text(max: Option<&Spanned<String>>, within: Option<&Quantity>) -> String {
    let mut out = String::from("max");
    match max {
        Some(m) => {
            let _ = write!(out, " {}", m.value);
        }
        None => out.push_str(" ?"),
    }
    if let Some(q) = within {
        let _ = write!(out, " within {}{}", q.number, q.unit);
    }
    out
}

/// Lower an element to a step flow.
fn step_flow(elem: &Elem, hop: Option<Hop>) -> Flow {
    Flow::Step {
        path: elem.path().written(),
        include: matches!(elem, Elem::Include(_)),
        hop,
    }
}

/// Lower one arm to its label and flows.
fn arm_flows(arm: &Arm) -> (String, Vec<Flow>) {
    (arm.pattern.written(), lower(&arm.chain))
}

/// Lower a chain: its links, then the tail (match arms, retry, terminal).
fn lower(chain: &Chain) -> Vec<Flow> {
    let mut out = Vec::new();
    let mut hop = None;
    for (elem, next) in &chain.links {
        out.push(step_flow(elem, hop));
        hop = Some(*next);
    }
    match &chain.tail {
        Tail::Match { elem, arms } => {
            out.push(step_flow(elem, hop));
            out.push(Flow::Alt {
                handle: false,
                arms: arms.iter().map(arm_flows).collect(),
            });
        }
        Tail::Open(elem) => out.push(step_flow(elem, hop)),
        Tail::EndOk(_) => out.push(Flow::Term("end ok".to_owned())),
        Tail::EndErr(v) => out.push(Flow::Term(format!("end err({})", v.text))),
        Tail::Sorry(_) => out.push(Flow::Term("sorry".to_owned())),
        Tail::Retry {
            step,
            max,
            within,
            otherwise,
            ..
        } => out.push(Flow::Retry {
            step: step.written(),
            bound: bound_text(max.as_ref(), within.as_ref()),
            otherwise: otherwise.as_ref().map(|c| lower(c)),
        }),
    }
    out
}

/// Lower a scenario: its chains in order, then each `handle` block as one alt.
fn lower_scenario(sc: &Scenario) -> Vec<Flow> {
    let mut out = Vec::new();
    for m in &sc.members {
        match m {
            ScMember::Chain(_, c) => out.extend(lower(c)),
            ScMember::Handle(h) => out.push(Flow::Alt {
                handle: true,
                arms: h.arms.iter().map(arm_flows).collect(),
            }),
            ScMember::Clause(_) => {}
        }
    }
    out
}

/// Add a goal block's variants as edges `actor -> goal`, `parent -> child` and `requires`.
fn collect_goal(g: &GoalBlock, sys: &str, plan: &mut Plan) {
    let base = g.path.dotted();
    let set = plan.goals.entry(sys.to_owned()).or_default();
    let owner = g.path.segments.first().cloned().unwrap_or_default();
    let mut variant = |v: &Variant| {
        let name = format!("{base}.{}", v.name.text);
        let from = if g.path.segments.len() == 1 {
            owner.clone()
        } else {
            base.clone()
        };
        set.insert((from, name.clone(), String::new()));
        for r in &v.requires {
            let req = if r.segments.len() == 1 {
                format!("{base}.{}", r.dotted())
            } else {
                r.dotted()
            };
            set.insert((name.clone(), req, "requires".to_owned()));
        }
    };
    for v in &g.variants {
        variant(v);
    }
    for grp in &g.groups {
        for v in &grp.variants {
            variant(v);
        }
    }
}

/// Walk items, attributing planning items to the nearest enclosing system.
fn collect(items: &[Item], sys: &str, plan: &mut Plan) {
    for item in items {
        match item {
            Item::Namespace(n) => collect(&n.items, sys, plan),
            Item::Plan(p) => match &**p {
                PlanItem::System(s) => collect(&s.items, &s.name.text, plan),
                PlanItem::Actor(a) => {
                    plan.actors
                        .entry(sys.to_owned())
                        .or_default()
                        .insert((a.name.text.clone(), a.kind.text.clone()));
                }
                PlanItem::Goal(g) => collect_goal(g, sys, plan),
                PlanItem::Step(s) => {
                    if let Some(o) = &s.outcome {
                        let names = o.iter().map(|x| x.name.text.clone()).collect();
                        plan.outcomes.insert(s.target.dotted(), names);
                    }
                }
                PlanItem::Scenario(sc) => {
                    let realizes = sc.realizes.iter().map(RefPath::dotted).collect();
                    plan.scenarios
                        .entry(sys.to_owned())
                        .or_default()
                        .insert(sc.name.text.clone(), (realizes, lower_scenario(sc)));
                }
                _ => {}
            },
            _ => {}
        }
    }
}

/// The system a model's unattributed items belong to: its first declared system.
fn default_system(items: &[Item]) -> Option<String> {
    items.iter().find_map(|i| match i {
        Item::Plan(p) => match &**p {
            PlanItem::System(s) => Some(s.name.text.clone()),
            _ => None,
        },
        Item::Namespace(n) => default_system(&n.items),
        _ => None,
    })
}

/// The lifeline a step path belongs to: its owner, or `system`.
fn owner(path: &str) -> String {
    match path.rsplit_once('.') {
        Some((o, _)) => o.to_owned(),
        None => "system".to_owned(),
    }
}

/// A mermaid-safe identifier.
fn ident(s: &str) -> String {
    s.chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '_' })
        .collect()
}

/// The step an arm pattern matches, looked up among the steps used in `flows`.
fn anchor_of(
    pattern: &str,
    flows: &[Flow],
    outcomes: &BTreeMap<String, Vec<String>>,
) -> Option<String> {
    let variant = pattern.rsplit('.').next().unwrap_or(pattern);
    let mut found = None;
    visit_steps(flows, &mut |p| {
        if found.is_none()
            && outcomes
                .get(p)
                .is_some_and(|o| o.iter().any(|x| x == variant))
        {
            found = Some(p.to_owned());
        }
    });
    found
}

/// Visit every step path in `flows`, nested constructs included.
fn visit_steps(flows: &[Flow], f: &mut dyn FnMut(&str)) {
    for fl in flows {
        match fl {
            Flow::Step { path, .. } => f(path),
            Flow::Alt { arms, .. } => arms.iter().for_each(|(_, a)| visit_steps(a, f)),
            Flow::Retry {
                step, otherwise, ..
            } => {
                f(step);
                if let Some(o) = otherwise {
                    visit_steps(o, f);
                }
            }
            Flow::Term(_) => {}
        }
    }
}

/// The sequence-diagram printer state.
struct Seq<'a> {
    out: String,
    depth: usize,
    all: &'a [Flow],
    outcomes: &'a BTreeMap<String, Vec<String>>,
}

impl Seq<'_> {
    /// Append one indented line.
    fn line(&mut self, text: &str) {
        let _ = writeln!(self.out, "{}{text}", "    ".repeat(self.depth));
    }

    /// Print `flows` starting from lifeline `prev`; returns the lifeline the flow ends on.
    fn flows(&mut self, flows: &[Flow], mut prev: Option<String>) -> Option<String> {
        for fl in flows {
            match fl {
                Flow::Step { path, include, hop } => {
                    let to = owner(path);
                    let label = if *include {
                        format!("include {path}")
                    } else {
                        path.clone()
                    };
                    match (&prev, hop) {
                        (Some(from), Some(h)) => {
                            let arrow = if *h == Hop::Try { "-->>" } else { "->>" };
                            self.line(&format!("{}{arrow}{}: {label}", ident(from), ident(&to)));
                        }
                        _ => self.line(&format!("Note over {}: {label}", ident(&to))),
                    }
                    prev = Some(to);
                }
                Flow::Alt { handle, arms } => {
                    for (i, (pat, chain)) in arms.iter().enumerate() {
                        let word = if i == 0 { "alt" } else { "else" };
                        self.line(&format!("{word} {pat}"));
                        self.depth += 1;
                        let start = handle
                            .then(|| anchor_of(pat, self.all, self.outcomes).map(|a| owner(&a)))
                            .flatten()
                            .or_else(|| prev.clone());
                        self.flows(chain, start);
                        self.depth -= 1;
                    }
                    self.line("end");
                }
                Flow::Retry {
                    step,
                    bound,
                    otherwise,
                } => {
                    let to = owner(step);
                    self.line(&format!("loop retry {bound}"));
                    self.depth += 1;
                    let from = prev.clone().unwrap_or_else(|| to.clone());
                    self.line(&format!("{}-->>{}: {step}", ident(&from), ident(&to)));
                    self.depth -= 1;
                    self.line("end");
                    if let Some(o) = otherwise {
                        self.line("opt retries exhausted");
                        self.depth += 1;
                        self.flows(o, Some(to.clone()));
                        self.depth -= 1;
                        self.line("end");
                    }
                    prev = Some(to);
                }
                Flow::Term(t) => {
                    let at = prev.clone().unwrap_or_else(|| "system".to_owned());
                    self.line(&format!("Note over {}: {t}", ident(&at)));
                }
            }
        }
        prev
    }
}

/// The sequence diagram of one scenario.
fn sequence(name: &str, flows: &[Flow], outcomes: &BTreeMap<String, Vec<String>>) -> String {
    let mut lifelines = BTreeSet::new();
    visit_steps(flows, &mut |p| {
        lifelines.insert(owner(p));
    });
    let mut s = Seq {
        out: String::new(),
        depth: 1,
        all: flows,
        outcomes,
    };
    s.line(&format!("title {name}"));
    for l in &lifelines {
        s.line(&format!("participant {} as {l}", ident(l)));
    }
    s.flows(flows, None);
    format!("sequenceDiagram\n{}", s.out)
}

/// The activity-diagram printer state.
struct Act<'a> {
    out: String,
    nodes: BTreeMap<String, String>,
    terms: usize,
    all: &'a [Flow],
    outcomes: &'a BTreeMap<String, Vec<String>>,
}

impl Act<'_> {
    /// The node id of `path`, declaring it on first use.
    fn node(&mut self, path: &str, include: bool) -> String {
        if let Some(id) = self.nodes.get(path) {
            return id.clone();
        }
        let id = format!("n{}", self.nodes.len());
        let label = if include {
            format!("include {path}")
        } else {
            path.to_owned()
        };
        let _ = writeln!(self.out, "    {id}[\"{label}\"]");
        self.nodes.insert(path.to_owned(), id.clone());
        id
    }

    /// Print one edge, with an optional label.
    fn edge(&mut self, from: &str, to: &str, label: &str) {
        if label.is_empty() {
            let _ = writeln!(self.out, "    {from} --> {to}");
        } else {
            let _ = writeln!(self.out, "    {from} -->|\"{label}\"| {to}");
        }
    }

    /// Print `flows` entered from `prev` (node id plus pending edge label); returns the last node.
    fn flows(
        &mut self,
        flows: &[Flow],
        mut prev: Option<(String, String)>,
    ) -> Option<(String, String)> {
        for fl in flows {
            match fl {
                Flow::Step { path, include, hop } => {
                    let id = self.node(path, *include);
                    if let Some((from, pending)) = prev.take() {
                        let mut label = pending;
                        if *hop == Some(Hop::Try) {
                            label = if label.is_empty() {
                                "try".to_owned()
                            } else {
                                format!("{label}, try")
                            };
                        }
                        self.edge(&from, &id, &label);
                    }
                    prev = Some((id, String::new()));
                }
                Flow::Alt { handle, arms } => {
                    for (pat, chain) in arms {
                        let anchor = if *handle {
                            anchor_of(pat, self.all, self.outcomes)
                        } else {
                            None
                        };
                        let from = anchor
                            .map(|a| self.node(&a, false))
                            .or_else(|| prev.as_ref().map(|p| p.0.clone()));
                        if let Some(f) = from {
                            self.flows(chain, Some((f, pat.clone())));
                        }
                    }
                    prev = None;
                }
                Flow::Retry {
                    step,
                    bound,
                    otherwise,
                } => {
                    let id = self.node(step, false);
                    let (from, pending) =
                        prev.take().unwrap_or_else(|| (id.clone(), String::new()));
                    let label = if pending.is_empty() {
                        format!("retry {bound}")
                    } else {
                        format!("{pending}, retry {bound}")
                    };
                    self.edge(&from, &id, &label);
                    if let Some(o) = otherwise {
                        self.flows(o, Some((id, "retries exhausted".to_owned())));
                    }
                }
                Flow::Term(t) => {
                    let id = format!("t{}", self.terms);
                    self.terms += 1;
                    let _ = writeln!(self.out, "    {id}([\"{t}\"])");
                    if let Some((from, pending)) = prev.take() {
                        self.edge(&from, &id, &pending);
                    }
                }
            }
        }
        prev
    }
}

/// The activity diagram of one scenario.
fn activity(name: &str, flows: &[Flow], outcomes: &BTreeMap<String, Vec<String>>) -> String {
    let mut a = Act {
        out: String::new(),
        nodes: BTreeMap::new(),
        terms: 0,
        all: flows,
        outcomes,
    };
    let _ = writeln!(a.out, "    start((\"{name}\"))");
    a.flows(flows, Some(("start".to_owned(), String::new())));
    format!("flowchart TD\n{}", a.out)
}

/// The use-case diagram of one system: actors outside the boundary, goals inside.
fn use_case(
    sys: &str,
    actors: &BTreeSet<(String, String)>,
    goals: &BTreeSet<(String, String, String)>,
    scenarios: &BTreeMap<String, (Vec<String>, Vec<Flow>)>,
) -> String {
    let mut out = String::from("flowchart LR\n");
    for (a, kind) in actors {
        let _ = writeln!(out, "    a_{}[\"{a} ({kind})\"]", ident(a));
    }
    let mut names = BTreeSet::new();
    for (from, to, _) in goals {
        names.insert(to.clone());
        if !actors.iter().any(|(a, _)| a == from) {
            names.insert(from.clone());
        }
    }
    let _ = writeln!(out, "    subgraph sys_{}[\"{sys}\"]", ident(sys));
    for g in &names {
        let _ = writeln!(out, "        g_{}([\"{g}\"])", ident(g));
    }
    for (name, (realizes, _)) in scenarios {
        let _ = writeln!(out, "        s_{}[\"scenario {name}\"]", ident(name));
        let _ = realizes;
    }
    let _ = writeln!(out, "    end");
    for (from, to, label) in goals {
        let src = if actors.iter().any(|(a, _)| a == from) {
            format!("a_{}", ident(from))
        } else {
            format!("g_{}", ident(from))
        };
        let dst = format!("g_{}", ident(to));
        if label.is_empty() {
            let _ = writeln!(out, "    {src} --> {dst}");
        } else {
            let _ = writeln!(out, "    {src} -.->|\"{label}\"| {dst}");
        }
    }
    for (name, (realizes, _)) in scenarios {
        for r in realizes {
            let _ = writeln!(
                out,
                "    s_{} -.->|\"realizes\"| g_{}",
                ident(name),
                ident(r)
            );
        }
    }
    out
}

/// Append one titled, fenced mermaid block.
fn block(out: &mut String, heading: &str, body: &str) {
    let _ = write!(out, "### {heading}\n\n```mermaid\n{body}```\n\n");
}

/// Render every system and scenario of `model` as mermaid diagrams (empty when none are planned).
pub fn render(model: &ModelFiles) -> String {
    let mut out = String::new();
    for root in load_roots(model) {
        let mut plan = Plan::default();
        let mut files: Vec<_> = root
            .files
            .iter()
            .filter(|f| f.parsed.status == FileStatus::Parsed)
            .collect();
        files.sort_by(|a, b| a.parsed.path.cmp(&b.parsed.path));
        let default = files
            .iter()
            .find_map(|f| default_system(&f.parsed.items))
            .unwrap_or_else(|| "system".to_owned());
        for f in &files {
            collect(&f.parsed.items, &default, &mut plan);
        }
        let mut systems: BTreeSet<&String> = plan.actors.keys().collect();
        systems.extend(plan.goals.keys());
        systems.extend(plan.scenarios.keys());
        tracing::debug!(root = %root.root, systems = systems.len(), "mermaid planning collected");
        let empty_a = BTreeSet::new();
        let empty_g = BTreeSet::new();
        let empty_s = BTreeMap::new();
        for sys in systems {
            let scs = plan.scenarios.get(sys).unwrap_or(&empty_s);
            let uc = use_case(
                sys,
                plan.actors.get(sys).unwrap_or(&empty_a),
                plan.goals.get(sys).unwrap_or(&empty_g),
                scs,
            );
            block(&mut out, &format!("use-case: {sys}"), &uc);
            for (name, (_, flows)) in scs {
                block(
                    &mut out,
                    &format!("sequence: {sys}.{name}"),
                    &sequence(name, flows, &plan.outcomes),
                );
                block(
                    &mut out,
                    &format!("activity: {sys}.{name}"),
                    &activity(name, flows, &plan.outcomes),
                );
            }
        }
    }
    out
}

/// Read the repository's models from `root` and render them with [`render`].
///
/// # Errors
///
/// [`CheckError`] for a bad `grimble.toml` table or a failed walk.
pub fn render_repo(root: &Path) -> Result<String, CheckError> {
    let entries = walk_repo(root)?;
    let table = GrimbleTable::load(root)?;
    let content = gob_walk::ContentSource::locate(root);
    let model = content.with_reader(|r| read_models(root, &entries, &table, &mut |p| r.read(p)));
    let text = render(&model);
    tracing::info!(bytes = text.len(), "mermaid rendered");
    Ok(text)
}
