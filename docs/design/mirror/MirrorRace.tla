----------------------------- MODULE MirrorRace -----------------------------
(***************************************************************************)
(* The mirror against an adversary with no bound on edits.                *)
(*                                                                         *)
(* Mirror.tla needs finitely many edits to keep its history finite. Here  *)
(* the history is abstracted: per issue, "fresh" says there are human     *)
(* edits after the last history read, "capt" says the current run read    *)
(* edits that it has not yet recorded as proposals. One edit chosen by    *)
(* the adversary is watched (w, wi) to state no-loss per edit. The ledger *)
(* value of the repository-owned field is the constant L. Each run has a  *)
(* call budget; the next call is refused once it is spent and the run     *)
(* ends. Calls: read state 1, read history 1, write 1 (only if the read   *)
(* value differs from L); recording proposals is a ledger commit (no      *)
(* call). The cursor is the position seen at the read (the repaired       *)
(* protocol), so an edit between the read and the write stays "fresh".    *)
(***************************************************************************)
EXTENDS Naturals

CONSTANTS
    N,           \* issues 1..N
    Budget,      \* calls per run
    Unbounded,   \* TRUE: the adversary may edit forever
    MaxEdits,    \* bound on edits when Unbounded = FALSE
    RoundRobin   \* each run starts at the issue after the last one completed

Iss == 1..N
L == 0

VARIABLES R, fresh, capt, pc, c, k, st, b, rv, rr, w, wi, ed
vars == <<R, fresh, capt, pc, c, k, st, b, rv, rr, w, wi, ed>>

Init ==
    /\ R = [i \in Iss |-> L]
    /\ fresh = [i \in Iss |-> FALSE]
    /\ capt = [i \in Iss |-> FALSE]
    /\ pc = "idle" /\ c = 1 /\ k = 0 /\ st = 1 /\ b = 0 /\ rv = L /\ rr = 1
    /\ w = "none" /\ wi = 1 /\ ed = 0

-----------------------------------------------------------------------------
(* Mirror. Runs are always possible (scheduled runs, repaired protocol). *)

Start ==
    /\ pc = "idle"
    /\ b' = Budget
    /\ st' = IF RoundRobin THEN rr ELSE 1
    /\ c' = IF RoundRobin THEN rr ELSE 1
    /\ k' = 0
    /\ pc' = "rs"
    /\ UNCHANGED <<R, fresh, capt, rv, rr, w, wi, ed>>

Refuse ==        \* budget spent: the call is refused and the run ends
    /\ pc \in {"rs", "rh", "wr"} /\ b = 0
    /\ pc' = "idle"
    /\ capt' = [capt EXCEPT ![c] = FALSE]                \* unrecorded reads are re-read next run
    /\ fresh' = [fresh EXCEPT ![c] = @ \/ capt[c]]
    /\ w' = IF w = "capt" /\ wi = c THEN "fresh" ELSE w
    /\ UNCHANGED <<R, c, k, st, b, rv, rr, wi, ed>>

ReadState ==
    /\ pc = "rs" /\ b > 0
    /\ rv' = R[c] /\ b' = b - 1 /\ pc' = "rh"
    /\ UNCHANGED <<R, fresh, capt, c, k, st, rr, w, wi, ed>>

ReadHist ==
    /\ pc = "rh" /\ b > 0
    /\ capt' = [capt EXCEPT ![c] = @ \/ fresh[c]]
    /\ fresh' = [fresh EXCEPT ![c] = FALSE]
    /\ w' = IF w = "fresh" /\ wi = c THEN "capt" ELSE w
    /\ b' = b - 1 /\ pc' = "rec"
    /\ UNCHANGED <<R, c, k, st, rv, rr, wi, ed>>

Record ==        \* ledger commit of the proposals (and the cursor)
    /\ pc = "rec"
    /\ capt' = [capt EXCEPT ![c] = FALSE]
    /\ w' = IF w = "capt" /\ wi = c THEN "done" ELSE w
    /\ pc' = IF rv # L THEN "wr" ELSE "fin"
    /\ UNCHANGED <<R, fresh, c, k, st, b, rv, rr, wi, ed>>

Write ==         \* revert to the ledger value; overwrites an edit made since the read
    /\ pc = "wr" /\ b > 0
    /\ R' = [R EXCEPT ![c] = L]
    /\ b' = b - 1 /\ pc' = "fin"
    /\ UNCHANGED <<fresh, capt, c, k, st, rv, rr, w, wi, ed>>

Fin ==
    /\ pc = "fin"
    /\ rr' = (c % N) + 1
    /\ k' = k + 1
    /\ IF k + 1 = N
       THEN pc' = "idle" /\ UNCHANGED c
       ELSE pc' = "rs" /\ c' = ((st - 1 + k + 1) % N) + 1
    /\ UNCHANGED <<R, fresh, capt, st, b, rv, w, wi, ed>>

Mirror == Start \/ Refuse \/ ReadState \/ ReadHist \/ Record \/ Write \/ Fin

-----------------------------------------------------------------------------
(* Adversary: edits any issue at any time, possibly forever. *)

Edit(i) ==
    /\ Unbounded \/ ed < MaxEdits
    /\ R' = [R EXCEPT ![i] = 1 - @]
    /\ fresh' = [fresh EXCEPT ![i] = TRUE]
    /\ ed' = IF Unbounded THEN ed ELSE ed + 1
    /\ \/ UNCHANGED <<w, wi>>
       \/ w = "none" /\ w' = "fresh" /\ wi' = i      \* watch this edit
    /\ UNCHANGED <<capt, pc, c, k, st, b, rv, rr>>

Next == Mirror \/ \E i \in Iss : Edit(i)
Spec == Init /\ [][Next]_vars /\ WF_vars(Mirror)

-----------------------------------------------------------------------------
TypeOK == R \in [Iss -> {0, 1}] /\ b \in 0..Budget /\ k \in 0..N

(* Safety: the mirror only ever writes the ledger value. *)
WritesOnlyLedger == [][Mirror => \A i \in Iss : R'[i] # R[i] => R'[i] = L]_vars

(* Convergence: eventually always equal (expected to fail when Unbounded). *)
Converge == <>[](\A i \in Iss : R[i] = L)
(* Weaker: every issue equals the ledger infinitely often. *)
InfOften == \A i \in Iss : []<>(R[i] = L)
(* No loss: the watched edit is eventually recorded as a proposal. *)
NoLoss == [](w = "fresh" => <>(w = "done"))
(* Not starved: every issue is completed by some run infinitely often. *)
NotStarved == \A i \in Iss : []<>(pc = "fin" /\ c = i)

=============================================================================
