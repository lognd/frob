//! Index read benchmarks over 1000 synthetic tickets (target: well under 50 ms warm).

#![allow(missing_docs, reason = "criterion_group! generates undocumented items")]

use std::hint::black_box;

use criterion::{Criterion, criterion_group, criterion_main};
use frob_ledger::TicketId;
use frob_ledger::index::{Index, ListFilter};
use frob_ledger::model::{
    Category, Frontmatter, Link, LinkKind, Priority, Stamp, Ticket, TicketType,
};

const TICKETS: usize = 1000;

fn synthetic(n: usize, ids: &[TicketId]) -> Ticket {
    let blocker = (!n.is_multiple_of(10)).then(|| ids[n - 1]);
    Ticket {
        front: Frontmatter {
            id: ids[n],
            title: format!("Synthetic ticket {n}"),
            ty: if n.is_multiple_of(7) {
                TicketType::Bug
            } else {
                TicketType::Task
            },
            flavour: None,
            category: if n.is_multiple_of(3) {
                Category::Done
            } else {
                Category::Todo
            },
            outcome: (n.is_multiple_of(3)).then_some(frob_ledger::model::Outcome::Done),
            priority: Priority::Medium,
            points: None,
            parent: (!n.is_multiple_of(50)).then(|| ids[n - n % 50]),
            reporter: "bench".into(),
            assignee: None,
            created: Stamp::from_unix(1_790_000_000),
            updated: Stamp::from_unix(1_790_000_000),
            persona: None,
            capability: None,
            outcome_text: None,
            idempotency_key: None,
            aliases: vec![format!("T-{n:04}")],
            labels: vec![format!("l{}", n % 20)],
            scope: vec![format!("crates/c{}/**", n % 40)],
            links: blocker
                .map(|b| Link {
                    kind: LinkKind::BlockedBy,
                    target: b,
                })
                .into_iter()
                .collect(),
            acceptance: vec![],
        },
        body: "Body text.\n".repeat(20),
    }
}

fn bench(c: &mut Criterion) {
    let dir = tempfile::tempdir().expect("tempdir");
    let ids: Vec<TicketId> = (0..TICKETS).map(|_| TicketId::mint()).collect();
    let tickets: Vec<Ticket> = (0..TICKETS).map(|n| synthetic(n, &ids)).collect();
    let mut index = Index::open(&dir.path().join("bench.sqlite")).expect("open");
    index.rebuild("bench", &tickets, 7).expect("rebuild");
    let handle = index
        .summary(ids[TICKETS / 2])
        .expect("sql")
        .expect("row")
        .handle;

    c.bench_function("rebuild_1000", |b| {
        b.iter(|| {
            index
                .rebuild("bench", black_box(&tickets), 7)
                .expect("rebuild");
        });
    });
    let db = dir.path().join("bench.sqlite");
    c.bench_function("show_warm", |b| {
        b.iter(|| {
            let idx = Index::open(&db).expect("open");
            let id = idx.resolve(black_box(&handle)).expect("resolve");
            black_box((idx.summary(id).expect("sql"), idx.get(id).expect("sql")))
        });
    });
    c.bench_function("list_all_warm", |b| {
        b.iter(|| {
            let idx = Index::open(&db).expect("open");
            black_box(idx.list(&ListFilter::default()).expect("list"))
        });
    });
    let doable = ListFilter {
        category: Some(Category::Todo),
        blocked: Some(false),
        ..ListFilter::default()
    };
    c.bench_function("doable_warm", |b| {
        b.iter(|| {
            let idx = Index::open(&db).expect("open");
            black_box(idx.list(&doable).expect("list"))
        });
    });
}

criterion_group!(benches, bench);
criterion_main!(benches);
