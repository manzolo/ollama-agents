/**
 * Ollama Agents Backoffice Application
 * Frontend JavaScript
 */

const API_BASE = '/api';

// Toast Notification System
const Toast = {
    show(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="Toast.remove(this.parentElement)">×</button>
        `;

        container.appendChild(toast);

        if (duration > 0) {
            setTimeout(() => Toast.remove(toast), duration);
        }

        return toast;
    },

    remove(toast) {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    },

    success(message, duration) {
        return this.show(message, 'success', duration);
    },

    error(message, duration) {
        return this.show(message, 'error', duration);
    },

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    },

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
};

// Dialog System
const Dialog = {
    confirm(message, title = 'Confirm') {
        return new Promise((resolve) => {
            const dialog = document.getElementById('confirm-dialog');
            const titleEl = document.getElementById('confirm-title');
            const messageEl = document.getElementById('confirm-message');
            const okBtn = document.getElementById('confirm-ok');
            const cancelBtn = document.getElementById('confirm-cancel');

            titleEl.textContent = title;
            messageEl.textContent = message;
            dialog.classList.add('active');

            const cleanup = () => {
                dialog.classList.remove('active');
                okBtn.onclick = null;
                cancelBtn.onclick = null;
            };

            okBtn.onclick = () => {
                cleanup();
                resolve(true);
            };

            cancelBtn.onclick = () => {
                cleanup();
                resolve(false);
            };

            // Close on backdrop click
            dialog.onclick = (e) => {
                if (e.target === dialog) {
                    cleanup();
                    resolve(false);
                }
            };
        });
    },

    prompt(message, defaultValue = '', title = 'Input Required') {
        return new Promise((resolve) => {
            const dialog = document.getElementById('prompt-dialog');
            const titleEl = document.getElementById('prompt-title');
            const messageEl = document.getElementById('prompt-message');
            const inputEl = document.getElementById('prompt-input');
            const okBtn = document.getElementById('prompt-ok');
            const cancelBtn = document.getElementById('prompt-cancel');

            titleEl.textContent = title;
            messageEl.textContent = message;
            inputEl.value = defaultValue;
            dialog.classList.add('active');
            inputEl.focus();

            const cleanup = () => {
                dialog.classList.remove('active');
                okBtn.onclick = null;
                cancelBtn.onclick = null;
                inputEl.onkeypress = null;
            };

            okBtn.onclick = () => {
                const value = inputEl.value;
                cleanup();
                resolve(value);
            };

            cancelBtn.onclick = () => {
                cleanup();
                resolve(null);
            };

            inputEl.onkeypress = (e) => {
                if (e.key === 'Enter') {
                    const value = inputEl.value;
                    cleanup();
                    resolve(value);
                }
            };

            // Close on backdrop click
            dialog.onclick = (e) => {
                if (e.target === dialog) {
                    cleanup();
                    resolve(null);
                }
            };
        });
    }
};

const app = {
    // State
    state: {
        agents: [],
        workflows: [],
        executions: [],
        currentTab: 'agents'
    },

    // Initialize
    init() {
        console.log('Initializing Backoffice App...');
        this.setupTabs();
        this.setupForms();
        this.loadAgents();
        this.loadWorkflows();
        this.loadExecutions();
    },

    // Tab Management
    setupTabs() {
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });
    },

    switchTab(tabName) {
        // Update buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.state.currentTab = tabName;

        // Load data for tab if needed
        if (tabName === 'execute') {
            this.populateWorkflowSelect();
        }
    },

    // Forms Setup
    setupForms() {
        // Execute workflow form
        document.getElementById('execute-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.executeWorkflow();
        });

        // Create workflow form
        document.getElementById('create-workflow-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.createWorkflow();
        });
    },

    // API Calls
    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || error.error || 'API request failed');
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            Toast.error(error.message);
            throw error;
        }
    },

    // Agents
    async loadAgents() {
        const container = document.getElementById('agents-list');
        container.innerHTML = '<div class="loading">Loading agents...</div>';

        try {
            const data = await this.apiCall('/agents');
            this.state.agents = data.agents;
            this.renderAgents();
        } catch (error) {
            container.innerHTML = '<div class="alert alert-error">Failed to load agents</div>';
        }
    },

    renderAgents() {
        const container = document.getElementById('agents-list');

        if (Object.keys(this.state.agents).length === 0) {
            container.innerHTML = '<div class="card"><p>No agents found</p></div>';
            return;
        }

        const agentsHTML = Object.entries(this.state.agents).map(([name, agent]) => {
            const statusClass = agent.status === 'healthy' ? 'healthy' : 'unavailable';
            const cardClass = `status-${agent.status}`;

            return `
                <div class="card agent-card ${cardClass}">
                    <div class="agent-header">
                        <div class="agent-name">${name}</div>
                        <span class="status-badge ${statusClass}">${agent.status}</span>
                    </div>
                    <p><strong>Model:</strong> ${agent.model || 'N/A'}</p>
                    <p><strong>URL:</strong> <code>${agent.url}</code></p>
                    ${agent.description ? `<p>${agent.description}</p>` : ''}
                    ${agent.capabilities && agent.capabilities.length > 0 ? `
                        <div class="capabilities">
                            ${agent.capabilities.map(cap => `<span class="capability-tag">${cap}</span>`).join('')}
                        </div>
                    ` : ''}
                    ${agent.status === 'healthy' ? `
                        <div style="margin-top: 15px;">
                            <button onclick="app.testAgent('${name}')" class="btn btn-small btn-primary">Test Agent</button>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

        container.innerHTML = agentsHTML;
    },

    async testAgent(agentName) {
        const testInput = await Dialog.prompt(`Enter test input for ${agentName}:`, 'Hello, test!', 'Test Agent');
        if (!testInput) return;

        try {
            const result = await this.apiCall('/agents/test', {
                method: 'POST',
                body: JSON.stringify({
                    agent_name: agentName,
                    input: testInput
                })
            });

            Toast.success(`Agent ${agentName} responded successfully!`);
            console.log('Agent Response:', result);
        } catch (error) {
            // Error already shown by apiCall
        }
    },

    // Workflows
    async loadWorkflows() {
        const container = document.getElementById('workflows-list');
        container.innerHTML = '<div class="loading">Loading workflows...</div>';

        try {
            const data = await this.apiCall('/workflows');
            this.state.workflows = data.workflows;
            this.renderWorkflows();
        } catch (error) {
            container.innerHTML = '<div class="alert alert-error">Failed to load workflows</div>';
        }
    },

    renderWorkflows() {
        const container = document.getElementById('workflows-list');

        if (this.state.workflows.length === 0) {
            container.innerHTML = '<div class="card"><p>No workflows found. Create one to get started!</p></div>';
            return;
        }

        const workflowsHTML = this.state.workflows.map(workflow => `
            <div class="card workflow-card">
                <div class="workflow-header">
                    <div>
                        <div class="workflow-name">${workflow.name}</div>
                        <p>${workflow.description || 'No description'}</p>
                    </div>
                </div>
                <p><strong>Steps:</strong> ${workflow.steps}</p>
                <p><strong>Version:</strong> ${workflow.version || 'N/A'}</p>
                <div class="workflow-actions">
                    <button onclick="app.viewWorkflow('${workflow.name}')" class="btn btn-small btn-primary">View</button>
                    <button onclick="app.runWorkflow('${workflow.name}')" class="btn btn-small btn-success">Run</button>
                    <button onclick="app.deleteWorkflow('${workflow.name}')" class="btn btn-small btn-danger">Delete</button>
                </div>
            </div>
        `).join('');

        container.innerHTML = workflowsHTML;
    },

    async viewWorkflow(workflowName) {
        try {
            const workflow = await this.apiCall(`/workflows/${workflowName}`);
            Toast.info(`Workflow: ${workflow.name} (${workflow.steps.length} steps) - Check console for details`);
            console.log('Workflow Details:', workflow);
        } catch (error) {
            // Error already shown
        }
    },

    runWorkflow(workflowName) {
        // Switch to execute tab and pre-select workflow
        this.switchTab('execute');
        document.getElementById('workflow-select').value = workflowName;
    },

    async deleteWorkflow(workflowName) {
        const confirmed = await Dialog.confirm(
            `Are you sure you want to delete workflow "${workflowName}"?`,
            'Delete Workflow'
        );

        if (!confirmed) return;

        try {
            await this.apiCall(`/workflows/${workflowName}`, { method: 'DELETE' });
            Toast.success(`Workflow "${workflowName}" deleted`);
            this.loadWorkflows();
        } catch (error) {
            // Error already shown
        }
    },

    showCreateWorkflow() {
        document.getElementById('create-workflow-modal').classList.add('active');
    },

    hideCreateWorkflow() {
        document.getElementById('create-workflow-modal').classList.remove('active');
        document.getElementById('create-workflow-form').reset();
    },

    async createWorkflow() {
        const name = document.getElementById('workflow-name').value;
        const description = document.getElementById('workflow-description').value;
        const configYaml = document.getElementById('workflow-config').value;

        // Parse YAML manually (simple approach)
        try {
            // For now, we'll create a simple workflow structure
            // In production, you'd use a YAML parser library
            const steps = this.parseSimpleYaml(configYaml);

            const workflow = {
                name,
                description,
                version: '1.0.0',
                steps
            };

            await this.apiCall('/workflows', {
                method: 'POST',
                body: JSON.stringify(workflow)
            });

            Toast.success(`Workflow "${name}" created successfully!`);
            this.hideCreateWorkflow();
            this.loadWorkflows();
        } catch (error) {
            Toast.error('Failed to create workflow. Check YAML format.');
        }
    },

    parseSimpleYaml(yamlText) {
        // Very simple YAML parser for steps
        // In production, use js-yaml library
        const steps = [];
        const lines = yamlText.split('\n');
        let currentStep = null;

        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('- name:')) {
                if (currentStep) steps.push(currentStep);
                currentStep = { name: trimmed.split(':')[1].trim() };
            } else if (currentStep) {
                if (trimmed.startsWith('agent:')) {
                    currentStep.agent = trimmed.split(':')[1].trim();
                } else if (trimmed.startsWith('input:')) {
                    currentStep.input = trimmed.split(':')[1].trim();
                }
            }
        }
        if (currentStep) steps.push(currentStep);
        return steps;
    },

    // Execute Workflow
    populateWorkflowSelect() {
        const select = document.getElementById('workflow-select');
        select.innerHTML = '<option value="">-- Select a workflow --</option>';

        this.state.workflows.forEach(workflow => {
            const option = document.createElement('option');
            option.value = workflow.name;
            option.textContent = `${workflow.name} (${workflow.steps} steps)`;
            select.appendChild(option);
        });
    },

    async executeWorkflow() {
        const workflowName = document.getElementById('workflow-select').value;
        const input = document.getElementById('workflow-input').value;

        if (!workflowName || !input) {
            Toast.warning('Please select a workflow and provide input');
            return;
        }

        const resultDiv = document.getElementById('execution-result');
        const resultContent = document.getElementById('execution-result-content');

        resultDiv.style.display = 'block';
        resultContent.innerHTML = '<div class="loading">Executing workflow...</div>';

        try {
            const result = await this.apiCall('/workflows/execute', {
                method: 'POST',
                body: JSON.stringify({
                    workflow_name: workflowName,
                    input: input
                })
            });

            this.renderExecutionResult(result.result);
            Toast.success('Workflow executed successfully!');
            this.loadExecutions();
        } catch (error) {
            resultContent.innerHTML = '<div class="alert alert-error">Workflow execution failed</div>';
        }
    },

    renderExecutionResult(execution) {
        const resultContent = document.getElementById('execution-result-content');

        const stepsHTML = execution.step_results.map((step, i) => {
            const statusClass = step.success ? 'success' : 'error';
            return `
                <div class="execution-step ${statusClass}">
                    <strong>${step.step_name || `Step ${i + 1}`}</strong><br>
                    Agent: ${step.agent}<br>
                    Status: ${step.success ? 'Success' : 'Failed'}<br>
                    ${step.success ? `<details><summary>Output</summary><pre>${step.output}</pre></details>` : `Error: ${step.error}`}
                </div>
            `;
        }).join('');

        resultContent.innerHTML = `
            <div class="alert alert-${execution.status === 'completed' ? 'success' : 'error'}">
                <strong>Status:</strong> ${execution.status}<br>
                <strong>Duration:</strong> ${execution.duration_seconds ? execution.duration_seconds.toFixed(2) + 's' : 'N/A'}
            </div>
            <h4>Workflow Steps:</h4>
            ${stepsHTML}
        `;
    },

    // Executions History
    async loadExecutions() {
        const container = document.getElementById('executions-list');
        container.innerHTML = '<div class="loading">Loading execution history...</div>';

        try {
            const data = await this.apiCall('/executions?limit=10');
            this.state.executions = data.executions;
            this.renderExecutions();
        } catch (error) {
            container.innerHTML = '<div class="alert alert-error">Failed to load executions</div>';
        }
    },

    renderExecutions() {
        const container = document.getElementById('executions-list');

        if (this.state.executions.length === 0) {
            container.innerHTML = '<div class="card"><p>No execution history yet</p></div>';
            return;
        }

        const executionsHTML = this.state.executions.map(exec => {
            const statusClass = `status-${exec.status}`;
            return `
                <div class="card execution-card ${statusClass}">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <h3>${exec.workflow_name}</h3>
                            <p><strong>ID:</strong> ${exec.execution_id}</p>
                            <p><strong>Status:</strong> <span class="status-badge ${exec.status}">${exec.status}</span></p>
                        </div>
                        <div style="text-align: right;">
                            <p><strong>${exec.current_step}/${exec.total_steps}</strong> steps</p>
                            ${exec.duration_seconds ? `<p>${exec.duration_seconds.toFixed(2)}s</p>` : ''}
                        </div>
                    </div>
                    ${exec.error ? `<div class="alert alert-error">${exec.error}</div>` : ''}
                    <details style="margin-top: 10px;">
                        <summary>View Steps</summary>
                        <div class="execution-steps">
                            ${exec.step_results.map((step, i) => `
                                <div class="execution-step ${step.success ? 'success' : 'error'}">
                                    <strong>${step.step_name || `Step ${i + 1}`}</strong> - ${step.agent}<br>
                                    ${step.success ? 'Completed' : `Failed: ${step.error}`}
                                </div>
                            `).join('')}
                        </div>
                    </details>
                </div>
            `;
        }).join('');

        container.innerHTML = executionsHTML;
    }
};

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => app.init());
} else {
    app.init();
}
