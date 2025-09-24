import json
import subprocess
from datetime import UTC, datetime, timezone
from typing import Dict, List

from tasklib import Task

from .timewarrior import timew_export

tagless = "TAGLESSTASK"
force_avoided_task_for_seconds = 25 * 60
force_switch_after_seconds = 25 * 60


def extract_tags_from(task):
    tags = []

    # Extract attributes for use as tags.
    if task["project"] is not None:
        tags.append(task["project"])

    if task["tags"] is not None:
        tags.extend(task["tags"])

    if len(tags) == 0:
        tags.append(tagless)
    return tags


def tags_and_description(task):
    tags = extract_tags_from(task)
    if len(tags) == 1 and tags[0] == tagless:
        return [task["description"]]
    else:
        return [task["description"]] + tags


def calculate_tag_sum(
    tags: List[str], taskDictionary: Dict[str, Task], virtualTimes: Dict[str, float]
) -> Dict[str, float]:
    tagSum = {}
    tids = taskDictionary.keys()
    for tag in tags:
        tagSum[tag] = sum(
            [
                virtualTimes[tid]
                for tid in tids
                if tag in extract_tags_from(taskDictionary[tid])
            ]
        )
    return tagSum


def get_time_tw(tw_event):
    start = datetime.strptime(tw_event["start"], "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    )
    if "end" in tw_event:
        end = datetime.strptime(tw_event["end"], "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    else:
        end = datetime.now(UTC)
    return (end - start).total_seconds()


def get_total_time_tags(tw_tags, time_span=":day", day=None):
    if day is None:
        day = timew_export(time_span)

    total_time = 0
    for event in day:
        if set(tw_tags).intersection(set(event["tags"])):
            total_time += get_time_tw(event)
    return total_time


def last_activity_time(tw_tags, day=None):
    if day is None:
        day = timew_export(":day")

    last_activity = [event for event in day if event["id"] == 1][0]
    if set(tw_tags) == set(last_activity["tags"]):
        return get_time_tw(last_activity)
    else:
        return 0


def print_task(task):
    day = timew_export()

    if task["start"] is not None:
        tw_ids = [
            d["id"] for d in day if set(d["tags"]) == set(tags_and_description(task))
        ]

        if len(tw_ids) > 0:
            tw_id = min(tw_ids)
            print(f"Timewarrior id: @{tw_id}")

    subprocess.run(["task", "ls", str(task["id"])])


def get_duration_on(tw_tags, time_span=":day", day=None):
    if tagless in tw_tags:
        tw_tags.remove(tagless)

    if len(tw_tags) <= 0:
        return 0

    if day is None:
        day = timew_export(time_span)

    total_time = 0
    tw_tags = set(tw_tags)
    for event in day:
        if tw_tags.intersection(set(event["tags"])) == tw_tags:
            total_time += get_time_tw(event)
    return total_time


def get_shares(executedTime, virtualTime, totalExecutedTime, totalVirtualTime):
    assert len(executedTime) == len(virtualTime)
    assert executedTime.keys() == virtualTime.keys()

    keys = executedTime.keys()
    # Calculate executed shares
    executedShares = {
        key: (executedTime[key] / totalExecutedTime if totalExecutedTime > 0 else 0)
        for key in keys
    }

    # Calculate shares
    shares = {key: virtualTime[key] / totalVirtualTime for key in keys}
    return (shares, executedShares)
