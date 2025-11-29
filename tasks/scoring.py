"""
Priority Scoring Algorithm for Smart Task Analyzer.

This module implements the intelligent task prioritization system that considers
multiple factors to determine which tasks should be worked on first.

ALGORITHM OVERVIEW:
-------------------
The scoring system uses a weighted multi-factor approach:

1. URGENCY (Base weight: 35%)
   - Calculated from days until due date
   - Past-due tasks get maximum urgency + overdue penalty
   - Urgency increases exponentially as deadline approaches
   
2. IMPORTANCE (Base weight: 30%)  
   - Direct user rating (1-10 scale)
   - Normalized to 0-100 scale for consistency
   
3. EFFORT/QUICK WINS (Base weight: 20%)
   - Lower effort tasks scored higher (inverse relationship)
   - Encourages completing quick wins to build momentum
   - Capped to prevent tiny tasks from dominating
   
4. DEPENDENCY IMPACT (Base weight: 15%)
   - Tasks that block other tasks get bonus points
   - More blocked tasks = higher priority for blocker
   - Helps prevent bottlenecks in task flow

EDGE CASES HANDLED:
- Past-due tasks: Heavily penalized but still ranked by other factors
- Missing data: Sensible defaults applied
- Circular dependencies: Detected and flagged
- Invalid dates: Treated as high urgency
- Extreme values: Clamped to reasonable ranges

STRATEGIES:
- smart_balance: Uses all factors with balanced weights (default)
- fastest_wins: Prioritizes low-effort tasks
- high_impact: Prioritizes importance over everything
- deadline_driven: Prioritizes urgency/due dates
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import math


# Default weight configuration
DEFAULT_WEIGHTS = {
    'urgency': 0.35,
    'importance': 0.30,
    'effort': 0.20,
    'dependency': 0.15,
}

# Strategy-specific weight configurations
STRATEGY_WEIGHTS = {
    'smart_balance': DEFAULT_WEIGHTS,
    'fastest_wins': {
        'urgency': 0.15,
        'importance': 0.15,
        'effort': 0.55,
        'dependency': 0.15,
    },
    'high_impact': {
        'urgency': 0.20,
        'importance': 0.55,
        'effort': 0.10,
        'dependency': 0.15,
    },
    'deadline_driven': {
        'urgency': 0.55,
        'importance': 0.20,
        'effort': 0.10,
        'dependency': 0.15,
    },
}

# Scoring constants
MAX_SCORE = 100
OVERDUE_PENALTY = 20  # Additional penalty for overdue tasks
DAYS_THRESHOLD_URGENT = 3  # Days until "urgent"
DAYS_THRESHOLD_SOON = 7  # Days until "coming soon"
MAX_EFFORT_HOURS = 40  # Cap for effort calculation


def calculate_urgency_score(due_date: date, today: Optional[date] = None) -> Tuple[float, int, bool]:
    """
    Calculate urgency score based on due date.
    
    Uses an exponential decay function where urgency increases
    rapidly as the deadline approaches.
    
    Args:
        due_date: The task's due date
        today: Current date (defaults to today, injectable for testing)
        
    Returns:
        Tuple of (urgency_score, days_until_due, is_overdue)
        - urgency_score: 0-100 scale (can exceed 100 for overdue)
        - days_until_due: Negative if overdue
        - is_overdue: Boolean flag
    """
    if today is None:
        today = date.today()
    
    days_until_due = (due_date - today).days
    is_overdue = days_until_due < 0
    
    if is_overdue:
        # Overdue tasks get maximum urgency plus penalty based on how late
        days_overdue = abs(days_until_due)
        # Cap the overdue penalty to prevent extreme values
        overdue_bonus = min(days_overdue * 5, 50)
        urgency_score = MAX_SCORE + OVERDUE_PENALTY + overdue_bonus
    elif days_until_due == 0:
        # Due today - maximum urgency
        urgency_score = MAX_SCORE
    elif days_until_due <= DAYS_THRESHOLD_URGENT:
        # Very urgent (1-3 days) - exponential increase
        urgency_score = MAX_SCORE - (days_until_due * 5)
    elif days_until_due <= DAYS_THRESHOLD_SOON:
        # Coming soon (4-7 days) - moderate urgency
        urgency_score = 70 - ((days_until_due - DAYS_THRESHOLD_URGENT) * 5)
    elif days_until_due <= 14:
        # 1-2 weeks away
        urgency_score = 50 - ((days_until_due - DAYS_THRESHOLD_SOON) * 3)
    elif days_until_due <= 30:
        # 2-4 weeks away
        urgency_score = 30 - ((days_until_due - 14) * 1)
    else:
        # More than a month away - low urgency
        # Minimum urgency of 5 to always have some consideration
        urgency_score = max(5, 15 - (days_until_due - 30) * 0.1)
    
    return (urgency_score, days_until_due, is_overdue)


def calculate_importance_score(importance: int) -> float:
    """
    Convert importance rating (1-10) to 0-100 scale.
    
    Uses a slightly curved function to give more weight to higher ratings.
    
    Args:
        importance: User rating from 1-10
        
    Returns:
        Importance score on 0-100 scale
    """
    # Clamp importance to valid range
    importance = max(1, min(10, importance))
    
    # Linear scaling with slight curve for higher values
    # This makes the difference between 9 and 10 more significant
    base_score = (importance / 10) * 100
    
    # Apply slight exponential curve
    curved_score = base_score * (1 + (importance - 5) * 0.02)
    
    return min(MAX_SCORE, max(0, curved_score))


def calculate_effort_score(estimated_hours: int) -> float:
    """
    Calculate effort score (higher score for lower effort = quick wins).
    
    Uses inverse relationship so smaller tasks score higher,
    encouraging completion of quick wins.
    
    Args:
        estimated_hours: Estimated hours to complete task
        
    Returns:
        Effort score on 0-100 scale (higher = easier/quicker)
    """
    # Clamp hours to valid range
    hours = max(1, min(MAX_EFFORT_HOURS, estimated_hours))
    
    # Inverse logarithmic relationship
    # 1 hour = ~100, 8 hours = ~50, 40 hours = ~10
    effort_score = MAX_SCORE * (1 - (math.log(hours + 1) / math.log(MAX_EFFORT_HOURS + 1)))
    
    return max(10, min(MAX_SCORE, effort_score))


def calculate_dependency_score(task_id: str, all_tasks: List[Dict]) -> Tuple[float, int]:
    """
    Calculate dependency score based on how many other tasks this blocks.
    
    Tasks that block many other tasks should be prioritized to prevent
    bottlenecks in the workflow.
    
    Args:
        task_id: The ID of the task to score
        all_tasks: List of all tasks to check dependencies
        
    Returns:
        Tuple of (dependency_score, blocking_count)
    """
    blocking_count = 0
    
    for task in all_tasks:
        dependencies = task.get('dependencies', [])
        if task_id in dependencies:
            blocking_count += 1
    
    # Score calculation: each blocked task adds points
    # Max out at 5 blocked tasks for scoring purposes
    effective_count = min(blocking_count, 5)
    dependency_score = effective_count * 20  # 0, 20, 40, 60, 80, 100
    
    return (dependency_score, blocking_count)


def detect_circular_dependencies(tasks: List[Dict]) -> List[List[str]]:
    """
    Detect circular dependencies in the task list.
    
    Uses depth-first search to find cycles in the dependency graph.
    
    Args:
        tasks: List of tasks with dependencies
        
    Returns:
        List of cycles found (each cycle is a list of task IDs)
    """
    # Build adjacency list
    task_ids = {task.get('id', str(i)): task for i, task in enumerate(tasks)}
    graph = {}
    
    for task in tasks:
        task_id = task.get('id', '')
        dependencies = task.get('dependencies', [])
        graph[task_id] = [dep for dep in dependencies if dep in task_ids]
    
    cycles = []
    visited = set()
    rec_stack = set()
    
    def dfs(node: str, path: List[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                if cycle not in cycles:
                    cycles.append(cycle)
        
        path.pop()
        rec_stack.remove(node)
    
    for node in graph:
        if node not in visited:
            dfs(node, [])
    
    return cycles


def calculate_priority_score(
    task: Dict,
    all_tasks: List[Dict],
    strategy: str = 'smart_balance',
    custom_weights: Optional[Dict[str, float]] = None,
    today: Optional[date] = None
) -> Dict[str, Any]:
    """
    Calculate the overall priority score for a task.
    
    This is the main scoring function that combines all factors
    using configurable weights based on the selected strategy.
    
    Args:
        task: The task to score
        all_tasks: All tasks (needed for dependency calculation)
        strategy: Scoring strategy to use
        custom_weights: Optional custom weight configuration
        today: Current date (injectable for testing)
        
    Returns:
        Dictionary containing:
        - priority_score: The calculated score
        - priority_level: High/Medium/Low classification
        - explanation: Human-readable explanation
        - Component scores and other metadata
    """
    # Get weights based on strategy
    if custom_weights:
        weights = {**DEFAULT_WEIGHTS, **custom_weights}
    else:
        weights = STRATEGY_WEIGHTS.get(strategy, DEFAULT_WEIGHTS)
    
    # Normalize weights to sum to 1
    total_weight = sum(weights.values())
    weights = {k: v / total_weight for k, v in weights.items()}
    
    # Parse due date
    due_date = task.get('due_date')
    if isinstance(due_date, str):
        try:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        except ValueError:
            due_date = date.today()  # Default to today if invalid
    elif not isinstance(due_date, date):
        due_date = date.today()
    
    # Get other task properties with defaults
    importance = task.get('importance', 5)
    estimated_hours = task.get('estimated_hours', 4)
    task_id = task.get('id', '')
    
    # Calculate individual scores
    urgency_score, days_until_due, is_overdue = calculate_urgency_score(due_date, today)
    importance_score = calculate_importance_score(importance)
    effort_score = calculate_effort_score(estimated_hours)
    dependency_score, blocking_count = calculate_dependency_score(task_id, all_tasks)
    
    # Calculate weighted score
    weighted_score = (
        urgency_score * weights['urgency'] +
        importance_score * weights['importance'] +
        effort_score * weights['effort'] +
        dependency_score * weights['dependency']
    )
    
    # Determine priority level
    if weighted_score >= 70 or is_overdue:
        priority_level = 'High'
    elif weighted_score >= 40:
        priority_level = 'Medium'
    else:
        priority_level = 'Low'
    
    # Generate explanation
    explanation = generate_explanation(
        task=task,
        urgency_score=urgency_score,
        importance_score=importance_score,
        effort_score=effort_score,
        dependency_score=dependency_score,
        days_until_due=days_until_due,
        is_overdue=is_overdue,
        blocking_count=blocking_count,
        strategy=strategy,
        weights=weights
    )
    
    return {
        'id': task_id,
        'title': task.get('title', 'Untitled'),
        'due_date': due_date.isoformat() if isinstance(due_date, date) else str(due_date),
        'estimated_hours': estimated_hours,
        'importance': importance,
        'dependencies': task.get('dependencies', []),
        'priority_score': round(weighted_score, 2),
        'priority_level': priority_level,
        'explanation': explanation,
        'is_overdue': is_overdue,
        'days_until_due': days_until_due,
        'blocking_count': blocking_count,
        '_scores': {
            'urgency': round(urgency_score, 2),
            'importance': round(importance_score, 2),
            'effort': round(effort_score, 2),
            'dependency': round(dependency_score, 2),
        }
    }


def generate_explanation(
    task: Dict,
    urgency_score: float,
    importance_score: float,
    effort_score: float,
    dependency_score: float,
    days_until_due: int,
    is_overdue: bool,
    blocking_count: int,
    strategy: str,
    weights: Dict[str, float]
) -> str:
    """
    Generate a human-readable explanation for the task's priority score.
    
    Args:
        Various score components and task data
        
    Returns:
        A string explaining why this task received its score
    """
    factors = []
    
    # Urgency factor
    if is_overdue:
        factors.append(f"⚠️ OVERDUE by {abs(days_until_due)} day(s)")
    elif days_until_due == 0:
        factors.append("📅 Due TODAY")
    elif days_until_due <= 3:
        factors.append(f"⏰ Due in {days_until_due} day(s) - URGENT")
    elif days_until_due <= 7:
        factors.append(f"📆 Due in {days_until_due} days")
    
    # Importance factor
    importance = task.get('importance', 5)
    if importance >= 8:
        factors.append(f"⭐ High importance ({importance}/10)")
    elif importance >= 6:
        factors.append(f"📌 Medium-high importance ({importance}/10)")
    
    # Effort factor (quick wins)
    hours = task.get('estimated_hours', 4)
    if hours <= 2:
        factors.append(f"⚡ Quick win (~{hours}h)")
    elif hours >= 16:
        factors.append(f"📊 Major effort ({hours}h)")
    
    # Dependency factor
    if blocking_count > 0:
        factors.append(f"🔗 Blocks {blocking_count} other task(s)")
    
    # Strategy note
    strategy_names = {
        'smart_balance': 'Balanced',
        'fastest_wins': 'Quick Wins',
        'high_impact': 'High Impact',
        'deadline_driven': 'Deadline Focus'
    }
    
    if not factors:
        factors.append("Standard priority task")
    
    return " • ".join(factors)


def analyze_tasks(
    tasks: List[Dict],
    strategy: str = 'smart_balance',
    custom_weights: Optional[Dict[str, float]] = None,
    today: Optional[date] = None
) -> Dict[str, Any]:
    """
    Analyze a list of tasks and return them sorted by priority.
    
    This is the main entry point for task analysis.
    
    Args:
        tasks: List of task dictionaries
        strategy: Scoring strategy to use
        custom_weights: Optional custom weights
        today: Current date (for testing)
        
    Returns:
        Dictionary containing:
        - tasks: Sorted list of tasks with scores
        - warnings: Any warnings (circular dependencies, etc.)
        - summary: Brief summary of the analysis
    """
    warnings = []
    
    # Detect circular dependencies
    cycles = detect_circular_dependencies(tasks)
    if cycles:
        for cycle in cycles:
            warnings.append(f"Circular dependency detected: {' → '.join(cycle)}")
    
    # Score all tasks
    scored_tasks = []
    for task in tasks:
        scored = calculate_priority_score(
            task=task,
            all_tasks=tasks,
            strategy=strategy,
            custom_weights=custom_weights,
            today=today
        )
        scored_tasks.append(scored)
    
    # Sort by priority score (descending)
    scored_tasks.sort(key=lambda x: x['priority_score'], reverse=True)
    
    # Generate summary
    overdue_count = sum(1 for t in scored_tasks if t['is_overdue'])
    high_priority_count = sum(1 for t in scored_tasks if t['priority_level'] == 'High')
    
    summary_parts = [f"Analyzed {len(tasks)} task(s)"]
    if overdue_count:
        summary_parts.append(f"{overdue_count} overdue")
    if high_priority_count:
        summary_parts.append(f"{high_priority_count} high priority")
    
    summary = " • ".join(summary_parts)
    
    return {
        'tasks': scored_tasks,
        'warnings': warnings,
        'summary': summary,
        'strategy': strategy
    }


def get_suggestions(
    tasks: List[Dict],
    count: int = 3,
    strategy: str = 'smart_balance',
    today: Optional[date] = None
) -> Dict[str, Any]:
    """
    Get the top N task suggestions for today.
    
    Args:
        tasks: List of task dictionaries
        count: Number of suggestions to return
        strategy: Scoring strategy to use
        today: Current date (for testing)
        
    Returns:
        Dictionary containing top tasks with detailed explanations
    """
    analysis = analyze_tasks(tasks, strategy=strategy, today=today)
    
    top_tasks = analysis['tasks'][:count]
    
    # Add more detailed suggestions
    for i, task in enumerate(top_tasks, 1):
        if i == 1:
            task['suggestion'] = "🎯 Start with this one - highest priority"
        elif i == 2:
            task['suggestion'] = "📋 Next up after completing the first task"
        else:
            task['suggestion'] = "📝 Consider tackling this today if time permits"
    
    # Generate summary advice
    if top_tasks:
        first_task = top_tasks[0]
        if first_task['is_overdue']:
            advice = f"⚠️ Focus on '{first_task['title']}' first - it's overdue!"
        elif first_task['days_until_due'] == 0:
            advice = f"📅 '{first_task['title']}' is due today - make it your priority!"
        elif first_task['blocking_count'] > 0:
            advice = f"🔗 Complete '{first_task['title']}' to unblock {first_task['blocking_count']} other task(s)."
        else:
            advice = f"✅ Start with '{first_task['title']}' based on the {strategy.replace('_', ' ')} strategy."
    else:
        advice = "No tasks to analyze. Add some tasks to get started!"
    
    return {
        'tasks': top_tasks,
        'summary': advice,
        'warnings': analysis['warnings'],
        'total_tasks': len(tasks)
    }

