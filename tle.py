# -*- coding: utf-8  -*-
from __future__ import unicode_literals, division

import logging
from bisect import bisect_right
from datetime import datetime, timedelta, date
from collections import OrderedDict

import requests
from sgp4.earth_gravity import wgs84
from sgp4.io import twoline2rv

import settings
from utils import clean_line

log = logging.getLogger(__name__)

NASA_TLE_URL = getattr(settings, 'nasa_tle_url')


class TLENotFound(ValueError):
    pass


class TLE(object):
    _iss_cache = {}

    def __init__(self, nasa_tle_url=None):
        if not nasa_tle_url:
            self.nasa_tle_url = NASA_TLE_URL
        self.tle_db = self.get_latest_tle_db()

    def get_latest_tle_db(self):
        tle_database = {}
        while not tle_database:
            response = requests.get(self.nasa_tle_url)
            try:
                lines = response.text.splitlines()
                for i, line in enumerate(lines):
                    if line.strip() == "ISS":
                        tle_line_1 = lines[i + 1].strip()
                        tle_line_2 = lines[i + 2].strip()
                        tle_database[self.tle_date(tle_line_1)] = (tle_line_1, tle_line_2)
            finally:
                response.close()

        return OrderedDict(item for item in sorted(tle_database.items()))

    def get_nearest_tle(self, dt=None, ignore=True):
        return self.tle_db[self.get_nearest_tle_dt(dt, ignore)]

    def get_nearest_tle_dt(self, dt=None, ignore=True):
        tle_dts = tuple(self.tle_db.keys())

        if not isinstance(dt, (datetime, date)):
            return tle_dts[0]

        try:
            tle_dt = find_le(tle_dts, dt)
        except ValueError:
            if ignore:
                return tle_dts[0]

            raise TLENotFound('Not found TLE for %r, the oldest TLE in db for %r' % (dt, tle_dts[0]))
        else:
            return tle_dt

    @staticmethod
    def tle_date(tle_line_1):
        date = clean_line(tle_line_1).split(' ')[3]
        year = 2000 + int(date[0:2])
        days_since_year_start = float(date[2:])
        return datetime(year, 1, 1, 0, 0, 0, 0) + timedelta(days=days_since_year_start)

    def get_iss(self, tle=None, dt=None):
        if tle is None and isinstance(dt, (datetime, date)):
            tle = self.get_nearest_tle(dt)

        if tle not in self._iss_cache:
            self._iss_cache[tle] = twoline2rv(tle[0], tle[1], wgs84)

        return self._iss_cache[tle]

    def get_iss_position(self, tle=None, dt=None):
        iss = self.get_iss(tle, dt)
        return iss.propagate(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def find_le(a, x):
    """
    Find rightmost value less than or equal to x
    """
    i = bisect_right(a, x)
    if i:
        return a[i - 1]
    raise ValueError


if __name__ == '__main__':
    tle = TLE()
    print(tle.get_nearest_tle())