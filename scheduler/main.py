#!/usr/bin/env python

import subprocess
from typing import List, Optional

import typer
from tasklib import TaskWarrior
from typing_extensions import Annotated

from .core import get_difference, get_tasks, get_times
from .utils import (
    extract_tags_from,
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
    tDict, filterString = get_tasks(filters)

    # Apply custom filters and restrict to unblocked and pending tasks
    # Check if there any tags
    if len(tDict) <= 0:
        print("Taskless")
        subprocess.run(["task", "ls", filterString])
        quit()

    tags = set([tag for task in tDict.values() for tag in extract_tags_from(task)])

    times = get_times(tDict, tags)

    # Shows must urgent task, since there is no sample time
    if times is None:
        print("No sampled time")
        print("Start by the most urgent task")
        tw = TaskWarrior()
        tasks = tw.tasks.filter(filterString)
        print_task(sorted(tasks, key=lambda d: d["urgency"], reverse=True)[0])
        quit()

    only_executed_task, difference, shares, executed_shares = get_difference(
        times, tDict
    )

    (virtualTime, executedTime), (sharesTag, executedSharesTag) = times

    # Problem of a urgent long task and short tags
    if only_executed_task is not None:
        tags = tags_and_description(only_executed_task)
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
            print_task(only_executed_task)
            quit()

    tid = max(difference, key=difference.get)

    # Verify if
    _last_activity_time = last_activity_time(tags_and_description(tDict[tid]))
    if _last_activity_time > force_switch_after_seconds and len(tDict) > 1:
        skiped_task = tDict[tid]
        print("skipping", skiped_task)
        difference.pop(tid)
        tid = max(difference, key=difference.get)

    print("Needed: ", int(shares[tid] * 10000) / 100, "%", sep="")
    print(
        "Executed:  ",
        int(executed_shares[tid] * 10000) / 100,
        "%",
        sep="",
    )

    print_task(tDict[tid])
