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

COT_GEN_PROMPT = '''You are given a lemma from an Isabelle/HOL theory file.  
Your task is to produce a structured reasoning trace and the final proof in the following format:

<example>
Input:
lemma list_all2_to_list_all:
  "list_all2 P xs xs = list_all (λx. P x x) xs"

```plaintext
Goal:
list_all2 P xs xs = list_all (λx. P x x) xs

Plan:
Induction on xs. Both predicates evaluate to True on the empty list, and in the Cons case they both unfold to the same recursive structure (P x x ∧ …), so induction proves equality.

Steps:
- Base case xs = []: both sides simplify to True (simp).  
- Inductive case xs = x # xs':  
  - Expanding list_all2 P (x#xs') (x#xs') gives P x x ∧ list_all2 P xs' xs'.  
  - Expanding list_all (λx. P x x) (x#xs') gives P x x ∧ list_all (λx. P x x) xs'.  
  - Apply induction hypothesis on the tail and simplify.  

Rules Used:
- List induction: induct xs  
- Definition unfolding and simplification: simp  
```

Output:
```isabelle
lemma list_all2_to_list_all:
  "list_all2 P xs xs = list_all (λx. P x x) xs"
  by (induct xs; simp)
```
</example>

Strictly follow the example steps (Goal ... Output), and make sure the Output is a valid Isabelle proof, keeping it minimal if possible.

Input:
{}

Goal:

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

Goal.  
list_all2 P xs xs = list_all (λx. P x x) xs

Plan.  
Induction on xs. Both predicates evaluate to True on the empty list, and in the Cons case they both unfold to the same recursive structure (P x x ∧ …), so induction proves equality.

Key Steps.  
- Base case xs = []: both sides simplify to True (simp).  
- Inductive case xs = x # xs':  
  - Expanding list_all2 P (x#xs') (x#xs') gives P x x ∧ list_all2 P xs' xs'.  
  - Expanding list_all (λx. P x x) (x#xs') gives P x x ∧ list_all (λx. P x x) xs'.  
  - Apply induction hypothesis on the tail and simplify.  

Rules Used.  
- List induction: induct xs  
- Definition unfolding and simplification: simp  

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

OBJ_GEN_PROMPT = '''<example>
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

Unfold the involved definitions, simplify the goal to an invariant preservation statement (that some state component remains unchanged by the operation), and solve the resulting equality or implication.

Lemma:
{}

Goal (what the lemma specifies):
'''

OBJ_PROOF_PROMPT = '''<example>
Input:
lemma pred_tcb_at_upd_apply:
  "pred_tcb_at proj P t (s\<lparr>kheap := p'\<rparr>) =
  pred_tcb_at proj P t (s\<lparr>kheap := (kheap s)(t := p' t)\<rparr>)"
  
Goal (what the lemma specifies):
- The value of pred_tcb_at … t depends **only on kheap s t**. Therefore, whether we replace the entire heap with p', or update only the entry for thread t with (kheap s)(t := p' t), the result is the same.

Useful facts for the proof (minimal):
- pred_tcb_at_def, obj_at_def (unfolding shows that only kheap s t is accessed)
- fun_upd_apply (expands function update at the point of update)

Output:
```isabelle
lemma pred_tcb_at_upd_apply:
  "pred_tcb_at proj P t (s\<lparr>kheap := p'\<rparr>) =
   pred_tcb_at proj P t (s\<lparr>kheap := (kheap s)(t := p' t)\<rparr>)"
  by (simp add: pred_tcb_at_def obj_at_def fun_upd_apply)
```
</example> 

Write a proof to verify the input lemma.

Requirements:
- Wrap output strictly within ```isabelle ... ```.
- Do not write natural language, comments, or explanations.
- Only emit Isabelle code: lemma, proof body, tactics.
- Prefer concise proofs (simp, auto, wpsimp, etc.).

Input:
{}

{}

Output:
'''