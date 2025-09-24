import tempfile
from os import mkdir
from pathlib import Path

import pytest
from tasklib import Task, TaskWarrior
from tasklib.lazy import LazyUUIDTaskSet

from taskwarrior_scheduler.core import get_tasks


@pytest.fixture
def get_taskwarrior():
    tmp = "tmp"
    try:
        mkdir(tmp)
    except FileExistsError:
        pass

    _dir = tempfile.mkdtemp(dir=tmp)
    conf = tempfile.mkstemp(dir=_dir)

    tw = TaskWarrior(data_location=_dir, create=True, taskrc_location=conf[1])
    new_task = Task(tw, description="my first task", tags=["mytag"])
    new_task.save()
    new_task = Task(tw, description="my second task", project="myproject")
    new_task.save()
    new_task = Task(tw, description="my third task")
    new_task.save()

    _set = LazyUUIDTaskSet(tw, [new_task["uuid"]])

    new_taskb = Task(
        tw,
        description="my dependent task",
    )
    new_taskb.save()

    new_taskb["depends"] = _set
    new_taskb.save()

    tw.execute_command(["context", "define", "mycontext", "-mytag"])

    return tw


@pytest.fixture
def tasks(get_taskwarrior):  # noqa
    return get_tasks(None, get_taskwarrior)[0]
