"""
Обработчики HTTP запросов приложения.
"""
from .auth import auth_routes
from .predictions import prediction_routes
from .history import history_routes
from .feedback import feedback_routes
from .health import health_routes

__all__ = [
    'auth_routes',
    'prediction_routes',
    'history_routes',
    'feedback_routes',
    'health_routes'
]
