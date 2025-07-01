"""Global fixtures and settings for the pytest test suite"""
import sys
import os
from helpers import constants

# Add test helper modules to search path with out making "tests" a Python package
sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))

if sys.version_info.major > 3 or (sys.version_info.major == 3 and sys.version_info.minor >= 12):
    constants.STANDARD_MSG_ATTRIBUTES.add('taskName')
