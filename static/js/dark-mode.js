/**
 * Dark Mode Manager
 * Shared dark mode functionality across all views
 */

const DarkMode = {
    init() {
        // Check localStorage for saved dark mode (use 'darkMode' key to match base.html)
        const darkModeEnabled = localStorage.getItem('darkMode') !== 'false';
        if (darkModeEnabled) {
            document.body.classList.add('dark-mode');
            this.updateToggleButton(true);
        }

        // Setup toggle button listener
        const toggleBtn = document.getElementById('dark-mode-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());
        }
    },

    toggle() {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isDark ? 'true' : 'false');
        this.updateToggleButton(isDark);
    },

    updateToggleButton(isDark) {
        const toggleBtn = document.getElementById('dark-mode-toggle');
        if (toggleBtn) {
            toggleBtn.textContent = isDark ? '☀️' : '🌙';
            toggleBtn.title = isDark ? 'Tryb jasny' : 'Tryb ciemny';
        }
    },

    isDarkMode() {
        return document.body.classList.contains('dark-mode');
    }
};

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => DarkMode.init());
} else {
    DarkMode.init();
}
