import json
from typing import Any
from typing import ClassVar
from typing import Literal

from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.plumbing import build_array_type
from pydantic import BaseModel as _BaseModel


class BaseModel(_BaseModel, OpenApiSerializerFieldExtension):
    target_class: ClassVar[str]
    is_list: ClassVar[bool | None] = None

    @classmethod
    def map_serializer_field(cls, auto_schema, direction):
        if cls.is_list:
            # Return schema for an array of objects
            return build_array_type(cls.model_json_schema())
        # Return schema for a single object
        return cls.model_json_schema()

    @classmethod
    def replace_ref(
        cls,
        defs: dict,
        schema: dict | list,
    ) -> dict[str, Any] | list | Any:
        """Function replace all ref with thier object

        Args:
            defs (dict): _description_
            schema (dict | list): _description_

        Returns:
            dict[str,Any]|list|Any: _description_
        """
        if type(schema) is list:
            return [cls.replace_ref(defs, value) for value in schema]
        if type(schema) is dict:
            if schema.get("$ref"):
                return defs.get(schema.get("$ref"), schema)
            return {
                key: (
                    cls.replace_ref(defs, value)
                    if type(value) in [list, dict]
                    else value
                )
                for key, value in schema.items()
            }
        return schema

    @classmethod
    def get_defs(cls, data: dict) -> dict[str, Any]:
        res = {f"#/$defs/{key}": value for key, value in data.get("$defs", {}).items()}
        return cls.replace_ref(res, res)

    @classmethod
    def model_json_schema(cls, *args, **kwargs) -> dict[str, Any]:
        """Generate jsonschema of the model.

        Returns:
            dict[str,Any]: _description_
        """
        data = super().model_json_schema(*args, **kwargs)
        defs: dict = cls.get_defs(data)
        res = cls.replace_ref(defs=defs, schema=data)
        return res

    @classmethod
    def model_json_schema_no_defs(cls, *args, **kwargs) -> dict[str, Any]:
        """Generate jsonschema of the model.

        Returns:
            dict[str,Any]:
        """
        data = super().model_json_schema(*args, **kwargs)
        defs: dict = cls.get_defs(data)
        res = cls.replace_ref(defs=defs, schema=data)
        res.pop("$defs", None)
        return res

    def dict_plain(self) -> dict:
        return json.loads(self.model_dump_json())


class BaseModelNoDefs(BaseModel):
    @classmethod
    def model_json_schema(cls, *args, **kwargs) -> dict[str, Any]:
        """Generate jsonschema of the model.

        Returns:
            dict[str,Any]: _description_
        """
        data = super().model_json_schema(*args, **kwargs)
        defs: dict = cls.get_defs(data)
        res = cls.replace_ref(defs=defs, schema=data)
        res.pop("$defs", None)
        return res

    def dict_plain(self) -> dict:
        return json.loads(self.model_dump_json())


class BaseTypeModel(BaseModelNoDefs):
    type: Literal["--none--"] = "--none--"

    @classmethod
    @property
    def object_type(cls) -> str:
        """return the type

        Returns:
            str: _description_
        """
        try:
            return cls.model_fields["type"].default
        except AttributeError:
            return "unknown"
