/**
 * Template Management Interface JavaScript
 * Provides interactive functionality for template creation, editing, and management
 */

class TemplateManagementInterface {
    constructor() {
        this.currentTemplate = null;
        this.templates = [];
        this.filteredTemplates = [];
        this.currentPage = 1;
        this.pageSize = 12;
        this.sortBy = 'name';
        this.sortOrder = 'asc';
        this.filters = {
            search: '',
            type: '',
            status: '',
            author: ''
        };
        
        // CodeMirror editor instance
        this.codeEditor = null;
        
        // Charts
        this.charts = {};
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.setupTabs();
        this.setupCodeEditor();
        await this.loadInitialData();
        this.updateStats();
    }

    setupEventListeners() {
        // Header actions
        document.getElementById('new-template-btn').addEventListener('click', () => {
            this.showNewTemplateModal();
        });

        document.getElementById('import-template-btn').addEventListener('click', () => {
            this.showImportTemplateModal();
        });

        // View toggle
        document.getElementById('grid-view-btn').addEventListener('click', () => {
            this.setViewMode('grid');
        });

        document.getElementById('list-view-btn').addEventListener('click', () => {
            this.setViewMode('list');
        });

        // Search and filters
        document.getElementById('template-search').addEventListener('input', (e) => {
            this.filters.search = e.target.value;
            this.applyFilters();
        });

        document.getElementById('search-btn').addEventListener('click', () => {
            this.applyFilters();
        });

        // Filter controls
        ['type-filter', 'status-filter', 'author-filter'].forEach(id => {
            document.getElementById(id).addEventListener('change', (e) => {
                const filterType = id.replace('-filter', '');
                this.filters[filterType] = e.target.value;
                this.applyFilters();
            });
        });

        document.getElementById('clear-filters').addEventListener('click', () => {
            this.clearFilters();
        });

        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Sort controls
        document.getElementById('sort-select').addEventListener('change', (e) => {
            this.sortBy = e.target.value;
            this.sortTemplates();
        });

        document.getElementById('sort-order').addEventListener('click', () => {
            this.toggleSortOrder();
        });

        // Pagination
        document.getElementById('prev-page').addEventListener('click', () => {
            this.previousPage();
        });

        document.getElementById('next-page').addEventListener('click', () => {
            this.nextPage();
        });

        // Editor actions
        document.getElementById('save-template').addEventListener('click', () => {
            this.saveTemplate();
        });

        document.getElementById('validate-template').addEventListener('click', () => {
            this.validateTemplate();
        });

        document.getElementById('preview-template').addEventListener('click', () => {
            this.previewTemplate();
        });

        document.getElementById('test-template').addEventListener('click', () => {
            this.testTemplate();
        });

        // Modal controls
        this.setupModalControls();
    }    setupMo
dalControls() {
        // New template modal
        document.getElementById('create-template-confirm').addEventListener('click', () => {
            this.createNewTemplate();
        });

        document.getElementById('create-template-cancel').addEventListener('click', () => {
            this.hideNewTemplateModal();
        });

        // Import template modal
        document.getElementById('import-template-confirm').addEventListener('click', () => {
            this.importTemplate();
        });

        document.getElementById('import-template-cancel').addEventListener('click', () => {
            this.hideImportTemplateModal();
        });

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                modal.style.display = 'none';
            });
        });

        // Click outside modal to close
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        });
    }

    setupTabs() {
        this.switchTab('browse');
    }

    setupCodeEditor() {
        const textarea = document.getElementById('code-editor');
        this.codeEditor = CodeMirror.fromTextArea(textarea, {
            lineNumbers: true,
            mode: 'text/plain',
            theme: 'default',
            indentUnit: 2,
            tabSize: 2,
            lineWrapping: false,
            autoCloseBrackets: true,
            matchBrackets: true,
            foldGutter: true,
            gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"]
        });

        // Editor options
        document.getElementById('editor-language').addEventListener('change', (e) => {
            this.setEditorMode(e.target.value);
        });

        document.getElementById('editor-theme').addEventListener('change', (e) => {
            this.codeEditor.setOption('theme', e.target.value);
        });

        document.getElementById('line-numbers').addEventListener('change', (e) => {
            this.codeEditor.setOption('lineNumbers', e.target.checked);
        });

        document.getElementById('word-wrap').addEventListener('change', (e) => {
            this.codeEditor.setOption('lineWrapping', e.target.checked);
        });

        // Auto-detect variables
        this.codeEditor.on('change', () => {
            this.detectVariables();
        });
    }

    setEditorMode(language) {
        const modes = {
            'python': 'python',
            'javascript': 'javascript',
            'yaml': 'yaml',
            'json': { name: 'javascript', json: true },
            'dockerfile': 'dockerfile',
            'html': 'htmlmixed',
            'css': 'css',
            'sql': 'sql',
            'text': 'text/plain'
        };

        const mode = modes[language] || 'text/plain';
        this.codeEditor.setOption('mode', mode);
    }

    async loadInitialData() {
        this.showLoading();
        
        try {
            await this.loadTemplates();
            await this.loadAuthors();
            this.applyFilters();
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('Failed to load templates');
        } finally {
            this.hideLoading();
        }
    }

    async loadTemplates() {
        try {
            const response = await fetch('/api/templates/custom');
            if (!response.ok) throw new Error('Failed to load templates');
            
            this.templates = await response.json();
            this.filteredTemplates = [...this.templates];
        } catch (error) {
            console.error('Failed to load templates:', error);
            throw error;
        }
    }

    async loadAuthors() {
        try {
            const authors = [...new Set(this.templates.map(t => t.author))];
            const authorFilter = document.getElementById('author-filter');
            
            // Clear existing options except "All Authors"
            while (authorFilter.children.length > 1) {
                authorFilter.removeChild(authorFilter.lastChild);
            }
            
            authors.forEach(author => {
                const option = document.createElement('option');
                option.value = author;
                option.textContent = author;
                authorFilter.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load authors:', error);
        }
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
        if (tabName === 'analytics') {
            this.loadAnalytics();
        } else if (tabName === 'validation') {
            this.loadValidation();
        }
    }

    setViewMode(mode) {
        const container = document.getElementById('templates-container');
        const gridBtn = document.getElementById('grid-view-btn');
        const listBtn = document.getElementById('list-view-btn');

        if (mode === 'grid') {
            container.className = 'templates-container grid-view';
            gridBtn.classList.add('active');
            listBtn.classList.remove('active');
        } else {
            container.className = 'templates-container list-view';
            listBtn.classList.add('active');
            gridBtn.classList.remove('active');
        }

        this.renderTemplates();
    }

    applyFilters() {
        this.filteredTemplates = this.templates.filter(template => {
            // Search filter
            if (this.filters.search) {
                const searchTerm = this.filters.search.toLowerCase();
                const matchesSearch = 
                    template.name.toLowerCase().includes(searchTerm) ||
                    template.description.toLowerCase().includes(searchTerm) ||
                    template.tags.some(tag => tag.toLowerCase().includes(searchTerm));
                
                if (!matchesSearch) return false;
            }

            // Type filter
            if (this.filters.type && template.template_type !== this.filters.type) {
                return false;
            }

            // Status filter
            if (this.filters.status && template.status !== this.filters.status) {
                return false;
            }

            // Author filter
            if (this.filters.author && template.author !== this.filters.author) {
                return false;
            }

            return true;
        });

        this.sortTemplates();
        this.currentPage = 1;
        this.renderTemplates();
        this.updatePagination();
    }

    clearFilters() {
        this.filters = {
            search: '',
            type: '',
            status: '',
            author: ''
        };

        // Reset form controls
        document.getElementById('template-search').value = '';
        document.getElementById('type-filter').value = '';
        document.getElementById('status-filter').value = '';
        document.getElementById('author-filter').value = '';

        this.applyFilters();
    }

    sortTemplates() {
        this.filteredTemplates.sort((a, b) => {
            let aValue, bValue;

            switch (this.sortBy) {
                case 'name':
                    aValue = a.name.toLowerCase();
                    bValue = b.name.toLowerCase();
                    break;
                case 'created':
                    aValue = new Date(a.created_at);
                    bValue = new Date(b.created_at);
                    break;
                case 'updated':
                    aValue = new Date(a.updated_at);
                    bValue = new Date(b.updated_at);
                    break;
                case 'usage':
                    aValue = a.usage_count || 0;
                    bValue = b.usage_count || 0;
                    break;
                case 'rating':
                    aValue = a.rating || 0;
                    bValue = b.rating || 0;
                    break;
                default:
                    aValue = a.name.toLowerCase();
                    bValue = b.name.toLowerCase();
            }

            if (aValue < bValue) return this.sortOrder === 'asc' ? -1 : 1;
            if (aValue > bValue) return this.sortOrder === 'asc' ? 1 : -1;
            return 0;
        });
    }

    toggleSortOrder() {
        this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
        const btn = document.getElementById('sort-order');
        const icon = btn.querySelector('i');
        
        if (this.sortOrder === 'asc') {
            icon.className = 'fas fa-sort-amount-down';
        } else {
            icon.className = 'fas fa-sort-amount-up';
        }

        this.sortTemplates();
        this.renderTemplates();
    }

    renderTemplates() {
        const container = document.getElementById('templates-container');
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageTemplates = this.filteredTemplates.slice(startIndex, endIndex);

        if (pageTemplates.length === 0) {
            container.innerHTML = `
                <div class="no-templates">
                    <i class="fas fa-folder-open"></i>
                    <h3>No templates found</h3>
                    <p>Try adjusting your search criteria or create a new template.</p>
                </div>
            `;
            return;
        }

        const isListView = container.classList.contains('list-view');
        
        container.innerHTML = pageTemplates.map(template => 
            this.renderTemplateCard(template, isListView)
        ).join('');

        // Add event listeners to template cards
        container.querySelectorAll('.template-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.template-actions')) {
                    const templateId = card.dataset.templateId;
                    this.openTemplate(templateId);
                }
            });
        });

        // Update results count
        document.getElementById('results-count').textContent = 
            `${this.filteredTemplates.length} template${this.filteredTemplates.length !== 1 ? 's' : ''} found`;
    } 
   renderTemplateCard(template, isListView) {
        const statusClass = template.status.toLowerCase();
        const typeClass = template.template_type.toLowerCase();
        
        return `
            <div class="template-card ${isListView ? 'list-view' : ''}" data-template-id="${template.id}">
                <div class="template-header">
                    <h3 class="template-title">${template.name}</h3>
                    <span class="template-type ${typeClass}">${template.template_type}</span>
                </div>
                <p class="template-description">${template.description}</p>
                <div class="template-meta">
                    <div class="template-info">
                        <span class="template-author">by ${template.author}</span>
                        <span class="template-version">v${template.version}</span>
                        <span class="template-status ${statusClass}">${template.status}</span>
                    </div>
                    <div class="template-stats">
                        <span><i class="fas fa-download"></i> ${template.usage_count || 0}</span>
                        <span><i class="fas fa-star"></i> ${template.rating || 0}</span>
                    </div>
                </div>
                <div class="template-actions">
                    <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); templateMgmt.editTemplate('${template.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); templateMgmt.duplicateTemplate('${template.id}')">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button class="btn btn-sm btn-outline" onclick="event.stopPropagation(); templateMgmt.exportTemplate('${template.id}')">
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            </div>
        `;
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredTemplates.length / this.pageSize);
        
        document.getElementById('prev-page').disabled = this.currentPage <= 1;
        document.getElementById('next-page').disabled = this.currentPage >= totalPages;
        document.getElementById('page-info').textContent = `Page ${this.currentPage} of ${totalPages}`;
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderTemplates();
            this.updatePagination();
        }
    }

    nextPage() {
        const totalPages = Math.ceil(this.filteredTemplates.length / this.pageSize);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.renderTemplates();
            this.updatePagination();
        }
    }

    // Template Management Methods
    async openTemplate(templateId) {
        try {
            const response = await fetch(`/api/templates/custom/${templateId}`);
            if (!response.ok) throw new Error('Failed to load template');
            
            this.currentTemplate = await response.json();
            this.loadTemplateIntoEditor();
            this.switchTab('editor');
        } catch (error) {
            console.error('Failed to open template:', error);
            this.showError('Failed to open template');
        }
    }

    loadTemplateIntoEditor() {
        if (!this.currentTemplate) return;

        // Load metadata
        document.getElementById('template-name').value = this.currentTemplate.metadata.name;
        document.getElementById('template-description').value = this.currentTemplate.metadata.description;
        document.getElementById('template-type').value = this.currentTemplate.metadata.template_type;
        document.getElementById('template-version').value = this.currentTemplate.metadata.version;
        document.getElementById('template-tags').value = this.currentTemplate.metadata.tags.join(', ');
        
        // Update status display
        const statusElement = document.getElementById('template-status');
        statusElement.textContent = this.currentTemplate.metadata.status;
        statusElement.className = `template-status ${this.currentTemplate.metadata.status.toLowerCase()}`;

        // Load content into editor
        this.codeEditor.setValue(this.currentTemplate.content);
        
        // Set editor mode based on template type
        this.setEditorModeFromType(this.currentTemplate.metadata.template_type);
        
        // Load variables
        this.loadVariables();
        
        // Load files
        this.loadFiles();
    }

    setEditorModeFromType(templateType) {
        const typeToMode = {
            'docker': 'dockerfile',
            'kubernetes': 'yaml',
            'api': 'python',
            'service': 'python',
            'model': 'python'
        };
        
        const mode = typeToMode[templateType] || 'text';
        document.getElementById('editor-language').value = mode;
        this.setEditorMode(mode);
    }

    loadVariables() {
        const container = document.getElementById('variables-container');
        const variables = this.currentTemplate.variables || {};
        
        container.innerHTML = '';
        
        Object.entries(variables).forEach(([name, config]) => {
            const variableElement = document.createElement('div');
            variableElement.className = 'variable-item';
            variableElement.innerHTML = `
                <div>
                    <span class="variable-name">${name}</span>
                    <span class="variable-type">${config.type || 'string'}</span>
                </div>
                <button class="btn btn-sm btn-outline" onclick="templateMgmt.removeVariable('${name}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
            container.appendChild(variableElement);
        });
    }

    loadFiles() {
        const container = document.getElementById('files-container');
        const files = this.currentTemplate.files || {};
        
        container.innerHTML = '';
        
        Object.entries(files).forEach(([filename, content]) => {
            const fileElement = document.createElement('div');
            fileElement.className = 'file-item';
            fileElement.innerHTML = `
                <div>
                    <span class="file-name">${filename}</span>
                    <span class="file-type">${this.getFileType(filename)}</span>
                </div>
                <button class="btn btn-sm btn-outline" onclick="templateMgmt.removeFile('${filename}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
            container.appendChild(fileElement);
        });
    }

    getFileType(filename) {
        const extension = filename.split('.').pop().toLowerCase();
        const types = {
            'py': 'Python',
            'js': 'JavaScript',
            'ts': 'TypeScript',
            'html': 'HTML',
            'css': 'CSS',
            'json': 'JSON',
            'yaml': 'YAML',
            'yml': 'YAML',
            'md': 'Markdown',
            'txt': 'Text'
        };
        return types[extension] || 'Unknown';
    }

    detectVariables() {
        const content = this.codeEditor.getValue();
        const variablePattern = /\{\{([^}]+)\}\}/g;
        const variables = new Set();
        
        let match;
        while ((match = variablePattern.exec(content)) !== null) {
            variables.add(match[1].trim());
        }
        
        // Update variables display
        this.updateDetectedVariables(Array.from(variables));
    }

    updateDetectedVariables(detectedVars) {
        const container = document.getElementById('variables-container');
        const existingVars = this.currentTemplate?.variables || {};
        
        // Add new variables that were detected but not yet defined
        detectedVars.forEach(varName => {
            if (!existingVars[varName]) {
                existingVars[varName] = {
                    type: 'string',
                    required: true,
                    description: `Variable: ${varName}`
                };
            }
        });
        
        // Update current template
        if (this.currentTemplate) {
            this.currentTemplate.variables = existingVars;
            this.loadVariables();
        }
    }

    async saveTemplate() {
        if (!this.currentTemplate) {
            this.showError('No template loaded');
            return;
        }

        this.showLoading();

        try {
            // Collect form data
            const templateData = {
                name: document.getElementById('template-name').value,
                description: document.getElementById('template-description').value,
                template_type: document.getElementById('template-type').value,
                version: document.getElementById('template-version').value,
                tags: document.getElementById('template-tags').value.split(',').map(t => t.trim()).filter(t => t),
                content: this.codeEditor.getValue(),
                variables: this.currentTemplate.variables || {},
                files: this.currentTemplate.files || {}
            };

            const response = await fetch(`/api/templates/custom/${this.currentTemplate.metadata.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(templateData)
            });

            if (!response.ok) throw new Error('Failed to save template');

            this.showSuccess('Template saved successfully');
            await this.loadTemplates();
            this.applyFilters();
        } catch (error) {
            console.error('Failed to save template:', error);
            this.showError('Failed to save template');
        } finally {
            this.hideLoading();
        }
    }

    async validateTemplate() {
        if (!this.currentTemplate) {
            this.showError('No template loaded');
            return;
        }

        this.showLoading();

        try {
            const response = await fetch('/api/templates/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: this.codeEditor.getValue(),
                    template_type: document.getElementById('template-type').value,
                    variables: this.currentTemplate.variables || {}
                })
            });

            if (!response.ok) throw new Error('Failed to validate template');

            const result = await response.json();
            this.displayValidationResults(result);
            
            // Switch to validation preview
            this.switchPreviewTab('validation');
        } catch (error) {
            console.error('Failed to validate template:', error);
            this.showError('Failed to validate template');
        } finally {
            this.hideLoading();
        }
    }

    displayValidationResults(result) {
        const container = document.getElementById('validation-content');
        
        let html = `
            <div class="validation-summary">
                <div class="validation-score ${result.is_valid ? 'valid' : 'invalid'}">
                    <h4>Validation Score: ${result.score.toFixed(1)}/100</h4>
                    <p>${result.is_valid ? 'Template is valid' : 'Template has issues'}</p>
                </div>
            </div>
        `;

        if (result.issues && result.issues.length > 0) {
            html += '<div class="validation-issues"><h4>Issues</h4>';
            result.issues.forEach(issue => {
                html += `
                    <div class="validation-issue ${issue.severity}">
                        <span class="issue-severity ${issue.severity}">${issue.severity}</span>
                        <div class="issue-message">${issue.message}</div>
                        ${issue.line_number ? `<div class="issue-location">Line ${issue.line_number}</div>` : ''}
                        ${issue.suggestion ? `<div class="issue-suggestion">Suggestion: ${issue.suggestion}</div>` : ''}
                    </div>
                `;
            });
            html += '</div>';
        }

        if (result.suggestions && result.suggestions.length > 0) {
            html += '<div class="validation-suggestions"><h4>Suggestions</h4>';
            result.suggestions.forEach(suggestion => {
                html += `<div class="suggestion-item">${suggestion}</div>`;
            });
            html += '</div>';
        }

        container.innerHTML = html;
    }

    switchPreviewTab(tabName) {
        // Hide all preview contents
        document.querySelectorAll('.preview-content').forEach(content => {
            content.classList.remove('active');
        });

        // Remove active class from all preview tabs
        document.querySelectorAll('.preview-tab').forEach(tab => {
            tab.classList.remove('active');
        });

        // Show selected preview content
        document.getElementById(`${tabName}-content`).classList.add('active');
        document.querySelector(`[data-preview="${tabName}"]`).classList.add('active');
    }

    // Modal Methods
    showNewTemplateModal() {
        document.getElementById('new-template-modal').style.display = 'block';
    }

    hideNewTemplateModal() {
        document.getElementById('new-template-modal').style.display = 'none';
        // Clear form
        document.getElementById('new-template-name').value = '';
        document.getElementById('new-template-description').value = '';
        document.getElementById('new-template-type').value = 'service';
        document.getElementById('new-template-starter').value = 'blank';
    }

    showImportTemplateModal() {
        document.getElementById('import-template-modal').style.display = 'block';
    }

    hideImportTemplateModal() {
        document.getElementById('import-template-modal').style.display = 'none';
        // Clear form
        document.getElementById('template-file').value = '';
        document.getElementById('template-url').value = '';
        document.getElementById('template-text').value = '';
        document.querySelector('input[name="import-type"][value="file"]').checked = true;
    }

    async createNewTemplate() {
        const name = document.getElementById('new-template-name').value;
        const description = document.getElementById('new-template-description').value;
        const type = document.getElementById('new-template-type').value;
        const starter = document.getElementById('new-template-starter').value;

        if (!name) {
            this.showError('Template name is required');
            return;
        }

        this.showLoading();

        try {
            const response = await fetch('/api/templates/custom', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    description,
                    template_type: type,
                    content: this.getStarterContent(type, starter),
                    author: 'Current User', // This should come from auth
                    version: '1.0.0',
                    tags: []
                })
            });

            if (!response.ok) throw new Error('Failed to create template');

            const result = await response.json();
            this.hideNewTemplateModal();
            this.showSuccess('Template created successfully');
            
            // Load the new template
            await this.openTemplate(result.template_id);
        } catch (error) {
            console.error('Failed to create template:', error);
            this.showError('Failed to create template');
        } finally {
            this.hideLoading();
        }
    }

    getStarterContent(type, starter) {
        if (starter === 'blank') {
            const starters = {
                'service': '# {{service_name}} Service\n\n# Service implementation here\n',
                'api': '# {{api_name}} API\n\n# API implementation here\n',
                'model': '# {{model_name}} Model\n\n# Model definition here\n',
                'database': '# {{db_name}} Database\n\n# Database schema here\n',
                'docker': 'FROM {{base_image}}\n\n# Docker configuration here\n',
                'kubernetes': 'apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {{app_name}}\n',
                'custom': '# {{template_name}}\n\n# Custom template content here\n'
            };
            return starters[type] || starters['custom'];
        }
        return '# Template content will be loaded here\n';
    }

    // Utility Methods
    updateStats() {
        const stats = {
            total: this.templates.length,
            active: this.templates.filter(t => t.status === 'active').length,
            my: this.templates.filter(t => t.author === 'Current User').length, // This should come from auth
            shared: this.templates.filter(t => t.author !== 'Current User').length
        };

        document.getElementById('total-templates').textContent = stats.total;
        document.getElementById('active-templates').textContent = stats.active;
        document.getElementById('my-templates').textContent = stats.my;
        document.getElementById('shared-templates').textContent = stats.shared;
    }

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

// Initialize the template management interface when the page loads
let templateMgmt;
document.addEventListener('DOMContentLoaded', () => {
    templateMgmt = new TemplateManagementInterface();
});   
 // Analytics functionality
    loadAnalytics() {
        const period = document.getElementById('analytics-period').value;
        
        fetch(`/api/templates/analytics?period=${period}`)
            .then(response => response.json())
            .then(data => {
                this.updateAnalyticsMetrics(data.metrics);
                this.updateAnalyticsCharts(data.charts);
                this.updateAnalyticsInsights(data.insights);
            })
            .catch(error => {
                console.error('Error loading analytics:', error);
                this.showNotification('Error loading analytics', 'error');
            });
    }

    updateAnalyticsMetrics(metrics) {
        document.getElementById('usage-count').textContent = metrics.usage_count || 0;
        document.getElementById('unique-users').textContent = metrics.unique_users || 0;
        document.getElementById('success-rate').textContent = `${metrics.success_rate || 0}%`;
        document.getElementById('avg-time').textContent = `${metrics.avg_time || 0}ms`;
    }

    updateAnalyticsCharts(chartData) {
        // Usage trend chart
        const usageCtx = document.getElementById('usage-trend-chart').getContext('2d');
        new Chart(usageCtx, {
            type: 'line',
            data: {
                labels: chartData.usage_trend.labels,
                datasets: [{
                    label: 'Template Usage',
                    data: chartData.usage_trend.data,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });

        // User activity chart
        const activityCtx = document.getElementById('user-activity-chart').getContext('2d');
        new Chart(activityCtx, {
            type: 'doughnut',
            data: {
                labels: chartData.user_activity.labels,
                datasets: [{
                    data: chartData.user_activity.data,
                    backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#f5576c']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    updateAnalyticsInsights(insights) {
        const container = document.getElementById('analytics-insights-list');
        container.innerHTML = '';
        
        insights.forEach(insight => {
            const insightElement = document.createElement('div');
            insightElement.className = 'insight-item';
            insightElement.innerHTML = `
                <div class="insight-icon">
                    <i class="fas ${insight.icon}"></i>
                </div>
                <div class="insight-content">
                    <h5>${insight.title}</h5>
                    <p>${insight.description}</p>
                    ${insight.action ? `<button class="btn btn-sm btn-primary">${insight.action}</button>` : ''}
                </div>
            `;
            container.appendChild(insightElement);
        });
    }

    // Testing functionality
    addTestCase() {
        this.showModal('test-case-modal');
        this.clearTestCaseForm();
    }

    clearTestCaseForm() {
        document.getElementById('test-case-name').value = '';
        document.getElementById('test-case-description').value = '';
        document.getElementById('test-case-inputs').value = '';
        document.getElementById('test-case-expected').value = '';
    }

    saveTestCase() {
        const testCase = {
            name: document.getElementById('test-case-name').value,
            description: document.getElementById('test-case-description').value,
            inputs: document.getElementById('test-case-inputs').value,
            expected: document.getElementById('test-case-expected').value
        };

        if (!testCase.name || !testCase.inputs) {
            this.showNotification('Please fill in required fields', 'error');
            return;
        }

        try {
            testCase.inputs = JSON.parse(testCase.inputs);
        } catch (error) {
            this.showNotification('Invalid JSON in inputs', 'error');
            return;
        }

        this.currentTemplate.test_cases = this.currentTemplate.test_cases || [];
        this.currentTemplate.test_cases.push(testCase);
        
        this.updateTestCasesList();
        this.hideModal('test-case-modal');
        this.showNotification('Test case added successfully', 'success');
    }

    updateTestCasesList() {
        const container = document.getElementById('test-cases-container');
        container.innerHTML = '';
        
        if (!this.currentTemplate.test_cases || this.currentTemplate.test_cases.length === 0) {
            container.innerHTML = '<div class="test-placeholder"><i class="fas fa-info-circle"></i><p>No test cases defined</p></div>';
            return;
        }

        this.currentTemplate.test_cases.forEach((testCase, index) => {
            const testElement = document.createElement('div');
            testElement.className = 'test-case-item';
            testElement.innerHTML = `
                <div class="test-case-header">
                    <h5>${testCase.name}</h5>
                    <div class="test-case-actions">
                        <button class="btn btn-sm btn-primary" onclick="templateManager.runTestCase(${index})">
                            <i class="fas fa-play"></i> Run
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="templateManager.editTestCase(${index})">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="templateManager.deleteTestCase(${index})">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
                <div class="test-case-content">
                    <p>${testCase.description}</p>
                    <div class="test-case-details">
                        <div class="test-inputs">
                            <strong>Inputs:</strong>
                            <pre>${JSON.stringify(testCase.inputs, null, 2)}</pre>
                        </div>
                        <div class="test-expected">
                            <strong>Expected:</strong>
                            <pre>${testCase.expected}</pre>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(testElement);
        });
    }

    runTestCase(index) {
        const testCase = this.currentTemplate.test_cases[index];
        
        fetch('/api/templates/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                template_id: this.currentTemplate.id,
                test_case: testCase
            })
        })
        .then(response => response.json())
        .then(result => {
            this.displayTestResult(index, result);
        })
        .catch(error => {
            console.error('Error running test case:', error);
            this.showNotification('Error running test case', 'error');
        });
    }

    runAllTests() {
        if (!this.currentTemplate.test_cases || this.currentTemplate.test_cases.length === 0) {
            this.showNotification('No test cases to run', 'warning');
            return;
        }

        this.currentTemplate.test_cases.forEach((testCase, index) => {
            this.runTestCase(index);
        });
    }

    displayTestResult(index, result) {
        const container = document.getElementById('test-results-container');
        
        // Clear placeholder if exists
        const placeholder = container.querySelector('.test-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        const resultElement = document.createElement('div');
        resultElement.className = `test-result ${result.passed ? 'test-passed' : 'test-failed'}`;
        resultElement.innerHTML = `
            <div class="test-result-header">
                <h5>${this.currentTemplate.test_cases[index].name}</h5>
                <span class="test-status">
                    <i class="fas ${result.passed ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                    ${result.passed ? 'PASSED' : 'FAILED'}
                </span>
            </div>
            <div class="test-result-content">
                <div class="test-output">
                    <strong>Output:</strong>
                    <pre>${result.output}</pre>
                </div>
                ${!result.passed ? `
                    <div class="test-error">
                        <strong>Error:</strong>
                        <pre>${result.error}</pre>
                    </div>
                ` : ''}
                <div class="test-timing">
                    <small>Execution time: ${result.execution_time}ms</small>
                </div>
            </div>
        `;
        
        container.appendChild(resultElement);
    }

    // Utility functions
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas ${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close">&times;</button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
        
        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
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

    showModal(modalId) {
        document.getElementById(modalId).style.display = 'flex';
    }

    hideModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }

    showLoading() {
        document.getElementById('loading-overlay').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }
}

// Initialize template manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.templateManager = new TemplateManager();
});