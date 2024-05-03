from datetime import datetime
from tzlocal import get_localzone
import datetime
import pytz


def get_iat():
    """
    
    :return: 
    """
    # Get the local timezone
    local_tz = get_localzone()
    print(f'local timezone: {local_tz}')

    # Get the current time in the local timezone
    current_time = datetime.datetime.now(local_tz)
    print(f'Current time: {current_time}')

    # Round the current time to zero seconds
    current_time_rounded = current_time.replace(second=0, microsecond=0)
    print(f'Current time rounded: {current_time_rounded}')

    # Convert to seconds since Unix epoch
    unix_epoch = datetime.datetime(1970, 1, 1, tzinfo=local_tz)
    seconds_since_epoch = (current_time_rounded - unix_epoch).total_seconds()

    print(f'seconds since Epoch: {seconds_since_epoch}')

    return seconds_since_epoch