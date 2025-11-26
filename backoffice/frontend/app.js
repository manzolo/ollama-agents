/**
 * Ollama Agents Backoffice Application
 * Frontend JavaScript
 */

const API_BASE = '/api';

// Theme Management
const ThemeManager = {
    STORAGE_KEY: 'ollama-agents-theme',
    THEMES: {
        LIGHT: 'light',
        DARK: 'dark'
    },

    /**
     * Initialize theme based on saved preference or system preference
     */
    init() {
        const savedTheme = this.getSavedTheme();
        const theme = savedTheme || this.getSystemTheme();
        this.setTheme(theme);
        this.setupToggle();
        this.watchSystemTheme();
    },

    /**
     * Get saved theme from localStorage
     */
    getSavedTheme() {
        return localStorage.getItem(this.STORAGE_KEY);
    },

    /**
     * Get system theme preference
     */
    getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return this.THEMES.DARK;
        }
        return this.THEMES.LIGHT;
    },

    /**
     * Set theme
     */
    setTheme(theme) {
        const root = document.documentElement;
        const icon = document.getElementById('theme-icon');

        if (theme === this.THEMES.DARK) {
            root.setAttribute('data-theme', 'dark');
            if (icon) icon.textContent = '☀️';
        } else {
            root.setAttribute('data-theme', 'light');
            if (icon) icon.textContent = '🌙';
        }

        localStorage.setItem(this.STORAGE_KEY, theme);
    },

    /**
     * Toggle theme
     */
    toggle() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? this.THEMES.LIGHT : this.THEMES.DARK;
        this.setTheme(newTheme);
    },

    /**
     * Setup toggle button
     */
    setupToggle() {
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());
        }
    },

    /**
     * Watch for system theme changes
     */
    watchSystemTheme() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                // Only apply system theme if user hasn't manually set a preference
                if (!this.getSavedTheme()) {
                    this.setTheme(e.matches ? this.THEMES.DARK : this.THEMES.LIGHT);
                }
            });
        }
    }
};

// Initialize theme as early as possible
ThemeManager.init();

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
    },

    alert(message, title = 'Alert') {
        return new Promise((resolve) => {
            const dialog = document.getElementById('confirm-dialog');
            const titleEl = document.getElementById('confirm-title');
            const messageEl = document.getElementById('confirm-message');
            const okBtn = document.getElementById('confirm-ok');
            const cancelBtn = document.getElementById('confirm-cancel');

            titleEl.textContent = title;
            // Support HTML content
            if (message.includes('<')) {
                messageEl.innerHTML = message;
            } else {
                messageEl.textContent = message;
            }

            dialog.classList.add('active');

            // Hide cancel button for alert
            cancelBtn.style.display = 'none';

            const cleanup = () => {
                dialog.classList.remove('active');
                cancelBtn.style.display = '';
                okBtn.onclick = null;
                messageEl.innerHTML = '';
            };

            okBtn.onclick = () => {
                cleanup();
                resolve(true);
            };

            // Close on backdrop click
            dialog.onclick = (e) => {
                if (e.target === dialog) {
                    cleanup();
                    resolve(true);
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

    // Store step outputs for copying (indexed by step ID)
    stepOutputs: {},

    // Initialize
    init() {
        //console.log('Initializing Backoffice App...');
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

        // Create agent form
        document.getElementById('create-agent-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.createAgent();
        });

        // Prompt assistant form
        document.getElementById('prompt-assistant-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.generatePrompt();
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
            console.error('Error loading agents:', error);
            container.innerHTML = `<div class="alert alert-error">Failed to load agents: ${error.message}</div>`;
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
                        <div style="margin-top: 15px; display: flex; gap: 8px; flex-wrap: wrap;">
                            <button onclick="app.testAgent('${name}')" class="btn btn-small btn-primary">Test</button>
                            <button onclick="app.restartAgent('${name}')" class="btn btn-small btn-secondary">🔄 Restart</button>
                            <button onclick="app.stopAgent('${name}')" class="btn btn-small btn-secondary">⏹ Stop</button>
                            <button onclick="app.deleteAgent('${name}')" class="btn btn-small btn-danger">🗑 Delete</button>
                        </div>
                    ` : agent.status === 'stopped' ? `
                        <div style="margin-top: 15px; display: flex; gap: 8px; flex-wrap: wrap;">
                            <button onclick="app.startAgent('${name}')" class="btn btn-small btn-success">▶ Start</button>
                            <button onclick="app.deleteAgent('${name}')" class="btn btn-small btn-danger">🗑 Delete</button>
                        </div>
                    ` : agent.status === 'starting' ? `
                        <div style="margin-top: 15px;">
                            <span style="color: var(--warning);">⏳ Starting...</span>
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

            // Show result in a dialog
            const resultHtml = `
                <div style="max-height: 60vh; overflow-y: auto;">
                    <h3 style="margin-top: 0;">Agent Response</h3>
                    <div style="margin-bottom: 15px;">
                        <strong>Agent:</strong> ${agentName}<br>
                        <strong>Status:</strong> <span style="color: #10b981;">Success</span>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Input:</strong>
                        <pre style="background: var(--bg-color); padding: 10px; border-radius: 4px; margin-top: 5px; white-space: pre-wrap; word-wrap: break-word;">${testInput}</pre>
                    </div>
                    <div>
                        <strong>Output:</strong>
                        <pre style="background: var(--bg-color); padding: 10px; border-radius: 4px; margin-top: 5px; white-space: pre-wrap; word-wrap: break-word;">${result.output || JSON.stringify(result, null, 2)}</pre>
                    </div>
                </div>
            `;

            await Dialog.alert(resultHtml, 'Test Result');
            Toast.success(`Agent ${agentName} responded successfully!`);
        } catch (error) {
            // Error already shown by apiCall
        }
    },

    showCreateAgent() {
        document.getElementById('create-agent-modal').classList.add('active');
    },

    hideCreateAgent() {
        document.getElementById('create-agent-modal').classList.remove('active');
        document.getElementById('create-agent-form').reset();
        // Reset temperature display
        document.getElementById('temperature-value').textContent = '0.7';
    },

    async createAgent() {
        const name = document.getElementById('agent-name').value.trim();
        const description = document.getElementById('agent-description').value.trim();
        const port = parseInt(document.getElementById('agent-port').value);
        const model = document.getElementById('agent-model').value;
        const temperature = parseFloat(document.getElementById('agent-temperature').value);
        const maxTokens = parseInt(document.getElementById('agent-max-tokens').value);
        const capabilitiesStr = document.getElementById('agent-capabilities').value.trim();
        const systemPrompt = document.getElementById('agent-prompt').value.trim();

        // Parse capabilities
        const capabilities = capabilitiesStr
            ? capabilitiesStr.split(',').map(c => c.trim()).filter(c => c)
            : [];

        // Validate
        if (!name.match(/^[a-z0-9-]+$/)) {
            Toast.error('Agent name must contain only lowercase letters, numbers, and hyphens');
            return;
        }

        try {
            const result = await this.apiCall('/agents/create', {
                method: 'POST',
                body: JSON.stringify({
                    name,
                    description,
                    port,
                    model,
                    temperature,
                    max_tokens: maxTokens,
                    capabilities,
                    system_prompt: systemPrompt
                })
            });

            Toast.success(`Agent "${name}" definition created successfully!`);
            //console.log('Agent Creation Result:', result);

            // Offer to deploy immediately
            const deployNow = await Dialog.confirm(
                `Agent definition created!\n\nDo you want to deploy it now?`,
                'Deploy Agent'
            );

            if (deployNow) {
                this.hideCreateAgent();
                await this.deployAgentDefinition(name);
            } else {
                this.hideCreateAgent();
            }

            this.loadAgents();
            this.loadAgentDefinitions();
        } catch (error) {
            // Error already shown by apiCall
            console.error('Agent creation failed:', error);
        }
    },

    async loadAgentDefinitions() {
        try {
            const data = await this.apiCall('/agents/definitions');
            this.state.agentDefinitions = data.definitions || [];
            this.renderAgentDefinitions();
        } catch (error) {
            console.error('Failed to load agent definitions:', error);
        }
    },

    renderAgentDefinitions() {
        // This will be called to show pending deployments
        const pending = this.state.agentDefinitions.filter(d => d.status === 'defined');
        if (pending.length > 0) {
            // Could show a notification or section for pending deployments
            console.log(`${pending.length} agent(s) pending deployment`);
        }
    },

    async deployAgentDefinition(agentName) {
        Toast.info(`Deploying ${agentName}... This may take 1-2 minutes.`);

        try {
            const result = await this.apiCall(`/agents/${agentName}/deploy`, {
                method: 'POST'
            });

            if (result.status === 'success') {
                Toast.success(`Agent "${agentName}" deployed successfully!` +
                    (result.gpu_mode ? ' (GPU mode detected)' : ''));
                this.loadAgents();
            } else {
                Toast.warning(`Agent deployed with issues: ${result.message}`);
            }
        } catch (error) {
            console.error('Deployment failed:', error);
        }
    },

    async restartAgent(agentName) {
        const confirmed = await Dialog.confirm(
            `Restart agent "${agentName}"?`,
            'Restart Agent'
        );

        if (!confirmed) return;

        try {
            await this.apiCall(`/agents/${agentName}/restart`, {
                method: 'POST'
            });
            Toast.success(`Agent "${agentName}" restarted successfully!`);
            setTimeout(() => this.loadAgents(), 2000);
        } catch (error) {
            console.error('Restart failed:', error);
        }
    },

    async stopAgent(agentName) {
        const confirmed = await Dialog.confirm(
            `Stop agent "${agentName}"?`,
            'Stop Agent'
        );

        if (!confirmed) return;

        try {
            await this.apiCall(`/agents/${agentName}/stop`, {
                method: 'POST'
            });
            Toast.success(`Agent "${agentName}" stopped successfully!`);
            setTimeout(() => this.loadAgents(), 2000);
        } catch (error) {
            console.error('Stop failed:', error);
        }
    },

    async startAgent(agentName) {
        Toast.info(`Starting agent "${agentName}"...`);

        try {
            const result = await this.apiCall(`/agents/${agentName}/start`, {
                method: 'POST'
            });
            Toast.success(result.message || `Agent "${agentName}" started successfully!`);
            setTimeout(() => this.loadAgents(), 2000);
        } catch (error) {
            console.error('Start failed:', error);
        }
    },

    async deleteAgent(agentName) {
        const confirmed = await Dialog.confirm(
            `⚠️ WARNING: This will permanently delete agent "${agentName}"!\n\nThis will remove:\n- Container\n- Configuration files\n- docker-compose.yml entry\n- Environment variables\n\nAre you absolutely sure?`,
            'Delete Agent'
        );

        if (!confirmed) return;

        Toast.info(`Deleting agent "${agentName}"...`);

        try {
            await this.apiCall(`/agents/${agentName}`, {
                method: 'DELETE'
            });
            Toast.success(`Agent "${agentName}" deleted successfully!`);
            setTimeout(() => this.loadAgents(), 1000);
        } catch (error) {
            console.error('Delete failed:', error);
        }
    },

    // Prompt Assistant Functions
    showPromptAssistant() {
        document.getElementById('prompt-assistant-modal').classList.add('active');
        this.showPromptAssistantForm();
    },

    showPromptAssistantForm() {
        document.getElementById('prompt-assistant-input-view').style.display = 'block';
        document.getElementById('prompt-assistant-result').style.display = 'none';
    },

    hidePromptAssistant() {
        document.getElementById('prompt-assistant-modal').classList.remove('active');
        document.getElementById('prompt-assistant-form').reset();
        this.showPromptAssistantForm();
    },

    async generatePrompt() {
        const purpose = document.getElementById('assistant-purpose').value.trim();
        const expertise = document.getElementById('assistant-expertise').value.trim();
        const inputFormat = document.getElementById('assistant-input').value.trim();
        const outputFormat = document.getElementById('assistant-output').value.trim();

        if (!purpose) {
            Toast.error('Please describe what the agent should do');
            return;
        }

        const inputView = document.getElementById('prompt-assistant-input-view');
        const resultDiv = document.getElementById('prompt-assistant-result');
        const outputPre = document.getElementById('prompt-assistant-output');

        // Hide form and show result view with loading
        inputView.style.display = 'none';
        resultDiv.style.display = 'block';
        outputPre.textContent = 'Generating prompt with AI... This may take 10-30 seconds...';

        try {
            const result = await this.apiCall('/agents/generate-prompt', {
                method: 'POST',
                body: JSON.stringify({
                    agent_purpose: purpose,
                    agent_expertise: expertise,
                    input_format: inputFormat,
                    output_format: outputFormat
                })
            });

            outputPre.textContent = result.generated_prompt;
            Toast.success('Prompt generated successfully!');

            // Store the generated prompt for later use
            this.generatedPrompt = result.generated_prompt;

        } catch (error) {
            outputPre.textContent = 'Failed to generate prompt. Please try again.';
            console.error('Prompt generation failed:', error);
        }
    },

    useGeneratedPrompt() {
        if (this.generatedPrompt) {
            document.getElementById('agent-prompt').value = this.generatedPrompt;
            this.hidePromptAssistant();
            Toast.success('Prompt inserted! You can edit it further if needed.');
        }
    },

    async regeneratePrompt() {
        const outputPre = document.getElementById('prompt-assistant-output');
        outputPre.textContent = 'Regenerating prompt... This may take 10-30 seconds...';
        await this.generatePrompt();
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
            const workflowHtml = this.formatWorkflowForDialog(workflow);
            await Dialog.alert(workflowHtml, `Workflow: ${workflow.name}`);
        } catch (error) {
            // Error already shown
        }
    },

    formatWorkflowForDialog(workflow) {
        const stepsHtml = workflow.steps.map((step, i) => {
            return `
                <div class="workflow-step-detail" style="margin: 10px 0; padding: 12px; background: var(--card-bg); border-radius: 4px; border-left: 3px solid var(--primary-color);">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="background: var(--primary-color); color: white; border-radius: 50%; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">${i + 1}</span>
                        <strong style="font-size: 14px; color: var(--text-color);">${step.name || `Step ${i + 1}`}</strong>
                    </div>
                    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 4px;">
                        <strong>Agent:</strong> <span style="color: var(--primary-color); font-weight: 500;">${step.agent}</span>
                    </div>
                    ${step.input ? `
                        <div style="margin-top: 8px;">
                            <strong style="font-size: 12px; color: var(--text-muted);">Input:</strong>
                            <div style="margin-top: 4px; padding: 8px; background: var(--bg-color); border-radius: 4px; font-size: 12px; color: var(--text-color); border: 1px solid var(--border-color);">
                                ${step.input.length > 200 ? step.input.substring(0, 200) + '...' : step.input}
                            </div>
                        </div>
                    ` : ''}
                    ${step.context_from ? `
                        <div style="margin-top: 4px; font-size: 12px; color: var(--text-muted);">
                            <strong>Uses output from:</strong> ${step.context_from}
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

        return `
            <div style="max-width: 600px;">
                <div class="workflow-info" style="margin-bottom: 16px; padding: 12px; border-radius: 4px; background: var(--card-bg); border-left: 4px solid var(--primary-color);">
                    <div style="font-size: 14px; color: var(--text-muted); margin-bottom: 4px;">
                        <strong>Description:</strong> <span style="color: var(--text-color);">${workflow.description || 'No description'}</span>
                    </div>
                    <div style="font-size: 14px; color: var(--text-muted);">
                        <strong>Version:</strong> ${workflow.version || 'N/A'} | <strong>Steps:</strong> ${workflow.steps.length}
                    </div>
                </div>
                <h4 style="margin: 16px 0 12px 0; font-size: 15px; color: var(--text-color);">Workflow Steps:</h4>
                ${stepsHtml}
            </div>
        `;
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

        // Show loading toast
        Toast.info('Executing workflow...');

        try {
            const result = await this.apiCall('/workflows/execute', {
                method: 'POST',
                body: JSON.stringify({
                    workflow_name: workflowName,
                    input: input
                })
            });

            // Show results in dialog
            const resultHtml = this.formatExecutionResultForDialog(result.result);
            await Dialog.alert(resultHtml, `Workflow Result: ${workflowName}`);

            Toast.success('Workflow executed successfully!');
            this.loadExecutions();
        } catch (error) {
            await Dialog.alert(
                '<div class="alert alert-error">Workflow execution failed. Please check the logs.</div>',
                'Execution Failed'
            );
        }
    },

    formatExecutionResultForDialog(execution) {
        const statusIcon = execution.status === 'completed' ? '✓' : '✗';
        const statusClass = execution.status === 'completed' ? 'success' : 'error';

        // Clear previous step outputs
        this.stepOutputs = {};

        const stepsHTML = execution.step_results.map((step, i) => {
            const stepIcon = step.success ? '✓' : '✗';
            const stepClass = step.success ? 'success' : 'error';
            const stepId = `step-output-${Date.now()}-${i}`;

            // Truncate output if too long for display
            let output = step.output || '';
            const maxLength = 500;
            let displayOutput = output;
            let isTruncated = false;
            if (output.length > maxLength) {
                displayOutput = output.substring(0, maxLength) + '...';
                isTruncated = true;
            }

            // Store full output in the stepOutputs object
            this.stepOutputs[stepId] = output;

            return `
                <div class="workflow-step-result ${stepClass}" style="margin: 10px 0; padding: 12px; border-left: 3px solid var(${step.success ? '--success-color' : '--danger-color'}); background: var(--card-bg); border-radius: 4px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 18px; color: var(${step.success ? '--success-color' : '--danger-color'});">${stepIcon}</span>
                        <strong style="font-size: 14px; color: var(--text-color);">${step.step_name || `Step ${i + 1}`}</strong>
                    </div>
                    <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 4px;">
                        <strong>Agent:</strong> ${step.agent}
                    </div>
                    ${step.success ? `
                        <details style="margin-top: 8px;">
                            <summary style="cursor: pointer; color: var(--primary-color); font-weight: 500;">View Output ${isTruncated ? `(${output.length} chars)` : ''}</summary>
                            <div style="position: relative; margin-top: 8px;">
                                <button onclick="app.copyStepOutput('${stepId}')" class="btn btn-small" style="position: absolute; top: 8px; right: 8px; z-index: 1; font-size: 11px; padding: 4px 8px;">
                                    📋 Copy Full Output
                                </button>
                                <pre id="${stepId}" style="margin: 0; padding: 10px; padding-top: 40px; background: var(--bg-color); border-radius: 4px; font-size: 12px; overflow-x: auto; max-height: 300px; overflow-y: auto; color: var(--text-color); border: 1px solid var(--border-color); white-space: pre-wrap; word-wrap: break-word;">${this.escapeHtml(displayOutput)}</pre>
                                ${isTruncated ? `<small style="color: var(--text-muted); font-style: italic; margin-top: 4px; display: block;">Showing first ${maxLength} characters. Click "Copy Full Output" to get complete text.</small>` : ''}
                            </div>
                        </details>
                    ` : `
                        <div style="margin-top: 8px; padding: 10px; background: var(--bg-color); border-radius: 4px; border: 1px solid var(--danger-color);">
                            <strong style="color: var(--danger-color);">Error:</strong> <span style="color: var(--text-color);">${step.error || 'Unknown error'}</span>
                        </div>
                    `}
                </div>
            `;
        }).join('');

        return `
            <div style="max-width: 600px;">
                <div class="workflow-result-summary" style="margin-bottom: 16px; padding: 12px; border-radius: 4px; background: var(--card-bg); border-left: 4px solid var(${execution.status === 'completed' ? '--success-color' : '--danger-color'});">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 20px; color: var(${execution.status === 'completed' ? '--success-color' : '--danger-color'});">${statusIcon}</span>
                        <strong style="font-size: 16px; color: var(--text-color);">${execution.status === 'completed' ? 'Workflow Completed' : 'Workflow Failed'}</strong>
                    </div>
                    <div style="font-size: 14px; color: var(--text-muted);">
                        <strong>Duration:</strong> ${execution.duration_seconds ? execution.duration_seconds.toFixed(2) + 's' : 'N/A'}
                    </div>
                </div>
                <h4 style="margin: 16px 0 12px 0; font-size: 15px; color: var(--text-color);">Workflow Steps:</h4>
                ${stepsHTML}
            </div>
        `;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    async copyStepOutput(stepId) {
        // Get full output from stored outputs object
        const fullOutput = this.stepOutputs[stepId];

        if (!fullOutput) {
            Toast.error('Output not found');
            return;
        }

        try {
            await navigator.clipboard.writeText(fullOutput);
            Toast.success('Output copied to clipboard!');
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = fullOutput;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                Toast.success('Output copied to clipboard!');
            } catch (err2) {
                Toast.error('Failed to copy to clipboard');
            }
            document.body.removeChild(textArea);
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
