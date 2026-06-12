#!/usr/bin/env python3
# ==============================================================================
# Script Name: benchmark_llm.py
# Description: Benchmarks local LLM performance running on Arm64 CPU.
#              Tracks TTFT, tokens/sec, and peak RAM (System & Ollama Process).
#              Outputs a clean, ready-to-copy Markdown table.
# ==============================================================================

import sys
import time
import json
import threading
import requests
import psutil

OLLAMA_HOST = "http://localhost:11434"

class RAMTracker:
    """Tracks peak RAM usage during an execution block."""
    def __init__(self):
        self.peak_sys_used = 0
        self.peak_proc_used = 0
        self.running = False
        self._thread = None
        self._target_pids = []

    def _find_ollama_pids(self):
        pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'ollama' in proc.info['name'].lower():
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return pids

    def _monitor(self):
        pids = self._find_ollama_pids()
        processes = []
        for pid in pids:
            try:
                processes.append(psutil.Process(pid))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        while self.running:
            # 1. System RAM tracking
            sys_mem = psutil.virtual_memory()
            if sys_mem.used > self.peak_sys_used:
                self.peak_sys_used = sys_mem.used

            # 2. Process RAM tracking (including children)
            proc_mem_total = 0
            for proc in list(processes):
                try:
                    # Include current process RSS
                    proc_mem_total += proc.memory_info().rss
                    # Include child processes RSS
                    for child in proc.children(recursive=True):
                        proc_mem_total += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process died or lost permission, remove it
                    if proc in processes:
                        processes.remove(proc)
            
            if proc_mem_total > self.peak_proc_used:
                self.peak_proc_used = proc_mem_total
            
            time.sleep(0.05) # Sample every 50ms

    def start(self):
        self.running = True
        self.peak_sys_used = psutil.virtual_memory().used
        self.peak_proc_used = 0
        self._thread = threading.Thread(target=self._monitor)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join()

def get_first_installed_model():
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                return models[0]["name"]
    except requests.exceptions.ConnectionError:
        print("Error: Ollama server is not running on localhost:11434.")
        sys.exit(1)
    return None

def run_benchmark_trial(model_name, prompt):
    print(f"\nRunning Trial: '{prompt[:40]}...'")
    
    tracker = RAMTracker()
    tracker.start()

    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": True
    }

    start_time = time.time()
    first_token_time = None
    char_count = 0
    token_estimate_count = 0
    full_response = ""

    # Ollama returns specific statistics at the very end
    ollama_eval_count = 0
    ollama_eval_duration_ns = 0

    try:
        # We start streaming the response
        response = requests.post(url, json=payload, stream=True, timeout=180)
        
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                
                # Record time to first token
                if first_token_time is None and chunk.get("response"):
                    first_token_time = time.time()
                
                text = chunk.get("response", "")
                full_response += text
                char_count += len(text)
                
                # If done, record Ollama stats
                if chunk.get("done", False):
                    ollama_eval_count = chunk.get("eval_count", 0)
                    ollama_eval_duration_ns = chunk.get("eval_duration", 0)

        end_time = time.time()
        tracker.stop()

        # Estimates & Metrics Calculations
        # 1 token is roughly 4 characters in English
        token_estimate_count = max(1, round(char_count / 4))
        
        # If Ollama didn't return eval_count, fallback to estimate
        actual_tokens = ollama_eval_count if ollama_eval_count > 0 else token_estimate_count
        
        # Latency (TTFT)
        ttft = (first_token_time - start_time) if first_token_time else (end_time - start_time)
        
        # Generation duration
        gen_duration = end_time - (first_token_time if first_token_time else start_time)
        gen_duration = max(0.001, gen_duration)
        
        # Speed Calculations
        client_tps = actual_tokens / gen_duration
        if ollama_eval_duration_ns > 0:
            ollama_tps = actual_tokens / (ollama_eval_duration_ns / 1e9)
        else:
            ollama_tps = client_tps

        # RAM formatting (Bytes to GB)
        peak_sys_ram_gb = tracker.peak_sys_used / (1024 ** 3)
        peak_proc_ram_gb = tracker.peak_proc_used / (1024 ** 3)

        return {
            "prompt_length": len(prompt),
            "tokens_generated": actual_tokens,
            "ttft": ttft,
            "client_tps": client_tps,
            "ollama_tps": ollama_tps,
            "peak_sys_ram": peak_sys_ram_gb,
            "peak_proc_ram": peak_proc_ram_gb,
            "success": True
        }

    except Exception as e:
        tracker.stop()
        print(f"Trial failed: {e}")
        return {"success": False}

def main():
    model_name = get_first_installed_model()
    if not model_name:
        print("Error: No models found. Run 'ollama pull phi3:mini' first.")
        sys.exit(1)

    # Detect physical memory
    sys_mem = psutil.virtual_memory()
    total_sys_ram_gb = sys_mem.total / (1024 ** 3)

    print("=" * 60)
    print(" Arm64 CPU LLM Inference Benchmark Suite")
    print(f" Target Model: {model_name}")
    print(f" System Memory: {total_sys_ram_gb:.2f} GB")
    print("=" * 60)

    # 3 prompt sizes for thorough evaluation
    prompts = [
        "Explain recursion in one sentence.",
        "Write a Python function to check if a number is prime, with docstrings.",
        "Write a paragraph explaining why running AI models locally on ARM-based edge devices is better for privacy and latency."
    ]

    results = []
    for idx, prompt in enumerate(prompts):
        res = run_benchmark_trial(model_name, prompt)
        if res["success"]:
            results.append(res)
            print(f" -> TTFT: {res['ttft']:.3f}s | TPS: {res['ollama_tps']:.2f} | Max Proc RAM: {res['peak_proc_ram']:.2f} GB")
        else:
            print(f" -> Trial {idx+1} failed.")

    if not results:
        print("Error: All trials failed. Cannot generate report.")
        sys.exit(1)

    # Calculate averages
    num_trials = len(results)
    avg_ttft = sum(r["ttft"] for r in results) / num_trials
    avg_tps = sum(r["ollama_tps"] for r in results) / num_trials
    avg_proc_ram = sum(r["peak_proc_ram"] for r in results) / num_trials
    avg_sys_ram = sum(r["peak_sys_ram"] for r in results) / num_trials
    avg_tokens = sum(r["tokens_generated"] for r in results) / num_trials

    # Print final markdown table
    print("\n" + "=" * 60)
    print(" BENCHMARK REPORT (MARKDOWN FORMAT)")
    print("=" * 60)
    print("\nCopy the block below for your hackathon submission:\n")

    markdown_report = f"""### Local LLM Inference Performance on Arm64 CPU

- **Model Used**: `{model_name}` (4-bit Quantized GGUF)
- **Host Architecture**: `Arm64 / aarch64`
- **Total System RAM**: `{total_sys_ram_gb:.2f} GB`

| Metric | Trial 1 (Short Prompt) | Trial 2 (Medium Prompt) | Trial 3 (Long Prompt) | Average |
| :--- | :---: | :---: | :---: | :---: |
| **Prompt Char Length** | {results[0]['prompt_length']} | {results[1]['prompt_length'] if num_trials > 1 else 'N/A'} | {results[2]['prompt_length'] if num_trials > 2 else 'N/A'} | {sum(r['prompt_length'] for r in results)//num_trials} |
| **Tokens Generated** | {results[0]['tokens_generated']} | {results[1]['tokens_generated'] if num_trials > 1 else 'N/A'} | {results[2]['tokens_generated'] if num_trials > 2 else 'N/A'} | {int(avg_tokens)} |
| **Time to First Token (TTFT)** | `{results[0]['ttft']:.3f} s` | `{results[1]['ttft']:.3f} s` if num_trials > 1 else 'N/A' | `{results[2]['ttft']:.3f} s` if num_trials > 2 else 'N/A' | `{avg_ttft:.3f} s` |
| **Tokens / Second (Ollama Engine)** | `{results[0]['ollama_tps']:.2f} t/s` | `{results[1]['ollama_tps']:.2f} t/s` if num_trials > 1 else 'N/A' | `{results[2]['ollama_tps']:.2f} t/s` if num_trials > 2 else 'N/A' | `{avg_tps:.2f} t/s` |
| **Peak Ollama Process RAM** | `{results[0]['peak_proc_ram']:.2f} GB` | `{results[1]['peak_proc_ram']:.2f} GB` if num_trials > 1 else 'N/A' | `{results[2]['peak_proc_ram']:.2f} GB` if num_trials > 2 else 'N/A' | `{avg_proc_ram:.2f} GB` |
| **Peak Total System RAM** | `{results[0]['peak_sys_ram']:.2f} GB` | `{results[1]['peak_sys_ram']:.2f} GB` if num_trials > 1 else 'N/A' | `{results[2]['peak_sys_ram']:.2f} GB` if num_trials > 2 else 'N/A' | `{avg_sys_ram:.2f} GB` |
"""
    # Quick fix for single trial display if any failed
    if num_trials < 3:
        # Simple print
        print(markdown_report)
    else:
        # Standard format
        # replace the placeholder evaluations
        markdown_report_clean = markdown_report.replace(" if num_trials > 1 else 'N/A'", "").replace(" if num_trials > 2 else 'N/A'", "")
        print(markdown_report_clean)

    print("=" * 60)

if __name__ == "__main__":
    main()
