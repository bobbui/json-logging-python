"""Optional fields and value handling in the JSON formatters (issue #137)."""
import json
import logging

import pytest

import json_logging
from json_logging.formatters import BaseJSONFormatter, JSONLogFormatter


@pytest.fixture
def component_settings():
    """Restore the module level component settings, which are read when a formatter is constructed."""
    saved = (json_logging.COMPONENT_ID, json_logging.COMPONENT_NAME, json_logging.COMPONENT_INSTANCE_INDEX)
    # base_object_common is a class level dict that formatter construction writes into, so restore it as well
    saved_common = dict(BaseJSONFormatter.base_object_common)
    for key in ("component_id", "component_name", "component_instance_idx"):
        BaseJSONFormatter.base_object_common.pop(key, None)
    yield
    BaseJSONFormatter.base_object_common.clear()
    BaseJSONFormatter.base_object_common.update(saved_common)
    json_logging.COMPONENT_ID, json_logging.COMPONENT_NAME, json_logging.COMPONENT_INSTANCE_INDEX = saved


def _format(**extra):
    record = logging.LogRecord("formatter-test", logging.INFO, __file__, 1, "hello", None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JSONLogFormatter().format(record))


def test_component_settings_are_added_when_set(component_settings):
    json_logging.COMPONENT_ID = "id-1"
    json_logging.COMPONENT_NAME = "name-1"
    json_logging.COMPONENT_INSTANCE_INDEX = 2

    output = _format()

    assert output["component_id"] == "id-1"
    assert output["component_name"] == "name-1"
    assert output["component_instance_idx"] == 2


def test_component_settings_are_omitted_by_default(component_settings):
    output = _format()

    assert "component_id" not in output
    assert "component_name" not in output
    assert "component_instance_idx" not in output


def test_non_serialisable_extra_value_falls_back_to_repr():
    class Unserialisable:
        def __repr__(self):
            return "<unserialisable>"

    output = _format(thing=Unserialisable())

    assert output["thing"] == "<unserialisable>"


def test_props_dict_is_merged_into_the_root_of_the_log():
    output = _format(props={"user": "alice", "attempt": 3})

    assert output["user"] == "alice"
    assert output["attempt"] == 3


def test_props_that_is_not_a_dict_is_not_merged():
    output = _format(props="not-a-dict")

    assert "not-a-dict" not in output.values()
