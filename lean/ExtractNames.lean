import Lean
open Lean

/-!
For every constant whose name starts with a prefix, print the constants used in its type and in
its value, by name. Run interpreted, so nothing is built:

  lean --run ExtractNames.lean <prefix> <module> <module> ...

Output lines: `name<TAB>type|value<TAB>used constant`. Tactic scripts in `autoParam` are dropped,
as in Extract.lean.
-/

partial def stripAuto (e : Expr) : Expr :=
  e.replace fun s =>
    if s.isAppOfArity ``autoParam 2 then some (stripAuto s.appFn!.appArg!) else none

def main (args : List String) : IO Unit := do
  let pre := (args.headD "Textbook").toName
  let mods := (args.drop 1).toArray.map String.toName
  initSearchPath (← findSysroot)
  let env ← importModules (mods.map ({ module := · })) {} (trustLevel := 1024)
  for (n, ci) in env.constants.map₁.toList do
    if pre.isPrefixOf n then
      for c in (stripAuto ci.type).getUsedConstantsAsSet do
        IO.println s!"{n.toString (escape := false)}\ttype\t{c.toString (escape := false)}"
      if let some v := ci.value? (allowOpaque := true) then
        for c in (stripAuto v).getUsedConstantsAsSet do
          IO.println s!"{n.toString (escape := false)}\tvalue\t{c.toString (escape := false)}"
