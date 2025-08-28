BASELINE_PROMPT = '''You are an Isabelle/seL4 proof assistant.
Your task is to take as input:
1. An Isabelle lemma statement or specification

You must output only a complete Isabelle proof in the correct style.

Requirements:
- Wrap output strictly within ```isabelle ... ```.
- Do not write natural language, comments, or explanations.
- Only emit Isabelle code: lemma, proof body, tactics.
- Prefer concise seL4 style proofs (simp, auto, wpsimp, etc.).

Input: Isabelle lemma statement or specification.
Output: Isabelle proof script that discharges it.

<example>
Input:
lemma akernel_invs:
  "\<lbrace>invs and (\<lambda>s. e \<noteq> Interrupt \<longrightarrow> ct_running s)\<rbrace>
   (call_kernel e) :: (unit,unit) s_monad
   \<lbrace>\<lambda>rv. invs and (\<lambda>s. ct_running s \<or> ct_idle s)\<rbrace>"

Output:
```isabelle
lemma akernel_invs:
  "\<lbrace>invs and (\<lambda>s. e \<noteq> Interrupt \<longrightarrow> ct_running s)\<rbrace>
   (call_kernel e) :: (unit,unit) s_monad
   \<lbrace>\<lambda>rv. invs and (\<lambda>s. ct_running s \<or> ct_idle s)\<rbrace>"
  unfolding call_kernel_def
  by (wpsimp wp: activate_invs simp: active_from_running)
```
</example> 

Input:
{}

Output:
'''

COT_GEN_PROMPT = '''You are an Isabelle/seL4 proof assistant.

Your task:
Given as input an Isabelle lemma statement or specification,
output only a reasoning chain (chain of thought) that describes
the proof plan — not the formal proof itself.

Requirements:
- Output must be a plain structured reasoning chain in natural language
  (bullet points or numbered steps).
- Do NOT output Isabelle code, proof scripts, or tactic invocations inside code blocks.
- The reasoning chain should explain the strategy (e.g., induction, cases),
  base and step cases, and the key tactics or simplifications that would be used.
- Keep it concise and aligned with common seL4 proof practices.

<example>
Input:
lemma list_all2_to_list_all:
  "list_all2 P xs xs = list_all (λx. P x x) xs"

Output (chain of thought):
- The lemma relates list_all2 on identical lists with list_all.
- Proof strategy: induction on xs.
- Base case xs = []: both sides simplify to True.
- Inductive case xs = y#ys: expand list_all2 and list_all,
  show equivalence by IH.
- Tactics: (induct xs; simp).
</example>

Input:
{}

Output (chain of thought):
'''

COT_PROOF_PROMPT = '''You are an Isabelle/seL4 proof assistant.
Your task is to take as input:
1. An Isabelle lemma statement or specification, and
2. A reasoning chain (chain of thought) describing the proof plan.

You must output only a complete Isabelle proof in the correct style.

Requirements:
- Wrap output strictly within ```isabelle ... ```.
- Do not include the chain of thought or natural language.
- Only emit Isabelle code: lemma, proof body, tactics.
- Follow the proof plan from the reasoning chain.
- Prefer concise seL4 style proofs (simp, auto, wpsimp, etc.).

<example>
Input:
Lemma:
lemma list_all2_to_list_all:
  "list_all2 P xs xs = list_all (λx. P x x) xs"

Chain of Thought:
- Prove by induction on xs.
- Base: simp handles.
- Step: expand definitions, apply IH, simp.

Output:
```isabelle
lemma list_all2_to_list_all:
  "list_all2 P xs xs = list_all (λx. P x x) xs"
  by (induct xs; simp)
```
</example>

Input:
{}

Chain of Thought:
{}

Output:
'''

OBJ_GEN_PROMPT = '''You are an Isabelle/HOL proof assistant tutor.

Task: 
Show me the subgoals generated when proving the following lemma by induction (if induction is indeed appropriate).

Requirements:
- Apply induction only if the lemma involves an explicitly recursive datatype (lists, natural numbers, etc.).
- If induction is not appropriate, just unfold definitions and simplify.
- Never invent or guess definitions. If a constant is unknown, keep it opaque (e.g., just write `corres_underlyingK ...`).
- Show the exact subgoals as Isabelle would print them after `induction` or `simp`.
- For inductive proofs, separate into "Base case" and "Inductive step", and include the induction hypothesis explicitly.
- Do not provide a finished proof script; only show the subgoals and explain briefly in natural language how LHS and RHS reduce.

Output Format:
1. Print each subgoal in Isabelle style (code block).
2. Under each subgoal, give a short natural-language explanation of how it simplifies.

<example>
Lemma:
lemma user_memory_update[wp]:
  "⟨λs. P (device_region s)⟩ do_machine_op (user_memory_update a)
   ⟨λrv s. P (device_region s)⟩"

After unfolding `do_machine_op_def` and `user_memory_update_def`,
the goal simplifies to:

  P (device_region s) ⟹ P (device_region s')

where `s'` is the updated state.

Because `device_region` is unchanged by `user_memory_update`,
the subgoal reduces to:

  device_region s' = device_region s

So the goal is immediate by simp.
</example>

Lemma:
{}
'''

OBJ_PROOF_PROMPT = '''You are an Isabelle/seL4 proof assistant.
Your task is to take as input:
1. An Isabelle lemma statement or specification

You must output only a complete Isabelle proof in the correct style.

Requirements:
- Wrap output strictly within ```isabelle ... ```.
- Do not write natural language, comments, or explanations.
- Only emit Isabelle code: lemma, proof body, tactics.
- Prefer concise seL4 style proofs (simp, auto, wpsimp, etc.).

Input: Isabelle lemma statement or specification.
Output: Isabelle proof script that discharges it.

<example>
Input:
lemma akernel_invs:
  "\<lbrace>invs and (\<lambda>s. e \<noteq> Interrupt \<longrightarrow> ct_running s)\<rbrace>
   (call_kernel e) :: (unit,unit) s_monad
   \<lbrace>\<lambda>rv. invs and (\<lambda>s. ct_running s \<or> ct_idle s)\<rbrace>"

Output:
```isabelle
lemma akernel_invs:
  "\<lbrace>invs and (\<lambda>s. e \<noteq> Interrupt \<longrightarrow> ct_running s)\<rbrace>
   (call_kernel e) :: (unit,unit) s_monad
   \<lbrace>\<lambda>rv. invs and (\<lambda>s. ct_running s \<or> ct_idle s)\<rbrace>"
  unfolding call_kernel_def
  by (wpsimp wp: activate_invs simp: active_from_running)
```
</example> 

Input:
{}

Objectives:
{}

Output:
'''