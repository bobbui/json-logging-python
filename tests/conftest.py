"""Global fixtures and settings for the pytest test suite"""
import sys
import os

# Add test helper modules to search path with out making "tests" a Python package
sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))
