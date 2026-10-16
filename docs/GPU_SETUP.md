# EasyOCR GPU Setup Guide

## Problem
EasyOCR runs on the CPU (slow) because PyTorch was installed without CUDA support. You will
see a warning like *"Neither CUDA nor MPS are available"*.

## Solution

### 1. Uninstall CPU-only PyTorch
```bash
pip uninstall torch torchvision torchaudio
```

### 2. Install PyTorch with CUDA support
Newer NVIDIA drivers are backward compatible with older CUDA builds, so a CUDA 12.1 / 12.4
wheel works with newer drivers.

**pip**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**conda**
```bash
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
```

### 3. Verify
```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```
Expected: `CUDA available: True` and your GPU name.

### 4. Use it
Set `ocr_gpu: true` in `config.yaml` (the default). Check utilisation with `nvidia-smi`
while the analysis is running.

No GPU? Set `ocr_gpu: false` or use `ocr_engine: tesseract`.
