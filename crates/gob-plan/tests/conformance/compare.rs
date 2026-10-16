//! Running a rule two ways over one input and rendering both as canonical JSON.

// frob:ticket 01M3ZX7HRM8SVB3607V973VQTH

use gob_plan::exec::Input;
use gob_plan::exec::outcome::{Kind, Outcomes, outcomes};
use gob_plan::exec::relations::Relations;
use gob_plan::plan::Plan;
use serde_json::{Value, json};

/// One input a rule is run over.
pub struct Case {
    /// Where the input came from, for failure messages.
    pub label: String,
    /// The language the source is folded in.
    pub lang: String,
    /// The source text.
    pub text: String,
}

/// A way of running a rule: the compiled-in module or the plan interpreter.
pub type Runner<'a> = &'a dyn Fn(&Input<'_>, &Relations) -> Result<Outcomes, String>;

/// The plan interpreter as a [`Runner`].
pub fn interpret(plan: &Plan) -> impl Fn(&Input<'_>, &Relations) -> Result<Outcomes, String> + '_ {
    move |input, rels| outcomes(plan, input, rels).map_err(|e| e.to_string())
}

/// Renders `out` as the JSON both sides must agree on, one value per finding.
pub fn render(out: &Outcomes, model: &gob_ir::Model, source: &gob_text::SourceText) -> Vec<Value> {
    let mut v: Vec<Value> = out
        .findings
        .iter()
        .map(|f| {
            let at = f.subject.and_then(|n| {
                let span = model.term().node(n).location().span()?;
                source.line_col(span.range.start())
            });
            json!({
                "kind": match f.kind { Kind::Fire => "fire", Kind::Unresolved => "unresolved" },
                "at": at.map(|lc| format!("{}:{}", lc.line, lc.col)),
                "report": f.report,
                "notes": f.notes,
                "reasons": f.reasons.iter().map(|r| format!("{r:?}")).collect::<Vec<_>>(),
                "witnesses": f.witnesses.iter().map(|w| format!("{w:?}")).collect::<Vec<_>>(),
                "row": format!("{:?}", out.rows.get(f.row)),
            })
        })
        .collect();
    v.push(json!({ "clean": out.clean, "truncated": out.truncated, "rows": out.rows.len() }));
    v
}

/// Where two runs first differ.
#[derive(Debug)]
pub struct Divergence {
    /// The rule id.
    pub rule: String,
    /// The input label.
    pub case: String,
    /// The index of the first differing finding.
    pub index: usize,
    /// What the compiled-in side said.
    pub compiled: String,
    /// What the plan side said.
    pub plan: String,
}

impl std::fmt::Display for Divergence {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "rule {} diverges on {}: first differing finding #{}: compiled-in {} vs plan {}",
            self.rule, self.case, self.index, self.compiled, self.plan
        )
    }
}

/// Runs `compiled` and `plan` over `case`; `Err` names the rule and the first differing finding.
pub fn conform(
    rule: &str,
    case: &Case,
    compiled: Runner<'_>,
    plan: Runner<'_>,
) -> Result<usize, Divergence> {
    let Ok(model) = gob_symbols::model_of_source(&case.lang, &case.text) else {
        return Ok(0);
    };
    let Ok(source) = gob_text::SourceText::new(case.text.clone()) else {
        return Ok(0);
    };
    let input = Input {
        model: &model,
        source: Some(&source),
    };
    let rels = Relations::new();
    let side = |r: Runner<'_>| match r(&input, &rels) {
        Ok(o) => render(&o, &model, &source),
        Err(e) => vec![json!({ "error": e })],
    };
    let (a, b) = (side(compiled), side(plan));
    let (ja, jb) = (
        serde_json::to_string(&a).unwrap_or_default(),
        serde_json::to_string(&b).unwrap_or_default(),
    );
    if ja == jb {
        tracing::debug!(rule, case = %case.label, findings = a.len(), "conforms");
        return Ok(a.len() - 1);
    }
    let index = (0..a.len().max(b.len()))
        .find(|&i| a.get(i) != b.get(i))
        .unwrap_or(0);
    let show = |v: &[Value]| {
        v.get(index)
            .map_or_else(|| "<none>".to_owned(), Value::to_string)
    };
    Err(Divergence {
        rule: rule.to_owned(),
        case: case.label.clone(),
        index,
        compiled: show(&a),
        plan: show(&b),
    })
}
