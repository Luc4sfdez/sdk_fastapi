// Configuration Management JavaScript

let editor = null;
let currentService = null;
let currentSchema = null;
let currentMode = 'json';
let validationTimer = null;

// Initialize the configuration editor
document.addEventListener('DOMContentLoaded', function() {
    initializeEditor();
    loadServices();
    loadSchemas();
    loadTemplates();
});

// Initialize CodeMirror editor
function initializeEditor() {
    const textarea = document.getElementById('configEditor');
    editor = CodeMirror.fromTextArea(textarea, {
        lineNumbers: true,
        mode: 'application/json',
        theme: 'monokai',
        autoCloseBrackets: true,
        matchBrackets: true,
        indentUnit: 2,
        tabSize: 2,
        lineWrapping: true
    });
    
    // Auto-validation on change
    editor.on('change', function() {
        clearTimeout(validationTimer);
        validationTimer = setTimeout(validateConfiguration, 1000);
    });
}

// Load available services
async function loadServices() {
    try {
        const response = await fetch('/api/services');
        const services = await response.json();
        
        const select = document.getElementById('serviceSelect');
        select.innerHTML = '<option value="">-- Select a Service --</option>';
        
        services.forEach(service => {
            const option = document.createElement('option');
            option.value = service.id;
            option.textContent = `${service.name} (${service.status})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading services:', error);
        showNotification('Error loading services', 'error');
    }
}

// Load available schemas
async function loadSchemas() {
    try {
        const response = await fetch('/api/configuration/schemas');
        const schemas = await response.json();
        
        const select = document.getElementById('schemaSelect');
        select.innerHTML = '<option value="">-- Select Schema --</option>';
        
        schemas.forEach(schema => {
            const option = document.createElement('option');
            option.value = schema.name;
            option.textContent = `${schema.name} (v${schema.version})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading schemas:', error);
        showNotification('Error loading schemas', 'error');
    }
}

// Load service configuration
async function loadServiceConfiguration() {
    const serviceId = document.getElementById('serviceSelect').value;
    if (!serviceId) {
        editor.setValue('');
        return;
    }
    
    currentService = serviceId;
    
    try {
        const response = await fetch(`/api/configuration/services/${serviceId}`);
        if (response.ok) {
            const config = await response.json();
            editor.setValue(JSON.stringify(config, null, 2));
        } else {
            editor.setValue('{\n  "name": "' + serviceId + '",\n  "port": 8080,\n  "environment": "development"\n}');
        }
        validateConfiguration();
    } catch (error) {
        console.error('Error loading service configuration:', error);
        showNotification('Error loading service configuration', 'error');
    }
}

// Load schema information
async function loadSchema() {
    const schemaName = document.getElementById('schemaSelect').value;
    if (!schemaName) {
        document.getElementById('schemaInfo').innerHTML = `
            <div class="text-muted text-center">
                <i class="fas fa-file-alt"></i>
                <p>Select a schema to view information</p>
            </div>
        `;
        return;
    }
    
    currentSchema = schemaName;
    
    try {
        const response = await fetch(`/api/configuration/schemas/${schemaName}`);
        const schema = await response.json();
        
        displaySchemaInfo(schema);
        generateFormEditor(schema);
    } catch (error) {
        console.error('Error loading schema:', error);
        showNotification('Error loading schema', 'error');
    }
}

// Display schema information
function displaySchemaInfo(schema) {
    const infoDiv = document.getElementById('schemaInfo');
    
    let requiredFields = '';
    if (schema.required_fields && schema.required_fields.length > 0) {
        requiredFields = schema.required_fields.map(field => 
            `<span class="badge bg-danger me-1">${field}</span>`
        ).join('');
    }
    
    let optionalFields = '';
    if (schema.optional_fields && schema.optional_fields.length > 0) {
        optionalFields = schema.optional_fields.map(field => 
            `<span class="badge bg-secondary me-1">${field}</span>`
        ).join('');
    }
    
    infoDiv.innerHTML = `
        <div class="mb-3">
            <h6><i class="fas fa-tag"></i> ${schema.name}</h6>
            <p class="text-muted small">${schema.description}</p>
            <small class="text-muted">Version: ${schema.version}</small>
        </div>
        
        ${requiredFields ? `
        <div class="mb-2">
            <strong>Required Fields:</strong><br>
            ${requiredFields}
        </div>
        ` : ''}
        
        ${optionalFields ? `
        <div class="mb-2">
            <strong>Optional Fields:</strong><br>
            ${optionalFields}
        </div>
        ` : ''}
    `;
}

// Generate form editor based on schema
function generateFormEditor(schema) {
    const formDiv = document.getElementById('configForm');
    
    if (!schema.schema || !schema.schema.properties) {
        formDiv.innerHTML = '<p class="text-muted">No form fields available for this schema</p>';
        return;
    }
    
    let formHTML = '';
    const properties = schema.schema.properties;
    const required = schema.schema.required || [];
    
    Object.keys(properties).forEach(fieldName => {
        const field = properties[fieldName];
        const isRequired = required.includes(fieldName);
        
        formHTML += generateFormField(fieldName, field, isRequired);
    });
    
    formDiv.innerHTML = formHTML;
    
    // Add event listeners for form changes
    formDiv.querySelectorAll('input, select, textarea').forEach(input => {
        input.addEventListener('change', updateConfigFromForm);
        input.addEventListener('input', updateConfigFromForm);
    });
}

// Generate individual form field
function generateFormField(name, field, required) {
    const requiredAttr = required ? 'required' : '';
    const requiredLabel = required ? '<span class="text-danger">*</span>' : '';
    
    let input = '';
    
    switch (field.type) {
        case 'string':
            if (field.enum) {
                input = `
                    <select class="form-select" id="form_${name}" ${requiredAttr}>
                        <option value="">-- Select ${name} --</option>
                        ${field.enum.map(option => `<option value="${option}">${option}</option>`).join('')}
                    </select>
                `;
            } else {
                input = `<input type="text" class="form-control" id="form_${name}" ${requiredAttr}>`;
            }
            break;
        case 'integer':
        case 'number':
            const min = field.minimum !== undefined ? `min="${field.minimum}"` : '';
            const max = field.maximum !== undefined ? `max="${field.maximum}"` : '';
            input = `<input type="number" class="form-control" id="form_${name}" ${min} ${max} ${requiredAttr}>`;
            break;
        case 'boolean':
            input = `
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="form_${name}">
                    <label class="form-check-label" for="form_${name}">
                        Enable ${name}
                    </label>
                </div>
            `;
            break;
        case 'object':
            input = `<textarea class="form-control" id="form_${name}" rows="3" placeholder="JSON object"></textarea>`;
            break;
        default:
            input = `<input type="text" class="form-control" id="form_${name}" ${requiredAttr}>`;
    }
    
    return `
        <div class="mb-3">
            <label for="form_${name}" class="form-label">
                ${name} ${requiredLabel}
            </label>
            ${input}
            ${field.description ? `<div class="form-text">${field.description}</div>` : ''}
        </div>
    `;
}

// Update configuration from form
function updateConfigFromForm() {
    if (currentMode !== 'form') return;
    
    const formData = {};
    const formDiv = document.getElementById('configForm');
    
    formDiv.querySelectorAll('input, select, textarea').forEach(input => {
        const fieldName = input.id.replace('form_', '');
        let value = input.value;
        
        if (input.type === 'checkbox') {
            value = input.checked;
        } else if (input.type === 'number') {
            value = value ? parseFloat(value) : null;
        } else if (input.classList.contains('form-control') && fieldName.includes('object')) {
            try {
                value = value ? JSON.parse(value) : {};
            } catch (e) {
                value = {};
            }
        }
        
        if (value !== null && value !== '') {
            formData[fieldName] = value;
        }
    });
    
    editor.setValue(JSON.stringify(formData, null, 2));
}

// Set editor mode
function setEditorMode(mode) {
    currentMode = mode;
    
    // Update button states
    document.querySelectorAll('.btn-group .btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    if (mode === 'form') {
        document.getElementById('textEditor').style.display = 'none';
        document.getElementById('formEditor').style.display = 'block';
        populateFormFromConfig();
    } else {
        document.getElementById('textEditor').style.display = 'block';
        document.getElementById('formEditor').style.display = 'none';
        
        if (mode === 'yaml') {
            editor.setOption('mode', 'yaml');
            convertToYAML();
        } else {
            editor.setOption('mode', 'application/json');
            convertToJSON();
        }
    }
}

// Populate form from current configuration
function populateFormFromConfig() {
    try {
        const config = JSON.parse(editor.getValue());
        
        Object.keys(config).forEach(key => {
            const input = document.getElementById(`form_${key}`);
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = !!config[key];
                } else if (typeof config[key] === 'object') {
                    input.value = JSON.stringify(config[key], null, 2);
                } else {
                    input.value = config[key];
                }
            }
        });
    } catch (error) {
        console.error('Error populating form:', error);
    }
}

// Convert configuration to YAML
function convertToYAML() {
    try {
        const config = JSON.parse(editor.getValue());
        const yaml = jsonToYaml(config);
        editor.setValue(yaml);
    } catch (error) {
        console.error('Error converting to YAML:', error);
    }
}

// Convert configuration to JSON
function convertToJSON() {
    try {
        const content = editor.getValue();
        if (currentMode === 'yaml') {
            const json = yamlToJson(content);
            editor.setValue(JSON.stringify(json, null, 2));
        }
    } catch (error) {
        console.error('Error converting to JSON:', error);
    }
}

// Simple JSON to YAML converter
function jsonToYaml(obj, indent = 0) {
    let yaml = '';
    const spaces = '  '.repeat(indent);
    
    for (const [key, value] of Object.entries(obj)) {
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            yaml += `${spaces}${key}:\n${jsonToYaml(value, indent + 1)}`;
        } else if (Array.isArray(value)) {
            yaml += `${spaces}${key}:\n`;
            value.forEach(item => {
                yaml += `${spaces}  - ${item}\n`;
            });
        } else {
            yaml += `${spaces}${key}: ${value}\n`;
        }
    }
    
    return yaml;
}

// Simple YAML to JSON converter (basic implementation)
function yamlToJson(yaml) {
    // This is a very basic YAML parser - in production, use a proper library
    const lines = yaml.split('\n').filter(line => line.trim());
    const result = {};
    
    lines.forEach(line => {
        const match = line.match(/^(\s*)([^:]+):\s*(.*)$/);
        if (match) {
            const key = match[2].trim();
            const value = match[3].trim();
            
            if (value === 'true' || value === 'false') {
                result[key] = value === 'true';
            } else if (!isNaN(value) && value !== '') {
                result[key] = parseFloat(value);
            } else {
                result[key] = value;
            }
        }
    });
    
    return result;
}

// Validate configuration
async function validateConfiguration() {
    if (!currentService || !currentSchema) {
        showValidationResult({ valid: false, errors: ['Please select both service and schema'] });
        return;
    }
    
    try {
        const config = JSON.parse(editor.getValue());
        
        const response = await fetch('/api/configuration/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                service_id: currentService,
                schema_name: currentSchema,
                configuration: config
            })
        });
        
        const result = await response.json();
        showValidationResult(result);
    } catch (error) {
        console.error('Validation error:', error);
        showValidationResult({ 
            valid: false, 
            errors: ['Invalid JSON format or validation service error'] 
        });
    }
}

// Show validation results
function showValidationResult(result) {
    const resultsDiv = document.getElementById('validationResults');
    
    if (result.valid) {
        resultsDiv.innerHTML = `
            <div class="alert alert-success">
                <i class="fas fa-check-circle"></i>
                <strong>Valid Configuration</strong>
                <p class="mb-0">Your configuration passes all validation checks.</p>
            </div>
        `;
    } else {
        const errors = result.errors || ['Unknown validation error'];
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Validation Errors</strong>
                <ul class="mb-0 mt-2">
                    ${errors.map(error => `<li>${error}</li>`).join('')}
                </ul>
            </div>
        `;
    }
}

// Save configuration
async function saveConfiguration() {
    if (!currentService) {
        showNotification('Please select a service first', 'error');
        return;
    }
    
    try {
        const config = JSON.parse(editor.getValue());
        
        const response = await fetch(`/api/configuration/services/${currentService}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                configuration: config,
                user: 'web-user' // In production, get from authentication
            })
        });
        
        if (response.ok) {
            showNotification('Configuration saved successfully', 'success');
        } else {
            const error = await response.json();
            showNotification(`Error saving configuration: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Save error:', error);
        showNotification('Error saving configuration', 'error');
    }
}

// Load templates
async function loadTemplates() {
    try {
        const response = await fetch('/api/configuration/templates');
        const templates = await response.json();
        
        const templatesDiv = document.getElementById('templatesList');
        
        if (templates.length === 0) {
            templatesDiv.innerHTML = `
                <div class="text-muted text-center">
                    <i class="fas fa-layer-group"></i>
                    <p>No templates available</p>
                </div>
            `;
            return;
        }
        
        let templatesHTML = '';
        templates.forEach(template => {
            templatesHTML += `
                <div class="mb-2">
                    <button class="btn btn-outline-primary btn-sm w-100" onclick="applyTemplate('${template.name}')">
                        <i class="fas fa-layer-group"></i> ${template.name}
                    </button>
                    <small class="text-muted d-block">${template.description}</small>
                </div>
            `;
        });
        
        templatesDiv.innerHTML = templatesHTML;
    } catch (error) {
        console.error('Error loading templates:', error);
    }
}

// Apply template
async function applyTemplate(templateName) {
    try {
        const response = await fetch(`/api/configuration/templates/${templateName}`);
        const template = await response.json();
        
        // Apply template variables with defaults
        let config = JSON.stringify(template.template_data, null, 2);
        
        // Replace template variables with defaults or prompts
        template.variables.forEach(variable => {
            const placeholder = `\${${variable}}`;
            if (config.includes(placeholder)) {
                const value = prompt(`Enter value for ${variable}:`) || variable;
                config = config.replace(new RegExp(`\\$\\{${variable}[^}]*\\}`, 'g'), value);
            }
        });
        
        editor.setValue(config);
        showNotification(`Template "${templateName}" applied`, 'success');
    } catch (error) {
        console.error('Error applying template:', error);
        showNotification('Error applying template', 'error');
    }
}

// Show configuration history
async function showHistory() {
    if (!currentService) {
        showNotification('Please select a service first', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/configuration/services/${currentService}/history`);
        const history = await response.json();
        
        const historyContent = document.getElementById('historyContent');
        
        if (history.length === 0) {
            historyContent.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-history"></i>
                    <p>No configuration history available</p>
                </div>
            `;
        } else {
            let historyHTML = '<div class="list-group">';
            
            history.forEach((entry, index) => {
                historyHTML += `
                    <div class="list-group-item">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">Version ${entry.version}</h6>
                            <small>${new Date(entry.timestamp).toLocaleString()}</small>
                        </div>
                        <p class="mb-1">Updated by: ${entry.user}</p>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" onclick="loadHistoryVersion(${index})">
                                <i class="fas fa-eye"></i> View
                            </button>
                            <button class="btn btn-outline-info" onclick="restoreVersion(${index})">
                                <i class="fas fa-undo"></i> Restore
                            </button>
                            ${index > 0 ? `<button class="btn btn-outline-warning" onclick="showDiff(${index}, ${index-1})">
                                <i class="fas fa-code-branch"></i> Diff
                            </button>` : ''}
                        </div>
                    </div>
                `;
            });
            
            historyHTML += '</div>';
            historyContent.innerHTML = historyHTML;
        }
        
        // Store history data for later use
        window.configHistory = history;
        
        // Show modal
        new bootstrap.Modal(document.getElementById('historyModal')).show();
    } catch (error) {
        console.error('Error loading history:', error);
        showNotification('Error loading configuration history', 'error');
    }
}

// Load specific history version
function loadHistoryVersion(index) {
    const entry = window.configHistory[index];
    editor.setValue(JSON.stringify(entry.configuration, null, 2));
    bootstrap.Modal.getInstance(document.getElementById('historyModal')).hide();
    showNotification(`Loaded version ${entry.version}`, 'info');
}

// Restore specific version
function restoreVersion(index) {
    if (confirm('Are you sure you want to restore this version? Current changes will be lost.')) {
        loadHistoryVersion(index);
    }
}

// Show diff between versions
function showDiff(newIndex, oldIndex) {
    const newConfig = window.configHistory[newIndex];
    const oldConfig = window.configHistory[oldIndex];
    
    const diffContent = document.getElementById('diffContent');
    
    // Simple diff display (in production, use a proper diff library)
    diffContent.innerHTML = `
        <div class="row">
            <div class="col-6">
                <h6>Version ${oldConfig.version} (${new Date(oldConfig.timestamp).toLocaleString()})</h6>
                <pre class="bg-light p-3"><code>${JSON.stringify(oldConfig.configuration, null, 2)}</code></pre>
            </div>
            <div class="col-6">
                <h6>Version ${newConfig.version} (${new Date(newConfig.timestamp).toLocaleString()})</h6>
                <pre class="bg-light p-3"><code>${JSON.stringify(newConfig.configuration, null, 2)}</code></pre>
            </div>
        </div>
    `;
    
    new bootstrap.Modal(document.getElementById('diffModal')).show();
}

// Show notification
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