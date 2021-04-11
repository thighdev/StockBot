from datetime import datetime
from pytz import timezone
from typing import List


def epoch_to_datetime_tz(epoch_list: List[int], tz: str = "UTC"):
    tz = timezone(tz)
    return [datetime.fromtimestamp(i, tz) for i in epoch_list]
