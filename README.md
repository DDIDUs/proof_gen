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

| Variant            | Qwen2.5-32B-Coder-Instruct | Qwen2.5-7B-Coder-Instruct |
|--------------------|---------:|---------:|
| baseline_output    | 5        | 3        |
| cot_output         | 1        | 0        |
| fs_baseline_output | 4        | 1        |
| fs_cot_output      | 3        | 1        |

