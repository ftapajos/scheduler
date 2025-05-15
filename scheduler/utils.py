#!/usr/bin/env python

import json
import subprocess
from datetime import UTC, datetime, timezone

tagless = "TAGLESSTASK"
force_avoided_task_for_seconds = 25 * 60
force_switch_after_seconds = 25 * 60


def extract_tags_from(task):
    tags = []

    # Extract attributes for use as tags.
    if task["project"] is not None:
        tags.append(task["project"])

    if task["tags"] is not None:
        if type(task["tags"]) is str:
            # Usage of tasklib (e.g. in taskpirate) converts the tag list into
            # a string
            # If this is the case, convert it back into a list first
            # See https://github.com/tbabej/taskpirate/issues/11
            tags.extend(task["tags"].split(","))
        else:
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


def calculate_tag_sum(tags, taskDictionary, dictionary):
    tagSum = {}
    tids = taskDictionary.keys()
    for tag in tags:
        tagSum[tag] = sum(
            [
                dictionary[tid]
                for tid in tids
                if tag in extract_tags_from(taskDictionary[tid])
            ]
        )
    return tagSum


def get_time_tw(event):
    start = datetime.strptime(event["start"], "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    )
    if "end" in event:
        end = datetime.strptime(event["end"], "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    else:
        end = datetime.now(UTC)
    return (end - start).total_seconds()


def get_total_time_tags(tags):
    day = json.loads(subprocess.check_output(["timew", "export", ":day"]))

    total_time = 0
    for event in day:
        if set(tags).intersection(set(event["tags"])):
            total_time += get_time_tw(event)
    return total_time


def last_activity_time(tags):
    day = json.loads(subprocess.check_output(["timew", "export", ":day"]))

    last_activity = [event for event in day if event["id"] == 1][0]
    if set(tags) == set(last_activity["tags"]):
        return get_time_tw(last_activity)
    else:
        return 0


def print_task(task):
    day = json.loads(subprocess.check_output(["timew", "export"]))

    if task["start"] is not None:
        tw_ids = [
            d["id"] for d in day if set(d["tags"]) == set(tags_and_description(task))
        ]

        if len(tw_ids) > 0:
            tw_id = min(tw_ids)
            print(f"Timewarrior id: @{tw_id}")

    subprocess.run(["task", "ls", str(task["id"])])


def get_duration_on(tags):
    if tagless in tags:
        tags.remove(tagless)

    if len(tags) <= 0:
        return 0

    day = json.loads(subprocess.check_output(["timew", "export", ":day"]))

    total_time = 0
    tags = set(tags)
    for event in day:
        if tags.intersection(set(event["tags"])) == tags:
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
