from setuptools import setup, find_packages

setup(
    name="json-logging",
    version='0.0.1',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*', 'example', 'dist', 'build']),
    license='Apache License 2.0',
    description="JSON Python Logging",
    long_description=open('README.rst').read(),
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
