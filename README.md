# Smart Task Analyzer

An intelligent task prioritization system that helps you decide what to work on first by analyzing multiple factors including urgency, importance, effort, and task dependencies.

![Smart Task Analyzer](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.0+-green.svg)
![Tests](https://img.shields.io/badge/Tests-45%2B%20Passing-success.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌟 Features

### Core Features
- ✅ **Intelligent Priority Scoring** - Multi-factor algorithm considering urgency, importance, effort, and dependencies
- ✅ **4 Sorting Strategies** - Smart Balance, Fastest Wins, High Impact, Deadline Driven
- ✅ **Circular Dependency Detection** - Automatically detects and warns about task cycles
- ✅ **Beautiful Dark UI** - Modern, responsive interface with color-coded priorities

### Bonus Features (All Implemented!)
- ✅ **Date Intelligence** - Excludes weekends and holidays from urgency calculation
- ✅ **Eisenhower Matrix View** - Visual 2D grid (Urgent vs Important) with 4 quadrants
- ✅ **Dependency Graph Visualization** - Interactive graph showing task relationships
- ✅ **Learning System** - Feedback mechanism that adjusts algorithm weights over time
- ✅ **Comprehensive Unit Tests** - 45+ test cases covering all features

## 📋 Table of Contents

- [Features](#-features)
- [Live Demo](#-live-demo)
- [Setup Instructions](#-setup-instructions)
- [Algorithm Explanation](#-algorithm-explanation)
- [Bonus Features](#-bonus-features-detailed)
- [API Documentation](#-api-documentation)
- [Design Decisions](#-design-decisions)
- [Time Breakdown](#-time-breakdown)
- [Project Structure](#-project-structure)

## 🚀 Live Demo

- **Frontend**: [https://marlness.github.io/smart-task-analyzer/](https://marlness.github.io/smart-task-analyzer/)
- **GitHub Repository**: [https://github.com/Marlness/smart-task-analyzer](https://github.com/Marlness/smart-task-analyzer)

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Marlness/smart-task-analyzer.git
   cd smart-task-analyzer
   ```

2. **Create and activate a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Start the Django development server**
   ```bash
   python manage.py runserver
   ```

6. **Open the frontend**
   - Open `frontend/index.html` in your browser
   - Or use a local server: `python -m http.server 5500 --directory frontend`
   - Then navigate to `http://localhost:5500`

### Running Tests

```bash
# Run all tests
python manage.py test tasks

# Run with verbose output
python manage.py test tasks -v 2
```

## 🧠 Algorithm Explanation

### Core Scoring System

The Smart Task Analyzer uses a **weighted multi-factor scoring algorithm** that considers four key dimensions to calculate task priority:

#### 1. Urgency Score (Default Weight: 35%)

Urgency is calculated based on the number of **working days** until the task's due date. The algorithm uses an **exponential decay function** where urgency increases rapidly as deadlines approach:

- **Overdue tasks**: Maximum urgency (100) plus penalty proportional to days overdue
- **Due today**: Maximum urgency score of 100
- **1-3 days**: High urgency (85-95), exponential increase
- **4-7 days**: Moderate urgency (50-70)
- **1-2 weeks**: Lower urgency (30-50)
- **30+ days**: Minimal urgency (5-15)

**Date Intelligence**: The algorithm automatically excludes weekends and major holidays (New Year's Day, Independence Day, Thanksgiving, Christmas) when calculating working days until due.

#### 2. Importance Score (Default Weight: 30%)

The user-provided importance rating (1-10) is normalized to a 0-100 scale with a slight curve applied to higher values. This makes the difference between 9 and 10 more meaningful than between 4 and 5.

#### 3. Effort/Quick Wins Score (Default Weight: 20%)

Uses an **inverse logarithmic relationship** where lower-effort tasks score higher:
- 1-hour tasks: ~90+ score
- 4-hour tasks: ~60 score
- 8-hour tasks: ~45 score
- 40-hour tasks: ~10 score

#### 4. Dependency Impact Score (Default Weight: 15%)

Tasks that block other tasks receive bonus points. Each blocked task adds 20 points (capped at 100). This prevents workflow bottlenecks by prioritizing blockers.

### Strategy Presets

| Strategy | Urgency | Importance | Effort | Dependency | Best For |
|----------|---------|------------|--------|------------|----------|
| **Smart Balance** | 35% | 30% | 20% | 15% | General use |
| **Fastest Wins** | 15% | 15% | 55% | 15% | Building momentum |
| **High Impact** | 20% | 55% | 10% | 15% | Strategic focus |
| **Deadline Driven** | 55% | 20% | 10% | 15% | Deadline pressure |

### Edge Cases Handled

1. **Overdue tasks**: Heavily weighted but still ranked by other factors
2. **Missing data**: Sensible defaults applied (importance=5, hours=4)
3. **Invalid dates**: Treated as due today (high urgency)
4. **Circular dependencies**: Detected, flagged, and visually highlighted
5. **Extreme values**: Clamped to reasonable ranges
6. **Weekends/Holidays**: Excluded from working days calculation

## ⭐ Bonus Features (Detailed)

### 1. 📅 Date Intelligence

The algorithm considers real working days instead of calendar days:

```python
# Holidays excluded from urgency calculation
HOLIDAYS = {
    (1, 1),    # New Year's Day
    (7, 4),    # Independence Day
    (12, 25),  # Christmas
    (12, 31),  # New Year's Eve
    (11, 28),  # Thanksgiving
    (11, 29),  # Day after Thanksgiving
}
```

**Example**: A task due Monday when it's Friday has only 1 working day, not 3 calendar days.

### 2. 📊 Eisenhower Matrix View

Tasks are automatically categorized into 4 quadrants:

| Quadrant | Criteria | Action |
|----------|----------|--------|
| 🔥 **Do First** | Urgent + Important | Handle immediately |
| 📅 **Schedule** | Important, Not Urgent | Plan for later |
| 👥 **Delegate** | Urgent, Not Important | Consider delegating |
| 🗑️ **Eliminate** | Neither | Deprioritize or remove |

**Classification Logic**:
- Urgent: urgency_score >= 60 OR is_overdue
- Important: importance >= 7

### 3. 🔗 Dependency Graph Visualization

- Visual representation of task dependencies
- Nodes positioned in a circular layout
- **Circular dependencies** are highlighted in red with ⚠️ warning
- Shows total nodes, edges, and any detected cycles

### 4. 🧠 Learning System

The algorithm improves based on user feedback:

```
POST /api/tasks/feedback/
{
    "task": { ... task data ... },
    "was_helpful": true
}
```

**How it works**:
1. Users rate suggestions with 👍 (Helpful) or 👎 (Not Helpful)
2. System tracks feedback patterns
3. Weight adjustments are applied (capped at ±15% per factor)
4. After 3+ feedbacks, learning is active
5. Weights can be reset via DELETE endpoint

### 5. 🧪 Comprehensive Unit Tests

45+ test cases covering:
- Urgency score calculation
- Importance normalization
- Effort/quick wins scoring
- Dependency impact
- Circular dependency detection
- Edge cases (missing data, invalid dates)
- Date intelligence (weekends, holidays)
- Eisenhower Matrix quadrant assignment
- Dependency graph building
- Learning system feedback

## 📡 API Documentation

### POST /api/tasks/analyze/

Analyze and prioritize a list of tasks.

**Request Body:**
```json
{
  "tasks": [
    {
      "id": "task-1",
      "title": "Fix login bug",
      "due_date": "2025-11-30",
      "estimated_hours": 3,
      "importance": 8,
      "dependencies": []
    }
  ],
  "strategy": "smart_balance"
}
```

**Response:**
```json
{
  "tasks": [...],
  "summary": "Analyzed 1 task(s) • 1 high priority",
  "warnings": [],
  "strategy": "smart_balance",
  "eisenhower_matrix": {
    "do_first": [...],
    "schedule": [...],
    "delegate": [...],
    "eliminate": [...]
  },
  "dependency_graph": {
    "nodes": [...],
    "edges": [...],
    "has_circular": false,
    "circular_dependencies": []
  }
}
```

### POST /api/tasks/suggest/

Get top N task suggestions with recommendations.

**Query Parameters:**
- `count`: Number of suggestions (default: 3)
- `strategy`: Scoring strategy (default: smart_balance)

### GET /api/tasks/strategies/

Get available sorting strategies with descriptions.

### POST /api/tasks/feedback/

Record user feedback for the learning system.

**Request Body:**
```json
{
  "task": { "id": "task-1", "_scores": {...}, "priority_score": 75 },
  "was_helpful": true
}
```

### GET /api/tasks/feedback/

Get learning system statistics.

### DELETE /api/tasks/feedback/

Reset learning system data.

## 🎨 Design Decisions

### Trade-offs Made

1. **Weighted Linear Combination vs. Machine Learning**
   - Chose simple weighted scoring for transparency and explainability
   - Users can understand and trust why tasks are ranked
   - Learning system provides adaptive capability without black-box ML

2. **Exponential Urgency vs. Linear**
   - Exponential curve matches human perception of deadlines
   - "Due tomorrow" feels much more urgent than "due in 3 days"

3. **Working Days vs. Calendar Days**
   - More accurate representation of actual time available
   - Reduces false urgency for weekend deadlines

4. **In-Memory Learning vs. Database Storage**
   - Faster iteration and simpler deployment
   - Learning persists during session, resets on restart
   - Could be extended to persistent storage

### Architecture Decisions

- **Django REST Framework**: Industry-standard, well-documented
- **Vanilla JavaScript**: No framework overhead, simple and fast
- **SQLite**: Zero-config database for development
- **CORS enabled**: Flexible frontend deployment
- **GitHub Pages**: Free, reliable static hosting

## ⏱️ Time Breakdown

| Phase | Estimated | Actual |
|-------|-----------|--------|
| Project Setup | 15 min | 20 min |
| Backend Models & Serializers | 30 min | 25 min |
| Scoring Algorithm | 45 min | 50 min |
| API Views & URLs | 30 min | 25 min |
| Unit Tests (Core) | 30 min | 35 min |
| Frontend HTML/CSS | 45 min | 50 min |
| Frontend JavaScript | 45 min | 40 min |
| Documentation | 20 min | 25 min |
| **Core Total** | **4.5 hours** | **4.5 hours** |
| | | |
| **Bonus: Date Intelligence** | 30 min | 25 min |
| **Bonus: Eisenhower Matrix** | 45 min | 40 min |
| **Bonus: Dependency Graph** | 45 min | 35 min |
| **Bonus: Learning System** | 60 min | 50 min |
| **Bonus: Additional Tests** | 45 min | 40 min |
| **Bonus Total** | **3.75 hours** | **3.25 hours** |
| | | |
| **Grand Total** | **8.25 hours** | **7.75 hours** |

## 📁 Project Structure

```
SmartTaskAnalyzer/
├── backend/                  # Django Project Configuration
│   ├── __init__.py
│   ├── settings.py          # Django settings (CORS, allowed hosts)
│   ├── urls.py              # Root URL configuration
│   ├── wsgi.py              # WSGI entry point
│   └── asgi.py              # ASGI entry point
├── tasks/                    # Tasks Application
│   ├── __init__.py
│   ├── models.py            # Task model definition
│   ├── views.py             # API views (analyze, suggest, feedback)
│   ├── serializers.py       # Request/Response serializers
│   ├── scoring.py           # Priority scoring algorithm ⭐
│   │   ├── LearningSystem   # Adaptive weight adjustment
│   │   ├── is_working_day   # Weekend/holiday detection
│   │   ├── calculate_*      # Score calculation functions
│   │   ├── build_dependency_graph
│   │   └── analyze_tasks    # Main entry point
│   ├── urls.py              # API URL routes
│   ├── tests.py             # 45+ unit tests
│   ├── admin.py             # Django admin config
│   └── apps.py              # App configuration
├── frontend/                 # Frontend Application
│   ├── index.html           # Main HTML (3 view tabs)
│   ├── styles.css           # CSS (dark theme, matrix, graph)
│   └── script.js            # JavaScript (API, views, feedback)
├── docs/                     # GitHub Pages deployment
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── manage.py                # Django management script
├── requirements.txt         # Python dependencies
├── pythonanywhere_wsgi.py   # Production WSGI config
└── README.md               # This file
```

## 🔮 Future Improvements

With more time, I would implement:

1. **Persistent Learning** - Save learning data to database
2. **User Accounts** - Save task lists per user
3. **Batch Operations** - Bulk edit/delete tasks
4. **Export/Import** - Save and load task configurations (JSON, CSV)
5. **Dark/Light Theme Toggle** - User preference for UI theme
6. **Keyboard Shortcuts** - Power user productivity features
7. **Mobile App** - React Native or Flutter implementation
8. **Notifications** - Remind users of upcoming deadlines
9. **Analytics Dashboard** - Track productivity patterns
10. **Team Collaboration** - Share task lists with team members

## 📄 License

MIT License - feel free to use this code for learning and development.

---

## 👨‍💻 Author

Built with ❤️ for intelligent productivity

**GitHub**: [https://github.com/Marlness/smart-task-analyzer](https://github.com/Marlness/smart-task-analyzer)
