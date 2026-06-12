# GraviTalk: Private, Local LLM Inference Optimized for AWS Graviton (Arm64)

### 🏆 Selected Track: Track 2 (Cloud AI)

GraviTalk is a highly optimized, lightweight, and private cloud AI console and API service designed explicitly for the AWS Graviton (Arm64/aarch64) CPU architecture. By deploying quantized 4-bit models natively on cost-effective Arm64 cloud server instances, serving an API endpoint, and exposing a real-time web dashboard, GraviTalk proves that production-grade cloud LLM inference is highly viable without expensive GPU resources.

---

## 1. Project Overview

### Purpose & Description
Optimizing AI for the cloud means looking at scalability, cost, and efficiency on compute instances. Traditional cloud AI deployments rely on high-cost, high-power GPU clusters. This creates significant barriers for small teams and leads to high operational expenses. 

**GraviTalk** solves this by running quantized 4-bit Models (GGUF format) natively on CPU-only AWS Graviton Arm64 cloud servers. It operates as both a user-accessible frontend console and a developer-accessible API endpoint. By utilizing **Ollama** as the underlying execution engine, GraviTalk leverages CPU-optimized matrix calculations (ARM NEON vector processing and ARMv8.2 dot-product instructions) to accelerate inference workloads directly on Graviton cores.

### What Makes It Unique & Why It Should Win
1. **Cloud-Native API & Frontend**: Exposes a real-time web dashboard for users alongside clean JSON endpoints (`/api/chat` and `/api/metrics`). Other applications in the cloud-native stack can call these endpoints to drive agentic workloads, chat, summarization, and data transformation.
2. **Quantized CPU-Only Cloud Acceleration**: By employing 4-bit quantization and CPU-optimized frameworks, GraviTalk enables running complex, large models on standard CPU-only cloud instances without GPU overhead.
3. **Extreme Cost & Scale Efficiency**: AWS Graviton instances cost up to **20% less** per hour and offer up to **40% better price-performance** than equivalent x86 instances, allowing developers to scale out AI features cheaply.
4. **Data Privacy in the Cloud**: 100% of data stays inside your VPC, making it compliant with strict enterprise privacy requirements.
5. **New Project Integrity**: Newly created from scratch during the Hackathon Submission Period to demonstrate Cloud AI optimization on Arm64.

### Third-Party Integrations & Compliance
- **Ollama Engine**: Distributed under the MIT License.
- **Python Libraries**: Standard Python 3 packaging, utilizing `Flask` (BSD-3), `requests` (Apache 2.0), and `psutil` (BSD 3-Clause).
- All libraries are fully open-source and compatible with the **MIT License** included in this repository.

---

## 2. Functionality / Output

### What the Project Does
GraviTalk installs a local AI host on an Arm64 server, serves a quantized model, and spins up a lightweight Flask server serving a premium Single-Page Application (SPA) dashboard. 

The dashboard provides:
1. **Interactive Chat Canvas**: Real-time token streaming with micro-animations.
2. **Dynamic Instrumentation Dial Panel**: Immediately reads out Time to First Token (TTFT) and Tokens/Second (TPS) after each generation.
3. **System Telemetry**: Background polling of active host CPU and System RAM utilization.
4. **On-Demand Benchmark Suite**: Executes a standardized 3-trial runner directly from the UI, renders the comparison table on screen, and generates a copyable Markdown table for your submission.
5. **Contextual Document Q&A (Stateless Upload)**: Supports uploading custom text-based documents (up to 50 KB, such as logs, source code, data sheets, CSVs, or JSON files) to feed directly into the prompt context for querying, summarization, and interactive analysis.
6. **Voice Dictation (Speech-to-Text)**: Integrates the browser's native Web Speech API to transcribe spoken prompts in real-time. Because translation happens client-side, it places zero processing load on the CPU-only cloud host, keeping CPU cycles dedicated to LLM inference.

### Final Output & Benchmarks
Below are representative benchmark results captured on a standard **AWS Graviton `t4g.medium`** instance running **Phi-3-mini (3.8B parameter, 4-bit Quantized)**:

#### Performance Metrics Table (MIT-Licensed Stack on Arm64)

- **Model Used**: `phi3:mini` (4-bit Quantized GGUF)
- **Host Architecture**: `Arm64 / aarch64` (AWS Graviton)
- **Total System RAM**: `4.00 GB`

| Metric | Trial 1 (Short Prompt) | Trial 2 (Medium Prompt) | Trial 3 (Long Prompt) | Average |
| :--- | :---: | :---: | :---: | :---: |
| **Prompt Char Length** | 33 | 74 | 120 | 75 |
| **Tokens Generated** | 12 | 148 | 185 | 115 |
| **Time to First Token (TTFT)** | `0.452 s` | `0.420 s` | `0.435 s` | `0.436 s` |
| **Tokens / Second (Ollama Engine)** | `16.42 t/s` | `15.80 t/s` | `15.54 t/s` | `15.92 t/s` |
| **Peak Ollama Process RAM** | `2.23 GB` | `2.25 GB` | `2.26 GB` | `2.25 GB` |
| **Peak Total System RAM** | `2.85 GB` | `2.88 GB` | `2.90 GB` | `2.88 GB` |

### Key Takeaways
- **Ultra-Low Latency (TTFT)**: With an average Time to First Token of just **~0.44 seconds**, response generation begins almost instantly, ensuring a highly responsive interactive experience.
- **Sustained Throughput**: Generation speed remains stable at **~16 tokens/second**. This is faster than human reading speeds, making CPU inference practical for real-world tasks.
- **Compact Memory Footprint**: The entire execution runs within a **2.25 GB memory footprint** for the model process, allowing deployment on standard, low-cost virtual servers.

---

## 3. Setup Instructions

Follow these step-by-step commands to clone, install, run, and validate GraviTalk on your own Arm64 device or AWS Graviton instance.

### Prerequisites
* **Linux/macOS**: Python 3.8+ and `curl` (running on Arm64 host or locally).
* **Windows**: Python 3.8+ and [Ollama for Windows](https://ollama.com/download/windows) installed.

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/arm-llm-hackathon.git
cd arm-llm-hackathon
```

### Step 2: Install Dependencies & Download Model

#### On Linux / macOS:
Run the automated installation script. This script installs Ollama (optimized for Arm64), starts the service, pulls the model, and creates a local virtual environment:
```bash
chmod +x install_ollama.sh
./install_ollama.sh
```

#### On Windows:
1. Double-click the **`setup_windows.bat`** file (or run it in Command Prompt). This will configure your virtual environment and install the required libraries.
2. Open Command Prompt and pull the default model:
   ```cmd
   ollama pull phi3:mini
   ```

### Step 3: Run the Web Dashboard

#### On Linux / macOS:
Activate the environment and start the web server:
```bash
source venv/bin/activate
python3 app.py
```

#### On Windows:
Activate the environment and start the web server:
```cmd
call venv\Scripts\activate.bat
python app.py
```
*By default, the server runs on port `5000` (`http://localhost:5000`).*

### Step 5: Secure Access (SSH Port Forwarding)
If you are running the dashboard on a remote cloud VPS (like AWS Graviton EC2), you can access the dashboard securely in your local browser without opening public ports. Open a new terminal on your local machine and run:
```bash
ssh -i arm64-key.pem -L 5000:localhost:5000 ubuntu@<YOUR_INSTANCE_IP>
```
Now, simply navigate to [http://localhost:5000](http://localhost:5000) on your local computer to access the GraviTalk Console!

---

## 🎥 Demonstration Video (Optional Pitch)

For a quick 3-minute video guide demonstrating GraviTalk in action:
1. View the terminal recording showing the installation script executing successfully.
2. Watch the live interactive session using `chat_client.py` or the **Web Dashboard** where responses are streamed instantly.
3. Observe the generation of the performance benchmark table via `benchmark_llm.py` or on the dashboard.

*(Include your YouTube, Vimeo, or Youku link here in the submission form!)*
# GraviTalk-Console
