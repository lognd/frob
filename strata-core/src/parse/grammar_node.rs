// Node/secret grammar productions: `node { ... }` blocks, `on_deploy`
// canary stages, and `secret { ... }` constructs (docs/strata/surface.md#parser).
// frob:ticket T-1627

impl Parser {
    fn parse_node(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'node'
        let id = self.expect_ident("node id")?;
        self.expect_symbol(':')?;
        let trust = self.expect_ident("trust level")?;
        let mut is_abstract = false;
        if self.at_keyword("abstract") {
            self.advance();
            is_abstract = true;
        }
        let mut clearance = "Secret".to_string();
        let mut attrs: Vec<String> = Vec::new();
        let mut residence: Option<String> = None;
        let mut capacity: Option<serde_json::Value> = None;
        // T-0702: `users NUMBER` (steady population) / `rate NUMBER UNIT`
        // (arrival rate) -- entry-node demand declarations, the source
        // side of the demand-propagation mandate (docs/strata/kernel.md
        // #demand-t-0702). Both optional and independent (a node may
        // declare either, both, or neither); a repeated clause overwrites
        // (mirrors `platform`/`residence`), not accumulates.
        let mut users: Option<f64> = None;
        let mut demand_rate: Option<serde_json::Value> = None;
        let mut errors_total = false;
        let mut panics_contained_by: Option<String> = None;
        let mut observe: Option<serde_json::Value> = None;
        let mut code: Vec<String> = Vec::new();
        let mut may: Vec<String> = Vec::new();
        // T-1440: per-grant `via GLOB[, GLOB...]` surface, carried alongside
        // the flat `may` atom list (kept for back-compat consumers that only
        // care about kinds, e.g. seccomp/syscall export) so a SYS100-style
        // per-file join can be built without touching every existing `may`
        // reader. A via-less `may` still lands here with `via: []`, which
        // Python-side join logic (docs/strata/surface.md#may-scope) treats
        // as "whole node" -- unscoped, matching pre-T-1440 semantics exactly.
        let mut may_grants: Vec<serde_json::Value> = Vec::new();
        let mut deploy: Option<serde_json::Value> = None;
        let mut carries: Vec<String> = Vec::new();
        let mut is_managed = false;
        let mut waives: Vec<serde_json::Value> = Vec::new();
        let mut runs_as: Option<String> = None;
        let mut is_unit = false;
        let mut owns: Vec<serde_json::Value> = Vec::new();
        let mut listens: Vec<i64> = Vec::new();
        let mut group: Vec<String> = Vec::new();
        let mut sudoers: Vec<String> = Vec::new();
        // T-0261: std.host windows fields -- Windows analogs of
        // runs_as/unit/owns (docs/strata/host.md#windows-surface-grammar).
        let mut platform: Option<String> = None;
        let mut service_account: Option<String> = None;
        let mut service_account_gmsa = false;
        let mut is_service = false;
        let mut acl: Vec<serde_json::Value> = Vec::new();
        let mut pipes: Vec<String> = Vec::new();
        let mut krb_realm: Option<String> = None;
        let mut krb_is_kdc = false;
        let mut krb_spns: Vec<String> = Vec::new();
        let mut krb_delegation: Option<String> = None;
        let mut krb_delegation_targets: Vec<String> = Vec::new();
        let mut krb_trusts: Vec<serde_json::Value> = Vec::new();
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
                    attrs.extend(self.parse_attrval()?);
                } else if self.at_keyword("realm") {
                    // T-0262: `realm "REALM.NAME"` -- names the Kerberos
                    // realm/AD domain this node participates in or, paired
                    // with `kdc`, represents (docs/strata/krb.md). STRING,
                    // not IDENT, since a realm name commonly carries `.`
                    // (same `runs_as`/`code` precedent). At most one per
                    // node; a repeated clause overwrites, mirroring
                    // `clearance`.
                    self.advance();
                    krb_realm = Some(self.expect_string("realm name")?);
                } else if self.at_keyword("kdc") {
                    // T-0262: bare marker -- this node is the Key
                    // Distribution Center for its `realm` (docs/strata/
                    // krb.md). Mirrors `unit`'s bare-marker shape.
                    self.advance();
                    krb_is_kdc = true;
                } else if self.at_keyword("spn") {
                    // T-0262: `spn "SPN/value@REALM"`+ -- one or more
                    // service principal names bound to this node's
                    // `runs_as` service account (T-0255's principal,
                    // docs/strata/krb.md). STRING, repeatable, same shape
                    // as `code`/`carries`.
                    self.advance();
                    krb_spns.push(self.expect_string("spn value")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        krb_spns.push(self.expect_string("spn value")?);
                    }
                } else if self.at_keyword("delegation") {
                    // T-0262: `delegation none|constrained|rbcd|unconstrained
                    // [target "SPN"]*` -- the crown-jewel lateral-movement
                    // modeling target (docs/strata/krb.md). The kind is an
                    // IDENT drawn from a closed vocabulary (validated at
                    // elaboration time, mirroring how `boundary`'s
                    // endorse/declassify kind is grammar-fixed but other
                    // closed-vocabulary clauses like `observe`'s log
                    // classes defer validation to the elaborator); `target`
                    // is only meaningful for `constrained` but the parser
                    // accepts it unconditionally and leaves that check to
                    // the elaborator (law 2: no silent drop, but also no
                    // parser-level coupling between two clauses' shapes).
                    self.advance();
                    krb_delegation = Some(self.expect_ident("delegation kind")?);
                    while self.at_keyword("target") {
                        self.advance();
                        krb_delegation_targets.push(self.expect_string("delegation target spn")?);
                    }
                } else if self.at_keyword("trusts") {
                    // T-0262: `trusts IDENT [direction "one-way"|"two-way"]
                    // [transitive]` -- a domain trust from this realm node
                    // to another (docs/strata/krb.md). IDENT is the target
                    // realm node's id (a dangling/non-realm reference is an
                    // elaboration-time check, not a parser one, matching
                    // `panics_contained_by`'s precedent). Repeatable: a
                    // realm may trust more than one other realm.
                    self.advance();
                    let target = self.expect_ident("trusts target realm node id")?;
                    let mut direction = "one-way".to_string();
                    if self.at_keyword("direction") {
                        self.advance();
                        direction = self.expect_string("trust direction")?;
                    }
                    let mut transitive = false;
                    if self.at_keyword("transitive") {
                        self.advance();
                        transitive = true;
                    }
                    krb_trusts.push(json!({
                        "target": target,
                        "direction": direction,
                        "transitive": transitive,
                    }));
                } else if self.at_keyword("runs_as") {
                    // T-0255: `runs_as "svc-name"` -- names the dedicated
                    // OS service user the deploy generator creates for
                    // this node (docs/strata/host.md). STRING, not IDENT,
                    // since a service-user name commonly carries `-`
                    // (same `code`/`may` precedent). At most one per node;
                    // a repeated clause overwrites, mirroring `clearance`.
                    self.advance();
                    runs_as = Some(self.expect_string("runs_as service user name")?);
                } else if self.at_keyword("unit") {
                    // T-0255: bare marker -- this node's process is
                    // modeled as a systemd unit (docs/strata/host.md).
                    // Hardening directives are DERIVED by the generator
                    // (T-0256) from the rest of the model (may
                    // capabilities, owns, listens); this marker only
                    // records that the binding applies.
                    self.advance();
                    is_unit = true;
                } else if self.at_keyword("owns") {
                    // T-0255: `owns "PATH" "MODE"` -- a filesystem path
                    // this node's service user owns, with an explicit
                    // octal mode (docs/strata/host.md). Both STRING: PATH
                    // carries `/` (not a valid ident char) and MODE is
                    // quoted for the same "opaque atom" reason `code`/
                    // `may` use STRING. Repeatable: a node may own more
                    // than one path.
                    self.advance();
                    let path = self.expect_string("owns path")?;
                    let mode = self.expect_string("owns mode")?;
                    owns.push(json!({"path": path, "mode": mode}));
                } else if self.at_keyword("listens") {
                    // T-0255: `listens PORT` -- a TCP/UDP port this node's
                    // unit binds a socket to (docs/strata/host.md).
                    // NUMBER, not STRING: a port is a plain integer with
                    // no non-ident characters, matching `capacity`'s
                    // replicas bounds convention. Repeatable.
                    self.advance();
                    listens.push(self.expect_int("listens port")?);
                } else if self.at_keyword("group") {
                    // T-0272: `group "NAME"`+ -- one or more OS groups this
                    // node's service user is a member of (docs/strata/
                    // host.md#surface-grammar). STRING, not IDENT, mirroring
                    // `runs_as`'s "opaque atom" reason (a group name may
                    // carry `-`). Repeatable: a node's service user may
                    // belong to more than one group, same shape as `code`/
                    // `carries`. Desugars to a `group=<name>` attr, one per
                    // entry (owns-adjacent: `_host.py::_host_attrs`).
                    self.advance();
                    group.push(self.expect_string("group name")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        group.push(self.expect_string("group name")?);
                    }
                } else if self.at_keyword("sudoers") {
                    // T-0272: `sudoers "RULE"`+ -- one or more sudoers grant
                    // lines for this node's service user (docs/strata/
                    // host.md#surface-grammar). STRING, since a sudoers rule
                    // is free-form text (e.g. "ALL=(root) NOPASSWD: /bin/
                    // systemctl restart app"), the same "opaque atom"
                    // reasoning as `may`/`carries`. Repeatable: a service
                    // user may hold more than one sudoers grant. Desugars to
                    // a `sudoers=<rule>` attr, one per entry.
                    self.advance();
                    sudoers.push(self.expect_string("sudoers rule")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        sudoers.push(self.expect_string("sudoers rule")?);
                    }
                } else if self.at_keyword("platform") {
                    // T-0261: `platform "windows"` -- the std.host platform
                    // discriminator (docs/strata/host.md#hostmanifest).
                    // STRING, matching `realm`'s "opaque atom" shape. At
                    // most one per node; a repeated clause overwrites,
                    // mirroring `clearance`. Only `"windows"` is a known
                    // value -- an unrecognized platform name fails closed
                    // at `_host.py::host_manifest_for` time, not here
                    // (mirrors `owns` MODE/`listens` PORT deferring
                    // well-formedness checks to the elaborator).
                    self.advance();
                    platform = Some(self.expect_string("platform name")?);
                } else if self.at_keyword("service_account") {
                    // T-0261: `service_account "NAME" [gmsa]` -- names the
                    // dedicated Windows service account (or, with the
                    // trailing bare `gmsa` marker, a group Managed Service
                    // Account for domain-joined hosts) the deploy generator
                    // creates for this node (docs/strata/host.md#windows-
                    // surface-grammar). STRING, the Windows analog of
                    // `runs_as`. At most one per node; a repeated clause
                    // overwrites, mirroring `clearance`.
                    self.advance();
                    service_account = Some(self.expect_string("service account name")?);
                    if self.at_keyword("gmsa") {
                        self.advance();
                        service_account_gmsa = true;
                    }
                } else if self.at_keyword("service") {
                    // T-0261: bare marker -- this node's process is modeled
                    // as a Windows Service Control Manager (SCM) service
                    // (docs/strata/host.md#windows-surface-grammar), the
                    // Windows analog of `unit`. Hardening directives
                    // (service SID type restricted, required-privileges
                    // allowlist, protected-process) are DERIVED by the
                    // generator from the rest of the model, exactly like
                    // `unit`'s hardening derivation -- this marker only
                    // records that the binding applies.
                    self.advance();
                    is_service = true;
                } else if self.at_keyword("acl") {
                    // T-0261: `acl "PATH" "RULE"` -- a Windows NTFS path
                    // this node's service account has an explicit DACL
                    // entry for, RULE an opaque `PRINCIPAL:RIGHTS[:deny]
                    // [:no_inherit]` atom (docs/strata/host.md#windows-
                    // surface-grammar), the Windows analog of `owns` (richer
                    // than a 3-octal mode: expresses per-principal rights,
                    // deny ACEs, and deny-inheritance). Both STRING, same
                    // "opaque atom" reasoning `owns`'s MODE uses --
                    // well-formedness is validated at `_host.py` elaborate
                    // time, not here. Repeatable: a node may declare more
                    // than one ACL entry.
                    self.advance();
                    let path = self.expect_string("acl path")?;
                    let rule = self.expect_string("acl rule")?;
                    acl.push(json!({"path": path, "rule": rule}));
                } else if self.at_keyword("pipe") {
                    // T-0261: `pipe "NAME"`+ -- one or more named pipes this
                    // node's service listens on (docs/strata/host.md
                    // #windows-surface-grammar), additive to the platform-
                    // agnostic `listens` PORT surface (Windows firewall
                    // ports reuse `listens` unchanged -- a bound port is
                    // the same concept on every platform). STRING, since a
                    // pipe name commonly carries `\`. Repeatable.
                    self.advance();
                    pipes.push(self.expect_string("pipe name")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        pipes.push(self.expect_string("pipe name")?);
                    }
                } else if self.at_keyword("bin_path") {
                    // T-0629: `bin_path "PATH" ["ARGS"]` -- the Windows SCM
                    // `binPath`/ImagePath (executable path, plus an optional
                    // trailing arguments string) `sc.exe create` needs to
                    // actually stand up a `service`-marked node's SCM
                    // service, not just harden an already-existing one
                    // (docs/strata/host.md#windows-surface-grammar). Both
                    // STRING, same "opaque atom" reasoning `acl`'s PATH/RULE
                    // use -- a Windows executable path commonly carries `:`
                    // for a drive letter and `\` separators, and the
                    // trailing ARGS string is free-form. Desugars STRAIGHT
                    // to `bin_path=<path>` (+ `bin_path_args=<args>` when
                    // ARGS given) node attrs here, the same direct-attr-push
                    // shape `skew` uses below, rather than threading a new
                    // NodeDecl field through `_ast.py`/`_elaborate.py` (out
                    // of this ticket's scope) -- `_host.py::
                    // _parse_host_attrs` reads the two attrs back
                    // regardless of which caller (node or store) produced
                    // them, same shared-encoding discipline every other
                    // std.host clause uses. At most one per node; a
                    // repeated clause overwrites (mirrors `platform`).
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
                    // T-0702: `users NUMBER` -- a steady population entry
                    // demand (docs/strata/kernel.md#demand-t-0702).
                    self.advance();
                    users = Some(self.expect_number("users population")?);
                } else if self.at_keyword("rate") {
                    // T-0702: `rate NUMBER UNIT` -- an arrival-rate entry
                    // demand, same QUANTITY shape `flow`'s `rate` clause
                    // and `capacity`'s rate use (docs/strata/kernel.md
                    // #demand-t-0702). Top-level on node/store, distinct
                    // from `capacity`'s own nested rate quantity.
                    self.advance();
                    demand_rate = Some(self.parse_quantity("rate")?);
                } else if self.at_keyword("skew") {
                    // skew := "skew" "zipf" NUMBER; desugars straight to a
                    // node attr "skew=<alpha>" (docs/strata/kernel.md
                    // #capacity-semantics) -- no dedicated kernel field.
                    self.advance();
                    self.expect_keyword("zipf")?;
                    let alpha = self.expect_number("skew zipf exponent")?;
                    attrs.push(format!("skew={}", alpha));
                } else if self.at_keyword("errors_total") {
                    // T-0070: bare marker; the elaborator turns this into a
                    // node attr "errors_total" and requires an observe block.
                    self.advance();
                    errors_total = true;
                } else if self.at_keyword("code") {
                    // T-0132: `code GLOB+` -- one or more STRING-quoted
                    // globs (surface.md#grammar-sketch); STRING rather than
                    // IDENT because globs carry `/` and `*`, neither a
                    // valid ident char. Elaborated to `code=<glob>` node
                    // attrs, one per glob (T-0078 attr convention).
                    self.advance();
                    code.push(self.expect_string("code glob")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        code.push(self.expect_string("code glob")?);
                    }
                } else if self.at_keyword("may") {
                    // T-0132: `may CAPABILITY` -- a STRING-quoted
                    // capability atom (e.g. "net.out:stripe.com"); STRING
                    // rather than IDENT because capability atoms carry `.`
                    // and `:`, neither a valid ident char. Repeatable via
                    // multiple `may "...";` statements; lands directly in
                    // `Node.may` (no attr encoding needed, unlike `code`).
                    //
                    // T-1440: an optional `via GLOB[, GLOB...]` trailer
                    // scopes this ONE grant down to a subset of the node's
                    // own `code` glob(s) instead of blessing the whole node
                    // -- one or more STRING-quoted globs, comma-separated
                    // (same STRING choice as `code`, globs carry `/`/`*`).
                    // Omitting `via` entirely keeps the pre-T-1440 meaning
                    // (whole-node grant) for migration; that is a parser-
                    // level default (`via: []`), not a distinct keyword.
                    self.advance();
                    let atom = self.expect_string("may capability")?;
                    let mut via: Vec<String> = Vec::new();
                    if self.at_keyword("via") {
                        self.advance();
                        via.push(self.expect_string("may via glob")?);
                        while self.at_symbol(',') {
                            self.advance();
                            via.push(self.expect_string("may via glob")?);
                        }
                    }
                    // T-1627: an optional `exclusive` trailer after the via
                    // list marks this ONE grant as the sole legitimate site
                    // for its capability atom -- turning a permission into
                    // an invariant (docs/strata/surface.md#may-scope). Only
                    // meaningful paired with a single symbol-form via entry
                    // (`"path::qualname"`, T-1627's other half): a bare or
                    // multi-entry/file-form `via` gives no single site to be
                    // exclusive ABOUT, so that combination is a hard parse
                    // error here rather than a silently-ignored keyword --
                    // "cannot express what the grant claims" must fail loud
                    // at parse time, not be discovered later at conformance
                    // time (or never).
                    let mut exclusive = false;
                    if self.at_keyword("exclusive") {
                        self.advance();
                        exclusive = true;
                        if via.len() != 1 || !via[0].contains("::") {
                            return self.err(format!(
                                "may \"{}\" exclusive requires exactly one symbol-form via \
                                 entry (\"path::qualname\"), got {} via entry/entries",
                                atom,
                                via.len()
                            ));
                        }
                    }
                    // T-1478: an optional `of GLOB[, GLOB...]` trailer,
                    // parsed after `via`/`exclusive`, narrows this ONE
                    // grant to a subset of the specific ARGUMENT values
                    // the observed effect carries (e.g. `may "env.read" of
                    // "FROB_*"` covers only an `os.environ[...]`-style
                    // read whose literal key matches "FROB_*"), one level
                    // finer than `via`'s file/symbol-SITE scoping. One or
                    // more STRING-quoted globs, comma-separated (same
                    // STRING choice `via`/`code` already use). Omitting
                    // `of` entirely keeps the pre-T-1478 meaning (grant
                    // covers every argument value) for migration -- a
                    // parser-level default (`of: []`), not a distinct
                    // keyword; join semantics live in
                    // `frob.strata._effects` (docs/strata/surface.md
                    // #may-scope).
                    let mut of_patterns: Vec<String> = Vec::new();
                    if self.at_keyword("of") {
                        self.advance();
                        of_patterns.push(self.expect_string("may of argument glob")?);
                        while self.at_symbol(',') {
                            self.advance();
                            of_patterns.push(self.expect_string("may of argument glob")?);
                        }
                    }
                    may.push(atom.clone());
                    may_grants.push(json!({
                        "atom": atom,
                        "via": via,
                        "exclusive": exclusive,
                        "of": of_patterns
                    }));
                } else if self.at_keyword("carries") {
                    // T-0154: `carries PII_TAG+` -- one or more STRING-
                    // quoted PII tags (e.g. "identifier.email"), the SAME
                    // STRING-not-IDENT shape T-0132 chose for `code`/`may`
                    // (`.` is not a valid ident char, docs/strata/
                    // surface.md#node-grammar). Elaborated to `pii=<tag>`
                    // node attrs, one per tag (mirrors `code`'s
                    // `code=<glob>` desugar, `_pii.py::_PII_PREFIX`).
                    self.advance();
                    carries.push(self.expect_string("carries pii tag")?);
                    while matches!(self.cur().kind, TokKind::Str(_)) {
                        carries.push(self.expect_string("carries pii tag")?);
                    }
                } else if self.at_keyword("on") {
                    // T-0136: `on deploy { canary { ... }; endorsed_by ...;
                    // rollback within QUANTITY }` -- a node's deploy
                    // contract (docs/strata/surface.md#std-deploy, T-0083's
                    // landed kernel construct). `on crash`/`on breach` are
                    // still unimplemented surface syntax (T-0083's own
                    // deferral note), so `deploy` is the only `on` keyword
                    // this parser accepts today; anything else is a parse
                    // error, not a silent no-op (law 2).
                    self.advance();
                    self.expect_keyword("deploy")?;
                    deploy = Some(self.parse_on_deploy_block()?);
                } else if self.at_keyword("panics_contained_by") {
                    // T-0070: names the crash-boundary supervisor node id;
                    // reference validity is an elaboration-time check.
                    self.advance();
                    panics_contained_by = Some(self.expect_ident("panics supervisor id")?);
                } else if self.at_keyword("managed") {
                    // T-0172: bare marker, no argument -- mirrors
                    // `errors_total`'s shape. Marks the node as external,
                    // pure-config infrastructure with no scannable code by
                    // declaration (docs/strata/surface.md#node-grammar,
                    // #key-construct-semantics): tier-2 code-binding
                    // conformance is not required for it, and a fired
                    // weakness obligation on it discharges without the
                    // stricter mitigation-chokepoint (boundary-kind) proof
                    // that a code-modeled node needs -- config evidence or
                    // an `assume` claim stands in (`_threat.py::
                    // _check_one_discharge`).
                    self.advance();
                    is_managed = true;
                } else if self.at_keyword("waive") {
                    // T-0174: `waive RULE reason="..." [ticket="T-XXXX"]` --
                    // an in-design waiver for a `frob sys audit` finding
                    // (SYS100-102/THREAT002-003/LINT004) against THIS node,
                    // the surface analog of `frob:waive` for gate
                    // violations (docs/strata/surface.md#node-grammar,
                    // `frob.strata._waive`). RULE and reason are STRING
                    // (not IDENT) for the same reason `may`/`carries` are:
                    // rule ids and free-text reasons are not valid idents.
                    // `reason` is mandatory at parse time (law 2: no
                    // fabricated/implicit waivers, mirrors `assume`'s
                    // mandatory `owner`/`review` above) -- a `waive` clause
                    // with no reason is a hard parse error, never a silent
                    // pass. Repeatable: a node may waive more than one
                    // rule.
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
                } else if self.at_keyword("observe") {
                    // T-0070: observe { log IDENT (, IDENT)* ; to IDENT }
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
                    return self.err("unknown node property");
                }
                if self.at_symbol(';') {
                    self.advance();
                } else {
                    break;
                }
            }
            self.expect_symbol('}')?;
        }
        ast.nodes.push(json!({
            "id": id,
            "trust": trust,
            "is_abstract": is_abstract,
            "clearance": clearance,
            "attrs": attrs,
            "capacity": capacity,
            "users": users,
            "rate": demand_rate,
            "residence": residence,
            "errors_total": errors_total,
            "panics_contained_by": panics_contained_by,
            "observe": observe,
            "code": code,
            "may": may,
            "may_grants": may_grants,
            "deploy": deploy,
            "carries": carries,
            "is_managed": is_managed,
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
            "krb_realm": krb_realm,
            "krb_is_kdc": krb_is_kdc,
            "krb_spns": krb_spns,
            "krb_delegation": krb_delegation,
            "krb_delegation_targets": krb_delegation_targets,
            "krb_trusts": krb_trusts,
        }));
        Ok(())
    }

    /// deploy_block := "{" deploy_prop (";" deploy_prop)* "}"
    /// deploy_prop  := "canary" "{" canary_stage ("," canary_stage)* "}"
    ///               | "endorsed_by" REF ("," REF)*
    ///               | "rollback" "within" QUANTITY
    /// canary_stage := IDENT "for" QUANTITY
    ///
    /// WHY: `on deploy` desugars straight onto `_models.py::DeployContract`
    /// (T-0083's landed kernel construct, no new primitive here) --
    /// `canary`/`endorsed_by` are optional and default to an empty list
    /// (the elaborator supplies `()`, matching `DeployContract.stages`/
    /// `endorsement_chain`'s own semantics of "no stages/no endorsement
    /// required" rather than a parser default), but `rollback within
    /// QUANTITY` is mandatory -- `DeployContract.rollback_budget` has no
    /// default, and a missing rollback bound is exactly the "half a
    /// containment story" charter law 2 refuses to leave implicit
    /// (docs/strata/surface.md#std-deploy).
    fn parse_on_deploy_block(&mut self) -> Result<serde_json::Value, ParseError> {
        self.expect_symbol('{')?;
        let mut stages: Vec<serde_json::Value> = Vec::new();
        let mut endorsed_by: Vec<String> = Vec::new();
        let mut rollback_budget: Option<serde_json::Value> = None;
        loop {
            if self.at_symbol('}') {
                break;
            }
            if self.at_keyword("canary") {
                self.advance();
                self.expect_symbol('{')?;
                if !self.at_symbol('}') {
                    stages.push(self.parse_canary_stage()?);
                    while self.at_symbol(',') {
                        self.advance();
                        stages.push(self.parse_canary_stage()?);
                    }
                }
                self.expect_symbol('}')?;
            } else if self.at_keyword("endorsed_by") {
                self.advance();
                endorsed_by.push(self.expect_ident("endorsed_by boundary id")?);
                while self.at_symbol(',') {
                    self.advance();
                    endorsed_by.push(self.expect_ident("endorsed_by boundary id")?);
                }
            } else if self.at_keyword("rollback") {
                self.advance();
                self.expect_keyword("within")?;
                rollback_budget = Some(self.parse_quantity("rollback budget")?);
            } else {
                return self.err("unknown deploy property");
            }
            if self.at_symbol(';') {
                self.advance();
            } else {
                break;
            }
        }
        self.expect_symbol('}')?;
        let rollback_budget = match rollback_budget {
            Some(r) => r,
            None => return self.err("on deploy block needs a rollback within QUANTITY clause"),
        };
        Ok(json!({
            "stages": stages,
            "endorsed_by": endorsed_by,
            "rollback_budget": rollback_budget,
        }))
    }

    /// canary_stage := IDENT "for" QUANTITY
    fn parse_canary_stage(&mut self) -> Result<serde_json::Value, ParseError> {
        let level = self.expect_ident("canary stage level")?;
        self.expect_keyword("for")?;
        let bake = self.parse_quantity("canary stage bake duration")?;
        Ok(json!({"level": level, "bake": bake}))
    }

    /// secret := "secret" ID "{" secret_prop (";" secret_prop)* "}"
    /// secret_prop := "issued_by" REF | "audience" "{" REF ("," REF)* "}"
    ///              | "lifetime" QUANTITY | "revoke" QUANTITY
    ///
    /// WHY: mirrors `_secrets.py::SecretSpec` field for field (T-0082's
    /// landed kernel construct, docs/strata/surface.md#std-secrets's
    /// normative sketch: `secret X issued_by Y audience [...] lifetime T
    /// revoke T'`). `revoke` is grammar-optional -- `SecretSpec.revoke` is
    /// `Quantity | None`, and the mandatory-revocation rule is enforced by
    /// `_secrets.py::_validate_secret_bounds` (`MissingRevocation`) at
    /// elaboration time, not here, matching how `code`/`may`'s downstream
    /// validation already lives in the elaborator rather than the parser.
    fn parse_secret(&mut self, ast: &mut ModuleAst) -> Result<(), ParseError> {
        self.advance(); // 'secret'
        let id = self.expect_ident("secret id")?;
        self.expect_symbol('{')?;
        let mut issued_by: Option<String> = None;
        let mut audience: Vec<String> = Vec::new();
        let mut lifetime: Option<serde_json::Value> = None;
        let mut revoke: Option<serde_json::Value> = None;
        loop {
            if self.at_symbol('}') {
                break;
            }
            if self.at_keyword("issued_by") {
                self.advance();
                issued_by = Some(self.expect_ident("secret issuing authority")?);
            } else if self.at_keyword("audience") {
                self.advance();
                self.expect_symbol('{')?;
                if !self.at_symbol('}') {
                    audience.push(self.expect_ident("secret audience member")?);
                    while self.at_symbol(',') {
                        self.advance();
                        audience.push(self.expect_ident("secret audience member")?);
                    }
                }
                self.expect_symbol('}')?;
            } else if self.at_keyword("lifetime") {
                self.advance();
                lifetime = Some(self.parse_quantity("secret lifetime")?);
            } else if self.at_keyword("revoke") {
                self.advance();
                revoke = Some(self.parse_quantity("secret revoke SLA")?);
            } else {
                return self.err("unknown secret property");
            }
            if self.at_symbol(';') {
                self.advance();
            } else {
                break;
            }
        }
        self.expect_symbol('}')?;
        let issued_by = match issued_by {
            Some(i) => i,
            None => return self.err("secret needs an issued_by clause"),
        };
        let lifetime = match lifetime {
            Some(l) => l,
            None => return self.err("secret needs a lifetime clause"),
        };
        ast.secrets.push(json!({
            "id": id,
            "issued_by": issued_by,
            "audience": audience,
            "lifetime": lifetime,
            "revoke": revoke,
        }));
        Ok(())
    }

}
