#!/bin/bash
# ==============================================================================
# Script Name: install_ollama.sh
# Description: Installs Ollama (optimized for Arm64/aarch64) and downloads
#              a lightweight 4-bit quantized LLM (default: Phi-3-mini).
#              Also sets up Python virtual environment and dependencies.
# ==============================================================================

set -euo pipefail

# Text colors for logging
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Verify Architecture is Arm64 (aarch64)
ARCH=$(uname -m)
log_info "Verifying system architecture..."
if [ "$ARCH" != "aarch64" ]; then
    log_warn "Current architecture is $ARCH. Ollama will still compile/run, but this script is optimized for Arm64 (aarch64) servers."
else
    log_success "Verified architecture is $ARCH (Arm64/Graviton)."
fi

# 2. Update package list and install basic dependencies
log_info "Updating package lists and installing basic requirements..."
sudo apt-get update -y
sudo apt-get install -y curl python3-pip python3-venv python3-dev build-essential

# 3. Check RAM to recommend the correct model
TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_MEM_GB=$(echo "scale=1; $TOTAL_MEM_KB / 1024 / 1024" | bc)
log_info "System RAM detected: ${TOTAL_MEM_GB} GB"

# Default model selection based on RAM
# Phi-3-mini (3.8B parameters) needs ~2.2GB for model weights and at least 3-4GB of RAM.
# Qwen2.5-1.5B (1.5B parameters) needs ~900MB for weights and runs perfectly on 2GB RAM.
DEFAULT_MODEL="phi3:mini"
if (( $(echo "$TOTAL_MEM_GB < 3.0" | bc -l) )); then
    log_warn "Your system RAM (${TOTAL_MEM_GB} GB) is less than 3 GB. Running 'phi3:mini' may cause Out-Of-Memory (OOM) errors or slow performance."
    log_warn "Switching default model to 'qwen2.5:1.5b' (~900MB weights) for smooth execution."
    DEFAULT_MODEL="qwen2.5:1.5b"
fi

# Allow overriding the model from the command line argument
MODEL=${1:-$DEFAULT_MODEL}

# 4. Install Ollama
log_info "Installing Ollama (compiled natively for Arm64 CPU acceleration)..."
# Ollama's official script automatically detects Arm64 and installs the precompiled, highly optimized aarch64 binary.
curl -fsSL https://ollama.com/install.sh | sh

# 5. Verify Ollama service is running and listening on port 11434
log_info "Checking Ollama service status..."
if systemctl is-active --quiet ollama; then
    log_success "Ollama service unit is active."
else
    log_warn "Ollama service is not running. Attempting to start it..."
    sudo systemctl start ollama
    sleep 3
    if systemctl is-active --quiet ollama; then
        log_success "Ollama service successfully started."
    else
        log_error "Could not start Ollama service. Please check systemctl logs."
        exit 1
    fi
fi

log_info "Waiting for Ollama API server to bind to port 11434..."
SERVER_READY=false
for i in {1..15}; do
    if curl -s http://localhost:11434 >/dev/null; then
        log_success "Ollama server is listening on port 11434 and ready."
        SERVER_READY=true
        break
    fi
    sleep 1
done

if [ "$SERVER_READY" = "false" ]; then
    log_warn "Ollama service is active but not responding on port 11434 yet."
    log_warn "Attempting to start Ollama server in background inline..."
    ollama serve > /dev/null 2>&1 &
    sleep 5
    if curl -s http://localhost:11434 >/dev/null; then
        log_success "Ollama inline server successfully started and listening."
    else
        log_error "Ollama server failed to respond on port 11434. Please run 'ollama serve' manually in another window."
        exit 1
    fi
fi

# 6. Pull the quantized model
log_info "Downloading quantized model '${MODEL}' (4-bit GGUF format)..."
# This downloads the model from Ollama registry, optimized for local CPU inference.
ollama pull "$MODEL"

# 7. Setup Python Virtual Environment and Install Interface/Benchmarking dependencies
log_info "Setting up Python virtual environment in directory 'venv'..."
python3 -m venv venv
# Activate virtual environment
# shellcheck disable=SC1091
source venv/bin/activate

log_info "Installing Python packages (requests, psutil, flask)..."
pip install --upgrade pip
pip install requests psutil flask

log_success "========================================================"
log_success " Setup Complete!"
log_success "========================================================"
log_success " - Ollama is installed and running."
log_success " - Model '${MODEL}' is downloaded."
log_success " - Python virtual environment is configured with required libraries."
log_success " To run the web dashboard/client/benchmark, activate the virtual environment:"
log_success "     source venv/bin/activate"
log_success " And run the web server dashboard:"
log_success "     python3 app.py"
log_success " (Or run client/benchmark in terminal):"
log_success "     python3 chat_client.py"
log_success "     python3 benchmark_llm.py"
log_success "========================================================"
