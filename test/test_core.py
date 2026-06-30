import pytest
from fixtures import get_taskwarrior, tasks
from tasklib import Task
from unittest.mock import patch

from taskwarrior_scheduler.core import get_tasks, get_times
from taskwarrior_scheduler.utils import extract_tags_from


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


def test_get_times_does_not_call_timew_when_day_provided(tasks):
    tags = set(tag for task in tasks.values() for tag in extract_tags_from(task))
    day = []
    with patch(
        "taskwarrior_scheduler.utils.timew_export",
        side_effect=AssertionError("timew must not be called from utils"),
    ):
        with patch(
            "taskwarrior_scheduler.core.timew_export",
            side_effect=AssertionError("timew must not be called from core"),
        ):
            result = get_times(tasks, tags, day=day)
    assert result is None
