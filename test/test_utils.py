from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fixtures import get_taskwarrior, tasks

from taskwarrior_scheduler.core import tagless
from taskwarrior_scheduler.utils import (
    _format_relative,
    calculate_tag_sum,
    extract_tags_from,
    get_time_tw,
    print_task,
)


def test_extract_tags_from(tasks):  # noqa
    tags = extract_tags_from(tasks[1])
    assert tags == ["mytag"]

    tags = extract_tags_from(tasks[2])
    assert tags == ["myproject"]

    tags = extract_tags_from(tasks[3])
    assert tags == [tagless]


def test_calculate_tag_sum(tasks):  # noqa
    tags = ["mytag"]
    virtualTimes = {i: 10 for i in tasks.keys()}
    result = calculate_tag_sum(tags, tasks, virtualTimes)
    assert len(result) == 1
    assert "mytag" in result
    assert result["mytag"] == 10


def test_get_time_tw():
    tw_event = {
        "id": 2,
        "start": "20250625T152913Z",
        "end": "20250625T153911Z",
        "tags": ["mytag"],
    }
    assert get_time_tw(tw_event) == 598

    del tw_event["end"]
    assert get_time_tw(tw_event) > 598


def test_format_relative():
    now = datetime.now(UTC)
    assert _format_relative(None) == ""
    assert _format_relative(now + timedelta(minutes=30)) == "30min"
    assert _format_relative(now + timedelta(hours=9)) == "9h"
    assert _format_relative(now + timedelta(days=2)) == "2d"
    assert _format_relative(now + timedelta(weeks=2)) == "2w"
    assert _format_relative(now - timedelta(hours=1)) == "1h ago"


def test_print_task_does_not_call_task_subprocess(tasks):
    task = list(tasks.values())[0]
    with patch("taskwarrior_scheduler.utils.timew_export", return_value=[]):
        with patch("subprocess.run") as mock_run:
            print_task(task)
            for call in mock_run.call_args_list:
                assert (
                    call.args[0][0] != "task"
                ), "print_task must not call the task subprocess"
