/**
 * API Documentation & Testing Interface JavaScript
 * Provides interactive functionality for API documentation and testing
 */

class APIDocsInterface {
    constructor() {
        this.currentService = null;
        this.currentEndpoint = null;
        this.services = [];
        this.endpoints = {};
        this.savedRequests = {};
        this.testHistory = [];
        this.charts = {};
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.setupTabs();
        this.setupThemes();
        await this.loadInitialData();
        this.updateStatistics();
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Service selection
        document.getElementById('service-selector').addEventListener('change', (e) => {
            this.loadServiceDocumentation(e.target.value);
        });

        // Testing interface
        document.getElementById('test-service').addEventListener('change', (e) => {
            this.loadServiceEndpoints(e.target.value);
        });

        document.getElementById('test-endpoint').addEventListener('change', (e) => {
            this.selectEndpoint(e.target.value);
        });

        // Request controls
        document.getElementById('send-request').addEventListener('click', () => {
            this.sendRequest();
        });

        document.getElementById('save-request').addEventListener('click', () => {
            this.showSaveRequestModal();
        });

        document.getElementById('clear-form').addEventListener('click', () => {
            this.clearRequestForm();
        });

        // Headers management
        document.querySelector('.add-header').addEventListener('click', () => {
            this.addHeaderRow();
        });

        // Body type selection
        document.getElementById('body-type').addEventListener('change', (e) => {
            this.updateBodyEditor(e.target.value);
        });

        // Swagger UI
        document.getElementById('swagger-service').addEventListener('change', (e) => {
            this.loadSwaggerUI(e.target.value);
        });

        // Modal controls
        document.getElementById('save-request-confirm').addEventListener('click', () => {
            this.saveRequest();
        });

        document.getElementById('save-request-cancel').addEventListener('click', () => {
            this.hideSaveRequestModal();
        });

        document.querySelector('.modal-close').addEventListener('click', () => {
            this.hideSaveRequestModal();
        });

        // Search and filters
        document.getElementById('service-search').addEventListener('input', (e) => {
            this.filterServices(e.target.value);
        });

        document.getElementById('endpoint-search').addEventListener('input', (e) => {
            this.searchEndpoints(e.target.value);
        });

        // Method filters
        document.querySelectorAll('[id^="filter-"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.applyEndpointFilters();
            });
        });

        // Refresh documentation
        document.getElementById('refresh-docs').addEventListener('click', () => {
            this.refreshDocumentation();
        });

        // Export documentation
        document.getElementById('export-docs').addEventListener('click', () => {
            this.exportDocumentation();
        });

        // Clear saved requests
        document.getElementById('clear-saved').addEventListener('click', () => {
            this.clearSavedRequests();
        });

        // Clear test history
        document.getElementById('clear-history').addEventListener('click', () => {
            this.clearTestHistory();
        });
    }

    setupTabs() {
        // Initialize first tab as active
        this.switchTab('documentation');
    }

    setupThemes() {
        const themeSelect = document.getElementById('theme-select');
        themeSelect.addEventListener('change', (e) => {
            this.applyTheme(e.target.value);
        });
    }

    switchTab(tabName) {
        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // Remove active class from all tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        // Show selected tab content
        document.getElementById(`${tabName}-tab`).classList.add('active');
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Load tab-specific data
        if (tabName === 'statistics') {
            this.updateStatistics();
            this.updateCharts();
        }
    }

    applyTheme(themeName) {
        document.body.className = document.body.className.replace(/theme-\w+/g, '');
        if (themeName !== 'default') {
            document.body.classList.add(`theme-${themeName}`);
        }
        
        // Save theme preference
        localStorage.setItem('api-docs-theme', themeName);
    }

    async loadInitialData() {
        this.showLoading();
        
        try {
            // Load services
            await this.loadServices();
            
            // Load saved requests
            await this.loadSavedRequests();
            
            // Load test history
            await this.loadTestHistory();
            
            // Apply saved theme
            const savedTheme = localStorage.getItem('api-docs-theme') || 'default';
            document.getElementById('theme-select').value = savedTheme;
            this.applyTheme(savedTheme);
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('Failed to load initial data');
        } finally {
            this.hideLoading();
        }
    }

    async loadServices() {
        try {
            const response = await fetch('/api/docs/services');
            if (!response.ok) throw new Error('Failed to load services');
            
            this.services = await response.json();
            this.populateServiceSelectors();
            this.renderServiceList();
            
        } catch (error) {
            console.error('Failed to load services:', error);
            throw error;
        }
    }

    populateServiceSelectors() {
        const selectors = [
            'service-selector',
            'test-service',
            'swagger-service'
        ];

        selectors.forEach(selectorId => {
            const select = document.getElementById(selectorId);
            select.innerHTML = '<option value="">Select a service...</option>';
            
            this.services.forEach(service => {
                const option = document.createElement('option');
                option.value = service.service_name;
                option.textContent = `${service.title} (${service.version})`;
                select.appendChild(option);
            });
        });

        // Also populate history filter
        const historyFilter = document.getElementById('history-filter');
        historyFilter.innerHTML = '<option value="all">All Services</option>';
        this.services.forEach(service => {
            const option = document.createElement('option');
            option.value = service.service_name;
            option.textContent = service.title;
            historyFilter.appendChild(option);
        });
    }

    renderServiceList() {
        const serviceList = document.getElementById('service-list');
        serviceList.innerHTML = '';

        this.services.forEach(service => {
            const serviceItem = document.createElement('div');
            serviceItem.className = 'service-item';
            serviceItem.dataset.serviceName = service.service_name;
            
            serviceItem.innerHTML = `
                <span class="service-name">${service.title}</span>
                <span class="service-status">Status: ${service.status}</span>
            `;
            
            serviceItem.addEventListener('click', () => {
                this.selectService(service.service_name);
            });
            
            serviceList.appendChild(serviceItem);
        });
    }

    selectService(serviceName) {
        // Update UI
        document.querySelectorAll('.service-item').forEach(item => {
            item.classList.remove('active');
        });
        
        document.querySelector(`[data-service-name="${serviceName}"]`).classList.add('active');
        
        // Update selectors
        document.getElementById('service-selector').value = serviceName;
        document.getElementById('test-service').value = serviceName;
        
        // Load service data
        this.loadServiceDocumentation(serviceName);
        this.loadServiceEndpoints(serviceName);
    }

    async loadServiceDocumentation(serviceName) {
        if (!serviceName) {
            document.getElementById('documentation-content').innerHTML = `
                <div class="welcome-message">
                    <i class="fas fa-info-circle"></i>
                    <h3>Welcome to API Documentation</h3>
                    <p>Select a service from the dropdown to view its documentation.</p>
                </div>
            `;
            return;
        }

        this.showLoading();
        
        try {
            const response = await fetch(`/api/docs/services/${serviceName}/documentation`);
            if (!response.ok) throw new Error('Failed to load documentation');
            
            const documentation = await response.text();
            document.getElementById('documentation-content').innerHTML = documentation;
            
        } catch (error) {
            console.error('Failed to load documentation:', error);
            document.getElementById('documentation-content').innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Error Loading Documentation</h3>
                    <p>Failed to load documentation for ${serviceName}</p>
                </div>
            `;
        } finally {
            this.hideLoading();
        }
    }

    async loadServiceEndpoints(serviceName) {
        if (!serviceName) {
            document.getElementById('test-endpoint').innerHTML = '<option value="">Select endpoint...</option>';
            return;
        }

        try {
            const response = await fetch(`/api/docs/services/${serviceName}/endpoints`);
            if (!response.ok) throw new Error('Failed to load endpoints');
            
            const endpoints = await response.json();
            this.endpoints[serviceName] = endpoints;
            
            const endpointSelect = document.getElementById('test-endpoint');
            endpointSelect.innerHTML = '<option value="">Select endpoint...</option>';
            
            endpoints.forEach((endpoint, index) => {
                const option = document.createElement('option');
                option.value = index;
                option.textContent = `${endpoint.method} ${endpoint.path} - ${endpoint.summary}`;
                endpointSelect.appendChild(option);
            });
            
        } catch (error) {
            console.error('Failed to load endpoints:', error);
        }
    }

    selectEndpoint(endpointIndex) {
        const serviceName = document.getElementById('test-service').value;
        if (!serviceName || !this.endpoints[serviceName]) return;

        const endpoint = this.endpoints[serviceName][endpointIndex];
        if (!endpoint) return;

        this.currentEndpoint = endpoint;
        this.updateRequestForm(endpoint);
    }

    updateRequestForm(endpoint) {
        // Update method and URL
        document.getElementById('request-method').textContent = endpoint.method;
        document.getElementById('request-method').className = `method-badge method-${endpoint.method.toLowerCase()}`;
        
        const service = this.services.find(s => s.service_name === endpoint.service_name);
        const fullUrl = `${service.base_url}${endpoint.path}`;
        document.getElementById('request-url').value = fullUrl;

        // Generate parameters
        this.generateParameterInputs(endpoint.parameters);

        // Clear body if not applicable
        if (!['POST', 'PUT', 'PATCH'].includes(endpoint.method)) {
            document.getElementById('body-type').value = 'none';
            this.updateBodyEditor('none');
        }
    }

    generateParameterInputs(parameters) {
        const container = document.getElementById('parameters-container');
        container.innerHTML = '';

        if (!parameters || parameters.length === 0) {
            container.innerHTML = '<p class="no-parameters">No parameters required</p>';
            return;
        }

        parameters.forEach(param => {
            const paramRow = document.createElement('div');
            paramRow.className = 'parameter-row';
            
            const required = param.required ? '<span class="parameter-required">*</span>' : '';
            const paramType = param.schema?.type || 'string';
            
            paramRow.innerHTML = `
                <label>${param.name}${required}</label>
                <input type="text" 
                       name="param-${param.name}" 
                       placeholder="${param.description || `Enter ${param.name}`}"
                       data-type="${paramType}"
                       data-required="${param.required || false}">
                <span class="parameter-info">${paramType} (${param.in})</span>
            `;
            
            container.appendChild(paramRow);
        });
    }

    addHeaderRow() {
        const container = document.getElementById('headers-container');
        const headerRow = document.createElement('div');
        headerRow.className = 'header-row';
        
        headerRow.innerHTML = `
            <input type="text" placeholder="Header name" class="header-name">
            <input type="text" placeholder="Header value" class="header-value">
            <button type="button" class="btn btn-sm btn-outline remove-header">
                <i class="fas fa-minus"></i>
            </button>
        `;
        
        // Add remove functionality
        headerRow.querySelector('.remove-header').addEventListener('click', () => {
            headerRow.remove();
        });
        
        container.appendChild(headerRow);
    }

    updateBodyEditor(bodyType) {
        const container = document.getElementById('body-container');
        
        switch (bodyType) {
            case 'none':
                container.innerHTML = '<p class="no-body">No request body</p>';
                break;
            case 'json':
                container.innerHTML = `
                    <textarea id="request-body" 
                              placeholder='{"key": "value"}'
                              data-language="json"></textarea>
                `;
                break;
            case 'form':
                container.innerHTML = `
                    <div id="form-data-container">
                        <div class="form-data-row">
                            <input type="text" placeholder="Key" class="form-key">
                            <input type="text" placeholder="Value" class="form-value">
                            <button type="button" class="btn btn-sm btn-outline add-form-data">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                    </div>
                `;
                break;
            case 'text':
                container.innerHTML = `
                    <textarea id="request-body" 
                              placeholder="Raw text content"></textarea>
                `;
                break;
        }
    }

    async sendRequest() {
        const serviceName = document.getElementById('test-service').value;
        const endpointIndex = document.getElementById('test-endpoint').value;
        
        if (!serviceName || !endpointIndex || !this.currentEndpoint) {
            this.showError('Please select a service and endpoint');
            return;
        }

        this.showLoading();

        try {
            // Collect parameters
            const parameters = {};
            document.querySelectorAll('[name^="param-"]').forEach(input => {
                const paramName = input.name.replace('param-', '');
                if (input.value) {
                    parameters[paramName] = input.value;
                }
            });

            // Collect headers
            const headers = {};
            document.querySelectorAll('.header-row').forEach(row => {
                const nameInput = row.querySelector('.header-name');
                const valueInput = row.querySelector('.header-value');
                if (nameInput.value && valueInput.value) {
                    headers[nameInput.value] = valueInput.value;
                }
            });

            // Collect body
            let body = null;
            const bodyType = document.getElementById('body-type').value;
            if (bodyType === 'json') {
                const bodyText = document.getElementById('request-body').value;
                if (bodyText) {
                    try {
                        body = JSON.parse(bodyText);
                    } catch (e) {
                        throw new Error('Invalid JSON in request body');
                    }
                }
            } else if (bodyType === 'text') {
                body = document.getElementById('request-body').value;
            }

            // Send request
            const response = await fetch('/api/docs/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    service_name: serviceName,
                    endpoint_path: this.currentEndpoint.path,
                    method: this.currentEndpoint.method,
                    parameters,
                    headers,
                    body
                })
            });

            if (!response.ok) throw new Error('Request failed');

            const result = await response.json();
            this.displayResponse(result);
            
            // Add to history
            this.addToHistory(result);
            
        } catch (error) {
            console.error('Request failed:', error);
            this.showError(error.message);
        } finally {
            this.hideLoading();
        }
    }

    displayResponse(response) {
        const container = document.getElementById('response-container');
        
        let statusClass = 'status-success';
        if (response.status_code >= 400) {
            statusClass = 'status-error';
        } else if (response.status_code >= 300) {
            statusClass = 'status-warning';
        }

        let bodyContent = '';
        if (response.body) {
            if (typeof response.body === 'object') {
                bodyContent = JSON.stringify(response.body, null, 2);
            } else {
                bodyContent = response.body;
            }
        }

        container.innerHTML = `
            <div class="response-info">
                <div class="response-status">
                    <span class="status-code ${statusClass}">${response.status_code}</span>
                    <span class="status-text">${this.getStatusText(response.status_code)}</span>
                </div>
                <div class="response-time">${response.response_time.toFixed(2)}ms</div>
            </div>
            
            <div class="response-headers">
                <h5><i class="fas fa-tags"></i> Response Headers</h5>
                <pre><code class="language-json">${JSON.stringify(response.headers, null, 2)}</code></pre>
            </div>
            
            <div class="response-body">
                <h5><i class="fas fa-file-code"></i> Response Body</h5>
                <pre><code class="language-json">${bodyContent}</code></pre>
            </div>
        `;

        // Highlight syntax
        Prism.highlightAll();
    }

    getStatusText(statusCode) {
        const statusTexts = {
            200: 'OK',
            201: 'Created',
            204: 'No Content',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            500: 'Internal Server Error'
        };
        return statusTexts[statusCode] || 'Unknown';
    }

    showSaveRequestModal() {
        document.getElementById('save-request-modal').style.display = 'block';
    }

    hideSaveRequestModal() {
        document.getElementById('save-request-modal').style.display = 'none';
        // Clear form
        document.getElementById('request-name').value = '';
        document.getElementById('request-tags').value = '';
        document.getElementById('request-notes').value = '';
    }

    async saveRequest() {
        const name = document.getElementById('request-name').value;
        if (!name) {
            this.showError('Please enter a request name');
            return;
        }

        const serviceName = document.getElementById('test-service').value;
        if (!serviceName || !this.currentEndpoint) {
            this.showError('Please select a service and endpoint');
            return;
        }

        try {
            // Collect current request data
            const parameters = {};
            document.querySelectorAll('[name^="param-"]').forEach(input => {
                const paramName = input.name.replace('param-', '');
                if (input.value) {
                    parameters[paramName] = input.value;
                }
            });

            const headers = {};
            document.querySelectorAll('.header-row').forEach(row => {
                const nameInput = row.querySelector('.header-name');
                const valueInput = row.querySelector('.header-value');
                if (nameInput.value && valueInput.value) {
                    headers[nameInput.value] = valueInput.value;
                }
            });

            let body = null;
            const bodyType = document.getElementById('body-type').value;
            if (bodyType === 'json') {
                const bodyText = document.getElementById('request-body').value;
                if (bodyText) {
                    body = JSON.parse(bodyText);
                }
            }

            const requestData = {
                name,
                service_name: serviceName,
                endpoint_path: this.currentEndpoint.path,
                method: this.currentEndpoint.method,
                parameters,
                headers,
                body,
                tags: document.getElementById('request-tags').value.split(',').map(t => t.trim()).filter(t => t),
                notes: document.getElementById('request-notes').value
            };

            const response = await fetch('/api/docs/requests', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) throw new Error('Failed to save request');

            this.hideSaveRequestModal();
            this.loadSavedRequests();
            this.showSuccess('Request saved successfully');

        } catch (error) {
            console.error('Failed to save request:', error);
            this.showError('Failed to save request');
        }
    }

    async loadSavedRequests() {
        try {
            const response = await fetch('/api/docs/requests');
            if (!response.ok) throw new Error('Failed to load saved requests');
            
            this.savedRequests = await response.json();
            this.renderSavedRequests();
            
        } catch (error) {
            console.error('Failed to load saved requests:', error);
        }
    }

    renderSavedRequests() {
        const container = document.getElementById('saved-requests');
        container.innerHTML = '';

        Object.entries(this.savedRequests).forEach(([name, request]) => {
            const requestItem = document.createElement('div');
            requestItem.className = 'saved-request-item';
            
            requestItem.innerHTML = `
                <div class="request-name">${name}</div>
                <div class="request-details">${request.method} ${request.endpoint_path}</div>
            `;
            
            requestItem.addEventListener('click', () => {
                this.loadSavedRequest(name);
            });
            
            container.appendChild(requestItem);
        });
    }

    async loadSavedRequest(name) {
        const request = this.savedRequests[name];
        if (!request) return;

        // Set service and endpoint
        document.getElementById('test-service').value = request.service_name;
        await this.loadServiceEndpoints(request.service_name);
        
        // Find and select endpoint
        const endpoints = this.endpoints[request.service_name];
        const endpointIndex = endpoints.findIndex(ep => 
            ep.path === request.endpoint_path && ep.method === request.method
        );
        
        if (endpointIndex >= 0) {
            document.getElementById('test-endpoint').value = endpointIndex;
            this.selectEndpoint(endpointIndex);
            
            // Populate form with saved data
            setTimeout(() => {
                // Set parameters
                Object.entries(request.parameters || {}).forEach(([name, value]) => {
                    const input = document.querySelector(`[name="param-${name}"]`);
                    if (input) input.value = value;
                });

                // Set headers
                Object.entries(request.headers || {}).forEach(([name, value]) => {
                    this.addHeaderRow();
                    const headerRows = document.querySelectorAll('.header-row');
                    const lastRow = headerRows[headerRows.length - 1];
                    lastRow.querySelector('.header-name').value = name;
                    lastRow.querySelector('.header-value').value = value;
                });

                // Set body
                if (request.body) {
                    document.getElementById('body-type').value = 'json';
                    this.updateBodyEditor('json');
                    setTimeout(() => {
                        document.getElementById('request-body').value = JSON.stringify(request.body, null, 2);
                    }, 100);
                }
            }, 100);
        }

        // Switch to testing tab
        this.switchTab('testing');
    }

    clearRequestForm() {
        document.getElementById('test-service').value = '';
        document.getElementById('test-endpoint').value = '';
        document.getElementById('request-method').textContent = 'GET';
        document.getElementById('request-url').value = '';
        document.getElementById('parameters-container').innerHTML = '';
        document.getElementById('headers-container').innerHTML = `
            <div class="header-row">
                <input type="text" placeholder="Header name" class="header-name">
                <input type="text" placeholder="Header value" class="header-value">
                <button type="button" class="btn btn-sm btn-outline add-header">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
        `;
        document.getElementById('body-type').value = 'none';
        this.updateBodyEditor('none');
        
        // Clear response
        document.getElementById('response-container').innerHTML = `
            <div class="no-response">
                <i class="fas fa-info-circle"></i>
                <p>No response yet. Send a request to see the response here.</p>
            </div>
        `;
    }

    async loadTestHistory() {
        try {
            const response = await fetch('/api/docs/history');
            if (!response.ok) throw new Error('Failed to load test history');
            
            this.testHistory = await response.json();
            this.renderTestHistory();
            
        } catch (error) {
            console.error('Failed to load test history:', error);
        }
    }

    renderTestHistory() {
        const container = document.getElementById('test-history');
        container.innerHTML = '';

        this.testHistory.slice(0, 10).forEach(test => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            
            const statusClass = test.response.status_code >= 400 ? 'status-error' : 'status-success';
            
            historyItem.innerHTML = `
                <div class="test-info">
                    <div class="test-endpoint">${test.request.endpoint.method} ${test.request.endpoint.path}</div>
                    <div class="test-service">${test.request.endpoint.service_name}</div>
                </div>
                <div class="test-result">
                    <span class="status-code ${statusClass}">${test.response.status_code}</span>
                    <span class="test-time">${new Date(test.timestamp).toLocaleTimeString()}</span>
                </div>
            `;
            
            container.appendChild(historyItem);
        });
    }

    addToHistory(response) {
        this.testHistory.unshift({
            timestamp: new Date().toISOString(),
            request: {
                endpoint: this.currentEndpoint
            },
            response: response
        });
        
        this.renderTestHistory();
        this.updateStatistics();
    }

    async loadSwaggerUI(serviceName) {
        if (!serviceName) {
            document.getElementById('swagger-container').innerHTML = `
                <div class="swagger-placeholder">
                    <i class="fas fa-code"></i>
                    <h3>Swagger UI</h3>
                    <p>Select a service to view its Swagger UI documentation.</p>
                </div>
            `;
            return;
        }

        this.showLoading();
        
        try {
            const response = await fetch(`/api/docs/services/${serviceName}/swagger`);
            if (!response.ok) throw new Error('Failed to load Swagger UI');
            
            const swaggerHTML = await response.text();
            document.getElementById('swagger-container').innerHTML = swaggerHTML;
            
        } catch (error) {
            console.error('Failed to load Swagger UI:', error);
            document.getElementById('swagger-container').innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Error Loading Swagger UI</h3>
                    <p>Failed to load Swagger UI for ${serviceName}</p>
                </div>
            `;
        } finally {
            this.hideLoading();
        }
    }

    async updateStatistics() {
        try {
            const [docsStats, testStats] = await Promise.all([
                fetch('/api/docs/statistics').then(r => r.json()),
                fetch('/api/docs/test-statistics').then(r => r.json())
            ]);

            // Update stat cards
            document.getElementById('total-services').textContent = docsStats.total_services || 0;
            document.getElementById('total-endpoints').textContent = docsStats.total_endpoints || 0;
            document.getElementById('total-tests').textContent = testStats.total_tests || 0;
            document.getElementById('success-rate').textContent = `${Math.round(testStats.success_rate * 100)}%`;

            // Update recent tests
            this.renderRecentTests(testStats);

        } catch (error) {
            console.error('Failed to update statistics:', error);
        }
    }

    renderRecentTests(testStats) {
        const container = document.getElementById('recent-tests');
        container.innerHTML = '';

        if (!this.testHistory.length) {
            container.innerHTML = '<p>No recent tests</p>';
            return;
        }

        this.testHistory.slice(0, 5).forEach(test => {
            const testItem = document.createElement('div');
            testItem.className = 'recent-test-item';
            
            const statusClass = test.response.status_code >= 400 ? 'status-error' : 'status-success';
            
            testItem.innerHTML = `
                <div class="test-info">
                    <div class="test-endpoint">${test.request.endpoint.method} ${test.request.endpoint.path}</div>
                    <div class="test-service">${test.request.endpoint.service_name}</div>
                </div>
                <div class="test-result">
                    <span class="status-code ${statusClass}">${test.response.status_code}</span>
                    <span class="response-time">${test.response.response_time.toFixed(2)}ms</span>
                </div>
            `;
            
            container.appendChild(testItem);
        });
    }

    updateCharts() {
        this.updateTestsByServiceChart();
        this.updateStatusCodesChart();
    }

    updateTestsByServiceChart() {
        const ctx = document.getElementById('tests-by-service-chart').getContext('2d');
        
        if (this.charts.testsByService) {
            this.charts.testsByService.destroy();
        }

        const serviceData = {};
        this.testHistory.forEach(test => {
            const service = test.request.endpoint.service_name;
            serviceData[service] = (serviceData[service] || 0) + 1;
        });

        this.charts.testsByService = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(serviceData),
                datasets: [{
                    data: Object.values(serviceData),
                    backgroundColor: [
                        '#667eea',
                        '#764ba2',
                        '#f093fb',
                        '#f5576c',
                        '#4facfe',
                        '#00f2fe'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    updateStatusCodesChart() {
        const ctx = document.getElementById('status-codes-chart').getContext('2d');
        
        if (this.charts.statusCodes) {
            this.charts.statusCodes.destroy();
        }

        const statusData = {};
        this.testHistory.forEach(test => {
            const status = test.response.status_code;
            statusData[status] = (statusData[status] || 0) + 1;
        });

        this.charts.statusCodes = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(statusData),
                datasets: [{
                    label: 'Count',
                    data: Object.values(statusData),
                    backgroundColor: '#667eea'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Search and Filter Methods
    filterServices(query) {
        const serviceItems = document.querySelectorAll('.service-item');
        const searchTerm = query.toLowerCase();

        serviceItems.forEach(item => {
            const serviceName = item.querySelector('.service-name').textContent.toLowerCase();
            if (serviceName.includes(searchTerm)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }

    searchEndpoints(query) {
        // This would search through endpoints in the current service
        // Implementation depends on how endpoints are displayed
        console.log('Searching endpoints for:', query);
    }

    applyEndpointFilters() {
        const filters = {
            get: document.getElementById('filter-get').checked,
            post: document.getElementById('filter-post').checked,
            put: document.getElementById('filter-put').checked,
            delete: document.getElementById('filter-delete').checked
        };

        // Apply filters to endpoint display
        console.log('Applying endpoint filters:', filters);
    }

    // Utility Methods
    async refreshDocumentation() {
        this.showLoading();
        try {
            const response = await fetch('/api/docs/refresh', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to refresh documentation');
            
            await this.loadServices();
            this.showSuccess('Documentation refreshed successfully');
        } catch (error) {
            console.error('Failed to refresh documentation:', error);
            this.showError('Failed to refresh documentation');
        } finally {
            this.hideLoading();
        }
    }

    async exportDocumentation() {
        const serviceName = document.getElementById('service-selector').value;
        if (!serviceName) {
            this.showError('Please select a service to export');
            return;
        }

        try {
            const response = await fetch(`/api/docs/services/${serviceName}/export`);
            if (!response.ok) throw new Error('Failed to export documentation');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${serviceName}-documentation.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showSuccess('Documentation exported successfully');
        } catch (error) {
            console.error('Failed to export documentation:', error);
            this.showError('Failed to export documentation');
        }
    }

    async clearSavedRequests() {
        if (!confirm('Are you sure you want to clear all saved requests?')) {
            return;
        }

        try {
            const response = await fetch('/api/docs/requests', { method: 'DELETE' });
            if (!response.ok) throw new Error('Failed to clear saved requests');
            
            this.savedRequests = {};
            this.renderSavedRequests();
            this.showSuccess('Saved requests cleared successfully');
        } catch (error) {
            console.error('Failed to clear saved requests:', error);
            this.showError('Failed to clear saved requests');
        }
    }

    async clearTestHistory() {
        if (!confirm('Are you sure you want to clear test history?')) {
            return;
        }

        try {
            const response = await fetch('/api/docs/history', { method: 'DELETE' });
            if (!response.ok) throw new Error('Failed to clear test history');
            
            this.testHistory = [];
            this.renderTestHistory();
            this.updateStatistics();
            this.showSuccess('Test history cleared successfully');
        } catch (error) {
            console.error('Failed to clear test history:', error);
            this.showError('Failed to clear test history');
        }
    }

    // UI Helper Methods
    showLoading() {
        document.getElementById('loading-overlay').style.display = 'block';
    }

    hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
            <span>${message}</span>
            <button class="notification-close">&times;</button>
        `;

        // Add to page
        document.body.appendChild(notification);

        // Add close functionality
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);

        // Add CSS for notifications if not present
        if (!document.querySelector('#notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                .notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 1rem 1.5rem;
                    border-radius: 4px;
                    color: white;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    z-index: 3000;
                    min-width: 300px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                }
                .notification-error { background-color: #dc3545; }
                .notification-success { background-color: #28a745; }
                .notification-info { background-color: #17a2b8; }
                .notification-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 1.2rem;
                    cursor: pointer;
                    margin-left: auto;
                }
            `;
            document.head.appendChild(style);
        }
    }
}

// Initialize the API Docs Interface when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new APIDocsInterface();
});