from __future__ import annotations

from typing import Literal, Optional, Union

from msgspec import Struct

from src.strings import (
    get_reference,
    is_valid_name,
    to_camel_case,
    to_python_types,
    validate_field,
)

from .array import BaseArrayItem, get_item_from_dict


class BaseField(Struct):
    type: Union[str, list]
    name: str
    required: bool = False
    """If required is not defined, it is assumed to be false."""
    description: Optional[str] = None

    @property
    def __typehint__(self) -> str:
        raise NotImplementedError

    def _get_required_field_class(self) -> str:
        if not self.required:
            raise ValueError("Field is not required")
        name_is_valid = is_valid_name(self.name)
        if not name_is_valid:
            name = validate_field(self.name)
            return (
                f"    {name}: {self.__typehint__} = pydantic.Field(\n"
                f'        alias="{self.name}"\n'
                f"    )\n"
            )
        return f"    {self.name}: {self.__typehint__}\n"

    def _get_optional_field_class(self) -> str:
        if self.required:
            raise ValueError("Field is required")
        name_is_valid = is_valid_name(self.name)
        if not name_is_valid:
            name = validate_field(self.name)
            return (
                f"    {name}: typing.Optional[{self.__typehint__}] = pydantic.Field(\n"
                f'        default=None, alias="{self.name}"\n'
                f"    )\n"
            )
        return f"    {self.name}: typing.Optional[{self.__typehint__}] = None\n"

    def to_field_class(self):
        if self.required:
            string = self._get_required_field_class()
        else:
            string = self._get_optional_field_class()

        if self.description is not None:
            string += f'    """{self.description}"""\n'
        return string


class ReferenceField(BaseField):
    type: str = "reference"
    """
    This field is missing from original schema for this property,
    but it is required for parsing.
    """
    reference: str
    default: Optional[str] = None

    @property
    def __typehint__(self) -> str:
        reference = get_reference(self.reference)
        return reference

    def _get_default_field_class(self) -> str:
        if self.default is None:
            raise ValueError("Default value is not defined")
        name_is_valid = is_valid_name(self.name)
        # If reference to have default value, then this value is the field of enum
        default_value = f"{self.__typehint__}.{self.default.upper()}"
        if not name_is_valid:
            name = validate_field(self.name)
            return (
                f"    {name}: {self.__typehint__} = pydantic.Field(\n"
                f'        default={default_value}, alias="{self.name}"\n'
                f"    )\n"
            )
        return f"    {self.name}: {self.__typehint__} = {default_value}\n"

    def to_field_class(self):
        if self.default is not None:
            string = self._get_default_field_class()
        elif self.required:
            string = self._get_required_field_class()
        else:
            string = self._get_optional_field_class()

        if self.description is not None:
            string += f'    """{self.description}"""\n'
        return string


class StringField(BaseField):
    type: str
    maxLength: Optional[int] = None
    format: Optional[Literal["uri"]] = None

    @property
    def __typehint__(self) -> str:
        return "str"


class IntegerField(BaseField):
    type: str
    default: Optional[int] = None
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    entity: Optional[Literal["owner"]] = None
    format: Optional[Literal["int64"]] = None

    @property
    def __typehint__(self) -> str:
        return "int"

    def _get_default_field_class(self) -> str:
        if self.default is None:
            raise ValueError("Default value is not defined")
        name_is_valid = is_valid_name(self.name)
        if not name_is_valid:
            name = validate_field(self.name)
            return (
                f"    {name}: {self.__typehint__} = pydantic.Field(\n"
                f'        default={self.default}, alias="{self.name}"\n'
                f"    )\n"
            )
        return f"    {self.name}: {self.__typehint__} = {self.default}\n"

    def to_field_class(self):
        if self.default is not None:
            string = self._get_default_field_class()
        elif self.required:
            string = self._get_required_field_class()
        else:
            string = self._get_optional_field_class()

        if self.description is not None:
            string += f'    """{self.description}"""\n'
        return string


class FloatField(BaseField):
    type: str
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[int] = None

    @property
    def __typehint__(self) -> str:
        return "float"


class BooleanField(BaseField):
    type: str
    default: Optional[bool] = None

    @property
    def __typehint__(self) -> str:
        return "bool"

    def _get_default_field_class(self) -> str:
        if self.default is None:
            raise ValueError("Default value is not defined")
        name_is_valid = is_valid_name(self.name)
        typehint = self.__typehint__
        if not name_is_valid:
            name = validate_field(self.name)
            return (
                f"    {name}: {typehint} = pydantic.Field(\n"
                f'        default={self.default}, alias="{self.name}"\n'
                f"    )\n"
            )
        return f"    {self.name}: {typehint} = {self.default}\n"

    def to_field_class(self):
        if self.default is not None:
            string = self._get_default_field_class()
        elif self.required:
            string = self._get_required_field_class()
        else:
            string = self._get_optional_field_class()

        if self.description is not None:
            string += f'    """{self.description}"""\n'
        return string


class DictField(BaseField):
    type: str

    @property
    def __typehint__(self) -> str:
        return "dict"


class ArrayField(BaseField):
    type: str
    items: BaseArrayItem

    @property
    def __typehint__(self) -> str:
        return f"list[{self.items.__typehint__}]"


class UnionField(BaseField):
    type: list[str]

    @property
    def __typehint__(self) -> str:
        python_types = to_python_types(self.type)
        types = ", ".join(python_types)
        return f"typing.Union[{types}]"


class OneOfField(BaseField):
    type: str = "oneOf"
    """
    This field is missing from original schema for this property,
    but it is required for parsing.
    """
    oneOf: list[BaseField]

    @property
    def __typehint__(self) -> str:
        typehints = [field.__typehint__ for field in self.oneOf]
        types = ", ".join(typehints)
        return f"typing.Union[{types}]"


class StringEnumField(StringField):
    __typehint__: str

    type: str
    enum: list[str]
    enumNames: Optional[list[str]] = None


class IntegerEnumField(IntegerField):
    __typehint__: str

    type: str
    enum: list[int]
    enumNames: list[str]


def get_property_from_dict(object_name: str, item: dict, property_name: str) -> BaseField:
    if item.get("enum") is not None:
        return _get_enum_property(name=property_name, object_name=object_name, item=item)
    if item.get("$ref") is not None:
        reference = item.pop("$ref")
        return ReferenceField(name=property_name, reference=reference, **item)
    if item.get("oneOf") is not None:
        one_of = item.pop("oneOf")
        # Fields of oneOf are not required a name, but the function requires it.
        # So we add name of oneOf field
        one_of = [get_property_from_dict(object_name, item, property_name) for item in one_of]
        return OneOfField(name=property_name, oneOf=one_of, **item)

    property_type = item.get("type")
    if isinstance(property_type, list):
        return UnionField(name=property_name, **item)
    if property_type == "array":
        copy_item = item.copy()
        copy_item["items"] = get_item_from_dict(copy_item["items"])
        return ArrayField(name=property_name, **copy_item)
    if property_type == "object":
        return DictField(name=property_name, **item)
    if property_type == "integer":
        return IntegerField(name=property_name, **item)
    if property_type == "number":
        return FloatField(name=property_name, **item)
    if property_type == "boolean":
        return BooleanField(name=property_name, **item)
    if property_type == "string":
        # Some properties with the type "string" may have the field "minimum".
        # I do not know what it is for, so it is simply deleted
        item.pop("minimum", None)
        return StringField(name=property_name, **item)
    raise ValueError(f"Unknown property type: {property_type}")


def _get_enum_property(object_name: str, item: dict, name: str) -> BaseField:
    property_type = item["type"]
    typehint = to_camel_case(f"{object_name}_{name}")
    if property_type == "string":
        return StringEnumField(__typehint__=typehint, name=name, **item)
    else:
        return IntegerEnumField(__typehint__=typehint, name=name, **item)
