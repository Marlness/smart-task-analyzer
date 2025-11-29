"""
Unit Tests for Smart Task Analyzer Scoring Algorithm.

These tests verify the core scoring logic handles various scenarios
correctly including edge cases.
"""

import unittest
from datetime import date, timedelta
from .scoring import (
    calculate_urgency_score,
    calculate_importance_score,
    calculate_effort_score,
    calculate_dependency_score,
    calculate_priority_score,
    detect_circular_dependencies,
    analyze_tasks,
    get_suggestions,
)


class TestUrgencyScore(unittest.TestCase):
    """Tests for urgency score calculation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.today = date(2025, 11, 29)  # Fixed date for testing
    
    def test_overdue_task_gets_high_urgency(self):
        """Overdue tasks should have urgency > 100."""
        past_due = date(2025, 11, 25)  # 4 days overdue
        score, days, is_overdue = calculate_urgency_score(past_due, self.today)
        
        self.assertTrue(is_overdue)
        self.assertEqual(days, -4)
        self.assertGreater(score, 100)
    
    def test_due_today_gets_maximum_urgency(self):
        """Tasks due today should have maximum urgency (100)."""
        score, days, is_overdue = calculate_urgency_score(self.today, self.today)
        
        self.assertFalse(is_overdue)
        self.assertEqual(days, 0)
        self.assertEqual(score, 100)
    
    def test_urgent_task_high_score(self):
        """Tasks due in 1-3 days should have high urgency (85-95)."""
        tomorrow = self.today + timedelta(days=1)
        score, days, _ = calculate_urgency_score(tomorrow, self.today)
        
        self.assertEqual(days, 1)
        self.assertGreaterEqual(score, 85)
        self.assertLess(score, 100)
    
    def test_week_away_moderate_urgency(self):
        """Tasks due in a week should have moderate urgency (50-70)."""
        next_week = self.today + timedelta(days=7)
        score, days, _ = calculate_urgency_score(next_week, self.today)
        
        self.assertEqual(days, 7)
        self.assertGreaterEqual(score, 50)
        self.assertLessEqual(score, 70)
    
    def test_month_away_low_urgency(self):
        """Tasks due in a month should have low urgency (<30)."""
        next_month = self.today + timedelta(days=30)
        score, days, _ = calculate_urgency_score(next_month, self.today)
        
        self.assertEqual(days, 30)
        self.assertLess(score, 30)
    
    def test_far_future_minimum_urgency(self):
        """Tasks due far in future should have minimum urgency (>0)."""
        far_future = self.today + timedelta(days=365)
        score, days, _ = calculate_urgency_score(far_future, self.today)
        
        self.assertGreater(score, 0)
        self.assertLess(score, 20)


class TestImportanceScore(unittest.TestCase):
    """Tests for importance score calculation."""
    
    def test_maximum_importance(self):
        """Importance 10 should give near-maximum score."""
        score = calculate_importance_score(10)
        self.assertGreaterEqual(score, 95)
        self.assertLessEqual(score, 100)
    
    def test_minimum_importance(self):
        """Importance 1 should give low score."""
        score = calculate_importance_score(1)
        self.assertLess(score, 15)
        self.assertGreater(score, 0)
    
    def test_medium_importance(self):
        """Importance 5 should give medium score (~50)."""
        score = calculate_importance_score(5)
        self.assertGreaterEqual(score, 45)
        self.assertLessEqual(score, 55)
    
    def test_clamps_out_of_range_values(self):
        """Values outside 1-10 should be clamped."""
        score_low = calculate_importance_score(-5)
        score_high = calculate_importance_score(100)
        
        # Should clamp to 1 and 10 respectively
        self.assertEqual(score_low, calculate_importance_score(1))
        self.assertEqual(score_high, calculate_importance_score(10))


class TestEffortScore(unittest.TestCase):
    """Tests for effort/quick wins score calculation."""
    
    def test_quick_task_high_score(self):
        """1-hour tasks should get high effort score."""
        score = calculate_effort_score(1)
        self.assertGreaterEqual(score, 80)
    
    def test_long_task_low_score(self):
        """Long tasks (40h) should get low effort score."""
        score = calculate_effort_score(40)
        self.assertLessEqual(score, 20)
    
    def test_medium_task_medium_score(self):
        """8-hour tasks should get medium score."""
        score = calculate_effort_score(8)
        self.assertGreaterEqual(score, 40)
        self.assertLessEqual(score, 60)
    
    def test_inverse_relationship(self):
        """Lower effort should always score higher."""
        score_1h = calculate_effort_score(1)
        score_4h = calculate_effort_score(4)
        score_8h = calculate_effort_score(8)
        score_16h = calculate_effort_score(16)
        
        self.assertGreater(score_1h, score_4h)
        self.assertGreater(score_4h, score_8h)
        self.assertGreater(score_8h, score_16h)


class TestDependencyScore(unittest.TestCase):
    """Tests for dependency/blocking score calculation."""
    
    def test_no_blockers_zero_score(self):
        """Tasks that don't block others should have zero dependency score."""
        tasks = [
            {'id': 'A', 'dependencies': []},
            {'id': 'B', 'dependencies': []},
        ]
        score, count = calculate_dependency_score('A', tasks)
        
        self.assertEqual(score, 0)
        self.assertEqual(count, 0)
    
    def test_blocking_one_task(self):
        """Blocking one task should add 20 points."""
        tasks = [
            {'id': 'A', 'dependencies': []},
            {'id': 'B', 'dependencies': ['A']},  # B depends on A
        ]
        score, count = calculate_dependency_score('A', tasks)
        
        self.assertEqual(score, 20)
        self.assertEqual(count, 1)
    
    def test_blocking_multiple_tasks(self):
        """Blocking multiple tasks should add more points."""
        tasks = [
            {'id': 'A', 'dependencies': []},
            {'id': 'B', 'dependencies': ['A']},
            {'id': 'C', 'dependencies': ['A']},
            {'id': 'D', 'dependencies': ['A']},
        ]
        score, count = calculate_dependency_score('A', tasks)
        
        self.assertEqual(count, 3)
        self.assertEqual(score, 60)  # 3 * 20


class TestCircularDependencyDetection(unittest.TestCase):
    """Tests for circular dependency detection."""
    
    def test_no_circular_dependencies(self):
        """Linear dependency chain should have no cycles."""
        tasks = [
            {'id': 'A', 'dependencies': []},
            {'id': 'B', 'dependencies': ['A']},
            {'id': 'C', 'dependencies': ['B']},
        ]
        cycles = detect_circular_dependencies(tasks)
        self.assertEqual(len(cycles), 0)
    
    def test_simple_circular_dependency(self):
        """A -> B -> A should be detected."""
        tasks = [
            {'id': 'A', 'dependencies': ['B']},
            {'id': 'B', 'dependencies': ['A']},
        ]
        cycles = detect_circular_dependencies(tasks)
        self.assertGreater(len(cycles), 0)
    
    def test_three_way_circular(self):
        """A -> B -> C -> A should be detected."""
        tasks = [
            {'id': 'A', 'dependencies': ['C']},
            {'id': 'B', 'dependencies': ['A']},
            {'id': 'C', 'dependencies': ['B']},
        ]
        cycles = detect_circular_dependencies(tasks)
        self.assertGreater(len(cycles), 0)


class TestPriorityScoreCalculation(unittest.TestCase):
    """Tests for overall priority score calculation."""
    
    def setUp(self):
        self.today = date(2025, 11, 29)
    
    def test_high_priority_task(self):
        """Task with urgency + importance should be high priority."""
        task = {
            'id': 'urgent-important',
            'title': 'Critical Bug Fix',
            'due_date': self.today,  # Due today
            'estimated_hours': 2,
            'importance': 9,
            'dependencies': []
        }
        result = calculate_priority_score(task, [task], today=self.today)
        
        self.assertEqual(result['priority_level'], 'High')
        self.assertGreater(result['priority_score'], 70)
    
    def test_low_priority_task(self):
        """Task with distant due date and low importance should be low priority."""
        task = {
            'id': 'low-priority',
            'title': 'Nice to Have',
            'due_date': self.today + timedelta(days=60),
            'estimated_hours': 20,
            'importance': 2,
            'dependencies': []
        }
        result = calculate_priority_score(task, [task], today=self.today)
        
        self.assertEqual(result['priority_level'], 'Low')
        self.assertLess(result['priority_score'], 40)
    
    def test_strategy_affects_score(self):
        """Different strategies should produce different rankings."""
        quick_task = {
            'id': 'quick',
            'title': 'Quick Task',
            'due_date': self.today + timedelta(days=14),
            'estimated_hours': 1,
            'importance': 5,
            'dependencies': []
        }
        long_important = {
            'id': 'important',
            'title': 'Important Task',
            'due_date': self.today + timedelta(days=14),
            'estimated_hours': 20,
            'importance': 10,
            'dependencies': []
        }
        tasks = [quick_task, long_important]
        
        # With fastest_wins, quick task should score higher
        quick_result = calculate_priority_score(
            quick_task, tasks, strategy='fastest_wins', today=self.today
        )
        important_result = calculate_priority_score(
            long_important, tasks, strategy='fastest_wins', today=self.today
        )
        self.assertGreater(quick_result['priority_score'], important_result['priority_score'])
        
        # With high_impact, important task should score higher
        quick_result2 = calculate_priority_score(
            quick_task, tasks, strategy='high_impact', today=self.today
        )
        important_result2 = calculate_priority_score(
            long_important, tasks, strategy='high_impact', today=self.today
        )
        self.assertGreater(important_result2['priority_score'], quick_result2['priority_score'])


class TestAnalyzeTasks(unittest.TestCase):
    """Tests for the main analyze_tasks function."""
    
    def setUp(self):
        self.today = date(2025, 11, 29)
        self.sample_tasks = [
            {
                'id': '1',
                'title': 'Low priority task',
                'due_date': '2025-12-15',
                'estimated_hours': 8,
                'importance': 3,
                'dependencies': []
            },
            {
                'id': '2',
                'title': 'High priority task',
                'due_date': '2025-11-30',  # Tomorrow
                'estimated_hours': 2,
                'importance': 9,
                'dependencies': []
            },
            {
                'id': '3',
                'title': 'Medium priority',
                'due_date': '2025-12-05',
                'estimated_hours': 4,
                'importance': 6,
                'dependencies': []
            }
        ]
    
    def test_tasks_are_sorted_by_priority(self):
        """Tasks should be returned sorted by priority score (descending)."""
        result = analyze_tasks(self.sample_tasks, today=self.today)
        
        self.assertEqual(len(result['tasks']), 3)
        
        scores = [t['priority_score'] for t in result['tasks']]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_result_contains_required_fields(self):
        """Result should contain all required fields."""
        result = analyze_tasks(self.sample_tasks, today=self.today)
        
        self.assertIn('tasks', result)
        self.assertIn('summary', result)
        self.assertIn('warnings', result)
        
        for task in result['tasks']:
            self.assertIn('priority_score', task)
            self.assertIn('priority_level', task)
            self.assertIn('explanation', task)


class TestGetSuggestions(unittest.TestCase):
    """Tests for the get_suggestions function."""
    
    def setUp(self):
        self.today = date(2025, 11, 29)
        self.sample_tasks = [
            {'id': '1', 'title': 'Task 1', 'due_date': '2025-12-01', 
             'estimated_hours': 2, 'importance': 8, 'dependencies': []},
            {'id': '2', 'title': 'Task 2', 'due_date': '2025-12-05',
             'estimated_hours': 4, 'importance': 6, 'dependencies': []},
            {'id': '3', 'title': 'Task 3', 'due_date': '2025-12-10',
             'estimated_hours': 8, 'importance': 4, 'dependencies': []},
            {'id': '4', 'title': 'Task 4', 'due_date': '2025-12-15',
             'estimated_hours': 16, 'importance': 2, 'dependencies': []},
        ]
    
    def test_returns_top_3_by_default(self):
        """Should return top 3 tasks by default."""
        result = get_suggestions(self.sample_tasks, today=self.today)
        
        self.assertEqual(len(result['tasks']), 3)
    
    def test_returns_requested_count(self):
        """Should return the requested number of tasks."""
        result = get_suggestions(self.sample_tasks, count=2, today=self.today)
        
        self.assertEqual(len(result['tasks']), 2)
    
    def test_includes_suggestion_text(self):
        """Each task should include suggestion text."""
        result = get_suggestions(self.sample_tasks, today=self.today)
        
        for task in result['tasks']:
            self.assertIn('suggestion', task)
    
    def test_includes_summary_advice(self):
        """Result should include summary advice."""
        result = get_suggestions(self.sample_tasks, today=self.today)
        
        self.assertIn('summary', result)
        self.assertTrue(len(result['summary']) > 0)


# Edge case tests
class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error handling."""
    
    def test_empty_task_list(self):
        """Should handle empty task list gracefully."""
        result = analyze_tasks([])
        
        self.assertEqual(len(result['tasks']), 0)
        self.assertIn('summary', result)
    
    def test_task_with_missing_fields(self):
        """Should handle tasks with missing optional fields."""
        task = {
            'title': 'Minimal Task',
            'due_date': '2025-12-01'
            # Missing: estimated_hours, importance, dependencies
        }
        result = calculate_priority_score(task, [task])
        
        self.assertIn('priority_score', result)
        self.assertIn('priority_level', result)
    
    def test_invalid_date_format(self):
        """Should handle invalid date formats."""
        task = {
            'id': 'bad-date',
            'title': 'Bad Date Task',
            'due_date': 'not-a-date',
            'estimated_hours': 4,
            'importance': 5,
            'dependencies': []
        }
        # Should not raise an exception
        result = calculate_priority_score(task, [task])
        self.assertIn('priority_score', result)


if __name__ == '__main__':
    unittest.main()

