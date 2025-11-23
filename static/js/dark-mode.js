/**
 * Dark Mode Manager
 * Shared dark mode functionality across all views
 */

const DarkMode = {
    init() {
        // Check localStorage for saved theme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
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
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
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
