"""Constants shared by multiple tests"""

import sys

_msg_attrs = [
    "written_at",
    "written_ts",
    "msg",
    "type",
    "logger",
    "thread",
    "level",
    "module",
    "line_no",
    "correlation_id",
]

if sys.version_info.major == 3 and sys.version_info.minor >= 12:
    _msg_attrs.append("taskName")

STANDARD_MSG_ATTRIBUTES = set(_msg_attrs)
