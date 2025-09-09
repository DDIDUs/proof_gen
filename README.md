# proof_gen

## CorresK Proof Experiments

이 실험은 **LLM을 활용한 Proof 생성 성능 비교**를 위해 진행. (하단 Varient는 prompt.py에 정의됨)
- `baseline_output`: 수동 작성된 증명 스크립트 기반 실행 결과  
- `cot_output`: Chain-of-Thought 기반 LLM 증명 생성 결과  
- `fs_baseline_output`: **Few-Shot** 예시를 제공한 후 baseline 방식으로 수행한 결과  
- `fs_cot_output`: **Few-Shot** 예시를 제공한 후 Chain-of-Thought 기반 LLM 증명 생성 결과  

아래 표는 두 차례 로그를 합산하여 variant별 **성공 개수**를 정리한 결과.

## 데이터셋 구성
- **평가 대상 데이터(lemmas_shorts.jsonl)**:  
  - `l4v/lib/CorresK/CorresK_Lemmas.thy` 내에서 **5줄 이내의 증명을 가지는 lemma**를 추출하여 사용 (총 **11개**)  
- **Few-Shot 예제 데이터(lemmas_AInvs.jsonl)**:  
  - `l4v/proof/invariant-abstract/AInvs.thy` 내에서 **5줄 이내의 증명을 가지는 lemma**를 추출하여 few-shot 예제로 사용 (총 **8개**)  

## Variant별 성공 개수

| Variant            | Qwen2.5-32B-Coder-Instruct | Qwen2.5-7B-Coder-Instruct | GPT-oss-120b |
|--------------------|---------:|---------:|---------:|
| baseline_output    | 5        | 3        | 4        |
| cot_output         | 1        | 0        | .        |
| fs_baseline_output | 4        | 1        | 2        |
| fs_cot_output      | 3        | 1        | .        |

## 실험 방법

1. 실험을 위한 의존성을 설치합니다.
```bash
python3 -m venv proof_gen
source proof_gen/bin/activate
```

```bash
pip install -r requirements.txt
```

이후 아래 링크의 설명을 따라 l4v를 빌드합니다.
https://gist.github.com/KiJeong-Lim/b6b0eaab665a24893130a102b677cb58

2. 실험을 위한 VLLM 서버를 실행합니다. 예제에서는 Qwen2.5-Coder-7B-Instruct 모델을 활용하였습니다.
```bash
bash server.sh
```

3. gen_proof.py를 실행하여 proof를 생성합니다.
```bash
python3 gen_proof.py \
      --input ./data/lemmas_short.jsonl \
      --output ./results/gen_results/Qwen2.5_7b_proofs.jsonl \
      --model Qwen/Qwen2.5-Coder-7B-Instruct \
      --base-url http://localhost:8004/v1 \
      --temperature 0.7 \
      --top-p 0.8 \
      --shots 4 \
      --samples 1
```

4. 이후 다음의 예시와 같이 생성된 proof에 대한 평가를 진행합니다.
```bash
export PATH="$PWD/verification/l4v/isabelle/bin:$PATH"

python3 eval.py \
      --jsonl ./results/gen_result/Qwen2.5_7b_proof.jsonl \
      --thy ./verifiaction/l4v/lib/CorresK/CorresK_Lemmas.thy \
      --session CorresK \
      --root l4v/ \
      --out ./results/eval_result/Qwen2.5_7b_CoT_build_report.jsonl
```
