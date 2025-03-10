import asyncio
import logging
import re
import secrets
import urllib.parse
from collections import OrderedDict
from collections.abc import Callable
from inspect import getframeinfo
from inspect import stack
from itertools import permutations
from operator import itemgetter
from os import getenv
from typing import Any
from typing import Literal
from unittest.mock import MagicMock
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mass_mail
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Subquery
from django.http import HttpRequest
from django.http import QueryDict
from django.utils import timezone
from django.utils.timesince import timeuntil
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.filters import SearchFilter
from rest_framework_simplejwt.tokens import RefreshToken

from core.helpers.custom_exceptions import CustomError

# from core.helpers.enums import NotificationActionSchema, NotificationType


def get_device_snapshot_data_(data: dict, spec_id: int | str) -> bool:
    """
    Check if a device is safe based on pollutant data from a device.

    Args:
        data (dict): A dictionary with pollutant names as keys and their values
            as values.
        spec_id (int | str): The ID of the device specification.

    Returns:
        bool: A list of boolean values indicating whether the device is safe or
            not for each pollutant.
    """
    checks = []
    datas = []
    status = "UNKNOWN"
    response = {"id": None, "name": None, "symbol": None, "snapshot": {}}
    cache.delete(f"POLLUTANTS_DATA_{spec_id}")
    pollutants_data = cache.get(f"POLLUTANTS_DATA_{spec_id}")
    if not pollutants_data:
        from core.backend.devices.models import Specification
        pollutants_data = {}
        for pollutant in Specification.objects.get(id=spec_id).pollutants.all():
            pollutants_data[pollutant.name] = {
                    "name": pollutant.name,
                    "id": pollutant.id,
                    "threshold": pollutant.threshold,
                    "symbol": pollutant.symbol,
                }
        cache_key = f"POLLUTANTS_DATA_{spec_id}"  # Using instance.id for a unique cache key
        cache.set(cache_key, pollutants_data, timeout=None)

    if data and pollutants_data:
        for key, value in data.items():
            pollutant = pollutants_data.get(key)
            if pollutant:
                response["id"] = pollutant.get("id")
                response["name"] = pollutant.get("name")
                response["symbol"] = pollutant.get("symbol")
                response["snapshot"]["pollutant_state"] = {
                    True: "SAFE",
                    False: "UNSAFE",
                }.get(value > pollutants_data.get(key).get("threshold")) or "Unknown"
                response["snapshot"]["summary"] = {
                    "SAFE": "Normal",
                    "UNSAFE": f"High {pollutant.get('symbol')} level",
                }.get(response["snapshot"]["pollutant_state"]) or "Unknown"
                response["snapshot"]["value"] = value
                datas.append(response)
        status = {
            True: "SAFE",
            False: "UNSAFE",
            None: "UNKNOWN",
        }.get(all(checks), None)

    return status, response

def get_device_snapshot_data(data: dict, spec_id: int | str) -> bool:
    """
    Check if a device is safe based on pollutant data from a device.

    Args:
        data (dict): A dictionary with pollutant names as keys and their values
            as values.
        spec_id (int | str): The ID of the device specification.

    Returns:
        bool: A list of boolean values indicating whether the device is safe or
            not for each pollutant.
    """
    cache_key = f"POLLUTANTS_DATA_{spec_id}"
    pollutants_data = cache.get(cache_key)

    if not pollutants_data:
        from core.backend.devices.models import Specification
        pollutants_data = {
            pollutant.name: {
                "name": pollutant.name,
                "id": pollutant.id,
                "threshold": pollutant.threshold,
                "symbol": pollutant.symbol,
            }
            for pollutant in Specification.objects.get(id=spec_id).pollutants.all()
        }
        cache.set(cache_key, pollutants_data, timeout=None)

    datas = []
    status = "UNKNOWN"

    if data and pollutants_data:
        for key, value in data.items():
            if (pollutant := pollutants_data.get(key)):
                is_safe = value <= pollutant["threshold"]
                pollutant_state = "SAFE" if is_safe else "UNSAFE"
                datas.append({
                    "id": pollutant["id"],
                    "name": pollutant["name"],
                    "symbol": pollutant["symbol"],
                    "snapshot": {
                        "pollutant_state": pollutant_state,
                        "summary": "Normal" if is_safe else f"High {pollutant['symbol']} level",
                        "value": value,
                    }
                })

        status = "SAFE" if all(d["snapshot"]["pollutant_state"] == "SAFE" for d in datas) else "UNSAFE"

    return status, datas

def short_uuid():
    # Generate a UUID version 4 object
    uuid_obj = uuid4()

    # Convert the UUID object to a hexadecimal string
    uuid_hex = uuid_obj.hex

    # Truncate the hexadecimal string to 8 characters
    uuid_short = uuid_hex[:6]

    # Return the truncated UUID string
    return uuid_short


def booleanize(value):
    """
    This function turns statements into booleans

    Returns:
        Boolean: True or False
    """
    returned_value = False
    if value == "true":
        returned_value = True
    elif value == "false":
        returned_value = False
    return returned_value


# def create_notification(
#     account: object,
#     title: str,
#     actions: NotificationActionSchema = None,
#     message=str,
#     thumbnail: str = None,
#     note_type: NotificationType = NotificationType.INFO,
# ):
#     from core.backend.notifications.models import Notification

#     Notification.objects.create(
#         user=account.user,
#         account=account,
#         type=note_type,
#         title=title,
#         message=message,
#         thumbnail=thumbnail,
#         actions=actions,
#     )


# def send_notification_by_instance_type(data, account: object | list[object]):
#     if isinstance(data, list):
#         for count, item in enumerate(data):
#             create_notification(
#                 account=account[count],
#                 title=item["title"],
#                 message=item["message"],
#                 note_type=NotificationType.SUCCESS,
#             )
#     else:
#         create_notification(
#             account=account,
#             title=data["title"],
#             message=data["message"],
#             note_type=NotificationType.SUCCESS,
#         )


def send_email_by_instance_type(data, from_email, recipient_list, extra: tuple = None):
    if isinstance(data, list):
        mail_multiple = (
            (
                data[0]["title"],
                data[0]["message"],
                from_email,
                [recipient_list[0]],
            ),
            (
                data[1]["title"],
                data[1]["message"],
                from_email,
                [recipient_list[1]],
            ),
            extra,
        )

    else:
        mail_multiple = (
            (
                data["title"],
                data["message"],
                from_email,
                recipient_list,
            ),
            extra,
        )
    send_mass_mail(mail_multiple)


def country_name_to_country_code_mapper(country: str):
    country = country.title()
    countries = {"Nigeria": "ng", "Ghana": "gh", "Kenya": "ke"}
    return countries.get(country)


async def close_pools(chan_layer):
    try:
        await chan_layer.close_pools()
    except ValueError:
        asyncio.sleep(1)
        close_pools(chan_layer)


async def closing_send(chan_layer, channel, message):
    await chan_layer.group_send(channel, message)
    await close_pools(chan_layer)


def get_bearer_token(request: HttpRequest) -> str:
    if hasattr(request, "is_websocket"):
        return request.query_params.get("authorization")
    authorization = request.headers.get("authorization")
    return authorization.split(" ")[1] if authorization else None


def get_user_uuid_token(user):
    from djoser import utils

    context = {}
    context["uid"] = utils.encode_uid(user.pk)
    context["token"] = default_token_generator.make_token(user)
    return context


def float_to_datetime(float_value: float | str) -> str:
    """
    Convert a float representing a future datetime to a datetime string
    or return "No Load" if no load is present

    Parameters:
        float_value (float): The float value representing the future datetime,
                             where the integer part is the number of days and
                             the fractional part represents the hours, minutes,
                             and seconds within 24 hours.

    Returns:
        datetime: The corresponding datetime object.
    """
    if float_value == "inf" or float_value is None:
        return None

    # Split the float value into integer and fractional parts
    days = int(float_value) if float_value else 0
    fractional_part = float_value - days

    # Calculate timedelta for days
    delta_days = timezone.timedelta(days=days)

    # Calculate timedelta for hours, minutes, and seconds
    delta_time = timezone.timedelta(hours=24 * fractional_part)

    # Calculate the future datetime
    future_datetime = timezone.datetime.now() + delta_days + delta_time
    return future_datetime.isoformat()


month_dict = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


month_abbv_dict = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def get_percentage_diff(first, second):
    try:
        percentage = abs(first - second) / ((first + second) / 2) * 100
    except ZeroDivisionError:
        percentage = float("inf")  # Handle division by zero
    return percentage


def datetime_to_human_understanding(datetime: str) -> str:
    """
    Convert a datetime string to a human-understandable format

    Parameters:
        datetime (str): The datetime string in ISO format.

    Returns:
        str: The corresponding human-understandable datetime string.
    >>> datetime_to_human_understanding("2022-01-01T00:00:00Z")
    "5 days"
    """
    if datetime is None:
        return "No Load"
    if isinstance(datetime, timezone.datetime):
        datetime = datetime.isoformat()
    return timeuntil(timezone.datetime.fromisoformat(datetime), depth=1)


def get_user_refresh_access_token(user):
    refresh = RefreshToken.for_user(user)
    data = {}
    data["refresh"] = str(refresh)
    data["access"] = str(refresh.access_token)
    return data


def silent(obj: object):
    try:
        return obj
    except Exception:
        return None


def get_file_path(instance, filename):
    import os
    import uuid

    filename = uuid.uuid4().hex[:8] + os.path.splitext(filename)[1]
    path = f"{instance.owner.id}/{instance.mimetype}/{filename}"
    return path


class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()

class AsyncTimer:
    def __init__(self, callback):
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self):
        await self._callback()

    async def cancel(self):
        await self._task.cancel()


def convert_and_compress_error(
    value: Any,
    converter: callable = str,
    allowed_values: list[Any] = [],
    raise_exception: bool = False,
    *args,
    **kwargs,
) -> Any | None:
    """function is used to convert from one datatype to the other without
    throwing an error if type is not convertible

    Args:
        value (Any): _description_
        converter (callable, optional): _description_. Defaults to str.
        allowed_values (List[Any]): _description_. Defaults to list
        raise_exception (bool, optional): _description_. Defaults to False.

    Returns:
        Union[Any,None]: _description_
    """
    if value is None or (allowed_values and value not in allowed_values):
        return None
    if raise_exception:
        return converter(value)

    try:
        return converter(value)
    except ValueError:
        ...


def get_image_path(instance, filename):
    return get_file_path(instance, filename)


def get_post_video_path(instance, filename):
    return get_file_path(instance, filename)


def get_doc_path(instance, filename):
    return get_file_path(instance, filename)


def get_random_models(n: int, model: str, app_label: str = "users") -> list[int]:
    """
    Returns a list of random interests ids
    """
    from django.apps import apps

    model = apps.get_model(app_label, model)

    return [obj for obj in model.objects.all().order_by("?").values_list("id", flat=True).distinct()[:n]]


def is_video(filename: str) -> bool:
    """
    Returns True if the file is a video
    """
    import mimetypes

    return mimetypes.guess_type(filename)[0].startswith("video")


def is_image(filename: str) -> bool:
    import mimetypes

    return mimetypes.guess_type(filename)[0].startswith("image")


def is_document(filename: str) -> bool:
    import mimetypes

    return mimetypes.guess_type(filename)[0].startswith("text") or mimetypes.guess_type(
        filename,
    )[
        0
    ].startswith("application")


def calculate_age(born):
    from datetime import date

    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def validate_age(date_of_birth):
    from django.utils.translation import gettext_lazy as _

    if calculate_age(date_of_birth) < 13:
        raise CustomError.BadRequest(
            _("You must be at least 13 years old."),
        )


def generate_referal_code(length: int = 5, name: str | None = ""):
    return name + uuid4().hex.upper()[:length]


def generate_barcode():
    return secrets.token_hex(15)


def generate_ref(length: int | None = None):
    return secrets.token_urlsafe(length).replace("_", "").replace("-", "")[:length]


def generate_id(length: int = 10):
    """generate id for all the models

    Args:
        length (int, optional): _description_. Defaults to 10.

    Returns:
        _type_: _description_
    """
    return uuid4().hex[:length]


def generate_api_key():
    """generate id for all the models

    Args:
        length (int, optional): _description_. Defaults to 10.

    Returns:
        _type_: _description_
    """
    return f"api_key_{secrets.token_urlsafe()}"


def payment_ref_generator(prefix: str = "PAY", length: int = 10):
    """generate reference for payment transactin

    Args:
        prefix (str, optional): _description_. Defaults to None.
        length (int, optional): _description_. Defaults to 10.
    """

    def wrapper():
        return f"{prefix}-{uuid4().hex[:length]}"

    return wrapper


def get_user_models_tagged_in_content(content: str) -> QuerySet:
    """function extract all the user tagged in a string

    Args:
        content (str): _description_

    Returns:
        QuerySet: _description_
    """
    User = get_user_model()
    regex = r"@(\w+)"
    matches = re.findall(regex, content, re.MULTILINE)
    return User.objects.filter(username__in=matches)


def get_hashtag_from_tagged_content(content: str) -> QuerySet:
    """function extract all the hastags models  in a string

    Args:
        content (str): _description_

    Returns:
        QuerySet: _description_
    """
    regex = r"#(\w+)"
    return re.findall(regex, content, re.MULTILINE)


def generate_room_uid():
    return generate_id(length=20)


def log(msg, *args, instance: object = None, method: callable = None):
    """logger

    Args:
        msg (_type_): _description_
        instance (object, optional): _description_. Defaults to None.
        method (callable, optional): _description_. Defaults to None.
    """
    # generate debug info
    caller = getframeinfo(stack()[1][0])

    # generate debug info

    classname = instance.__class__.__name__ if instance else ""
    method_name = method.__name__ if method else ""

    if method_name:
        method_name = f".{method_name}()"

    if classname:
        classname = f"[{classname}]"

    print("============================================")
    print(("%s:%d - %s" % (caller.filename, caller.lineno, "")).replace("/app/", ""))
    print("============================================")
    print("\n", classname, method_name, msg, *args, "\n")
    print("============================================\n")


def transform_event_data(event_data={}, *args):
    """_summary_

    Args:
        event_data (dict, optional): _description_. Defaults to {}.

    Returns:
        Dict: {
            "method_name":str,
            "event":str,
            "body":dict,
            "params":dict
        }
    """
    method_name = event_data.get("type", "")

    event = (method_name[3:] if method_name.startswith("on_") else method_name).replace(
        "_",
        ".",
    )

    body = event_data.get("data", {})
    exclude_channels = event_data.get("exclude_channels", [])
    params = event_data.get("params", {})
    result = {
        "method_name": method_name,
        "event": event,
        "body": body,
        "params": params,
        "exclude_channels": exclude_channels,
    }
    if not args:
        return result

    return itemgetter(*args)(result)


def filter_fields(
    data: dict[str, Any],
    include: list[str] = [],
    exclude: list[str] = [],
):
    """filter certain fields from dictionary

    Args:
        data (Dict[str,Any]): dictionary to filter
        include (List[str], optional): list of keys to include in the new dictionary. Defaults to [].
        exclude (List[str], optional): list of keys to exclude in the new dictionary. Defaults to [].
    """
    result = {}

    for key, value in data.items():
        if (
            include
            and (value or value in [False, 0])
            and key in include
            or exclude
            and (value or value in [False, 0])
            and key not in exclude
            or value
            or value in [False, 0]
        ):
            result[key] = value

    return result


def get_changed_fields(prev, current):
    """function to compare two dict and return a
        list of fields that have changed

    Args:
        prev (_type_): _description_
        current (_type_): _description_

    Returns:
        _type_: _description_
    """

    prev = prev or {}
    current = current or {}

    if not all([prev, current]):
        data = prev or current
        return [key for key, _ in data.items()]

    current_item_list = list(current.items())
    prev_item_list = list(prev.items())
    assert len(current_item_list) == len(
        prev_item_list,
    ), "previous data and current data must have the same number of keys"
    result = []
    for index in range(len(current_item_list)):
        if current_item_list[index][1] != prev_item_list[index][1]:
            result.append(current_item_list[index][0])
    return result


def get_all_methods_starting_with(
    instance: object,
    startswith: str,
    *args,
    **kwargs,
) -> list[callable]:
    log("get_all_methods_starting_with()", instance=instance)
    """return a list of method starting with the startswith string

    Args:
        instance (object): _description_
        startswith (str, optional): _description_. Defaults to None.

    Returns:
        List[callable]: list of callable
    """

    return [
        getattr(instance, method_name)
        for method_name in dir(instance)
        if method_name.startswith(startswith) and callable(getattr(instance, method_name))
    ]


def make_distinct(qs: QuerySet, field: str = "id") -> QuerySet:
    """function generate unique queryset using subquery

    Args:
        qs (QuerySet): description
        field (str, optional): description. Defaults to "id".

    Returns:
        QuerySet: description
    """
    kwargs = {f"{field}__in": Subquery(qs.values(field))}
    return qs.model.objects.filter(**kwargs)


class FilterAndSearchManager:
    def __init__(
        self,
        *,
        request: HttpRequest,
        filterset_fields: list[str] = [],
        filterset_keys: dict[str, Callable[[Any], Any | None]] = {},
        search_fields: list[str] = [],
        ordering_fields: list[str] = [],
        ordering: list[str] = [],
        filter_map: dict[str, str | list[str]] = {},
    ) -> None:
        """filter, ordering and search management class

        Args:
            request (HttpRequest): django request object
            filterset_fields (list[str], optional): a list of fields in the queryset
            to used and perform filters. Defaults to [].
            filterset_keys (dict[str,Callable[[Any],Any|None]], optional): \
                a dict of field_name:converter queryset in the queryset. Defaults to {
                "rating":int,
                "price":float
            }.
            search_fields (list[str], optional): fields to used for search. Defaults to [].
            ordering_fields (list[str], optional): fileds to use for default ordering
            when ordering is not specified. Defaults to [].
            ordering (list[str], optional): fields allowed to be used for ordering when
            specifying ordering in the request object. Defaults to [].
            filter_map (dict[str,str | list[str]], optional): a dictionary where the key is
              the query params key in the request and the value is the key that will be
              used for the filter. Defaults to {}.

        Examples:
            filter_map: {
                "courses":[
                    "student_teams__courses__id",
                    "instructor_teams__courses__id",
                ],
                "owner":"courses__owner__id",
                "rating[]":"courses__rating",
            }
        """

        self.filterset_fields = filterset_fields
        self.search_fields = search_fields
        self.ordering_fields = ordering_fields
        self.ordering = ordering
        self.request = request
        self.filter_map = filter_map
        self.filterset_keys = filterset_keys

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    def subpress_error(
        self,
        function: Callable[[Any], Any | None],
        value: Any,
    ) -> Any | None:
        try:
            return function(value)
        except (ValueError, TypeError):
            # Ignore errors raised during conversion and continue to the next field.
            pass

    def build_filter_params(
        self,
        request: HttpRequest,
        field_callable_dict: dict[
            str,
            Callable[[Any], Any] | list[Callable[[Any], Any]],
        ],
    ) -> dict[str, Any]:
        """
        Build filter parameters for Django queryset filter function from request data.

        Parameters:
            request (django.http.HttpRequest): The Django request object containing the data.
            field_callable_dict (dict[str, Callable[[Any], Any]|list[Callable[[Any], Any]]]):\
                 A dictionary with field names as keys and callables as values.

        Returns:
            dict: A dictionary of filter parameters to be used with Django queryset .filter() function.
        """
        filter_params = {}

        if not isinstance(request.GET, QueryDict):
            return filter_params

        for field, field_callable in field_callable_dict.items():
            if isinstance(field_callable, list) and len(field_callable) > 0:
                # If the field_callable is specified as a list, apply each converter to the list of values.
                values = request.GET.getlist(field)
                converted_values = [
                    self.subpress_error(callable_item, val)
                    for val, callable_item in zip(values, field_callable, strict=False)
                ]
                # Filter out None and empty values from the converted list.
                converted_values = [val for val in converted_values if val is not None]
                if converted_values:
                    filter_params[field] = converted_values
            else:
                # If the field_callable is not a list, apply the converter to the single value.
                value = request.GET.get(field)
                if value is not None:
                    try:
                        converted_value = field_callable(value)
                        if converted_value is not None:
                            filter_params[field] = converted_value
                    except (ValueError, TypeError):
                        # Ignore errors raised during conversion and continue to the next field.
                        pass

        return filter_params

    def filter_queryset_with_filterset_keys(self, queryset: QuerySet) -> QuerySet:
        """method take in a queryset and filter it based on the mapping that was provided
        with filterset_keys

        filterset_keys:
        {
            "name":str,
            "age":int, #this retrieve it as a single value
            "ids":[str] #this try retriving the query params as a list
        }

        Args:
            queryset (QuerySet):

        Returns:
            QuerySet:
        """
        if not self.filterset_keys:
            return queryset

        kwargs = self.build_filter_params(self.request, self.filterset_keys)
        if kwargs:
            queryset = queryset.filter(**kwargs)

        return queryset

    def filter_queryset_with_dict_maping(self, queryset: QuerySet) -> QuerySet:
        """method take in a queryset and filter it based on the mapping that was provided

        Args:
            queryset (QuerySet):

        Returns:
            QuerySet:
        """
        if not self.filter_map:
            return queryset

        query_params: QueryDict = self.request.GET  # get query dictionary
        query_kwargs = {}
        for key, value in self.filter_map.items():  # loop through the filter map
            if key in query_params.dict():  # if the filter map key exists
                if type(value) is str:  # check if it is string
                    data_list = query_params.getlist(key)
                    data_single = query_params.get(key)
                    if data_list:
                        query_kwargs[f"{value}__in"] = data_list
                    elif data_single:
                        query_kwargs[value] = data_single
                elif type(value) is list:
                    q = Q()
                    data_list = query_params.getlist(key)
                    data_single = query_params.get(key)

                    if data_list:
                        for sub_value in value:
                            q |= Q(**{f"{sub_value}__in": data_list})
                        queryset = queryset.filter(q)
                    elif data_single:
                        query_kwargs[value] = query_params.get(key)
                        for sub_value in value:
                            q |= Q(**{sub_value: data_single})
                        queryset = queryset.filter(q)

        if query_kwargs:
            queryset = queryset.filter(**query_kwargs)

        return queryset

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Given a queryset, filter it with whichever filter backend is in use.

        You are unlikely to want to override this method, although you may need
        to call it either from a list view, or from a custom `get_object`
        method if you want to apply the configured filtering backend to the
        default queryset.
        """
        for Backend in list(self.filter_backends):
            backend: DjangoFilterBackend = Backend()
            queryset = backend.filter_queryset(self.request, queryset, self)
        self.filter_queryset_with_dict_maping(queryset)
        return queryset


class BaseModelMixin(models.Model):
    id: int = models.BigAutoField(primary_key=True)
    uid: str = models.CharField(default=generate_id, editable=False, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, editable=True)
    updated_at = models.DateTimeField(
        auto_now=True,
        auto_now_add=False,
        db_index=True,
        editable=True,
    )
    active = models.BooleanField(_("active"), default=True, db_index=True)

    def __str__(self):
        return f"< {type(self).__name__}({self.id}) >"

    @classmethod
    def _serializer_fields(cls, exclude=[], *args):
        args = ["id", "active", "created_at", "updated_at", *args]
        return sorted(list({field for field in args if field and field not in exclude}))

    @classmethod
    def _serializer_extra_kwargs(cls, exclude=[], **kwargs: dict[str, Any]):
        return {key: value for key, value in kwargs.items() if value and key not in exclude}

    @classmethod
    def serializer_fields(cls, *args, exclude=[]):
        return cls._serializer_fields(exclude, *args)

    @classmethod
    def serializer_extra_kwargs(cls, exclude=[], **kwargs):
        return cls._serializer_extra_kwargs(exclude, **kwargs)

    def get_field_or_none(self, field_name: str) -> tuple[bool, Any]:
        """get a field or return <is not None>,data


        res = getattr(self,field_name,None)\n
        return res is not None,res


        Args:
            field_name (str): _description_

        Returns:
            Tuple[bool,Any]: return result . True,Any
        """
        res = getattr(self, field_name, None)
        return res is not None, res

    def get_attribute_by_path(self, obj: object, dot_path: str) -> Any | None:
        """
        Retrieve an attribute or method of an object using a dot-separated path.

        Args:
            obj: The object to search within.
            dot_path (str): Dot-separated path to the attribute/method.

        Returns:
            Any|None: The attribute or method if found, or None if not found.
        """
        path_components = dot_path.split(".")
        current_obj = obj

        for component in path_components:
            if hasattr(current_obj, component):
                current_obj = getattr(current_obj, component)
            else:
                return None

        return current_obj

    class Meta:
        abstract = True
        ordering = ["-created_at", "id"]


class TestHelper:
    def add_permission_side_effect(
        self,
        mock_dependency: MagicMock,
        permission: dict[str, Any],
    ) -> MagicMock:
        mock_dependency.side_effect = lambda base_url, service, permission_id, dot_path: permission.get(dot_path)
        return mock_dependency

    def generate_timedelta(
        self,
        when: Literal["before", "after"],
        period: Literal["weeks", "days", "minutes", "seconds"] = "days",
        value: int = 2,
    ) -> str:
        """
        Args:
            when (Literal["before", "after"]): description
            period (Literal["weeks", "days", "minutes", "seconds"]): description
            value (int): description
        """
        if when == "before":
            return (timezone.now() - timezone.timedelta(**{period: value})).date().isoformat()
        if when == "after":
            return (timezone.now() + timezone.timedelta(**{period: value})).date().isoformat()

    def no_duplicate(
        self,
        data: list[str | int] | list[dict[str, Any]],
        id_field: str | int = "id",
    ) -> bool:
        if not data:
            return True
        if type(data[0]) in [dict, OrderedDict]:
            data = [x.get(id_field) for x in data]
        return len(data) == len(set(data))

    def has_no_duplicate_in_response_results(
        self,
        response,
        id_field: str | int = "id",
    ) -> bool:
        data: list[str | int] | list[dict[str, Any]] = response.data.get("results")
        if not data:
            return True
        if type(data[0]) in [dict, OrderedDict]:
            data = [x.get(id_field) for x in data]
        return len(data) == len(set(data))

    def has_fields(self, response, fields: list[int | str]) -> bool:
        data: dict = response.data
        conditions = []
        for x in fields:
            exist = x in data
            conditions.append(exist)
            if not exist:
                logging.warning("field -> '%s' does not exists", x)
        return all(conditions)

    def has_specified_fields(self, data: dict, fields: list[int | str]) -> bool:
        conditions = []
        for x in fields:
            exist = x in data
            conditions.append(exist)
            if not exist:
                logging.warning("field -> '%s' does not exists", x)
        return all(conditions)

    def extract_results_in_response(self, response) -> list[dict]:
        return response.data.get("results")

    def has_fields_in_response_results(self, response, fields: list[int | str]) -> bool:
        results: list[dict] = response.data.get("results")
        if not results:
            return False
        data: dict = results[0]
        conditions = []
        for x in fields:
            exist = x in data
            conditions.append(exist)
            if not exist:
                logging.warning("field -> '%s' does not exists", x)
        return all(conditions)

    def has_paginated_count(self, response, count: int) -> bool:
        return response.data.get("count") == count

    def has_response_status(self, response, status_code: int) -> bool:
        return response.status_code == status_code

    def add_query_params_to_url(self, url: str, params: dict[str, Any]) -> str:
        query_string = urllib.parse.urlencode(params)
        return f"{url}?{query_string}"


def duration_to_timedelta(value):
    """Convert a duration string in the format "DAYS:HH:MM:SS" to a timedelta object."""
    try:
        days, hours, minutes, seconds = map(int, value.split(":"))
        return timezone.timedelta(
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
        )
    except ValueError:
        return None


def suggest_ticker(ticker, predefined_list):
    def valid_permutation(ticker, predefined_list):
        for perm in permutations(ticker):
            new_str = ticker[:2] + "".join(perm)
            if new_str not in predefined_list:
                return new_str
        return None

    # Check permutations of the last 3 characters
    result = valid_permutation(ticker[2:], predefined_list)
    if result:
        return ticker[:2] + result

    # Check permutations of the last 2 characters if the 3-character permutation did not work
    result = valid_permutation(ticker[3:], predefined_list)
    if result:
        return ticker[:3] + result

    return None


def is_setting_config(settings: Literal["local", "production", "test"]) -> bool:
    config = getenv("DJANGO_SETTINGS_MODULE", "config.settings.local").split(".")[-1]
    return settings == config
