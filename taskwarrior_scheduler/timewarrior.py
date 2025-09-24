import json
import subprocess
from datetime import datetime, timezone


def timew_export(timespan=None):
    array = ["timew", "export"]
    if timespan is not None:
        array.append(timespan)

    return json.loads(subprocess.check_output(array))
