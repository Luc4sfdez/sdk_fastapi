// Log Management JavaScript

let logManager = {
    // State
    isStreaming: false,
    autoScroll: true,
    showTimestamps: true,
    wordWrap: true,
    regexSearch: false,
    currentLogs: [],
    filteredLogs: [],
    selectedLogEntry: null,
    
    // WebSocket connection
    websocket: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    
    // Filters
    currentFilters: {
        service: '',
        level: '',
        source: '',
        search: '',
        startTime: '',
        endTime: '',
        component: '',
        requestId: '',
        limit: 500
    },
    
    // Statistics
    stats: {
        total: 0,
        warnings: 0,
        errors: 0
    }
};

// Initialize the log management interface
document.addEventListener('DOMContentLoaded', function() {
    initializeLogManager();
    loadServices();
    loadInitialLogs();
    setupEventListeners();
});

// Initialize log manager
function initializeLogManager() {
    console.log('Initializing Log Manager...');
    
    // Setup auto-scroll
    const logContainer = document.getElementById('logContainer');
    logContainer.addEventListener('scroll', handleScroll);
    
    // Setup keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Setup context menu
    document.addEventListener('contextmenu', handleContextMenu);
    
    // Update UI state
    updateUIState();
}

// Load available services
async function loadServices() {
    try {
        const response = await fetch('/api/logs/services');
        const services = await response.json();
        
        const select = document.getElementById('serviceSelect');
        select.innerHTML = '<option value="">-- All Services --</option>';
        
        services.forEach(service => {
            const option = document.createElement('option');
            option.value = service;
            option.textContent = service;
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading services:', error);
        showNotification('Error loading services', 'error');
    }
}

// Load initial logs
async function loadInitialLogs() {
    showLoadingIndicator(true);
    
    try {
        const logs = await fetchLogs();
        logManager.currentLogs = logs;
        applyFiltersAndDisplay();
        updateStatistics();
        
    } catch (error) {
        console.error('Error loading initial logs:', error);
        showNotification('Error loading logs', 'error');
    } finally {
        showLoadingIndicator(false);
    }
}

// Fetch logs from API
async function fetchLogs(filters = null) {
    const params = new URLSearchParams();
    
    const activeFilters = filters || logManager.currentFilters;
    
    if (activeFilters.service) params.append('service_ids', activeFilters.service);
    if (activeFilters.level) params.append('levels', activeFilters.level);
    if (activeFilters.source) params.append('sources', activeFilters.source);
    if (activeFilters.search) {
        if (logManager.regexSearch) {
            params.append('regex_pattern', activeFilters.search);
        } else {
            params.append('search_text', activeFilters.search);
        }
    }
    if (activeFilters.startTime) params.append('start_time', activeFilters.startTime);
    if (activeFilters.endTime) params.append('end_time', activeFilters.endTime);
    if (activeFilters.component) params.append('components', activeFilters.component);
    if (activeFilters.requestId) params.append('request_id', activeFilters.requestId);
    params.append('limit', activeFilters.limit);
    params.append('sort_desc', 'true');
    
    const response = await fetch(`/api/logs/search?${params}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

// Apply filters and display logs
function applyFiltersAndDisplay() {
    // Apply client-side filtering if needed
    logManager.filteredLogs = logManager.currentLogs;
    
    // Display logs
    displayLogs(logManager.filteredLogs);
    
    // Update statistics
    updateStatistics();
    
    // Show/hide no logs message
    const noLogsMessage = document.getElementById('noLogsMessage');
    noLogsMessage.style.display = logManager.filteredLogs.length === 0 ? 'block' : 'none';
}

// Display logs in the container
function displayLogs(logs) {
    const container = document.getElementById('logEntries');
    container.innerHTML = '';
    
    if (logs.length === 0) {
        return;
    }
    
    // Create document fragment for better performance
    const fragment = document.createDocumentFragment();
    
    logs.forEach((log, index) => {
        const logElement = createLogElement(log, index);
        fragment.appendChild(logElement);
    });
    
    container.appendChild(fragment);
    
    // Auto-scroll to bottom if enabled
    if (logManager.autoScroll) {
        scrollToBottom();
    }
}

// Create a log entry element
function createLogElement(log, index) {
    const div = document.createElement('div');
    div.className = `log-entry ${log.level}`;
    div.dataset.index = index;
    div.onclick = () => selectLogEntry(index);
    div.ondblclick = () => showLogDetails(log);
    
    let content = '';
    
    // Timestamp
    if (logManager.showTimestamps) {
        const timestamp = new Date(log.timestamp).toLocaleString();
        content += `<span class="log-timestamp">[${timestamp}]</span> `;
    }
    
    // Log level
    content += `<span class="log-level ${log.level}">${log.level}</span>`;
    
    // Service
    content += `<span class="log-service">${log.service_id}</span>`;
    
    // Source
    if (log.source) {
        content += `<span class="log-source ${log.source}">${log.source.toUpperCase()}</span>`;
    }
    
    // Component
    if (log.component) {
        content += `<span class="log-component">[${log.component}]</span>`;
    }
    
    // Message
    let message = log.message;
    if (logManager.currentFilters.search && !logManager.regexSearch) {
        message = highlightSearchText(message, logManager.currentFilters.search);
    }
    content += `<span class="log-message">${escapeHtml(message)}</span>`;
    
    // Metadata
    if (log.request_id || log.user_id || (log.metadata && Object.keys(log.metadata).length > 0)) {
        content += '<div class="log-metadata">';
        if (log.request_id) content += `Request: ${log.request_id} `;
        if (log.user_id) content += `User: ${log.user_id} `;
        if (log.metadata && Object.keys(log.metadata).length > 0) {
            content += `Metadata: ${JSON.stringify(log.metadata)}`;
        }
        content += '</div>';
    }
    
    div.innerHTML = content;
    return div;
}

// Highlight search text in message
function highlightSearchText(text, searchTerm) {
    if (!searchTerm) return text;
    
    const regex = new RegExp(`(${escapeRegex(searchTerm)})`, 'gi');
    return text.replace(regex, '<span class="search-highlight">$1</span>');
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Escape regex special characters
function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\\]\\]/g, '\\\\$&');
}

// Select log entry
function selectLogEntry(index) {
    // Remove previous selection
    document.querySelectorAll('.log-entry.selected').forEach(el => {
        el.classList.remove('selected');
    });
    
    // Add selection to clicked entry
    const logElement = document.querySelector(`[data-index="${index}"]`);
    if (logElement) {
        logElement.classList.add('selected');
        logManager.selectedLogEntry = logManager.filteredLogs[index];
    }
}

// Show log details modal
function showLogDetails(log) {
    const modal = new bootstrap.Modal(document.getElementById('logDetailModal'));
    const content = document.getElementById('logDetailContent');
    
    content.innerHTML = `
        <table class="table table-bordered log-detail-table">
            <tr><th>Timestamp</th><td>${new Date(log.timestamp).toLocaleString()}</td></tr>
            <tr><th>Level</th><td><span class="log-level ${log.level}">${log.level}</span></td></tr>
            <tr><th>Service</th><td>${log.service_id}</td></tr>
            <tr><th>Source</th><td>${log.source || 'N/A'}</td></tr>
            <tr><th>Component</th><td>${log.component || 'N/A'}</td></tr>
            <tr><th>Thread ID</th><td>${log.thread_id || 'N/A'}</td></tr>
            <tr><th>Request ID</th><td>${log.request_id || 'N/A'}</td></tr>
            <tr><th>User ID</th><td>${log.user_id || 'N/A'}</td></tr>
            <tr><th>Message</th><td>${escapeHtml(log.message)}</td></tr>
            <tr><th>Tags</th><td>${log.tags ? log.tags.join(', ') : 'None'}</td></tr>
        </table>
        
        ${log.metadata && Object.keys(log.metadata).length > 0 ? `
            <h6>Metadata:</h6>
            <div class="log-detail-json">${JSON.stringify(log.metadata, null, 2)}</div>
        ` : ''}
    `;
    
    modal.show();
}

// Apply filters
async function applyFilters() {
    // Update filter state
    logManager.currentFilters = {
        service: document.getElementById('serviceSelect').value,
        level: document.getElementById('levelSelect').value,
        source: document.getElementById('sourceSelect').value,
        search: document.getElementById('searchInput').value,
        startTime: document.getElementById('startTime').value,
        endTime: document.getElementById('endTime').value,
        component: document.getElementById('componentInput').value,
        requestId: document.getElementById('requestIdInput').value,
        limit: parseInt(document.getElementById('limitSelect').value)
    };
    
    // Update filter indicators
    updateFilterIndicators();
    
    // Fetch new logs if not streaming
    if (!logManager.isStreaming) {
        showLoadingIndicator(true);
        try {
            const logs = await fetchLogs();
            logManager.currentLogs = logs;
            applyFiltersAndDisplay();
        } catch (error) {
            console.error('Error applying filters:', error);
            showNotification('Error applying filters', 'error');
        } finally {
            showLoadingIndicator(false);
        }
    } else {
        // Apply filters to current logs
        applyFiltersAndDisplay();
    }
}

// Update filter indicators
function updateFilterIndicators() {
    const filters = logManager.currentFilters;
    
    // Update form elements with active filter styling
    Object.keys(filters).forEach(key => {
        const element = document.getElementById(key + 'Select') || 
                       document.getElementById(key + 'Input');
        if (element && filters[key]) {
            element.classList.add('filter-active');
        } else if (element) {
            element.classList.remove('filter-active');
        }
    });
}

// Handle search input keyup
function handleSearchKeyup(event) {
    if (event.key === 'Enter') {
        applyFilters();
    }
}

// Toggle regex search
function toggleRegexSearch() {
    logManager.regexSearch = !logManager.regexSearch;
    const icon = document.getElementById('regexIcon');
    const button = icon.parentElement;
    
    if (logManager.regexSearch) {
        button.classList.add('regex-active');
        icon.className = 'fas fa-code';
    } else {
        button.classList.remove('regex-active');
        icon.className = 'fas fa-code';
    }
    
    // Re-apply search if there's a search term
    if (logManager.currentFilters.search) {
        applyFilters();
    }
}

// Real-time streaming functions
async function startRealTimeStreaming() {
    if (logManager.isStreaming) return;
    
    try {
        // Start WebSocket connection
        await connectWebSocket();
        
        logManager.isStreaming = true;
        updateStreamingStatus();
        showNotification('Real-time streaming started', 'success');
        
    } catch (error) {
        console.error('Error starting streaming:', error);
        showNotification('Error starting streaming', 'error');
    }
}

async function stopRealTimeStreaming() {
    if (!logManager.isStreaming) return;
    
    try {
        // Close WebSocket connection
        if (logManager.websocket) {
            logManager.websocket.close();
            logManager.websocket = null;
        }
        
        logManager.isStreaming = false;
        updateStreamingStatus();
        showNotification('Real-time streaming stopped', 'info');
        
    } catch (error) {
        console.error('Error stopping streaming:', error);
        showNotification('Error stopping streaming', 'error');
    }
}

// WebSocket connection
async function connectWebSocket() {
    return new Promise((resolve, reject) => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/logs/stream`;
        
        logManager.websocket = new WebSocket(wsUrl);
        
        logManager.websocket.onopen = () => {
            console.log('WebSocket connected');
            logManager.reconnectAttempts = 0;
            
            // Send initial configuration
            const config = {
                service_id: logManager.currentFilters.service || 'all',
                filters: logManager.currentFilters
            };
            logManager.websocket.send(JSON.stringify(config));
            
            resolve();
        };
        
        logManager.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'log_entry') {
                    handleNewLogEntry(data.log);
                } else if (data.type === 'error') {
                    console.error('WebSocket error:', data.message);
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        logManager.websocket.onclose = () => {
            console.log('WebSocket disconnected');
            if (logManager.isStreaming && logManager.reconnectAttempts < logManager.maxReconnectAttempts) {
                setTimeout(() => {
                    logManager.reconnectAttempts++;
                    connectWebSocket().catch(console.error);
                }, 2000 * logManager.reconnectAttempts);
            }
        };
        
        logManager.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            reject(error);
        };
    });
}

// Handle new log entry from WebSocket
function handleNewLogEntry(log) {
    // Add to current logs
    logManager.currentLogs.unshift(log);
    
    // Limit the number of logs in memory
    if (logManager.currentLogs.length > logManager.currentFilters.limit * 2) {
        logManager.currentLogs = logManager.currentLogs.slice(0, logManager.currentFilters.limit);
    }
    
    // Re-apply filters and display
    applyFiltersAndDisplay();
    
    // Add animation to new entry
    setTimeout(() => {
        const newEntry = document.querySelector('.log-entry');
        if (newEntry) {
            newEntry.classList.add('new-entry');
        }
    }, 100);
}

// Update streaming status
function updateStreamingStatus() {
    const statusElement = document.getElementById('streamingStatus');
    
    if (logManager.isStreaming) {
        statusElement.textContent = 'Active';
        statusElement.className = 'badge bg-success streaming-active';
    } else {
        statusElement.textContent = 'Stopped';
        statusElement.className = 'badge bg-secondary';
    }
}

// Toggle functions
function toggleAutoScroll() {
    logManager.autoScroll = !logManager.autoScroll;
    const icon = document.getElementById('autoScrollIcon');
    
    if (logManager.autoScroll) {
        icon.parentElement.classList.add('auto-scroll-active');
        scrollToBottom();
    } else {
        icon.parentElement.classList.remove('auto-scroll-active');
    }
}

function toggleTimestamps() {
    logManager.showTimestamps = !logManager.showTimestamps;
    const container = document.getElementById('logContainer');
    
    if (logManager.showTimestamps) {
        container.classList.remove('timestamps-hidden');
    } else {
        container.classList.add('timestamps-hidden');
    }
    
    // Re-display logs
    displayLogs(logManager.filteredLogs);
}

function toggleWordWrap() {
    logManager.wordWrap = !logManager.wordWrap;
    const container = document.getElementById('logContainer');
    
    if (logManager.wordWrap) {
        container.classList.add('word-wrap-enabled');
        container.classList.remove('word-wrap-disabled');
    } else {
        container.classList.add('word-wrap-disabled');
        container.classList.remove('word-wrap-enabled');
    }
}

// Export functions
function exportLogs() {
    const modal = new bootstrap.Modal(document.getElementById('exportModal'));
    modal.show();
}

async function performExport() {
    const format = document.getElementById('exportFormat').value;
    const limit = parseInt(document.getElementById('exportLimit').value);
    const useCurrentFilters = document.getElementById('exportCurrentFilters').checked;
    
    try {
        showLoadingIndicator(true);
        
        const params = new URLSearchParams();
        params.append('format', format);
        params.append('limit', limit);
        
        if (useCurrentFilters) {
            const filters = logManager.currentFilters;
            if (filters.service) params.append('service_ids', filters.service);
            if (filters.level) params.append('levels', filters.level);
            if (filters.source) params.append('sources', filters.source);
            if (filters.search) params.append('search_text', filters.search);
            if (filters.startTime) params.append('start_time', filters.startTime);
            if (filters.endTime) params.append('end_time', filters.endTime);
        }
        
        const response = await fetch(`/api/logs/export?${params}`);
        if (!response.ok) {
            throw new Error(`Export failed: ${response.status}`);
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `logs_export_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        // Close modal
        bootstrap.Modal.getInstance(document.getElementById('exportModal')).hide();
        showNotification('Logs exported successfully', 'success');
        
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Error exporting logs', 'error');
    } finally {
        showLoadingIndicator(false);
    }
}

// Clear logs
function clearLogs() {
    if (confirm('Are you sure you want to clear all displayed logs?')) {
        logManager.currentLogs = [];
        logManager.filteredLogs = [];
        displayLogs([]);
        updateStatistics();
        showNotification('Logs cleared', 'info');
    }
}

// Update statistics
function updateStatistics() {
    const logs = logManager.filteredLogs;
    
    logManager.stats.total = logs.length;
    logManager.stats.warnings = logs.filter(log => log.level === 'WARNING').length;
    logManager.stats.errors = logs.filter(log => log.level === 'ERROR' || log.level === 'CRITICAL').length;
    
    document.getElementById('totalLogsCount').textContent = logManager.stats.total;
    document.getElementById('warningLogsCount').textContent = logManager.stats.warnings;
    document.getElementById('errorLogsCount').textContent = logManager.stats.errors;
}

// Utility functions
function scrollToBottom() {
    const container = document.getElementById('logContainer');
    container.scrollTop = container.scrollHeight;
}

function handleScroll() {
    const container = document.getElementById('logContainer');
    const isAtBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 10;
    
    if (!isAtBottom && logManager.autoScroll) {
        logManager.autoScroll = false;
        document.getElementById('autoScrollIcon').parentElement.classList.remove('auto-scroll-active');
    }
}

function showLoadingIndicator(show) {
    const indicator = document.getElementById('loadingIndicator');
    indicator.style.display = show ? 'block' : 'none';
}

function showNotification(message, type = 'info') {
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
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

function updateUIState() {
    updateStreamingStatus();
    updateFilterIndicators();
}

// Event listeners
function setupEventListeners() {
    // Filter change events
    document.getElementById('serviceSelect').addEventListener('change', applyFilters);
    document.getElementById('levelSelect').addEventListener('change', applyFilters);
    document.getElementById('sourceSelect').addEventListener('change', applyFilters);
    document.getElementById('limitSelect').addEventListener('change', applyFilters);
    document.getElementById('startTime').addEventListener('change', applyFilters);
    document.getElementById('endTime').addEventListener('change', applyFilters);
    document.getElementById('componentInput').addEventListener('change', applyFilters);
    document.getElementById('requestIdInput').addEventListener('change', applyFilters);
    
    // Search input with debounce
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(applyFilters, 500);
    });
}

// Keyboard shortcuts
function handleKeyboardShortcuts(event) {
    if (event.ctrlKey || event.metaKey) {
        switch (event.key) {
            case 'f':
                event.preventDefault();
                document.getElementById('searchInput').focus();
                break;
            case 'r':
                event.preventDefault();
                if (logManager.isStreaming) {
                    stopRealTimeStreaming();
                } else {
                    startRealTimeStreaming();
                }
                break;
            case 'e':
                event.preventDefault();
                exportLogs();
                break;
        }
    }
    
    // Other shortcuts
    switch (event.key) {
        case 'Escape':
            // Clear selection
            document.querySelectorAll('.log-entry.selected').forEach(el => {
                el.classList.remove('selected');
            });
            logManager.selectedLogEntry = null;
            break;
    }
}

// Context menu
function handleContextMenu(event) {
    const logEntry = event.target.closest('.log-entry');
    if (logEntry) {
        event.preventDefault();
        showContextMenu(event.clientX, event.clientY, logEntry);
    }
}

function showContextMenu(x, y, logEntry) {
    // Remove existing context menu
    const existingMenu = document.querySelector('.context-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // Create context menu
    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    
    const index = parseInt(logEntry.dataset.index);
    const log = logManager.filteredLogs[index];
    
    menu.innerHTML = `
        <div class="context-menu-item" onclick="showLogDetails(${JSON.stringify(log).replace(/"/g, '&quot;')})">
            <i class="fas fa-info-circle"></i> View Details
        </div>
        <div class="context-menu-item" onclick="copyLogMessage('${escapeHtml(log.message)}')">
            <i class="fas fa-copy"></i> Copy Message
        </div>
        <div class="context-menu-item" onclick="filterByService('${log.service_id}')">
            <i class="fas fa-filter"></i> Filter by Service
        </div>
        <div class="context-menu-item" onclick="filterByLevel('${log.level}')">
            <i class="fas fa-layer-group"></i> Filter by Level
        </div>
    `;
    
    document.body.appendChild(menu);
    
    // Remove menu when clicking elsewhere
    setTimeout(() => {
        document.addEventListener('click', function removeMenu() {
            menu.remove();
            document.removeEventListener('click', removeMenu);
        });
    }, 100);
}

function copyLogMessage(message) {
    navigator.clipboard.writeText(message).then(() => {
        showNotification('Message copied to clipboard', 'success');
    }).catch(() => {
        showNotification('Failed to copy message', 'error');
    });
}

function filterByService(serviceId) {
    document.getElementById('serviceSelect').value = serviceId;
    applyFilters();
}

function filterByLevel(level) {
    document.getElementById('levelSelect').value = level;
    applyFilters();
}