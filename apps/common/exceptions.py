"""
Custom DRF exception handler so every API error follows a consistent shape:

{
    "success": false,
    "error": {
        "code": "validation_error",
        "message": "...",
        "details": {...}
    }
}
"""
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        return None

    error_code = getattr(exc, 'default_code', exc.__class__.__name__.lower())

    detail = response.data
    message = detail if isinstance(detail, str) else 'One or more errors occurred.'

    response.data = {
        'success': False,
        'error': {
            'code': error_code,
            'message': message,
            'details': detail if not isinstance(detail, str) else None,
        },
    }
    return response
