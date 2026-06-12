#!/usr/bin/env python3
# ==============================================================================
# Script Name: app.py
# Description: Flask Web Backend serving the GraviTalk Dashboard.
#              Provides real-time SSE chat streaming, system monitoring endpoints,
#              and on-demand benchmark running.
# ==============================================================================

import os
import sys
import time
import json
import requests
import psutil
from flask import Flask, render_template, jsonify, request, Response

app = Flask(__name__, template_folder='templates')

OLLAMA_HOST = "http://localhost:11434"

def get_installed_models():
    """Helper to fetch list of installed models."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [m["name"] for m in models]
    except Exception:
        pass
    return []

def get_ollama_memory():
    """Helper to calculate Ollama memory usage in GB."""
    proc_ram = 0
    for proc in psutil.process_iter(['name']):
        try:
            if 'ollama' in proc.info['name'].lower():
                proc_ram += proc.memory_info().rss
                for child in proc.children(recursive=True):
                    proc_ram += child.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return proc_ram / (1024 ** 3)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models', methods=['GET'])
def list_models():
    models = get_installed_models()
    return jsonify({"models": models})

@app.route('/api/metrics', methods=['GET'])
def system_metrics():
    """Returns real-time server telemetry data."""
    try:
        sys_mem = psutil.virtual_memory()
        total_ram = sys_mem.total / (1024 ** 3)
        used_ram = sys_mem.used / (1024 ** 3)
        ollama_ram = get_ollama_memory()
        cpu_percent = psutil.cpu_percent(interval=None)
        
        return jsonify({
            "status": "success",
            "cpu_percent": round(cpu_percent, 1),
            "total_ram": round(total_ram, 2),
            "used_ram": round(used_ram, 2),
            "ollama_ram": round(ollama_ram, 2)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Streams chat tokens and latency telemetry using SSE."""
    data = request.json
    model = data.get('model')
    prompt = data.get('prompt')
    file_name = data.get('fileName')
    file_content = data.get('fileContent')
    images = data.get('images')
    
    if not model or not prompt:
        return jsonify({"status": "error", "message": "Missing model or prompt"}), 400
        
    # Inject document context if provided
    if file_name and file_content:
        prompt = f"Context Document (Filename: {file_name}):\n---\n{file_content}\n---\nUser Query: {prompt}"
        
    def generate():
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        if images:
            payload["images"] = images
        
        start_time = time.time()
        first_token_time = None
        char_count = 0
        ollama_eval_count = 0
        ollama_eval_duration_ns = 0
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=180)
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    
                    # Check if Ollama returned an API error (e.g. model doesn't support images)
                    if "error" in chunk:
                        error_msg = chunk["error"]
                        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                        return
                        
                    text = chunk.get("response", "")
                    
                    if first_token_time is None and text:
                        first_token_time = time.time()
                        
                    char_count += len(text)
                    
                    # Send token chunk to client
                    yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"
                    
                    if chunk.get("done", False):
                        ollama_eval_count = chunk.get("eval_count", 0)
                        ollama_eval_duration_ns = chunk.get("eval_duration", 0)
            
            end_time = time.time()
            
            # Latency (TTFT)
            ttft = (first_token_time - start_time) if first_token_time else (end_time - start_time)
            # Duration of output generation
            gen_duration = end_time - (first_token_time if first_token_time else start_time)
            gen_duration = max(0.001, gen_duration)
            
            token_estimate = max(1, round(char_count / 4))
            actual_tokens = ollama_eval_count if ollama_eval_count > 0 else token_estimate
            
            # Speed (TPS)
            client_tps = actual_tokens / gen_duration
            ollama_tps = actual_tokens / (ollama_eval_duration_ns / 1e9) if ollama_eval_duration_ns > 0 else client_tps
            
            # System Metrics at completion
            sys_mem = psutil.virtual_memory()
            used_ram = sys_mem.used / (1024 ** 3)
            ollama_ram = get_ollama_memory()
            
            # Yield final meta packet
            meta = {
                "type": "metadata",
                "ttft": round(ttft, 3),
                "tps": round(ollama_tps, 2),
                "tokens": actual_tokens,
                "used_ram": round(used_ram, 2),
                "ollama_ram": round(ollama_ram, 2)
            }
            yield f"data: {json.dumps(meta)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/benchmark', methods=['POST'])
def run_benchmark():
    """Runs the 3-trial benchmark on demand and returns the results."""
    data = request.json or {}
    model = data.get('model')
    
    if not model:
        models = get_installed_models()
        if not models:
            return jsonify({"status": "error", "message": "No local models found to benchmark."}), 400
        model = models[0]
        
    prompts = [
        "Explain recursion in one sentence.",
        "Write a concise Python function to check if a number is prime.",
        "Explain in two sentences why local AI on ARM edge devices improves privacy."
    ]
    
    results = []
    
    for prompt in prompts:
        # Sample RAM start
        ram_start_sys = psutil.virtual_memory().used / (1024 ** 3)
        ollama_start_ram = get_ollama_memory()
        
        # Request params
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": 50
            }
        }
        
        start_time = time.time()
        first_token_time = None
        char_count = 0
        ollama_eval_count = 0
        ollama_eval_duration_ns = 0
        
        # Monitor memory peaks in a simple polling loop during stream
        peak_sys_ram = ram_start_sys
        peak_ollama_ram = ollama_start_ram
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=180)
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    text = chunk.get("response", "")
                    if first_token_time is None and text:
                        first_token_time = time.time()
                    char_count += len(text)
                    if chunk.get("done", False):
                        ollama_eval_count = chunk.get("eval_count", 0)
                        ollama_eval_duration_ns = chunk.get("eval_duration", 0)
                    
                    # Quick memory check during stream block
                    sys_mem = psutil.virtual_memory().used / (1024 ** 3)
                    ollama_mem = get_ollama_memory()
                    if sys_mem > peak_sys_ram: peak_sys_ram = sys_mem
                    if ollama_mem > peak_ollama_ram: peak_ollama_ram = ollama_mem
                    
            end_time = time.time()
            
            ttft = (first_token_time - start_time) if first_token_time else (end_time - start_time)
            gen_duration = end_time - (first_token_time if first_token_time else start_time)
            gen_duration = max(0.001, gen_duration)
            
            token_estimate = max(1, round(char_count / 4))
            actual_tokens = ollama_eval_count if ollama_eval_count > 0 else token_estimate
            
            client_tps = actual_tokens / gen_duration
            ollama_tps = actual_tokens / (ollama_eval_duration_ns / 1e9) if ollama_eval_duration_ns > 0 else client_tps
            
            results.append({
                "prompt": prompt,
                "prompt_length": len(prompt),
                "tokens_generated": actual_tokens,
                "ttft": round(ttft, 3),
                "tps": round(ollama_tps, 2),
                "peak_sys_ram": round(peak_sys_ram, 2),
                "peak_ollama_ram": round(peak_ollama_ram, 2)
            })
        except Exception as e:
            return jsonify({"status": "error", "message": f"Trial failed: {str(e)}"}), 500

    # Calculate averages
    num_trials = len(results)
    avg_ttft = sum(r["ttft"] for r in results) / num_trials
    avg_tps = sum(r["tps"] for r in results) / num_trials
    avg_ollama_ram = sum(r["peak_ollama_ram"] for r in results) / num_trials
    avg_sys_ram = sum(r["peak_sys_ram"] for r in results) / num_trials
    avg_tokens = sum(r["tokens_generated"] for r in results) / num_trials
    
    # Generate Markdown Table
    total_sys_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    markdown_report = f"""| Metric | Trial 1 (Short Prompt) | Trial 2 (Medium Prompt) | Trial 3 (Long Prompt) | Average |
| :--- | :---: | :---: | :---: | :---: |
| **Prompt Char Length** | {results[0]['prompt_length']} | {results[1]['prompt_length']} | {results[2]['prompt_length']} | {sum(r['prompt_length'] for r in results)//num_trials} |
| **Tokens Generated** | {results[0]['tokens_generated']} | {results[1]['tokens_generated']} | {results[2]['tokens_generated']} | {int(avg_tokens)} |
| **Time to First Token (TTFT)** | `{results[0]['ttft']:.3f} s` | `{results[1]['ttft']:.3f} s` | `{results[2]['ttft']:.3f} s` | `{avg_ttft:.3f} s` |
| **Tokens / Second (Ollama Engine)** | `{results[0]['tps']:.2f} t/s` | `{results[1]['tps']:.2f} t/s` | `{results[2]['tps']:.2f} t/s` | `{avg_tps:.2f} t/s` |
| **Peak Ollama Process RAM** | `{results[0]['peak_ollama_ram']:.2f} GB` | `{results[1]['peak_ollama_ram']:.2f} GB` | `{results[2]['peak_ollama_ram']:.2f} GB` | `{avg_ollama_ram:.2f} GB` |
| **Peak Total System RAM** | `{results[0]['peak_sys_ram']:.2f} GB` | `{results[1]['peak_sys_ram']:.2f} GB` | `{results[2]['peak_sys_ram']:.2f} GB` | `{avg_sys_ram:.2f} GB` |"""

    return jsonify({
        "status": "success",
        "model": model,
        "total_system_ram": round(total_sys_ram_gb, 2),
        "results": results,
        "averages": {
            "ttft": round(avg_ttft, 3),
            "tps": round(avg_tps, 2),
            "ollama_ram": round(avg_ollama_ram, 2),
            "sys_ram": round(avg_sys_ram, 2)
        },
        "markdown_table": markdown_report
    })

if __name__ == '__main__':
    # Binding to all interfaces so it can be accessed on external browser if public IP is allowed.
    # Security note: In setup instructions, we suggest local port forwarding for safety.
    app.run(host='0.0.0.0', port=5000, debug=True)
