# Predictions for the second round of follow-ups

Written 2026-10-16 16:41 UTC, before any of the data below was collected or looked at. Each prediction
says what would count as confirmed and what would count as failed. Results are reported against these
lines in the README whichever way they come out.

## 1. Research proofs (rewording rule)

The first round found the three finished research proofs deeper (234 to 262 levels) than any proof in
the sample (at most 231), and the README suggested the burden of knowledge "may live in proofs".
A quick check then found no trend with year in how far proofs go beyond their statements inside the
sample (rho -0.04), with the deepest sample proofs from 1837 and 1846.

Test: split each research proof's longest chain into layers inside the project's own files and layers
in mathlib, and do the same for every sample theorem, counting its "own development" as the folder its
file sits in.

Rule: if the research proofs are no deeper than the sample once their own-development layers are
compared like for like, the README drops the claim. If they are still deeper, it keeps the claim with
that caveat.

## 2. Depth and the syllabus

mathlib's `docs/undergrad.yaml` lists the undergraduate curriculum; `docs/overview.yaml` lists a wider
survey that adds graduate topics.

- P2a. Items in the undergraduate list are shallower than items found only in the overview.
  Confirmed if the median depth is lower and a one-sided Mann-Whitney test gives p < 0.05.
- P2b. The same holds within each stratum (statements through the reals, and not).

My prior is weak: graduate abstractions such as categories are shallow in mathlib, so P2a may fail.

## 3. Concepts built on the reals, on fresh data

The first round found that among 60 concepts whose definition passes through the reals, newer ones sit
deeper (rho +0.35, CI 0.09 to 0.57), a pattern noticed after the main test failed.

- P3. Among concepts from the same two mathlib lists that were not in the first 183, and whose
  definition passes through the reals, depth rises with the year the concept appeared.
  Confirmed if Spearman rho > 0 with the 95% bootstrap interval above 0.
- Dates for the fresh concepts come primarily from Wikipedia (the automatic method of test 6, blind to
  depth). Hand dates are a secondary check: they are not blind, because the depths of these concepts
  were printed during the first round.
- Expected alongside: across all fresh concepts, no positive trend.

## 4. Library time

Each theorem and concept gets the date it first entered mathlib (mathlib3 from 2017, mathlib4 after the
port), from git history.

- P4a (known answer). No statement that passes through the reals entered the library before the reals.
- P4b. In library time, statement depth rises with the date of entry: rho > 0, 95% interval above 0.
- P4c. That rise is stronger than the (absent) rise in historical time: rho(library) - rho(history) > 0
  with a bootstrap interval above 0.

## 5. A third library: HOL Light

HOL Light builds the natural numbers from an axiom of infinity, then the reals directly from natural
numbers ("nearly additive" functions), skipping the rationals, then defines the integers as a subset of
the reals.

- P5a (structural). In HOL Light the reals sit above the naturals with no rational layer between, and
  the integers sit above the reals.
- P5b. No time trend among Wiedijk's 100 theorems in HOL Light: the 95% interval for rho includes 0.
- P5c. Passing through the reals explains more of the variation in depth than the year does.
- P5d. For theorems in both, HOL Light depth correlates positively with mathlib depth.
