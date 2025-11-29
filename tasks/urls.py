"""
URL routing for Tasks API.
"""

from django.urls import path
from .views import AnalyzeTasksView, SuggestTasksView, StrategiesView, FeedbackView

urlpatterns = [
    path('analyze/', AnalyzeTasksView.as_view(), name='analyze-tasks'),
    path('suggest/', SuggestTasksView.as_view(), name='suggest-tasks'),
    path('strategies/', StrategiesView.as_view(), name='strategies'),
    path('feedback/', FeedbackView.as_view(), name='feedback'),
]

