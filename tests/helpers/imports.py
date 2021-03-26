"""Helper functions related to module imports"""
import sys


def undo_imports_from_package(package: str):
    """Removes all imported modules from the given package from sys.modules"""
    for k in sorted(sys.modules.keys(), key=lambda s: len(s), reverse=True):
        if k == package or k.startswith(package + '.'):
            del sys.modules[k]
