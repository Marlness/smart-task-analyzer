"""
Task Model for Smart Task Analyzer.

This module defines the Task model which represents a task with properties
for priority scoring including due date, importance, estimated effort,
and dependencies on other tasks.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Task(models.Model):
    """
    Represents a task in the Smart Task Analyzer system.
    
    Attributes:
        title: The name/description of the task
        due_date: When the task is due
        estimated_hours: Estimated time to complete the task
        importance: User-provided importance rating (1-10 scale)
        dependencies: JSON list of task IDs this task depends on
        created_at: When the task was created
        updated_at: When the task was last updated
    """
    
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    estimated_hours = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Estimated hours to complete the task"
    )
    importance = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Importance rating from 1 (low) to 10 (high)"
    )
    dependencies = models.JSONField(
        default=list,
        blank=True,
        help_text="List of task IDs that this task depends on"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} (Due: {self.due_date})"

