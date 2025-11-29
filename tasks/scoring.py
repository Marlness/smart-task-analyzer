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
from typing import Dict, List, Tuple, Optional, Any, Set
import math


# Common US holidays (month, day) - extensible
HOLIDAYS = {
    (1, 1),    # New Year's Day
    (7, 4),    # Independence Day
    (12, 25),  # Christmas
    (12, 31),  # New Year's Eve
    (11, 28),  # Thanksgiving (approximate)
    (11, 29),  # Day after Thanksgiving
}


# ============================================
# LEARNING SYSTEM
# ============================================
# Stores user feedback to adjust algorithm weights over time

class LearningSystem:
    """
    Learning System that adjusts algorithm weights based on user feedback.
    
    When users mark suggestions as helpful or not helpful, the system
    learns and adjusts the weights for future recommendations.
    
    The learning uses a simple exponential moving average approach
    to gradually shift weights based on feedback patterns.
    """
    
    def __init__(self):
        # Feedback history: list of (task_features, was_helpful)
        self.feedback_history: List[Dict] = []
        # Learned weight adjustments (starts at 0 = no adjustment)
        self.weight_adjustments = {
            'urgency': 0.0,
            'importance': 0.0,
            'effort': 0.0,
            'dependency': 0.0,
        }
        # Learning rate (how quickly to adjust)
        self.learning_rate = 0.05
        # Feedback count for statistics
        self.helpful_count = 0
        self.not_helpful_count = 0
    
    def record_feedback(self, task_data: Dict, was_helpful: bool) -> Dict:
        """
        Record user feedback for a task suggestion.
        
        Args:
            task_data: The task that was suggested (with scores)
            was_helpful: True if user found suggestion helpful
            
        Returns:
            Updated statistics
        """
        # Extract relevant features
        feedback = {
            'was_helpful': was_helpful,
            'urgency_score': task_data.get('_scores', {}).get('urgency', 50),
            'importance_score': task_data.get('_scores', {}).get('importance', 50),
            'effort_score': task_data.get('_scores', {}).get('effort', 50),
            'dependency_score': task_data.get('_scores', {}).get('dependency', 0),
            'priority_score': task_data.get('priority_score', 50),
            'is_overdue': task_data.get('is_overdue', False),
        }
        
        self.feedback_history.append(feedback)
        
        if was_helpful:
            self.helpful_count += 1
        else:
            self.not_helpful_count += 1
        
        # Update weight adjustments based on feedback
        self._update_weights(feedback)
        
        return self.get_statistics()
    
    def _update_weights(self, feedback: Dict) -> None:
        """Update weight adjustments based on feedback."""
        was_helpful = feedback['was_helpful']
        
        # If helpful, slightly increase weights for high-scoring factors
        # If not helpful, slightly decrease them
        adjustment = self.learning_rate if was_helpful else -self.learning_rate
        
        # Normalize scores to -1 to 1 range for adjustment
        urgency_factor = (feedback['urgency_score'] - 50) / 50
        importance_factor = (feedback['importance_score'] - 50) / 50
        effort_factor = (feedback['effort_score'] - 50) / 50
        dependency_factor = (feedback['dependency_score'] - 50) / 50
        
        # Apply adjustments (capped at ±0.15 to prevent wild swings)
        self.weight_adjustments['urgency'] = max(-0.15, min(0.15,
            self.weight_adjustments['urgency'] + adjustment * urgency_factor))
        self.weight_adjustments['importance'] = max(-0.15, min(0.15,
            self.weight_adjustments['importance'] + adjustment * importance_factor))
        self.weight_adjustments['effort'] = max(-0.15, min(0.15,
            self.weight_adjustments['effort'] + adjustment * effort_factor))
        self.weight_adjustments['dependency'] = max(-0.15, min(0.15,
            self.weight_adjustments['dependency'] + adjustment * dependency_factor))
    
    def get_adjusted_weights(self, base_weights: Dict[str, float]) -> Dict[str, float]:
        """
        Get weights adjusted by learned preferences.
        
        Args:
            base_weights: The base strategy weights
            
        Returns:
            Adjusted weights incorporating learned preferences
        """
        adjusted = {}
        for key, value in base_weights.items():
            adjustment = self.weight_adjustments.get(key, 0)
            adjusted[key] = max(0.05, value + adjustment)  # Minimum 5% weight
        
        # Normalize to sum to 1
        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}
    
    def get_statistics(self) -> Dict:
        """Get learning system statistics."""
        total = self.helpful_count + self.not_helpful_count
        return {
            'total_feedback': total,
            'helpful_count': self.helpful_count,
            'not_helpful_count': self.not_helpful_count,
            'helpful_rate': self.helpful_count / total if total > 0 else 0,
            'weight_adjustments': self.weight_adjustments.copy(),
            'is_learning': total >= 3,  # Start applying after 3 feedbacks
        }
    
    def reset(self) -> Dict:
        """Reset learning data."""
        self.feedback_history = []
        self.weight_adjustments = {k: 0.0 for k in self.weight_adjustments}
        self.helpful_count = 0
        self.not_helpful_count = 0
        return self.get_statistics()


# Global learning system instance
learning_system = LearningSystem()


def is_working_day(d: date) -> bool:
    """Check if a date is a working day (not weekend or holiday)."""
    # Weekend check (Saturday = 5, Sunday = 6)
    if d.weekday() >= 5:
        return False
    # Holiday check
    if (d.month, d.day) in HOLIDAYS:
        return False
    return True


def count_working_days(start_date: date, end_date: date) -> int:
    """
    Count working days between two dates (excluding weekends and holidays).
    Used for more accurate urgency calculation.
    """
    if end_date < start_date:
        return -count_working_days(end_date, start_date)
    
    working_days = 0
    current = start_date
    while current <= end_date:
        if is_working_day(current):
            working_days += 1
        current += timedelta(days=1)
    return working_days


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


def calculate_urgency_score(due_date: date, today: Optional[date] = None, use_working_days: bool = True) -> Tuple[float, int, bool, int]:
    """
    Calculate urgency score based on due date.
    
    Uses an exponential decay function where urgency increases
    rapidly as the deadline approaches.
    
    DATE INTELLIGENCE: When use_working_days=True, the algorithm considers
    only working days (excludes weekends and holidays) for more accurate
    urgency calculation. A task due Monday when it's Friday has only 1 
    working day, not 3 calendar days.
    
    Args:
        due_date: The task's due date
        today: Current date (defaults to today, injectable for testing)
        use_working_days: If True, exclude weekends/holidays from calculation
        
    Returns:
        Tuple of (urgency_score, days_until_due, is_overdue, working_days_until_due)
        - urgency_score: 0-100 scale (can exceed 100 for overdue)
        - days_until_due: Calendar days (negative if overdue)
        - is_overdue: Boolean flag
        - working_days_until_due: Working days only
    """
    if today is None:
        today = date.today()
    
    days_until_due = (due_date - today).days
    is_overdue = days_until_due < 0
    
    # Calculate working days for date intelligence
    if use_working_days and not is_overdue:
        working_days = count_working_days(today, due_date) - 1  # Exclude today
        effective_days = max(0, working_days)
    else:
        effective_days = days_until_due
        working_days = days_until_due
    
    if is_overdue:
        # Overdue tasks get maximum urgency plus penalty based on how late
        days_overdue = abs(days_until_due)
        # Cap the overdue penalty to prevent extreme values
        overdue_bonus = min(days_overdue * 5, 50)
        urgency_score = MAX_SCORE + OVERDUE_PENALTY + overdue_bonus
    elif effective_days == 0:
        # Due today - maximum urgency
        urgency_score = MAX_SCORE
    elif effective_days <= DAYS_THRESHOLD_URGENT:
        # Very urgent (1-3 working days) - exponential increase
        urgency_score = MAX_SCORE - (effective_days * 5)
    elif effective_days <= DAYS_THRESHOLD_SOON:
        # Coming soon (4-7 working days) - moderate urgency
        urgency_score = 70 - ((effective_days - DAYS_THRESHOLD_URGENT) * 5)
    elif effective_days <= 14:
        # 1-2 weeks away
        urgency_score = 50 - ((effective_days - DAYS_THRESHOLD_SOON) * 3)
    elif effective_days <= 30:
        # 2-4 weeks away
        urgency_score = 30 - ((effective_days - 14) * 1)
    else:
        # More than a month away - low urgency
        # Minimum urgency of 5 to always have some consideration
        urgency_score = max(5, 15 - (effective_days - 30) * 0.1)
    
    return (urgency_score, days_until_due, is_overdue, working_days)


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


def build_dependency_graph(tasks: List[Dict]) -> Dict[str, Any]:
    """
    Build a dependency graph structure for visualization.
    
    Returns data suitable for rendering a visual dependency graph,
    including nodes, edges, and circular dependency warnings.
    
    Args:
        tasks: List of tasks with dependencies
        
    Returns:
        Dictionary containing:
        - nodes: List of node objects with id, title, and metadata
        - edges: List of edge objects showing dependencies
        - circular_dependencies: List of detected cycles
        - has_circular: Boolean flag
    """
    nodes = []
    edges = []
    
    # Build task lookup
    task_map = {task.get('id', str(i)): task for i, task in enumerate(tasks)}
    
    # Create nodes
    for task in tasks:
        task_id = task.get('id', '')
        nodes.append({
            'id': task_id,
            'title': task.get('title', 'Untitled'),
            'importance': task.get('importance', 5),
            'dependencies_count': len(task.get('dependencies', [])),
        })
    
    # Create edges (from dependency to task that depends on it)
    for task in tasks:
        task_id = task.get('id', '')
        dependencies = task.get('dependencies', [])
        for dep_id in dependencies:
            if dep_id in task_map:
                edges.append({
                    'from': dep_id,
                    'to': task_id,
                    'label': 'blocks'
                })
    
    # Detect circular dependencies
    cycles = detect_circular_dependencies(tasks)
    
    # Mark nodes involved in cycles
    circular_node_ids = set()
    for cycle in cycles:
        for node_id in cycle:
            circular_node_ids.add(node_id)
    
    for node in nodes:
        node['in_cycle'] = node['id'] in circular_node_ids
    
    return {
        'nodes': nodes,
        'edges': edges,
        'circular_dependencies': cycles,
        'has_circular': len(cycles) > 0,
        'total_nodes': len(nodes),
        'total_edges': len(edges)
    }


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
    urgency_score, days_until_due, is_overdue, working_days = calculate_urgency_score(due_date, today)
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
    
    # Eisenhower Matrix quadrant calculation
    # Urgent: urgency_score >= 60, Important: importance >= 7
    is_urgent = urgency_score >= 60 or is_overdue
    is_important = importance >= 7
    
    if is_urgent and is_important:
        eisenhower_quadrant = 'do_first'  # Quadrant 1: Do First
    elif is_important and not is_urgent:
        eisenhower_quadrant = 'schedule'   # Quadrant 2: Schedule
    elif is_urgent and not is_important:
        eisenhower_quadrant = 'delegate'   # Quadrant 3: Delegate
    else:
        eisenhower_quadrant = 'eliminate'  # Quadrant 4: Eliminate/Low Priority
    
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
        'working_days_until_due': working_days,
        'blocking_count': blocking_count,
        'eisenhower_quadrant': eisenhower_quadrant,
        'is_urgent': is_urgent,
        'is_important': is_important,
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
    
    # Build dependency graph for visualization
    dependency_graph = build_dependency_graph(tasks)
    
    # Build Eisenhower Matrix data
    eisenhower_matrix = {
        'do_first': [],      # Urgent + Important (Quadrant 1)
        'schedule': [],      # Not Urgent + Important (Quadrant 2)
        'delegate': [],      # Urgent + Not Important (Quadrant 3)
        'eliminate': [],     # Not Urgent + Not Important (Quadrant 4)
    }
    
    for task in scored_tasks:
        quadrant = task.get('eisenhower_quadrant', 'eliminate')
        eisenhower_matrix[quadrant].append({
            'id': task['id'],
            'title': task['title'],
            'priority_score': task['priority_score'],
            'is_urgent': task.get('is_urgent', False),
            'is_important': task.get('is_important', False),
        })
    
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
        'strategy': strategy,
        'dependency_graph': dependency_graph,
        'eisenhower_matrix': eisenhower_matrix,
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

