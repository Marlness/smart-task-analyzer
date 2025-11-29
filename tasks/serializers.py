"""
Serializers for Task API endpoints.

Provides serialization/deserialization for Task data with validation.
"""

from rest_framework import serializers
from datetime import date


class TaskInputSerializer(serializers.Serializer):
    """
    Serializer for incoming task data.
    
    Validates task input and provides default values where appropriate.
    Handles edge cases like missing or invalid data gracefully.
    """
    
    id = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(max_length=255)
    due_date = serializers.DateField()
    estimated_hours = serializers.IntegerField(min_value=1, default=1)
    importance = serializers.IntegerField(min_value=1, max_value=10, default=5)
    dependencies = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    
    def validate_title(self, value):
        """Ensure title is not empty or just whitespace."""
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty")
        return value.strip()
    
    def validate_estimated_hours(self, value):
        """Ensure estimated hours is reasonable."""
        if value <= 0:
            return 1  # Default to 1 hour for invalid values
        if value > 1000:
            raise serializers.ValidationError("Estimated hours seems unreasonably high (max 1000)")
        return value
    
    def validate(self, data):
        """
        Additional validation for the task as a whole.
        Generates an ID if not provided.
        """
        # Generate ID if not provided
        if 'id' not in data or not data['id']:
            import uuid
            data['id'] = str(uuid.uuid4())[:8]
        
        return data


class TaskOutputSerializer(serializers.Serializer):
    """
    Serializer for task output with calculated priority score.
    
    Includes all task fields plus the calculated priority score
    and explanation for why the task received its score.
    """
    
    id = serializers.CharField()
    title = serializers.CharField()
    due_date = serializers.DateField()
    estimated_hours = serializers.IntegerField()
    importance = serializers.IntegerField()
    dependencies = serializers.ListField(child=serializers.CharField())
    priority_score = serializers.FloatField()
    priority_level = serializers.CharField()  # High, Medium, Low
    explanation = serializers.CharField()
    is_overdue = serializers.BooleanField()
    days_until_due = serializers.IntegerField()
    blocking_count = serializers.IntegerField(required=False, default=0)


class AnalyzeRequestSerializer(serializers.Serializer):
    """
    Serializer for the analyze endpoint request.
    
    Accepts a list of tasks and optional strategy parameter.
    """
    
    tasks = TaskInputSerializer(many=True)
    strategy = serializers.ChoiceField(
        choices=[
            ('smart_balance', 'Smart Balance'),
            ('fastest_wins', 'Fastest Wins'),
            ('high_impact', 'High Impact'),
            ('deadline_driven', 'Deadline Driven'),
        ],
        default='smart_balance',
        required=False
    )
    
    # Optional weight configuration for advanced users
    weights = serializers.DictField(required=False, default=dict)


class SuggestResponseSerializer(serializers.Serializer):
    """
    Serializer for the suggest endpoint response.
    
    Returns top tasks with detailed explanations.
    """
    
    tasks = TaskOutputSerializer(many=True)
    summary = serializers.CharField()
    warnings = serializers.ListField(child=serializers.CharField(), required=False)

