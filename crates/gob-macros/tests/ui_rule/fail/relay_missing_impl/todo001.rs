use gob_rules::rule;

pub trait ObligationHost {}

#[rule(
    id = "TODO001",
    slug = "bare-work-marker",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    body = relay,
    fix = Manual,
    applies = universal(needs = [Comments], min_fidelity = F1),
    host = ObligationHost,
    version = 1,
    since = "0.0.0",
)]
pub struct Todo001;



fn main() {}
