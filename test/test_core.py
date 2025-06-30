import pytest
from fixtures import get_taskwarrior
from tasklib import Task

from scheduler.core import get_tasks, get_times


def test_get_tasks(get_taskwarrior):  # noqa
    value = get_tasks([], get_taskwarrior)
    assert len(value[0]) == 3, "Wrong number of tasks"
    assert value[1] == "+UNBLOCKED and +PENDING", "Wrong filterString"

    value = get_tasks(None, get_taskwarrior)
    assert len(value[0]) == 3, "Wrong number of tasks"
    assert value[1] == "+UNBLOCKED and +PENDING", "Wrong filterString"

    value = get_tasks(["-mytag"], get_taskwarrior)
    assert len(value[0]) == 2, "Wrong number of tasks"
    assert value[1] == "( -mytag ) and +UNBLOCKED and +PENDING", "Wrong filterString"

    get_taskwarrior.execute_command(["context", "mycontext"])

    value = get_tasks(None, get_taskwarrior)
    assert len(value[0]) == 2, "Wrong number of tasks"
    assert value[1] == "+UNBLOCKED and +PENDING and ( -mytag )", "Wrong filterString"
