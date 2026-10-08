# Moderation Service Skeleton

Минимальный сервис-скелет без валидаций и бизнес-проверок:
- принимает RPC-запрос на создание задачи;
- сразу отвечает `IN_PROGRESS`;
- через 1 секунду публикует событие `moderation.task.completed`;
- результат отдается отдельной RPC-ручкой.

## Run

В общей среде для Python-интервью зависимости уже установлены, поэтому первую команду можно
пропустить. Для отдельного локального окружения выполните полный набор команд:

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m service.main
```

Сервис поднимается на `http://localhost:8080`.

## Terminal Test Scenario

1. Запустите сервис в первом терминале:

```bash
python3 -m service.main
```

2. Во втором терминале отправьте задачу:

```bash
SUBMIT_RESPONSE=$(curl -sS -X POST http://localhost:8080/rpc/SubmitModerationTask \
  -H 'Content-Type: application/json' \
  -d '{
    "request_id": "req-100",
    "review": {
      "review_id": "review-100",
      "text": "Тут обман и преступники"
    }
  }')
echo "$SUBMIT_RESPONSE"
```

Ожидается ответ со статусом `IN_PROGRESS` и `task_id`.

3. Сохраните `task_id` и сразу запросите результат:

```bash
TASK_ID=$(echo "$SUBMIT_RESPONSE" | jq -r '.task_id')
curl -sS -X POST http://localhost:8080/rpc/GetModerationTaskResult \
  -H 'Content-Type: application/json' \
  -d "{\"task_id\":\"$TASK_ID\"}"
```

Ожидается `status: IN_PROGRESS`.

4. Подождите 1 секунду и запросите снова:

```bash
sleep 1.2
curl -sS -X POST http://localhost:8080/rpc/GetModerationTaskResult \
  -H 'Content-Type: application/json' \
  -d "{\"task_id\":\"$TASK_ID\"}"
```

Ожидается `status: COMPLETED`.

5. Проверьте первый терминал: там будет напечатано событие `moderation.task.completed` в JSON.

## Notes

- Требуется `jq` для извлечения `task_id`.
- Публикация события сейчас сделана через `print(...)` в `stdout` как заглушка.
- Нужен Python 3.12. Набор зависимостей совпадает с остальными Python-кейсами для интервью и
  описан в корневом `pyproject.toml`.
- Сервис использует ансамбль `ML + rules`:
  - модели по темам лежат в `service/models/*.joblib`;
  - манифест и пороги: `service/models/manifest.json`.
- Обучение/пересборка артефактов:
```bash
python3 scripts/train_topic_models.py
```
