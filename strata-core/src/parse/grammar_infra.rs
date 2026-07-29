// Infra-primitive grammar productions: `store`, `cache`, `resource`,
// `queue`, `cdn`, `balancer`, and metric names (docs/strata/surface.md#parser).
// frob:waive REF002 reason="a T-1099 grammar-family split fragment of parse.rs, imported only by parse/mod.rs's `mod` declaration by design -- the same package structure every sibling parse/grammar_*.rs module has, a second consumer would not be genuine"
// frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: T-1099 split strata-core/src/parse.rs (whose single INV006 calibration-batch waiver, T-0585, is preserved verbatim in parse/mod.rs) into grammar-family fragments; this file inherits some of that same source-level design-rationale/scope-cut prose (a docstring or comment describing already-implemented internal behavior, verifiable by reading the code it annotates) rather than a separate cross-module contract needing its own tracked invariant; disposed as the same calibration batch, not claim-by-claim"

impl Parser {
    /// PERCENT := NUMBER '%'; used by `hit` on cache/cdn (std.infra).
    fn parse_percent(&mut self, what: &str) -> Result<f64, ParseError> {
        let n = self.expect_number(what)?;
        self.expect_symbol('%')?;
        Ok(n)
    }

    /// store := "store" ID ":" TRUST "{" store_prop (";" store_prop)* "}"?
    /// store_prop := node_prop | "engine" IDENT | "immutable" | "append_only"
    ///             | "rpo" QUANTITY
    ///
    /// WHY: store is std.infra's node-with-extras; it reuses the node_prop
    /// surface (clearance/attr/residence/capacity/errors_total/
    /// panics_contained_by/observe/`on deploy`, T-0247) verbatim plus
    /// engine, the immutable/append_only markers the elaborator needs for
    /// the cdn-unlimited-staleness pairing, and `rpo` -- a store's declared
    /// durability/replication lag, the same age-collapse family as cache ttl
    /// (docs/strata/surface.md#std-infra, docs/strata/kernel.md#age-
    /// propagation-semantics). The grammar accepts any unit here; dimension
    /// validation (must be a time unit) is the elaborator's job, matching
    /// how ttl/staleness stay units-only at parse time too. T-0247's four
    /// clauses are the observability/deploy-contract subset of node_prop a
    /// store needed; std.krb's realm/kdc/spn/delegation/trusts remain
    /// node-only (not requested by this ticket, filed separately if still
    /// needed).
    fn parse_store(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'store'
        let id = self.expect_ident("store id")?;
        self.expect_symbol(':')?;
        let trust = self.expect_ident("trust level")?;
        let mut clearance = "Secret".to_string();
        let mut attrs: Vec<String> = Vec::new();
        let mut residence: Option<String> = None;
        let mut capacity: Option<serde_json::Value> = None;
        // T-0702: same `users`/`rate` entry-demand shape as `node`'s --
        // a store is a node too (docs/strata/surface.md#key-construct-
        // semantics), so it can be the demand-declaring endpoint too.
        let mut users: Option<f64> = None;
        let mut demand_rate: Option<serde_json::Value> = None;
        let mut engine: Option<String> = None;
        let mut immutable = false;
        let mut append_only = false;
        let mut rpo: Option<serde_json::Value> = None;
        let mut carries: Vec<String> = Vec::new();
        let mut is_managed = false;
        let mut code: Vec<String> = Vec::new();
        let mut may: Vec<String> = Vec::new();
        let mut waives: Vec<serde_json::Value> = Vec::new();
        let mut runs_as: Option<String> = None;
        let mut is_unit = false;
        let mut owns: Vec<serde_json::Value> = Vec::new();
        let mut listens: Vec<i64> = Vec::new();
        let mut group: Vec<String> = Vec::new();
        let mut sudoers: Vec<String> = Vec::new();
        // T-0261: same std.host windows fields as `node` (parse_node) --
        // a store is a node too.
        let mut platform: Option<String> = None;
        let mut service_account: Option<String> = None;
        let mut service_account_gmsa = false;
        let mut is_service = false;
        let mut acl: Vec<serde_json::Value> = Vec::new();
        let mut pipes: Vec<String> = Vec::new();
        let mut errors_total = false;
        let mut panics_contained_by: Option<String> = None;
        let mut observe: Option<serde_json::Value> = None;
        let mut deploy: Option<serde_json::Value> = None;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("clearance") {
                    self.advance();
                    clearance = self.expect_ident("clearance level")?;
                } else if self.at_keyword("attr") {
                    self.advance();
                    attrs.push(self.parse_attrval()?);
                } else if self.at_keyword("runs_as") {
                    // T-0255: same shape as `node`'s `runs_as` -- a store
                    // is a node too (docs/strata/surface.md
                    // #key-construct-semantics).
                    self.advance();
                    runs_as = Some(self.expect_string("runs_as service user name")?);
                } else if self.at_keyword("unit") {
                    // T-0255: same bare marker as `node`'s `unit`.
                    self.advance();
                    is_unit = true;
                } else if self.at_keyword("owns") {
                    // T-0255: same `owns "PATH" "MODE"` shape as `node`.
                    self.advance();
                    let path = self.expect_string("owns path")?;
                    let mode = self.expect_string("owns mode")?;
                    owns.push(json!({"path": path, "mode": mode}));
                } else if self.at_keyword("listens") {
                    // T-0255: same `listens PORT` shape as `node`.
                    self.advance();
                    listens.push(self.expect_int("listens port")?);
                } else if self.at_keyword("group") {
                    // T-0272: same `group "NAME"`+ shape as `node`'s clause
                    // -- a store is a node too (docs/strata/surface.md
                    // #key-construct-semantics).
                    self.advance();
                    group.push(self.expect_string("group name")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        group.push(self.expect_string("group name")?);
                    }
                } else if self.at_keyword("sudoers") {
                    // T-0272: same `sudoers "RULE"`+ shape as `node`'s
                    // clause -- a store is a node too.
                    self.advance();
                    sudoers.push(self.expect_string("sudoers rule")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        sudoers.push(self.expect_string("sudoers rule")?);
                    }
                } else if self.at_keyword("platform") {
                    // T-0261: same `platform "windows"` shape as `node`'s
                    // clause -- a store is a node too.
                    self.advance();
                    platform = Some(self.expect_string("platform name")?);
                } else if self.at_keyword("service_account") {
                    // T-0261: same `service_account "NAME" [gmsa]` shape as
                    // `node`'s clause -- a store is a node too.
                    self.advance();
                    service_account = Some(self.expect_string("service account name")?);
                    if self.at_keyword("gmsa") {
                        self.advance();
                        service_account_gmsa = true;
                    }
                } else if self.at_keyword("service") {
                    // T-0261: same bare marker as `node`'s `service`.
                    self.advance();
                    is_service = true;
                } else if self.at_keyword("acl") {
                    // T-0261: same `acl "PATH" "RULE"` shape as `node`'s
                    // clause -- a store is a node too.
                    self.advance();
                    let path = self.expect_string("acl path")?;
                    let rule = self.expect_string("acl rule")?;
                    acl.push(json!({"path": path, "rule": rule}));
                } else if self.at_keyword("pipe") {
                    // T-0261: same `pipe "NAME"`+ shape as `node`'s clause
                    // -- a store is a node too.
                    self.advance();
                    pipes.push(self.expect_string("pipe name")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        pipes.push(self.expect_string("pipe name")?);
                    }
                } else if self.at_keyword("bin_path") {
                    // T-0629: same `bin_path "PATH" ["ARGS"]` shape as
                    // `node`'s clause -- a store is a node too
                    // (docs/strata/surface.md#key-construct-semantics).
                    self.advance();
                    let path = self.expect_string("bin_path path")?;
                    attrs.retain(|a| {
                        !a.starts_with("bin_path=") && !a.starts_with("bin_path_args=")
                    });
                    attrs.push(format!("bin_path={}", path));
                    if matches!(self.cur().kind, TokKind::Str(_)) {
                        let args = self.expect_string("bin_path args")?;
                        attrs.push(format!("bin_path_args={}", args));
                    }
                } else if self.at_keyword("access") {
                    self.parse_access_attr(&mut attrs)?;
                } else if self.at_keyword("code") {
                    // T-0166: `code GLOB+` -- same STRING+ shape T-0132 gave
                    // `node` (parse_node); a store is a node too
                    // (docs/strata/surface.md#key-construct-semantics), so
                    // it binds source the same way a code-modeled node does.
                    self.advance();
                    code.push(self.expect_string("code glob")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        code.push(self.expect_string("code glob")?);
                    }
                } else if self.at_keyword("waive") {
                    // T-0250: `waive RULE reason="..." [ticket="T-XXXX"]` --
                    // same shape and same mandatory-reason rule as
                    // parse_node's T-0174 waive clause; a store is a node
                    // too (docs/strata/surface.md#key-construct-semantics),
                    // so a `frob sys audit` finding against a store
                    // (SYS100-102/THREAT002-003/LINT004) needs the same
                    // in-design waiver escape hatch. `reason` is mandatory
                    // at parse time (law 2: no fabricated/implicit
                    // waivers) -- a `waive` clause with no reason is a hard
                    // parse error, never a silent pass. Repeatable: a store
                    // may waive more than one rule.
                    self.advance();
                    let rule = self.expect_string("waive rule id")?;
                    self.expect_keyword("reason")?;
                    let reason = self.expect_string("waive reason")?;
                    let mut ticket: Option<String> = None;
                    if self.at_keyword("ticket") {
                        self.advance();
                        ticket = Some(self.expect_string("waive ticket ref")?);
                    }
                    waives.push(json!({
                        "rule": rule,
                        "reason": reason,
                        "ticket": ticket,
                    }));
                } else if self.at_keyword("may") {
                    // T-0166: `may CAPABILITY` -- same STRING-quoted
                    // capability atom shape T-0132 gave `node`. Lands
                    // directly in `Node.may` on elaboration, same as node.
                    self.advance();
                    may.push(self.expect_string("may capability")?);
                } else if self.at_keyword("carries") {
                    // T-0154: same `carries PII_TAG+` shape as `node`
                    // (parse_node) -- a store is the most common PII
                    // resting place, so it gets the same declaration.
                    self.advance();
                    carries.push(self.expect_string("carries pii tag")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        carries.push(self.expect_string("carries pii tag")?);
                    }
                } else if self.at_keyword("residence") {
                    self.advance();
                    residence = Some(self.expect_ident("residence atom")?);
                } else if self.at_keyword("capacity") {
                    self.advance();
                    let rate = self.parse_quantity("capacity rate")?;
                    self.expect_keyword("replicas")?;
                    let lo = self.expect_int("replicas_min")?;
                    self.expect_dotdot()?;
                    let hi = self.expect_int("replicas_max")?;
                    capacity = Some(json!({"rate": rate, "replicas_min": lo, "replicas_max": hi}));
                } else if self.at_keyword("users") {
                    // T-0702: same `users NUMBER` shape as `node`'s clause.
                    self.advance();
                    users = Some(self.expect_number("users population")?);
                } else if self.at_keyword("rate") {
                    // T-0702: same `rate NUMBER UNIT` shape as `node`'s
                    // clause, top-level and distinct from `capacity`'s own
                    // nested rate quantity.
                    self.advance();
                    demand_rate = Some(self.parse_quantity("rate")?);
                } else if self.at_keyword("engine") {
                    self.advance();
                    engine = Some(self.expect_ident("engine name")?);
                } else if self.at_keyword("immutable") {
                    self.advance();
                    immutable = true;
                } else if self.at_keyword("append_only") {
                    self.advance();
                    append_only = true;
                } else if self.at_keyword("rpo") {
                    self.advance();
                    rpo = Some(self.parse_quantity("rpo")?);
                } else if self.at_keyword("skew") {
                    self.advance();
                    self.expect_keyword("zipf")?;
                    let alpha = self.expect_number("skew zipf exponent")?;
                    attrs.push(format!("skew={}", alpha));
                } else if self.at_keyword("managed") {
                    // T-0172: same bare marker as `node` (parse_node) --
                    // a store is a node too (docs/strata/surface.md
                    // #key-construct-semantics: "component / store: nodes").
                    self.advance();
                    is_managed = true;
                } else if self.at_keyword("errors_total") {
                    // T-0247: same bare marker as `node`'s `errors_total`
                    // (parse_node) -- a store is a node too (docs/strata/
                    // surface.md#key-construct-semantics), so the
                    // errors-total observability claim applies to it
                    // unchanged. The elaborator turns this into the same
                    // `errors_total` node attr `node` gets.
                    self.advance();
                    errors_total = true;
                } else if self.at_keyword("panics_contained_by") {
                    // T-0247: same `panics_contained_by IDENT` shape as
                    // `node`'s clause; reference validity is an
                    // elaboration-time check, mirroring parse_node.
                    self.advance();
                    panics_contained_by = Some(self.expect_ident("panics supervisor id")?);
                } else if self.at_keyword("on") {
                    // T-0247: same `on deploy { ... }` shape as `node`'s
                    // clause (parse_node); `deploy` is still the only `on`
                    // keyword this parser accepts, matching parse_node's
                    // deferral note for `on crash`/`on breach`.
                    self.advance();
                    self.expect_keyword("deploy")?;
                    deploy = Some(self.parse_on_deploy_block()?);
                } else if self.at_keyword("observe") {
                    // T-0247: same `observe { log IDENT (, IDENT)*; to
                    // IDENT }` shape as `node`'s clause (parse_node).
                    self.advance();
                    self.expect_symbol('{')?;
                    let mut log: Vec<String> = Vec::new();
                    let mut to: Option<String> = None;
                    loop {
                        if self.at_symbol('}') {
                            break;
                        }
                        if self.at_keyword("log") {
                            self.advance();
                            log.push(self.expect_ident("observe log class")?);
                            while self.at_symbol(',') {
                                self.advance();
                                log.push(self.expect_ident("observe log class")?);
                            }
                        } else if self.at_keyword("to") {
                            self.advance();
                            to = Some(self.expect_ident("observe target id")?);
                        } else {
                            return self.err("unknown observe property");
                        }
                        if self.at_symbol(';') {
                            self.advance();
                        } else {
                            break;
                        }
                    }
                    self.expect_symbol('}')?;
                    let to = match to {
                        Some(t) => t,
                        None => return self.err("observe block needs a to IDENT"),
                    };
                    observe = Some(json!({"log": log, "to": to}));
                } else {
                    return self.err("unknown store property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.stores.push(json!({
            "id": id,
            "trust": trust,
            "clearance": clearance,
            "attrs": attrs,
            "capacity": capacity,
            "users": users,
            "rate": demand_rate,
            "residence": residence,
            "engine": engine,
            "immutable": immutable,
            "append_only": append_only,
            "rpo": rpo,
            "carries": carries,
            "is_managed": is_managed,
            "code": code,
            "may": may,
            "waives": waives,
            "runs_as": runs_as,
            "is_unit": is_unit,
            "owns": owns,
            "listens": listens,
            "group": group,
            "sudoers": sudoers,
            "platform": platform,
            "service_account": service_account,
            "service_account_gmsa": service_account_gmsa,
            "is_service": is_service,
            "acl": acl,
            "pipes": pipes,
            "errors_total": errors_total,
            "panics_contained_by": panics_contained_by,
            "observe": observe,
            "deploy": deploy,
        }));
        Ok(())
    }

    /// cache := "cache" ID "of" ID "{" cache_prop (";" cache_prop)* "}"?
    /// cache_prop := "keyed_by" IDENT | "ttl" QUANTITY | "staleness" QUANTITY
    ///             | "hit" PERCENT | "policy" IDENT | "invalidate_on" IDENT
    ///
    /// WHY: `invalidate_on` is repeatable (a cache may be invalidated by
    /// several write flows), collected in declaration order so the
    /// elaborator's mandatory-invalidation check can report every declared
    /// edge (docs/strata/surface.md#std-infra).
    fn parse_cache(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'cache'
        let id = self.expect_ident("cache id")?;
        self.expect_keyword("of")?;
        let of = self.expect_ident("cache source-of-truth id")?;
        let mut keyed_by: Option<String> = None;
        let mut ttl: Option<serde_json::Value> = None;
        let mut staleness: Option<serde_json::Value> = None;
        let mut hit: Option<f64> = None;
        let mut policy: Option<String> = None;
        let mut invalidate_on: Vec<String> = Vec::new();
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("keyed_by") {
                    self.advance();
                    keyed_by = Some(self.expect_ident("keyed_by field")?);
                } else if self.at_keyword("ttl") {
                    self.advance();
                    ttl = Some(self.parse_quantity("ttl")?);
                } else if self.at_keyword("staleness") {
                    self.advance();
                    staleness = Some(self.parse_quantity("staleness")?);
                } else if self.at_keyword("hit") {
                    self.advance();
                    hit = Some(self.parse_percent("hit ratio")?);
                } else if self.at_keyword("policy") {
                    self.advance();
                    policy = Some(self.expect_ident("cache policy")?);
                } else if self.at_keyword("invalidate_on") {
                    self.advance();
                    invalidate_on.push(self.expect_ident("invalidate_on flow id")?);
                } else {
                    return self.err("unknown cache property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.caches.push(json!({
            "id": id,
            "of": of,
            "keyed_by": keyed_by,
            "ttl": ttl,
            "staleness": staleness,
            "hit": hit,
            "policy": policy,
            "invalidate_on": invalidate_on,
        }));
        Ok(())
    }

    /// queue := "queue" ID (":" TRUST)? "{" queue_prop (";" queue_prop)* "}"?
    /// queue_prop := "delivery" IDENT | "ordering" IDENT | "attr" ATTRVAL
    ///             | "clearance" IDENT
    ///
    /// WHY optional TRUST: T-0093 -- queue previously had no TRUST clause at
    /// all and the elaborator hardcoded a `"trusted"` default
    /// (docs/strata/surface.md#std-infra deviation note). The clause is
    /// optional (not mandatory) so every existing `.strata` source without it
    /// keeps parsing identically; the elaborator still defaults to
    /// `"trusted"` when omitted.
    /// resource := "resource" ID ("{" resource_prop (";" resource_prop)* "}")?
    /// resource_prop := "arbitrated_by" ID | "lock" STRING
    ///
    /// WHY: T-0700's shared-resource declaration -- names a resource
    /// `access` clauses (`parse_access_attr`) reference by matching
    /// STRING id, and optionally binds a single arbiter (a node id that
    /// mediates access) or a lease/lock NAME. At most one of
    /// `arbitrated_by`/`lock` may be given -- a resource with both would
    /// leave the contention-proof obligation unable to tell which
    /// mechanism actually discharges it, so this is a parse error rather
    /// than a silent "last one wins" (same discipline `parse_resource`'s
    /// sibling clauses use for at-most-one fields elsewhere in this
    /// file). A bare `resource ID;` (no body) declares the resource
    /// exists with no arbiter -- the contention proof then requires every
    /// accessor to be read/alpha-only (module docstring compatibility
    /// matrix, `src/frob/strata/_access.py`).
    fn parse_resource(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'resource'
        let id = self.expect_ident("resource id")?;
        let mut arbitrated_by: Option<String> = None;
        let mut lock: Option<String> = None;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("arbitrated_by") {
                    if arbitrated_by.is_some() || lock.is_some() {
                        return self.err(
                            "resource may declare at most one of arbitrated_by/lock",
                        );
                    }
                    self.advance();
                    arbitrated_by = Some(self.expect_ident("arbiter node id")?);
                } else if self.at_keyword("lock") {
                    if arbitrated_by.is_some() || lock.is_some() {
                        return self.err(
                            "resource may declare at most one of arbitrated_by/lock",
                        );
                    }
                    self.advance();
                    lock = Some(self.expect_string("lock name")?);
                } else {
                    return self.err("unknown resource property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.resources.push(json!({
            "id": id,
            "arbitrated_by": arbitrated_by,
            "lock": lock,
        }));
        Ok(())
    }

    fn parse_queue(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'queue'
        let id = self.expect_ident("queue id")?;
        let mut trust: Option<String> = None;
        if self.at_symbol(':') {
            self.advance();
            trust = Some(self.expect_ident("trust level")?);
        }
        let mut delivery: Option<String> = None;
        let mut ordering: Option<String> = None;
        let mut attrs: Vec<String> = Vec::new();
        let mut clearance: Option<String> = None;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("delivery") {
                    self.advance();
                    delivery = Some(self.expect_ident("delivery mode")?);
                } else if self.at_keyword("ordering") {
                    self.advance();
                    ordering = Some(self.expect_ident("ordering mode")?);
                } else if self.at_keyword("attr") {
                    self.advance();
                    attrs.push(self.parse_attrval()?);
                } else if self.at_keyword("clearance") {
                    self.advance();
                    clearance = Some(self.expect_ident("clearance level")?);
                } else {
                    return self.err("unknown queue property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.queues.push(json!({
            "id": id,
            "trust": trust,
            "delivery": delivery,
            "ordering": ordering,
            "attrs": attrs,
            "clearance": clearance,
        }));
        Ok(())
    }

    /// cdn := "cdn" ID "of" ID "{" cdn_prop (";" cdn_prop)* "}"?
    /// cdn_prop := "provider" IDENT ":" TRUST | "staleness" (QUANTITY | "unlimited")
    ///           | "hit" PERCENT | "tls_terminates_at_provider"
    fn parse_cdn(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'cdn'
        let id = self.expect_ident("cdn id")?;
        self.expect_keyword("of")?;
        let of = self.expect_ident("cdn source-of-truth id")?;
        let mut provider: Option<String> = None;
        let mut provider_trust: Option<String> = None;
        let mut staleness: Option<serde_json::Value> = None;
        let mut staleness_unlimited = false;
        let mut hit: Option<f64> = None;
        let mut tls_terminates_at_provider = false;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("provider") {
                    self.advance();
                    provider = Some(self.expect_ident("provider name")?);
                    self.expect_symbol(':')?;
                    provider_trust = Some(self.expect_ident("provider trust level")?);
                } else if self.at_keyword("staleness") {
                    self.advance();
                    if self.at_keyword("unlimited") {
                        self.advance();
                        staleness_unlimited = true;
                    } else {
                        staleness = Some(self.parse_quantity("staleness")?);
                    }
                } else if self.at_keyword("hit") {
                    self.advance();
                    hit = Some(self.parse_percent("hit ratio")?);
                } else if self.at_keyword("tls_terminates_at_provider") {
                    self.advance();
                    tls_terminates_at_provider = true;
                } else {
                    return self.err("unknown cdn property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.cdns.push(json!({
            "id": id,
            "of": of,
            "provider": provider,
            "provider_trust": provider_trust,
            "staleness": staleness,
            "staleness_unlimited": staleness_unlimited,
            "hit": hit,
            "tls_terminates_at_provider": tls_terminates_at_provider,
        }));
        Ok(())
    }

    /// balancer := "balancer" ID (":" TRUST)? "{" balancer_prop (";" balancer_prop)* "}"?
    /// balancer_prop := "policy" IDENT | "sticky"
    ///
    /// WHY optional TRUST: T-0093, same rationale as `parse_queue` above --
    /// balancer had no TRUST clause and defaulted to `"trusted"` in the
    /// elaborator; the clause is optional to stay backward-compatible with
    /// every existing `.strata` source.
    fn parse_balancer(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'balancer'
        let id = self.expect_ident("balancer id")?;
        let mut trust: Option<String> = None;
        if self.at_symbol(':') {
            self.advance();
            trust = Some(self.expect_ident("trust level")?);
        }
        let mut policy: Option<String> = None;
        let mut sticky = false;
        if self.at_symbol('{') {
            self.advance();
            loop {
                if self.at_symbol('}') {
                    break;
                }
                if self.at_keyword("policy") {
                    self.advance();
                    policy = Some(self.expect_ident("balancer policy")?);
                } else if self.at_keyword("sticky") {
                    self.advance();
                    sticky = true;
                } else {
                    return self.err("unknown balancer property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.balancers.push(json!({
            "id": id,
            "trust": trust,
            "policy": policy,
            "sticky": sticky,
        }));
        Ok(())
    }

    fn parse_metric(&mut self) -> Result<String, ParseError> {
        let m = self.expect_ident("metric")?;
        match m.as_str() {
            "age" | "rate" | "latency" | "size" | "utilization" => Ok(m),
            _ => self.err(format!("unknown metric {:?}", m)),
        }
    }
}
