from math import exp
from typing import Any, Dict, List, Optional, Tuple

import typer
from tasklib import TaskWarrior
from tasklib.backends import TaskWarriorException

from .timewarrior import timew_export
from .utils import (
    calculate_tag_sum,
    extract_tags_from,
    get_duration_on,
    get_shares,
    get_total_time_tags,
    last_activity_time,
    tags_and_description,
)

tagless = "TAGLESSTASK"
force_avoided_task_for_seconds = 25 * 60
force_switch_after_seconds = 25 * 60


def get_tasks(filters, tw=TaskWarrior()):
    # Apply custom filters and restrict to unblocked and pending tasks
    if filters is not None:
        filterString = " ".join(filters)
    else:
        filterString = ""
    if len(filterString) > 1:
        filterString = f"( {filterString} ) and "
    else:
        filterString = ""
    filterString += "+UNBLOCKED and +PENDING"

    _tasksTags = []
    tasks = {}
    try:
        # Gets context's filter and apply it manually
        context = tw.execute_command(["_get", "rc.context"])[0]

        if context:
            context_read = tw.execute_command(
                ["_get", "rc.context." + context + ".read"]
            )[0]
            filterString += f" and ( {context_read} )"

        # If there are two identical tasks, get only the one with the
        # highest urgency
        _tasksTags = []
        tasks = {}
        for task in sorted(
            tw.tasks.filter(filterString), key=lambda d: d["urgency"], reverse=True
        ):
            _tags = set(tags_and_description(task))
            if _tags not in _tasksTags:
                _tasksTags.append(_tags)
                tasks[task["id"]] = task
    except TaskWarriorException as e:
        print("Taskwarrior error:", e)

    return (
        tasks,
        filterString,
    )


def get_times(tasks, tags, day: Optional[List[Dict[str, Any]]] = None):
    if len(tasks) <= 0:
        return None

    if day is None:
        day = timew_export(":day")

    # Calculate virtual times
    virtualTime = {}
    for k in tasks.keys():
        virtualTime[k] = exp(tasks[k]["urgency"])

    # Calculate executed times
    executedTime = {
        tid: get_duration_on(tags_and_description(tasks[tid]), day=day)
        for tid in virtualTime.keys()
    }

    executedTimeTag = {tag: get_duration_on([tag], day=day) for tag in tags}
    totalTimeTags = get_total_time_tags(executedTimeTag.keys(), day=day)
    totalExecutedTime = sum(executedTime.values())

    if totalTimeTags == 0 and totalExecutedTime == 0:
        return None

    totalVirtualTime = sum(virtualTime.values())

    # Calculate virtual times for each tag
    virtualTimeTag = calculate_tag_sum(tags, tasks, virtualTime)
    sharesTag, executedSharesTag = get_shares(
        executedTimeTag, virtualTimeTag, totalTimeTags, totalVirtualTime
    )

    return (virtualTime, executedTime), (sharesTag, executedSharesTag)


def find_next_task(
    tDict: Dict[str, Any], day: List[Dict[str, Any]]
) -> Tuple[Any, Optional[float], Optional[float]]:
    tags = set([tag for task in tDict.values() for tag in extract_tags_from(task)])
    times = get_times(tDict, tags, day=day)

    if times is None:
        print("No sampled time")
        print("Start by the most urgent task")
        most_urgent = sorted(tDict.values(), key=lambda d: d["urgency"], reverse=True)[
            0
        ]
        return (most_urgent, None, None)

    only_executed_task, difference, shares, executed_shares = get_difference(
        times, tDict
    )

    if only_executed_task is not None:
        _tags = tags_and_description(only_executed_task)
        _last_activity_time = last_activity_time(_tags, day=day)

        if _last_activity_time < force_avoided_task_for_seconds:
            print("This is the only pending task started today")
            print(
                "Please keep doing it for",
                f"{int((force_avoided_task_for_seconds - _last_activity_time) / 60)}min",
                "uninterruptly",
            )
            return (only_executed_task, None, None)

    tid = max(difference, key=difference.get)

    _last_activity_time = last_activity_time(tags_and_description(tDict[tid]), day=day)
    if _last_activity_time > force_switch_after_seconds and len(tDict) > 1:
        print("skipping", tDict[tid])
        difference.pop(tid)
        tid = max(difference, key=difference.get)

    return (tDict[tid], shares[tid], executed_shares[tid])


def get_tag_correction(sharesTag, executedSharesTag):
    tag_correction = {}
    for tag in sharesTag.keys():
        if executedSharesTag[tag] > sharesTag[tag]:
            tag_correction[tag] = sharesTag[tag] / executedSharesTag[tag]
        else:
            tag_correction[tag] = 1
    return tag_correction


def get_difference(times, tasks):
    # Get all tags
    if times is None:
        (virtualTime, executedTime), (sharesTag, executedSharesTag) = ({}, {}), ({}, {})
    else:
        (virtualTime, executedTime), (sharesTag, executedSharesTag) = times

    tag_correction = get_tag_correction(sharesTag, executedSharesTag)

    # Calculate executed time for each tag
    tids = tasks.keys()
    for tid in tids:
        for tag in extract_tags_from(tasks[tid]):
            virtualTime[tid] *= tag_correction[tag]

    totalVirtualTime = sum(virtualTime.values())
    totalExecutedTime = sum(executedTime.values())

    # Calculate shares
    shares, executedShares = get_shares(
        executedTime, virtualTime, totalExecutedTime, totalVirtualTime
    )

    differences = {key: shares[key] - executedShares[key] for key in shares.keys()}

    if 1 in executedShares.values():
        tid = list(executedShares.keys())[list(executedShares.values()).index(1)]
        if (
            sorted(tasks.values(), key=lambda d: d["urgency"], reverse=True)[0]["id"]
            == tid
        ):
            return tasks[tid], differences, shares, executedShares

    return None, differences, shares, executedShares
