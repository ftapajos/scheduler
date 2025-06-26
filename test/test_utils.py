from fixtures import get_taskwarrior, tasks

from scheduler.core import tagless
from scheduler.utils import calculate_tag_sum, extract_tags_from, get_time_tw


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
