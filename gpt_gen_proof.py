# prove_isabelle_baseline_only.py
# Baseline + Few-shot Baseline (CoT/FS-CoT 제거)

import asyncio, json, argparse
from openai import AsyncOpenAI
from prompt import BASELINE_PROMPT  # CoT 프롬프트 불필요

DEFAULT_BASE_URL = "http://129.254.177.83:11434/v1"

# ---------- few-shot ----------
def fewshot_block(path, k, title="Few-shot Isabelle Proof Examples"):
    if not path or k <= 0: 
        return ""
    exs = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= k: break
            try:
                r = json.loads(line)
                inp, out = (r.get("input","").strip(), r.get("gt","").strip())
                if inp and out: exs.append((inp, out))
            except:
                pass
    if not exs:
        return ""
    parts = [f"{title}:"]
    for i, (inp, out) in enumerate(exs, 1):
        parts.append(f"\nExample {i}:\nInput:\n{inp}\n\nOutput:\n{out}\n")
    parts.append("\n--- End of Few-shot Examples ---\n")
    return "\n".join(parts)

def inject_fs(tpl, lemma, fs):
    body = tpl.format(lemma)
    return f"{fs}\n{body}" if fs else body

# ---------- llm ----------
async def llm(client, model, prompt, temperature=0.65, top_p=0.95):
    r = await client.chat.completions.create(
        model=model,
        messages=[{"role":"user","content":prompt}],
        temperature=temperature, top_p=top_p
    )
    return r.choices[0].message.content

async def do_baseline(client, model, lemma, fs="", T=0.65):
    prompt_text = inject_fs(BASELINE_PROMPT, lemma, fs)
    return await llm(client, model, prompt_text, temperature=T)

# ---------- per-item ----------
async def process_one(client, model, item, fs_block, T):
    lemma = item.get("input","")
    out = {
        "input": lemma,
        "gt": item.get("gt"),
        "baseline_output": None,
        "fs_baseline_output": None,
    }

    async def safe(coro):
        try:
            return await coro
        except Exception as e:
            return f"[ERROR] {e}"

    # (1) baseline (no few-shot)
    b0 = asyncio.create_task(safe(do_baseline(client, model, lemma, fs="", T=T)))
    # (2) few-shot baseline
    b1 = asyncio.create_task(safe(do_baseline(client, model, lemma, fs=fs_block, T=T)))

    r_b0, r_b1 = await asyncio.gather(b0, b1)
    out["baseline_output"] = r_b0
    out["fs_baseline_output"] = r_b1
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
                    "baseline_output": f"[ERROR] invalid json: {e}",
                    "fs_baseline_output": None
                }, ensure_ascii=False) + "\n")
                continue
            try:
                res = await process_one(client, model, item, fs_block, temperature)
                fout.write(json.dumps(res, ensure_ascii=False) + "\n")
            except Exception as e:
                fout.write(json.dumps({
                    "input": item.get("input"), "gt": item.get("gt"),
                    "baseline_output": f"[ERROR] {e}",
                    "fs_baseline_output": f"[ERROR] {e}"
                }, ensure_ascii=False) + "\n")

# ---------- cli ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", default="./lemmas_short.jsonl")
    ap.add_argument("--output", "-o", default="./gptoss_120b_proofs.jsonl")
    ap.add_argument("--model", "-m", default="gpt-oss:120b")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--temperature", type=float, default=0.65)
    ap.add_argument("--fewshot-file", type=str, default="./lemmas_AInvs.jsonl")
    ap.add_argument("--shots", type=int, default=4)
    args = ap.parse_args()

    asyncio.run(run(
        inp=args.input, outp=args.output, model=args.model,
        base_url=args.base_url, temperature=args.temperature,
        fs_file=args.fewshot_file, shots=args.shots
    ))
