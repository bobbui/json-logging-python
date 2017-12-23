from setuptools import setup

setup(
    name="json-logging",
    version='0.0.1',
    packages=['json_logging'],
    description="JSON Python Logging",
    long_description=open('README.md').read(),
    author="Bui Nguyen Thang (Bob)",
    author_email="thang.bn@live.com",
    keywords=["json", "python", "logging", "request instrumentation"],
    platforms='any',
    url="https://github.com/thangbn/json-logging",
    classifiers=[
        'Development Status :: 3 - Alpha',
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
