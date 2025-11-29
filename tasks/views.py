"""
API Views for Smart Task Analyzer.

This module provides the REST API endpoints for analyzing and
prioritizing tasks.

Endpoints:
- POST /api/tasks/analyze/ - Analyze a list of tasks
- GET /api/tasks/suggest/ - Get top 3 task suggestions
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import date
import json

from .serializers import (
    AnalyzeRequestSerializer,
    TaskInputSerializer,
    TaskOutputSerializer,
)
from .scoring import analyze_tasks, get_suggestions


class AnalyzeTasksView(APIView):
    """
    POST /api/tasks/analyze/
    
    Accepts a list of tasks and returns them sorted by priority score.
    Each task includes its calculated score and explanation.
    
    Request Body:
    {
        "tasks": [
            {
                "id": "optional-id",
                "title": "Fix login bug",
                "due_date": "2025-11-30",
                "estimated_hours": 3,
                "importance": 8,
                "dependencies": []
            },
            ...
        ],
        "strategy": "smart_balance",  // optional: fastest_wins, high_impact, deadline_driven
        "weights": {}  // optional: custom weight configuration
    }
    
    Response:
    {
        "tasks": [...sorted tasks with scores...],
        "summary": "Analysis summary",
        "warnings": [...any warnings like circular dependencies...],
        "strategy": "smart_balance"
    }
    """
    
    def post(self, request):
        """Handle POST request to analyze tasks."""
        try:
            # Parse request data
            data = request.data
            
            # Handle both direct task list and wrapped format
            if isinstance(data, list):
                # Direct list of tasks
                tasks = data
                strategy = request.query_params.get('strategy', 'smart_balance')
                custom_weights = None
            else:
                # Wrapped format with tasks key
                serializer = AnalyzeRequestSerializer(data=data)
                if not serializer.is_valid():
                    return Response(
                        {
                            'error': 'Validation failed',
                            'details': serializer.errors
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                validated_data = serializer.validated_data
                tasks = validated_data.get('tasks', [])
                strategy = validated_data.get('strategy', 'smart_balance')
                custom_weights = validated_data.get('weights')
            
            # Validate individual tasks
            validated_tasks = []
            validation_errors = []
            
            for i, task in enumerate(tasks):
                task_serializer = TaskInputSerializer(data=task)
                if task_serializer.is_valid():
                    validated_tasks.append(task_serializer.validated_data)
                else:
                    validation_errors.append({
                        'index': i,
                        'task': task.get('title', f'Task {i}'),
                        'errors': task_serializer.errors
                    })
            
            # If all tasks failed validation, return error
            if validation_errors and not validated_tasks:
                return Response(
                    {
                        'error': 'All tasks failed validation',
                        'details': validation_errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Analyze tasks
            result = analyze_tasks(
                tasks=validated_tasks,
                strategy=strategy,
                custom_weights=custom_weights
            )
            
            # Add validation warnings if some tasks were skipped
            if validation_errors:
                result['warnings'].append(
                    f"{len(validation_errors)} task(s) skipped due to validation errors"
                )
                result['validation_errors'] = validation_errors
            
            return Response(result, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError:
            return Response(
                {'error': 'Invalid JSON in request body'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Internal error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SuggestTasksView(APIView):
    """
    GET /api/tasks/suggest/
    POST /api/tasks/suggest/
    
    Returns the top 3 tasks the user should work on today,
    with detailed explanations for why each was chosen.
    
    GET: Uses tasks stored in session or returns empty
    POST: Accepts tasks in request body (same format as analyze)
    
    Query Parameters:
    - count: Number of suggestions (default: 3)
    - strategy: Scoring strategy (default: smart_balance)
    
    Response:
    {
        "tasks": [
            {
                "title": "Fix login bug",
                "priority_score": 85.5,
                "explanation": "Due in 2 days - URGENT • High importance (8/10)",
                "suggestion": "🎯 Start with this one - highest priority"
            },
            ...
        ],
        "summary": "Focus on 'Fix login bug' first - it's due soon!",
        "warnings": []
    }
    """
    
    def get(self, request):
        """Handle GET request - returns suggestions for provided tasks."""
        # For GET requests, we expect tasks to be passed as JSON query param
        # or we return an informative message
        tasks_param = request.query_params.get('tasks')
        
        if tasks_param:
            try:
                tasks = json.loads(tasks_param)
            except json.JSONDecodeError:
                return Response(
                    {'error': 'Invalid JSON in tasks parameter'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Return helpful message for GET without tasks
            return Response({
                'message': 'Send a POST request with tasks to get suggestions',
                'example': {
                    'tasks': [
                        {
                            'title': 'Example task',
                            'due_date': '2025-12-01',
                            'estimated_hours': 4,
                            'importance': 7,
                            'dependencies': []
                        }
                    ]
                },
                'available_strategies': [
                    'smart_balance',
                    'fastest_wins', 
                    'high_impact',
                    'deadline_driven'
                ]
            })
        
        return self._get_suggestions(tasks, request)
    
    def post(self, request):
        """Handle POST request with tasks in body."""
        data = request.data
        
        # Handle both direct task list and wrapped format
        if isinstance(data, list):
            tasks = data
        else:
            tasks = data.get('tasks', [])
        
        return self._get_suggestions(tasks, request)
    
    def _get_suggestions(self, tasks, request):
        """Common logic for getting suggestions."""
        try:
            count = int(request.query_params.get('count', 3))
            strategy = request.query_params.get('strategy', 'smart_balance')
            
            # Validate tasks
            validated_tasks = []
            for task in tasks:
                task_serializer = TaskInputSerializer(data=task)
                if task_serializer.is_valid():
                    validated_tasks.append(task_serializer.validated_data)
            
            if not validated_tasks:
                return Response(
                    {'error': 'No valid tasks provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get suggestions
            result = get_suggestions(
                tasks=validated_tasks,
                count=count,
                strategy=strategy
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': f'Invalid parameter: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Internal error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StrategiesView(APIView):
    """
    GET /api/tasks/strategies/
    
    Returns available scoring strategies with descriptions.
    """
    
    def get(self, request):
        """Return available strategies."""
        strategies = {
            'smart_balance': {
                'name': 'Smart Balance',
                'description': 'Balanced approach considering urgency, importance, effort, and dependencies',
                'weights': {'urgency': 0.35, 'importance': 0.30, 'effort': 0.20, 'dependency': 0.15}
            },
            'fastest_wins': {
                'name': 'Fastest Wins',
                'description': 'Prioritize quick, low-effort tasks to build momentum',
                'weights': {'urgency': 0.15, 'importance': 0.15, 'effort': 0.55, 'dependency': 0.15}
            },
            'high_impact': {
                'name': 'High Impact',
                'description': 'Focus on the most important tasks first',
                'weights': {'urgency': 0.20, 'importance': 0.55, 'effort': 0.10, 'dependency': 0.15}
            },
            'deadline_driven': {
                'name': 'Deadline Driven',
                'description': 'Prioritize based on approaching deadlines',
                'weights': {'urgency': 0.55, 'importance': 0.20, 'effort': 0.10, 'dependency': 0.15}
            }
        }
        
        return Response({
            'strategies': strategies,
            'default': 'smart_balance'
        })

