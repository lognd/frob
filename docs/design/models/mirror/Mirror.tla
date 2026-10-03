------------------------------- MODULE Mirror -------------------------------
(***************************************************************************)
(* The one-way ticket mirror of docs/design/mirror.md section 3.1.        *)
(*                                                                         *)
(* Two replicas of each ticket: the ledger (ticket branch, source of      *)
(* truth for repository-owned fields) and one tracker issue. Field "r" is *)
(* repository-owned (title/body), field "tf" is tracker-owned (labels     *)
(* outside frob:, comments). The hidden ULID marker "mk" lives in the     *)
(* body. One mirror process runs non-atomic steps; humans edit the        *)
(* tracker at any time; calls fail, are refused by the per-run budget,    *)
(* lose their response, are delayed or delivered twice; the mirror        *)
(* crashes at any step; the map file may be read stale.                   *)
(*                                                                         *)
(* Boolean protocol switches select between the protocol as written       *)
(* (all FALSE) and the repaired protocol (all TRUE); see README.md.       *)
(***************************************************************************)
EXTENDS Integers, Sequences, FiniteSets, TLC

CONSTANTS
    NT,           \* number of tickets (tickets are 1..NT)
    NV,           \* size of the value domain of field r (values 0..NV-1)
    MaxIssues,    \* tracker issue numbers 1..MaxIssues
    MaxDays,      \* days 0..MaxDays (for the comment rate bound)
    Budget,       \* API calls per run; the next call is refused (rate limit)
    MaxEdits,     \* human edits of the repository-owned field r
    MaxTEdits,    \* human edits of the tracker-owned field tf
    MaxCommits,   \* maintainer ledger commits (accepted proposals are extra)
    MaxCrashes,   \* mirror crashes (at any step)
    MaxFails,     \* failed calls (5xx, timeout before effect): no effect
    MaxNet,       \* network anomalies, of the kinds in NetKinds
    NetKinds,     \* subset of {"lost","delay","dupw","dupc"}
    MaxSpoof,     \* human marker edits plus human-created marked issues
    MaxStale,     \* runs that read an old version of the map file
    HMax,         \* bound on history length (checked by HistBound)
    \* protocol switches (FALSE = as written in mirror.md, TRUE = repaired)
    Sched,              \* runs are also started by a schedule, not only by ledger pushes
    CursorAtRead,       \* history cursor = position observed at the read, not after the publish
    EarlyCursor,        \* that position is taken at the first read of the ticket (find or state)
    MapCAS,             \* the map file is written with compare-and-swap on its content
    AuthCreation,       \* a marker counts only in the bot-authored creation revision
    ConsistentFind,     \* find-by-ULID is read-your-writes (list by label), not a lagging search index
    ScanDups,           \* every run lists the ticket's issues, reads their history, closes duplicates
    CommentCheckTracker,\* "one comment per day" is checked against the issue's comments
    RoundRobin,         \* each run starts at the ticket after the last one completed
    Dedupe              \* proposals are deduplicated by tracker event id

ASSUME NetKinds \subseteq {"lost", "delay", "dupw", "dupc"}

T   == 1..NT
Val == 0..(NV - 1)
I   == 1..MaxIssues
Day == 0..MaxDays
BOT == "bot"
HUM == "hum"

Min(S) == CHOOSE x \in S : \A y \in S : x <= y
Max(S) == CHOOSE x \in S : \A y \in S : y <= x

VARIABLES
    \* ---- ledger (ticket branch); only maintainers and the mirror write it
    led,        \* [T -> Val]: projection of field r for each ticket
    lvals,      \* ghost: [T -> SUBSET Val], every value the ledger has held for the ticket
    prop,       \* [T -> proposal]: one collapsed proposal per ticket (one human user)
    rec,        \* [T -> SUBSET Nat]: tracker event ids (history positions) recorded as proposals
    resolved,   \* ghost: event ids whose proposal was accepted or declined
    trig,       \* a ledger push not yet consumed by a run (CI trigger)
    \* ---- map file mirror.toml on the ticket branch
    mapf,       \* [m: ticket -> issue (0 none), cur: history cursor, lc: last comment day, rr: next ticket]
    mapPrev,    \* the previous version of the map file (what a stale read sees)
    \* ---- tracker
    iss,        \* [I -> issue record]
    nIss,       \* next issue number
    hist,       \* append-only change history, positions are tracker event ids
    idx,        \* issues visible to the (lagging) search index
    com,        \* [I -> [Day -> Nat]]: comments by the bot per issue per day
    dupCom,     \* ghost: comments that are duplicated deliveries
    day,
    \* ---- network
    net,        \* requests whose effect is still to come (delayed or duplicated)
    \* ---- mirror process (local state, lost on crash)
    m,
    \* ---- bounded environment counters
    cnt

vars == <<led, lvals, prop, rec, resolved, trig, mapf, mapPrev,
          iss, nIss, hist, idx, com, dupCom, day, net, m, cnt>>

ledV == <<led, lvals, prop, rec, resolved, trig>>
mapV == <<mapf, mapPrev>>
trkV == <<iss, nIss, hist, idx, com, dupCom, day>>

NoIssue == [ex |-> FALSE, au |-> "none", mk0 |-> 0, mk |-> 0, r |-> 0, tf |-> 0, op |-> FALSE]
InitMap == [m |-> [t \in T |-> 0], cur |-> [t \in T |-> 0],
            lc |-> [t \in T |-> -1], rr |-> 1]
NoProp  == [st |-> "none", v |-> 0, hs |-> {}]
MIdle   == [pc |-> "idle", sL |-> [t \in T |-> 0], mL |-> InitMap,
            stl |-> FALSE, b |-> 0, k |-> 0, st |-> 1, ct |-> 1,
            rs |-> [r |-> 0, mk |-> 0], hp |-> -1, ents |-> {}, np |-> FALSE,
            dups |-> {}, dc |-> {}, rw |-> 0, lw |-> 0, quiet |-> FALSE]

Entry(i, f, u, v, t) == [i |-> i, f |-> f, u |-> u, v |-> v, t |-> t]

(* Ground truth: the ticket an issue was created for by the bot (0 otherwise). *)
Own(i) == IF iss[i].ex /\ iss[i].au = BOT THEN iss[i].mk0 ELSE 0
Owned(t) == {i \in I : i < nIss /\ Own(i) = t}
HumanR(p) == hist[p].u = HUM /\ hist[p].f = "r"
(* A human edit of a repository-owned field of a ticket's issue, not yet a proposal. *)
Unrec(t, p) == p \in 1..Len(hist) /\ HumanR(p) /\ Own(hist[p].i) = t /\ p \notin rec[t]
Synced(t) == mapf.m[t] # 0 /\ iss[mapf.m[t]].r = led[t] /\ iss[mapf.m[t]].mk = t
Clean == /\ net = {}
         /\ \A t \in T : /\ Synced(t)
                         /\ Owned(t) = {mapf.m[t]}
                         /\ \A p \in 1..Len(hist) : ~Unrec(t, p)

(* What find-by-ULID matches on. *)
FindMark(i) == IF AuthCreation THEN iss[i].mk0 ELSE iss[i].mk
Found(t) == {i \in I : i < nIss /\ iss[i].au = BOT /\ FindMark(i) = t
                       /\ (ConsistentFind \/ i \in idx)}

Init ==
    /\ led = [t \in T |-> 0]
    /\ lvals = [t \in T |-> {0}]
    /\ prop = [t \in T |-> NoProp]
    /\ rec = [t \in T |-> {}]
    /\ resolved = {}
    /\ trig = TRUE
    /\ mapf = InitMap
    /\ mapPrev = InitMap
    /\ iss = [i \in I |-> NoIssue]
    /\ nIss = 1
    /\ hist = << >>
    /\ idx = {}
    /\ com = [i \in I |-> [d \in Day |-> 0]]
    /\ dupCom = [i \in I |-> [d \in Day |-> 0]]
    /\ day = 0
    /\ net = {}
    /\ m = MIdle
    /\ cnt = [ed |-> 0, te |-> 0, cm |-> 0, cr |-> 0, fl |-> 0, nt |-> 0, sp |-> 0, sl |-> 0]

-----------------------------------------------------------------------------
(* Mirror process. Control flow per ticket:                                *)
(*   find? -> create? -> rstate -> rhist -> prop? -> write? -> close*      *)
(*   -> comment? -> fin, then the next ticket, then commit (map file).     *)
(* Calls (find, create, rstate, rhist, write, close, comment) cost one     *)
(* unit of budget each; prop (ledger commit) and commit (map file) are    *)
(* git pushes to the ticket branch, not tracker API calls.                *)

CallPC == {"find", "create", "rstate", "rhist", "write", "close", "comment"}

Begin(mm, kk) ==
    IF kk = NT THEN [mm EXCEPT !.k = kk, !.pc = "commit"]
    ELSE LET t == ((mm.st - 1 + kk) % NT) + 1
         IN [mm EXCEPT !.k = kk, !.ct = t, !.dups = {}, !.dc = {}, !.np = FALSE,
                       !.ents = {}, !.hp = -1, !.rs = [r |-> 0, mk |-> 0],
                       !.pc = IF mm.mL.m[t] = 0 \/ ScanDups THEN "find" ELSE "rstate"]

NeedWrite(mm)    == mm.rs.r # mm.sL[mm.ct] \/ mm.rs.mk # mm.ct
CommentDue(mm)   == mm.np /\ (CommentCheckTracker \/ mm.mL.lc[mm.ct] # day)
AfterClose(mm)   == IF CommentDue(mm) THEN "comment" ELSE "fin"
AfterWrite(mm)   == IF mm.dc # {} THEN "close" ELSE AfterClose(mm)
AfterProp(mm)    == IF NeedWrite(mm) THEN "write" ELSE AfterWrite(mm)

MStart ==
    /\ m.pc = "idle"
    /\ trig \/ Sched
    /\ \E stale \in BOOLEAN :
         /\ stale => (cnt.sl < MaxStale /\ mapPrev # mapf)
         /\ cnt' = IF stale THEN [cnt EXCEPT !.sl = @ + 1] ELSE cnt
         /\ LET ml == IF stale THEN mapPrev ELSE mapf
                m0 == [m EXCEPT !.sL = led, !.mL = ml, !.stl = stale,
                                !.b = Budget, !.st = IF RoundRobin THEN ml.rr ELSE 1,
                                !.rw = 0, !.lw = 0, !.quiet = Clean /\ ~stale]
            IN m' = Begin(m0, 0)
    /\ trig' = FALSE
    /\ UNCHANGED <<led, lvals, prop, rec, resolved, mapV, trkV, net>>

MRefuse ==   \* rate limit: the budget of this run is exhausted, the call is refused
    /\ m.pc \in CallPC /\ m.b = 0
    /\ m' = [m EXCEPT !.pc = "commit"]
    /\ UNCHANGED <<ledV, mapV, trkV, net, cnt>>

MFail ==     \* the call fails with no effect; the run stops cleanly
    /\ m.pc \in CallPC /\ m.b > 0 /\ cnt.fl < MaxFails
    /\ cnt' = [cnt EXCEPT !.fl = @ + 1]
    /\ m' = [m EXCEPT !.b = @ - 1, !.pc = "commit"]
    /\ UNCHANGED <<ledV, mapV, trkV, net>>

MCrash ==    \* the process dies; local state is lost, requests in flight stay in flight
    /\ m.pc # "idle" /\ cnt.cr < MaxCrashes
    /\ cnt' = [cnt EXCEPT !.cr = @ + 1]
    /\ m' = MIdle
    /\ UNCHANGED <<ledV, mapV, trkV, net>>

MFind ==
    /\ m.pc = "find" /\ m.b > 0
    /\ LET t     == m.ct
           F     == Found(t)
           canon == IF m.mL.m[t] # 0 THEN m.mL.m[t]
                    ELSE IF F = {} THEN 0 ELSE Min(F)
           D     == IF ScanDups THEN F \ {canon} ELSE {}
       IN m' = [m EXCEPT !.b = @ - 1, !.mL.m[t] = canon, !.dups = D,
                         !.dc = {d \in D : iss[d].op},
                         !.hp = IF EarlyCursor THEN Len(hist) ELSE -1,
                         !.pc = IF canon = 0 THEN "create" ELSE "rstate"]
    /\ UNCHANGED <<ledV, mapV, trkV, net, cnt>>

MCreate ==
    /\ m.pc = "create" /\ m.b > 0 /\ nIss <= MaxIssues
    /\ LET t  == m.ct
           i  == nIss
           ni == [ex |-> TRUE, au |-> BOT, mk0 |-> t, mk |-> t, r |-> m.sL[t], tf |-> 0, op |-> TRUE]
           e  == Entry(i, "create", BOT, m.sL[t], t)
       IN \/ \* success: the response carries the issue number
             /\ iss' = [iss EXCEPT ![i] = ni] /\ nIss' = i + 1 /\ hist' = Append(hist, e)
             \* the cursor stays at the position seen before the find (EarlyCursor):
             \* an earlier, delayed create may have produced an issue already edited
             /\ m' = [m EXCEPT !.b = @ - 1, !.rw = @ + 1, !.mL.m[t] = i,
                               !.mL.cur[t] = IF CursorAtRead THEN @ ELSE Len(hist) + 1,
                               !.hp = IF EarlyCursor THEN @ ELSE Len(hist) + 1, !.pc = "fin"]
             /\ UNCHANGED <<net, cnt>>
          \/ \* the issue is created but the response is lost: the mirror sees a failure
             /\ "lost" \in NetKinds /\ cnt.nt < MaxNet
             /\ cnt' = [cnt EXCEPT !.nt = @ + 1]
             /\ iss' = [iss EXCEPT ![i] = ni] /\ nIss' = i + 1 /\ hist' = Append(hist, e)
             /\ m' = [m EXCEPT !.b = @ - 1, !.rw = @ + 1, !.pc = "commit"]
             /\ UNCHANGED net
          \/ \* timeout: no effect yet, the request may still take effect later
             /\ "delay" \in NetKinds /\ cnt.nt < MaxNet
             /\ cnt' = [cnt EXCEPT !.nt = @ + 1]
             /\ net' = net \cup {[k |-> "create", i |-> 0, t |-> t, v |-> m.sL[t]]}
             /\ m' = [m EXCEPT !.b = @ - 1, !.rw = @ + 1, !.pc = "commit"]
             /\ UNCHANGED <<iss, nIss, hist>>
    /\ UNCHANGED <<ledV, mapV, idx, com, dupCom, day>>

MRState ==
    /\ m.pc = "rstate" /\ m.b > 0
    /\ LET i == m.mL.m[m.ct]
       IN m' = [m EXCEPT !.b = @ - 1, !.rs = [r |-> iss[i].r, mk |-> iss[i].mk],
                         !.hp = IF EarlyCursor /\ @ < 0 THEN Len(hist) ELSE @,
                         !.pc = "rhist"]
    /\ UNCHANGED <<ledV, mapV, trkV, net, cnt>>

MRHist ==
    /\ m.pc = "rhist" /\ m.b > 0
    /\ LET t  == m.ct
           S  == {m.mL.m[t]} \cup m.dups
           E  == {p \in (m.mL.cur[t] + 1)..Len(hist) : HumanR(p) /\ hist[p].i \in S}
           E2 == IF Dedupe THEN E \ rec[t] ELSE E
           m1 == [m EXCEPT !.b = @ - 1, !.ents = E2,
                           !.hp = IF EarlyCursor THEN @ ELSE Len(hist)]
       IN m' = [m1 EXCEPT !.pc = IF E2 # {} THEN "prop" ELSE AfterProp(m1)]
    /\ UNCHANGED <<ledV, mapV, trkV, net, cnt>>

MProp ==     \* ledger commit of the proposal events (CAS on the ticket branch)
    /\ m.pc = "prop"
    /\ LET t  == m.ct
           hs == IF prop[t].st = "pending" THEN prop[t].hs \cup m.ents ELSE m.ents
       IN /\ prop' = [prop EXCEPT ![t] = [st |-> "pending", v |-> hist[Max(hs)].v, hs |-> hs]]
          /\ rec' = [rec EXCEPT ![t] = @ \cup m.ents]
          /\ LET m1 == [m EXCEPT !.np = TRUE, !.lw = @ + 1]
             IN m' = [m1 EXCEPT !.pc = AfterProp(m1)]
    /\ UNCHANGED <<led, lvals, resolved, trig, mapV, trkV, net, cnt>>

MWrite ==    \* revert r (and the marker) to the projection of the run's ledger snapshot
    /\ m.pc = "write" /\ m.b > 0
    /\ LET t   == m.ct
           i   == m.mL.m[t]
           chg == iss[i].r # m.sL[t] \/ iss[i].mk # t
           h2  == IF chg THEN Append(hist, Entry(i, "r", BOT, m.sL[t], t)) ELSE hist
           m1  == [m EXCEPT !.b = @ - 1, !.rw = @ + 1,
                            !.mL.cur[t] = IF CursorAtRead THEN @ ELSE Len(h2)]
       IN /\ iss' = [iss EXCEPT ![i].r = m.sL[t], ![i].mk = t]
          /\ hist' = h2
          /\ m' = [m1 EXCEPT !.pc = AfterWrite(m1)]
          /\ \/ UNCHANGED <<net, cnt>>
             \/ /\ "dupw" \in NetKinds /\ cnt.nt < MaxNet
                /\ cnt' = [cnt EXCEPT !.nt = @ + 1]
                /\ net' = net \cup {[k |-> "write", i |-> i, t |-> t, v |-> m.sL[t]]}
    /\ UNCHANGED <<ledV, mapV, nIss, idx, com, dupCom, day>>

MClose ==    \* close one duplicate issue of the ticket (never delete)
    /\ m.pc = "close" /\ m.b > 0
    /\ LET d  == Min(m.dc)
           m1 == [m EXCEPT !.b = @ - 1, !.rw = @ + 1, !.dc = @ \ {d}]
       IN /\ iss' = [iss EXCEPT ![d].op = FALSE]
          /\ hist' = IF iss[d].op THEN Append(hist, Entry(d, "close", BOT, 0, m.ct)) ELSE hist
          /\ m' = [m1 EXCEPT !.pc = IF m1.dc # {} THEN "close" ELSE AfterClose(m1)]
    /\ UNCHANGED <<ledV, mapV, nIss, idx, com, dupCom, day, net, cnt>>

MComment ==  \* the host-template comment: "saved as a proposal, a maintainer can accept it"
    /\ m.pc = "comment" /\ m.b > 0
    /\ LET t    == m.ct
           i    == m.mL.m[t]
           post == ~CommentCheckTracker \/ com[i][day] = 0
       IN /\ m' = [m EXCEPT !.b = @ - 1, !.rw = IF post THEN @ + 1 ELSE @,
                            !.mL.lc[t] = IF post THEN day ELSE @, !.pc = "fin"]
          /\ com' = IF post THEN [com EXCEPT ![i][day] = @ + 1] ELSE com
          /\ \/ UNCHANGED <<net, cnt>>
             \/ /\ post /\ "dupc" \in NetKinds /\ cnt.nt < MaxNet
                /\ cnt' = [cnt EXCEPT !.nt = @ + 1]
                /\ net' = net \cup {[k |-> "comment", i |-> i, t |-> t, v |-> 0]}
    /\ UNCHANGED <<ledV, mapV, iss, nIss, hist, idx, dupCom, day>>

MFin ==      \* ticket done: advance its cursor (in the local copy of the map) and move on
    /\ m.pc = "fin"
    /\ LET t  == m.ct
           m1 == [m EXCEPT !.mL.cur[t] = IF CursorAtRead THEN m.hp ELSE @,
                           !.mL.rr = (t % NT) + 1]
       IN m' = Begin(m1, m.k + 1)
    /\ UNCHANGED <<ledV, mapV, trkV, net, cnt>>

MCommit ==   \* write the map file to the ticket branch, then the run ends
    /\ m.pc = "commit"
    /\ IF (MapCAS /\ m.stl) \/ m.mL = mapf
       THEN UNCHANGED mapV
       ELSE mapf' = m.mL /\ mapPrev' = IF MaxStale > 0 THEN mapf ELSE mapPrev
    /\ m' = MIdle
    /\ UNCHANGED <<ledV, trkV, net, cnt>>

MirrorStep ==
    \/ MStart \/ MFind \/ MCreate \/ MRState \/ MRHist \/ MProp \/ MWrite
    \/ MClose \/ MComment \/ MFin \/ MCommit \/ MRefuse \/ MFail \/ MCrash

-----------------------------------------------------------------------------
(* Environment: adversarial tracker users, maintainers, network, time.    *)

Disturb == m' = [m EXCEPT !.quiet = FALSE]

HEditR(i, v) ==   \* any human edits the repository-owned field of any issue
    /\ i < nIss /\ v # iss[i].r /\ cnt.ed < MaxEdits
    /\ iss' = [iss EXCEPT ![i].r = v]
    /\ hist' = Append(hist, Entry(i, "r", HUM, v, 0))
    /\ cnt' = [cnt EXCEPT !.ed = @ + 1]
    /\ Disturb
    /\ UNCHANGED <<ledV, mapV, nIss, idx, com, dupCom, day, net>>

HEditT(i) ==      \* any human edits a tracker-owned field
    /\ i < nIss /\ cnt.te < MaxTEdits
    /\ iss' = [iss EXCEPT ![i].tf = 1 - @]
    /\ hist' = Append(hist, Entry(i, "tf", HUM, 1 - iss[i].tf, 0))
    /\ cnt' = [cnt EXCEPT !.te = @ + 1]
    /\ Disturb
    /\ UNCHANGED <<ledV, mapV, nIss, idx, com, dupCom, day, net>>

HSpoof(i, t) ==   \* a human pastes another ticket's marker into a bot issue's body
    /\ i < nIss /\ iss[i].au = BOT /\ iss[i].mk # t /\ cnt.sp < MaxSpoof
    /\ iss' = [iss EXCEPT ![i].mk = t]
    /\ hist' = Append(hist, Entry(i, "mk", HUM, t, 0))
    /\ cnt' = [cnt EXCEPT !.sp = @ + 1]
    /\ Disturb
    /\ UNCHANGED <<ledV, mapV, nIss, idx, com, dupCom, day, net>>

HCreate(t) ==     \* a human creates an issue carrying a copied marker
    /\ nIss <= MaxIssues /\ cnt.sp < MaxSpoof
    /\ iss' = [iss EXCEPT ![nIss] = [ex |-> TRUE, au |-> HUM, mk0 |-> t, mk |-> t,
                                     r |-> 0, tf |-> 0, op |-> TRUE]]
    /\ nIss' = nIss + 1
    /\ hist' = Append(hist, Entry(nIss, "create", HUM, 0, 0))
    /\ cnt' = [cnt EXCEPT !.sp = @ + 1]
    /\ Disturb
    /\ UNCHANGED <<ledV, mapV, idx, com, dupCom, day, net>>

LCommit(t, v) ==  \* a maintainer changes a repository-owned field through ticket verbs
    /\ cnt.cm < MaxCommits /\ v # led[t]
    /\ led' = [led EXCEPT ![t] = v]
    /\ lvals' = [lvals EXCEPT ![t] = @ \cup {v}]
    /\ trig' = TRUE
    /\ cnt' = [cnt EXCEPT !.cm = @ + 1]
    /\ Disturb
    /\ UNCHANGED <<prop, rec, resolved, mapV, trkV, net>>

Accept(t) ==      \* frob ticket proposals accept: an event authored by the accepter
    /\ prop[t].st = "pending"
    /\ led' = [led EXCEPT ![t] = prop[t].v]
    /\ lvals' = [lvals EXCEPT ![t] = @ \cup {prop[t].v}]
    /\ prop' = [prop EXCEPT ![t].st = "accepted"]
    /\ resolved' = resolved \cup prop[t].hs
    /\ trig' = TRUE
    /\ Disturb
    /\ UNCHANGED <<rec, mapV, trkV, net, cnt>>

Decline(t) ==
    /\ prop[t].st = "pending"
    /\ prop' = [prop EXCEPT ![t].st = "declined"]
    /\ resolved' = resolved \cup prop[t].hs
    /\ trig' = TRUE
    /\ Disturb
    /\ UNCHANGED <<led, lvals, rec, mapV, trkV, net, cnt>>

Deliver(x) ==     \* a delayed or duplicated request takes effect now
    /\ x \in net
    /\ net' = net \ {x}
    /\ CASE x.k = "create" ->
              /\ nIss <= MaxIssues
              /\ iss' = [iss EXCEPT ![nIss] = [ex |-> TRUE, au |-> BOT, mk0 |-> x.t, mk |-> x.t,
                                               r |-> x.v, tf |-> 0, op |-> TRUE]]
              /\ nIss' = nIss + 1
              /\ hist' = Append(hist, Entry(nIss, "create", BOT, x.v, x.t))
              /\ UNCHANGED <<com, dupCom>>
         [] x.k = "write" ->
              /\ iss' = [iss EXCEPT ![x.i].r = x.v, ![x.i].mk = x.t]
              /\ hist' = IF iss[x.i].r # x.v \/ iss[x.i].mk # x.t
                         THEN Append(hist, Entry(x.i, "r", BOT, x.v, x.t)) ELSE hist
              /\ UNCHANGED <<nIss, com, dupCom>>
         [] x.k = "comment" ->
              /\ com' = [com EXCEPT ![x.i][day] = @ + 1]
              /\ dupCom' = [dupCom EXCEPT ![x.i][day] = @ + 1]
              /\ UNCHANGED <<iss, nIss, hist>>
    /\ Disturb
    /\ UNCHANGED <<ledV, mapV, idx, day, cnt>>

Tick ==
    /\ day < MaxDays
    /\ day' = day + 1
    /\ UNCHANGED <<ledV, mapV, iss, nIss, hist, idx, com, dupCom, net, m, cnt>>

IndexI(i) ==      \* the search index catches up with issue i
    /\ ~ConsistentFind /\ i < nIss /\ i \notin idx
    /\ idx' = idx \cup {i}
    /\ UNCHANGED <<ledV, mapV, iss, nIss, hist, com, dupCom, day, net, m, cnt>>

Env ==
    \/ \E i \in I, v \in Val : HEditR(i, v)
    \/ \E i \in I : HEditT(i)
    \/ \E i \in I, t \in T : HSpoof(i, t)
    \/ \E t \in T : HCreate(t)
    \/ \E t \in T, v \in Val : LCommit(t, v)
    \/ \E t \in T : Accept(t) \/ Decline(t)
    \/ \E x \in net : Deliver(x)
    \/ Tick
    \/ \E i \in I : IndexI(i)

Next == MirrorStep \/ Env

(* Weak fairness of the mirror only; humans, maintainers and the network  *)
(* get none. The search index eventually catches up.                      *)
Fairness == WF_vars(MirrorStep) /\ WF_vars(\E i \in I : IndexI(i))

Spec == Init /\ [][Next]_vars /\ Fairness
SafetySpec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* Properties.                                                             *)

TypeOK ==
    /\ led \in [T -> Val]
    /\ nIss \in 1..(MaxIssues + 1)
    /\ m.pc \in {"idle", "commit", "fin", "prop"} \cup CallPC
    /\ m.b \in 0..Budget

(* S1: the mirror never writes a tracker-owned field. *)
NoTrackerOwnedWrite ==
    \A p \in 1..Len(hist) : hist[p].u = BOT => hist[p].f # "tf"
NoTrackerOwnedWriteA ==
    [][\A i \in I : iss'[i].tf # iss[i].tf => HEditT(i)]_vars

(* S2 (inductive core of no-loss): every human edit of a repository-owned *)
(* field of a ticket's issue that lies at or before the ticket's committed *)
(* cursor has been recorded as a proposal.                                  *)
CursorSound ==
    \A t \in T : \A p \in 1..Len(hist) :
        (p <= mapf.cur[t] /\ HumanR(p) /\ Own(hist[p].i) = t) => p \in rec[t]

(* S3: never two issues for one ticket. *)
NoDupIssue == \A t \in T : Cardinality(Owned(t)) <= 1

(* S4: proposals never modify the tracker; every value the bot puts in a  *)
(* repository-owned field is a value the ledger held for that ticket, the *)
(* run's snapshot is the ledger, and only ticket verbs (maintainer commit, *)
(* accept) change the ledger.                                               *)
WritesFromLedger ==
    /\ \A p \in 1..Len(hist) :
          (hist[p].u = BOT /\ hist[p].f \in {"r", "create"})
              => hist[p].v \in lvals[hist[p].t]
    /\ \A x \in net : x.k \in {"create", "write"} => x.v \in lvals[x.t]
SnapshotIsLedger ==
    [][(m.pc = "idle" /\ m'.pc # "idle") => m'.sL = led]_vars
ProposalsNoTrackerEffect ==
    [][(m.pc = "prop" /\ rec' # rec) => UNCHANGED <<iss, hist, com, net>>]_vars
LedgerOnlyByVerbs ==
    [][led' # led => \E t \in T : Accept(t) \/ \E v \in Val : LCommit(t, v)]_vars

(* S5: the map file never points a ticket at another ticket's issue. *)
MapOwn ==
    \A t \in T : mapf.m[t] # 0 => (iss[mapf.m[t]].au = BOT /\ iss[mapf.m[t]].mk0 = t)

(* S6: comment bound: at most one per issue per day, plus duplicated deliveries. *)
CommentBound == \A i \in I, d \in Day : com[i][d] <= 1 + dupCom[i][d]

(* S7: tracker mutations per run never exceed the budget, nor 3 per ticket plus closes. *)
RunBound == m.rw <= Budget /\ m.rw <= 3 * NT + MaxIssues

(* S8: an accepted or declined edit is never reopened as a pending proposal. *)
NoReopen == \A t \in T : prop[t].st = "pending" => prop[t].hs \cap resolved = {}

(* S9: idempotence: a run that starts converged, with fresh map and no     *)
(* disturbance during the run, changes neither the tracker nor the ledger. *)
Idempotent == m.quiet => (m.rw = 0 /\ m.lw = 0)

(* Model sanity: bounds not hit. *)
HistBound == Len(hist) <= HMax
NotStuck == m.pc = "create" => nIss <= MaxIssues

(* L1: convergence: every repository-owned field eventually equals the     *)
(* ledger projection and stays so.                                         *)
Converge == <>[](\A t \in T : Synced(t))

(* L2: no loss: every tracker edit of a repository-owned field is          *)
(* eventually recorded as a proposal (collapse keeps superseded edits in   *)
(* the proposal's event set, so "superseded" is a special case).           *)
NoLoss == \A t \in T : \A p \in 1..HMax : [](Unrec(t, p) => <>(~Unrec(t, p)))

(* L3: not starved: every ticket is completed by some run infinitely often. *)
NotStarved == \A t \in T : []<>(m.pc = "fin" /\ m.ct = t)

(* L4: duplicates are eventually closed: at most one open issue per ticket. *)
DupsClosed == <>[](\A t \in T : Cardinality({i \in Owned(t) : iss[i].op}) <= 1)

=============================================================================
