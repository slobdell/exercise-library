import datetime
import pytz
import time
from pytz.exceptions import AmbiguousTimeError


def datetime_to_timestamp_ms(dt):
    if dt is None:
        return None
    return int(time.mktime(dt.timetuple()) * 1000 + (dt.microsecond / 1000))


def timestamp_ms_to_datetime(timestamp_ms):
    if timestamp_ms is None:
        return None
    microsecond = (timestamp_ms % 1000) * 1000
    return datetime.datetime.utcfromtimestamp(timestamp_ms / 1000).replace(microsecond=microsecond)


def date_to_datetime(d):
    return datetime.datetime.fromordinal(d.toordinal())


def get_timezone_from_utc_offset_minutes(offset_minutes):
    for possible_timezone_string in pytz.all_timezones:
        possible_timezone = pytz.timezone(possible_timezone_string)
        try:
            if offset_minutes == int(possible_timezone.utcoffset(datetime.datetime.utcnow()).total_seconds() / 60):
                return possible_timezone
        except AmbiguousTimeError:
            # During DST transitions this can die... if it does, just skip that TZ
            pass
    return pytz.timezone("UTC")
