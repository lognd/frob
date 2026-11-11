//! Renders a finding's report message: the template's `{var.field}` placeholders read the field
//! off the finding's subject node, so a host can show the text the rule's author wrote.

// frob:ticket 01M71T80ZZPW5Z00CKF3ANQ2X3

use crate::exec::core::Reader;
use crate::exec::outcome::Finding;
use crate::exec::{Datum, Input, Scalar};
use crate::plan::Plan;

/// The message of `finding`: its report's template with each `{var.field}` replaced by the field of
/// the subject node. A placeholder that cannot be read (no subject, absent or unknown field) is kept verbatim.
pub fn render_message(plan: &Plan, input: &Input<'_>, finding: &Finding) -> String {
    let p = plan.parts();
    let Some(template) = p
        .reports
        .get(finding.report)
        .and_then(|r| p.strings.get(r.message as usize))
    else {
        tracing::warn!(
            report = finding.report,
            "finding names a report the plan lacks"
        );
        return String::new();
    };
    let reader = Reader {
        model: input.model,
        source: input.source,
    };
    let mut out = String::with_capacity(template.len());
    let mut rest = template.as_str();
    while let Some(open) = rest.find('{') {
        out.push_str(&rest[..open]);
        let tail = &rest[open + 1..];
        let Some(close) = tail.find('}') else {
            out.push_str(&rest[open..]);
            rest = "";
            break;
        };
        let holder = &tail[..close];
        let read = match (finding.subject, holder.split_once('.')) {
            (Some(node), Some((_, field))) => reader.field(node, field),
            _ => Datum::Unknown,
        };
        match read {
            Datum::Known(Scalar::Str(s)) => out.push_str(&s),
            Datum::Known(Scalar::Int(i)) => out.push_str(&i.to_string()),
            Datum::Known(Scalar::Bool(b)) => out.push_str(&b.to_string()),
            _ => {
                tracing::debug!(placeholder = holder, "message placeholder left unfilled");
                out.push('{');
                out.push_str(holder);
                out.push('}');
            }
        }
        rest = &tail[close + 1..];
    }
    out.push_str(rest);
    out
}
