#!/bin/bash
set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKOFFICE_URL="${BACKOFFICE_URL:-http://localhost:8080}"
TEST_AGENT_1="test-agent-echo"
TEST_AGENT_2="test-agent-reverse"
TEST_WORKFLOW="test-workflow-chain"
CLEANUP_ON_ERROR="${CLEANUP_ON_ERROR:-true}"

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

run_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    log_info "$1"
}

pass_test() {
    log_success "$1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail_test() {
    log_error "$1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

check_health() {
    run_test "Checking backoffice health"
    response=$(curl -s -w "\n%{http_code}" "$BACKOFFICE_URL/api/health")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" -eq 200 ]; then
        pass_test "Backoffice is healthy"
        return 0
    else
        fail_test "Backoffice health check failed (HTTP $http_code)"
        return 1
    fi
}

cleanup() {
    log_info "=== Cleanup ==="

    # Delete workflow
    run_test "Deleting test workflow: $TEST_WORKFLOW"
    response=$(curl -s -w "\n%{http_code}" -X DELETE "$BACKOFFICE_URL/api/workflows/$TEST_WORKFLOW")
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 404 ]; then
        log_success "Workflow deleted or already gone"
    else
        log_warning "Failed to delete workflow (HTTP $http_code)"
    fi

    # Delete agents
    for agent in "$TEST_AGENT_1" "$TEST_AGENT_2"; do
        run_test "Deleting test agent: $agent"
        response=$(curl -s -w "\n%{http_code}" -X DELETE "$BACKOFFICE_URL/api/agents/$agent?remove_files=true")
        http_code=$(echo "$response" | tail -n1)
        if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 404 ]; then
            log_success "Agent $agent deleted or already gone"
        else
            log_warning "Failed to delete agent $agent (HTTP $http_code)"
        fi
    done
}

# Trap to cleanup on error if enabled
if [ "$CLEANUP_ON_ERROR" = "true" ]; then
    trap cleanup EXIT
fi

# ============================================================================
# Main Test Suite
# ============================================================================

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Ollama Agents API Integration Test Suite        ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo ""
log_info "Testing against: $BACKOFFICE_URL"
echo ""

# ============================================================================
# 1. Health Check
# ============================================================================
log_info "=== Phase 1: Health Check ==="
check_health || exit 1
echo ""

# ============================================================================
# 2. Create Test Agents
# ============================================================================
log_info "=== Phase 2: Create Test Agents ==="

# Agent 1: Echo Agent
run_test "Creating agent: $TEST_AGENT_1"
response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/agents/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "'"$TEST_AGENT_1"'",
    "description": "Test agent that echoes input",
    "port": 7900,
    "model": "llama3.2",
    "temperature": 0.1,
    "max_tokens": 512,
    "capabilities": ["text-processing", "testing"],
    "system_prompt": "You are a helpful assistant. Simply echo back the input you receive with the prefix \"ECHO: \". Keep responses short and direct."
  }')
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    pass_test "Agent $TEST_AGENT_1 created"
else
    fail_test "Failed to create agent $TEST_AGENT_1 (HTTP $http_code)"
    exit 1
fi

# Agent 2: Reverse Agent
run_test "Creating agent: $TEST_AGENT_2"
response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/agents/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "'"$TEST_AGENT_2"'",
    "description": "Test agent that reverses text",
    "port": 7901,
    "model": "llama3.2",
    "temperature": 0.1,
    "max_tokens": 512,
    "capabilities": ["text-processing", "testing"],
    "system_prompt": "You are a helpful assistant. Reverse the order of words in the input text. Only return the reversed text, nothing else."
  }')
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    pass_test "Agent $TEST_AGENT_2 created"
else
    fail_test "Failed to create agent $TEST_AGENT_2 (HTTP $http_code)"
    exit 1
fi
echo ""

# ============================================================================
# 3. Deploy Test Agents
# ============================================================================
log_info "=== Phase 3: Deploy Test Agents ==="

for agent in "$TEST_AGENT_1" "$TEST_AGENT_2"; do
    run_test "Deploying agent: $agent"
    response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/agents/$agent/deploy")
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" -eq 200 ]; then
        pass_test "Agent $agent deployed"
    else
        fail_test "Failed to deploy agent $agent (HTTP $http_code)"
        body=$(echo "$response" | head -n-1)
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        exit 1
    fi
done
echo ""

# Wait for agents to start
log_info "Waiting for agents to start (30s)..."
sleep 30

# Trigger plugin discovery to ensure agents are registered
log_info "Triggering plugin discovery..."
curl -s -X POST "$BACKOFFICE_URL/api/plugins/discover" > /dev/null
sleep 2

# ============================================================================
# 4. Verify Agents are Running
# ============================================================================
log_info "=== Phase 4: Verify Agents ==="

run_test "Listing all agents"
response=$(curl -s -w "\n%{http_code}" "$BACKOFFICE_URL/api/agents")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
if [ "$http_code" -eq 200 ]; then
    agent_count=$(echo "$body" | jq -r '.count')
    log_success "Found $agent_count agents"

    # Check if our test agents are present
    for agent in "$TEST_AGENT_1" "$TEST_AGENT_2"; do
        if echo "$body" | jq -e ".agents.\"$agent\"" > /dev/null 2>&1; then
            status=$(echo "$body" | jq -r ".agents.\"$agent\".status")
            log_success "Agent $agent is present (status: $status)"
        else
            log_error "Agent $agent not found in agent list"
        fi
    done
    pass_test "Agents listed successfully"
else
    fail_test "Failed to list agents (HTTP $http_code)"
    exit 1
fi

# Check agent status
for agent in "$TEST_AGENT_1" "$TEST_AGENT_2"; do
    run_test "Checking status of $agent"
    response=$(curl -s -w "\n%{http_code}" "$BACKOFFICE_URL/api/agents/$agent/status")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    if [ "$http_code" -eq 200 ]; then
        container_running=$(echo "$body" | jq -r '.container_status')
        healthy=$(echo "$body" | jq -r '.healthy')
        
        if [ "$container_running" = "running" ] && [ "$healthy" = "true" ]; then
            log_success "Agent $agent container is running and healthy"
        else
            log_warning "Agent $agent status issue: container=$container_running, healthy=$healthy"
        fi
        pass_test "Agent status retrieved"
    else
        log_error "Failed to check status of $agent (HTTP $http_code)"
    fi
done
echo ""

# ============================================================================
# 5. Test Individual Agents
# ============================================================================
log_info "=== Phase 5: Test Individual Agents ==="

run_test "Testing $TEST_AGENT_1 (echo agent)"
response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/agents/test" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "'"$TEST_AGENT_1"'",
    "input": "Hello World"
  }')
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
if [ "$http_code" -eq 200 ]; then
    success=$(echo "$body" | jq -r '.success')
    if [ "$success" = "true" ]; then
        output=$(echo "$body" | jq -r '.output' | head -c 100)
        log_success "Agent $TEST_AGENT_1 responded: ${output}..."
    else
        log_error "Agent $TEST_AGENT_1 call failed"
        echo "$body" | jq '.'
    fi
    pass_test "Agent test completed"
else
    fail_test "Failed to test agent $TEST_AGENT_1 (HTTP $http_code)"
fi

run_test "Testing $TEST_AGENT_2 (reverse agent)"
response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/agents/test" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "'"$TEST_AGENT_2"'",
    "input": "one two three"
  }')
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
if [ "$http_code" -eq 200 ]; then
    success=$(echo "$body" | jq -r '.success')
    if [ "$success" = "true" ]; then
        output=$(echo "$body" | jq -r '.output' | head -c 100)
        log_success "Agent $TEST_AGENT_2 responded: ${output}..."
    else
        log_error "Agent $TEST_AGENT_2 call failed"
        echo "$body" | jq '.'
    fi
    pass_test "Agent test completed"
else
    fail_test "Failed to test agent $TEST_AGENT_2 (HTTP $http_code)"
fi
echo ""

# ============================================================================
# 6. Create Test Workflow
# ============================================================================
log_info "=== Phase 6: Create Test Workflow ==="

run_test "Creating workflow: $TEST_WORKFLOW"
response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/workflows" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "'"$TEST_WORKFLOW"'",
    "description": "Test workflow that chains echo and reverse",
    "version": "1.0.0",
    "steps": [
      {
        "name": "echo-step",
        "agent": "'"$TEST_AGENT_1"'",
        "input": "original"
      },
      {
        "name": "reverse-step",
        "agent": "'"$TEST_AGENT_2"'",
        "input": "previous"
      }
    ]
  }')
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    pass_test "Workflow $TEST_WORKFLOW created"
else
    fail_test "Failed to create workflow (HTTP $http_code)"
    body=$(echo "$response" | head -n-1)
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
    exit 1
fi
echo ""

# ============================================================================
# 7. List and Get Workflow
# ============================================================================
log_info "=== Phase 7: Verify Workflow ==="

run_test "Listing all workflows"
response=$(curl -s -w "\n%{http_code}" "$BACKOFFICE_URL/api/workflows")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
if [ "$http_code" -eq 200 ]; then
    workflow_count=$(echo "$body" | jq -r '.count')
    log_success "Found $workflow_count workflows"

    # Check if our test workflow is present
    if echo "$body" | jq -e ".workflows[] | select(.name==\"$TEST_WORKFLOW\")" > /dev/null 2>&1; then
        log_success "Workflow $TEST_WORKFLOW is in the list"
    else
        log_error "Workflow $TEST_WORKFLOW not found in workflow list"
    fi
    pass_test "Workflows listed successfully"
else
    fail_test "Failed to list workflows (HTTP $http_code)"
    exit 1
fi

run_test "Getting workflow details: $TEST_WORKFLOW"
response=$(curl -s -w "\n%{http_code}" "$BACKOFFICE_URL/api/workflows/$TEST_WORKFLOW")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
if [ "$http_code" -eq 200 ]; then
    step_count=$(echo "$body" | jq -r '.steps | length')
    pass_test "Workflow has $step_count steps"
else
    fail_test "Failed to get workflow details (HTTP $http_code)"
fi
echo ""

# ============================================================================
# 8. Execute Workflow
# ============================================================================
log_info "=== Phase 8: Execute Workflow ==="

run_test "Executing workflow: $TEST_WORKFLOW"
response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/workflows/$TEST_WORKFLOW/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Testing workflow execution"
  }')
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 200 ]; then
    execution_id=$(echo "$body" | jq -r '.execution_id')
    workflow_status=$(echo "$body" | jq -r '.result.status')

    if [ "$workflow_status" = "completed" ]; then
        log_success "Workflow executed successfully (ID: $execution_id)"

        # Show step results
        step_results=$(echo "$body" | jq -r '.result.step_results[] | "\(.step_name): \(.success)"')
        echo "$step_results" | while read line; do
            log_info "  - $line"
        done

        # Check execution endpoint
        run_test "Getting execution status: $execution_id"
        response=$(curl -s -w "\n%{http_code}" "$BACKOFFICE_URL/api/executions/$execution_id")
        http_code=$(echo "$response" | tail -n1)
        if [ "$http_code" -eq 200 ]; then
            pass_test "Execution details retrieved"
        else
            fail_test "Failed to get execution details (HTTP $http_code)"
        fi
        pass_test "Workflow executed successfully"
    else
        fail_test "Workflow execution failed (status: $workflow_status)"
        echo "$body" | jq '.result.error'
    fi
else
    fail_test "Failed to execute workflow (HTTP $http_code)"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
fi
echo ""

# ============================================================================
# 9. Update Workflow
# ============================================================================
log_info "=== Phase 9: Update Workflow ==="

run_test "Updating workflow: $TEST_WORKFLOW"
response=$(curl -s -w "\n%{http_code}" -X PUT "$BACKOFFICE_URL/api/workflows/$TEST_WORKFLOW" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "'"$TEST_WORKFLOW"'",
    "description": "Updated test workflow description",
    "version": "1.1.0",
    "steps": [
      {
        "name": "echo-step",
        "agent": "'"$TEST_AGENT_1"'",
        "input": "original"
      }
    ]
  }')
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    pass_test "Workflow updated successfully"
else
    fail_test "Failed to update workflow (HTTP $http_code)"
fi
echo ""

# ============================================================================
# 10. Cleanup
# ============================================================================
log_info "=== Phase 10: Cleanup ==="

run_test "Deleting workflow: $TEST_WORKFLOW"
response=$(curl -s -w "\n%{http_code}" -X DELETE "$BACKOFFICE_URL/api/workflows/$TEST_WORKFLOW")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    pass_test "Workflow deleted"
else
    fail_test "Failed to delete workflow (HTTP $http_code)"
fi

run_test "Stopping agent: $TEST_AGENT_1"
response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/agents/$TEST_AGENT_1/stop")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    pass_test "Agent $TEST_AGENT_1 stopped"
else
    log_warning "Failed to stop agent $TEST_AGENT_1 (HTTP $http_code)"
fi

run_test "Stopping agent: $TEST_AGENT_2"
response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/agents/$TEST_AGENT_2/stop")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    pass_test "Agent $TEST_AGENT_2 stopped"
else
    log_warning "Failed to stop agent $TEST_AGENT_2 (HTTP $http_code)"
fi

run_test "Deleting agent: $TEST_AGENT_1"
response=$(curl -s -w "\n%{http_code}" -X DELETE "$BACKOFFICE_URL/api/agents/$TEST_AGENT_1?remove_files=true")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    pass_test "Agent $TEST_AGENT_1 deleted"
else
    fail_test "Failed to delete agent $TEST_AGENT_1 (HTTP $http_code)"
fi

run_test "Deleting agent: $TEST_AGENT_2"
response=$(curl -s -w "\n%{http_code}" -X DELETE "$BACKOFFICE_URL/api/agents/$TEST_AGENT_2?remove_files=true")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    pass_test "Agent $TEST_AGENT_2 deleted"
else
    fail_test "Failed to delete agent $TEST_AGENT_2 (HTTP $http_code)"
fi

echo ""
# ============================================================================
# Summary
# ============================================================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Test Summary                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total Tests:  ${BLUE}$TESTS_RUN${NC}"
echo -e "Passed:       ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed:       ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
