# Smart Task Analyzer

An intelligent task prioritization system that helps you decide what to work on first by analyzing multiple factors including urgency, importance, effort, and task dependencies.

![Smart Task Analyzer](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Table of Contents

- [Overview](#overview)
- [Setup Instructions](#setup-instructions)
- [Algorithm Explanation](#algorithm-explanation)
- [Design Decisions](#design-decisions)
- [API Documentation](#api-documentation)
- [Time Breakdown](#time-breakdown)
- [Future Improvements](#future-improvements)

## Overview

Smart Task Analyzer is a full-stack application that:
- Accepts a list of tasks with properties (due date, importance, effort, dependencies)
- Calculates intelligent priority scores using a configurable algorithm
- Returns tasks sorted by priority with explanations
- Provides multiple sorting strategies for different work styles

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SmartTaskAnalyzer
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
python manage.py test tasks
```

## Algorithm Explanation

### Core Scoring System (300-500 words)

The Smart Task Analyzer uses a **weighted multi-factor scoring algorithm** that considers four key dimensions to calculate task priority:

#### 1. Urgency Score (Default Weight: 35%)

Urgency is calculated based on the number of days until the task's due date. The algorithm uses an **exponential decay function** where urgency increases rapidly as deadlines approach:

- **Overdue tasks**: Receive maximum urgency (100) plus a penalty proportional to days overdue. This ensures overdue items float to the top while still being ranked among themselves.
- **Due today**: Maximum urgency score of 100
- **1-3 days**: High urgency (85-95), exponential increase
- **4-7 days**: Moderate urgency (50-70)
- **1-2 weeks**: Lower urgency (30-50)
- **30+ days**: Minimal urgency (5-15)

The exponential curve ensures that the urgency difference between "due tomorrow" and "due in 3 days" is more significant than between "due in 30 days" and "due in 33 days" - matching human intuition about deadlines.

#### 2. Importance Score (Default Weight: 30%)

The user-provided importance rating (1-10) is normalized to a 0-100 scale with a slight curve applied to higher values. This makes the difference between 9 and 10 more meaningful than between 4 and 5, reflecting that "critical" tasks deserve extra weight.

#### 3. Effort/Quick Wins Score (Default Weight: 20%)

Uses an **inverse logarithmic relationship** where lower-effort tasks score higher. This encourages completing "quick wins" to build momentum:
- 1-hour tasks: ~90+ score
- 4-hour tasks: ~60 score
- 8-hour tasks: ~45 score
- 40-hour tasks: ~10 score

The logarithmic curve prevents tiny tasks from completely dominating while still giving meaningful advantage to quick tasks.

#### 4. Dependency Impact Score (Default Weight: 15%)

Tasks that block other tasks receive bonus points. Each blocked task adds 20 points (capped at 100). This prevents workflow bottlenecks by prioritizing blockers.

### Strategy Presets

Users can choose different weighting strategies:

| Strategy | Urgency | Importance | Effort | Dependency |
|----------|---------|------------|--------|------------|
| Smart Balance | 35% | 30% | 20% | 15% |
| Fastest Wins | 15% | 15% | 55% | 15% |
| High Impact | 20% | 55% | 10% | 15% |
| Deadline Driven | 55% | 20% | 10% | 15% |

### Edge Cases Handled

1. **Overdue tasks**: Heavily weighted but still ranked by other factors
2. **Missing data**: Sensible defaults applied (importance=5, hours=4)
3. **Invalid dates**: Treated as due today (high urgency)
4. **Circular dependencies**: Detected and flagged as warnings
5. **Extreme values**: Clamped to reasonable ranges

## Design Decisions

### Trade-offs Made

1. **Weighted Linear Combination vs. Machine Learning**
   - Chose simple weighted scoring for transparency and explainability
   - Users can understand and trust why tasks are ranked as they are
   - ML would require training data and be a "black box"

2. **Exponential Urgency vs. Linear**
   - Exponential curve matches human perception of deadlines
   - "Due tomorrow" feels much more urgent than "due in 3 days"
   - Linear scaling wouldn't capture this psychological reality

3. **Quick Wins as Positive vs. Large Tasks as Negative**
   - Framed as rewarding quick tasks rather than punishing large ones
   - Prevents demotivation for necessary large projects
   - Minimum score ensures large tasks aren't completely buried

4. **In-Memory vs. Database Storage**
   - API is stateless - receives tasks and returns scored results
   - Simplifies deployment and avoids data persistence complexity
   - Task model exists for future enhancement (saved task lists)

5. **Strategy Presets vs. Full Customization**
   - Presets cover common use cases (80/20 rule)
   - Custom weights available for power users
   - Balances simplicity with flexibility

### Architecture Decisions

- **Django REST Framework**: Industry-standard, well-documented, great for rapid development
- **Vanilla JavaScript**: No framework overhead for a simple UI
- **SQLite**: Sufficient for local development, no setup required
- **CORS enabled**: Allows frontend to run separately from backend

## API Documentation

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
  "tasks": [
    {
      "id": "task-1",
      "title": "Fix login bug",
      "due_date": "2025-11-30",
      "estimated_hours": 3,
      "importance": 8,
      "dependencies": [],
      "priority_score": 78.5,
      "priority_level": "High",
      "explanation": "📅 Due in 2 days • ⭐ High importance (8/10)",
      "is_overdue": false,
      "days_until_due": 2,
      "blocking_count": 0
    }
  ],
  "summary": "Analyzed 1 task(s) • 1 high priority",
  "warnings": [],
  "strategy": "smart_balance"
}
```

### POST /api/tasks/suggest/

Get top 3 task suggestions with recommendations.

**Query Parameters:**
- `count`: Number of suggestions (default: 3)
- `strategy`: Scoring strategy (default: smart_balance)

### GET /api/tasks/strategies/

Get available sorting strategies with descriptions.

## Time Breakdown

| Phase | Estimated | Actual |
|-------|-----------|--------|
| Project Setup | 15 min | 20 min |
| Backend Models & Serializers | 30 min | 25 min |
| Scoring Algorithm | 45 min | 50 min |
| API Views & URLs | 30 min | 25 min |
| Unit Tests | 30 min | 35 min |
| Frontend HTML/CSS | 45 min | 50 min |
| Frontend JavaScript | 45 min | 40 min |
| Documentation | 20 min | 25 min |
| **Total** | **4.5 hours** | **4.5 hours** |

## Bonus Challenges Attempted

- ✅ **Circular Dependency Detection**: Algorithm detects and warns about circular dependencies using depth-first search
- ✅ **Configurable Weights**: Users can customize algorithm weights via API
- ✅ **Comprehensive Unit Tests**: 20+ test cases covering edge cases

## Future Improvements

With more time, I would implement:

1. **Eisenhower Matrix View**: Visual 2x2 grid showing Urgent vs Important
2. **Date Intelligence**: Consider weekends/holidays in urgency calculation
3. **Learning System**: Track which suggestions users follow and adjust weights
4. **Task Persistence**: Save task lists to database for returning users
5. **Dependency Visualization**: Interactive graph showing task relationships
6. **Batch Operations**: Bulk edit/delete tasks
7. **Export/Import**: Save and load task configurations
8. **Dark/Light Theme Toggle**: User preference for UI theme
9. **Keyboard Shortcuts**: Power user productivity features
10. **Mobile App**: React Native or Flutter implementation

## Project Structure

```
SmartTaskAnalyzer/
├── backend/                  # Django Project Configuration
│   ├── __init__.py
│   ├── settings.py          # Django settings
│   ├── urls.py              # Root URL configuration
│   ├── wsgi.py              # WSGI entry point
│   └── asgi.py              # ASGI entry point
├── tasks/                    # Tasks Application
│   ├── __init__.py
│   ├── models.py            # Task model definition
│   ├── views.py             # API view handlers
│   ├── serializers.py       # Request/Response serializers
│   ├── scoring.py           # Priority scoring algorithm ⭐
│   ├── urls.py              # API URL routes
│   ├── tests.py             # Unit tests
│   ├── admin.py             # Django admin config
│   └── apps.py              # App configuration
├── frontend/                 # Frontend Application
│   ├── index.html           # Main HTML structure
│   ├── styles.css           # CSS styling
│   └── script.js            # JavaScript logic
├── manage.py                # Django management script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## License

MIT License - feel free to use this code for learning and development.

---

Built with ❤️ for intelligent productivity

