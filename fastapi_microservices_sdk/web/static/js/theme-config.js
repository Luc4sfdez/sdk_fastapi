/**
 * Sistema de Configuración de Temas
 * Permite personalizar colores, fuentes y estilos
 */

class ThemeConfig {
    constructor() {
        this.currentLang = localStorage.getItem('sdk_language') || 'es';
        this.currentTheme = localStorage.getItem('sdk_theme') || 'default';
        this.translations = {};
        this.init();
    }

    async init() {
        await this.loadTranslations();
        this.applyTheme();
        this.setupLanguageSelector();
        this.setupThemeSelector();
    }

    // Cargar traducciones
    async loadTranslations() {
        try {
            const response = await fetch(`/static/i18n/${this.currentLang}.json`);
            this.translations = await response.json();
            this.applyTranslations();
        } catch (error) {
            console.error('Error loading translations:', error);
        }
    }

    // Aplicar traducciones
    applyTranslations() {
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.getTranslation(key);
            if (translation) {
                element.textContent = translation;
            }
        });

        // Actualizar placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            const translation = this.getTranslation(key);
            if (translation) {
                element.placeholder = translation;
            }
        });

        // Actualizar títulos
        document.querySelectorAll('[data-i18n-title]').forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            const translation = this.getTranslation(key);
            if (translation) {
                element.title = translation;
            }
        });
    }

    // Obtener traducción por clave
    getTranslation(key) {
        const keys = key.split('.');
        let value = this.translations;
        
        for (const k of keys) {
            if (value && typeof value === 'object' && k in value) {
                value = value[k];
            } else {
                return null;
            }
        }
        
        return typeof value === 'string' ? value : null;
    }

    // Cambiar idioma
    async changeLanguage(lang) {
        this.currentLang = lang;
        localStorage.setItem('sdk_language', lang);
        await this.loadTranslations();
        
        // Actualizar selector
        const selector = document.getElementById('languageSelector');
        if (selector) {
            selector.value = lang;
        }
    }

    // Configurar selector de idioma
    setupLanguageSelector() {
        const selector = document.getElementById('languageSelector');
        if (selector) {
            selector.value = this.currentLang;
            selector.addEventListener('change', (e) => {
                this.changeLanguage(e.target.value);
            });
        }
    }

    // Aplicar tema
    applyTheme() {
        const theme = this.getThemeConfig(this.currentTheme);
        const root = document.documentElement;

        // Aplicar variables CSS
        Object.entries(theme.colors).forEach(([key, value]) => {
            root.style.setProperty(`--color-${key}`, value);
        });

        Object.entries(theme.fonts).forEach(([key, value]) => {
            root.style.setProperty(`--font-${key}`, value);
        });

        // Aplicar clase de tema
        document.body.className = document.body.className.replace(/theme-\w+/g, '');
        document.body.classList.add(`theme-${this.currentTheme}`);
    }

    // Obtener configuración de tema
    getThemeConfig(themeName) {
        const themes = {
            default: {
                colors: {
                    primary: '#667eea',
                    secondary: '#764ba2',
                    accent: '#ff6b6b',
                    success: '#1cc88a',
                    warning: '#f6c23e',
                    danger: '#e74c3c',
                    background: '#f8f9fa',
                    surface: '#ffffff',
                    text: '#2c3e50'
                },
                fonts: {
                    primary: "'Poppins', sans-serif",
                    secondary: "'Inter', sans-serif",
                    mono: "'Fira Code', monospace"
                }
            },
            dark: {
                colors: {
                    primary: '#667eea',
                    secondary: '#764ba2',
                    accent: '#ff6b6b',
                    success: '#1cc88a',
                    warning: '#f6c23e',
                    danger: '#e74c3c',
                    background: '#1a1a1a',
                    surface: '#2d2d2d',
                    text: '#ffffff'
                },
                fonts: {
                    primary: "'Poppins', sans-serif",
                    secondary: "'Inter', sans-serif",
                    mono: "'Fira Code', monospace"
                }
            },
            corporate: {
                colors: {
                    primary: '#2c5aa0',
                    secondary: '#1e3a5f',
                    accent: '#ff8c00',
                    success: '#28a745',
                    warning: '#ffc107',
                    danger: '#dc3545',
                    background: '#f4f6f9',
                    surface: '#ffffff',
                    text: '#333333'
                },
                fonts: {
                    primary: "'Roboto', sans-serif",
                    secondary: "'Open Sans', sans-serif",
                    mono: "'Source Code Pro', monospace"
                }
            }
        };

        return themes[themeName] || themes.default;
    }

    // Configurar selector de tema
    setupThemeSelector() {
        const selector = document.getElementById('themeSelector');
        if (selector) {
            selector.value = this.currentTheme;
            selector.addEventListener('change', (e) => {
                this.changeTheme(e.target.value);
            });
        }
    }

    // Cambiar tema
    changeTheme(theme) {
        this.currentTheme = theme;
        localStorage.setItem('sdk_theme', theme);
        this.applyTheme();
    }

    // Personalizar colores
    customizeColors(colors) {
        const root = document.documentElement;
        Object.entries(colors).forEach(([key, value]) => {
            root.style.setProperty(`--color-${key}`, value);
        });
        
        // Guardar personalización
        localStorage.setItem('sdk_custom_colors', JSON.stringify(colors));
    }

    // Personalizar fuentes
    customizeFonts(fonts) {
        const root = document.documentElement;
        Object.entries(fonts).forEach(([key, value]) => {
            root.style.setProperty(`--font-${key}`, value);
        });
        
        // Guardar personalización
        localStorage.setItem('sdk_custom_fonts', JSON.stringify(fonts));
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.themeConfig = new ThemeConfig();
});

// Función global para cambiar idioma
function changeLanguage(lang) {
    if (window.themeConfig) {
        window.themeConfig.changeLanguage(lang);
    }
}

// Función global para cambiar tema
function changeTheme(theme) {
    if (window.themeConfig) {
        window.themeConfig.changeTheme(theme);
    }
}