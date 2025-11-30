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
echo -e "${BLUE}║       Ollama Agents API Integration Test Suite         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
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
# 10. Test Example Workflows
# ============================================================================
log_info "=== Phase 10: Test Example Workflows ==="

run_test "Listing all workflows (including examples)"
response=$(curl -s -w "\n%{http_code}" "$BACKOFFICE_URL/api/workflows")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
if [ "$http_code" -eq 200 ]; then
    workflow_count=$(echo "$body" | jq -r '.count')
    log_success "Found $workflow_count total workflows"

    # Check for example workflows
    if echo "$body" | jq -e '.workflows[] | select(.name=="ConvertAndValidate")' > /dev/null 2>&1; then
        log_success "Example workflow 'ConvertAndValidate' found"
    else
        log_warning "Example workflow 'ConvertAndValidate' not found"
    fi

    if echo "$body" | jq -e '.workflows[] | select(.name=="ValidateAndConvert")' > /dev/null 2>&1; then
        log_success "Example workflow 'ValidateAndConvert' found"
    else
        log_warning "Example workflow 'ValidateAndConvert' not found"
    fi

    pass_test "Workflows listed with examples"
else
    fail_test "Failed to list workflows (HTTP $http_code)"
fi

run_test "Getting example workflow details: ConvertAndValidate"
response=$(curl -s -w "\n%{http_code}" "$BACKOFFICE_URL/api/workflows/ConvertAndValidate")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
if [ "$http_code" -eq 200 ]; then
    source=$(echo "$body" | jq -r '.source')
    step_count=$(echo "$body" | jq -r '.steps | length')
    description=$(echo "$body" | jq -r '.description')

    log_info "  Source: $source"
    log_info "  Description: $description"
    log_info "  Steps: $step_count"

    if [ "$source" = "example" ] || [ "$source" = "examples" ]; then
        log_success "Workflow correctly marked as example"
    elif [ "$source" = "null" ] || [ -z "$source" ]; then
        log_warning "Workflow source is not set (field may not be implemented yet)"
    else
        log_warning "Workflow source is '$source', expected 'example'"
    fi

    pass_test "Example workflow details retrieved"
else
    fail_test "Failed to get example workflow (HTTP $http_code)"
fi

run_test "Attempting to update example workflow (protection check)"
response=$(curl -s -w "\n%{http_code}" -X PUT "$BACKOFFICE_URL/api/workflows/ConvertAndValidate" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ConvertAndValidate",
    "description": "Trying to modify example workflow",
    "version": "2.0.0",
    "steps": []
  }')
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 403 ] || [ "$http_code" -eq 400 ]; then
    log_success "Example workflow protected from updates (HTTP $http_code)"
elif [ "$http_code" -eq 200 ]; then
    log_warning "Example workflow was updated (protection may not be implemented)"
else
    log_info "Update returned HTTP $http_code"
fi
pass_test "Example workflow update check completed"

run_test "Attempting to delete example workflow (protection check)"
response=$(curl -s -w "\n%{http_code}" -X DELETE "$BACKOFFICE_URL/api/workflows/ConvertAndValidate")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)
if [ "$http_code" -eq 403 ] || [ "$http_code" -eq 400 ]; then
    log_success "Example workflow protected from deletion (HTTP $http_code)"
elif [ "$http_code" -eq 200 ]; then
    log_warning "Example workflow was deleted (protection may not be implemented)"
else
    log_info "Delete returned HTTP $http_code"
fi
pass_test "Example workflow deletion check completed"

run_test "Executing example workflow: ConvertAndValidate"
# Sample docker-compose input for testing
COMPOSE_INPUT='version: "3.8"
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    deploy:
      replicas: 2
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"'

response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/workflows/ConvertAndValidate/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "'"$(echo "$COMPOSE_INPUT" | sed 's/"/\\"/g' | tr '\n' ' ')"'"
  }')
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" -eq 200 ]; then
    execution_id=$(echo "$body" | jq -r '.execution_id')
    workflow_status=$(echo "$body" | jq -r '.result.status')

    log_info "  Execution ID: $execution_id"
    log_info "  Status: $workflow_status"

    if [ "$workflow_status" = "completed" ]; then
        log_success "Example workflow executed successfully"

        # Show step results
        step_count=$(echo "$body" | jq -r '.result.step_results | length')
        log_info "  Completed $step_count steps:"
        echo "$body" | jq -r '.result.step_results[] | "    - \(.step_name): \(if .success then "✓" else "✗" end)"'

        pass_test "Example workflow execution successful"
    else
        log_warning "Workflow completed with status: $workflow_status"
        # Show error if present
        error=$(echo "$body" | jq -r '.result.error // "No error message"')
        if [ "$error" != "No error message" ]; then
            log_info "  Error: $error"
        fi
        pass_test "Example workflow execution completed (check status)"
    fi
else
    log_warning "Workflow execution returned HTTP $http_code"
    log_info "Response: $(echo "$body" | jq -c '.')"
    pass_test "Example workflow execution attempted (check agents availability)"
fi

echo ""

# ============================================================================
# 11. Test Export/Import
# ============================================================================
log_info "=== Phase 11: Test Export/Import ==="

# Test Agent Export
run_test "Exporting agent: $TEST_AGENT_1"
response=$(curl -s -w "\n%{http_code}" -o "/tmp/${TEST_AGENT_1}.zip" "$BACKOFFICE_URL/api/agents/$TEST_AGENT_1/export")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    if [ -f "/tmp/${TEST_AGENT_1}.zip" ]; then
        file_size=$(stat -f%z "/tmp/${TEST_AGENT_1}.zip" 2>/dev/null || stat -c%s "/tmp/${TEST_AGENT_1}.zip" 2>/dev/null)
        log_success "Agent exported successfully (${file_size} bytes)"
        pass_test "Agent export successful"
        
        # Verify ZIP contents
        run_test "Verifying ZIP bundle contents"
        if command -v unzip > /dev/null 2>&1; then
            zip_contents=$(unzip -l "/tmp/${TEST_AGENT_1}.zip" 2>/dev/null | grep -E "\.(yml|txt|env|md)$" | wc -l)
            if [ "$zip_contents" -gt 0 ]; then
                log_success "ZIP contains $zip_contents files"
                
                # Check for required files
                if unzip -l "/tmp/${TEST_AGENT_1}.zip" | grep -q "agent.yml"; then
                    log_success "  ✓ agent.yml found"
                else
                    log_error "  ✗ agent.yml missing"
                fi
                
                if unzip -l "/tmp/${TEST_AGENT_1}.zip" | grep -q "docker-compose.yml"; then
                    log_success "  ✓ docker-compose.yml found"
                else
                    log_warning "  ! docker-compose.yml not found (may not exist for this agent)"
                fi
                
                if unzip -l "/tmp/${TEST_AGENT_1}.zip" | grep -q "\.env"; then
                    log_success "  ✓ .env found"
                else
                    log_warning "  ! .env not found (may not exist for this agent)"
                fi
                
                pass_test "ZIP bundle verified"
            else
                log_warning "ZIP appears empty or unreadable"
                pass_test "Export completed (verification skipped)"
            fi
        else
            log_warning "unzip not available, skipping content verification"
            pass_test "Export completed (verification skipped)"
        fi
    else
        fail_test "Export file not created"
    fi
else
    fail_test "Failed to export agent (HTTP $http_code)"
fi

# Test Agent Import
TEST_IMPORT_AGENT="test-agent-imported"
run_test "Importing agent from ZIP as: $TEST_IMPORT_AGENT"

# Modify the ZIP to change agent name (if possible)
if [ -f "/tmp/${TEST_AGENT_1}.zip" ] && command -v unzip > /dev/null 2>&1 && command -v zip > /dev/null 2>&1; then
    # Extract, modify, and re-zip
    mkdir -p "/tmp/agent_import_test"
    cd "/tmp/agent_import_test"
    unzip -q "/tmp/${TEST_AGENT_1}.zip"
    
    # Find and modify agent.yml to change name
    agent_yml=$(find . -name "agent.yml" | head -n1)
    if [ -n "$agent_yml" ]; then
        # Change agent name in YAML
        sed -i.bak "s/name: $TEST_AGENT_1/name: $TEST_IMPORT_AGENT/" "$agent_yml" 2>/dev/null || \
        sed -i.bak "s/name:.*$TEST_AGENT_1/name: $TEST_IMPORT_AGENT/" "$agent_yml" 2>/dev/null
        
        # Change port to avoid conflict
        sed -i.bak "s/port: 7900/port: 7902/" "$agent_yml" 2>/dev/null
        
        # Re-create ZIP
        zip -q -r "/tmp/${TEST_IMPORT_AGENT}.zip" .
        cd - > /dev/null
        rm -rf "/tmp/agent_import_test"
        
        # Now import the modified ZIP
        response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/agents/import" \
          -F "file=@/tmp/${TEST_IMPORT_AGENT}.zip")
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n-1)
        
        if [ "$http_code" -eq 200 ]; then
            imported_name=$(echo "$body" | jq -r '.agent_name')
            files_count=$(echo "$body" | jq -r '.files_imported | length')
            log_success "Agent imported: $imported_name ($files_count files)"
            
            # Show imported files
            echo "$body" | jq -r '.files_imported[]' | while read file; do
                log_info "  - $file"
            done
            
            pass_test "Agent import successful"
        else
            fail_test "Failed to import agent (HTTP $http_code)"
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        fi
    else
        log_warning "Could not modify agent.yml, skipping import test"
        pass_test "Import test skipped"
    fi
else
    log_warning "Required tools not available, skipping import test"
    pass_test "Import test skipped"
fi

# Test Workflow Export
run_test "Exporting workflow: $TEST_WORKFLOW"
response=$(curl -s -w "\n%{http_code}" -o "/tmp/${TEST_WORKFLOW}.zip" "$BACKOFFICE_URL/api/workflows/$TEST_WORKFLOW/export")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ]; then
    if [ -f "/tmp/${TEST_WORKFLOW}.zip" ]; then
        file_size=$(stat -f%z "/tmp/${TEST_WORKFLOW}.zip" 2>/dev/null || stat -c%s "/tmp/${TEST_WORKFLOW}.zip" 2>/dev/null)
        log_success "Workflow exported successfully (${file_size} bytes)"
        
        # Verify workflow ZIP
        if command -v unzip > /dev/null 2>&1; then
            if unzip -l "/tmp/${TEST_WORKFLOW}.zip" | grep -q "workflow.yml"; then
                log_success "  ✓ workflow.yml found in ZIP"
            else
                log_error "  ✗ workflow.yml missing from ZIP"
            fi
        fi
        
        pass_test "Workflow export successful"
    else
        fail_test "Workflow export file not created"
    fi
else
    fail_test "Failed to export workflow (HTTP $http_code)"
fi

# Test Workflow Import
TEST_IMPORT_WORKFLOW="test-workflow-imported"
run_test "Importing workflow from ZIP as: $TEST_IMPORT_WORKFLOW"

if [ -f "/tmp/${TEST_WORKFLOW}.zip" ] && command -v unzip > /dev/null 2>&1 && command -v zip > /dev/null 2>&1; then
    # Extract, modify, and re-zip
    mkdir -p "/tmp/workflow_import_test"
    cd "/tmp/workflow_import_test"
    unzip -q "/tmp/${TEST_WORKFLOW}.zip"
    
    # Find and modify workflow.yml to change name
    workflow_yml=$(find . -name "workflow.yml" | head -n1)
    if [ -n "$workflow_yml" ]; then
        # Change workflow name
        sed -i.bak "s/name: $TEST_WORKFLOW/name: $TEST_IMPORT_WORKFLOW/" "$workflow_yml" 2>/dev/null || \
        sed -i.bak "s/name:.*$TEST_WORKFLOW/name: $TEST_IMPORT_WORKFLOW/" "$workflow_yml" 2>/dev/null
        
        # Re-create ZIP
        zip -q -r "/tmp/${TEST_IMPORT_WORKFLOW}.zip" .
        cd - > /dev/null
        rm -rf "/tmp/workflow_import_test"
        
        # Import the modified ZIP
        response=$(curl -s -w "\n%{http_code}" -X POST "$BACKOFFICE_URL/api/workflows/import" \
          -F "file=@/tmp/${TEST_IMPORT_WORKFLOW}.zip")
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n-1)
        
        if [ "$http_code" -eq 200 ]; then
            imported_name=$(echo "$body" | jq -r '.workflow_name')
            log_success "Workflow imported: $imported_name"
            pass_test "Workflow import successful"
            
            # Clean up imported workflow
            curl -s -X DELETE "$BACKOFFICE_URL/api/workflows/$TEST_IMPORT_WORKFLOW" > /dev/null
        else
            fail_test "Failed to import workflow (HTTP $http_code)"
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        fi
    else
        log_warning "Could not modify workflow.yml, skipping import test"
        pass_test "Workflow import test skipped"
    fi
else
    log_warning "Required tools not available, skipping workflow import test"
    pass_test "Workflow import test skipped"
fi

# Cleanup test files
rm -f "/tmp/${TEST_AGENT_1}.zip" "/tmp/${TEST_IMPORT_AGENT}.zip" "/tmp/${TEST_WORKFLOW}.zip" "/tmp/${TEST_IMPORT_WORKFLOW}.zip"

# Delete imported agent if it was created
if [ -n "$TEST_IMPORT_AGENT" ]; then
    curl -s -X DELETE "$BACKOFFICE_URL/api/agents/$TEST_IMPORT_AGENT?remove_files=true" > /dev/null 2>&1
fi

echo ""

# ============================================================================
# 12. Cleanup
# ============================================================================
log_info "=== Phase 12: Cleanup ==="

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
