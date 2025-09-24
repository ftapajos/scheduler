#!/usr/bin/env python

from typing import List, Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Column, Table
from typing_extensions import Annotated

from .core import get_difference, get_tag_correction, get_tasks, get_times, tagless
from .utils import extract_tags_from

app = typer.Typer()

console = Console()


@app.command()
def tags(
    ctx: typer.Context, filters: Annotated[Optional[List[str]], typer.Argument()] = None
):
    tasks, filterString = get_tasks(filters)

    # Get all tags
    tags = set([tag for task in tasks.values() for tag in extract_tags_from(task)])

    times = get_times(tasks, tags)

    # Shows must urgent task, since there is no sample time
    if times is None:
        print("[bold red]Not enough sampled time[/bold red]")
        quit()

    (virtualTime, executedTime), (sharesTag, executedSharesTag) = times

    tag_correction = get_tag_correction(sharesTag, executedSharesTag)

    tags = sorted(tag_correction.items(), key=lambda item: item[1])
    tags = [tag for tag in tags if tag[0] != tagless]

    table = Table("Tag", Column("Time penalization", justify="right"))
    for tag in tags:
        value = -(1 - tag[1]) * 100
        table.add_row(tag[0], f"{value:.2f}%")
    console.print(table)


@app.command()
def diff(
    ctx: typer.Context, filters: Annotated[Optional[List[str]], typer.Argument()] = None
):
    tasks, filterString = get_tasks(filters)

    tags = set([tag for task in tasks.values() for tag in extract_tags_from(task)])

    times = get_times(tasks, tags)

    _, difference, shares, executed_shares = get_difference(times, tasks)

    if len(difference) == 0:
        print("[bold red]No tasks[/bold red]")
        quit()

    else:
        sorted_tasks = sorted(
            difference.items(), key=lambda item: item[1], reverse=True
        )
        table = Table(
            "id",
            "Description",
            Column("Needed", justify="right"),
            Column("Executed", justify="right"),
        )

        for task in sorted_tasks:
            tid = task[0]
            share = 100 * shares[tid]
            executed_share = 100 * executed_shares[tid]
            table.add_row(
                str(tid), str(tasks[tid]), f"{share:.2f}%", f"{executed_share:.2f}%"
            )

    with console.pager():
        console.print(table)
