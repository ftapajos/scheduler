#!/usr/bin/env python

from math import exp

import typer
from tasklib import TaskWarrior

from .utils import (
    calculate_tag_sum,
    get_duration_on,
    get_shares,
    get_total_time_tags,
    tags_and_description,
)

app = typer.Typer()

tagless = "TAGLESSTASK"
force_avoided_task_for_seconds = 25 * 60
force_switch_after_seconds = 25 * 60


def get_tasks(filters):
    # Apply custom filters and restrict to unblocked and pending tasks
    tw = TaskWarrior()
    if filters is not None:
        filterString = " ".join(filters)
    else:
        filterString = ""
    if len(filterString) > 1:
        filterString = "( " + filterString + " ) "
    else:
        filterString = ""
    filterString += "+UNBLOCKED and +PENDING"

    # Gets context's filter and apply it manually
    context = tw.execute_command(["_get", "rc.context"])[0]

    if context:
        context_read = tw.execute_command(["_get", "rc.context." + context + ".read"])[
            0
        ]
        filterString += " and ( " + context_read + ")"

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

    return (
        tasks,
        filterString,
    )


def get_times(tasks, tags):
    if len(tasks) <= 0:
        return None

    # Calculate virtual times
    virtualTime = {}
    for k in tasks.keys():
        virtualTime[k] = exp(tasks[k]["urgency"])

    # Calculate executed times
    executedTime = {
        tid: get_duration_on(tags_and_description(tasks[tid]))
        for tid in virtualTime.keys()
    }

    executedTimeTag = {tag: get_duration_on([tag]) for tag in tags}

    totalTimeTags = get_total_time_tags(executedTimeTag.keys())
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


def get_tag_correction(sharesTag, executedSharesTag):
    tag_correction = {}
    for tag in sharesTag.keys():
        if executedSharesTag[tag] > sharesTag[tag]:
            tag_correction[tag] = sharesTag[tag] / executedSharesTag[tag]
        else:
            tag_correction[tag] = 1
    return tag_correction
