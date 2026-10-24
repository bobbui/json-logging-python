"""Error paths of the helpers in json_logging.util (issue #137)."""
import logging

import pytest

from json_logging import util


def test_update_formatter_for_loggers_rejects_non_logger():
    with pytest.raises(RuntimeError):
        util.update_formatter_for_loggers(["not-a-logger"], logging.Formatter)


def test_update_formatter_for_loggers_replaces_other_formatters_only():
    class Wanted(logging.Formatter):
        pass

    logger = logging.Logger("util-validation-test")
    replaced = logging.StreamHandler()
    kept = logging.StreamHandler()
    already_wanted = Wanted()
    kept.setFormatter(already_wanted)
    logger.addHandler(replaced)
    logger.addHandler(kept)

    util.update_formatter_for_loggers([logger], Wanted)

    assert isinstance(replaced.formatter, Wanted)
    assert kept.formatter is already_wanted


def test_validate_subclass_accepts_subclass():
    assert util.validate_subclass(logging.StreamHandler, logging.Handler) is True


def test_validate_subclass_rejects_non_subclass():
    with pytest.raises(RuntimeError, match="is not a subclass of"):
        util.validate_subclass(dict, logging.Handler)


@pytest.mark.parametrize("value, default, expected", [("7", 1, 7), ("x", 1, 1), (None, 3, 3), (4, 0, 4)])
def test_parse_int_falls_back_to_default(value, default, expected):
    assert util.parse_int(value, default) == expected
