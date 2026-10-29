import Mathlib

/-!
# Textbook restatements

Classical theorems restated with as little machinery as each result allows: coordinates instead of
inner product spaces, `ℕ` and `%` instead of `ZMod`, an ε-δ hypothesis instead of a topology.
Each statement is proved from mathlib's own version, so it follows from the theorem mathlib
lists. Only the statements are measured; the proofs show the restatements are faithful.
-/

namespace Textbook

open Finset

/-- Pythagoras with coordinates: the angle at `C` is right when the dot product vanishes. -/
theorem pythagoras (x₁ y₁ x₂ y₂ x₃ y₃ : ℝ)
    (h : (x₁ - x₃) * (x₂ - x₃) + (y₁ - y₃) * (y₂ - y₃) = 0) :
    (x₁ - x₂) ^ 2 + (y₁ - y₂) ^ 2 =
      ((x₁ - x₃) ^ 2 + (y₁ - y₃) ^ 2) + ((x₂ - x₃) ^ 2 + (y₂ - y₃) ^ 2) := by
  linear_combination (-2 : ℝ) * h

/-- The same identity with integer coordinates. -/
theorem pythagoras_int (x₁ y₁ x₂ y₂ x₃ y₃ : ℤ)
    (h : (x₁ - x₃) * (x₂ - x₃) + (y₁ - y₃) * (y₂ - y₃) = 0) :
    (x₁ - x₂) ^ 2 + (y₁ - y₂) ^ 2 =
      ((x₁ - x₃) ^ 2 + (y₁ - y₃) ^ 2) + ((x₂ - x₃) ^ 2 + (y₂ - y₃) ^ 2) := by
  linear_combination (-2 : ℤ) * h

/-- Thales: a point on the unit circle sees the diameter from `(-1, 0)` to `(1, 0)` at a right angle. -/
theorem thales (x y : ℝ) (h : x ^ 2 + y ^ 2 = 1) : (x + 1) * (x - 1) + y * y = 0 := by
  linear_combination h

/-- Heron, with the area given by the shoelace formula: `16 S² = 4 D²` where `D = 2S`. -/
theorem heron (x₁ y₁ x₂ y₂ x₃ y₃ : ℝ) :
    4 * ((x₂ - x₁) * (y₃ - y₁) - (x₃ - x₁) * (y₂ - y₁)) ^ 2 =
      2 * ((x₂ - x₃) ^ 2 + (y₂ - y₃) ^ 2) * ((x₁ - x₃) ^ 2 + (y₁ - y₃) ^ 2)
      + 2 * ((x₁ - x₃) ^ 2 + (y₁ - y₃) ^ 2) * ((x₁ - x₂) ^ 2 + (y₁ - y₂) ^ 2)
      + 2 * ((x₁ - x₂) ^ 2 + (y₁ - y₂) ^ 2) * ((x₂ - x₃) ^ 2 + (y₂ - y₃) ^ 2)
      - ((x₂ - x₃) ^ 2 + (y₂ - y₃) ^ 2) ^ 2 - ((x₁ - x₃) ^ 2 + (y₁ - y₃) ^ 2) ^ 2
      - ((x₁ - x₂) ^ 2 + (y₁ - y₂) ^ 2) ^ 2 := by
  ring

/-- Euclid: above every number there is a prime, with "prime" spelled out. -/
theorem euclid_primes (n : ℕ) : ∃ p, n < p ∧ 2 ≤ p ∧ ∀ d, d ∣ p → d = 1 ∨ d = p := by
  obtain ⟨p, hle, hp⟩ := Nat.exists_infinite_primes (n + 1)
  exact ⟨p, by omega, hp.two_le, fun d hd => hp.eq_one_or_self_of_dvd d hd⟩

/-- No rational number squares to 2. -/
theorem sqrt_two_irrational (x : ℚ) : x ^ 2 ≠ 2 := by
  intro h
  have h' : (x : ℝ) ^ 2 = 2 := by exact_mod_cast h
  have : √2 = ((|x| : ℚ) : ℝ) := by
    rw [← h', Real.sqrt_sq_eq_abs]
    push_cast
    rfl
  exact irrational_sqrt_two.ne_rat _ this

/-- Fermat's little theorem with remainders. -/
theorem fermat_little (p a : ℕ) (hp : p.Prime) (ha : ¬ p ∣ a) : a ^ (p - 1) % p = 1 := by
  have hc : Nat.Coprime a p := Nat.Coprime.symm ((Nat.Prime.coprime_iff_not_dvd hp).mpr ha)
  have h := Nat.ModEq.pow_totient hc
  rw [Nat.totient_prime hp] at h
  unfold Nat.ModEq at h
  rw [h]
  exact Nat.mod_eq_of_lt hp.one_lt

/-- Wilson: `p` divides `(p - 1)! + 1`. -/
theorem wilson (p : ℕ) (hp : p.Prime) : p ∣ (p - 1).factorial + 1 := by
  have := Fact.mk hp
  rw [← ZMod.natCast_eq_zero_iff]
  push_cast
  rw [ZMod.wilsons_lemma]
  ring

/-- Chinese remainder theorem for two coprime moduli, with remainders. -/
theorem crt (m n a b : ℕ) (h : Nat.Coprime m n) : ∃ x, x % m = a % m ∧ x % n = b % n :=
  ⟨(Nat.chineseRemainder h a b).1, (Nat.chineseRemainder h a b).2⟩

/-- Bézout's identity for integers. -/
theorem bezout (a b : ℤ) : ∃ x y : ℤ, a * x + b * y = (Int.gcd a b : ℤ) :=
  ⟨Int.gcdA a b, Int.gcdB a b, (Int.gcd_eq_gcd_ab a b).symm⟩

/-- Fermat's two squares theorem. -/
theorem two_squares (p : ℕ) (hp : p.Prime) (h : p % 4 = 1) : ∃ a b : ℕ, a ^ 2 + b ^ 2 = p := by
  have := Fact.mk hp
  exact Nat.Prime.sq_add_sq (by omega)

/-- Sum of a finite geometric series of rationals. -/
theorem geometric_sum (r : ℚ) (hr : r ≠ 1) (n : ℕ) :
    ∑ i ∈ range n, r ^ i = (r ^ n - 1) / (r - 1) :=
  geom_sum_eq hr n

/-- Sum of an arithmetic series. -/
theorem arithmetic_sum (n : ℕ) : 2 * ∑ i ∈ range (n + 1), i = n * (n + 1) := by
  induction n with
  | zero => simp
  | succ k ih =>
    rw [sum_range_succ, mul_add, ih]
    ring

/-- Triangle inequality for real numbers. -/
theorem triangle (a b : ℝ) : |a + b| ≤ |a| + |b| :=
  abs_add_le a b

/-- Arithmetic and geometric means of two numbers, squared. -/
theorem am_gm (a b : ℝ) : a * b ≤ ((a + b) / 2) ^ 2 := by
  nlinarith [sq_nonneg (a - b)]

/-- The binomial theorem over the natural numbers. -/
theorem binomial (x y n : ℕ) :
    (x + y) ^ n = ∑ k ∈ range (n + 1), n.choose k * x ^ k * y ^ (n - k) := by
  rw [add_pow]
  apply sum_congr rfl
  intro k _
  rw [Nat.cast_id]
  ring

/-- Intermediate value theorem for a function that is continuous in the ε-δ sense. -/
theorem ivt (f : ℝ → ℝ) (a b : ℝ) (hab : a ≤ b)
    (hf : ∀ x ε, 0 < ε → ∃ δ > 0, ∀ y, |y - x| < δ → |f y - f x| < ε)
    (ha : f a ≤ 0) (hb : 0 ≤ f b) : ∃ c, a ≤ c ∧ c ≤ b ∧ f c = 0 := by
  have hc : Continuous f := Metric.continuous_iff.mpr fun x ε hε => by
    obtain ⟨δ, hδ, h⟩ := hf x ε hε
    exact ⟨δ, hδ, fun y hy => by rw [Real.dist_eq] at hy ⊢; exact h y hy⟩
  obtain ⟨c, ⟨hac, hcb⟩, hfc⟩ := intermediate_value_Icc hab hc.continuousOn ⟨ha, hb⟩
  exact ⟨c, hac, hcb, hfc⟩

/-- Fundamental theorem of algebra for polynomials with complex coefficients. -/
theorem fta (p : Polynomial ℂ) (hp : 0 < p.degree) : ∃ z : ℂ, p.eval z = 0 := by
  obtain ⟨z, hz⟩ := Complex.exists_root hp
  exact ⟨z, hz⟩

/-- Area of the unit disc as an integral. -/
theorem area_circle : ∫ x in (-1 : ℝ)..1, 2 * √(1 - x ^ 2) = Real.pi := by
  rw [intervalIntegral.integral_const_mul, integral_sqrt_one_sub_sq]
  ring

/-- Cauchy-Schwarz for finite sums. -/
theorem cauchy_schwarz (n : ℕ) (a b : Fin n → ℝ) :
    (∑ i, a i * b i) ^ 2 ≤ (∑ i, a i ^ 2) * ∑ i, b i ^ 2 :=
  Finset.sum_mul_sq_le_sq_mul_sq _ _ _

end Textbook
