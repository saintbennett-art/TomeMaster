#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# BITNET LOCAL CPU ENGINE — Setup Script
# ═══════════════════════════════════════════════════════════════════════════
# Microsoft BitNet 1.58-bit: Runs LLMs entirely on CPU using ternary weights.
# No GPU required. No cloud. No API key. Sovereign intelligence.
#
# Requirements:
#   - Python 3.9+
#   - CMake 3.22+
#   - Clang 18+
#   - ~2GB disk space
#   - ~1GB RAM for the 2B model
#
# Usage:
#   chmod +x bitnet_setup.sh
#   ./bitnet_setup.sh          # Full install + start server
#   ./bitnet_setup.sh --server # Start server only (after install)
#   ./bitnet_setup.sh --chat   # Interactive chat mode
#
# Server runs on http://localhost:8080 (OpenAI-compatible API)
# TomeMaster and VoxScript connect to it automatically.
# ═══════════════════════════════════════════════════════════════════════════

set -e

BITNET_DIR="${HOME}/BitNet"
MODEL_DIR="${BITNET_DIR}/models/BitNet-b1.58-2B-4T"
THREADS=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
PORT=8080

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  ⚛️  BITNET CPU ENGINE — Sovereign 1-Bit Intelligence${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# ─── Detect OS ─────────────────────────────────────────────────────────────
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo -e "${GREEN}▸ Detected OS:${NC} $OS"
echo -e "${GREEN}▸ CPU threads:${NC} $THREADS"
echo ""

# ─── Server-Only Mode ──────────────────────────────────────────────────────
if [[ "$1" == "--server" ]]; then
    echo -e "${CYAN}▸ Starting BitNet server on port ${PORT}...${NC}"
    cd "$BITNET_DIR"
    python run_inference_server.py \
        -m "${MODEL_DIR}/ggml-model-i2_s.gguf" \
        -t "$THREADS" \
        --host 0.0.0.0 \
        --port "$PORT" \
        -c 2048 \
        -n 4096
    exit 0
fi

# ─── Chat Mode ─────────────────────────────────────────────────────────────
if [[ "$1" == "--chat" ]]; then
    echo -e "${CYAN}▸ Starting BitNet interactive chat...${NC}"
    cd "$BITNET_DIR"
    python run_inference.py \
        -m "${MODEL_DIR}/ggml-model-i2_s.gguf" \
        -p "You are a helpful AI assistant." \
        -t "$THREADS" \
        -c 2048 \
        -cnv
    exit 0
fi

# ─── Full Install ──────────────────────────────────────────────────────────

# Step 1: Install prerequisites
echo -e "${YELLOW}[1/5] Installing prerequisites...${NC}"
if [[ "$OS" == "linux" ]]; then
    sudo apt update -qq
    sudo apt install -y -qq python3-pip python3-dev cmake build-essential git wget
    # Install Clang 18
    if ! command -v clang-18 &>/dev/null; then
        echo -e "${YELLOW}  ▸ Installing Clang 18...${NC}"
        wget -qO- https://apt.llvm.org/llvm.sh | sudo bash -s 18
    fi
    export CC=clang-18
    export CXX=clang++-18
elif [[ "$OS" == "macos" ]]; then
    # macOS with Homebrew
    if ! command -v brew &>/dev/null; then
        echo -e "${RED}Error: Homebrew not found. Install from https://brew.sh${NC}"
        exit 1
    fi
    brew install cmake python@3.11 llvm
    export CC=$(brew --prefix llvm)/bin/clang
    export CXX=$(brew --prefix llvm)/bin/clang++
fi
echo -e "${GREEN}  ✓ Prerequisites installed${NC}"

# Step 2: Clone BitNet
echo -e "${YELLOW}[2/5] Cloning BitNet repository...${NC}"
if [[ -d "$BITNET_DIR" ]]; then
    echo -e "${GREEN}  ✓ BitNet directory exists, pulling latest...${NC}"
    cd "$BITNET_DIR" && git pull --quiet
else
    git clone --recursive https://github.com/microsoft/BitNet.git "$BITNET_DIR"
    cd "$BITNET_DIR"
fi
pip install -r requirements.txt --quiet 2>/dev/null || pip3 install -r requirements.txt --quiet
echo -e "${GREEN}  ✓ Repository cloned and dependencies installed${NC}"

# Step 3: Download model
echo -e "${YELLOW}[3/5] Downloading BitNet-b1.58-2B-4T model (~400MB)...${NC}"
if [[ -f "${MODEL_DIR}/ggml-model-i2_s.gguf" ]]; then
    echo -e "${GREEN}  ✓ Model already downloaded${NC}"
else
    pip install huggingface-hub --quiet 2>/dev/null || pip3 install huggingface-hub --quiet
    huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf --local-dir "$MODEL_DIR"
    echo -e "${GREEN}  ✓ Model downloaded${NC}"
fi

# Step 4: Build
echo -e "${YELLOW}[4/5] Building bitnet.cpp (this takes 2-5 minutes)...${NC}"
cd "$BITNET_DIR"
python setup_env.py -md "$MODEL_DIR" -q i2_s
echo -e "${GREEN}  ✓ Build complete${NC}"

# Step 5: Start server
echo -e "${YELLOW}[5/5] Starting BitNet server...${NC}"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ BitNet is ready!${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}▸ Server:${NC}  http://localhost:${PORT}"
echo -e "  ${GREEN}▸ API:${NC}     http://localhost:${PORT}/v1/chat/completions"
echo -e "  ${GREEN}▸ Models:${NC}  http://localhost:${PORT}/v1/models"
echo -e "  ${GREEN}▸ Threads:${NC} ${THREADS}"
echo ""
echo -e "  ${YELLOW}TomeMaster:${NC} Automatically detected via Settings → BitNet CPU Engine"
echo -e "  ${YELLOW}VoxScript:${NC}  Add Key → BitNet (CPU) → http://localhost:${PORT}"
echo ""
echo -e "  ${CYAN}To stop:${NC} Press Ctrl+C"
echo -e "  ${CYAN}To restart:${NC} ./bitnet_setup.sh --server"
echo -e "  ${CYAN}To chat:${NC} ./bitnet_setup.sh --chat"
echo ""

python run_inference_server.py \
    -m "${MODEL_DIR}/ggml-model-i2_s.gguf" \
    -t "$THREADS" \
    --host 0.0.0.0 \
    --port "$PORT" \
    -c 2048 \
    -n 4096
