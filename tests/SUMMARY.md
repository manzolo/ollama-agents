# API Test Suite Implementation Summary

## Overview

A comprehensive API integration test suite has been created to validate all Ollama Agents endpoints. The test suite can be run locally or in CI/CD pipelines.

## Files Created/Modified

### 1. **test-api.sh** (NEW)
Main test script that validates the complete API surface.

**Location:** `/tests/test-api.sh`

**Features:**
- ✅ Colored output (Blue/Green/Red/Yellow)
- ✅ Progress tracking with counters
- ✅ Automatic cleanup on completion/error
- ✅ Configurable via environment variables
- ✅ CI/CD friendly (proper exit codes)
- ✅ Detailed logging and error messages

**Permissions:** Executable (`chmod +x`)

### 2. **README.md** (NEW)
Complete documentation for the test suite.

**Location:** `/tests/README.md`

**Contents:**
- Quick start guide
- Complete test coverage list
- Configuration options
- Output examples
- Debugging guide
- How to add new tests

### 3. **SUMMARY.md** (NEW - This File)
Implementation summary and usage guide.

**Location:** `/tests/SUMMARY.md`

### 4. **.github/workflows/test.yml** (MODIFIED)
GitHub Actions workflow updated to include API tests.

**Changes:**
- Added new test step: "Test - Comprehensive API Integration Test"
- Updated test summary to include API integration tests
- Runs automatically on push/PR to main/develop branches

### 5. **Makefile** (MODIFIED)
Added convenient make target for running tests.

**Changes:**
- Added `test-api` target
- Updated `.PHONY` declaration

## Test Coverage

### Phase 1: Health Check
- `GET /api/health` - Backoffice health status

### Phase 2-3: Agent Creation & Deployment
- `POST /api/agents/create` - Create agent definitions
- `POST /api/agents/{name}/deploy` - Deploy agents as containers

### Phase 4: Agent Verification
- `GET /api/agents` - List all agents
- `GET /api/agents/{name}/status` - Get agent deployment status

### Phase 5: Individual Agent Testing
- `POST /api/agents/test` - Test agent execution

### Phase 6-7: Workflow Management
- `POST /api/workflows` - Create workflow
- `GET /api/workflows` - List all workflows
- `GET /api/workflows/{name}` - Get workflow details

### Phase 8: Workflow Execution
- `POST /api/workflows/{name}/execute` - Execute workflow ⭐ **NEW ENDPOINT**
- `GET /api/executions/{execution_id}` - Get execution status

### Phase 9: Workflow Updates
- `PUT /api/workflows/{name}` - Update workflow

### Phase 10: Cleanup
- `DELETE /api/workflows/{name}` - Delete workflow
- `POST /api/agents/{name}/stop` - Stop agent
- `DELETE /api/agents/{name}` - Delete agent completely

## Test Agents

The test suite creates two temporary agents:

### test-agent-echo
- **Port:** 7900
- **Purpose:** Echoes input with "ECHO: " prefix
- **Model:** llama3.2
- **Temperature:** 0.1

### test-agent-reverse
- **Port:** 7901
- **Purpose:** Reverses word order in input
- **Model:** llama3.2
- **Temperature:** 0.1

### test-workflow-chain
- **Steps:** 2
  1. Echo step (uses test-agent-echo)
  2. Reverse step (uses test-agent-reverse)
- **Purpose:** Validates workflow chaining and step orchestration

## Usage

### Local Testing

```bash
# Quick test
make test-api

# Or run directly from project root
./tests/test-api.sh

# Custom configuration
BACKOFFICE_URL=http://localhost:8080 \
CLEANUP_ON_ERROR=true \
make test-api
```

### CI/CD (GitHub Actions)

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Workflow location:** `.github/workflows/test.yml`

**Execution time:** ~30-60 seconds (depending on agent startup time)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKOFFICE_URL` | `http://localhost:8080` | Backoffice API base URL |
| `CLEANUP_ON_ERROR` | `true` | Clean up test resources on failure |

## Output Format

### Success Case

```
╔════════════════════════════════════════════════════════╗
║       Ollama Agents API Integration Test Suite        ║
╔════════════════════════════════════════════════════════╗

[INFO] Testing against: http://localhost:8080

=== Phase 1: Health Check ===
[✓] Backoffice is healthy

=== Phase 2: Create Test Agents ===
[✓] Agent test-agent-echo created
[✓] Agent test-agent-reverse created

...

╔════════════════════════════════════════════════════════╗
║                    Test Summary                        ║
╚════════════════════════════════════════════════════════╝

Total Tests:  42
Passed:       42
Failed:       0

✓ All tests passed!
```

### Failure Case

```
[✗] Failed to create agent test-agent-echo (HTTP 500)
...
Total Tests:  42
Passed:       35
Failed:       7

✗ Some tests failed
```

## Exit Codes

- `0` - All tests passed ✅
- `1` - One or more tests failed ❌

## Dependencies

The test suite requires:
- ✅ `curl` - HTTP requests
- ✅ `jq` - JSON parsing
- ✅ `docker` - Container management
- ✅ `bash` - Shell execution
- ✅ Running Ollama Agents system

## Integration with Existing Tests

The comprehensive API test complements existing tests:

### Existing Tests (`.github/workflows/test.yml`)
1. Health checks
2. Agent info endpoint
3. Process endpoint
4. Raw endpoint
5. OpenAPI schema
6. Context endpoints
7. Individual agent creation/deployment/deletion

### New Comprehensive Test (Phase 11)
8. **Full end-to-end workflow:**
   - Multi-agent creation
   - Workflow creation with agent chaining
   - Workflow execution
   - Result validation
   - Complete cleanup

## Debugging

### View Logs

```bash
# Backoffice logs
docker compose logs backoffice

# Agent logs
docker compose logs test-agent-echo
docker compose logs test-agent-reverse

# All logs
docker compose logs
```

### Manual Cleanup

If test fails and doesn't cleanup:

```bash
# Delete workflow
curl -X DELETE http://localhost:8080/api/workflows/test-workflow-chain

# Delete agents
curl -X DELETE http://localhost:8080/api/agents/test-agent-echo?remove_files=true
curl -X DELETE http://localhost:8080/api/agents/test-agent-reverse?remove_files=true

# Or use docker
docker stop agent-test-agent-echo agent-test-agent-reverse
docker rm agent-test-agent-echo agent-test-agent-reverse
```

### Disable Auto-Cleanup for Debugging

```bash
CLEANUP_ON_ERROR=false make test-api

# Then inspect the running containers
docker ps
curl http://localhost:8080/api/agents
curl http://localhost:8080/api/workflows
```

## Key Features

### 🎨 Color-Coded Output
- Blue: Informational messages
- Green: Successful tests
- Red: Failed tests
- Yellow: Warnings

### 📊 Progress Tracking
- Test counter (Total/Passed/Failed)
- Phase-by-phase execution
- Clear test summary

### 🧹 Auto-Cleanup
- Removes all test resources
- Runs even on failure (configurable)
- Prevents test pollution

### 🔧 CI/CD Ready
- Proper exit codes
- Machine-readable output
- Environment variable configuration

### 📝 Detailed Logging
- HTTP status codes
- Response bodies (JSON formatted)
- Error messages with context

## Future Enhancements

Potential additions to the test suite:

1. **Performance Testing**
   - Measure endpoint response times
   - Track workflow execution duration
   - Monitor resource usage

2. **Concurrent Testing**
   - Multiple simultaneous workflow executions
   - Parallel agent deployments
   - Race condition detection

3. **Error Case Testing**
   - Invalid inputs
   - Missing dependencies
   - Network failures

4. **Extended Workflow Testing**
   - More complex multi-step workflows
   - Conditional execution
   - Error handling paths

5. **Plugin Discovery Testing**
   - Validate plugin registry
   - Test plugin discovery endpoint
   - Verify manifest validation

## Success Criteria

A successful test run validates:

✅ All core API endpoints are functional
✅ Agent creation and deployment works
✅ Workflows can be created and executed
✅ Multi-step agent chaining functions correctly
✅ Cleanup properly removes test resources
✅ Error handling returns appropriate HTTP codes
✅ JSON responses have correct structure

## Maintenance

To maintain the test suite:

1. **Update tests when adding new endpoints**
   - Add test cases to `test-api.sh`
   - Update `TEST-API-README.md` documentation
   - Increment test counters

2. **Keep dependencies current**
   - Monitor `curl` and `jq` versions
   - Update Docker images
   - Check GitHub Actions versions

3. **Monitor test execution time**
   - Optimize slow tests
   - Adjust timeouts as needed
   - Consider parallel execution

4. **Review test coverage**
   - Ensure all endpoints are tested
   - Add edge case testing
   - Validate error scenarios

## Contact & Support

- **Documentation:** See `TEST-API-README.md` for detailed usage
- **GitHub Actions:** `.github/workflows/test.yml`
- **Issues:** Report test failures as GitHub issues
- **Contributions:** PRs welcome for new test cases

---

**Created:** 2025-11-27
**Last Updated:** 2025-11-27
**Test Script Version:** 1.0.0
**Coverage:** 10 API endpoint categories, 15+ individual endpoints
