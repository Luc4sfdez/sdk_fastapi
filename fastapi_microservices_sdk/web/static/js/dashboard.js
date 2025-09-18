/**
 * Enhanced Dashboard JavaScript for FastAPI Microservices SDK
 */

class Dashboard {
    constructor() {
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.services = new Map();
        this.metrics = new Map();
        
        this.init();
    }
    
    init() {
        console.log('Initializing Enhanced Dashboard');
        
        // Initialize WebSocket connection
        this.initWebSocket();
        
        // Load initial data
        this.loadServices();
        this.loadMetrics();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Start periodic updates
        this.startPeriodicUpdates();
    }
    
    initWebSocket() {
        if (!window.WebSocket) {
            console.warn('WebSocket not supported');
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = (event) => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(event);
            };
            
            this.websocket.onclose = (event) => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                this.scheduleReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
        }
    }
    
    handleWebSocketMessage(event) {
        try {
            const message = JSON.parse(event.data);
            
            switch (message.type) {
                case 'service_update':
                    this.handleServiceUpdate(message.data);
                    break;
                case 'metrics_update':
                    this.handleMetricsUpdate(message.data);
                    break;
                case 'alert':
                    this.handleAlert(message.data);
                    break;
                default:
                    console.log('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            
            setTimeout(() => {
                this.initWebSocket();
            }, delay);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }
    
    updateConnectionStatus(connected) {
        const indicator = document.querySelector('.connection-status');
        if (indicator) {
            indicator.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
            indicator.title = connected ? 'Connected' : 'Disconnected';
        }
    }
    
    async loadServices() {
        try {
            const response = await fetch('/api/services');
            if (response.ok) {
                const services = await response.json();
                this.updateServicesDisplay(services);
            }
        } catch (error) {
            console.error('Error loading services:', error);
        }
    }
    
    async loadMetrics() {
        try {
            const response = await fetch('/api/metrics/system');
            if (response.ok) {
                const metrics = await response.json();
                this.updateMetricsDisplay(metrics);
            }
        } catch (error) {
            console.error('Error loading metrics:', error);
        }
    }
    
    updateServicesDisplay(services) {
        const container = document.querySelector('#services-container');
        if (!container) return;
        
        // Store services data
        services.forEach(service => {
            this.services.set(service.id, service);
        });
        
        // Update display
        container.innerHTML = services.map(service => this.createServiceCard(service)).join('');
        
        // Setup service action handlers
        this.setupServiceActions();
    }
    
    createServiceCard(service) {
        const statusClass = `status-${service.status.toLowerCase()}`;
        const healthClass = `health-${service.health_status.toLowerCase()}`;
        
        return `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card service-card" data-service-id="${service.id}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h5 class="card-title">${service.name}</h5>
                            <span class="status-indicator ${statusClass}" title="${service.status}"></span>
                        </div>
                        <p class="card-text text-muted">${service.template_type}</p>
                        <div class="row text-center">
                            <div class="col">
                                <small class="text-muted">Port</small>
                                <div class="fw-bold">${service.port}</div>
                            </div>
                            <div class="col">
                                <small class="text-muted">CPU</small>
                                <div class="fw-bold">${service.resource_usage.cpu_percent.toFixed(1)}%</div>
                            </div>
                            <div class="col">
                                <small class="text-muted">Memory</small>
                                <div class="fw-bold">${(service.resource_usage.memory_mb / 1024).toFixed(1)}GB</div>
                            </div>
                        </div>
                        <div class="mt-3">
                            <div class="btn-group w-100" role="group">
                                <button class="btn btn-sm btn-outline-primary service-action" 
                                        data-action="view" data-service-id="${service.id}">
                                    View
                                </button>
                                <button class="btn btn-sm btn-outline-success service-action" 
                                        data-action="start" data-service-id="${service.id}"
                                        ${service.status === 'running' ? 'disabled' : ''}>
                                    Start
                                </button>
                                <button class="btn btn-sm btn-outline-warning service-action" 
                                        data-action="stop" data-service-id="${service.id}"
                                        ${service.status === 'stopped' ? 'disabled' : ''}>
                                    Stop
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateMetricsDisplay(metrics) {
        // Update system metrics cards
        this.updateMetricCard('total-services', metrics.total_services || 0);
        this.updateMetricCard('running-services', metrics.running_services || 0);
        this.updateMetricCard('cpu-usage', `${(metrics.total_cpu_usage || 0).toFixed(1)}%`);
        this.updateMetricCard('memory-usage', `${(metrics.total_memory_usage || 0).toFixed(1)}%`);
    }
    
    updateMetricCard(cardId, value) {
        const card = document.querySelector(`#${cardId} .metric-value`);
        if (card) {
            card.textContent = value;
        }
    }
    
    setupServiceActions() {
        document.querySelectorAll('.service-action').forEach(button => {
            button.addEventListener('click', async (e) => {
                const action = e.target.dataset.action;
                const serviceId = e.target.dataset.serviceId;
                
                await this.handleServiceAction(action, serviceId);
            });
        });
    }
    
    async handleServiceAction(action, serviceId) {
        try {
            let endpoint = '';
            let method = 'POST';
            
            switch (action) {
                case 'start':
                    endpoint = `/api/services/${serviceId}/start`;
                    break;
                case 'stop':
                    endpoint = `/api/services/${serviceId}/stop`;
                    break;
                case 'restart':
                    endpoint = `/api/services/${serviceId}/restart`;
                    break;
                case 'view':
                    window.location.href = `/services/${serviceId}`;
                    return;
                default:
                    console.warn('Unknown action:', action);
                    return;
            }
            
            const response = await fetch(endpoint, { method });
            
            if (response.ok) {
                this.showNotification(`Service ${action} initiated successfully`, 'success');
                // Reload services to update status
                setTimeout(() => this.loadServices(), 1000);
            } else {
                this.showNotification(`Failed to ${action} service`, 'error');
            }
            
        } catch (error) {
            console.error(`Error performing ${action} on service ${serviceId}:`, error);
            this.showNotification(`Error: ${error.message}`, 'error');
        }
    }
    
    handleServiceUpdate(data) {
        // Update service in local storage
        this.services.set(data.service_id, data);
        
        // Update service card if visible
        const card = document.querySelector(`[data-service-id="${data.service_id}"]`);
        if (card) {
            // Update status indicator
            const indicator = card.querySelector('.status-indicator');
            if (indicator) {
                indicator.className = `status-indicator status-${data.status.toLowerCase()}`;
                indicator.title = data.status;
            }
            
            // Update action buttons
            const startBtn = card.querySelector('[data-action="start"]');
            const stopBtn = card.querySelector('[data-action="stop"]');
            
            if (startBtn) startBtn.disabled = data.status === 'running';
            if (stopBtn) stopBtn.disabled = data.status === 'stopped';
        }
    }
    
    handleMetricsUpdate(data) {
        this.updateMetricsDisplay(data);
    }
    
    handleAlert(data) {
        this.showNotification(data.message, data.severity);
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
    
    setupEventListeners() {
        // Refresh button
        document.addEventListener('click', (e) => {
            if (e.target.matches('.refresh-btn')) {
                this.loadServices();
                this.loadMetrics();
            }
        });
        
        // Search functionality
        const searchInput = document.querySelector('#service-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterServices(e.target.value);
            });
        }
    }
    
    filterServices(query) {
        const cards = document.querySelectorAll('.service-card');
        const lowerQuery = query.toLowerCase();
        
        cards.forEach(card => {
            const serviceName = card.querySelector('.card-title').textContent.toLowerCase();
            const serviceType = card.querySelector('.card-text').textContent.toLowerCase();
            
            const matches = serviceName.includes(lowerQuery) || serviceType.includes(lowerQuery);
            card.parentElement.style.display = matches ? 'block' : 'none';
        });
    }
    
    startPeriodicUpdates() {
        // Update services every 30 seconds
        setInterval(() => {
            if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                this.loadServices();
            }
        }, 30000);
        
        // Update metrics every 10 seconds
        setInterval(() => {
            if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                this.loadMetrics();
            }
        }, 10000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});