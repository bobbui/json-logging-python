"""Constants shared by multiple tests"""
import sys

STANDARD_MSG_ATTRIBUTES = {
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
}

# Python 3.12+ fills in taskName for records logged inside an asyncio task; it is left out when it is None
ASYNC_TASK_MSG_ATTRIBUTES = STANDARD_MSG_ATTRIBUTES | ({"taskName"} if sys.version_info >= (3, 12) else set())
