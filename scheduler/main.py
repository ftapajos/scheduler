#!/usr/bin/env python

import subprocess
from datetime import datetime, timedelta, timezone
from math import exp
from sys import argv
from typing import List, Optional

import typer
from tasklib import TaskWarrior
from typing_extensions import Annotated

from .utils import (
    calculate_tag_sum,
    extract_tags_from,
    get_duration_on,
    get_shares,
    get_total_time_tags,
    last_activity_time,
    print_task,
    tags_and_description,
)

app = typer.Typer()

tagless = "TAGLESSTASK"
force_avoided_task_for_seconds = 25 * 60
force_switch_after_seconds = 25 * 60


@app.callback(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    invoke_without_command=True,
)
def next(
    ctx: typer.Context, filters: Annotated[Optional[List[str]], typer.Argument()] = None
):
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

    tasks = tw.tasks.filter(filterString)

    # Check if there any tags
    if len(tasks) <= 0:
        print("Taskless")
        subprocess.run(["task", "ls", filterString])
        quit()

    # Get all tags
    tags = set([tag for task in tasks for tag in extract_tags_from(task)])

    # Calculate virtual times
    virtualTime = {}
    tDict = {}
    _tasksTags = []
    for task in sorted(tasks, key=lambda d: d["urgency"], reverse=True):
        _tags = set(tags_and_description(task))
        if _tags not in _tasksTags:
            _tasksTags.append(_tags)
            tDict[task["id"]] = task
            virtualTime[task["id"]] = exp(task["urgency"])

    # Calculate executed times
    executedTime = {
        tid: get_duration_on(tags_and_description(tDict[tid]))
        for tid in virtualTime.keys()
    }

    executedTimeTag = {tag: get_duration_on([tag]) for tag in tags}

    totalTimeTags = get_total_time_tags(executedTimeTag.keys())
    totalExecutedTime = sum(executedTime.values())

    # Shows must urgent task, since there is no sample time
    if totalTimeTags == 0 and totalExecutedTime == 0:
        print("No sampled time")
        print("Start by the most urgent task")
        tasks = tw.tasks.filter(filterString)
        print_task(sorted(tasks, key=lambda d: d["urgency"], reverse=True)[0])
        quit()

    totalVirtualTime = sum(virtualTime.values())

    # Calculate virtual times for each tag
    virtualTimeTag = calculate_tag_sum(tags, tDict, virtualTime)
    sharesTag, executedSharesTag = get_shares(
        executedTimeTag, virtualTimeTag, totalTimeTags, totalVirtualTime
    )

    tag_correction = {}
    for tag in sharesTag.keys():
        if executedSharesTag[tag] > sharesTag[tag]:
            tag_correction[tag] = sharesTag[tag] / executedSharesTag[tag]
        else:
            tag_correction[tag] = 1

    # Calculate executed time for each tag
    tids = tDict.keys()
    for tid in tids:
        for tag in extract_tags_from(tDict[tid]):
            virtualTime[tid] *= tag_correction[tag]

    totalVirtualTime = sum(virtualTime.values())

    # Calculate shares
    shares, executedShares = get_shares(
        executedTime, virtualTime, totalExecutedTime, totalVirtualTime
    )

    # Problem of a urgent long task and short tags
    if 1 in executedShares.values():
        tid = list(executedShares.keys())[list(executedShares.values()).index(1)]

        if sorted(tasks, key=lambda d: d["urgency"], reverse=True)[0]["id"] == tid:
            tags = tags_and_description(tDict[tid])
            _last_activity_time = last_activity_time(tags)

            if _last_activity_time < force_avoided_task_for_seconds:
                print("This is the only pending task started today")
                print(
                    "Please keep doing it for",
                    f"{int((
                        force_avoided_task_for_seconds-_last_activity_time
                      )/60)}min",
                    "uninterruptly",
                )
                print_task(tDict[tid])
                quit()

    difference = {key: shares[key] - executedShares[key] for key in shares.keys()}

    tid = max(difference, key=difference.get)

    # Verify if 
    _last_activity_time = last_activity_time(tags_and_description(tDict[tid]))
    if _last_activity_time > force_switch_after_seconds and len(tasks) > 1:
        skiped_task = tDict[tid]
        print("skipping", skiped_task)
        difference.pop(tid)
        tid = max(difference, key=difference.get)

    print("Needed: ", int(shares[tid] * 10000) / 100, "%", sep="")
    print(
        "Executed:  ",
        (
            int(executedTime[tid] * 10000 / totalExecutedTime) / 100
            if totalExecutedTime > 0
            else 0
        ),
        "%",
        sep="",
    )

    print_task(tDict[tid])
