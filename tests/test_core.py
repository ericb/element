import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../')  # noqa

from ciri import fields
from ciri.fields import FieldError
from ciri.core import Schema, SchemaOptions
from ciri.registry import SchemaRegistry, schema_registry
from ciri.exception import ValidationError, SerializationError, FieldValidationError

import pytest


def test_empty_serialization():
    schema = Schema()
    schema.serialize({})
    assert schema.errors == {}


def test_empty_validation():
    schema = Schema()
    schema.validate({})
    assert schema.errors == {}


def test_default_value():
    class S(Schema):
        active = fields.Boolean(default=True)
    schema = S()
    assert schema.serialize({}) == {'active': True}


def test_default_callable():
    def make_name(schema, field):
        return 'audrey'

    class S(Schema):
        name = fields.String(default=make_name)
    schema = S()
    assert schema.serialize({}) == {'name': 'audrey'}


def test_required_field():
    class S(Schema):
        name = fields.String(required=True)
    schema = S()
    with pytest.raises(ValidationError):
        schema.serialize({})
    assert schema._raw_errors['name'].message == fields.String().message.required


def test_allow_none_field():
    class S(Schema):
        age = fields.Integer(allow_none=True)
    schema = S()
    assert schema.serialize({'name': 2, 'age': None}) == {'age': None}


def test_missing_field_with_allow_none():
    class S(Schema):
        age = fields.Integer(allow_none=True)
    schema = S()
    assert schema.serialize({'name': 2}) == {'age': None}


def test_halt_on_error():
    class S(Schema):
        name = fields.String(required=True)
        age = fields.Integer(required=True)

    schema = S()
    with pytest.raises(ValidationError):
        schema.validate(halt_on_error=True)
    assert len(schema.errors) == 1


def test_multiple_invalid_fields():
    class S(Schema):
        name = fields.String(required=True)
        age = fields.Integer(required=True)

    errors = {'name': {'message': fields.String().message.invalid},
              'age': {'message': fields.Integer().message.invalid}}

    schema = S()
    with pytest.raises(ValidationError):
        schema.serialize({'name': 33, 'age': '33'})
        assert schema.errors == errors


def test_schema_kwargs():
    class Sub(Schema):
        hello = fields.String(required=True)

    class S(Schema):
        name = fields.String(required=True)
        active = fields.Boolean()
        sub = fields.Schema(Sub)

    schema = S(name='ciri', active=True, sub=Sub(hello='testing'))
    assert schema.serialize() == {'name': 'ciri', 'active': True, 'sub': {'hello': 'testing'}}


def test_subclass_schema():
    class Person(Schema):
        name = fields.String()
        age = fields.Integer()

    class Parent(Person):
        child = fields.Schema(Person)

    child = Person(name='Sarah', age=17)
    father = Parent(name='Jack', age=52, child=child)

    assert father.serialize() == {'name': 'Jack', 'age': 52, 'child': {'name': 'Sarah', 'age': 17}}


def test_subclass_override_schema():
    class Person(Schema):
        name = fields.String(allow_empty=True)
        age = fields.Integer()

    class Parent(Person):
        name = fields.String(allow_empty=False)
        child = fields.Schema(Person)

    child = Person(name='', age=17)
    father = Parent(name='Jack', age=52, child=child)

    assert father.serialize() == {'name': 'Jack', 'age': 52, 'child': {'name': '', 'age': 17}}


def test_double_subclass_schema():
    class Person(Schema):
        name = fields.String()
        age = fields.Integer()

    class Parent(Person):
        child = fields.Schema(Person)

    class Father(Parent):
        sex = fields.String(default='male')

    child = Person(name='Sarah', age=17)
    father = Father(name='Jack', age=52, child=child)

    assert father.serialize() == {'sex': 'male', 'name': 'Jack', 'age': 52, 'child': {'name': 'Sarah', 'age': 17}}


def test_errors_reset():
    class S(Schema):
        name = fields.String(required=True)
    schema = S()
    with pytest.raises(ValidationError):
        schema.serialize({})
    schema.serialize({'name': 'pi'})
    assert not schema.errors


def test_schema_opts_cls():
    opts = SchemaOptions()
    assert opts.allow_none == False


def test_schema_opts_cls_overrides():
    opts = SchemaOptions(allow_none=True)
    assert opts.allow_none == True


def test_schema_opts_allow_none_used():
    opts = SchemaOptions(allow_none=True)
    class S(Schema):
        name = fields.String()
    schema = S()
    schema.config({'options': opts})
    assert schema.serialize({}) == {'name': None}


def test_schema_opts_set_on_definition():
    class S(Schema):
        __schema_options__ = SchemaOptions(allow_none=True)
        name = fields.String()

    schema = S()
    assert schema.serialize({}) == {'name': None}


def test_simple_validator_with_invalid_value():
    def validate_mark(schema, field, value):
        if value == 'mark':
            return value
        raise FieldValidationError(FieldError(field, 'invalid'))

    class S(Schema):
        name = fields.String(post_validate=[validate_mark])
    schema = S()
    with pytest.raises(ValidationError):
        schema.serialize({'name': 'bob'})
    assert schema._raw_errors['name'].message == fields.String().message.invalid

def test_simple_validator_with_valid_value():
    def validate_mark(schema, field, value):
        if value == 'mark':
            return value
        raise FieldValidationError(FieldError(field, 'invalid'))

    class S(Schema):
        name = fields.String(post_validate=[validate_mark])
    schema = S()
    assert schema.serialize({'name': 'mark'}) == {'name': 'mark'}


def test_multiple_validators_with_invalid_value():
    def validate_mark(schema, field, value):
        if value == 'mark':
            return value
        raise FieldValidationError(FieldError(field, 'invalid'))

    def is_integer(schema, field, value):
        if not isinstance(value, int):
            return False
        return True

    class S(Schema):
        name = fields.String(post_validate=[validate_mark, is_integer])
    schema = S()
    with pytest.raises(ValidationError):
        schema.serialize({'name': 'marcus'})
    assert schema._raw_errors['name'].message == fields.String().message.invalid


def test_multiple_validators_with_valid_value():
    def validate_mark(schema, field, value):
        if value == 'mark':
            return True
        return False

    def is_integer(schema, field, value):
        if not isinstance(value, int):
            return True
        return False

    class S(Schema):
        name = fields.String(validators=[validate_mark, is_integer])
    schema = S()
    assert schema.serialize({'name': 'mark'}) == {'name': 'mark'}


def test_field_serialization_name():
    class S(Schema):
        name = fields.String(name='first_name')
    schema = S()
    assert schema.serialize({'name': 'Tester'}) == {'first_name': 'Tester'}


def test_simple_pre_validate():
    def not_fiona(schema, field, value):
        if value == 'fiona':
            raise FieldValidationError(FieldError(self, 'invalid'))
        return value

    class S(Schema):
        first_name = fields.String(pre_validate=[not_fiona])
        last_name = fields.String()

    schema = S()
    assert schema.serialize({'first_name': 'foo bar', 'last_name': 'jenkins'}) == {'first_name': 'foo bar', 'last_name': 'jenkins'}


def test_simple_post_validate():
    def not_fiona(schema, field, value):
        if value == 'fiona':
            raise FieldValidationError(FieldError(self, 'invalid'))
        return value

    class S(Schema):
        first_name = fields.String(post_validate=[not_fiona])
        last_name = fields.String()

    schema = S()
    assert schema.serialize({'first_name': 'foo bar', 'last_name': 'jenkins'}) == {'first_name': 'foo bar', 'last_name': 'jenkins'}


def test_simple_pre_validate_error():
    def not_fiona(schema, field, value):
        if value == 'fiona':
            raise FieldValidationError(FieldError(field, 'invalid'))
        return value

    class S(Schema):
        first_name = fields.String(pre_validate=[not_fiona])
        last_name = fields.String()

    schema = S()
    with pytest.raises(ValidationError):
        schema.serialize({'first_name': 'fiona', 'last_name': 'jenkins'})
    assert schema._raw_errors['first_name'].message == fields.String().message.invalid


def test_simple_pre_serializer():
    def capitilize(schema, field, value):
        return value.title()

    class S(Schema):
        first_name = fields.String(pre_serialize=[capitilize])
        last_name = fields.String()

    schema = S()
    assert schema.serialize({'first_name': 'foo bar', 'last_name': 'jenkins'}) == {'first_name': 'Foo Bar', 'last_name': 'jenkins'}


def test_simple_post_serializer():
    def capitilize(schema, field, value):
        return value.title()

    class S(Schema):
        first_name = fields.String(post_serialize=[capitilize])
        last_name = fields.String()

    schema = S()
    assert schema.serialize({'first_name': 'foo bar', 'last_name': 'jenkins'}) == {'first_name': 'Foo Bar', 'last_name': 'jenkins'}


def test_simple_pre_deserializer():
    def capitilize(schema, field, value):
        return value.title()

    class S(Schema):
        first_name = fields.String(pre_deserialize=[capitilize])
        last_name = fields.String()

    schema = S()
    s = schema.deserialize({'first_name': 'foo bar', 'last_name': 'jenkins'})
    assert s.first_name == 'Foo Bar'


def test_simple_post_deserializer():
    def capitilize(schema, field, value):
        return value.title()

    class S(Schema):
        first_name = fields.String(post_deserialize=[capitilize])
        last_name = fields.String()

    schema = S()
    s = schema.deserialize({'first_name': 'foo bar', 'last_name': 'jenkins'})
    assert s.first_name == 'Foo Bar'


def test_method_pre_validate():
    class S(Schema):
        name = fields.String(pre_validate=['not_bella'])

        def not_bella(self, schema, field, value):
            if value == 'bella':
                raise FieldValidationError(FieldError(field, 'invalid'))
            return value

    schema = S()
    assert schema.serialize({'name': 'sybil'}) == {'name': 'sybil'}


def test_failing_pre_validate():
    class S(Schema):
        name = fields.String(pre_validate=['not_bella'])

        def not_bella(self, schema, field, value):
            if value == 'bella':
                raise FieldValidationError(FieldError(field, 'invalid'))
            return value

    schema = S()
    with pytest.raises(ValidationError):
        schema.serialize({'name': 'bella'})
    assert schema._raw_errors['name'].message == fields.String().message.invalid
