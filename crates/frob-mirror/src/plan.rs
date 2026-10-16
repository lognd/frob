//! Work classes (mirror.md 3.2, F8): strict class priority, round-robin resumption inside a class.
//!
//! Class 1 is served before class 2 and so on; inside a class a run resumes after the last
//! ticket the previous run completed, so a small budget cannot starve later tickets.

// frob:ticket 01M4052RW8F31VNBZ6AJM20TF3

use std::collections::BTreeMap;

use tracing::{debug, trace};

use crate::budget::Plan;

/// The five work classes, declared in strict priority order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum WorkClass {
    /// Recovery of uncertain creates.
    Recovery,
    /// Ledger-driven updates, oldest first.
    Update,
    /// Creates, oldest first.
    Create,
    /// Reconcile of changed issues.
    Reconcile,
    /// The round-robin sweep.
    Sweep,
}

impl WorkClass {
    /// Whether work in this class writes to the tracker (and so spends a mutation).
    pub fn mutates(self) -> bool {
        matches!(self, Self::Recovery | Self::Update | Self::Create)
    }
}

/// One unit of work: a ticket to handle in a class.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkItem {
    /// The class this work belongs to.
    pub class: WorkClass,
    /// Age key; lower is older and served first.
    pub age: u64,
    /// The ticket id (tie-break and cursor identity).
    pub ticket: String,
}

impl WorkItem {
    fn key(&self) -> (u64, &str) {
        (self.age, self.ticket.as_str())
    }
}

/// Per-class resume points: the last completed item of each class.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Cursors {
    last: BTreeMap<WorkClass, (u64, String)>,
}

impl Cursors {
    /// Record `item` as the last completed work of its class.
    pub fn complete(&mut self, item: &WorkItem) {
        trace!(class = ?item.class, ticket = %item.ticket, "plan: cursor advanced");
        self.last
            .insert(item.class, (item.age, item.ticket.clone()));
    }

    /// The last completed (age, ticket) of `class`, if any.
    pub fn get(&self, class: WorkClass) -> Option<(u64, &str)> {
        self.last.get(&class).map(|(a, t)| (*a, t.as_str()))
    }
}

/// Order one class: oldest first, rotated to start after the cursor.
fn rotate(mut items: Vec<WorkItem>, cursor: Option<(u64, &str)>) -> Vec<WorkItem> {
    items.sort_by(|a, b| a.key().cmp(&b.key()));
    if let Some(c) = cursor {
        let start = items.iter().position(|i| i.key() > c).unwrap_or(0);
        items.rotate_left(start);
    }
    items
}

/// Choose the work one run does: classes in strict priority, each rotated after its cursor.
///
/// Spends `cost` calls per item against `plan.calls`; mutating classes also spend
/// `plan.mutations`, and creates `plan.creates`. A class that cannot be fully served ends
/// the run: lower classes never jump ahead of unserved higher-class work.
pub fn select(items: Vec<WorkItem>, cursors: &Cursors, plan: &Plan, cost: u64) -> Vec<WorkItem> {
    let mut by_class: BTreeMap<WorkClass, Vec<WorkItem>> = BTreeMap::new();
    for i in items {
        by_class.entry(i.class).or_default().push(i);
    }
    let (mut calls, mut muts, mut creates) = (plan.calls, plan.mutations, plan.creates);
    let mut out = Vec::new();
    'classes: for (class, group) in by_class {
        for item in rotate(group, cursors.get(class)) {
            let fits = calls >= cost
                && (!class.mutates() || muts > 0)
                && (class != WorkClass::Create || creates > 0);
            if !fits {
                debug!(?class, ticket = %item.ticket, "plan: budget exhausted");
                break 'classes;
            }
            calls -= cost;
            if class.mutates() {
                muts -= 1;
            }
            if class == WorkClass::Create {
                creates -= 1;
            }
            out.push(item);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use super::*;

    fn item(class: WorkClass, age: u64, t: &str) -> WorkItem {
        WorkItem {
            class,
            age,
            ticket: t.into(),
        }
    }

    fn plan(calls: u64) -> Plan {
        Plan {
            calls,
            creates: 50,
            mutations: 300,
            spacing: Duration::ZERO,
        }
    }

    // frob:tests select
    #[test]
    fn higher_class_is_exhausted_before_lower() {
        use WorkClass::*;
        let items = vec![
            item(Sweep, 1, "s"),
            item(Create, 1, "c"),
            item(Reconcile, 1, "r"),
            item(Update, 2, "u2"),
            item(Update, 1, "u1"),
            item(Recovery, 1, "x"),
        ];
        let got = select(items.clone(), &Cursors::default(), &plan(12), 3);
        let ids: Vec<_> = got.iter().map(|i| i.ticket.as_str()).collect();
        assert_eq!(ids, ["x", "u1", "u2", "c"]);
        let all = select(items, &Cursors::default(), &plan(100), 3);
        assert_eq!(all.len(), 6);
        assert_eq!(all[5].ticket, "s");
    }

    // frob:tests select
    #[test]
    fn small_budget_does_not_starve_second_ticket() {
        let items = vec![
            item(WorkClass::Update, 1, "t1"),
            item(WorkClass::Update, 2, "t2"),
        ];
        let mut cur = Cursors::default();
        let mut done = Vec::new();
        for _ in 0..2 {
            let got = select(items.clone(), &cur, &plan(4), 3);
            assert_eq!(got.len(), 1);
            cur.complete(&got[0]);
            done.push(got[0].ticket.clone());
        }
        assert_eq!(done, ["t1", "t2"]);
    }

    // frob:tests select
    #[test]
    fn class_resumes_after_last_completed_and_wraps() {
        let items = vec![
            item(WorkClass::Create, 1, "a"),
            item(WorkClass::Create, 2, "b"),
            item(WorkClass::Create, 3, "c"),
        ];
        let mut cur = Cursors::default();
        cur.complete(&items[1]);
        let got = select(items.clone(), &cur, &plan(9), 3);
        let ids: Vec<_> = got.iter().map(|i| i.ticket.as_str()).collect();
        assert_eq!(ids, ["c", "a", "b"]);
        cur.complete(&items[2]);
        let got = select(items, &cur, &plan(3), 3);
        assert_eq!(got[0].ticket, "a");
    }
}
