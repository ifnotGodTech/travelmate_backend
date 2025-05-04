from rest_framework.response import Response
from rest_framework import status

def success_response(data=None, message=None, status_code=status.HTTP_200_OK):
    """Standard success response format"""
    return Response({
        'success': True,
        'message': message,
        'data': data
    }, status=status_code)

def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """Standard error response format"""
    return Response({
        'success': False,
        'message': message,
        'errors': errors
    }, status=status_code)
