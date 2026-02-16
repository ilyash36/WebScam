# Футер «Compose & Code by 1nowen» — Спецификация стилей

> Исчерпывающая документация для переноса футера на другие проекты с сохранением цветовой стилистики и шрифта.

---

## 1. Текст и структура HTML

### Текст
```
Compose & Code by 1nowen
```

### HTML-разметка

**Вариант с анимацией «wen» (рекомендуемый):**
```html
<div class="footer-text">Compose & Code by 1no<span class="highlight-wen">wen</span></div>
```

**Вариант без анимации (простой текст):**
```html
<div class="footer-text">Compose & Code by 1nowen</div>
```

---

## 2. Шрифт

**Обязательно:** `Sigmar`, cursive

### Подключение Google Fonts
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sigmar&display=swap" rel="stylesheet">
```

Если Sigmar уже подключен вместе с другими шрифтами:
```html
<link href="https://fonts.googleapis.com/css2?family=Sigmar&family=Comfortaa:wght@400;500;600;700;900&display=swap" rel="stylesheet">
```

---

## 3. Варианты цветовой схемы

### Вариант A: Светлый фон (главная страница 1nowen)

- **Основной текст:** `#000000` (чёрный)
- **Часть «wen»:** белый текст (`#ffffff`) на чёрном фоне (`#000000`)
- **При hover на «wen»:** белый текст на синем градиенте (см. раздел 5)

### Вариант B: Тёмный фон (страницы треков)

- **Основной текст:** `#ffffff` (белый)
- **Часть «wen»:** чёрный текст (`#000000`) на белом фоне (`#ffffff`)
- **При hover на «wen»:** чёрный текст на синем градиенте (см. раздел 5)
- **Text-shadow:** `1px 1px 3px rgba(0, 0, 0, 0.5)` — для читаемости на тёмном фоне

---

## 4. Базовые стили `.footer-text`

```css
.footer-text {
    font-family: 'Sigmar', cursive;
    font-weight: normal;
    text-align: center;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    pointer-events: none;
    z-index: 10;
}
```

### Базовые размеры для разных разрешений

| Разрешение | font-size | bottom |
|------------|-----------|--------|
| Desktop (по умолчанию) | 0.8rem | 5px (светлый фон) / 30px (тёмный фон) |
| ≤768px (планшет) | 0.7rem | 10px / 20px |
| ≤480px (мобильный) | 0.65rem / 0.55rem | 10px / 15px |

---

## 5. Стили `.highlight-wen` (анимация части «wen»)

### Структура слоёв
- **::before** (z-index: -2): основной фон — чёрный или белый в зависимости от варианта
- **::after** (z-index: -1): градиент при hover

### Вариант A (светлый фон — чёрный текст страницы)

```css
.highlight-wen {
    background: transparent !important;
    color: #ffffff !important;
    padding: 0 2px;
    transition: none;
    display: inline-block;
    position: relative;
}

.highlight-wen::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: #000000;
    border-radius: 0px;
    transition: border-radius 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    z-index: -2;
    pointer-events: none;
}

.highlight-wen::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, #000033 0%, #000066 50%, #000099 100%);
    opacity: 0;
    border-radius: 0px;
    transition: opacity 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), 
                border-radius 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    z-index: -1;
    pointer-events: none;
}

/* Hover — анимация появления градиента */
.footer-text:hover .highlight-wen {
    background: transparent !important;
    color: #ffffff !important;
}

.footer-text:hover .highlight-wen::before {
    border-radius: 14%;
    transition: border-radius 1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.footer-text:hover .highlight-wen::after {
    opacity: 1;
    border-radius: 14%;
    transition: opacity 1s cubic-bezier(0.25, 0.46, 0.45, 0.94), 
                border-radius 1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
```

### Вариант B (тёмный фон — белый текст страницы)

```css
.highlight-wen {
    background: transparent !important;
    color: #000000 !important;  /* чёрный текст на белом фоне */
    padding: 0 2px;
    transition: none;
    display: inline-block;
    position: relative;
}

.highlight-wen::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: #ffffff;  /* белый фон вместо чёрного */
    border-radius: 0px;
    transition: border-radius 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    z-index: -2;
    pointer-events: none;
}

.highlight-wen::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, #000033 0%, #000066 50%, #000099 100%);
    opacity: 0;
    border-radius: 0px;
    transition: opacity 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), 
                border-radius 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    z-index: -1;
    pointer-events: none;
}

.footer-text:hover .highlight-wen {
    background: transparent !important;
    color: #000000 !important;
}

.footer-text:hover .highlight-wen::before {
    background: #ffffff;
    border-radius: 14%;
    transition: border-radius 1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.footer-text:hover .highlight-wen::after {
    opacity: 1;
    border-radius: 14%;
    transition: opacity 1s cubic-bezier(0.25, 0.46, 0.45, 0.94), 
                border-radius 1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
```

---

## 6. Градиент «wen» при hover

**Единый градиент для обоих вариантов:**
```css
linear-gradient(135deg, #000033 0%, #000066 50%, #000099 100%)
```

- `#000033` — тёмно-синий
- `#000066` — средний синий
- `#000099` — синий

**Timing function:** `cubic-bezier(0.25, 0.46, 0.45, 0.94)`

---

## 7. Полный CSS для светлого фона (Вариант A)

```css
.footer-text {
    position: absolute;
    bottom: 5px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.8rem;
    font-family: 'Sigmar', cursive;
    font-weight: normal;
    color: #000000;
    text-align: center;
    z-index: 10;
    pointer-events: none;
    width: 100%;
}

.highlight-wen {
    background: transparent !important;
    color: #ffffff !important;
    padding: 0 2px;
    transition: none;
    display: inline-block;
    position: relative;
}

.highlight-wen::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: #000000;
    border-radius: 0px;
    transition: border-radius 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    z-index: -2;
    pointer-events: none;
}

.highlight-wen::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, #000033 0%, #000066 50%, #000099 100%);
    opacity: 0;
    border-radius: 0px;
    transition: opacity 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), 
                border-radius 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    z-index: -1;
    pointer-events: none;
}

.footer-text:hover .highlight-wen {
    background: transparent !important;
    color: #ffffff !important;
}

.footer-text:hover .highlight-wen::before {
    border-radius: 14%;
    transition: border-radius 1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.footer-text:hover .highlight-wen::after {
    opacity: 1;
    border-radius: 14%;
    transition: opacity 1s cubic-bezier(0.25, 0.46, 0.45, 0.94), 
                border-radius 1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

@media (max-width: 768px) {
    .footer-text {
        font-size: 0.7rem;
        bottom: 10px;
    }
}

@media (max-width: 480px) {
    .footer-text {
        font-size: 0.55rem;
        bottom: 10px;
    }
}
```

---

## 8. Полный CSS для тёмного фона (Вариант B)

```css
.footer-text {
    position: absolute;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.8rem;
    font-family: 'Sigmar', cursive;
    font-weight: normal;
    color: #ffffff;
    text-align: center;
    text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
    z-index: 10;
    pointer-events: none;
    width: 100%;
}

.highlight-wen {
    background: transparent !important;
    color: #000000 !important;
    padding: 0 2px;
    transition: none;
    display: inline-block;
    position: relative;
}

.highlight-wen::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: #ffffff;
    border-radius: 0px;
    transition: border-radius 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    z-index: -2;
    pointer-events: none;
}

.highlight-wen::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, #000033 0%, #000066 50%, #000099 100%);
    opacity: 0;
    border-radius: 0px;
    transition: opacity 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), 
                border-radius 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    z-index: -1;
    pointer-events: none;
}

.footer-text:hover .highlight-wen {
    background: transparent !important;
    color: #000000 !important;
}

.footer-text:hover .highlight-wen::before {
    background: #ffffff;
    border-radius: 14%;
    transition: border-radius 1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.footer-text:hover .highlight-wen::after {
    opacity: 1;
    border-radius: 14%;
    transition: opacity 1s cubic-bezier(0.25, 0.46, 0.45, 0.94), 
                border-radius 1s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

@media (max-width: 768px) {
    .footer-text {
        font-size: 0.7rem;
        bottom: 20px;
    }
}

@media (max-width: 480px) {
    .footer-text {
        font-size: 0.65rem;
        bottom: 15px;
    }
}
```

---

## 9. Требования к родительскому контейнеру

Футер использует `position: absolute`, поэтому родительский контейнер должен иметь `position: relative` (или `position: absolute` / `fixed`):

```css
.parent-container {
    position: relative;
    min-height: 100vh; /* или другая высота */
    padding-bottom: 60px; /* запас для футера */
}
```

---

## 10. Краткая шпаргалка цветов

| Элемент | Светлый фон | Тёмный фон |
|---------|-------------|------------|
| Основной текст | `#000000` | `#ffffff` |
| «wen» текст | `#ffffff` | `#000000` |
| «wen» фон (::before) | `#000000` | `#ffffff` |
| «wen» градиент (::after, hover) | `#000033 → #000066 → #000099` | тот же |
| Text-shadow | не нужен | `1px 1px 3px rgba(0,0,0,0.5)` |

---

## 11. Минимальная версия (без анимации «wen»)

Если анимация не нужна, используйте простой текст:

```html
<div class="footer-text">Compose & Code by 1nowen</div>
```

```css
.footer-text {
    font-family: 'Sigmar', cursive;
    font-weight: normal;
    font-size: 0.8rem;
    text-align: center;
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    z-index: 10;
}

/* Светлый фон */
.footer-text { color: #000000; }

/* Тёмный фон */
.footer-text { 
    color: #ffffff; 
    text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
}
```

---

*Документ создан на основе проекта 1nowen Site. Последнее обновление: февраль 2026.*
