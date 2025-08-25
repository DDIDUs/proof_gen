import asyncio, json, argparse
from openai import AsyncOpenAI
from prompt import *  

DEFAULT_BASE_URL = "http://localhost:8004/v1"

def fewshot_block(path, k, title="Few-shot Isabelle Proof Examples"):
    if not path or k <= 0: return ""
    exs = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= k: break
            try:
                r = json.loads(line)
                inp, out = (r.get("input","").strip(), r.get("gt","").strip())
                if inp and out: exs.append((inp, out))
            except: pass
    if not exs: return ""
    parts = [f"{title}:"]
    for i,(inp,out) in enumerate(exs,1):
        parts.append(f"\nExample {i}:\nInput:\n{inp}\n\nOutput:\n{out}\n")
    parts.append("\n--- End of Few-shot Examples ---\n")
    return "\n".join(parts)

def inject_fs(tpl, lemma, fs):  # single-input prompt
    body = tpl.format(lemma)
    return f"{fs}\n{body}" if fs else body

def inject_fs_cot(tpl, lemma, sketch, fs):  # lemma+sketch prompt
    body = tpl.format(lemma, sketch)
    return f"{fs}\n{body}" if fs else body

async def llm(client, model, prompt, temperature=0.65, top_p=0.95):
    r = await client.chat.completions.create(
        model=model, messages=[{"role":"user","content":prompt}],
        temperature=temperature, top_p=top_p
    )
    return r.choices[0].message.content

async def do_baseline(client, model, lemma, fs="", T=0.65):
    return await llm(client, model, inject_fs(BASELINE_PROMPT, lemma, fs), temperature=T)

async def do_cot(client, model, lemma, fs="", T=0.65):
    sketch = await llm(client, model, inject_fs(COT_GEN_PROMPT, lemma, fs), temperature=T)
    proof  = await llm(client, model, inject_fs_cot(COT_PROOF_PROMPT, lemma, sketch, fs), temperature=T)
    return proof, sketch

async def process_one(client, model, item, fs_block, T):
    lemma = item.get("input","")
    out = {
        "input": lemma, "gt": item.get("gt"),
        "baseline_output": None, "cot_sketch": None, "cot_output": None,
        "fs_baseline_output": None, "fs_cot_sketch": None, "fs_cot_output": None,
    }

    async def safe(coro):
        try: return await coro
        except Exception as e: return f"[ERROR] {e}"

    b0 = asyncio.create_task(safe(do_baseline(client, model, lemma, fs="", T=T)))
    c0 = asyncio.create_task(safe(do_cot(client, model, lemma, fs="", T=T)))
    b1 = asyncio.create_task(safe(do_baseline(client, model, lemma, fs=fs_block, T=T)))
    c1 = asyncio.create_task(safe(do_cot(client, model, lemma, fs=fs_block, T=T)))

    r_b0, r_c0, r_b1, r_c1 = await asyncio.gather(b0, c0, b1, c1)

    out["baseline_output"] = r_b0
    if isinstance(r_c0, tuple): out["cot_output"], out["cot_sketch"] = r_c0
    else: out["cot_output"] = r_c0

    out["fs_baseline_output"] = r_b1
    if isinstance(r_c1, tuple): out["fs_cot_output"], out["fs_cot_sketch"] = r_c1
    else: out["fs_cot_output"] = r_c1
    return out

# ---------- runner ----------
async def run(inp, outp, model, base_url, temperature, fs_file, shots):
    client = AsyncOpenAI(api_key="EMPTY", base_url=base_url)
    fs_block = fewshot_block(fs_file, shots)

    with open(inp, "r", encoding="utf-8") as fin, open(outp, "w", encoding="utf-8") as fout:
        for line in fin:
            try:
                item = json.loads(line)
            except Exception as e:
                fout.write(json.dumps({
                    "input": None, "gt": None,
                    "baseline_output": None, "cot_sketch": None, "cot_output": f"[ERROR] invalid json: {e}",
                    "fs_baseline_output": None, "fs_cot_sketch": None, "fs_cot_output": None
                }, ensure_ascii=False) + "\n")
                continue
            try:
                res = await process_one(client, model, item, fs_block, temperature)
                fout.write(json.dumps(res, ensure_ascii=False) + "\n")
            except Exception as e:
                fout.write(json.dumps({
                    "input": item.get("input"), "gt": item.get("gt"),
                    "baseline_output": f"[ERROR] {e}", "cot_sketch": None, "cot_output": f"[ERROR] {e}",
                    "fs_baseline_output": f"[ERROR] {e}", "fs_cot_sketch": None, "fs_cot_output": f"[ERROR] {e}"
                }, ensure_ascii=False) + "\n")

# ---------- cli ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", default="./lemmas_short.jsonl")
    ap.add_argument("--output", "-o", default="./Qwen2.5_7b_proofs.jsonl")
    ap.add_argument("--model", "-m", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--fewshot-file", type=str, default='./lemmas_AInvs.jsonl')
    ap.add_argument("--shots", type=int, default=4)
    args = ap.parse_args()

    asyncio.run(run(
        inp=args.input, outp=args.output, model=args.model,
        base_url=args.base_url, temperature=args.temperature,
        fs_file=args.fewshot_file, shots=args.shots
    ))
