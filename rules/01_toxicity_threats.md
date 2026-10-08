# Регламент: Токсичность, оскорбления и угрозы

## Цель
Блокировать контент с оскорблениями, hate speech и угрозами в тексте/изображениях, сохраняя допустимую эмоциональную критику.

## Технические зависимости и контракт
- `obscene_lexicon`: список токенов с метаданными severity (`low|medium|high`) в JSON.
- `hate_patterns`: набор regex/phrase-паттернов с указанием защищенного признака.
- `threat_patterns`: набор паттернов с типом угрозы (`direct|indirect`).
- `vision_violence_score`: число `0.0..1.0` по каждой картинке.
- `ocr_result`: массив блоков `{text, confidence}`, confidence `0.0..1.0`.

Пример минимального формата:
```json
{
  "obscene_lexicon": [{"token":"...", "severity":"medium"}],
  "hate_patterns": [{"pattern":"...", "target_group":"religion"}],
  "threat_patterns": [{"pattern":"...", "threat_type":"direct"}]
}
```

## Термины и определения
- **Hate speech**: унижение, дегуманизация или призыв к ущербу по защищенному признаку (раса, национальность, этничность, религия, пол, гендер, ориентация, инвалидность).
- **Прямая угроза**: явное обещание вреда (`"я тебя убью"`).
- **Косвенная угроза**: намек на вред без явного обещания (`"тебя найдут"`).
- **Адресат есть**: в тексте присутствует 2-е лицо, обращение к конкретному человеку/группе или сущности (`ты`, `вы`, `этот продавец`, название группы).
- **Цитирование без позиции автора**: токсичная цитата приведена без осуждения/дистанцирования (`цитирую`, но нет маркеров "это недопустимо", "не согласен").

## Нормализация входа
- Хранить две версии: `raw_text` и `normalized_text`.
- `normalized_text`: lowercase, нормализация смешанной кириллицы/латиницы, сжатие повторов до 2 символов (`ууужас` -> `уужас`).
- Emoji не удаляются: маппятся в токены (`🤬` -> `emoji_anger`, `🔞` -> `emoji_18plus`) и участвуют в проверке.
- Все решения логируются с ссылкой на `raw_text`, чтобы не терять интенсивность/контекст.

## Алгоритм проверки
1. Выполнить текстовые проверки на `raw_text` и `normalized_text` параллельно.
2. Для каждой картинки выполнить OCR.
3. Если средний OCR confidence < `0.65`, не ставить `TOXIC_IMAGE_TEXT`; отправить в `REVIEW` с техническим флагом `LOW_OCR_CONFIDENCE`.
4. Если OCR confidence >= `0.65`, прогнать OCR-текст через те же словари/паттерны.
5. Получить `vision_violence_score` по каждой картинке:
- `>= 0.85`: высокий риск насилия.
- `0.60..0.84`: средний риск, требуется `REVIEW`.
- `< 0.60`: низкий риск.
6. Собрать все reason codes и рассчитать финальное решение через приоритеты.

## Таблица решений (детерминированная)
- `REJECT`:
- Есть `TOXIC_HATE`.
- Или есть `TOXIC_THREAT_DIRECT`.
- Или есть `TOXIC_IMAGE_TEXT` + threat/hate-паттерн.
- `REVIEW`:
- Есть только `TOXIC_INSULT` без адресата.
- Или `TOXIC_THREAT_INDIRECT`.
- Или цитирование токсичной фразы без явной позиции автора.
- Или `LOW_OCR_CONFIDENCE`.
- Или `vision_violence_score` в диапазоне `0.60..0.84`.
- `APPROVE`:
- Нет reason codes из этого регламента.
- Есть эмоциональная критика продукта/сервиса без адресной атаки.

## Приоритеты и мультиразметка
- Формат результата: `primary_reason_code` + `secondary_reason_codes[]`.
- Порядок приоритета (сверху вниз):
1. `ILLEGAL_INCITEMENT`
2. `TOXIC_HATE`
3. `TOXIC_THREAT_DIRECT`
4. `TOXIC_THREAT_INDIRECT`
5. `TOXIC_IMAGE_TEXT`
6. `TOXIC_INSULT`
- Если изображение содержит и угрозу, и незаконный призыв, `primary = ILLEGAL_INCITEMENT`, `secondary` включает `TOXIC_IMAGE_TEXT` и тип угрозы.

## Reason codes
- `TOXIC_INSULT`: адресное оскорбление/унижение без защищенного признака.
- `TOXIC_HATE`: hate speech по защищенному признаку.
- `TOXIC_THREAT_DIRECT`: явная угроза физического вреда.
- `TOXIC_THREAT_INDIRECT`: косвенная угроза/запугивание.
- `TOXIC_IMAGE_TEXT`: токсичный/угрожающий текст, найденный OCR на изображении.
- `LOW_OCR_CONFIDENCE`: технический код для ручной проверки при слабом OCR.

## Примеры
- `REJECT`: "Ты мразь, тебя надо избить".
- `REVIEW`: "Цитирую: 'ты мразь'".
- `APPROVE`: "Сервис раздражает, но товар пришел вовремя".

## Edge cases
- Маскировка угроз (`l33t`, разрывы символами, mixed `a/а`, `p/р`) проверяется на `normalized_text`.
- Псевдокоды (`binary`, `морзе`) без уверенной декодировки -> `REVIEW` с `TOXIC_THREAT_INDIRECT`.
- Повторные проверки: использовать cache key `sha256(review_text + image_hashes + ruleset_version)`.

## Тестовая матрица
- T1: Прямая угроза в тексте -> `REJECT`, `TOXIC_THREAT_DIRECT`.
- T2: Косвенная угроза -> `REVIEW`, `TOXIC_THREAT_INDIRECT`.
- T3: Hate speech -> `REJECT`, `TOXIC_HATE`.
- T4: Мат без адресата -> `REVIEW`, `TOXIC_INSULT`.
- T5: Негатив о сервисе без оскорблений -> `APPROVE`.
- T6: OCR-токсичность при confidence >= 0.65 -> `REJECT/REVIEW` + `TOXIC_IMAGE_TEXT`.
- T7: OCR confidence < 0.65 -> `REVIEW`, `LOW_OCR_CONFIDENCE`.
- T8: Конфликт image threat + illegal incitement -> primary `ILLEGAL_INCITEMENT`, secondary includes toxic codes.
- T9: Mixed alphabet bypass -> должно детектироваться и не уходить в `APPROVE`.
- T10: FP-контроль: "убийственный сервис" (метафора) -> `REVIEW` или `APPROVE` по контексту, не `REJECT`.
- T11: FN-контроль: "тебя найдут" -> не ниже `REVIEW`.
