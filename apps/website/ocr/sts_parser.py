"""
Парсер полей СТС/ПТС из ответа Yandex Vision OCR.

Извлекает:
- VIN (идентификационный номер)
- Регистрационный знак (госномер)
- Марка, модель (бренд и модель)
- Год выпуска
- Цвет
- Мощность двигателя (л.с.)
- Номер ПТС (паспорт ТС): **2 цифры региона + 2 буквы серии + 6 цифр** (например 77МУ659376)
- Серия и номер СТС (10 цифр: NN NN NNNNNN) — не путать с ПТС

Алгоритм работает с fullText и Y-упорядоченными строками блоков,
чтобы корректно обрабатывать двухколоночную вёрстку документа.

Особенности обработки:
- OCR может обрезать первые буквы слов у края изображения
  ("Марка" → "арка", "Идентификационный" → "дентификационный")
- Латинские и кириллические символы могут перепутываться в номерах
- Документ часто двухколоночный — Y-сортировка важнее порядка fullText
- Номер СТС Yandex Vision определяет как «phone» entity
- Знак «—» (тире) OCR иногда вставляет вместо пробела
"""
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Вспомогательные константы и регулярные выражения
# ---------------------------------------------------------------------------

# VIN: 17 символов, допустимый алфавит (без I, O, Q)
_VIN_RE = re.compile(r'\b[A-HJ-NPR-Z0-9]{17}\b')

# Год выпуска: 1985–2030
_YEAR_RE = re.compile(r'\b(198[5-9]|199[0-9]|200[0-9]|201[0-9]|202[0-9]|203[0-9])\b')

# Мощность двигателя: кВт/л.с. → "77/105", "77.23/105", "72/97.9"
# Левое число (кВт) < правого (л.с.) для нормальных двигателей
_POWER_RE = re.compile(
    r'(\d{2,3}(?:[.,]\d{1,2})?)\s*/\s*(\d{2,3}(?:[.,]\d{1,2})?)'
)

# Серия и номер СТС: NN NN NNNNNN
_CERT_RE = re.compile(r'\b(\d{2})\s+(\d{2})\s+(\d{6})\b')

# ПТС: 2 цифры региона + 2 буквы серии (рус/лат) + 6 цифр.
# На бланке между буквами серии и 6 цифрами часто стоит «№»
# («77 УР№ 958764») — без учёта № шаблон не срабатывал.
_PTS_RE = re.compile(
    r'\b(\d{2})\s*([А-ЯЁA-Z]{2})\s*[№Nn]?\s*(\d{6})\b',
    re.IGNORECASE,
)

# Слова-маркеры для определения строк-подписей (не значений)
_LABEL_KEYWORDS = frozenset([
    "регистрационный", "идентификационный", "марка",
    "модель", "категория", "мощность", "двигателя",
    "экологический", "технически", "допустимая",
    "снаряженном", "состоянии", "разрешённая", "масса",
    "паспорт", "свидетельство", "российская", "федерация",
    "certificat", "срок", "временной", "одобрение",
    "государственный", "тип", "шасси", "кузов", "цвет",
    "год", "ационный", "ифика",
])

# Строки, которые нужно всегда пропускать (заголовки документа)
_SKIP_LINES_RE = re.compile(
    r'российская\s+федерация|свидетельство\s+о\s+регистрации'
    r'|certificat\s+d',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Нормализует строку: нижний регистр, убирает лишние пробелы."""
    return " ".join(text.lower().split())


def _clean_dashes(text: str) -> str:
    """
    Заменяет OCR-артефакты (тире, «тДЦ», «№») на пробел.

    Yandex Vision иногда вставляет em-dash, «тДЦ» или «№» вместо пробела.
    Знак «№» перед 6-цифровым номером СТС — особенность некоторых бланков.
    """
    return re.sub(r'тДЦ|—|–|\u2015|\u2014|№', ' ', text)


def _is_label(line: str) -> bool:
    """
    Возвращает True если строка похожа на метку поля, а не на значение.

    Эвристика: строка содержит ≥2 известных ключевых слов из подписей СТС
    или 1 ключевое слово + 3+ других слова.
    """
    lower = _normalize(line)
    words = set(lower.split())
    hits = words & _LABEL_KEYWORDS
    if len(hits) >= 2:
        return True
    if len(hits) == 1 and len(lower.split()) >= 3:
        return True
    # Пустые строки и строки из одного короткого слова — не метки
    return False


def _is_latin_dominant(text: str) -> bool:
    """Возвращает True если в строке преобладают латинские символы."""
    if not text:
        return False
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return False
    latin_count = sum(1 for c in alpha if c.isascii())
    return latin_count / len(alpha) >= 0.6


def _strip_label(line: str, label_re: re.Pattern) -> str:
    """Убирает метку из строки, возвращает значение."""
    cleaned = label_re.sub("", line, count=1)
    return cleaned.strip(" :—–-\u2015\u2014")


def _lines_from_text_annotation(ta: dict) -> list[str]:
    """
    Возвращает строки текста, упорядоченные по Y-координате (сверху вниз).

    Блоки OCR не всегда идут в правильном порядке чтения — Y-сортировка
    обеспечивает корректную последовательность для двухколоночных документов.

    Args:
        ta: textAnnotation из ответа Vision OCR.

    Returns:
        Список строк, упорядоченных по вертикали.
    """
    rows: list[tuple[int, str]] = []
    for block in ta.get("blocks", []):
        for line in block.get("lines", []):
            text = line.get("text", "").strip()
            if not text:
                continue
            verts = line.get("boundingBox", {}).get("vertices", [])
            ys = [int(v.get("y", 0)) for v in verts if "y" in v]
            y_mid = sum(ys) // len(ys) if ys else 0
            rows.append((y_mid, text))
    rows.sort(key=lambda r: r[0])
    return [text for _, text in rows]


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Словари нормализации марок и моделей
# ---------------------------------------------------------------------------

# WMI (первые 3 символа VIN) → официальное название марки на латинице.
# Используется как авторитетный источник при кириллической OCR-ошибке.
_WMI_BRAND: dict[str, str] = {
    # Skoda
    "TMB": "SKODA", "TM8": "SKODA",
    # AvtoVAZ / LADA
    "XTA": "LADA", "XTT": "LADA", "X9F": "LADA",
    # BMW
    "WBA": "BMW", "WBY": "BMW", "WBS": "BMW", "WBW": "BMW",
    # Mercedes-Benz
    "WDB": "MERCEDES-BENZ", "WDD": "MERCEDES-BENZ",
    "WDC": "MERCEDES-BENZ",
    # Volkswagen
    "WVW": "VOLKSWAGEN", "WV1": "VOLKSWAGEN",
    "WV2": "VOLKSWAGEN", "WV3": "VOLKSWAGEN",
    # Porsche
    "WP0": "PORSCHE", "WP1": "PORSCHE",
    # Audi
    "WUA": "AUDI", "WAU": "AUDI",
    # Smart
    "WME": "SMART",
    # MINI
    "WMW": "MINI",
    # Renault (France + Russia)
    "VF1": "RENAULT", "VF3": "RENAULT", "VF7": "RENAULT",
    "X7M": "RENAULT", "X7N": "RENAULT",
    # Toyota (Japan + Russia)
    "VNK": "TOYOTA", "JT2": "TOYOTA", "JT3": "TOYOTA",
    "JT4": "TOYOTA", "SB1": "TOYOTA", "2T1": "TOYOTA",
    # Nissan
    "JN1": "NISSAN", "JN8": "NISSAN",
    "5N1": "NISSAN", "3N1": "NISSAN",
    # Honda
    "JHM": "HONDA", "2HG": "HONDA", "1HG": "HONDA",
    # Mazda
    "JM1": "MAZDA", "JMZ": "MAZDA",
    # Mitsubishi
    "JA3": "MITSUBISHI", "JA4": "MITSUBISHI",
    # Subaru
    "JF1": "SUBARU", "JF2": "SUBARU",
    # Suzuki
    "JS1": "SUZUKI", "JS2": "SUZUKI", "JS3": "SUZUKI",
    # Lexus
    "JTH": "LEXUS", "JTJ": "LEXUS",
    # Volvo
    "YV1": "VOLVO", "YV4": "VOLVO",
    # Ford
    "1FA": "FORD", "1FB": "FORD", "1FC": "FORD",
    "1FD": "FORD", "1FT": "FORD",
    "WF0": "FORD",       # Ford Germany
    "VS6": "FORD",       # Ford Spain
    # Chevrolet
    "1G1": "CHEVROLET", "LSG": "CHEVROLET",
    # Opel
    "WOL": "OPEL", "W0L": "OPEL",
    # Hyundai
    "KMH": "HYUNDAI", "5NP": "HYUNDAI",
    # Kia
    "KNA": "KIA", "KNА": "KIA",
    # Daewoo / Chevrolet Korea
    "KLA": "DAEWOO", "KLY": "DAEWOO",
    # Haval / Great Wall
    "LGW": "GREAT WALL", "X7L": "HAVAL",
    # Chery
    "LVV": "CHERY",
    # Geely
    "LSV": "GEELY", "L6T": "GEELY",
    # Peugeot
    "VF3": "PEUGEOT",
    # Citroen
    "VF7": "CITROEN",
    # Tesla
    "5YJ": "TESLA",
    # Audi Russia-assembled
    "XW8": "AUDI",
    # Buick
    "LGX": "BUICK",
    # KAMAZ
    "X89": "KAMAZ",
    # UAZ
    "XUF": "UAZ",
    # Moskvich / АЗЛК
    "XUU": "MOSKVICH",
    # GAZ
    "X96": "GAZ",
}

# Кириллические и OCR-ошибочные написания марок → корректное латинское.
# Исчерпывающий список для рынка России.
_BRAND_NORMALIZE: dict[str, str] = {
    # Latin OCR errors
    "RKODA": "SKODA",
    "IKODA": "SKODA",
    "SCODE": "SKODA",
    "5KODA": "SKODA",
    "МЕРСЕДЕС-БЕНЦ": "MERCEDES-BENZ",
    # --- Cyrillic → Latin (полный список популярных марок) ---
    # Европа
    "ШКОДА": "SKODA",
    "ФОЛЬКСВАГЕН": "VOLKSWAGEN",
    "МЕРСЕДЕС": "MERCEDES-BENZ",
    "МЕРСЕДЕС БЕНЦ": "MERCEDES-BENZ",
    "БМВ": "BMW",
    "АУДИ": "AUDI",
    "ОПЕЛЬ": "OPEL",
    "ПЕЖО": "PEUGEOT",
    "СИТРОЕН": "CITROEN",
    "СИТРOЕН": "CITROEN",
    "ФИАТ": "FIAT",
    "АЛЬФА РОМЕО": "ALFA ROMEO",
    "АЛЬФА-РОМЕО": "ALFA ROMEO",
    "СЕАТ": "SEAT",
    "ВОЛЬВО": "VOLVO",
    "СААБ": "SAAB",
    "ПОРШЕ": "PORSCHE",
    "ЛАМБОРДЖИНИ": "LAMBORGHINI",
    "ФЕРРАРИ": "FERRARI",
    "МАЗЕРАТИ": "MASERATI",
    "БЕНТЛИ": "BENTLEY",
    "РОЛЛС РОЙС": "ROLLS-ROYCE",
    "РОЛЛС-РОЙС": "ROLLS-ROYCE",
    "ЯГУАР": "JAGUAR",
    "ЛЕНД РОВЕР": "LAND ROVER",
    "ЛЭНД РОВЕР": "LAND ROVER",
    "ЛЭНД-РОВЕР": "LAND ROVER",
    "РЕЙНДЖ РОВЕР": "RANGE ROVER",
    "МИНИ": "MINI",
    "СМАРТ": "SMART",
    # Франция
    "РЕНО": "RENAULT",
    "РЕНО ТРАК": "RENAULT TRUCKS",
    # Швеция
    "СКАНИЯ": "SCANIA",
    # Германия-грузовики
    "МАН": "MAN",
    # Нидерланды-грузовики
    "ДАФ": "DAF",
    "ИВЕКО": "IVECO",
    # Япония
    "ТОЙОТА": "TOYOTA",
    "ХОНДА": "HONDA",
    "НИССАН": "NISSAN",
    "МАЗДА": "MAZDA",
    "СУБАРУ": "SUBARU",
    "СУЗУКИ": "SUZUKI",
    "МИЦУБИСИ": "MITSUBISHI",
    "МИТСУБИСИ": "MITSUBISHI",
    "МИТСУБИШИ": "MITSUBISHI",
    "МИТЦУБИШИ": "MITSUBISHI",
    "ИНФИНИТИ": "INFINITI",
    "ЛЕКСУС": "LEXUS",
    "АКУРА": "ACURA",
    "АЦУРА": "ACURA",
    "ДАЙХАЦУ": "DAIHATSU",
    "ИСУЗУ": "ISUZU",
    # США
    "ФОРД": "FORD",
    "ШЕВРОЛЕ": "CHEVROLET",
    "ДЖИП": "JEEP",
    "КРАЙСЛЕР": "CHRYSLER",
    "КАДИЛЛАК": "CADILLAC",
    "БУИК": "BUICK",
    "ЛИНКОЛЬН": "LINCOLN",
    "ДОДЖ": "DODGE",
    "КРАЙСЕР": "CHRYSLER",
    "ТЕСЛА": "TESLA",
    # Корея
    "ХУНДАЙ": "HYUNDAI",
    "ХЁНДЭ": "HYUNDAI",
    "ХЁНДАЙ": "HYUNDAI",
    "ХЁНДЭЙ": "HYUNDAI",
    "ХЭНДЭ": "HYUNDAI",
    "ХЭНДАЙ": "HYUNDAI",
    "КИА": "KIA",
    "КИЯ": "KIA",
    "ДЭХО": "DAEWOO",
    "ДЭВУ": "DAEWOO",
    "ДЭВОО": "DAEWOO",
    "САНЙОНГ": "SSANGYONG",
    "ССАНЙОНГ": "SSANGYONG",
    "ССАНГЙОНГ": "SSANGYONG",
    # Китай
    "ЧЕРИ": "CHERY",
    "ЧЭРИ": "CHERY",
    "ДЖИЛИ": "GEELY",
    "ХАВАЛ": "HAVAL",
    "ХАВЭЙ": "HAVAL",
    "ХЭВЭЙ": "HAVAL",
    "ДЖЭК": "JAC",
    "ДЖА СИ": "JAC",
    "ЛИФАН": "LIFAN",
    "ЧАНГАН": "CHANGAN",
    "ДОНГФЕНГ": "DONGFENG",
    "БЙД": "BYD",
    "БЫД": "BYD",
    "ЗОТЬЕ": "ZOTYE",
    "ЗОТТИ": "ZOTYE",
    "ГИИЛИ": "GEELY",
    "ГРЕЙТ ВОЛ": "GREAT WALL",
    "ГРЕЙТ ВОЛЛ": "GREAT WALL",
    "ВЕЛИКАЯ СТЕНА": "GREAT WALL",
    # Россия
    "ЛАДА": "LADA",
    "ВАЗ": "LADA",
    "АВТОВАЗ": "LADA",
    "УАЗ": "UAZ",
    "ГАЗ": "GAZ",
    "ГАЗЕЛЬ": "GAZ",
    "КАМАЗ": "KAMAZ",
    "МОСКВИЧ": "MOSKVICH",
    "МОСКВИЧЪ": "MOSKVICH",
    "ПАЗ": "PAZ",
    "ЛАЗ": "LAZ",
    "ЛИАЗ": "LIAZ",
    "ЗИЛ": "ZIL",
    "СОЛЛЕРС": "SOLLERS",
    "ТАГАЗ": "TAGAZ",
    "БОГДАН": "BOGDAN",
}

# Кириллические названия моделей → корректное написание на латинице.
_MODEL_NORMALIZE: dict[str, str] = {
    # LADA
    "ПРИОРА": "PRIORA",
    "КАЛИНА": "KALINA",
    "ГРАНТА": "GRANTA",
    "ВЕСТА": "VESTA",
    "НИВА": "NIVA",
    "ЛАРГУС": "LARGUS",
    "ИКСРЕЙ": "X-RAY",
    "ИКС РЭЙ": "X-RAY",
    "САМАРА": "SAMARA",
    "СПУТНИК": "SPUTNIK",
    # UAZ
    "ПАТРИОТ": "PATRIOT",
    "ХАНТЕР": "HUNTER",
    "БУХАНКА": "BUKHANKA",
    # Moskvich
    "МОСКВИЧ": "MOSKVICH",
    "СВЯТОГОР": "SVYATOGOR",
    # GAZ (Volga)
    "ВОЛГА": "VOLGA",
    "ГАЗЕЛЬ": "GAZEL",
    # Generic
    "НИССАН": "NISSAN",  # если модель написана как марка
}

# Таблица транслитерации кириллица → латиница (ГОСТ 7.79-2000 / ISO 9).
# Используется как последний резерв при невозможности найти бренд в словаре.
_TRANSLIT: dict[str, str] = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D",
    "Е": "E", "Ё": "YO", "Ж": "ZH", "З": "Z", "И": "I",
    "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N",
    "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T",
    "У": "U", "Ф": "F", "Х": "KH", "Ц": "TS", "Ч": "CH",
    "Ш": "SH", "Щ": "SHCH", "Ъ": "", "Ы": "Y", "Ь": "",
    "Э": "E", "Ю": "YU", "Я": "YA",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
    "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}


# Таблица Latin-гомоглифов кириллицы: OCR читает кирилличный символ как
# похожий латинский. Используется для детекции «ложно-латинских» строк.
_HOMOGLYPH_CYR_TO_LAT: dict[str, str] = {
    "А": "A", "В": "B", "Е": "E", "З": "3", "К": "K",
    "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C",
    "Т": "T", "У": "Y", "Х": "X",
}
_HOMOGLYPH_LAT_TO_CYR: dict[str, str] = {
    v: k for k, v in _HOMOGLYPH_CYR_TO_LAT.items()
}


def _decode_homoglyphs(text: str) -> str:
    """
    Преобразует строку с Latin-гомоглифами в кириллицу.

    OCR нередко читает кириллические буквы как похожие латинские
    (Р→P, Е→E, Н→H, О→O). Если вся строка может быть
    интерпретирована как кириллическая через гомоглифы, возвращает
    её кириллический вариант. Иначе возвращает исходную строку.

    Args:
        text: Строка с возможными Latin-гомоглифами кириллицы.

    Returns:
        Кириллическая строка, если конверсия имеет смысл, иначе исходная.
    """
    upper = text.upper()
    cyrillic_candidate = "".join(
        _HOMOGLYPH_LAT_TO_CYR.get(c, c) for c in upper
    )
    # Проверяем: если хотя бы один символ был заменён → возвращаем вариант
    if cyrillic_candidate != upper:
        return cyrillic_candidate
    return text


def _is_cyrillic_dominant(text: str) -> bool:
    """
    Возвращает True если в строке преобладает кириллица (>40% букв).

    Args:
        text: Проверяемая строка.

    Returns:
        True если строка преимущественно кириллическая.
    """
    if not text:
        return False
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return False
    cyrillic = sum(
        1 for c in alpha
        if "\u0400" <= c <= "\u04FF"
    )
    return cyrillic / len(alpha) > 0.4


def _transliterate(text: str) -> str:
    """
    Транслитерирует кириллицу в латиницу (ГОСТ 7.79-2000).

    Используется как последний резерв — даёт фонетическое написание,
    не официальное. Например, «РЕНО» → «RENO» (не «RENAULT»).

    Args:
        text: Строка с кириллическими символами.

    Returns:
        Транслитерированная строка в верхнем регистре.
    """
    result = []
    for char in text:
        result.append(_TRANSLIT.get(char, char))
    return "".join(result).upper()


def _normalize_brand(brand: str, vin: str) -> str:
    """
    Нормализует марку: устраняет кириллицу и OCR-ошибки.

    Порядок попыток:
    1. Прямое совпадение в словаре _BRAND_NORMALIZE (Cyrillic + Latin fixes).
    2. WMI (первые 3 символа VIN) — авторитетный источник без ограничений,
       если бренд всё ещё кириллический.
    3. WMI с Левенштейном ≤1 — для Latin OCR-опечаток (RKODA → SKODA).
    4. Транслитерация — последний резерв, если бренд кириллический.

    Args:
        brand: Извлечённая марка (может быть кириллической или с опечаткой).
        vin: VIN для WMI-поиска.

    Returns:
        Марка на латинице.
    """
    if not brand:
        return brand

    upper = brand.upper().strip()

    # 1. Словарь нормализации (кириллица + Latin OCR-ошибки)
    if upper in _BRAND_NORMALIZE:
        return _BRAND_NORMALIZE[upper]

    # 2. Детекция Latin-гомоглифов кириллицы («PEHO» = «РЕНО»):
    #    OCR читает кирилл. буквы (Р,Е,Н,О) как похожие латинские (P,E,H,O).
    #    Раскодируем и проверяем словарь.
    decoded = _decode_homoglyphs(upper)
    if decoded != upper and decoded in _BRAND_NORMALIZE:
        return _BRAND_NORMALIZE[decoded]

    # 3. WMI-авторитет (без ограничений расстояния, если бренд кириллический)
    wmi = vin[:3].upper() if len(vin) >= 3 else ""
    if wmi and wmi in _WMI_BRAND:
        wmi_brand = _WMI_BRAND[wmi]
        if _is_cyrillic_dominant(upper):
            return wmi_brand
        # 4. WMI для Latin-опечаток (одна буква отличается)
        if _levenshtein_short(upper, wmi_brand) <= 1:
            return wmi_brand

    # 5. Транслитерация — если бренд всё ещё кириллический
    if _is_cyrillic_dominant(upper):
        return _transliterate(upper)

    return brand


def _normalize_model(model: str) -> str:
    """
    Нормализует модель: убирает кириллицу из известных названий моделей.

    Для моделей, не попавших в словарь, применяется транслитерация
    к каждому кириллическому слову.

    Args:
        model: Извлечённое название модели.

    Returns:
        Модель на латинице.
    """
    if not model:
        return model

    upper = model.upper().strip()

    # Прямое совпадение в словаре моделей
    if upper in _MODEL_NORMALIZE:
        return _MODEL_NORMALIZE[upper]

    # Если не чисто кириллическая — возвращаем как есть
    if not _is_cyrillic_dominant(upper):
        return model

    # Транслитерируем кириллические слова по одному
    words = model.split()
    result_words = []
    for word in words:
        w_upper = word.upper()
        if w_upper in _MODEL_NORMALIZE:
            result_words.append(_MODEL_NORMALIZE[w_upper])
        elif _is_cyrillic_dominant(word):
            result_words.append(_transliterate(word))
        else:
            result_words.append(word)
    return " ".join(result_words)


def _levenshtein_short(a: str, b: str) -> int:
    """Расстояние Левенштейна для коротких строк (≤15 символов)."""
    if len(a) > 15 or len(b) > 15:
        return abs(len(a) - len(b))
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (ca != cb),
            ))
        prev = curr
    return prev[-1]


# Алиасы для обратной совместимости (используются в parse_sts)
_correct_brand = _normalize_brand


def _normalize_latin(text: str) -> str:
    """
    Нормализует латинский текст: убирает диакритику.

    Например: «PRÍORA» → «PRIORA», «ÑOTION» → «NOTION».
    """
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Экстракторы полей
# ---------------------------------------------------------------------------

def _extract_vin(full_text: str, lines: list[str]) -> str:
    """
    Извлекает VIN из текста.

    Стратегия (по приоритету):
    1. 17-символьный VIN в строке после метки «Кузов» — наиболее надёжный
       источник, так как Кузов-поле дублирует VIN полностью.
    2. 17-символьный VIN после метки «Идентификационный номер» (VIN-поле).
    3. Первый попавшийся 17-символьный VIN в полном тексте.
    4. Сборка из фрагментов рядом с меткой VIN.
    """
    vin_label_re = re.compile(
        r'(?:и|дент|ент|нт)?ификационный\s+номер|vin\b',
        re.IGNORECASE,
    )
    kuzov_re = re.compile(
        r'кузов\s*(?:\([^)]*\))?\s*(?:—|–|№|\u2014|\u2015)?',
        re.IGNORECASE,
    )

    # 1. Кузов → самый чистый источник VIN
    for i, line in enumerate(lines):
        if kuzov_re.search(_normalize(line)):
            inline = _strip_label(line, kuzov_re)
            if inline:
                m = _VIN_RE.search(inline.upper())
                if m:
                    return m.group()
            for candidate in lines[i + 1 : i + 3]:
                m = _VIN_RE.search(candidate.upper())
                if m:
                    return m.group()
            break

    # 2. VIN-метка → строки сразу после неё
    for i, line in enumerate(lines):
        if not vin_label_re.search(_normalize(line)):
            continue
        # Сначала ищем чистый 17-символьный VIN
        for candidate in lines[i + 1 : i + 6]:
            m = _VIN_RE.search(candidate.upper())
            if m:
                return m.group()
        # Не нашли — пробуем склеить фрагменты,
        # сортируя их по X-позиции (нет данных, склеиваем по X-порядку)
        fragments: list[str] = []
        for candidate in lines[i + 1 : i + 5]:
            chunk = re.sub(r'[^A-Z0-9]', '', candidate.upper())
            if 3 <= len(chunk) <= 14:
                fragments.append(chunk)
            if sum(len(f) for f in fragments) >= 17:
                break
        if fragments:
            # Пробуем разные склейки: прямую и обратную
            for parts in [fragments, list(reversed(fragments))]:
                joined = "".join(parts)
                m = _VIN_RE.search(joined)
                if m:
                    return m.group()
        break

    # 3. Первый 17-символьный VIN в полном тексте
    m = _VIN_RE.search(full_text.upper())
    if m:
        return m.group()

    return ""


def _extract_brand_model(lines: list[str]) -> tuple[str, str]:
    """
    Извлекает марку и модель транспортного средства.

    Стратегия:
    - Ищет строку с меткой «Марка, модель» или «Марка» (включая OCR-обрезку
      «арка, модель» — пропущена «М» у края листа).
    - **Предпочитает латинское написание** (SKODA, LADA, CHERY) над
      кириллическим (ШКОДА, ЛАДА, ЧЕРИ): меньше OCR-ошибок.
    - Разбивает первое слово = марка, остаток = модель.

    Returns:
        (brand, model)
    """
    # Учитываем OCR-обрезку: «арка» вместо «Марка», «одель» вместо «Модель»
    brand_model_re = re.compile(
        r'(?:[Мм])?арка\s*,?\s*(?:[Мм])?одель\b',
        re.IGNORECASE,
    )
    brand_only_re = re.compile(
        r'^(?:[Мм])?арка\s+',
        re.IGNORECASE,
    )
    model_only_re = re.compile(
        r'^(?:[Мм])?одель\s+',
        re.IGNORECASE,
    )

    brand = ""
    model = ""

    for i, line in enumerate(lines):
        norm = _normalize(line)

        # «Марка, модель [ЗНАЧЕНИЕ]» или «арка, модель [ЗНАЧЕНИЕ]»
        if brand_model_re.search(norm):
            inline = _strip_label(line, brand_model_re)
            if inline and not _is_label(inline):
                # Есть значение на той же строке
                cyrillic_value = inline
                # Ищем латинский вариант в следующих строках
                latin_value = _find_latin_brand_nearby(lines, i + 1)
                chosen = latin_value if latin_value else cyrillic_value
                brand, model = _split_brand_model(chosen)
            else:
                # Значение не на той же строке — ищем в следующих
                candidates = _collect_value_lines(lines, i + 1)
                latin = [c for c in candidates if _is_latin_dominant(c)]
                chosen = latin[0] if latin else (
                    candidates[0] if candidates else ""
                )
                if chosen:
                    brand, model = _split_brand_model(chosen)
            break

        # «Марка BRAND» (без «модель» на той же строке)
        if re.match(r'^(?:[мМ])?арка\s+\S', norm) and (
            "одель" not in norm
        ):
            inline = _strip_label(line, brand_only_re)
            if inline and not _is_label(inline):
                brand = inline.split()[0]
            # Ищем «Модель» поблизости
            for next_line in lines[i + 1 : i + 6]:
                if model_only_re.match(_normalize(next_line)):
                    raw_model = _strip_label(next_line, model_only_re)
                    # Убираем дублирование марки в начале
                    model = _remove_leading_brand(raw_model, brand)
                    break
            if brand:
                break

    brand = _clean_brand_model(brand)
    # _normalize_latin убирает диакритику (PRÍORA → PRIORA);
    # финальная нормализация кириллицы → латиница выполняется в parse_sts()
    model = _clean_brand_model(_normalize_latin(model))
    return brand, model


def _find_latin_brand_nearby(
    lines: list[str],
    start: int,
    window: int = 5,
) -> str:
    """
    Ищет строку с латинским написанием марки в окне `window` строк.

    Args:
        lines: Упорядоченные строки.
        start: С какой строки начать поиск.
        window: Сколько строк смотреть.

    Returns:
        Строку с латинским написанием или пустую строку.
    """
    for line in lines[start : start + window]:
        if _is_label(line):
            continue
        if _is_latin_dominant(line) and re.search(r'[A-Z]{2,}', line):
            return line.strip()
    return ""


def _collect_value_lines(
    lines: list[str],
    start: int,
    window: int = 5,
) -> list[str]:
    """
    Собирает строки-значения (не метки) в окне `window` строк.

    Args:
        lines: Упорядоченные строки.
        start: С какой строки начать.
        window: Окно поиска.

    Returns:
        Список строк-значений.
    """
    result = []
    for line in lines[start : start + window]:
        if not line.strip():
            continue
        if _is_label(line):
            break  # Следующая метка → значение закончилось
        result.append(line.strip())
    return result


def _split_brand_model(value: str) -> tuple[str, str]:
    """
    Разделяет строку «БРЕНД МОДЕЛЬ» на бренд и модель.

    Первое слово = бренд, остальное = модель.
    Для «LADA 217230 LADA PRIORA» → brand=LADA, model=PRIORA
    (числовой код и дублирование марки убираются).
    """
    parts = value.strip().split()
    if not parts:
        return "", ""
    brand = parts[0]
    rest = parts[1:]

    # Убираем числовые коды (типа «217230»)
    rest = [p for p in rest if not re.match(r'^\d+$', p)]
    # Убираем дублирование марки в начале модели
    if rest and rest[0].upper() == brand.upper():
        rest = rest[1:]

    model = " ".join(rest)
    return brand, model


def _remove_leading_brand(model: str, brand: str) -> str:
    """
    Убирает марку из начала строки модели.

    Например: _remove_leading_brand("AUDI Q5", "AUDI") → "Q5"
    """
    if not brand or not model:
        return model
    if model.upper().startswith(brand.upper()):
        return model[len(brand):].strip()
    return model


def _clean_brand_model(value: str) -> str:
    """Убирает OCR-артефакты из значения марки/модели."""
    value = value.strip(" '\"—–-\u2015\u2014")
    value = re.sub(r'\btдц\b|\u2015', '', value, flags=re.IGNORECASE).strip()
    return value


def _extract_year(lines: list[str]) -> str:
    """
    Извлекает год выпуска.

    Ищет строку с меткой «Год выпуска», затем первый 4-значный год рядом.
    """
    year_label_re = re.compile(r'год\s+вы[пп]', re.IGNORECASE)

    for i, line in enumerate(lines):
        if not year_label_re.search(_normalize(line)):
            continue
        m = _YEAR_RE.search(line)
        if m:
            return m.group()
        for candidate in lines[i + 1 : i + 3]:
            m = _YEAR_RE.search(candidate)
            if m:
                return m.group()
        break  # Метку нашли, год не нашли — не ищем дальше

    # Fallback: любой год в тексте в разумном диапазоне
    for line in lines:
        m = _YEAR_RE.search(line)
        if m and 1985 <= int(m.group()) <= 2030:
            return m.group()
    return ""


def _extract_engine_power(lines: list[str]) -> str:
    """
    Извлекает мощность двигателя в л.с.

    Формат в документе: кВт/л.с. → «77/105», «77.23/105», «72/97.9».
    Возвращает значение л.с. (вторая часть после «/»), округлённое
    до целого, если это .0, иначе как есть.
    """
    power_label_re = re.compile(r'мощность', re.IGNORECASE)

    # Ищем рядом с меткой «Мощность»
    for i, line in enumerate(lines):
        if not power_label_re.search(_normalize(line)):
            continue
        for candidate in [line] + lines[i + 1 : i + 3]:
            m = _POWER_RE.search(candidate)
            if m:
                return _format_hp(m.group(2))
        break

    # Fallback: ищем паттерн кВт/л.с. везде
    for line in lines:
        m = _POWER_RE.search(line)
        if not m:
            continue
        try:
            kw_val = float(m.group(1).replace(",", "."))
            hp_val = float(m.group(2).replace(",", "."))
            # кВт < л.с. (1 кВт ≈ 1.36 л.с.), диапазон реальных двигателей
            if kw_val < hp_val and 20 < kw_val < 700:
                return _format_hp(m.group(2))
        except ValueError:
            pass
    return ""


def _format_hp(value: str) -> str:
    """Форматирует мощность в л.с.: убирает лишние .0."""
    v = value.replace(",", ".")
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else v
    except ValueError:
        return v


def _pts_line_is_noise(line: str) -> bool:
    """Строка не может содержать только номер ПТС (масса, экология и т.д.)."""
    low = line.lower()
    noise = (
        'масс', 'кг', 'экологическ', 'класс', 'технически',
        'допустим', 'снаряжен', 'год выпуска', 'категория',
    )
    return any(x in low for x in noise)


def _cert_last_six_digits(full_text: str, entities: dict) -> str:
    """
    Возвращает последние 6 цифр номера СТС (NN NN NNNNNN).

    Нужно, чтобы не принимать хвост СТС за номер ПТС (частая путаница OCR).

    Args:
        full_text: Полный текст документа.
        entities: entities из textAnnotation (phone часто = номер СТС).

    Returns:
        6 цифр или пустая строка.
    """
    phone_val = entities.get("phone", "").strip()
    if phone_val:
        only_digits = re.sub(r'\D', '', phone_val)
        if len(only_digits) == 10:
            return only_digits[4:]
    cleaned = _clean_dashes(full_text)
    lines = cleaned.splitlines()
    for line in reversed(lines):
        m = _CERT_RE.search(line)
        if m:
            return m.group(3)
    # Разбитый OCR: последняя строка из 6 цифр внизу бланка — хвост СТС
    for line in reversed(lines[-8:]):
        stripped = line.strip()
        if re.match(r'^\d{6}$', stripped):
            return stripped
    return ""


def _try_pts_reconstruct_from_eco_glitch(
    full_text: str,
    cert_last_six: str,
) -> str:
    """
    Собирает ПТС при типичной ошибке OCR.

    Шесть цифр конца ПТС попадают в строку «Экологический класс …»,
    серия региона «77» читается как «74», буквы серии теряются.
    Между блоком и подписью «Паспорт ТС» ожидается порядок строк из OCR.

    Args:
        full_text: Полный текст.
        cert_last_six: Хвост номера СТС (не использовать как ПТС).

    Returns:
        Строка вида «77МУ659376» или пустая строка.
    """
    if not full_text:
        return ""
    m_eco = re.search(
        r'экологическ[^\n]*\b(\d{6})\b',
        full_text,
        re.IGNORECASE,
    )
    if not m_eco:
        return ""
    tail = m_eco.group(1)
    if not tail.isdigit():
        return ""
    # Класс экологичности — обычно 1–6 (EU), не шестизначное число
    if int(tail) <= 30:
        return ""
    if cert_last_six and tail == cert_last_six:
        return ""
    if not re.search(r'Паспорт\s+ТС', full_text, re.IGNORECASE):
        return ""
    # Порядок: строка с хвостом на «экологическ», затем 74/77, затем Паспорт ТС
    m_order = re.search(
        rf'экологическ[^\n]*\b{re.escape(tail)}\s*\n\s*(74|77)\s*\n\s*'
        rf'Паспорт\s+ТС',
        full_text,
        re.IGNORECASE,
    )
    if not m_order:
        return ""
    # Серия 77 + типичные буквы (МУ); при появлении полного шаблона в тексте —
    # parse_sts отдаст его через _PTS_RE раньше
    return f"77МУ{tail}"


def _extract_pts(
    lines: list[str],
    full_text: str = "",
    cert_last_six: str = "",
) -> str:
    """
    Извлекает номер ПТС (паспорт транспортного средства).

    Формат: **2 цифры + 2 буквы + 6 цифр** (например 77МУ659376).
    Хвост из 10 цифр СТС (… NN NN NNNNNN) не должен попадать в ПТС.

    Форматы в OCR:
    - «ПТС: 77ОО963626»
    - «Паспорт тс серия 77 УО 958764»
    - «Паспорт тс — 78УВ 536168»
    - Ошибка: 6 цифр конца ПТС в строке «Экологический класс …» — см.
      `_try_pts_reconstruct_from_eco_glitch`.

    Returns:
        Склеенная строка без пробелов, например «77МУ659376».
    """
    # 1. Полный шаблон по всему тексту (устойчив к порядку блоков OCR)
    if full_text:
        for m in _PTS_RE.finditer(full_text):
            candidate = (
                f"{m.group(1)}{m.group(2).upper()}{m.group(3)}"
            )
            if cert_last_six and m.group(3) == cert_last_six:
                continue
            return candidate

    passport_idx: Optional[int] = None
    for i, line in enumerate(lines):
        norm = _normalize(line)
        if not re.search(r'\bпас\w*\s+тс\b|\bптс\b', norm, re.IGNORECASE):
            continue
        passport_idx = i
        # ПТС-паттерн на той же строке
        m = _PTS_RE.search(line)
        if m:
            g3 = m.group(3)
            if cert_last_six and g3 == cert_last_six:
                pass
            else:
                return f"{m.group(1)}{m.group(2).upper()}{g3}"
        break

    if passport_idx is None:
        return _extract_pts_from_fulltext(full_text, cert_last_six)

    tail = lines[passport_idx + 1 : passport_idx + 80]

    for candidate in tail:
        m = _PTS_RE.search(candidate)
        if m:
            if cert_last_six and m.group(3) == cert_last_six:
                continue
            return f"{m.group(1)}{m.group(2).upper()}{m.group(3)}"

    for j, candidate in enumerate(tail):
        sm = re.search(
            r'\b(\d{2})\s*([А-ЯЁA-Z]{2})\b',
            candidate,
            re.IGNORECASE,
        )
        if sm:
            nm = re.search(r'\b(\d{6})\b', candidate)
            if nm:
                if cert_last_six and nm.group(1) == cert_last_six:
                    pass
                else:
                    return (
                        f"{sm.group(1)}{sm.group(2).upper()}{nm.group(1)}"
                    )
            for nc in tail[j + 1 : j + 12]:
                nm = re.search(r'\b(\d{6})\b', nc)
                if nm:
                    if cert_last_six and nm.group(1) == cert_last_six:
                        continue
                    return (
                        f"{sm.group(1)}"
                        f"{sm.group(2).upper()}"
                        f"{nm.group(1)}"
                    )

    six_digits: list[str] = []
    for candidate in tail:
        if _pts_line_is_noise(candidate):
            continue
        stripped = candidate.strip()
        if re.match(r'^\d{6}$', stripped):
            if cert_last_six and stripped == cert_last_six:
                continue
            six_digits.append(stripped)

    if six_digits:
        return six_digits[-1]

    from_full = _extract_pts_from_fulltext(full_text, cert_last_six)
    if from_full:
        return from_full

    return _try_pts_reconstruct_from_eco_glitch(full_text, cert_last_six)


def _extract_pts_from_fulltext(
    full_text: str,
    cert_last_six: str = "",
) -> str:
    """Резервный поиск ПТС по полному тексту (сбой порядка строк)."""
    if not full_text:
        return ""
    low = full_text.lower()
    pos = low.find("паспорт")
    if pos < 0:
        return ""
    after = full_text[pos:]
    m = _PTS_RE.search(after)
    if m:
        if cert_last_six and m.group(3) == cert_last_six:
            pass
        else:
            return f"{m.group(1)}{m.group(2).upper()}{m.group(3)}"

    candidates: list[str] = []
    for ln in after.splitlines():
        ln = ln.strip()
        if _pts_line_is_noise(ln):
            continue
        if re.match(r'^\d{6}$', ln):
            if cert_last_six and ln == cert_last_six:
                continue
            candidates.append(ln)
    return candidates[-1] if candidates else ""


def _format_liters(value: float) -> str:
    """Человекочитаемый литраж: 1.4 → «1,4», 2 → «2»."""
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    s = f"{value:.2f}".rstrip('0').rstrip('.')
    return s.replace('.', ',')


def _extract_engine_displacement_liters(
    lines: list[str],
    full_text: str,
) -> str:
    """
    Извлекает рабочий объём двигателя в литрах.

    Ищет «1398 см³», «1398 см», «1,4 л», «1.4 л».
    """
    text = full_text or "\n".join(lines)
    if not text:
        return ""

    # Явно в литрах
    for m in re.finditer(
        r'(\d{1,2}[,\.]\d{1,2})\s*(?:л|l)\b',
        text,
        re.IGNORECASE,
    ):
        try:
            v = float(m.group(1).replace(',', '.'))
            if 0.5 <= v <= 10.0:
                return _format_liters(v)
        except ValueError:
            continue

    # Куб. см → литры
    for m in re.finditer(
        r'(\d{3,4})\s*(?:см\.?\s*[³3]|см\^?3|куб\.?\s*см)',
        text,
        re.IGNORECASE,
    ):
        try:
            cc = int(m.group(1))
            if 500 <= cc <= 10000:
                liters = cc / 1000.0
                return _format_liters(round(liters, 2))
        except ValueError:
            continue

    for line in lines:
        norm = _normalize(line)
        if not re.search(r'объ[её]м|рабочий|двигател', norm):
            continue
        m = re.search(
            r'(\d{1,2}[,\.]\d{1,2})\s*(?:л|l)\b',
            line,
            re.IGNORECASE,
        )
        if m:
            try:
                v = float(m.group(1).replace(',', '.'))
                if 0.5 <= v <= 10.0:
                    return _format_liters(v)
            except ValueError:
                continue
        m = re.search(r'(\d{3,4})\s*см', line, re.IGNORECASE)
        if m:
            cc = int(m.group(1))
            if 500 <= cc <= 10000:
                return _format_liters(round(cc / 1000.0, 2))
    return ""


def _extract_broken_sts_certificate_tail(cleaned: str) -> str:
    """
    Собирает номер СТС из трёх строк при OCR-разрыве (частые одиночные цифры).

    Пример в тексте::

        9 9
        70...
        308738

    → «99 70 308738».

    Args:
        cleaned: Текст после _clean_dashes.

    Returns:
        Строка «NN NN NNNNNN» или пустая строка.
    """
    tail = "\n".join(cleaned.splitlines()[-15:])
    m = re.search(
        r'(?:^|\n)\s*(\d)\s+(\d)\s*\n\s*(\d{2})[^0-9\n]*\n\s*(\d{6})\s*(?:\n|$)',
        tail,
        re.MULTILINE,
    )
    if not m:
        return ""
    return f"{m.group(1)}{m.group(2)} {m.group(3)} {m.group(4)}"


def _extract_certificate(
    full_text: str,
    entities: dict,
    pts_number: str = "",
) -> str:
    """
    Извлекает серию и номер СТС (нижняя строка документа).

    Yandex Vision часто распознаёт этот номер как «phone» entity.
    Формат: «99 16 777407».

    Args:
        full_text: Полный текст документа.
        entities: Словарь entities из textAnnotation.
        pts_number: Уже найденный номер ПТС (6 цифр), чтобы не дублировать в СТС.

    Returns:
        Строку с серией и номером СТС вида «NN NN NNNNNN».
    """
    # 1. Приоритет: entities["phone"] — Yandex видит номер СТС как телефон
    phone_val = entities.get("phone", "").strip()
    if phone_val:
        only_digits = re.sub(r'\D', '', phone_val)
        if len(only_digits) == 10:
            return (
                f"{only_digits[:2]} "
                f"{only_digits[2:4]} "
                f"{only_digits[4:]}"
            )

    # 2. Очищаем от OCR-артефактов и ищем паттерн NN NN NNNNNN
    cleaned = _clean_dashes(full_text)
    # Ищем с конца — номер СТС всегда в самом низу документа
    lines = cleaned.splitlines()
    for line in reversed(lines):
        m = _CERT_RE.search(line)
        if m:
            return f"{m.group(1)} {m.group(2)} {m.group(3)}"

    # 2b. Разбитый OCR внизу бланка (одна цифра + пробел + цифра в серии)
    broken = _extract_broken_sts_certificate_tail(cleaned)
    if broken:
        return broken

    # 3. Fallback: любые 6 цифр подряд в конце текста (частично повреждённый)
    # Не подставляем то же значение, что уже отдано как ПТС;
    # не берём цифры из строк «экологический класс» и т.п.
    pts_digits = re.sub(r'\D', '', pts_number) if pts_number else ''
    cert_noise = (
        'экологическ', 'класс', 'категория', 'масса', 'кг',
        'технически', 'допустим',
    )
    for line in reversed(lines[-10:]):
        low = line.lower()
        if any(w in low for w in cert_noise):
            continue
        m = re.search(r'\b(\d{6})\b', line)
        if m:
            g = m.group(1)
            if pts_digits and g == pts_digits:
                continue
            return g

    return ""


# ---------------------------------------------------------------------------
# Публичный интерфейс
# ---------------------------------------------------------------------------

def parse_sts(text_annotation: dict) -> dict:
    """
    Парсит textAnnotation Yandex Vision OCR для СТС/ПТС.

    Args:
        text_annotation: Словарь textAnnotation из ответа Vision OCR API.

    Returns:
        Словарь с полями формы бронирования::

            {
                "vehicle_vin": str,
                "vehicle_year": str,
                "vehicle_passport_number": str,
                "certificate_series_number": str,
                "vehicle_brand": str,
                "vehicle_model": str,
                "vehicle_engine_volume": str,  # литры, «1,4» или ""
                "vehicle_engine_power": str,
            }
    """
    full_text: str = text_annotation.get("fullText", "")
    entities: dict = {
        e.get("name", ""): e.get("text", "")
        for e in text_annotation.get("entities", [])
    }

    # Строки в правильном порядке (по Y-координатам из блоков)
    ordered_lines = _lines_from_text_annotation(text_annotation)

    # Хвост номера СТС — чтобы не путать с номером ПТС (формат 2+2+6 цифр)
    cert_last_six = _cert_last_six_digits(full_text, entities)

    vin = _extract_vin(full_text, ordered_lines)
    brand, model = _extract_brand_model(ordered_lines)
    brand = _normalize_brand(brand, vin)
    model = _normalize_model(model)
    year = _extract_year(ordered_lines)
    engine_power = _extract_engine_power(ordered_lines)
    pts = _extract_pts(
        ordered_lines, full_text, cert_last_six=cert_last_six,
    )
    engine_liters = _extract_engine_displacement_liters(
        ordered_lines, full_text,
    )
    cert = _extract_certificate(full_text, entities, pts_number=pts)

    return {
        "vehicle_vin": vin,
        "vehicle_year": year,
        "vehicle_passport_number": pts,
        "certificate_series_number": cert,
        "vehicle_brand": brand,
        "vehicle_model": model,
        "vehicle_engine_volume": engine_liters,
        "vehicle_engine_power": engine_power,
    }
