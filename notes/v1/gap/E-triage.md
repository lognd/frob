# v1 triage summary (387 tickets)

IMPORTANT: this build has no verb that moves a ticket from triage to todo (`ticket triage` is designed in tickets.md but unbuilt; `ticket update` refuses category; `requeue` only acts on in-progress). Accepted tickets therefore stay in category triage, carry the label `triage:accepted`, have the chosen priority, and have their v1 `milestone:*` label stripped unless releases.md places them. Duplicate and wont-fix tickets are closed (done category).

## Per cluster

| Cluster | Accepted | Duplicate | Wont-fix | Rationale |
|---|---|---|---|---|
| B1 | 98 | 1 | 3 | STORE/SYSDESIGN/GRAMMAR rules kept as grimble-sysdesign pack work (D88, D89, 0.538.0); grammar-keyword asks superseded by typed attrs; scaffold duplicate. |
| B2 | 22 | 0 | 5 | Web families kept as crunk-web / grimble-websec pack work (D89); v1 Python gate plumbing closed. |
| B3c | 1 | 0 | 0 | PT-11 waiver determinism, low. |
| B3d | 15 | 2 | 18 | V-model and strata expressiveness kept as grmb capability asks; v1 registry, docs and strata-file chores closed. |
| B4 | 70 | 1 | 2 | Consumer-audit rule requests kept as low-priority pack/adapter content; two closed (policy.norm, subject-count epic) and CI001 duplicate. |
| C1a | 2 | 3 | 0 | PT-6 carrier kept; queue, stacked and duplicate items folded. |
| C1b | 2 | 3 | 0 | PT-6, PT-8, PT-17 carriers; whole-tree fix duplicate of ~R5QDX7H. |
| C2 | 3 | 2 | 0 | PT-2, PT-5, PT-12 carriers; close-with-unlanded duplicate of ~CKZS2R3. |
| C3 | 1 | 5 | 0 | PT-2 scope lint carrier plus PT-10 stacked-ticket decision; others duplicates. |
| C4a | 13 | 3 | 22 | v1 Python/vitest runner bugs closed; provider-level requirements (jest, dotnet, aliasing, PASS only when executed) kept. |
| C4b | 1 | 1 | 0 | PT-4 carriers kept; empty subject set duplicate. |
| C4c | 1 | 0 | 0 | PT-4 carrier (tri-state parent verdict). |
| D2 | 6 | 0 | 12 | Adapter expansion epics kept; v1 walkers, facets and Python helpers closed. |
| E1 | 6 | 8 | 7 | v1 frob-suggest false positives folded into the PT-3 frob hook carrier; v1 daemon/serve/claude plumbing closed. |
| E3 | 1 | 0 | 0 | PT-9 build identity. |
| F1 | 3 | 2 | 30 | v1 doc-narrative burn-downs and rules closed; NARR family requirement kept as one epic. |
| F2 | 1 | 0 | 0 | PT-14 advisory cross-clone epic claims. |
| G1 | 5 | 0 | 1 | PT-11, PT-18, PT-7, PT-8 carriers; FMT001 string-literal item closed (D44). |
| G2 | 1 | 0 | 4 | v1 CLI shim and argparse items closed; envelope covers JSON defect. |
| total | 252 | 31 | 104 | |

## Accepted tickets (handle, v1 id, priority, title)

### B1
- ~3VM7F8C T-6430 medium: STORE: database-paradigm misuse lint family
- ~77ZBPRY T-6388 low: SYSDESIGN504: critical-reachable store with declared RPO but no declared RTO
- ~EZC1FTE T-6390 low: SYSDESIGN202: autoscaled service with no local admission-control/load-shedding check
- ~RXSBM8Q T-6392 low: STORE201: JSON/JSONB column queried by many distinct paths, no expression index (relationa
- ~Q6B9F49 T-6393 low: STORE302: per-request full-collection/table/index scan reachable from a request handler, r
- ~NH163QX T-6394 low: Kubernetes manifest ingestion (Deployment/Service/Ingress/HPA/PDB/NetworkPolicy/probes/res
- ~EWSM4J3 T-6395 low: Helm values ingestion
- ~EMT1JYG T-6396 low: config-surface detection and a ConfigDoc contract in frob.lang
- ~BJ4HZK1 T-6397 low: STORE105: `find`/`find_one` inside a loop over a prior query's result (N+1, MongoDB)
- ~AZ2MT42 T-6398 low: engine vocabulary: product->paradigm table read from the existing store engine attr
- ~WP90GAR T-6399 low: SYSDESIGN401: request-scoped data written to local disk/in-process cache reused across req
- ~SW6V62Y T-6400 low: STORE205: leading/trailing `LIKE`/`ILIKE '%x%'` on a column with no trigram/tsvector index
- ~JDTSV9J T-6401 low: authority gaps and dropped rows
- ~7RY1H0E T-6402 low: STORE113: wildcard query with a leading wildcard (Elasticsearch)
- ~BZ8MG5A T-6403 low: STORE104: non-atomic `GET`-then-conditional-`SET` check-then-set race (Redis)
- ~DPXBMZ7 T-6404 low: SYSDESIGN106: default-allow security group / broad ingress on data tier / public subnet fo
- ~Z45GAQ9 T-6406 low: docker-compose ingestion
- ~8ATR031 T-6407 low: STORE109: Cypher query with no `LIMIT` (Neo4j)
- ~XHWWXMS T-6408 low: SYSDESIGN407: no SIGTERM handler / no preStop hook covering LB deregistration lag
- ~8VGNKVM T-6410 low: horizontal-scaling readiness (SYSDESIGN401+)
- ~52C5SNN T-6412 low: SYSDESIGN409: single migration both adds a required NOT NULL column and drops/renames an o
- ~FFP9JWP T-6413 low: SYSDESIGN504: `outbox_for`-marked store with no relay flow to its queue within N hops
- ~JF41NMA T-6414 low: close the 13 authority gaps in db-paradigm-research.md with primary sources
- ~Y5YVZ5R T-6415 low: STORE112: `from`/`size` paging beyond the 10,000-hit window (Elasticsearch)
- ~43DYKWJ T-6416 low: GRAMMAR: cache `stampede_guard` and queue `partitions`+`keyed_by`
- ~J4YX5HQ T-6417 low: Terraform/HCL ingestion (security groups, LB, WAF, DNS records)
- ~SRJKZF4 T-6418 low: STORE101: `KEYS pattern` in application/production code (Redis)
- ~BAJ16FR T-6420 low: SYSDESIGN104: LB deregistration_delay unset while workload terminationGracePeriodSeconds i
- ~3YDZ31V T-6421 low: STORE121: `WITH RECURSIVE` issued in a loop with an increasing depth parameter
- ~B0CBGCY T-6422 low: GRAMMAR: `cell` deployment-partitioning declaration with `mode active_active|active_passiv
- ~T9PCATG T-6423 low: SYSDESIGN108: declared `may` egress capability with no matching firewall/NAT egress allow-
- ~M0XQY5G T-6424 low: edge and network (SYSDESIGN101+)
- ~FWRW85A T-6425 low: SYSDESIGN107: internal listener accepting plaintext when design declares zero-trust
- ~7EKCR7M T-6426 low: config-surface ingestion
- ~1YB26XK T-6427 low: STORE107: `Scan` used where `Query` (key condition) would suffice, in a request handler (D
- ~X1CH4QH T-6429 low: data tier and operations (SYSDESIGN501+)
- ~ZDBKHYB T-6432 low: STORE111: Cartesian product from disconnected `MATCH` patterns (Neo4j)
- ~0PCB2QZ T-6433 low: SYSDESIGN201: trust-escalating boundary with no `admit.rate_limit`/`admit.max_size` declar
- ~04B9WMJ T-6435 low: STORE304: recursive/hierarchical traversal by repeated relational queries when a graph sto
- ~AKFGNHT T-6436 low: SYSDESIGN103: upstream cluster with neither active health check nor outlier detection
- ~YQ3KQSF T-6437 low: SYSDESIGN105: internet-facing listener with no managed WAF ruleset bound
- ~02R275A T-6438 low: STORE119: poll loop around `SELECT ... WHERE status='pending'` instead of a queue product 
- ~S85YXVC T-6440 low: STORE208: collection query missing index coverage (`find({})`/leading-wildcard `$regex`, M
- ~R23NRVT T-6441 low: SYSDESIGN503: data store with no declared consistency model
- ~AHKN41F T-6442 low: STORE118: `HeadObject`/`GetObject` in a loop over a candidate key list to filter by metada
- ~BSEV8PW T-6444 low: GRAMMAR: node compute-shape axis (`lifecycle`, `schedule`, `image`, `sidecar_of`)
- ~1R5MECT T-6445 low: SYSDESIGN403: horizontally-scaled Deployment with HPA minReplicas 1 or no HPA at all
- ~870VBCF T-6446 low: SYSDESIGN301: outbound call sets a fresh fixed timeout instead of deriving from the inboun
- ~P89AFAT T-6447 low: STORE305: search index written as the sole source of truth (no canonical-store writer for 
- ~MATNJYX T-6449 low: STORE301: many-to-many relationship modeled in a document store with manual application-si
- ~FFVW7WX T-6450 low: STORE206: high-cardinality tag column (unique IDs/timestamps/hashes as InfluxDB tags)
- ~8D47X8P T-6451 low: SYSDESIGN410: at-least-once queue consumer with no dedup/idempotency check
- ~SQETY9D T-6453 low: STORE2xx repo-fact rules
- ~D71CSNJ T-6454 low: STORE204: blocking command (`BLPOP`/`BRPOP`/`WAIT`/long `SUBSCRIBE`) issued on a shared/po
- ~X4J7K69 T-6455 low: GRAMMAR: module-level `owner STRING` declaration
- ~DV558BD T-6456 low: vet capability kinds per store client library (redis, mongo, dynamodb, neo4j, elasticsearc
- ~369JNE8 T-6457 low: STORE1xx call-shape rules
- ~PNNHA7F T-6458 low: SYSDESIGN501: read-only traffic routed to the primary write endpoint, no replica configure
- ~AMFY9DS T-6459 low: STORE102: unbounded `SMEMBERS`/`HGETALL`/`LRANGE key 0 -1` (Redis)
- ~G99DAXB T-6460 low: GRAMMAR: store_prop scaling/data axis (`conflict`, `keyed_by`+`shards`, `consistency`, `re
- ~J8GK72B T-6461 low: STORE108: variable-length path pattern (`[*]`) with no upper bound (Neo4j)
- ~3V0WSN0 T-6462 low: SYSDESIGN304: high-fanout cache-fill flow with `stampede_guard` undeclared or unproven
- ~Z91W3YV T-6463 low: STORE authority gaps and dropped rows
- ~9FRPGDP T-6465 low: SYSDESIGN102: hardcoded TLS cert/key material in ingress/LB config, no cert-manager/ACM an
- ~NZTK1EQ T-6467 low: GRAMMAR: flow `hedge after QUANTITY` for request hedging
- ~ZYFWQ88 T-6469 low: SYSDESIGN303: `hedge_after`-marked flow whose destination is not idempotent
- ~44CFZHV T-6470 low: SYSDESIGN405: multi-AZ-declared Deployment with no topologySpreadConstraints/podAntiAffini
- ~KVHJ87C T-6471 low: STORE110: `RETURN n` (bare node/relationship) instead of property projection (Neo4j)
- ~TAY990V T-6472 low: SYSDESIGN406: workload with a livenessProbe but no readinessProbe, or vice versa
- ~5KR8FTB T-6474 low: STORE115: `ALTER TABLE ... UPDATE`/`DELETE` mutation on a high-volume ClickHouse table
- ~3XK4H4V T-6475 low: SYSDESIGN302: outbound retry logic with a per-call max-attempts but no aggregate process-w
- ~3M1J0DR T-6476 medium: SYSDESIGN: system-design linting and strata architecture expressiveness
- ~V9E6M2A T-6477 low: STORE303: multi-entity ACID write pattern issued against a store declared with no native m
- ~EN6Q5YS T-6478 low: SYSDESIGN101: declared tier-1 availability with no health-checked/multi-provider DNS failo
- ~M0AG6FT T-6479 low: SYSDESIGN408: (pool_size_per_replica * max_replicas) exceeds declared DB max_connections
- ~0BC3QYX T-6480 low: STORE202: `*_cache`-named table with no expiry column (relational)
- ~SECH7YK T-6481 low: SYSDESIGN505: production service with no declared cell/multi-region active-active/passive 
- ~G9Z8DWV T-6482 low: close the marked authority gaps in sysdesign-research.md with primary sources
- ~4G0B1Q4 T-6483 low: SYSDESIGN202: bursty-ingress/fixed-capacity design declaration with no interposed queue
- ~H9G3HAK T-6484 low: STORE114: `script_fields`/inline `script` evaluated per-document in a request handler (Ela
- ~JBEEJ2B T-6485 low: STORE203: Redis as durable primary store with no AOF/RDB persistence config reviewed
- ~ZZZPVWP T-6486 low: SYSDESIGN402: session middleware configured with an in-memory/file-based backend
- ~JFZHKS8 T-6487 low: GRAMMAR: node operational axis (`drain`, `cert_expiry`, `health` closed vocabulary, `owner
- ~9JXR1YQ T-6489 low: resilience gaps not in REL (SYSDESIGN301+)
- ~RJG2NEW T-6490 low: SYSDESIGN404: multi-replica Deployment with no matching PodDisruptionBudget
- ~3PFA95C T-6491 low: STORE103: `SET`/`SETEX` on a cache-named key with no TTL (Redis)
- ~2SE123B T-6492 low: STORE207: single-table DynamoDB design with no documented access-pattern key schema
- ~8H8GE7S T-6495 low: admission and rate limiting (SYSDESIGN201+)
- ~WAP6859 T-6500 low: STORE117: `ListObjectsV2` with no `Prefix`, or called in a loop, to "find" an object (S3)
- ~6RGC19M T-6501 low: SYSDESIGN502: high-write-volume store with no declared partition/shard key
- ~8SEEP4D T-6502 low: STORE209: point `DELETE` on a TimescaleDB hypertable instead of a chunk/partition drop
- ~8Z79R41 T-6503 low: Envoy/NGINX/Caddy structured config ingestion
- ~09CJ83S T-6504 low: STORE116: row-by-row `INSERT` in a loop instead of a batched write (ClickHouse/InfluxDB)
- ~E9VHSP0 T-6505 low: STORE106: `$lookup` issued in a per-request hot path (MongoDB)
- ~7GQ564A T-6506 low: STORE120: file-read/upload bytes bound directly into an `INSERT`/`UPDATE` (blob-in-relatio
- ~P0BQRA2 T-6508 low: STORE3xx declared-vs-observed via strata
- ~XYTGV57 T-6509 low: SYSDESIGN407: container spec with no resources.requests set
- ~GXBEQTV T-6510 low: strata expressiveness: model any scaled system

### B2
- ~C707FRF T-3814 low: F-012: add a Playwright (@playwright/test) test collector so specs can be bound as frob:te
- ~NJ6WT20 T-4034 low: frob:tests kind=a11y obligation
- ~SSFY6KD T-4077 low: M-8: error-state a11y assertion plus RHF aria-invalid lint
- ~N134SE7 T-5140 medium: Web application lint families: appsec, compliance, accessibility, SEO and web performance,
- ~VPYYSEE T-5141 low: WEBSEC injection and output encoding: XSS sinks, SSTI, eval/exec, unsafe deserialization, 
- ~8VQ159Z T-5142 low: WEBSEC session, authentication and cryptography: CSRF, cookie flags, fixation and timeout,
- ~ZJAD3XB T-5143 low: WEBSEC configuration, headers and supply chain: CSP/HSTS/COOP/CORP set, CORS, debug flags,
- ~P0BC04T T-5144 low: WEBSEC authorization, business logic and LLM surface: admin routes without auth, front-end
- ~B0QHQEG T-5145 low: COMPLY: required pages, disclosures and config for CCPA/CPRA, CalOPPA, GDPR and ePrivacy, 
- ~JGEK1XJ T-5146 low: A11Y: WCAG 2.2 Level A and AA static rules over HTML/JSX/TSX/Vue/templates plus accessibil
- ~7PX2ZBW T-5147 low: SEO and WEBPERF: Google spam policies, per-page title/description/canonical/og/structured 
- ~4V8BH51 T-5148 low: SQL: extract SQL from host languages, sqlfluff as parser with a frob rule plugin for perfo
- ~2PZPVYD T-5365 low: SEO113-120: spam-policy shape detectors
- ~BRG0VTQ T-5402 low: Add EXPRESS to FrameworkKind and extend WEBSEC authz substrate to Express handlers
- ~R17789X T-5445 low: SQL103/SQL107 + TS/Prisma N+1 ORM rules
- ~6M7AGD4 T-5446 low: sqlfluff plugin: schema/session-level performance rules split off T-5335
- ~F0631DG T-5496 low: WEBSEC217 reserved id follow-up (JWT/OAuth family)
- ~XQJXRV6 T-5500 low: WEBSEC225 reserved id follow-up (password policy family)
- ~0S9ZR42 T-5508 low: WEBSEC403 full-strength server-route cross-reference
- ~5YW9FSX T-6610 low: SEO119/SEO120: split scaled-content vs. doorway-page detectors
- ~GR4ZPYH T-6534 low: WEBSEC/A11Y precision pass: 12 false-positive shapes measured on a real app (about 5 perce
- ~5E0V6W3 T-6540 low: detect_frameworks only sniffs the repo root: follow workspace members so web families run 

### B3c
- ~GS46EFY T-6532 low: strata/source `frob:waive SYS113` applies on one run and not the next identical run (cache

### B3d
- ~B8WYR32 T-3815 low: F-013: V-model authoring from spec docs (frob sys vmodel import docs/spec/*.md) + per-mile
- ~W33B3A3 T-3920 low: what strata could not express in a real threat-model pass: eight expressiveness gaps, incl
- ~VWSJX8H T-4071 low: F-273: auth-pages audit -- V-model closure is satisfied by existence, never by reachabilit
- ~PRGDJ7B T-4109 low: consumer round-3 backend audit: ten defects frob or strata should have caught, each with a
- ~X0QQ0NM T-4157 low: consumer round-4 engine audit: findings frob or strata should have caught, including a wai
- ~6YTWET9 T-4189 low: strata: require a rate attribute on inbound writes to a carries-bearing store from an unau
- ~0MVPEG2 T-4216 low: strata: declare page-wide/global capabilities distinctly from component-local ones, with a
- ~9BAGVE9 T-4218 low: strata: declare client-persisted browser storage as a capability with cleared_on triggers,
- ~1S8ACP0 T-4222 low: strata: mark outbound fetch capabilities volatility=external; a volatility=external source
- ~3C3JG79 T-4232 low: strata: model a node's runtime-mounted artifact set; check relative import/include targets
- ~ZHB0RTE T-4245 low: SYS/REL: require a timeout attribute on every net.connect/fetch_url strata grant, and flag
- ~VRKXQ36 T-4250 low: strata flow-participation: a shared contract implemented by more than one component must h
- ~REPG8H8 T-4253 low: strata: connect a browser node's declared media/fetch capability grants to the CSP/edge po
- ~HFD9PDF T-5768 low: Review verdict as ticket evidence + strata verification node
- ~VF2FAYY T-5797 low: TIER002: resolve frob:verifies against the strata V-model graph

### B4
- ~BSGQXJJ T-3919 low: every HIGH in a consumer backend audit sat behind green gates: the false-negative list and
- ~0TP6YWM T-3928 low: the edge/ops and frontend audit lists, and the five asks that four independent audits conv
- ~4QW70Y2 T-3942 low: F-175..F-185: backend delta audit -- and the recurrence signal that 3 first-audit asks wer
- ~ZBSN566 T-3952 low: ASSERT001: no bare assert in src/**
- ~F4TDPXR T-3954 low: frob:tests covers= failure-path binding
- ~THC05AJ T-3955 low: shell grammar for ops/**.sh plus starter policy
- ~1YP4XHR T-3959 low: waiver path for INV001/INV002
- ~RFX8DJX T-3960 low: known-dangerous-comparison-idiom rule (substring vs prefix)
- ~4GRPKRR T-3963 low: TAINT-IDENT001: store-read value used as identifier
- ~82JF0MY T-3966 low: ENVVAR003: config constructed outside its designated site
- ~ZTTYPJ4 T-3967 low: RESULT001: network-I/O async def may not return None
- ~Y6SCDZ6 T-3968 low: route/guard inventory: CSRF, confirm-gate and pagination axes
- ~D2KJ3PP T-3969 low: waiver debt: follow_up waivers ticket-scoped, milestone budget
- ~1HQATKY T-3970 low: PROTO001: protocol conformance at wiring sites
- ~Z53C7YQ T-3971 low: ENVVAR002: every config field has a non-test reader
- ~GT0S8M0 T-3972 low: LOOP001: asyncio.run inside a loop
- ~QMPSRAV T-3975 medium: evidence satisfaction must exclude xfail/xpass/skip by default
- ~4RBRQHB T-3976 low: refs.artifact: declared surface for verbatim build-output directories
- ~5J61JYM T-3977 low: frob:pending T-#### directive for spec-first red tests
- ~5H5DB7Q T-3981 low: F-195: unresolved evidence id asserts the test does not exist instead of suggesting the ne
- ~F7RBEX4 T-3987 low: cmd: evidence: reproducibility hardening (cwd, re-run, empty-output)
- ~6FV77F5 T-3991 low: GEN001: declared-generated-files block plus drift gate
- ~SD0M99M T-3996 low: required_file: declared surface for untracked-but-mandatory artifacts
- ~KQSJFAK T-4025 low: F-236+: frontend delta audit -- substring-as-prefix is now a measured cross-language, cros
- ~SYSK2BD T-4033 low: frob:claim directive (or frob:doc guidance) for cross-file comment assertions
- ~2RH1A9P T-4035 low: frob:mirror: cross-language literal-constant equality directive
- ~4CESXMT T-4038 low: unpaired resource acquisition: known acquire/release API table
- ~1M6NZ7K T-4039 low: state/transition construct: unreachable-exit lifecycle states
- ~KFNZ4W8 T-4072 low: M-3: generated-types staleness check plus hand-written-interface ban
- ~2Z0G51P T-4074 low: H-2: unguarded default for required build-time env config
- ~633VW5W T-4075 low: M-2: invariant binding two L5 rows for cross-row consistency
- ~S24T511 T-4076 low: M-7: allowlist check for public/-style static-assets directories
- ~1BKXXFD T-4078 low: M-9: rate-limit invariant for unauthenticated PII-returning routes
- ~HGGVNZ8 T-4079 low: L-1: document.cookie write pattern for client_storage scanner
- ~HYKK80T T-4080 low: L-2: import.meta.env pattern for browser-side env.read
- ~CJ3RQQ5 T-4081 low: L-6: ban err.message flowing directly into rendered state
- ~EJK6SE6 T-4089 low: F-296: engine round-3 audit -- contracts stated in prose, enforced on one side of an ABI b
- ~TX3DG2D T-4090 low: H3-1b: TS frob:invariant positive control for throw-safe re-arm loops
- ~AQQHHY0 T-4091 low: H3-1a: policy.pattern for wasm-twin buffer-length parity in TS
- ~CGQFD33 T-4092 low: H3-3: units/epoch obligation on time-typed ABI parameters
- ~BYF5SEF T-4093 low: H3-4/H3-5: ticket-referenced exhaustive-deps disables, per-file-vs-interaction gap
- ~0FPQXHD T-4094 low: H3-7: empty catch/degrade path with no logging in src/
- ~7CT2H1F T-4095 low: H3-11: wasm-bearing dynamic import as fetch_url capability
- ~30RA4E2 T-4096 low: H3-13: policy.pattern banning per-frame TypedArray allocation in Renderer
- ~SJ4C4BC T-4113 medium: H3-3: an outbound flow's destination must be constrained to its declared node, and every f
- ~P2EYCEC T-4117 medium: H3-9: a module docstring's claim about its own module's code is never checked against that
- ~5BEHX2T T-4135 low: consumer backlog F-315 through F-338: 24 untriaged findings including four whole verbatim 
- ~EHS7ENJ T-4166 low: consumer round-4 shell audit: nine findings, including outcomes that depend on wall-clock 
- ~F18KDVY T-4175 low: consumer round-4 backend audit: nine findings written as why the gates missed them, includ
- ~ZEZ45SB T-4182 low: consumer round-5 shell audit: findings written as why the gates, the design language and t
- ~H387ZSP T-4188 low: frob:invariant call-graph-closure kind: a symbol reading a guard state must have a reachab
- ~KCTJCK8 T-4190 low: lint: a *_path Field default that is a relative path should be flagged
- ~W1SG606 T-4192 low: route-inventory check: a handler returning a dict/mapping literal response must declare a 
- ~MZX27BF T-4211 low: exported check*/*Check symbol with no reference from a declared entrypoint list is a findi
- ~SHM3Q68 T-4215 low: gate: a dynamically-resolved import/reference resolving to a path unreachable from the shi
- ~A85HVPF T-4217 low: interface/adapter parity: every optional member of an invariant-marked port must be implem
- ~AHHJZJ7 T-4220 low: purity/ownership invariant: a controller documented Pure must not be wired to a caller tha
- ~RG8GTGX T-4223 low: split a display-only error-code list into a display axis and a needs-client-recovery axis,
- ~DP3S737 T-4225 low: TODO001: bump severity for a frob:todo/skip guard whose reason names a production command 
- ~QGMN5WS T-4226 low: cross-artifact producer/consumer check: a value one script writes and another parses must 
- ~84P9467 T-4227 low: evidence classification: a test whose subject is constructed in the test file rather than 
- ~C7N16H7 T-4228 low: coverage-over-a-registry is not coverage-over-the-real-surface: add a surface-enumeration 
- ~TTQYWR4 T-4229 low: runbook fenced shell commands: a doc-adjacent directive naming the execution container, ch
- ~2EAXR0A T-4231 low: extend the PII-structural gate to model the message/extra split inside a log record
- ~N9B6EES T-4233 low: frob:invariant: flag a component whose only bound tests exercise one happy-path fixture va
- ~VXKMGDY T-4237 low: classify a documented command's path arguments by execution context (container namespace v
- ~9C8YK7E T-4238 low: deploy-script semantic checks: an image a script pulls must be one a job pushes; an unauth
- ~DHZ6KRV T-4239 low: bind a shell component to its runtime image and shellcheck/lint it with that image's actua
- ~MTHZXYJ T-4249 low: client-side totality mirror: export a server registry's total code/field set and require t
- ~VAN56Z5 T-4252 low: AFFECT-style check: on ticket close, flag sibling symbols with the same shape that still m

### C1a
- ~JHA8CYK T-6516 medium: land: stacked successor hunks silently dropped after the base squash-lands; verify hunk pr
- ~T9WKA9Z T-6518 medium: verify: single-instance full checks with memory admission; name the stage when the pass is

### C1b
- ~J8HVP93 T-3270 low: frob ticket land's fixed wall-clock timeout races variable-cost contention, killing progre
- ~F6YXYRZ T-6604 medium: frob check --ticket: refuse a second concurrent full check for the same worktree (per-work

### C2
- ~PVJ9SQM T-3978 high: A scope glob matching zero tracked files is accepted silently, granting a lease over nothi
- ~H1NWDN9 T-4031 medium: F-238: a ticket with zero acceptance criteria passes the acceptance check vacuously and la
- ~W91G8EK T-6543 medium: `frob ticket done-report` (no --fix) mutates the tree: its internal scoped check wrote 60 

### C3
- ~P2W1WMP T-3842 medium: F-037: a series worktree (three sibling leaf tickets on one branch) cannot land -- blocks 

### C4a
- ~5ND00YZ T-3921 low: add a jest test collector (frob.testing._collect_ts currently vitest-only)
- ~DWEF5H8 T-4040 low: waived frob:tests must still record its claimed kind
- ~3A1W4FQ T-4058 low: F-262: the vitest stage reports a failure COUNT with no node ids, so a flake cannot be tol
- ~KHAA6D2 T-4059 low: F-261: a wrong-direction frob:tests directive parses silently and only surfaces later as a
- ~VZBDJTE T-4070 low: frob test's touched-set selector calls any symbol in a test file a test, so a module-level
- ~S6KHXYZ T-4149 low: decide and document the no-[[test.runner]]-declared fallback policy
- ~Y0Y36YX T-4643 low: touched-set test selection misses tests that fake a changed function signature
- ~SDFS36Z T-5487 low: Wire dotnet/unity test runners into ticket-runner CLI for csharp/Unity node ids
- ~X4W9S9S T-6535 medium: `frob check --fix` TEST010 MOVE handler corrupts Python: re-parse after every Tier-A edit 
- ~G762T83 T-6545 low: test runners: 'typescript' and 'ts' (and js/javascript) are not aliased, so vitest evidenc
- ~46VKHER T-6549 medium: test runners: exit-code-only outcome records PASS when the filter selects nothing; require
- ~M7XBF7P T-6590 low: frob check: csharp/unity project type -- detection via detect_unity_project or *.asmdef an
- ~DSYX0M9 T-6603 low: frob test reports NoRunner when a touched set contains test fixture data files (tests/fixt

### C4b
- ~S8FXM30 T-3068 medium: TDD commit protocol: test-first commit marks the test xfail(strict=True), implementation c

### C4c
- ~Y32GVV7 T-4009 medium: F-223: a brand-new test is NO_VERDICT at the parent commit, so --designate-repro-force is 

### D2
- ~Y27W0D5 T-1597 medium: Language support expansion: C#, Java, CUDA, Zig, Bash and the top 20-50 languages
- ~49P22KK T-1598 low: Language expansion: research and rank the target set, define per-language semantics
- ~Y18T290 T-1607 low: Language expansion: remaining ranked languages, in research-recommended batches
- ~XFXTYZR T-1608 low: Cross-language inspection stress test: one repo, every supported language, one obligation 
- ~WF10TGF T-4016 low: F-230: the TS walker emits no symbol for describe()/it() call expressions, so no frob:test
- ~RCMBYFN T-4513 low: C# and Unity support for frob (owner directive 2026-09-16)

### E1
- ~GVGDB1W T-2963 low: Windows-native daemon transport (epic): named pipes vs loopback TCP+token vs AF_UNIX hybri
- ~6AVMFPF T-3714 low: vet --hook vets whole resolution instead of delta
- ~Y5QNHBX T-3803 low: F-001: frob serve (MCP) exits 1 in a repo with no frob.toml -- give a clear reason or a sc
- ~QDMB8GH T-5098 low: frob-suggest: log every block/allow/ignored-ack decision to .frob/telemetry.jsonl
- ~KCF29W6 T-5099 low: frob-suggest: replace blanket FROB_SUGGEST_ACK with per-rule token, update docs
- ~KHCKTS3 T-5101 medium: Claude Code hooks: 10% precision on frob-suggest, double registration doubles the attempt 

### E3
- ~821FN00 T-4001 medium: Two different builds both report 0.530.0, so consumer bug reports cannot be checked agains

### F1
- ~AA0PAPK T-2994 low: Epic: narrative belongs in tickets, code and docs carry utility
- ~Q576RV4 T-4187 low: DRIFT: compare a module's own docstring against its own module's code, not only doc files 
- ~50S27S8 T-4193 low: playbook: a failure-injection repro test must assert every field of the response, not only

### F2
- ~RR15A7Z T-4272 medium: multi-contributor epic claims: a remote collaborator claims an epic, everyone else sees it

### G1
- ~GCNECVB T-3858 medium: frob:waive is silently inert in files with no registered grammar: the suppression mechanis
- ~0G7VZJ5 T-4015 low: F-228: ticket-id matching has no token boundary, so UT-2207 reads as a citation of T-2207 
- ~JDNWN5E T-4036 medium: F-240+: engine delta audit -- a rule-shaped remediation must not be closable by fixing ins
- ~8RAXTMJ T-4069 low: Three gates were satisfied today by making the code worse: state and audit the 'cheapest c
- ~JHBNG21 T-5153 medium: frob check: the sys stage takes 1268s of a 1900s root check and --files scoping does not s

### G2
- ~7VYS0DH T-3879 low: establish a tail-me result-block contract for every verb, and collapse high-cardinality wa

## Milestones
B1 and B2 accepted tickets carry milestone:0.538.0 (D89, releases.md section 7). Every other accepted ticket had its imported v1 milestone label removed because v1 versions such as 0.534.0 collide with v2 release names. 0.539.0 (B1) was rewritten to 0.538.0.

## For the coordinator's attention

- Triage accept verb missing: 252 accepted tickets cannot leave triage. Needs `ticket triage accept` (tickets.md) built, or a bulk transition, then filter on label triage:accepted.
- ~KHCKTS3 (PT-3 frob hook carrier): 9 v1 frob-suggest/protect-secrets tickets were closed as duplicates of it; check you agree it is the single carrier.
- ~PVJ9SQM (PT-2), ~P2W1WMP (PT-10 needs a D-number), ~JHA8CYK (PT-6), ~F6YXYRZ/~T9WKA9Z/~JHBNG21 (PT-8), ~Y32GVV7/~S8FXM30 (PT-4), ~821FN00 (PT-9), ~RR15A7Z (PT-14), ~H1NWDN9 (PT-12, contradicts tickets.md s9 on purpose): the PT carriers; confirm priorities.
- ~P1MZAEK (FMT001 string literals) closed wont-fix on D44 although the selection had it import-open; ~KSGQT45, ~32WEEAQ, ~9BTK4E2 (grammar items) closed as superseded by grmb-spec typed attrs and pack-defined lattices; confirm you agree.
- ~3QF2P3A (strata V-model epic) closed as duplicate of ~QNDWNDM (G16); ~6Q5ZBXE (T-4052) as duplicate of ~CKZS2R3.
- B1 GRAMMAR-style accepted tickets carry a comment marking them uncertain (vocabulary should be pack typed attrs; see ~XEZW79B).
- Items accepted with uncertainty notes (comment on the ticket): ~DWEF5H8, ~KHAA6D2, ~VZBDJTE, ~Y0Y36YX, ~633VW5W, ~4RBRQHB, ~1YP4XHR, ~P2EYCEC, ~7VYS0DH, ~GVGDB1W, ~HFD9PDF, ~B8WYR32, ~VWSJX8H.
- Milestone 0.539.0 appeared on the v1 B1 tickets and is not in releases.md.
