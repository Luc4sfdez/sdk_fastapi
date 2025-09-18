/**
 * System Health Dashboard JavaScript
 * Handles real-time monitoring, charts, and diagnostics
 */

class SystemHealthDashboard {
    constructor() {
        this.charts = {};
        this.updateInterval = null;
        this.websocket = null;
        this.currentTab = 'overview';
        this.alertsData = [];
        this.componentsData = [];
        
        // Initialize dashboard
        this.init();
    }

    async init() {
        try {
            // Setup event listeners
            this.setupEventListeners();
            
            // Initialize tabs
            this.initializeTabs();
            
            // Load initial data
            await this.loadInitialData();
            
            // Setup real-time updates
            this.setupRealTimeUpdates();
            
            // Initialize charts
            this.initializeCharts();
            
            console.log('System Health Dashboard initialized successfully');
        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showNotification('Failed to initialize dashboard', 'error');
        }
    }

    setupEventListeners() {
        // Header actions
        document.getElementById('refresh-all')?.addEventListener('click', () => this.refreshAll());
        document.getElementById('export-report')?.addEventListener('click', () => this.exportReport());
        document.getElementById('run-diagnostics')?.addEventListener('click', () => this.runDiagnostics());

        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Process controls
        document.getElementById('refresh-processes')?.addEventListener('click', () => this.loadTopProcesses());
        document.getElementById('process-sort')?.addEventListener('change', () => this.loadTopProcesses());

        // Health check configuration
        document.getElementById('save-config')?.addEventListener('click', () => this.saveHealthConfig());
        document.getElementById('custom-check-type')?.addEventListener('change', (e) => this.toggleCustomCheckConfig(e.target.value));
        document.getElementById('add-custom-check')?.addEventListener('click', () => this.addCustomHealthCheck());

        // Alert filters
        document.getElementById('alert-status-filter')?.addEventListener('change', () => this.filterAlerts());
        document.getElementById('alert-severity-filter')?.addEventListener('change', () => this.filterAlerts());
        document.getElementById('alert-component-filter')?.addEventListener('change', () => this.filterAlerts());
        document.getElementById('clear-filters')?.addEventListener('click', () => this.clearAlertFilters());

        // Alert actions
        document.getElementById('resolve-selected')?.addEventListener('click', () => this.resolveSelectedAlerts());
        document.getElementById('acknowledge-selected')?.addEventListener('click', () => this.acknowledgeSelectedAlerts());
        document.getElementById('export-alerts')?.addEventListener('click', () => this.exportAlerts());

        // Log controls
        document.getElementById('refresh-logs')?.addEventListener('click', () => this.loadSystemLogs());
        document.getElementById('log-level')?.addEventListener('change', () => this.loadSystemLogs());
        document.getElementById('log-search')?.addEventListener('input', (e) => this.searchLogs(e.target.value));

        // Modal close
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) modal.style.display = 'none';
            });
        });

        // Alert modal actions
        document.getElementById('resolve-alert')?.addEventListener('click', () => this.resolveCurrentAlert());
        document.getElementById('acknowledge-alert')?.addEventListener('click', () => this.acknowledgeCurrentAlert());
    }

    initializeTabs() {
        // Show first tab by default
        this.switchTab('overview');
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`)?.classList.add('active');

        this.currentTab = tabName;

        // Load tab-specific data
        this.loadTabData(tabName);
    }

    async loadTabData(tabName) {
        try {
            switch (tabName) {
                case 'overview':
                    await this.loadOverviewData();
                    break;
                case 'resources':
                    await this.loadResourcesData();
                    break;
                case 'components':
                    await this.loadComponentsData();
                    break;
                case 'alerts':
                    await this.loadAlertsData();
                    break;
                case 'performance':
                    await this.loadPerformanceData();
                    break;
                case 'diagnostics':
                    await this.loadDiagnosticsData();
                    break;
            }
        } catch (error) {
            console.error(`Failed to load ${tabName} data:`, error);
        }
    }

    async loadInitialData() {
        try {
            // Load system health summary
            await this.loadHealthSummary();
            
            // Load system information
            await this.loadSystemInfo();
            
            // Load current metrics
            await this.loadCurrentMetrics();
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    async loadHealthSummary() {
        try {
            const response = await fetch('/api/system-health/summary');
            const data = await response.json();
            
            this.updateHealthSummary(data);
        } catch (error) {
            console.error('Failed to load health summary:', error);
        }
    }

    updateHealthSummary(data) {
        // Update overall status
        const statusIcon = document.getElementById('overall-status-icon');
        const statusText = document.getElementById('overall-status-text');
        const statusDesc = document.getElementById('overall-status-desc');
        const lastCheckTime = document.getElementById('last-check-time');
        const healthScore = document.getElementById('health-score');

        if (statusIcon && statusText && statusDesc) {
            // Remove existing status classes
            statusIcon.classList.remove('healthy', 'warning', 'critical', 'unknown');
            
            // Add current status class
            statusIcon.classList.add(data.overall_status || 'unknown');
            
            // Update text
            statusText.textContent = this.getStatusText(data.overall_status);
            statusDesc.textContent = this.getStatusDescription(data);
            
            if (lastCheckTime && data.last_check) {
                lastCheckTime.textContent = `Last check: ${this.formatTime(data.last_check)}`;
            }
            
            if (healthScore) {
                const score = data.health_score || 0;
                healthScore.textContent = score;
                
                // Update score circle
                const scoreCircle = healthScore.closest('.score-circle');
                if (scoreCircle) {
                    const scoreDeg = (score / 100) * 360;
                    scoreCircle.style.setProperty('--score-deg', `${scoreDeg}deg`);
                }
            }
        }

        // Update active alerts count
        const activeAlertsElement = document.getElementById('active-alerts');
        if (activeAlertsElement) {
            activeAlertsElement.textContent = data.active_alerts || 0;
        }
    }

    async loadCurrentMetrics() {
        try {
            const response = await fetch('/api/system-health/metrics/current');
            const data = await response.json();
            
            this.updateCurrentMetrics(data);
        } catch (error) {
            console.error('Failed to load current metrics:', error);
        }
    }

    updateCurrentMetrics(data) {
        // Update CPU usage
        const cpuUsage = document.getElementById('cpu-usage');
        const cpuTrend = document.getElementById('cpu-trend');
        if (cpuUsage && data.cpu) {
            cpuUsage.textContent = `${data.cpu.percent.toFixed(1)}%`;
            this.updateTrend(cpuTrend, data.cpu.trend);
        }

        // Update Memory usage
        const memoryUsage = document.getElementById('memory-usage');
        const memoryTrend = document.getElementById('memory-trend');
        if (memoryUsage && data.memory) {
            memoryUsage.textContent = `${data.memory.percent.toFixed(1)}%`;
            this.updateTrend(memoryTrend, data.memory.trend);
        }

        // Update Disk usage
        const diskUsage = document.getElementById('disk-usage');
        const diskTrend = document.getElementById('disk-trend');
        if (diskUsage && data.disk) {
            diskUsage.textContent = `${data.disk.percent.toFixed(1)}%`;
            this.updateTrend(diskTrend, data.disk.trend);
        }

        // Update Network connections
        const networkConnections = document.getElementById('network-connections');
        const networkTrend = document.getElementById('network-trend');
        if (networkConnections && data.network) {
            networkConnections.textContent = data.network.connections || 0;
            this.updateTrend(networkTrend, data.network.trend);
        }

        // Update System uptime
        const systemUptime = document.getElementById('system-uptime');
        if (systemUptime && data.uptime) {
            systemUptime.textContent = this.formatUptime(data.uptime);
        }
    }

    updateTrend(trendElement, trend) {
        if (!trendElement) return;

        const icon = trendElement.querySelector('i');
        const text = trendElement.querySelector('span');

        // Remove existing trend classes
        trendElement.classList.remove('increasing', 'decreasing', 'stable');
        
        // Add current trend class
        trendElement.classList.add(trend || 'stable');

        // Update icon
        if (icon) {
            icon.classList.remove('fa-arrow-up', 'fa-arrow-down', 'fa-arrow-right');
            
            switch (trend) {
                case 'increasing':
                    icon.classList.add('fa-arrow-up');
                    break;
                case 'decreasing':
                    icon.classList.add('fa-arrow-down');
                    break;
                default:
                    icon.classList.add('fa-arrow-right');
            }
        }

        // Update text
        if (text) {
            text.textContent = this.getTrendText(trend);
        }
    }

    async loadSystemInfo() {
        try {
            const response = await fetch('/api/system-health/info');
            const data = await response.json();
            
            this.updateSystemInfo(data);
        } catch (error) {
            console.error('Failed to load system info:', error);
        }
    }

    updateSystemInfo(data) {
        const container = document.getElementById('system-info-grid');
        if (!container) return;

        container.innerHTML = '';

        const infoItems = [
            { label: 'Platform', value: data.platform },
            { label: 'System', value: data.system },
            { label: 'Release', value: data.release },
            { label: 'Machine', value: data.machine },
            { label: 'CPU Count', value: data.cpu_count },
            { label: 'Total Memory', value: this.formatBytes(data.memory_total) },
            { label: 'Total Disk', value: this.formatBytes(data.disk_total) },
            { label: 'Boot Time', value: this.formatDateTime(data.boot_time) }
        ];

        infoItems.forEach(item => {
            if (item.value) {
                const infoElement = document.createElement('div');
                infoElement.className = 'info-item';
                infoElement.innerHTML = `
                    <strong>${item.label}:</strong>
                    <span>${item.value}</span>
                `;
                container.appendChild(infoElement);
            }
        });
    }

    async loadOverviewData() {
        try {
            // Load recent activity
            await this.loadRecentActivity();
            
            // Update charts if they exist
            if (this.charts.cpuMemoryChart) {
                await this.updateCpuMemoryChart();
            }
            
            if (this.charts.networkIoChart) {
                await this.updateNetworkIoChart();
            }
        } catch (error) {
            console.error('Failed to load overview data:', error);
        }
    }

    async loadRecentActivity() {
        try {
            const response = await fetch('/api/system-health/activity');
            const data = await response.json();
            
            this.updateRecentActivity(data.activities || []);
        } catch (error) {
            console.error('Failed to load recent activity:', error);
        }
    }

    updateRecentActivity(activities) {
        const container = document.getElementById('activity-feed');
        if (!container) return;

        container.innerHTML = '';

        if (activities.length === 0) {
            container.innerHTML = '<div class="activity-placeholder">No recent activity</div>';
            return;
        }

        activities.forEach(activity => {
            const activityElement = document.createElement('div');
            activityElement.className = 'activity-item';
            activityElement.innerHTML = `
                <div class="activity-icon ${activity.type}">
                    <i class="fas ${this.getActivityIcon(activity.type)}"></i>
                </div>
                <div class="activity-content">
                    <h5>${activity.title}</h5>
                    <p>${activity.description}</p>
                </div>
                <div class="activity-time">
                    ${this.formatTime(activity.timestamp)}
                </div>
            `;
            container.appendChild(activityElement);
        });
    }

    initializeCharts() {
        // Initialize CPU & Memory Chart
        this.initializeCpuMemoryChart();
        
        // Initialize Network I/O Chart
        this.initializeNetworkIoChart();
        
        // Initialize other charts based on current tab
        if (this.currentTab === 'resources') {
            this.initializeResourceCharts();
        } else if (this.currentTab === 'performance') {
            this.initializePerformanceCharts();
        }
    }

    initializeCpuMemoryChart() {
        const canvas = document.getElementById('cpu-memory-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        this.charts.cpuMemoryChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU %',
                        data: [],
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Memory %',
                        data: [],
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute',
                            displayFormats: {
                                minute: 'HH:mm'
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                animation: {
                    duration: 0
                }
            }
        });
    }

    initializeNetworkIoChart() {
        const canvas = document.getElementById('network-io-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        this.charts.networkIoChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Bytes Sent',
                        data: [],
                        borderColor: '#17a2b8',
                        backgroundColor: 'rgba(23, 162, 184, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Bytes Received',
                        data: [],
                        borderColor: '#ffc107',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return this.formatBytes(value);
                            }.bind(this)
                        }
                    },
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute',
                            displayFormats: {
                                minute: 'HH:mm'
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                animation: {
                    duration: 0
                }
            }
        });
    }

    async updateCpuMemoryChart() {
        try {
            const response = await fetch('/api/system-health/metrics/history?minutes=60');
            const data = await response.json();
            
            if (data.cpu && data.memory && this.charts.cpuMemoryChart) {
                const labels = data.cpu.map(item => new Date(item.timestamp));
                const cpuData = data.cpu.map(item => item.percent);
                const memoryData = data.memory.map(item => item.percent);
                
                this.charts.cpuMemoryChart.data.labels = labels;
                this.charts.cpuMemoryChart.data.datasets[0].data = cpuData;
                this.charts.cpuMemoryChart.data.datasets[1].data = memoryData;
                this.charts.cpuMemoryChart.update('none');
            }
        } catch (error) {
            console.error('Failed to update CPU/Memory chart:', error);
        }
    }

    async updateNetworkIoChart() {
        try {
            const response = await fetch('/api/system-health/metrics/history?minutes=60');
            const data = await response.json();
            
            if (data.network && this.charts.networkIoChart) {
                const labels = data.network.map(item => new Date(item.timestamp));
                const sentData = data.network.map(item => item.bytes_sent);
                const recvData = data.network.map(item => item.bytes_recv);
                
                this.charts.networkIoChart.data.labels = labels;
                this.charts.networkIoChart.data.datasets[0].data = sentData;
                this.charts.networkIoChart.data.datasets[1].data = recvData;
                this.charts.networkIoChart.update('none');
            }
        } catch (error) {
            console.error('Failed to update Network I/O chart:', error);
        }
    }

    setupRealTimeUpdates() {
        // Setup periodic updates
        this.updateInterval = setInterval(() => {
            this.refreshCurrentData();
        }, 10000); // Update every 10 seconds

        // Setup WebSocket for real-time updates
        this.setupWebSocket();
    }

    setupWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/system-health`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected for system health updates');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected, attempting to reconnect...');
                setTimeout(() => this.setupWebSocket(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Failed to setup WebSocket:', error);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'metrics_update':
                this.updateCurrentMetrics(data.data);
                break;
            case 'health_update':
                this.updateHealthSummary(data.data);
                break;
            case 'alert_new':
                this.handleNewAlert(data.data);
                break;
            case 'alert_resolved':
                this.handleResolvedAlert(data.data);
                break;
            case 'component_status':
                this.updateComponentStatus(data.data);
                break;
        }
    }

    async refreshCurrentData() {
        try {
            await this.loadHealthSummary();
            await this.loadCurrentMetrics();
            
            // Update charts if visible
            if (this.currentTab === 'overview') {
                await this.updateCpuMemoryChart();
                await this.updateNetworkIoChart();
            }
        } catch (error) {
            console.error('Failed to refresh current data:', error);
        }
    }

    async refreshAll() {
        try {
            this.showLoading();
            
            await this.loadInitialData();
            await this.loadTabData(this.currentTab);
            
            this.showNotification('Dashboard refreshed successfully', 'success');
        } catch (error) {
            console.error('Failed to refresh dashboard:', error);
            this.showNotification('Failed to refresh dashboard', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Utility functions
    getStatusText(status) {
        const statusTexts = {
            healthy: 'System Healthy',
            warning: 'System Warning',
            critical: 'System Critical',
            unknown: 'Status Unknown'
        };
        return statusTexts[status] || 'Status Unknown';
    }

    getStatusDescription(data) {
        if (data.overall_status === 'healthy') {
            return 'All systems operating normally';
        } else if (data.overall_status === 'warning') {
            return `${data.warning_components || 0} components need attention`;
        } else if (data.overall_status === 'critical') {
            return `${data.critical_components || 0} critical issues detected`;
        }
        return 'System status check in progress';
    }

    getTrendText(trend) {
        const trendTexts = {
            increasing: 'Increasing',
            decreasing: 'Decreasing',
            stable: 'Stable'
        };
        return trendTexts[trend] || 'Stable';
    }

    getActivityIcon(type) {
        const icons = {
            info: 'fa-info-circle',
            warning: 'fa-exclamation-triangle',
            error: 'fa-times-circle',
            success: 'fa-check-circle'
        };
        return icons[type] || 'fa-info-circle';
    }

    formatTime(timestamp) {
        if (!timestamp) return '--';
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    }

    formatDateTime(timestamp) {
        if (!timestamp) return '--';
        const date = new Date(timestamp);
        return date.toLocaleString();
    }

    formatUptime(seconds) {
        if (!seconds) return '--';
        
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }

    formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'flex';
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'none';
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas ${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close">&times;</button>
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
        
        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    // Cleanup
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.websocket) {
            this.websocket.close();
        }
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// Global functions for diagnostic tools
window.runSystemHealthCheck = async function() {
    try {
        const response = await fetch('/api/system-health/diagnostics/health-check', {
            method: 'POST'
        });
        const result = await response.json();
        
        displayDiagnosticResult('System Health Check', result);
    } catch (error) {
        console.error('Failed to run system health check:', error);
    }
};

window.runPerformanceBenchmark = async function() {
    try {
        const response = await fetch('/api/system-health/diagnostics/benchmark', {
            method: 'POST'
        });
        const result = await response.json();
        
        displayDiagnosticResult('Performance Benchmark', result);
    } catch (error) {
        console.error('Failed to run performance benchmark:', error);
    }
};

window.runResourceAnalysis = async function() {
    try {
        const response = await fetch('/api/system-health/diagnostics/resource-analysis', {
            method: 'POST'
        });
        const result = await response.json();
        
        displayDiagnosticResult('Resource Analysis', result);
    } catch (error) {
        console.error('Failed to run resource analysis:', error);
    }
};

window.runTroubleshoot = async function() {
    try {
        const response = await fetch('/api/system-health/diagnostics/troubleshoot', {
            method: 'POST'
        });
        const result = await response.json();
        
        displayDiagnosticResult('Troubleshoot Issues', result);
    } catch (error) {
        console.error('Failed to run troubleshoot:', error);
    }
};

function displayDiagnosticResult(title, result) {
    const container = document.getElementById('diagnostic-results');
    if (!container) return;

    const resultElement = document.createElement('div');
    resultElement.className = 'diagnostic-result';
    resultElement.innerHTML = `
        <h5>${title}</h5>
        <div class="result-content">
            <pre>${JSON.stringify(result, null, 2)}</pre>
        </div>
        <div class="result-timestamp">
            ${new Date().toLocaleString()}
        </div>
    `;
    
    // Remove placeholder if exists
    const placeholder = container.querySelector('.results-placeholder');
    if (placeholder) {
        placeholder.remove();
    }
    
    container.appendChild(resultElement);
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.systemHealthDashboard = new SystemHealthDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.systemHealthDashboard) {
        window.systemHealthDashboard.destroy();
    }
});