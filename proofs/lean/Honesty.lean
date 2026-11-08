/-
Lean 4 model of the honesty theorem.

A fact store is a structure with a `lo` relation (facts known to hold, "Must") and a `hi` relation
(facts that might hold, "Must + May"), with `lo <= hi`. A concretisation is any classical relation
squeezed between them. Formulas are evaluated in Kleene's strong three-valued logic K3
(`none` = Unknown, `some true` = Yes, `some false` = No). Negation may apply to any formula, and
the only recursive construct is the positive transitive closure of a base relation, so negation
never sits inside a recursion: this is the stratified fragment (base relations, then positive
closure, then negation and boolean structure above them).

Main results, no `sorry`, core Lean only (no Mathlib):
  * `eval_sound`: a definite K3 answer equals the classical answer in EVERY concretisation.
  * `eval_exact`: on a closed structure (lo = hi) the answer is never Unknown.

Check with:  lean proofs/lean/Honesty.lean  (ticket 01M4CXV5B9VGBKA67GJT0WRFJ0)
-/
open Classical

namespace Honesty

/-- Kleene three-valued truth value: `none` is Unknown. -/
abbrev K3 := Option Bool

/-- K3 negation; Unknown stays Unknown. -/
def K3.not : K3 → K3
  | some b => some (!b)
  | none => none

/-- K3 conjunction; a definite No wins, Yes is the identity. -/
def K3.and : K3 → K3 → K3
  | some false, _ => some false
  | _, some false => some false
  | some true, y => y
  | x, some true => x
  | none, none => none

/-- K3 disjunction; a definite Yes wins, No is the identity. -/
def K3.or : K3 → K3 → K3
  | some true, _ => some true
  | _, some true => some true
  | some false, y => y
  | x, some false => x
  | none, none => none

/-- A family of binary relations indexed by a relation id. -/
abbrev Rel := Nat → Nat → Nat → Prop

/-- A fact store: `lo` facts are certain, `hi` facts are possible, and `lo <= hi`. -/
structure Struct where
  lo : Rel
  hi : Rel
  le : ∀ r x y, lo r x y → hi r x y

/-- `C` is a concretisation of `S`: it contains every `lo` fact and only `hi` facts. -/
def Struct.Conc (S : Struct) (C : Rel) : Prop :=
  ∀ r x y, (S.lo r x y → C r x y) ∧ (C r x y → S.hi r x y)

/-- Positive transitive closure of relation `r` inside `R`. -/
inductive Reach (R : Rel) (r : Nat) : Nat → Nat → Prop
  | base : R r x y → Reach R r x y
  | step : Reach R r x y → R r y z → Reach R r x z

/-- Reachability is monotone in the underlying relation. -/
theorem Reach.mono {R R' : Rel} (h : ∀ r x y, R r x y → R' r x y) {r x y : Nat}
    (p : Reach R r x y) : Reach R' r x y := by
  induction p with
  | base a => exact .base (h _ _ _ a)
  | step _ a ih => exact .step ih (h _ _ _ a)

/-- Formulas: ground atoms, positive closure, boolean connectives, bounded quantifiers (HOAS). -/
inductive Formula
  | atom (r x y : Nat)
  | reach (r x y : Nat)
  | not (f : Formula)
  | and (f g : Formula)
  | or (f g : Formula)
  | ex (n : Nat) (f : Nat → Formula)
  | all (n : Nat) (f : Nat → Formula)

/-- Classical meaning of a formula in a concrete relation family. -/
def holds (C : Rel) : Formula → Prop
  | .atom r x y => C r x y
  | .reach r x y => Reach C r x y
  | .not f => ¬ holds C f
  | .and f g => holds C f ∧ holds C g
  | .or f g => holds C f ∨ holds C g
  | .ex n f => ∃ i, i < n ∧ holds C (f i)
  | .all n f => ∀ i, i < n → holds C (f i)

/-- K3 disjunction of `g 0 .. g (n-1)`. -/
def orN : Nat → (Nat → K3) → K3
  | 0, _ => some false
  | n + 1, g => K3.or (orN n g) (g n)

/-- K3 conjunction of `g 0 .. g (n-1)`. -/
def andN : Nat → (Nat → K3) → K3
  | 0, _ => some true
  | n + 1, g => K3.and (andN n g) (g n)

/-- Three-valued evaluation: Yes from `lo`, No from absence in `hi`, otherwise Unknown. -/
noncomputable def eval (S : Struct) : Formula → K3
  | .atom r x y => if S.lo r x y then some true else if ¬ S.hi r x y then some false else none
  | .reach r x y =>
      if Reach S.lo r x y then some true else if ¬ Reach S.hi r x y then some false else none
  | .not f => K3.not (eval S f)
  | .and f g => K3.and (eval S f) (eval S g)
  | .or f g => K3.or (eval S f) (eval S g)
  | .ex n f => orN n (fun i => eval S (f i))
  | .all n f => andN n (fun i => eval S (f i))

/-- `Sound p x`: any definite value of `x` agrees with the proposition `p`. -/
def Sound (p : Prop) (x : K3) : Prop := ∀ b, x = some b → (p ↔ b = true)

theorem Sound.not {p : Prop} {x : K3} (h : Sound p x) : Sound (¬ p) x.not := by
  intro b hb
  cases x with
  | none => simp [K3.not] at hb
  | some a =>
    have := h a rfl
    cases a <;> simp_all [K3.not]

theorem Sound.and {p q : Prop} {x y : K3} (hx : Sound p x) (hy : Sound q y) :
    Sound (p ∧ q) (K3.and x y) := by
  intro b hb
  cases x with
  | none =>
    cases y with
    | none => simp [K3.and] at hb
    | some c =>
      have := hy c rfl
      cases c <;> simp_all [K3.and]
  | some a =>
    have := hx a rfl
    cases a with
    | false => simp_all [K3.and]
    | true =>
      cases y with
      | none => simp_all [K3.and]
      | some c =>
        have := hy c rfl
        cases c <;> simp_all [K3.and]

theorem Sound.or {p q : Prop} {x y : K3} (hx : Sound p x) (hy : Sound q y) :
    Sound (p ∨ q) (K3.or x y) := by
  intro b hb
  cases x with
  | none =>
    cases y with
    | none => simp [K3.or] at hb
    | some c =>
      have := hy c rfl
      cases c <;> simp_all [K3.or]
  | some a =>
    have := hx a rfl
    cases a with
    | true => simp_all [K3.or]
    | false =>
      cases y with
      | none => simp_all [K3.or]
      | some c =>
        have := hy c rfl
        cases c <;> simp_all [K3.or]

theorem Sound.orN {n : Nat} {P : Nat → Prop} {g : Nat → K3}
    (h : ∀ i, i < n → Sound (P i) (g i)) : Sound (∃ i, i < n ∧ P i) (orN n g) := by
  induction n with
  | zero =>
    intro b hb
    have : b = false := by
      have h0 : (some false : K3) = some b := hb
      exact (Option.some.inj h0).symm
    subst this
    exact ⟨fun ⟨i, hi, _⟩ => absurd hi (Nat.not_lt_zero _), fun h => by cases h⟩
  | succ n ih =>
    have h1 := ih (fun i hi => h i (Nat.lt_succ_of_lt hi))
    have h2 := Sound.or h1 (h n (Nat.lt_succ_self n))
    intro b hb
    refine Iff.trans ⟨?_, ?_⟩ (h2 b hb)
    · rintro ⟨i, hi, hp⟩
      rcases Nat.lt_succ_iff_lt_or_eq.mp hi with hi | hi
      · exact .inl ⟨i, hi, hp⟩
      · subst hi; exact .inr hp
    · rintro (⟨i, hi, hp⟩ | hp)
      · exact ⟨i, Nat.lt_succ_of_lt hi, hp⟩
      · exact ⟨n, Nat.lt_succ_self n, hp⟩

theorem Sound.andN {n : Nat} {P : Nat → Prop} {g : Nat → K3}
    (h : ∀ i, i < n → Sound (P i) (g i)) : Sound (∀ i, i < n → P i) (andN n g) := by
  induction n with
  | zero =>
    intro b hb
    have : b = true := by
      have h0 : (some true : K3) = some b := hb
      exact (Option.some.inj h0).symm
    subst this
    exact ⟨fun _ => rfl, fun _ i hi => absurd hi (Nat.not_lt_zero _)⟩
  | succ n ih =>
    have h1 := ih (fun i hi => h i (Nat.lt_succ_of_lt hi))
    have h2 := Sound.and h1 (h n (Nat.lt_succ_self n))
    intro b hb
    refine Iff.trans ⟨?_, ?_⟩ (h2 b hb)
    · intro hall
      exact ⟨fun i hi => hall i (Nat.lt_succ_of_lt hi), hall n (Nat.lt_succ_self n)⟩
    · rintro ⟨ha, hn⟩ i hi
      rcases Nat.lt_succ_iff_lt_or_eq.mp hi with hi | hi
      · exact ha i hi
      · subst hi; exact hn

/-- Honesty theorem: a definite K3 answer is the classical answer in every concretisation. -/
theorem eval_sound (S : Struct) (C : Rel) (hC : S.Conc C) (φ : Formula) :
    ∀ b, eval S φ = some b → (holds C φ ↔ b = true) := by
  have key : Sound (holds C φ) (eval S φ) := by
    induction φ with
    | atom r x y =>
      intro b hb
      simp only [eval, holds] at hb ⊢
      by_cases h1 : S.lo r x y
      · simp [h1] at hb; subst hb; simpa using (hC r x y).1 h1
      · by_cases h2 : S.hi r x y
        · simp [h1, h2] at hb
        · simp [h1, h2] at hb; subst hb; simpa using fun c => h2 ((hC r x y).2 c)
    | reach r x y =>
      intro b hb
      simp only [eval, holds] at hb ⊢
      by_cases h1 : Reach S.lo r x y
      · simp [h1] at hb; subst hb
        simpa using Reach.mono (fun r x y a => (hC r x y).1 a) h1
      · by_cases h2 : Reach S.hi r x y
        · simp [h1, h2] at hb
        · simp [h1, h2] at hb; subst hb
          simpa using fun c => h2 (Reach.mono (fun r x y a => (hC r x y).2 a) c)
    | not f ih => exact Sound.not ih
    | and f g ihf ihg => exact Sound.and ihf ihg
    | or f g ihf ihg => exact Sound.or ihf ihg
    | ex n f ih => exact Sound.orN (fun i _ => ih i)
    | all n f ih => exact Sound.andN (fun i _ => ih i)
  exact key

theorem K3.not_ne {x : K3} (h : x ≠ none) : x.not ≠ none := by
  cases x <;> simp_all [K3.not]

theorem K3.and_ne {x y : K3} (hx : x ≠ none) (hy : y ≠ none) : K3.and x y ≠ none := by
  rcases x with _ | _ | _ <;> rcases y with _ | _ | _ <;> simp_all [K3.and]

theorem K3.or_ne {x y : K3} (hx : x ≠ none) (hy : y ≠ none) : K3.or x y ≠ none := by
  rcases x with _ | _ | _ <;> rcases y with _ | _ | _ <;> simp_all [K3.or]

theorem orN_ne {n : Nat} {g : Nat → K3} (h : ∀ i, g i ≠ none) : orN n g ≠ none := by
  induction n with
  | zero => simp [orN]
  | succ n ih => exact K3.or_ne ih (h n)

theorem andN_ne {n : Nat} {g : Nat → K3} (h : ∀ i, g i ≠ none) : andN n g ≠ none := by
  induction n with
  | zero => simp [andN]
  | succ n ih => exact K3.and_ne ih (h n)

/-- Exactness: when `lo = hi` (no uncertainty) the evaluator never answers Unknown. -/
theorem eval_exact (S : Struct) (hS : S.lo = S.hi) (φ : Formula) : eval S φ ≠ none := by
  induction φ with
  | atom r x y =>
    simp only [eval]
    by_cases h1 : S.lo r x y
    · simp [h1]
    · have : ¬ S.hi r x y := hS ▸ h1
      simp [h1, this]
  | reach r x y =>
    simp only [eval]
    by_cases h1 : Reach S.lo r x y
    · simp [h1]
    · have : ¬ Reach S.hi r x y := hS ▸ h1
      simp [h1, this]
  | not f ih => exact K3.not_ne ih
  | and f g ihf ihg => exact K3.and_ne ihf ihg
  | or f g ihf ihg => exact K3.or_ne ihf ihg
  | ex n f ih => exact orN_ne ih
  | all n f ih => exact andN_ne ih

end Honesty
