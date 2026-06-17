let menuIcon = document.querySelector('#menu-icon');
let navbar = document.querySelector('.navbar');
let themeBtn = document.querySelector('#theme-btn');

// Theme variables
const themes = ['dark', 'light', 'blue', 'purple', 'green'];
let currentThemeIndex = 0;

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('selectedTheme') || 'dark';
    currentThemeIndex = themes.indexOf(savedTheme);
    applyTheme(savedTheme);
});

// Menu toggle functionality
menuIcon.onclick = () => {
    menuIcon.classList.toggle('bx-x');
    navbar.classList.toggle('active');
};

// Theme switching functionality
themeBtn.onclick = () => {
    currentThemeIndex = (currentThemeIndex + 1) % themes.length;
    const newTheme = themes[currentThemeIndex];
    applyTheme(newTheme);
    localStorage.setItem('selectedTheme', newTheme);
    
    // Add rotation animation
    themeBtn.classList.add('active');
    setTimeout(() => {
        themeBtn.classList.remove('active');
    }, 600);
};

// Function to apply theme
function applyTheme(theme) {
    const body = document.body;
    
    // Remove all theme classes
    themes.forEach(t => {
        if (t !== 'dark') {
            body.classList.remove(`${t}-theme`);
        }
    });
    
    // Apply new theme
    if (theme !== 'dark') {
        body.classList.add(`${theme}-theme`);
    }
    
    // Add smooth transition
    body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
}