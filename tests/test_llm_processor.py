from datetime import timedelta
import base64

from health_companion_bot.llm_processor import (
    SleepLog,
    _build_user_message,
    _count_non_null_fields,
    _parse_sleep_text,
)


def test_duration_parses_human_readable() -> None:
    log = SleepLog(duration="7 ч 4 мин")
    assert log.duration == timedelta(hours=7, minutes=4)


def test_duration_parses_hh_mm() -> None:
    log = SleepLog(duration="07:15")
    assert log.duration == timedelta(hours=7, minutes=15)


def test_duration_ignores_garbage() -> None:
    log = SleepLog(duration=",  ")
    assert log.duration is None


def test_parse_sleep_text_extracts_fields() -> None:
    text = (
        "Ночной сон: 7 ч 4 мин\n"
        "Глубокий сон: 29 %\n"
        "Легкий сон: 45 %\n"
        "Быстрый сон: 26 %\n"
        "Время глубокого сна: 81 балл\n"
        "Количество пробуждений: 0 раз\n"
        "Качество дыхания: 98 баллов\n"
        "Ср. пульс: 49 уд/мин\n"
        "Ср. ВСР: 47 мс\n"
        "Ср. SpO2: 98 %\n"
        "Ср. частота дыхания: 14 вдох/мин\n"
    )
    data = _parse_sleep_text(text)
    assert data["duration"] == timedelta(hours=7, minutes=4)
    assert data["deep_stage"] == 29
    assert data["light_stage"] == 45
    assert data["rem_stage"] == 26
    assert data["time_deep_stage_score"] == 81
    assert data["wake_up_count"] == 0
    assert data["breathe_quality"] == 98
    assert data["average_pulse"] == 49
    assert data["average_pulse_variability"] == 47
    assert data["average_spo2"] == 98
    assert data["breathe_frequency"] == 14


def test_count_non_null_fields() -> None:
    log = SleepLog(average_pulse=49, breathe_frequency=14)
    assert _count_non_null_fields(log) == 2


def test_build_user_message_with_image(tmp_path) -> None:
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"test-image")
    message = _build_user_message("hello", image_path)
    assert message["role"] == "user"
    assert message["content"] == "hello"
    assert "images" in message
    assert message["images"][0] == base64.b64encode(b"test-image").decode("ascii")
