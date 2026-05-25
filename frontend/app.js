/**
 * SEA-1 MCQ Battle Platform - Central JavaScript Controller
 * Handles Session management, API fetch wrappers, Navbar rendering, and UI themes.
 */

const API_BASE = '/api';

// --- Session & Storage Management ---
const Auth = {
    saveToken(token) {
        localStorage.setItem('mcq_jwt_token', token);
    },
    
    getToken() {
        return localStorage.getItem('mcq_jwt_token');
    },
    
    clearSession() {
        localStorage.removeItem('mcq_jwt_token');
        localStorage.removeItem('mcq_user');
        localStorage.removeItem('current_quiz_questions');
        localStorage.removeItem('last_quiz_results');
    },
    
    saveUser(user) {
        localStorage.setItem('mcq_user', JSON.stringify(user));
    },
    
    getUser() {
        const user = localStorage.getItem('mcq_user');
        return user ? JSON.parse(user) : null;
    },
    
    isAuthenticated() {
        return !!this.getToken();
    },

    logout() {
        // Stateless API logout call (optional but polite)
        fetch(`${API_BASE}/auth/logout`, { method: 'POST' }).finally(() => {
            this.clearSession();
            window.location.href = 'login.html';
        });
    }
};

// --- Secure API Fetch Wrapper ---
async function fetchAPI(endpoint, options = {}) {
    const token = Auth.getToken();
    
    // Set headers
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
        ...options,
        headers
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, config);
        
        // Auto handle session expiration
        if (response.status === 401) {
            console.warn("Session expired or unauthorized. Redirecting to login.");
            Auth.clearSession();
            if (!window.location.pathname.endsWith('login.html') && !window.location.pathname.endsWith('register.html')) {
                window.location.href = 'login.html';
            }
            return { error: true, msg: "Session expired. Please log in again." };
        }
        
        const data = await response.json();
        if (!response.ok) {
            return { error: true, msg: data.msg || "Request failed" };
        }
        
        return data;
    } catch (err) {
        console.error(`API Error on ${endpoint}:`, err);
        return { error: true, msg: "Network error. Make sure the server is running." };
    }
}

// --- Page Guards ---
function protectPage() {
    if (!Auth.isAuthenticated()) {
        window.location.href = 'login.html';
    }
}

function redirectIfLoggedIn() {
    if (Auth.isAuthenticated()) {
        window.location.href = 'dashboard.html';
    }
}

// --- Dynamic Common UI Builders ---
function renderNavbar() {
    const navbarContainer = document.getElementById('navbar-container');
    if (!navbarContainer) return;

    const isLoggedIn = Auth.isAuthenticated();
    const user = Auth.getUser();

    let navLinks = '';
    if (isLoggedIn) {
        const isAdmin = user && user.username === 'admin';
        navLinks = `
            <a href="dashboard.html" class="px-3 py-2 rounded-lg text-sm font-medium hover:text-blue-400 transition-colors">Dashboard</a>
            <a href="quiz.html" class="px-3 py-2 rounded-lg text-sm font-medium hover:text-blue-400 transition-colors">Quiz Arena</a>
            <a href="leaderboard.html" class="px-3 py-2 rounded-lg text-sm font-medium hover:text-blue-400 transition-colors">Leaderboard</a>
            <a href="profile.html" class="px-3 py-2 rounded-lg text-sm font-medium hover:text-blue-400 transition-colors">Profile</a>
            ${isAdmin ? `<a href="admin.html" class="px-3 py-2 rounded-lg text-sm font-medium hover:text-purple-400 transition-colors text-purple-300 border border-purple-500/20 bg-purple-500/5">Admin</a>` : ''}
        `;
    } else {
        navLinks = `
            <a href="index.html" class="px-3 py-2 rounded-lg text-sm font-medium hover:text-blue-400 transition-colors">Home</a>
            <a href="leaderboard.html" class="px-3 py-2 rounded-lg text-sm font-medium hover:text-blue-400 transition-colors">Leaderboard</a>
        `;
    }

    const authSection = isLoggedIn && user
        ? `
            <div class="flex items-center gap-4">
                <div class="hidden md:flex flex-col text-right">
                    <span class="text-xs text-gray-400">Streak: 🔥 ${user.streak || 0}</span>
                    <span class="text-sm font-semibold text-blue-400">${user.username}</span>
                </div>
                <div class="h-8 w-8 rounded-full ${getBadgeClass(user.badge)} flex items-center justify-center font-bold text-white text-xs ring-2 ring-white/10">
                    ${user.username[0].toUpperCase()}
                </div>
                <button onclick="Auth.logout()" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 transition-all cursor-pointer">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </button>
            </div>
          `
        : `
            <div class="flex items-center gap-2">
                <a href="login.html" class="px-3 py-1.5 rounded-lg text-sm font-semibold hover:text-white text-gray-300 transition-all">Login</a>
                <a href="register.html" class="px-4 py-2 rounded-lg text-sm font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-500/20 transition-all">Register</a>
            </div>
          `;

    navbarContainer.innerHTML = `
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <!-- Logo -->
                <div class="flex items-center">
                    <a href="index.html" class="flex items-center gap-2">
                        <div class="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <i class="fas fa-graduation-cap text-white text-lg"></i>
                        </div>
                        <span class="text-lg font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent font-display">
                            SEA-1 MCQ Battle
                        </span>
                    </a>
                </div>
                <!-- Links -->
                <nav class="hidden md:flex space-x-2 text-gray-300">
                    ${navLinks}
                </nav>
                <!-- Auth / User Actions -->
                <div>
                    ${authSection}
                </div>
            </div>
        </div>
    `;
}

// --- Dynamic helper utilities ---
function getBadgeClass(badge) {
    const b = (badge || 'Bronze').toLowerCase();
    if (b === 'platinum') return 'badge-platinum';
    if (b === 'gold') return 'badge-gold';
    if (b === 'silver') return 'badge-silver';
    return 'badge-bronze';
}

function formatDate(isoString) {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Automatically init navbar if script loaded
document.addEventListener('DOMContentLoaded', () => {
    renderNavbar();
});
