# GPU Support Guide

## Overview

Ollama Agents supports both **CPU** and **GPU** modes. GPU acceleration significantly improves model performance but is optional.

## Default: CPU Mode

By default, the system runs in **CPU mode**:
```bash
make up       # CPU mode
make init     # CPU mode
```

This works everywhere:
- ✅ Local development machines
- ✅ GitHub Actions CI/CD
- ✅ Cloud servers without GPU
- ✅ ARM-based systems (M1/M2 Macs)

## Enabling GPU Support

### Prerequisites

1. **NVIDIA GPU** - CUDA-compatible GPU required
2. **NVIDIA Driver** - Latest driver installed
3. **Docker GPU Support**:
   ```bash
   # Install nvidia-docker2
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

   sudo apt-get update
   sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

### Verify GPU Access

```bash
# Check NVIDIA driver
nvidia-smi

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Use GPU Mode

**Option 1: Via Makefile (Recommended)**
```bash
# Initialize with GPU
make init-gpu

# Or start with GPU
make up-gpu

# Restart with GPU
make restart-gpu

# Rebuild with GPU
make rebuild-gpu
```

**Option 2: Via Docker Compose**
```bash
# Start with GPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Stop (same as CPU)
docker compose down
```

## Architecture

### CPU Mode (Default)
```
docker-compose.yml
└── ollama service (CPU only)
```

### GPU Mode
```
docker-compose.yml (base config)
+ docker-compose.gpu.yml (GPU override)
└── ollama service (with NVIDIA GPU)
```

## GPU Configuration

The GPU configuration is in `docker-compose.gpu.yml`:

```yaml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [ gpu ]
```

This configuration:
- **driver: nvidia** - Use NVIDIA GPU runtime
- **count: all** - Use all available GPUs
- **capabilities: [gpu]** - Enable GPU capabilities

### Customize GPU Usage

To use specific GPUs, edit `docker-compose.gpu.yml`:

```yaml
# Use only GPU 0
devices:
  - driver: nvidia
    device_ids: ['0']
    capabilities: [ gpu ]

# Use GPUs 0 and 1
devices:
  - driver: nvidia
    device_ids: ['0', '1']
    capabilities: [ gpu ]
```

## Performance Comparison

**CPU Mode:**
- Response time: 5-15 seconds
- Memory: ~4GB RAM
- Best for: Development, testing, CI/CD

**GPU Mode:**
- Response time: 1-3 seconds
- Memory: ~2-4GB VRAM + 2GB RAM
- Best for: Production, high-throughput workloads

## CI/CD Considerations

### GitHub Actions

GitHub Actions runners **don't have GPUs**, so we use CPU mode:

```yaml
# .github/workflows/test.yml
- name: Build services
  run: |
    docker compose build --no-cache  # CPU mode by default
```

### Self-Hosted Runners with GPU

If you have self-hosted runners with GPUs:

```yaml
jobs:
  test:
    runs-on: self-hosted-gpu  # Your GPU runner
    steps:
      - name: Build and start services
        run: |
          docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

## Troubleshooting

### GPU Not Detected

```bash
# Check nvidia-docker is installed
dpkg -l | grep nvidia-docker

# Check Docker can see GPU
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Check Ollama logs
docker compose logs ollama
```

### Out of Memory

If you get OOM errors:

1. **Use smaller models**:
   ```bash
   # In .env
   SWARM_CONVERTER_MODEL=llama3.2:1b  # Smaller model
   ```

2. **Limit GPU memory**:
   Edit `docker-compose.gpu.yml`:
   ```yaml
   environment:
     - OLLAMA_GPU_MEMORY_LIMIT=4GB
   ```

3. **Use CPU mode** for some agents:
   Keep GPU for performance-critical agents only

### Permission Denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker run --rm hello-world
```

## Best Practices

### Development
```bash
# Use CPU mode for quick tests
make up
make test-agent agent=swarm-converter

# Switch to GPU for performance testing
make down
make up-gpu
```

### Production
```bash
# Use GPU mode for best performance
make init-gpu

# Or deploy with GPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### Mixed Mode (Advanced)

Run some services with GPU, others without:

1. Create `docker-compose.partial-gpu.yml`:
   ```yaml
   services:
     ollama:
       deploy:
         resources:
           reservations:
             devices:
               - driver: nvidia
                 count: 1
                 capabilities: [ gpu ]
   ```

2. Use it:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.partial-gpu.yml up -d
   ```

## Checking GPU Usage

**While services are running:**

```bash
# Monitor GPU usage
watch -n 1 nvidia-smi

# Check Ollama GPU usage
docker compose exec ollama sh -c "nvidia-smi"

# View GPU metrics
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## Summary

| Mode | Command | Use Case |
|------|---------|----------|
| CPU | `make up` | Development, CI/CD, no GPU available |
| GPU | `make up-gpu` | Production, GPU available, best performance |

**Remember:**
- Default is CPU mode (works everywhere)
- GPU mode is optional (better performance)
- CI/CD automatically uses CPU mode
- Local development can use either mode

For questions or issues, check the [README.md](../README.md) or open an issue.
