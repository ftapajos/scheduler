from datetime import timedelta
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from taskwarrior_scheduler.sne import app

runner = CliRunner()


def _make_task(description, tags, project=None, start=None):
    data = {
        "description": description,
        "tags": tags,
        "project": project,
        "start": start,
    }
    mock = MagicMock()
    mock.__getitem__ = MagicMock(side_effect=lambda key: data[key])
    mock.__setitem__ = MagicMock(side_effect=lambda key, val: data.update({key: val}))
    return mock


def test_sne_sem_tarefa_ativa():
    mock_task = _make_task("my task", ["mytag"])
    with patch(
        "taskwarrior_scheduler.sne.get_tasks", return_value=({"1": mock_task}, "")
    ):
        with patch("taskwarrior_scheduler.sne.timew_export", return_value=[]):
            with patch(
                "taskwarrior_scheduler.sne.get_active_tw_entry", return_value=None
            ):
                result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "No active task" in result.output


def test_sne_fallback_quando_wait_delta_none():
    # Quando calculate_skip_wait retorna None, comporta-se como next (exit 1, sem save)
    active_entry = {"start": "20260630T090000Z", "tags": ["mytag", "my first task"]}
    active_task = _make_task("my first task", ["mytag"])
    next_task = _make_task("my second task", ["othertag"])
    tDict = {"1": active_task, "2": next_task}

    with patch("taskwarrior_scheduler.sne.get_tasks", return_value=(tDict, "")):
        with patch(
            "taskwarrior_scheduler.sne.timew_export", return_value=[active_entry]
        ):
            with patch(
                "taskwarrior_scheduler.sne.get_active_tw_entry",
                return_value=active_entry,
            ):
                with patch(
                    "taskwarrior_scheduler.sne.calculate_skip_wait", return_value=None
                ):
                    with patch(
                        "taskwarrior_scheduler.sne.find_next_task",
                        return_value=(next_task, None, None),
                    ):
                        with patch("taskwarrior_scheduler.sne.print_task"):
                            result = runner.invoke(app, [])

    assert result.exit_code == 1
    active_task.save.assert_not_called()


def test_sne_define_wait_e_sugere_proxima():
    # Caminho normal: define wait na tarefa ativa e sugere próxima (exit 0)
    active_entry = {"start": "20260630T090000Z", "tags": ["mytag", "my first task"]}
    active_task = _make_task("my first task", ["mytag"])
    next_task = _make_task("my second task", ["othertag"])
    tDict = {"1": active_task, "2": next_task}
    wait_delta = timedelta(minutes=30)

    with patch("taskwarrior_scheduler.sne.get_tasks", return_value=(tDict, "")):
        with patch(
            "taskwarrior_scheduler.sne.timew_export", return_value=[active_entry]
        ):
            with patch(
                "taskwarrior_scheduler.sne.get_active_tw_entry",
                return_value=active_entry,
            ):
                with patch(
                    "taskwarrior_scheduler.sne.calculate_skip_wait",
                    return_value=wait_delta,
                ):
                    with patch(
                        "taskwarrior_scheduler.sne.find_next_task",
                        return_value=(next_task, None, None),
                    ):
                        with patch("taskwarrior_scheduler.sne.print_task"):
                            result = runner.invoke(app, [])

    assert result.exit_code == 0
    active_task.save.assert_called_once()


def test_sne_tarefa_ativa_nao_encontrada_no_pending():
    # Active timewarrior entry has tags that don't match any pending task
    active_entry = {"start": "20260630T090000Z", "tags": ["completed_tag", "done task"]}
    mock_task = _make_task("other task", ["othertag"])
    tDict = {"1": mock_task}

    with patch("taskwarrior_scheduler.sne.get_tasks", return_value=(tDict, "")):
        with patch(
            "taskwarrior_scheduler.sne.timew_export", return_value=[active_entry]
        ):
            with patch(
                "taskwarrior_scheduler.sne.get_active_tw_entry",
                return_value=active_entry,
            ):
                result = runner.invoke(app, [])

    assert result.exit_code == 1
    assert "Active task not found in pending tasks" in result.output


def test_sne_sem_outras_tarefas_apos_remover_ativa():
    # Only one pending task and it's the active one — nothing left to suggest
    active_entry = {"start": "20260630T090000Z", "tags": ["mytag", "my first task"]}
    active_task = _make_task("my first task", ["mytag"])
    tDict = {"1": active_task}

    with patch("taskwarrior_scheduler.sne.get_tasks", return_value=(tDict, "")):
        with patch(
            "taskwarrior_scheduler.sne.timew_export", return_value=[active_entry]
        ):
            with patch(
                "taskwarrior_scheduler.sne.get_active_tw_entry",
                return_value=active_entry,
            ):
                result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "No other tasks available" in result.output
