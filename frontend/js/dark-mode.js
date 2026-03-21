/**
 * Dark Mode Toggle Functionality
 * Add this to your main JavaScript file or include separately
 */

// Dark Mode Manager
class DarkModeManager {
    constructor() {
        this.themeKey = 'iatrs-theme';
        this.init();
    }

    init() {
        // Load saved theme or default to light mode
        const savedTheme = localStorage.getItem(this.themeKey) || 'light';
        this.setTheme(savedTheme);
        
        // Create toggle button if it doesn't exist
        this.createToggleButton();
        
        // Listen for system theme changes
        this.listenForSystemTheme();
    }

    setTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            document.body.classList.add('dark-mode');
        } else {
            document.documentElement.removeAttribute('data-theme');
            document.body.classList.remove('dark-mode');
        }
        
        localStorage.setItem(this.themeKey, theme);
        this.updateToggleButton(theme);
    }

    toggle() {
        const currentTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    createToggleButton() {
        // Check if button already exists
        if (document.getElementById('theme-toggle')) {
            return;
        }

        const button = document.createElement('button');
        button.id = 'theme-toggle';
        button.className = 'theme-toggle';
        button.setAttribute('aria-label', 'Toggle dark mode');
        button.innerHTML = '🌙';
        
        button.addEventListener('click', () => this.toggle());
        
        document.body.appendChild(button);
    }

    updateToggleButton(theme) {
        const button = document.getElementById('theme-toggle');
        if (button) {
            button.innerHTML = theme === 'dark' ? '☀️' : '🌙';
            button.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
        }
    }

    listenForSystemTheme() {
        // Listen for system theme changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                // Only auto-switch if user hasn't set a preference
                if (!localStorage.getItem(this.themeKey)) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }

    // Get current theme
    getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }

    // Check if dark mode is active
    isDarkMode() {
        return this.getCurrentTheme() === 'dark';
    }
}

// Initialize dark mode when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.darkMode = new DarkModeManager();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DarkModeManager;
}
