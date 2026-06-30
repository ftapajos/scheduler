#!/usr/bin/env python

import os
import subprocess
from typing import Annotated, List, Optional

import typer

from .core import find_next_task, get_tasks
from .timewarrior import timew_export
from .utils import get_active_tw_entry, print_task, tags_and_description

app = typer.Typer()


@app.callback(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    invoke_without_command=True,
)
def fne(
    ctx: typer.Context, filters: Annotated[Optional[List[str]], typer.Argument()] = None
):
    tDict, filterString = get_tasks(filters)

    if len(tDict) <= 0:
        print("Taskless")
        subprocess.run(["task", "ls", filterString])
        quit()

    day = timew_export(":day")

    active_entry = get_active_tw_entry(day)
    if active_entry is not None:
        active_tags = set(active_entry["tags"])
        for tid, task in list(tDict.items()):
            if active_tags == set(tags_and_description(task)):
                tDict.pop(tid)
                break

    if len(tDict) <= 0:
        print("No other tasks available")
        quit()

    task, needed, executed = find_next_task(tDict, day)

    if needed is not None:
        print("Needed: ", int(needed * 10000) / 100, "%", sep="")
        print("Executed:  ", int(executed * 10000) / 100, "%", sep="")

    print_task(task)

    if task["start"] is not None:
        all_entries = timew_export()
        tw_ids = [
            d["id"]
            for d in all_entries
            if set(d["tags"]) == set(tags_and_description(task))
        ]
        if tw_ids:
            timew_write = os.environ.get("TIMEWARRIOR_WRITE", "timew")
            subprocess.run([timew_write, "cont", f"@{min(tw_ids)}"])
