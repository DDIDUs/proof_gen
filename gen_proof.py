import asyncio, json, argparse, os
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
            except:
                pass
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
        temperature=temperature, top_p=top_p, extra_body={"repetition_penalty": 1.1}
    )
    return r.choices[0].message.content

async def do_baseline(client, model, lemma, fs="", T=0.65, top_p=0.95):
    return await llm(client, model, inject_fs(BASELINE_PROMPT, lemma, fs), temperature=T, top_p=top_p)

async def do_cot(client, model, lemma, fs="", T=0.65, top_p=0.95):
    return await llm(client, model, inject_fs(COT_GEN_PROMPT, lemma, fs), temperature=T, top_p=top_p)

async def process_one_sample(client, model, lemma, fs_block, T, top_p, sample_id):
    """
    한 lemma에 대한 단일 샘플을 생성.
    """
    out = {
        "input": lemma,
        "baseline_output": None,
        "cot_output": None,
        "sample_id": sample_id
    }

    async def safe(coro):
        try:
            return await coro
        except Exception as e:
            return f"[ERROR] {e}"

    b_task = asyncio.create_task(safe(do_baseline(client, model, lemma, fs=fs_block, T=T, top_p=top_p)))
    c_task = asyncio.create_task(safe(do_cot(client, model, lemma, fs=fs_block, T=T, top_p=top_p)))
    r_b, r_c = await asyncio.gather(b_task, c_task)

    out["baseline_output"] = r_b
    # do_cot가 tuple을 반환하지 않도록 유지(스케치 따로 없음)
    out["cot_output"] = r_c

    return out

async def process_one(client, model, item, fs_block, T, top_p, samples):
    """
    한 lemma에 대해 'samples' 횟수만큼 생성하여 리스트로 반환.
    """
    lemma = item.get("input","")
    gt = item.get("gt")
    results = []

    # 샘플 개수만큼 병렬 실행 가능하도록 태스크 생성
    tasks = [
        asyncio.create_task(process_one_sample(client, model, lemma, fs_block, T, top_p, sample_id=i))
        for i in range(1, samples+1)
    ]
    samples_out = await asyncio.gather(*tasks, return_exceptions=True)

    # 각 샘플 결과에 ground truth 추가(있다면) 및 예외 처리
    for i, res in enumerate(samples_out, start=1):
        if isinstance(res, Exception):
            results.append({
                "input": lemma, "gt": gt,
                "baseline_output": f"[ERROR] {res}",
                "cot_output": f"[ERROR] {res}",
                "sample_id": i
            })
        else:
            res["gt"] = gt
            results.append(res)

    return results

# ---------- runner ----------
async def run(inp, outp, model, base_url, temperature, top_p, fs_file, shots, samples):
    client = AsyncOpenAI(api_key="EMPTY", base_url=base_url)
    fs_block = fewshot_block(fs_file, shots)

    # 출력 파일 디렉토리 생성 (없으면)
    out_dir = os.path.dirname(outp)
    if out_dir:  # 빈 문자열이 아닐 때만 생성 시도
        os.makedirs(out_dir, exist_ok=True)

    with open(inp, "r", encoding="utf-8") as fin, open(outp, "w", encoding="utf-8") as fout:
        for line in fin:
            try:
                item = json.loads(line)
            except Exception as e:
                fout.write(json.dumps({
                    "input": None, "gt": None,
                    "baseline_output": None,
                    "cot_output": None,
                    "sample_id": None,
                    "error": f"[ERROR] invalid json: {e}"
                }, ensure_ascii=False) + "\n")
                continue
            try:
                all_samples = await process_one(client, model, item, fs_block, temperature, top_p, samples)
                for rec in all_samples:
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception as e:
                fout.write(json.dumps({
                    "input": item.get("input"),
                    "gt": item.get("gt"),
                    "baseline_output": f"[ERROR] {e}",
                    "cot_output": f"[ERROR] {e}",
                    "sample_id": None
                }, ensure_ascii=False) + "\n")

# ---------- cli ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", default="./data/lemmas_short.jsonl")
    ap.add_argument("--output", "-o", default="./results/gen_results/Qwen2.5_7b_CoT_proofs.jsonl")
    ap.add_argument("--model", "-m", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--top-p", type=float, default=0.8)
    ap.add_argument("--fewshot-file", type=str, default='./data/lemmas_AInvs.jsonl')
    ap.add_argument("--shots", type=int, default=4)
    ap.add_argument("--samples", "-s", type=int, default=5, help="number of generations per lemma")
    args = ap.parse_args()

    asyncio.run(run(
        inp=args.input,
        outp=args.output,
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        top_p=args.top_p,
        fs_file=args.fewshot_file,
        shots=args.shots,
        samples=args.samples
    ))
