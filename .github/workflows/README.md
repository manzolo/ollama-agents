# GitHub Actions CI/CD

This directory contains GitHub Actions workflows for automated testing and continuous integration.

## Workflows

### test.yml - Automated Testing

Runs comprehensive tests on every push and pull request to `main` and `develop` branches.

#### Test Flow

```
1. Checkout code
2. Setup Docker Buildx
3. Install dependencies (jq, curl)
4. Build services
5. Start Ollama service
6. Wait for Ollama health
7. Pull llama3.2 model
8. Start swarm-converter agent
9. Wait for agent health
10. Run tests:
    - Health check
    - Agent info
    - Process endpoint
    - Raw endpoint
    - OpenAPI schema
    - Context endpoints
11. Cleanup
```

#### Duration

- **Typical run time**: 15-20 minutes
- **Timeout**: 30 minutes

#### Test Commands

The workflow executes these test commands:

```bash
# Health Check
curl -s http://localhost:7001/health | jq .

# Agent Info
curl -s http://localhost:7001/info | jq .

# Process Test
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d '{"input": "..."}' | jq .

# Raw Endpoint Test
curl -X POST http://localhost:7001/process/raw \
  -H "Content-Type: application/json" \
  -d '{"input": "..."}' | jq .

# OpenAPI Schema
curl -s http://localhost:7001/openapi.json | jq .

# Context Endpoints
curl -s http://localhost:7001/context | jq .
```

## Running Tests Locally

To run the same tests locally:

```bash
# 1. Build and start services
docker compose build
docker compose up -d

# 2. Wait for services
sleep 30

# 3. Run health checks
curl -s http://localhost:7001/health | jq .

# 4. Run process test
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d '{"input": "version: '\''3.8'\''\nservices:\n  web:\n    build: ."}' \
  | jq .

# 5. Cleanup
docker compose down -v
```

## Troubleshooting

### Tests Failing Locally

```bash
# Check logs
docker compose logs ollama
docker compose logs swarm-converter

# Check health
docker compose ps

# Manual health check
curl http://localhost:7001/health
```

### Timeout Issues

If tests timeout:
1. Increase `timeout-minutes` in workflow
2. Check if model download is slow
3. Verify Docker resources (RAM/CPU)

### Model Download Issues

```bash
# Pre-pull the model
docker compose exec ollama ollama pull llama3.2

# Verify model exists
docker compose exec ollama ollama list
```

## Adding New Tests

To add new tests to the workflow:

1. Add a new step in `.github/workflows/test.yml`
2. Use descriptive name: `- name: Test - Your Test Name`
3. Include error checking
4. Add to test summary at the end

Example:

```yaml
- name: Test - New Feature
  run: |
    echo "Testing new feature..."
    response=$(curl -s http://localhost:7001/new-endpoint)
    echo "$response" | jq .

    # Validate response
    status=$(echo "$response" | jq -r '.status')
    if [ "$status" != "success" ]; then
      echo "Test failed"
      exit 1
    fi
    echo "✓ New feature test passed"
```

## Environment Variables

The workflow uses these environment variables:

- `DOCKER_BUILDKIT: 1` - Enable BuildKit for faster builds
- Standard Docker Compose environment variables from `.env`

## Secrets

No secrets are currently required. If you need to add authentication or API keys:

1. Add secrets in GitHub repository settings
2. Reference in workflow: `${{ secrets.YOUR_SECRET }}`
3. Pass to Docker Compose: `-e SECRET_KEY=${{ secrets.YOUR_SECRET }}`

## Best Practices

1. ✅ Always include health checks before tests
2. ✅ Add proper wait times for service startup
3. ✅ Use `-T` flag with `docker compose exec` in CI
4. ✅ Always cleanup resources with `docker compose down -v`
5. ✅ Show logs on failure for debugging
6. ✅ Use `if: always()` for cleanup steps
7. ✅ Include test summary for quick overview

## Badges

Add status badge to your README:

```markdown
![Tests](https://github.com/YOUR_USERNAME/ollama-agents/actions/workflows/test.yml/badge.svg)
```

## Future Enhancements

Potential additions:
- [ ] Performance testing
- [ ] Load testing with multiple concurrent requests
- [ ] Security scanning (Trivy, Snyk)
- [ ] Code coverage reporting
- [ ] Multi-agent pipeline tests
- [ ] Integration tests with multiple agents
- [ ] Docker image scanning
- [ ] Deployment automation
