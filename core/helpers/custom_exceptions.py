from drf_spectacular.utils import OpenApiResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class CustomError:
    class Forbidden(APIException):
        status_code = status.HTTP_403_FORBIDDEN
        default_code = "forbidden"
        default_detail = "You do not have permission to perform this action."

    class ServiceUnavailable(APIException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        default_code = "service_unavailable"
        default_detail = "Service temporarily unavailable, please try again later."

    class BadRequest(APIException):
        status_code = status.HTTP_400_BAD_REQUEST
        default_code = "bad_request"
        default_detail = "Bad request."

    class NotFound(APIException):
        status_code = status.HTTP_404_NOT_FOUND
        default_code = "not_found"
        default_detail = "Resource not found."

    class NotAcceptable(APIException):
        status_code = status.HTTP_406_NOT_ACCEPTABLE
        default_code = "not_acceptable"
        default_detail = "Not acceptable."

    class MethodNotAllowed(APIException):
        status_code = status.HTTP_405_METHOD_NOT_ALLOWED
        default_code = "method_not_allowed"
        default_detail = "Method not allowed."

    class Redirect(APIException):
        status_code = status.HTTP_302_FOUND
        default_code = "redirect"
        default_detail = "Redirect."

    class UnAuthorized(APIException):
        status_code = status.HTTP_401_UNAUTHORIZED
        default_code = "unauthorized"
        default_detail = "Unauthorized."

    class Conflict(APIException):
        status_code = status.HTTP_409_CONFLICT
        default_code = "conflict"
        default_detail = "Conflict."

    class InternalServerError(APIException):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        default_code = "internal_server_error"
        default_detail = "Internal server error."

    @classmethod
    def raise_error(
        cls,
        message: str,
        exception: str = "BadRequest",
    ):
        e: APIException = getattr(cls, exception)
        raise e(message)

    error_responses = [
        "Forbidden",
        "ServiceUnavailable",
        "BadRequest",
        "EmptyResponse",
        "NotFound",
        "NotAcceptable",
        "MethodNotAllowed",
        "Redirect",
        "UnAuthorized",
    ]

    @classmethod
    def DEFAULT_ERROR_SCHEMA(cls):  # noqa: N802
        return {
            getattr(cls, error).status_code: {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "example": getattr(cls, error).default_detail,
                    },
                },
            }
            for error in cls.error_responses
        }


DEFAULT_ERROR_SCHEMA = {
    status.HTTP_400_BAD_REQUEST: {
        "detail": "Bad Request",
    },
    status.HTTP_403_FORBIDDEN: {
        "detail": "You do not have the permission to perform this action",
    },
    status.HTTP_404_NOT_FOUND: {
        "detail": "Not Found",
    },
}


def create_response_schema(entity_name, serializer_retrieve, id_message):
    return {
        status.HTTP_201_CREATED: OpenApiResponse(
            response=serializer_retrieve,
            description=f"Successfully created {entity_name}.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            description="Bad Request",
            response=CustomError.DEFAULT_ERROR_SCHEMA(),
            examples={
                "application/json": {
                    "detail": f"{entity_name.capitalize()} with the provided {id_message} already exists.",  # noqa: E501
                },
            },
        ),
        **CustomError.DEFAULT_ERROR_SCHEMA(),
    }


def get_all_schema(entity_name, serializer_class):
    return {
        status.HTTP_200_OK: OpenApiResponse(
            response=serializer_class,
            description="Successfully retrieved list of devices.",
        ),
        **CustomError.DEFAULT_ERROR_SCHEMA(),
    }


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now modify the response to ensure all error values are in a list.
    if response is not None:
        if isinstance(response.data, dict):
            for key, value in response.data.items():
                if not isinstance(value, list):
                    response.data[key] = [value]
    return response
