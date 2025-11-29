/**
 * Smart Task Analyzer - Frontend JavaScript
 * 
 * Handles user interactions, API communication, and dynamic UI updates.
 */

// Configuration
// For local development: 'http://127.0.0.1:8000/api/tasks'
// For production: Update this to your deployed backend URL
const API_BASE_URL = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
    ? 'http://127.0.0.1:8000/api/tasks'
    : 'https://marlness.pythonanywhere.com/api/tasks';

// State
let tasks = [];
let taskIdCounter = 1;
let lastAnalysisResult = null;
let currentView = 'list';

// DOM Elements
const elements = {
    // Input toggle
    toggleBtns: document.querySelectorAll('.toggle-btn'),
    formMode: document.getElementById('form-mode'),
    jsonMode: document.getElementById('json-mode'),
    
    // Form elements
    taskForm: document.getElementById('task-form'),
    titleInput: document.getElementById('task-title'),
    dueDateInput: document.getElementById('due-date'),
    hoursInput: document.getElementById('estimated-hours'),
    importanceInput: document.getElementById('importance'),
    importanceValue: document.getElementById('importance-value'),
    dependenciesInput: document.getElementById('dependencies'),
    
    // JSON input
    jsonInput: document.getElementById('json-input'),
    parseJsonBtn: document.getElementById('parse-json'),
    
    // Task list
    taskList: document.getElementById('task-list'),
    taskCount: document.getElementById('task-count'),
    clearTasksBtn: document.getElementById('clear-tasks'),
    
    // Strategy
    strategyInputs: document.querySelectorAll('input[name="strategy"]'),
    strategyOptions: document.querySelectorAll('.strategy-option'),
    
    // Analyze button
    analyzeBtn: document.getElementById('analyze-btn'),
    
    // Results
    emptyState: document.getElementById('empty-state'),
    loadingState: document.getElementById('loading-state'),
    errorState: document.getElementById('error-state'),
    errorMessage: document.getElementById('error-message'),
    retryBtn: document.getElementById('retry-btn'),
    resultsContainer: document.getElementById('results-container'),
    resultsMeta: document.getElementById('results-meta'),
    warningsSection: document.getElementById('warnings-section'),
    warningsContent: document.getElementById('warnings-content'),
    summaryText: document.getElementById('summary-text'),
    resultsList: document.getElementById('results-list'),
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    // Set default due date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    elements.dueDateInput.valueAsDate = tomorrow;
    
    // Event listeners
    setupEventListeners();
    
    // Update UI state
    updateAnalyzeButton();
}

function setupEventListeners() {
    // Input mode toggle
    elements.toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => handleModeToggle(btn.dataset.mode));
    });
    
    // Form submission
    elements.taskForm.addEventListener('submit', handleFormSubmit);
    
    // Importance slider
    elements.importanceInput.addEventListener('input', (e) => {
        elements.importanceValue.textContent = e.target.value;
    });
    
    // JSON parse
    elements.parseJsonBtn.addEventListener('click', handleJsonParse);
    
    // Clear tasks
    elements.clearTasksBtn.addEventListener('click', clearAllTasks);
    
    // Strategy selection
    elements.strategyOptions.forEach(option => {
        option.addEventListener('click', () => {
            elements.strategyOptions.forEach(o => o.classList.remove('selected'));
            option.classList.add('selected');
        });
    });
    
    // Analyze button
    elements.analyzeBtn.addEventListener('click', handleAnalyze);
    
    // Retry button
    elements.retryBtn.addEventListener('click', handleAnalyze);
}

// Mode Toggle
function handleModeToggle(mode) {
    elements.toggleBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    
    elements.formMode.classList.toggle('hidden', mode !== 'form');
    elements.jsonMode.classList.toggle('hidden', mode !== 'json');
}

// Form Submission
function handleFormSubmit(e) {
    e.preventDefault();
    
    const task = {
        id: `task-${taskIdCounter++}`,
        title: elements.titleInput.value.trim(),
        due_date: elements.dueDateInput.value,
        estimated_hours: parseInt(elements.hoursInput.value) || 4,
        importance: parseInt(elements.importanceInput.value) || 5,
        dependencies: parseDependencies(elements.dependenciesInput.value),
    };
    
    // Validate
    if (!task.title || !task.due_date) {
        showError('Please fill in all required fields');
        return;
    }
    
    addTask(task);
    resetForm();
}

function parseDependencies(input) {
    if (!input || !input.trim()) return [];
    return input.split(',')
        .map(d => d.trim())
        .filter(d => d.length > 0);
}

function resetForm() {
    elements.titleInput.value = '';
    elements.hoursInput.value = '';
    elements.importanceInput.value = '5';
    elements.importanceValue.textContent = '5';
    elements.dependenciesInput.value = '';
    elements.titleInput.focus();
}

// Task Management
function addTask(task) {
    tasks.push(task);
    renderTaskList();
    updateAnalyzeButton();
}

function removeTask(taskId) {
    tasks = tasks.filter(t => t.id !== taskId);
    renderTaskList();
    updateAnalyzeButton();
}

function clearAllTasks() {
    tasks = [];
    taskIdCounter = 1;
    renderTaskList();
    updateAnalyzeButton();
    showEmptyState();
}

function renderTaskList() {
    elements.taskCount.textContent = tasks.length;
    
    if (tasks.length === 0) {
        elements.taskList.innerHTML = '<li class="empty-list-message" style="color: var(--text-muted); text-align: center; padding: 1rem;">No tasks added yet</li>';
        return;
    }
    
    elements.taskList.innerHTML = tasks.map(task => `
        <li class="task-list-item" data-id="${task.id}">
            <div class="task-list-item-content">
                <span class="task-list-item-title">${escapeHtml(task.title)}</span>
                <span class="task-list-item-meta">
                    📅 ${formatDate(task.due_date)} • ⏱️ ${task.estimated_hours}h • ⭐ ${task.importance}/10
                </span>
            </div>
            <button class="task-list-item-remove" onclick="removeTask('${task.id}')" title="Remove task">
                ✕
            </button>
        </li>
    `).join('');
}

// JSON Parsing
function handleJsonParse() {
    const jsonText = elements.jsonInput.value.trim();
    
    if (!jsonText) {
        showError('Please enter JSON data');
        return;
    }
    
    try {
        const parsed = JSON.parse(jsonText);
        const taskArray = Array.isArray(parsed) ? parsed : [parsed];
        
        // Validate and add tasks
        let addedCount = 0;
        const errors = [];
        
        taskArray.forEach((task, index) => {
            if (!task.title) {
                errors.push(`Task ${index + 1}: Missing title`);
                return;
            }
            if (!task.due_date) {
                errors.push(`Task ${index + 1}: Missing due_date`);
                return;
            }
            
            // Ensure ID
            if (!task.id) {
                task.id = `task-${taskIdCounter++}`;
            }
            
            // Set defaults
            task.estimated_hours = task.estimated_hours || 4;
            task.importance = task.importance || 5;
            task.dependencies = task.dependencies || [];
            
            addTask(task);
            addedCount++;
        });
        
        if (addedCount > 0) {
            elements.jsonInput.value = '';
            handleModeToggle('form');
            
            if (errors.length > 0) {
                showError(`Added ${addedCount} task(s). Errors: ${errors.join('; ')}`);
            }
        } else {
            showError(`No valid tasks found. ${errors.join('; ')}`);
        }
        
    } catch (e) {
        showError(`Invalid JSON: ${e.message}`);
    }
}

// Analyze Tasks
async function handleAnalyze() {
    if (tasks.length === 0) {
        showError('Please add at least one task');
        return;
    }
    
    const strategy = document.querySelector('input[name="strategy"]:checked').value;
    
    showLoadingState();
    
    try {
        const response = await fetch(`${API_BASE_URL}/analyze/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                tasks: tasks,
                strategy: strategy,
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Server error: ${response.status}`);
        }
        
        const data = await response.json();
        renderResults(data);
        
    } catch (error) {
        console.error('Analysis failed:', error);
        showErrorState(error.message || 'Failed to analyze tasks. Make sure the backend server is running.');
    }
}

// Results Rendering
function renderResults(data) {
    hideAllStates();
    elements.resultsContainer.classList.remove('hidden');
    lastAnalysisResult = data;
    
    // Update meta
    elements.resultsMeta.textContent = `${data.tasks.length} tasks • ${data.strategy.replace('_', ' ')}`;
    
    // Render warnings
    if (data.warnings && data.warnings.length > 0) {
        elements.warningsSection.classList.remove('hidden');
        elements.warningsContent.innerHTML = data.warnings.map(w => `<div>${escapeHtml(w)}</div>`).join('');
    } else {
        elements.warningsSection.classList.add('hidden');
    }
    
    // Render summary
    elements.summaryText.textContent = data.summary || 'Tasks analyzed and prioritized.';
    
    // Set up view tabs
    setupViewTabs();
    
    // Render all views
    renderPriorityList(data.tasks);
    renderEisenhowerMatrix(data.eisenhower_matrix);
    renderDependencyGraph(data.dependency_graph);
    
    // Update learning stats
    updateLearningStats();
}

// Setup view tabs
function setupViewTabs() {
    const tabs = document.querySelectorAll('.view-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const view = tab.dataset.view;
            switchView(view);
        });
    });
}

// Switch between views
function switchView(view) {
    currentView = view;
    
    // Update tab states
    document.querySelectorAll('.view-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.view === view);
    });
    
    // Update view visibility
    document.querySelectorAll('.view-content').forEach(content => {
        content.classList.add('hidden');
    });
    document.getElementById(`${view}-view`).classList.remove('hidden');
}

// Render Priority List with feedback buttons
function renderPriorityList(tasks) {
    const resultsList = document.getElementById('results-list');
    resultsList.innerHTML = tasks.map((task, index) => {
        const rank = index + 1;
        const rankClass = rank <= 3 ? `rank-${rank}` : '';
        const priorityClass = `priority-${task.priority_level.toLowerCase()}`;
        
        return `
            <div class="result-card" style="animation-delay: ${index * 0.1}s" data-task-id="${task.id}">
                <div class="result-card-header">
                    <div class="result-card-rank ${rankClass}">${rank}</div>
                    <div class="result-card-info">
                        <div class="result-card-title">
                            ${escapeHtml(task.title)}
                            ${task.is_overdue ? '<span class="overdue-badge">OVERDUE</span>' : ''}
                        </div>
                        <div class="result-card-meta">
                            <span>📅 ${formatDate(task.due_date)}</span>
                            <span>⏱️ ${task.estimated_hours}h</span>
                            <span>⭐ ${task.importance}/10</span>
                            ${task.blocking_count > 0 ? `<span>🔗 Blocks ${task.blocking_count}</span>` : ''}
                            ${task.working_days_until_due !== undefined ? `<span>📆 ${task.working_days_until_due} work days</span>` : ''}
                        </div>
                    </div>
                    <div class="result-card-score">
                        <span class="score-value ${priorityClass}">${task.priority_score.toFixed(1)}</span>
                        <span class="priority-badge ${priorityClass}">${task.priority_level}</span>
                    </div>
                </div>
                <div class="result-card-explanation">
                    ${escapeHtml(task.explanation)}
                </div>
                <div class="feedback-buttons">
                    <button class="feedback-btn helpful" onclick="sendFeedback('${task.id}', true, this)">
                        👍 Helpful
                    </button>
                    <button class="feedback-btn not-helpful" onclick="sendFeedback('${task.id}', false, this)">
                        👎 Not Helpful
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Render Eisenhower Matrix
function renderEisenhowerMatrix(matrix) {
    if (!matrix) return;
    
    const quadrants = {
        'do_first': document.querySelector('#quadrant-do-first .quadrant-tasks'),
        'schedule': document.querySelector('#quadrant-schedule .quadrant-tasks'),
        'delegate': document.querySelector('#quadrant-delegate .quadrant-tasks'),
        'eliminate': document.querySelector('#quadrant-eliminate .quadrant-tasks'),
    };
    
    Object.entries(quadrants).forEach(([key, element]) => {
        if (!element) return;
        const tasks = matrix[key] || [];
        
        if (tasks.length === 0) {
            element.innerHTML = '<div class="quadrant-task" style="opacity: 0.5; text-align: center;">No tasks</div>';
        } else {
            element.innerHTML = tasks.map(task => `
                <div class="quadrant-task">
                    <span class="quadrant-task-title">${escapeHtml(task.title)}</span>
                    <span class="quadrant-task-score">${task.priority_score.toFixed(1)}</span>
                </div>
            `).join('');
        }
    });
}

// Render Dependency Graph
function renderDependencyGraph(graph) {
    const container = document.getElementById('graph-container');
    const info = document.getElementById('graph-info');
    
    if (!graph || graph.total_edges === 0) {
        container.innerHTML = `
            <div class="no-dependencies">
                <div class="no-dependencies-icon">🔗</div>
                <p>No dependencies defined between tasks</p>
            </div>
        `;
        info.innerHTML = '';
        return;
    }
    
    // Simple visualization using positioned divs
    const nodes = graph.nodes;
    const edges = graph.edges;
    
    // Calculate positions in a circle
    const containerWidth = 500;
    const containerHeight = 300;
    const centerX = containerWidth / 2;
    const centerY = containerHeight / 2;
    const radius = Math.min(containerWidth, containerHeight) / 3;
    
    container.style.width = containerWidth + 'px';
    container.style.height = containerHeight + 'px';
    container.style.position = 'relative';
    
    // Position nodes in a circle
    const nodePositions = {};
    nodes.forEach((node, index) => {
        const angle = (2 * Math.PI * index) / nodes.length - Math.PI / 2;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);
        nodePositions[node.id] = { x, y };
    });
    
    // Render nodes
    let html = '';
    nodes.forEach(node => {
        const pos = nodePositions[node.id];
        const circularClass = node.in_cycle ? 'circular' : '';
        html += `
            <div class="graph-node ${circularClass}" 
                 style="left: ${pos.x - 50}px; top: ${pos.y - 15}px; min-width: 100px; text-align: center;"
                 title="${escapeHtml(node.title)}">
                ${escapeHtml(node.title.substring(0, 15))}${node.title.length > 15 ? '...' : ''}
            </div>
        `;
    });
    
    // Render edges (simplified - just show connections info)
    container.innerHTML = html;
    
    // Show graph info
    const circularWarning = graph.has_circular 
        ? `<span style="color: var(--accent-red);">⚠️ Circular dependencies detected!</span><br>` 
        : '';
    
    info.innerHTML = `
        ${circularWarning}
        <strong>${graph.total_nodes}</strong> tasks • 
        <strong>${graph.total_edges}</strong> dependencies
        ${graph.circular_dependencies.length > 0 
            ? `<br>Cycles: ${graph.circular_dependencies.map(c => c.join(' → ')).join('; ')}` 
            : ''}
    `;
}

// Send feedback to learning system
async function sendFeedback(taskId, wasHelpful, buttonElement) {
    const taskData = lastAnalysisResult?.tasks.find(t => t.id === taskId);
    if (!taskData) return;
    
    // Disable both buttons
    const container = buttonElement.parentElement;
    container.querySelectorAll('.feedback-btn').forEach(btn => {
        btn.classList.add('submitted');
        btn.disabled = true;
    });
    buttonElement.textContent = wasHelpful ? '👍 Thanks!' : '👎 Noted';
    
    try {
        const response = await fetch(`${API_BASE_URL}/feedback/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task: taskData,
                was_helpful: wasHelpful
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            updateLearningStats(data.statistics);
        }
    } catch (error) {
        console.error('Failed to send feedback:', error);
    }
}

// Update learning system stats display
async function updateLearningStats(stats) {
    const statsElement = document.getElementById('feedback-stats');
    if (!statsElement) return;
    
    if (!stats) {
        try {
            const response = await fetch(`${API_BASE_URL}/feedback/`);
            if (response.ok) {
                const data = await response.json();
                stats = data.statistics;
            }
        } catch (error) {
            statsElement.textContent = 'No feedback yet';
            return;
        }
    }
    
    if (stats && stats.total_feedback > 0) {
        const rate = (stats.helpful_rate * 100).toFixed(0);
        statsElement.textContent = `${stats.total_feedback} feedback(s) • ${rate}% helpful`;
        if (stats.is_learning) {
            statsElement.textContent += ' • 🎓 Learning active';
        }
    } else {
        statsElement.textContent = 'No feedback yet - rate suggestions to improve!';
    }
}

// Make sendFeedback available globally
window.sendFeedback = sendFeedback;

// UI State Management
function updateAnalyzeButton() {
    elements.analyzeBtn.disabled = tasks.length === 0;
}

function showEmptyState() {
    hideAllStates();
    elements.emptyState.classList.remove('hidden');
}

function showLoadingState() {
    hideAllStates();
    elements.loadingState.classList.remove('hidden');
    elements.analyzeBtn.disabled = true;
    elements.analyzeBtn.querySelector('.btn-text').textContent = 'Analyzing...';
    elements.analyzeBtn.querySelector('.loading-spinner').classList.remove('hidden');
}

function showErrorState(message) {
    hideAllStates();
    elements.errorState.classList.remove('hidden');
    elements.errorMessage.textContent = message;
    resetAnalyzeButton();
}

function hideAllStates() {
    elements.emptyState.classList.add('hidden');
    elements.loadingState.classList.add('hidden');
    elements.errorState.classList.add('hidden');
    elements.resultsContainer.classList.add('hidden');
    resetAnalyzeButton();
}

function resetAnalyzeButton() {
    elements.analyzeBtn.disabled = tasks.length === 0;
    elements.analyzeBtn.querySelector('.btn-text').textContent = 'Analyze Tasks';
    elements.analyzeBtn.querySelector('.loading-spinner').classList.add('hidden');
}

function showError(message) {
    // Simple alert for form errors - could be replaced with toast notification
    alert(message);
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    try {
        const date = new Date(dateStr + 'T00:00:00');
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const diffDays = Math.floor((date - today) / (1000 * 60 * 60 * 24));
        
        if (diffDays < 0) {
            return `${Math.abs(diffDays)}d overdue`;
        } else if (diffDays === 0) {
            return 'Today';
        } else if (diffDays === 1) {
            return 'Tomorrow';
        } else if (diffDays <= 7) {
            return `In ${diffDays} days`;
        } else {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }
    } catch {
        return dateStr;
    }
}

// Make removeTask available globally for onclick handlers
window.removeTask = removeTask;

