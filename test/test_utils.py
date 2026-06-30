from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fixtures import get_taskwarrior, tasks

from taskwarrior_scheduler.core import tagless
from taskwarrior_scheduler.utils import (
    _format_relative,
    calculate_skip_wait,
    calculate_tag_sum,
    extract_tags_from,
    get_time_tw,
    print_task,
)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _entry(tags, start, end=None):
    e = {"id": 1, "start": _fmt(start), "tags": tags}
    if end is not None:
        e["end"] = _fmt(end)
    return e


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


def test_calculate_skip_wait_sem_entradas_anteriores():
    active_start = datetime(2026, 6, 30, 10, 0, 0, tzinfo=UTC)
    active_tags = {"mytag", "my first task"}
    with patch("taskwarrior_scheduler.utils.timew_export", return_value=[]):
        result = calculate_skip_wait(active_tags, active_start)
    assert result is None


def test_calculate_skip_wait_apenas_entrada_ativa():
    # Entrada sem "end" = entrada ativa; deve ser ignorada
    active_start = datetime(2026, 6, 30, 10, 0, 0, tzinfo=UTC)
    active_tags = {"mytag", "my first task"}
    entries = [_entry(list(active_tags), active_start)]
    with patch("taskwarrior_scheduler.utils.timew_export", return_value=entries):
        result = calculate_skip_wait(active_tags, active_start)
    assert result is None


def test_calculate_skip_wait_delta_dentro_do_limite():
    # ΔT = 30min → wait = 60min
    active_start = datetime(2026, 6, 30, 9, 30, 0, tzinfo=UTC)
    active_tags = {"mytag", "my first task"}
    entries = [
        _entry(
            list(active_tags),
            datetime(2026, 6, 30, 8, 0, 0, tzinfo=UTC),
            datetime(2026, 6, 30, 9, 0, 0, tzinfo=UTC),
        )
    ]
    with patch("taskwarrior_scheduler.utils.timew_export", return_value=entries):
        result = calculate_skip_wait(active_tags, active_start)
    assert result == timedelta(minutes=60)


def test_calculate_skip_wait_delta_acima_do_limite():
    # ΔT = 2h > 1h → None
    active_start = datetime(2026, 6, 30, 9, 0, 0, tzinfo=UTC)
    active_tags = {"mytag", "my first task"}
    entries = [
        _entry(
            list(active_tags),
            datetime(2026, 6, 30, 6, 0, 0, tzinfo=UTC),
            datetime(2026, 6, 30, 7, 0, 0, tzinfo=UTC),
        )
    ]
    with patch("taskwarrior_scheduler.utils.timew_export", return_value=entries):
        result = calculate_skip_wait(active_tags, active_start)
    assert result is None


def test_calculate_skip_wait_delta_negativo():
    # last_end > active_start (clock skew) → None
    active_start = datetime(2026, 6, 30, 9, 0, 0, tzinfo=UTC)
    active_tags = {"mytag", "my first task"}
    entries = [
        _entry(
            list(active_tags),
            datetime(2026, 6, 30, 8, 0, 0, tzinfo=UTC),
            datetime(2026, 6, 30, 9, 5, 0, tzinfo=UTC),  # end after active_start
        )
    ]
    with patch("taskwarrior_scheduler.utils.timew_export", return_value=entries):
        result = calculate_skip_wait(active_tags, active_start)
    assert result is None


def test_calculate_skip_wait_usa_end_mais_recente():
    # Duas entradas anteriores — usar o max(end): ΔT = 10:00−9:45 = 15min → wait = 30min
    active_start = datetime(2026, 6, 30, 10, 0, 0, tzinfo=UTC)
    active_tags = {"mytag", "my first task"}
    entries = [
        _entry(
            list(active_tags),
            datetime(2026, 6, 30, 7, 0, 0, tzinfo=UTC),
            datetime(2026, 6, 30, 7, 30, 0, tzinfo=UTC),
        ),
        _entry(
            list(active_tags),
            datetime(2026, 6, 30, 9, 30, 0, tzinfo=UTC),
            datetime(2026, 6, 30, 9, 45, 0, tzinfo=UTC),
        ),
    ]
    with patch("taskwarrior_scheduler.utils.timew_export", return_value=entries):
        result = calculate_skip_wait(active_tags, active_start)
    assert result == timedelta(minutes=30)


def test_calculate_skip_wait_ignora_outras_tags():
    active_start = datetime(2026, 6, 30, 10, 0, 0, tzinfo=UTC)
    active_tags = {"mytag", "my first task"}
    other_tags = {"othertag", "other task"}
    entries = [
        _entry(
            list(other_tags),
            datetime(2026, 6, 30, 9, 0, 0, tzinfo=UTC),
            datetime(2026, 6, 30, 9, 30, 0, tzinfo=UTC),
        )
    ]
    with patch("taskwarrior_scheduler.utils.timew_export", return_value=entries):
        result = calculate_skip_wait(active_tags, active_start)
    assert result is None
