# coding=utf-8
import time
import timeit
from datetime import datetime

utcnow = datetime.utcnow()

numbers = 1000000
# timeit_timeit = timeit.timeit(lambda: '%04d-%02d-%02dT%02d:%02d:%02dZ' % (
#     utcnow.year, utcnow.month, utcnow.day, utcnow.hour, utcnow.minute, utcnow.second), number=numbers)
# print(timeit_timeit)
#
# timeit_timeit1 = timeit.timeit(lambda: '%04d-%02d-%02dT%02d:%02d:%02d.%03dZ' % (
#     utcnow.year, utcnow.month, utcnow.day, utcnow.hour, utcnow.minute, utcnow.second, int(utcnow.microsecond / 1000)),
#                                number=numbers)
# print(timeit_timeit1)
#
# timeit_timeit2 = timeit.timeit(lambda: utcnow.strftime('%Y-%m-%dT%H:%M:%S.%fZ'), number=numbers)
# print(timeit_timeit2)
#
# timeit_timeit3 = timeit.timeit(
#     lambda: '{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z'.format(utcnow.year, utcnow.month, utcnow.day,
#                                                                 utcnow.hour, utcnow.minute, utcnow.second),
#     number=numbers)
# print(timeit_timeit3)

_epoch = datetime(1970, 1, 1)
# python 3
# print(utcnow.timestamp())
# timeit1 = timeit.timeit(lambda: utcnow.timestamp(), number=numbers)
# print(timeit1)

# python 2
print(time.mktime(utcnow.timetuple()))
timeit1 = timeit.timeit(lambda: time.mktime(utcnow.timetuple()), number=numbers)
print(timeit1)

print((utcnow - _epoch).total_seconds())
timeit2 = timeit.timeit(lambda: int((utcnow - _epoch).total_seconds()) * 1000000000 + utcnow.microsecond * 1000,
                        number=numbers)
print(timeit2)

timeit3 = timeit.timeit(lambda: (int((utcnow - _epoch).total_seconds()) * 1000000 + utcnow.microsecond) * 1000,
                        number=numbers)
print(timeit3)
# 1456820553816849408
# 1496635859
# 1496637019171670000
