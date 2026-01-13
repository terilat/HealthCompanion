from __future__ import annotations

import base64
import json
import logging
import re
from datetime import date as Date, time as Time, timedelta as TimeDelta
from pathlib import Path
from typing import Any

import httpx
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
SYSTEM_PROMPT = (
    "Тебе на вход будет подаваться текст или скриншот из приложения Huawei Health. "
    "Ты должен извлечь из них структурированные данные согласно формату и вернуть их "
    "в требуемом формате. Не нужно добавлять никаких комментариев или пояснений. "
    "Если какое-то поле не удалось извлечь, то верни null. Список извлекаемых данных: "
    "duration (общая продолжительность сна), score (общая оценка качества сна), deep_stage "
    "(доля глубокого сна в общей продолжительности сна), light_stage (доля легкого сна "
    "в общей продолжительности сна), rem_stage (доля быстрого сна в общей продолжительности "
    "сна), time_deep_stage_score (оценка времени глубокого сна), wake_up_count (количество "
    "пробуждений за ночь), breathe_quality (качество дыхания), average_pulse (средний пульс "
    "за ночь), average_pulse_variability (средняя вариабельность пульса), average_spo2 "
    "(средний уровень насыщения крови кислородом), breathe_frequency (частота дыхания)."
)
OCR_PROMPT = (
    "Считай весь текст со скриншота максимально точно. "
    "Верни только распознанный текст, построчно, без комментариев."
)

MIN_NON_NULL_FIELDS = 5


class SleepLog(BaseModel):
    date: Date | None = Field(None, description="Дата сна в формате ISO 8601. Формат: YYYY-MM-DD")
    start: Time | None = Field(None, description="Время начала сна в формате ISO 8601. Формат: HH:MM")
    end: Time | None = Field(None, description="Время окончания сна в формате ISO 8601. Формат: HH:MM")
    duration: TimeDelta | None = Field(None, description="Общая продолжительность сна. Формат: HH:MM")

    score: int | None = Field(None, description="Общая оценка качества сна (0-100)", ge=0, le=100)

    deep_stage: int | None = Field(
        None,
        description="Доля глубокого сна в общей продолжительности сна (0-100)",
        ge=0,
        le=100,
    )
    light_stage: int | None = Field(
        None,
        description="Доля легкого сна в общей продолжительности сна (0-100)",
        ge=0,
        le=100,
    )
    rem_stage: int | None = Field(
        None,
        description="Доля быстрого сна в общей продолжительности сна (0-100)",
        ge=0,
        le=100,
    )

    time_deep_stage_score: int | None = Field(
        None, description="Оценка времени глубокого сна (0-100)", ge=0, le=100
    )

    wake_up_count: int | None = Field(None, description="Количество пробуждений за ночь", ge=0)

    breathe_quality: int | None = Field(
        None, description="Качество дыхания (0-100)", ge=0, le=100
    )

    average_pulse: int | None = Field(None, description="Средний пульс за ночь (уд/мин)", ge=0, le=200)
    average_pulse_variability: int | None = Field(
        None, description="Средняя вариабельность пульса (мс)", ge=0
    )
    average_spo2: int | None = Field(
        None, description="Средний уровень насыщения крови кислородом (%)", ge=0, le=100
    )

    breathe_frequency: int | None = Field(
        None, description="Частота дыхания (дыханий в минуту)", ge=0, le=60
    )

    @field_validator("duration", mode="before")
    @classmethod
    def _parse_duration(cls, value: Any) -> Any:
        if value is None or isinstance(value, TimeDelta):
            return value
        if not isinstance(value, str):
            return value
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if not re.search(r"\d", cleaned):
            return None
        if ":" in cleaned:
            parts = cleaned.split(":")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return TimeDelta(hours=int(parts[0]), minutes=int(parts[1]))
        hours_match = re.search(r"(\d+)\s*(?:ч|час(?:а|ов)?)", cleaned)
        minutes_match = re.search(r"(\d+)\s*(?:мин|минута|минуты|минут)", cleaned)
        if hours_match or minutes_match:
            hours = int(hours_match.group(1)) if hours_match else 0
            minutes = int(minutes_match.group(1)) if minutes_match else 0
            return TimeDelta(hours=hours, minutes=minutes)
        return None

# Создаем клиент OpenAI, настроенный на Ollama API
openai_client = AsyncOpenAI(
    base_url=f"{OLLAMA_BASE_URL}/v1",
    api_key="ollama",  # Ollama не требует реальный API ключ
)

# Патчим клиент через instructor для структурированного вывода
client = instructor.patch(
    openai_client,
    mode=instructor.Mode.JSON,
)


def _encode_image(image_path: Path) -> str:
    with image_path.open("rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")
    return encoded


def _build_user_message(user_text: str, image_path: Path | None) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "user", "content": user_text}
    if image_path:
        message["images"] = [_encode_image(image_path)]
    return message


async def _extract_with_ollama(
    user_text: str,
    response_model: type[BaseModel],
    image_path: Path,
) -> BaseModel:
    payload = {
        "model": "qwen3-vl:8b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            _build_user_message(user_text, image_path),
        ],
        "stream": False,
        "format": response_model.model_json_schema(),
    }
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        response = await http_client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
    content = (data.get("message") or {}).get("content", "")
    try:
        return response_model.model_validate_json(content)
    except Exception as exc:
        json_start = content.find("{")
        json_end = content.rfind("}")
        if json_start != -1 and json_end != -1 and json_end > json_start:
            try:
                return response_model.model_validate(json.loads(content[json_start : json_end + 1]))
            except Exception:
                pass
        logger.warning("Failed to parse Ollama response: %s", content)
        raise exc


async def _extract_text_with_ollama(image_path: Path) -> str:
    payload = {
        "model": "qwen3-vl:8b",
        "messages": [
            {"role": "system", "content": OCR_PROMPT},
            _build_user_message("Считай текст с изображения.", image_path),
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        response = await http_client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
    return (data.get("message") or {}).get("content", "")


def _parse_sleep_text(text: str) -> dict[str, Any]:
    cleaned = " ".join(text.replace("\n", " ").split())
    data: dict[str, Any] = {}

    duration_match = re.search(
        r"Ночной сон:\s*(\d+)\s*ч(?:\s*(\d+)\s*мин)?",
        cleaned,
        flags=re.IGNORECASE,
    )
    if duration_match:
        hours = int(duration_match.group(1))
        minutes = int(duration_match.group(2) or 0)
        data["duration"] = TimeDelta(hours=hours, minutes=minutes)

    deep_match = re.search(r"Глубокий сон:\s*(\d+)\s*%", cleaned, flags=re.IGNORECASE)
    if deep_match:
        data["deep_stage"] = int(deep_match.group(1))

    light_match = re.search(r"Легкий сон:\s*(\d+)\s*%", cleaned, flags=re.IGNORECASE)
    if light_match:
        data["light_stage"] = int(light_match.group(1))

    rem_match = re.search(r"Быстрый сон:\s*(\d+)\s*%", cleaned, flags=re.IGNORECASE)
    if rem_match:
        data["rem_stage"] = int(rem_match.group(1))

    deep_score_match = re.search(
        r"Время глубокого сна:\s*(\d+)\s*балл",
        cleaned,
        flags=re.IGNORECASE,
    )
    if deep_score_match:
        data["time_deep_stage_score"] = int(deep_score_match.group(1))

    wake_match = re.search(
        r"Количество пробуждений:\s*(\d+)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if wake_match:
        data["wake_up_count"] = int(wake_match.group(1))

    breathe_match = re.search(
        r"Качество дыхания:\s*(\d+)\s*балл",
        cleaned,
        flags=re.IGNORECASE,
    )
    if breathe_match:
        data["breathe_quality"] = int(breathe_match.group(1))

    pulse_match = re.search(r"Ср\.\s*пульс:\s*(\d+)", cleaned, flags=re.IGNORECASE)
    if pulse_match:
        data["average_pulse"] = int(pulse_match.group(1))

    hrv_match = re.search(r"Ср\.\s*ВСР:\s*(\d+)", cleaned, flags=re.IGNORECASE)
    if hrv_match:
        data["average_pulse_variability"] = int(hrv_match.group(1))

    spo2_match = re.search(r"Ср\.\s*SpO2:\s*(\d+)", cleaned, flags=re.IGNORECASE)
    if spo2_match:
        data["average_spo2"] = int(spo2_match.group(1))

    breath_freq_match = re.search(
        r"Ср\.\s*частота дыхания:\s*(\d+)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if breath_freq_match:
        data["breathe_frequency"] = int(breath_freq_match.group(1))

    return data


def _count_non_null_fields(model: BaseModel) -> int:
    return sum(value is not None for value in model.model_dump().values())


async def extract_health_data(
    user_text: str,
    response_model: type[BaseModel],
    image_path: Path | None = None,
) -> BaseModel:
    if image_path:
        result = await _extract_with_ollama(user_text, response_model, image_path)
        if _count_non_null_fields(result) < MIN_NON_NULL_FIELDS:
            ocr_text = await _extract_text_with_ollama(image_path)
            extracted = _parse_sleep_text(ocr_text)
            if extracted:
                merged = {**result.model_dump(), **extracted}
                return response_model.model_validate(merged)
        return result
    result = await client.chat.completions.create(
        model="qwen3-vl:8b",
        messages=[
            {
                "role": "system", 
                "content": SYSTEM_PROMPT,
            },
            _build_user_message(user_text, image_path),
        ],
        response_model=response_model,
        max_retries=3,
        timeout=60.0,
    )
    return result
