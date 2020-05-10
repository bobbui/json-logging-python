# Command for development 
create file **.pypirc**

```
[distutils]
index-servers =
  pypi
  pypitest

[pypi]
repository: https://upload.pypi.org/legacy/
username:
password:

[pypitest]
repository: https://test.pypi.org/legacy/
username=
password=
```
build
```bash
python setup.py bdist_wheel --universal
python setup.py sdist
```

pypitest
```
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
pip3 install json_logging --index-url https://test.pypi.org/simple/
```
pypi
```
pip3 install json_logging
twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

```
