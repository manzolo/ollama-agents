# API Integration Test Suite

Comprehensive test script for validating all Ollama Agents API endpoints.

## Quick Start

```bash
# Make sure the system is running
make up

# Run the full test suite
make test-api

# Or run directly from project root
./tests/test-api.sh
```

## What It Tests

The test suite validates all major API operations in a complete end-to-end flow:

### 1. **Health Check**
- Verifies backoffice service is running
- Tests: `GET /api/health`

### 2. **Agent Lifecycle**
- Creates two test agents (`test-agent-echo` and `test-agent-reverse`)
- Deploys agents as Docker containers
- Verifies agents are running and healthy
- Tests individual agent execution
- Stops and deletes agents
- **Tests:**
  - `POST /api/agents/create`
  - `POST /api/agents/{name}/deploy`
  - `GET /api/agents`
  - `GET /api/agents/{name}/status`
  - `POST /api/agents/test`
  - `POST /api/agents/{name}/stop`
  - `DELETE /api/agents/{name}`

### 3. **Workflow Management**
- Creates a workflow using the test agents
- Lists all workflows
- Gets workflow details
- Executes the workflow
- Updates the workflow
- Deletes the workflow
- **Tests:**
  - `POST /api/workflows`
  - `GET /api/workflows`
  - `GET /api/workflows/{name}`
  - `POST /api/workflows/{name}/execute`
  - `PUT /api/workflows/{name}`
  - `DELETE /api/workflows/{name}`

### 4. **Execution Tracking**
- Retrieves execution status
- Verifies execution results
- **Tests:**
  - `GET /api/executions/{execution_id}`

## Configuration

The script supports environment variables for customization:

```bash
# Custom backoffice URL (default: http://localhost:8080)
export BACKOFFICE_URL="http://custom-host:8080"

# Disable cleanup on error (useful for debugging)
export CLEANUP_ON_ERROR="false"

# Run the tests
make test-api
```

## Output

The script provides color-coded output:

- 🔵 **Blue** - Informational messages
- ✅ **Green** - Successful tests
- ❌ **Red** - Failed tests
- ⚠️  **Yellow** - Warnings

### Example Output

```
╔════════════════════════════════════════════════════════╗
║       Ollama Agents API Integration Test Suite        ║
╔════════════════════════════════════════════════════════╗

[INFO] Testing against: http://localhost:8080

=== Phase 1: Health Check ===
[INFO] Checking backoffice health
[✓] Backoffice is healthy

=== Phase 2: Create Test Agents ===
[INFO] Creating agent: test-agent-echo
[✓] Agent test-agent-echo created
...

╔════════════════════════════════════════════════════════╗
║                    Test Summary                        ║
╚════════════════════════════════════════════════════════╝

Total Tests:  42
Passed:       42
Failed:       0

✓ All tests passed!
```

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

## CI/CD Integration

The test script is automatically run in GitHub Actions on every push and pull request. See `.github/workflows/test.yml` for the full CI pipeline.

### Manual CI Testing

```bash
# Simulate CI environment
export BACKOFFICE_URL="http://localhost:8080"
export CLEANUP_ON_ERROR="true"
make test-api
```

## Cleanup

The script automatically cleans up all test resources:
- Deletes test workflows
- Stops and removes test agent containers
- Removes agent files

If the script fails, cleanup still runs by default. To disable:

```bash
export CLEANUP_ON_ERROR="false"
make test-api
```

## Debugging Failed Tests

If tests fail, you can:

1. **Check service logs:**
   ```bash
   docker compose logs backoffice
   docker compose logs test-agent-echo
   docker compose logs test-agent-reverse
   ```

2. **Inspect agent status:**
   ```bash
   curl http://localhost:8080/api/agents
   curl http://localhost:8080/api/agents/test-agent-echo/status
   ```

3. **Check workflow details:**
   ```bash
   curl http://localhost:8080/api/workflows/test-workflow-chain
   ```

4. **Run with cleanup disabled:**
   ```bash
   CLEANUP_ON_ERROR=false make test-api
   # Then manually inspect the running containers
   docker ps
   ```

## Requirements

- `curl` - HTTP client
- `jq` - JSON processor
- `docker` - Container runtime
- Running Ollama Agents system (`make up`)

## Adding New Tests

To add tests to the script:

1. Open `tests/test-api.sh`
2. Add a new phase or test within an existing phase
3. Use the helper functions:
   - `run_test "Description"` - Start a test
   - `log_success "Message"` - Mark test passed
   - `log_error "Message"` - Mark test failed
   - `log_warning "Message"` - Show warning
   - `log_info "Message"` - Informational message

Example:

```bash
run_test "Testing new endpoint"
response=$(curl -s -w "\n%{http_code}" "$BACKOFFICE_URL/api/new-endpoint")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    log_success "New endpoint works"
else
    log_error "New endpoint failed (HTTP $http_code)"
fi
```

## See Also

- [Main Documentation](../docs/GETTING-STARTED.md)
- [Test Summary](SUMMARY.md)
- [GitHub Actions Workflow](../.github/workflows/test.yml)
- [API Documentation](http://localhost:8080/docs)
