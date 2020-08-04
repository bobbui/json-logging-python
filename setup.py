import io
import sys

from setuptools import setup, find_packages

version_info_major = sys.version_info[0]
if version_info_major == 3:
    long_description = open('README.rst', encoding="utf8").read()
else:
    io_open = io.open('README.rst', encoding="utf8")
    long_description = io_open.read()

setup(
    name="json-logging",
    version='1.2.5',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*', 'example', 'dist', 'build']),
    license='Apache License 2.0',
    description="JSON Python Logging",
    long_description=long_description,
    author="Bui Nguyen Thang (Bob)",
    author_email="bob.bui@outlook.com",
    keywords=["json", "elastic", "python", "python3", "python2", "logging", "logging-library", "json", "elasticsearch",
              "elk", "elk-stack", "logstash", "kibana"],
    platforms='any',
    url="https://github.com/thangbn/json-logging",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: System :: Logging',
        'Framework :: Flask',
    ]
)
