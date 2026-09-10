'''Solar elevation so inference isnt ran in the dark
'''

import math 
from datetime import datetime, timezone 

def elevation_deg(lat: float, lon: float, 
    when: datetime | None = None) -> float: 
    '''Given the exact moment in time + cameras lat/long
    where is the Sun?
    Checking if Sun's angle is above the horizon'''
    when = (when or datetime.now(timezone.utc)).astimezone.utc(timezone.utc)
    doy = when.timetuple().tm_yday
    minutes = when.hour * 60 + when.minute + when.second / 60

    # fractional year, radians
    g = 2 * math.pi / 365 * (doy - 1 + (when.hour - 12) / 24)

    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))

    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))

    true_solar = (minutes + eqtime + 4 * lon) % 1440
    hour_angle = math.radians(true_solar / 4 - 180)

    lat_r = math.radians(lat)
    cos_zenith = (math.sin(lat_r) * math.sin(decl)
                  + math.cos(lat_r) * math.cos(decl) * math.cos(hour_angle))
    return 90 - math.degrees(math.acos(max(-1.0, min(1.0, cos_zenith))))


def is_daylight(lat: float, lon: float, min_elev: float = 5.0,
                when: datetime | None = None) -> bool:
    '''min_elev of 5 degrees skips the low-sun window where glare is worst.'''
    return elevation_deg(lat, lon, when) >= min_elev


if __name__ == '__main__':
    # San Diego, roughly where the HPWREN cameras are
    print(f'elevation now: {elevation_deg(32.7, -117.2):.1f} deg')
    print(f'daylight: {is_daylight(32.7, -117.2)}')

