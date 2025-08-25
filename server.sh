vllm serve Qwen/Qwen2.5-Coder-7B-Instruct \
                                --max-model-len 32768 \
                                --gpu-memory-utilization 0.95 \
                                --trust-remote-code \
                                --port 8004 \