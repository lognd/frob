+++
id = "01M3AXSDBCZ0WN62JE8P0BQRA2"
title = "STORE3xx declared-vs-observed via strata"
type = "story"
category = "todo"
priority = "low"
parent = "01M38BCP8YSPMT8SG9Y3VM7F8C"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:26Z"
aliases = ["T-6508"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
+++

The paradigm-level mismatches (many-to-many in a document store, ACID
writes against a non-transactional store, graph-shaped traversal
reimplemented relationally, a search index treated as source of truth)
are only decidable once the design states WHICH store a code path talks
to and what KIND it is -- exactly the `engine` slot on strata's `store`
node plus its `code=` binding (`_infra.py::_store_base_attrs` already
emits `engine=<ident>`, currently read by nothing). Four leaves, strictly
ordered: (a) a shared attr registry so `engine` gets a reader at all and
future attrs stop being phantom keys; (b) a closed product->paradigm
vocabulary read off that attr, OWNER-OWNED because it touches strata
surface semantics; (c) new vet capability kinds per store client library
so SYS100/SYS101 already refuse an undeclared store client in a bound
file, the same enforcement SYS100/SYS101 already give every other
capability kind; (d) the five STORE30x rules themselves, each comparing
the declared paradigm against the observed access pattern in the bound
files.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
