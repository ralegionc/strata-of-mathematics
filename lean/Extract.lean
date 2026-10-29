import Lean
open Lean

/-!
Dump the whole dependency graph of an imported environment (by default `Mathlib`; further
module names on the command line are imported too, e.g. the `Archive` files that hold some of
Freek Wiedijk's 100 theorems).

Writes three tab-separated files to the output directory:

* `nodes.tsv`: `id name kind module flags nbinders ninst nsort`
* `edges_type.tsv`: `src dst` for every constant used in the type of `src`
* `edges_value.tsv`: `src dst` for every constant used in the value of `src`
  (definition bodies, proof terms, and the constructors of an inductive type)

Tactic scripts stored in `autoParam` annotations are dropped before collecting constants.

`kind` is one of `axiom def thm opaque quot induct ctor rec`. `flags` is a bit mask:
1 internal name, 2 instance, 4 projection, 8 auxiliary recursor or `noConfusion`,
16 matcher, 32 class, 64 structure, 128 private name.
`nbinders`, `ninst`, `nsort` count the leading `∀` binders of the type, how many of them are
instance-implicit, and how many bind a type (`Sort u`).
-/

def kindName : ConstantInfo → String
  | .axiomInfo _ => "axiom"
  | .defnInfo _ => "def"
  | .thmInfo _ => "thm"
  | .opaqueInfo _ => "opaque"
  | .quotInfo _ => "quot"
  | .inductInfo _ => "induct"
  | .ctorInfo _ => "ctor"
  | .recInfo _ => "rec"

partial def binderCounts (e : Expr) (n i s : Nat := 0) : Nat × Nat × Nat :=
  match e with
  | .forallE _ t b bi =>
    let i := if bi.isInstImplicit then i + 1 else i
    let s := if t.isSort then s + 1 else s
    binderCounts b (n + 1) i s
  | .mdata _ b => binderCounts b n i s
  | _ => (n, i, s)

/-- Replace every `autoParam T stx` by `T`: the tactic script `stx` is `Lean.Syntax` data,
not a mathematical dependency. -/
partial def stripAuto (e : Expr) : Expr :=
  e.replace fun s =>
    if s.isAppOfArity ``autoParam 2 then some (stripAuto s.appFn!.appArg!) else none

def flagsOf (env : Environment) (n : Name) : Nat :=
  (if n.isInternal then 1 else 0)
  + (if Meta.isInstanceCore env n then 2 else 0)
  + (if env.isProjectionFn n then 4 else 0)
  + (if isAuxRecursor env n || isNoConfusion env n then 8 else 0)
  + (if Meta.isMatcherCore env n then 16 else 0)
  + (if isClass env n then 32 else 0)
  + (if isStructure env n then 64 else 0)
  + (if isPrivateName n then 128 else 0)

/-- Buffered writer: flush every `limit` characters. -/
structure Buf where
  h : IO.FS.Handle
  s : String := ""

def Buf.push (b : Buf) (line : String) : IO Buf := do
  let s := b.s ++ line ++ "\n"
  if s.utf8ByteSize > 1000000 then
    b.h.putStr s
    return { b with s := "" }
  return { b with s := s }

def Buf.close (b : Buf) : IO Unit := b.h.putStr b.s *> b.h.flush

unsafe def main (args : List String) : IO UInt32 := do
  let outDir : System.FilePath := args.headD "out"
  let roots : Array Name := match args.drop 1 with
    | [] => #[`Mathlib]
    | rs => rs.toArray.map String.toName
  IO.FS.createDirAll outDir
  initSearchPath (← findSysroot)
  enableInitializersExecution
  IO.println s!"importing {roots} ..."
  let env ← importModules (roots.map ({ module := · })) {} (trustLevel := 1024) (loadExts := true)
  let mods := env.header.moduleNames
  -- stable order: sort by name
  let consts := env.constants.map₁.toArray.qsort (fun a b => a.1.lt b.1)
  IO.println s!"{consts.size} constants"
  let mut ids : Std.HashMap Name Nat := {}
  for h : k in [0:consts.size] do
    ids := ids.insert consts[k].1 k
  let mut nodes : Buf := { h := ← IO.FS.Handle.mk (outDir / "nodes.tsv") .write }
  let mut et : Buf := { h := ← IO.FS.Handle.mk (outDir / "edges_type.tsv") .write }
  let mut ev : Buf := { h := ← IO.FS.Handle.mk (outDir / "edges_value.tsv") .write }
  nodes ← nodes.push "id\tname\tkind\tmodule\tflags\tnbinders\tninst\tnsort"
  et ← et.push "src\tdst"
  ev ← ev.push "src\tdst"
  let mut nT := 0
  let mut nV := 0
  for h : k in [0:consts.size] do
    let (n, ci) := consts[k]
    let modName := match env.getModuleIdxFor? n with
      | some idx => (mods[idx.toNat]?.getD .anonymous).toString
      | none => ""
    let (nb, ni, ns) := binderCounts ci.type
    nodes ← nodes.push s!"{k}\t{n.toString (escape := false)}\t{kindName ci}\t{modName}\t{flagsOf env n}\t{nb}\t{ni}\t{ns}"
    for c in (stripAuto ci.type).getUsedConstantsAsSet do
      if let some j := ids[c]? then
        if j != k then
          et ← et.push s!"{k}\t{j}"
          nT := nT + 1
    let valConsts : NameSet := match ci.value? (allowOpaque := true) with
      | some v => (stripAuto v).getUsedConstantsAsSet
      | none => match ci with
        | .inductInfo val => .ofList val.ctors
        | _ => {}
    for c in valConsts do
      if let some j := ids[c]? then
        if j != k then
          ev ← ev.push s!"{k}\t{j}"
          nV := nV + 1
    if k % 50000 == 0 then
      IO.println s!"  {k} / {consts.size}"
  nodes.close; et.close; ev.close
  IO.println s!"done: {consts.size} nodes, {nT} type edges, {nV} value edges"
  return 0
