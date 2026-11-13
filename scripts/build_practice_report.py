#!/usr/bin/env python3
"""Собрать отчёт ПМ.05 в Microsoft PowerPoint.

Структура слайдов — черновой каркас этапа 13 плана работ (Приложения 1 в бланке нет).
Снимки: docs/images/report/*.png (живая панель диспетчера).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "docs" / "images" / "report"
OUT = ROOT / "docs" / "pm05-otchet-praktiki.pptx"

TEAL = RGBColor(0x0B, 0x4F, 0x4A)
TEAL_DARK = RGBColor(0x08, 0x38, 0x33)
CREAM = RGBColor(0xF4, 0xF0, 0xE6)
CARD = RGBColor(0xFF, 0xFD, 0xF8)
INK = RGBColor(0x1C, 0x24, 0x1F)
MUTED = RGBColor(0x3E, 0x4C, 0x46)
LINE = RGBColor(0xDD, 0xD4, 0xC6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
AMBER = RGBColor(0x8A, 0x4B, 0x08)
FONT = "Calibri"
W = Inches(13.333)
H = Inches(7.5)


def rgb_of(color: RGBColor) -> str:
    return f"{color[0]:02X}{color[1]:02X}{color[2]:02X}"


def set_run(run, size=16, bold=False, color=INK, font=FONT, italic=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("a:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("a:rFonts"), {})
        rPr.append(rFonts)
    rFonts.set("ascii", font)
    rFonts.set("hAnsi", font)
    rFonts.set("cs", font)
    rFonts.set("eastAsia", font)


def add_text(slide, left, top, width, height, text, size=16, bold=False, color=INK,
             align=PP_ALIGN.LEFT, font=FONT, italic=False, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    try:
        tf._txBody.bodyPr.set("anchor", {MSO_ANCHOR.TOP: "t", MSO_ANCHOR.MIDDLE: "ctr", MSO_ANCHOR.BOTTOM: "b"}[anchor])
    except Exception:
        pass
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    set_run(run, size=size, bold=bold, color=color, font=font, italic=italic)
    return box


def add_paras(slide, left, top, width, height, items, size=16, color=INK, space=8, bold_first=False):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(space)
        if isinstance(item, tuple):
            text, is_bold = item
        else:
            text, is_bold = item, (bold_first and i == 0)
        run = p.add_run()
        run.text = text
        set_run(run, size=size, bold=is_bold, color=color)
    return box


def add_bullets(slide, left, top, width, height, items, size=16, color=INK, space=6):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.level = 0
        p.space_after = Pt(space)
        pPr = p._p.get_or_add_pPr()
        buFont = pPr.makeelement(qn("a:buFont"), {"typeface": FONT})
        buChar = pPr.makeelement(qn("a:buChar"), {"char": "•"})
        pPr.append(buFont)
        pPr.append(buChar)
        run = p.add_run()
        run.text = item
        set_run(run, size=size, color=color)
    return box


def solid_rect(slide, left, top, width, height, fill, line=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    return shape


def rounded(slide, left, top, width, height, fill, line=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.adjustments[0] = 0.08
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    return shape


def set_bg(slide, color=CREAM):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def footer(slide, n, total):
    solid_rect(slide, Inches(0), Inches(7.28), W, Inches(0.22), TEAL)
    add_text(
        slide, Inches(0.5), Inches(7.28), Inches(10.2), Inches(0.22),
        "АНО ВО «Московский университет «Синергия»  ·  ПМ.05  ·  производственная практика",
        size=11, color=WHITE, anchor=MSO_ANCHOR.MIDDLE,
    )
    add_text(
        slide, Inches(11.3), Inches(7.28), Inches(1.5), Inches(0.22),
        f"{n} / {total}",
        size=11, color=WHITE, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE,
    )


def header(slide, kicker, title):
    solid_rect(slide, Inches(0), Inches(0), W, Inches(0.12), TEAL)
    add_text(slide, Inches(0.5), Inches(0.22), Inches(12.3), Inches(0.28),
             kicker, size=12, color=TEAL, bold=True)
    add_text(slide, Inches(0.5), Inches(0.46), Inches(12.3), Inches(0.5),
             title, size=26, color=TEAL_DARK, bold=True)


def blank(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    return slide


def add_picture_fit(slide, path, left, top, width, height):
    im = Image.open(path)
    iw, ih = im.size
    box_a = width / height
    img_a = iw / ih
    if img_a > box_a:
        w = width
        h = int(width * ih / iw)
        l, t = left, top + (height - h) // 2
    else:
        h = height
        w = int(height * iw / ih)
        l, t = left + (width - w) // 2, top
    frame = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l - Inches(0.04), t - Inches(0.04),
                                   w + Inches(0.08), h + Inches(0.08))
    frame.adjustments[0] = 0.03
    frame.fill.solid()
    frame.fill.fore_color.rgb = WHITE
    frame.line.color.rgb = LINE
    frame.line.width = Pt(1)
    return slide.shapes.add_picture(str(path), l, t, w, h)


def add_table(slide, left, top, width, rows, col_w, font_size=13, height=None):
    if height is None:
        height = Inches(min(5.55, 0.62 * len(rows)))
    table_shape = slide.shapes.add_table(len(rows), len(rows[0]), left, top, width, height)
    table = table_shape.table
    for i, w in enumerate(col_w):
        table.columns[i].width = w
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            cell.text = ""
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.04)
            cell.margin_bottom = Inches(0.04)
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = val
            if r == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = TEAL
                set_run(run, size=font_size, bold=True, color=WHITE)
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = CARD if r % 2 else CREAM
                set_run(run, size=font_size, color=INK)
    return table_shape


def build():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    slides_meta = []

    def push(fn):
        slides_meta.append(fn)

    # --- 1 title ---
    def s_title(slide, n, total):
        solid_rect(slide, Inches(0), Inches(0), Inches(0.38), H, TEAL)
        solid_rect(slide, Inches(0.38), Inches(0), W - Inches(0.38), Inches(0.12), TEAL)
        add_text(slide, Inches(0.7), Inches(0.35), Inches(12), Inches(0.35),
                 "АНО ВО «Московский университет «Синергия»", size=16, color=TEAL, bold=True)
        add_text(slide, Inches(0.7), Inches(0.68), Inches(12), Inches(0.3),
                 "Факультет информационных технологий  ·  специальность 09.02.07",
                 size=14, color=MUTED)
        add_text(slide, Inches(0.7), Inches(1.35), Inches(12), Inches(0.35),
                 "Производственная практика", size=18, color=AMBER, bold=True)
        add_text(slide, Inches(0.7), Inches(1.7), Inches(12.1), Inches(1.35),
                 "Отчёт о прохождении практики\nпо модулю ПМ.05",
                 size=36, color=TEAL_DARK, bold=True)
        add_text(slide, Inches(0.7), Inches(3.2), Inches(12), Inches(0.7),
                 "Проектирование и разработка информационных систем\n"
                 "Тема: веб-приложение — административная панель на Flask + MySQL",
                 size=18, color=INK)
        rounded(slide, Inches(0.7), Inches(4.15), Inches(11.9), Inches(2.55), CARD, LINE)
        fields = [
            "Обучающийся (Ф.И.О.):  ________________________________",
            "Группа (шифр и номер):  ________________",
            "Период практики:  «____» ________ 20___ г.  —  «____» ________ 20___ г.",
            "Руководитель практики от образовательной организации:  ________________________________",
            "Информационная система:  «СвязьСервис» — учёт заявок на ремонт и подключение",
        ]
        add_paras(slide, Inches(0.95), Inches(4.3), Inches(11.4), Inches(2.25), fields, size=15, space=8)
        add_text(slide, Inches(0.7), Inches(6.85), Inches(12), Inches(0.3),
                 "Москва, 2026", size=14, color=MUTED)
        # no numbered footer on title; thin bar already at top

    push(s_title)

    def s_note(slide, n, total):
        header(slide, "Вид работ 6  ·  оформление отчёта", "О структуре этой презентации")
        add_paras(slide, Inches(0.5), Inches(1.15), Inches(12.3), Inches(1.2), [
            "Индивидуальное задание требует отчёт в формате Microsoft PowerPoint "
            "«согласно Приложению 1». Самого Приложения 1 в бланке нет.",
        ], size=17, space=8)
        add_bullets(slide, Inches(0.5), Inches(2.35), Inches(12.3), Inches(3.6), [
            "Слайды собраны по видам работ 1–6 бланка и по черновому каркасу этапа 13 плана работ.",
            "Ф.И.О., шифр группы и даты в бланке пустые — в отчёте оставлены прочерки, без выдуманных сведений.",
            "Скриншоты — живая панель диспетчера учебной ИС «СвязьСервис» (13.11.2026).",
            "Подписанная справка с места практики и загрузка в lms.synergy.ru в этот файл не входят "
            "и не имитируются (этап 14).",
            "Если Приложение 1 появится — порядок слайдов нужно сверить с ним и при необходимости пересобрать.",
        ], size=16, space=10)
        footer(slide, n, total)

    push(s_note)

    def s_toc(slide, n, total):
        header(slide, "Содержание", "Базовая и информационно-вспомогательная информация")
        left = [
            "1. Цель практики и вид деятельности ВД 5",
            "2. Виды работ 1–6 (обзор)",
            "3. Инструктажи и совещание (вид 1)",
            "4. Профильная организация (вид 2)",
            "5. Источники и темы самоподготовки (вид 3)",
            "6. Постановка задачи: Flask-админка и MySQL",
            "7. Состав оборудования и программных средств",
            "8. Архитектура приложения",
            "9. База данных",
            "10. Экраны панели диспетчера",
        ]
        right = [
            "11. Безопасность",
            "12. Журнал действий и анализ использования ИС",
            "13. Тестирование и критерии качества",
            "14. Документация по эксплуатации",
            "15. Оценка качества и экономической эффективности",
            "16. Теория и практика, рекомендации (вид 5)",
            "17. Практический опыт по девяти пунктам бланка",
            "18. Отчётные документы (вид 6)",
            "19. Заключение",
        ]
        add_paras(slide, Inches(0.55), Inches(1.2), Inches(6.2), Inches(5.6), left, size=16, space=10)
        add_paras(slide, Inches(6.9), Inches(1.2), Inches(5.9), Inches(5.6), right, size=16, space=10)
        footer(slide, n, total)

    push(s_toc)

    def s_goal(slide, n, total):
        header(slide, "Цель практики", "ВД 5. Проектирование и разработка информационных систем")
        add_paras(slide, Inches(0.5), Inches(1.15), Inches(12.3), Inches(1.1), [
            "Подготовиться к экзамену по модулю ПМ.05: получить практический опыт разработки "
            "информационной системы и оформить результаты практики.",
        ], size=17, space=6)
        rounded(slide, Inches(0.5), Inches(2.3), Inches(6.0), Inches(4.4), CARD, LINE)
        rounded(slide, Inches(6.8), Inches(2.3), Inches(6.0), Inches(4.4), CARD, LINE)
        add_text(slide, Inches(0.75), Inches(2.5), Inches(5.5), Inches(0.4),
                 "Что проверяет руководитель", size=16, bold=True, color=TEAL)
        add_bullets(slide, Inches(0.75), Inches(3.0), Inches(5.5), Inches(3.4), [
            "работающая административная панель;",
            "презентация PowerPoint (этот файл);",
            "справка с места практики (отдельно);",
            "комплект в ЭИОС lms.synergy.ru.",
        ], size=15, space=8)
        add_text(slide, Inches(7.05), Inches(2.5), Inches(5.5), Inches(0.4),
                 "Практический результат этой работы", size=16, bold=True, color=TEAL)
        add_bullets(slide, Inches(7.05), Inches(3.0), Inches(5.5), Inches(3.4), [
            "панель диспетчера ИС «СвязьСервис»;",
            "Flask, Jinja2, SQLAlchemy, MySQL 8;",
            "вход, роль администратора, CRUD, фильтры, пагинация, журнал;",
            "методика тестов и документация по эксплуатации в репозитории.",
        ], size=15, space=8)
        footer(slide, n, total)

    push(s_goal)

    def s_kinds(slide, n, total):
        header(slide, "Обзор задания", "Виды работ 1–6")
        add_table(slide, Inches(0.45), Inches(1.15), Inches(12.4), [
            ("№", "Вид работ по бланку", "Где в этом отчёте"),
            ("1", "Ознакомительная лекция, совещание, инструктажи по ОТ, ТБ, ПБ и санитарным правилам",
             "Слайд «Инструктажи» — факты и даты к заполнению"),
            ("2", "Структура профильной организации, подразделение, нормативные документы",
             "Слайд «Организация» — поля бланка пустые"),
            ("3", "Литература и темы по веб-приложениям (два пособия IPR SMART)",
             "Слайд «Источники»"),
            ("4", "Экспериментально-практическая работа: админка Flask + MySQL",
             "Постановка задачи, архитектура, БД, экраны, безопасность, журнал"),
            ("5", "Анализ результатов, презентационные материалы, предложения",
             "Тесты, эксплуатация, эффективность, рекомендации"),
            ("6", "Отчёт PowerPoint, справка, размещение комплекта в LMS",
             "Этот файл; справка и LMS — не выдумываются"),
        ], [Inches(0.55), Inches(6.7), Inches(5.15)], font_size=12, height=Inches(5.25))
        add_text(slide, Inches(0.5), Inches(6.75), Inches(12.3), Inches(0.4),
                 "Период выполнения работ в таблице бланка пустой. Даты уточняются у куратора группы в lms.synergy.ru.",
                 size=13, color=MUTED, italic=True)
        footer(slide, n, total)

    push(s_kinds)

    def s_briefing(slide, n, total):
        header(slide, "Вид работ 1", "Инструктажи и совещание с руководителем практики")
        add_paras(slide, Inches(0.5), Inches(1.15), Inches(12.3), Inches(0.7), [
            "По бланку до допуска к работам нужно пройти совещание и инструктажи. "
            "В задании нет отметок о дате и месте — ниже поля, а не выдуманные факты.",
        ], size=16)
        add_table(slide, Inches(0.45), Inches(2.0), Inches(12.4), [
            ("Мероприятие", "Дата", "Кто проводил", "Отметка"),
            ("Инструктивное совещание (обязанности, субординация, внешний вид, распорядок, конфиденциальность)",
             "«____» ______ 20___", "____________________", "☐ пройдено"),
            ("Охрана труда и техника безопасности", "«____» ______ 20___", "____________________", "☐ пройдено"),
            ("Пожарная безопасность", "«____» ______ 20___", "____________________", "☐ пройдено"),
            ("Санитарно-эпидемиологические правила и гигиенические нормативы",
             "«____» ______ 20___", "____________________", "☐ пройдено"),
            ("Медицинские противопоказания (справка — только при наличии)", "—", "мед. учреждение", "☐ не требуется / ☐ приложена"),
        ], [Inches(6.3), Inches(2.0), Inches(2.3), Inches(1.8)], font_size=11, height=Inches(4.2))
        add_text(slide, Inches(0.5), Inches(6.55), Inches(12.3), Inches(0.55),
                 "Подпись обучающегося на бланке («индивидуальное задание получил»): ________________  /  ________________",
                 size=14, color=INK)
        footer(slide, n, total)

    push(s_briefing)

    def s_org(slide, n, total):
        header(slide, "Вид работ 2", "Профильная организация — база практики")
        add_paras(slide, Inches(0.5), Inches(1.15), Inches(12.3), Inches(0.85), [
            "Бланк не называет организацию-базу. Учебный стенд «СвязьСервис» — предметная область кода, "
            "а не подмена профильной организации. Название базы, подразделение и регламенты заполняются по факту.",
        ], size=16)
        rounded(slide, Inches(0.5), Inches(2.15), Inches(6.05), Inches(4.5), CARD, LINE)
        add_text(slide, Inches(0.75), Inches(2.3), Inches(5.55), Inches(0.35),
                 "К заполнению по месту практики", size=16, bold=True, color=TEAL)
        add_paras(slide, Inches(0.75), Inches(2.75), Inches(5.55), Inches(3.6), [
            "Организация: ________________________________",
            "Подразделение: _____________________________",
            "Профиль деятельности: ______________________",
            "Ответственное лицо (справка): _______________",
            "Устав / положение: ☐ ознакомлен",
            "Правила внутреннего распорядка: ☐ ознакомлен",
            "Политика информационной безопасности: ☐ ознакомлен",
        ], size=14, space=8)
        rounded(slide, Inches(6.8), Inches(2.15), Inches(6.05), Inches(4.5), CARD, LINE)
        add_text(slide, Inches(7.05), Inches(2.3), Inches(5.55), Inches(0.35),
                 "Учебный объект практики (код)", size=16, bold=True, color=TEAL)
        add_bullets(slide, Inches(7.05), Inches(2.8), Inches(5.55), Inches(3.5), [
            "ИС «СвязьСервис»: заявки на ремонт и подключение;",
            "абонент видит только свои записи;",
            "диспетчер ведёт общий список, справочники и журнал;",
            "данные в базе учебные, не персональные данные реальных абонентов;",
            "репозиторий: Soloea-ru/pm05-uchet-remontov.",
        ], size=15, space=8)
        footer(slide, n, total)

    push(s_org)

    def s_lit(slide, n, total):
        header(slide, "Вид работ 3", "Источники и темы самоподготовки «Веб-приложения»")
        add_table(slide, Inches(0.45), Inches(1.15), Inches(12.4), [
            ("Источник", "Как использован в этой практике"),
            ("Вагин Д. В., Петров Р. В. Современные технологии разработки веб-приложений. НГТУ, 2019. "
             "https://www.iprbookshop.ru/98738.html",
             "Клиент/сервер, страница собирается на сервере, маршруты и шаблоны."),
            ("Позевалкин В. В., Панова Н. Ф. Разработка веб-приложений на основе клиентских каркасов и библиотек. ОГУ, 2025. "
             "https://www.iprbookshop.ru/153228.html",
             "В проекте нет SPA (React и аналоги): HTML/CSS и немного JS. Для учебной админки достаточно; "
             "как «современный фронтенд» из пособия — не применялось."),
        ], [Inches(7.4), Inches(5.0)], font_size=12, height=Inches(2.2))
        add_text(slide, Inches(0.5), Inches(3.55), Inches(12.3), Inches(0.35),
                 "Темы бланка, которыми нужно владеть", size=16, bold=True, color=TEAL)
        add_bullets(slide, Inches(0.5), Inches(3.95), Inches(12.3), Inches(2.9), [
            "архитектура веб-приложений, клиент и сервер;",
            "Flask: маршруты, Jinja2, модели, конфигурация;",
            "SQL, ORM SQLAlchemy, подключение к MySQL, CRUD;",
            "аутентификация, сессии, роли; три уровня (представление, правила, данные);",
            "CSRF, хеш пароля, экранирование; модульная админка и UX-доступность.",
        ], size=15, space=6)
        footer(slide, n, total)

    push(s_lit)

    def s_task(slide, n, total):
        header(slide, "Вид работ 4  ·  постановка задачи", "Административная панель Flask + MySQL")
        add_paras(slide, Inches(0.5), Inches(1.15), Inches(12.3), Inches(0.8), [
            "Бланк: модернизировать уже свёрстанную HTML/CSS-страницу админки, встроить в Flask "
            "и подключить к существующей MySQL. Отдельного ТЗ нет — требования взяты из пункта 4 бланка.",
        ], size=16)
        add_table(slide, Inches(0.45), Inches(2.1), Inches(12.4), [
            ("Требование бланка", "Как сделано в «СвязьСервис»"),
            ("Вход и роль «администратор»", "Логин/пароль, сессия; в панель пускает роль admin (диспетчер)"),
            ("Списки, фильтры, пагинация", "Все заявки: статус, вариант работ, поиск; по 5 записей на страницу"),
            ("Добавление, изменение, удаление", "Заявки и справочники; удаление с отдельным подтверждением"),
            ("Данные из MySQL в Jinja2", "SQLAlchemy, utf8mb4, экранирование вывода"),
            ("Ошибки, CSRF, журнал", "Страницы 400/403/404/503; CSRF на POST; таблица admin_actions"),
        ], [Inches(4.6), Inches(7.8)], font_size=13, height=Inches(4.15))
        add_text(slide, Inches(0.5), Inches(6.55), Inches(12.3), Inches(0.5),
                 "Готовой «чужой» MySQL и отдельной вёрстки в бланке не было: схема и экраны предыдущей практики перенесены на MySQL 8.",
                 size=14, color=MUTED, italic=True)
        footer(slide, n, total)

    push(s_task)

    def s_stack(slide, n, total):
        header(slide, "Состав средств", "Оборудование и программные средства разработки")
        add_table(slide, Inches(0.45), Inches(1.2), Inches(12.4), [
            ("Средство", "Назначение"),
            ("ОС разработчика / стенд тестов", "Windows (команды README) или Ubuntu 24.04; автотесты — 4 CPU, 16 ГиБ"),
            ("Python 3.12, Flask 3, Jinja2, Werkzeug", "Серверное приложение, шаблоны, сессии"),
            ("Flask-SQLAlchemy, SQLAlchemy, PyMySQL", "ORM и драйвер MySQL"),
            ("MySQL 8.0 (Docker Compose mysql:8.0)", "Рабочая база svyazservice; секреты только из .env"),
            ("HTML, CSS, JS без UI-библиотеки", "Готовая вёрстка панели, встроена в Jinja2"),
            ("unittest, Google Chrome", "Методика тестирования и ручной просмотр экранов"),
            ("Git, Microsoft PowerPoint", "Версии кода и этот отчёт"),
        ], [Inches(5.1), Inches(7.3)], font_size=13, height=Inches(5.5))
        footer(slide, n, total)

    push(s_stack)

    def s_arch(slide, n, total):
        header(slide, "Архитектура", "Клиент/сервер, папки проекта, три уровня")
        add_paras(slide, Inches(0.5), Inches(1.15), Inches(12.3), Inches(0.7), [
            "Браузер не ходит в MySQL сам: запрос → Flask → SQLAlchemy → MySQL; ответ — HTML из Jinja2.",
        ], size=16)
        boxes = [
            (0.5, "Представление", "templates/\nмаршруты\napp/routes.py\napp/admin.py"),
            (4.7, "Бизнес-логика", "права и роли\nvalidators.py\nпроверки в admin.py"),
            (8.9, "Доступ к данным", "app/models.py\nSQLAlchemy\nMySQL 8"),
        ]
        for x, title, body in boxes:
            rounded(slide, Inches(x), Inches(2.0), Inches(3.9), Inches(2.35), CARD, TEAL)
            add_text(slide, Inches(x + 0.2), Inches(2.15), Inches(3.5), Inches(0.4),
                     title, size=16, bold=True, color=TEAL, align=PP_ALIGN.CENTER)
            add_text(slide, Inches(x + 0.2), Inches(2.6), Inches(3.5), Inches(1.55),
                     body, size=15, color=INK, align=PP_ALIGN.CENTER)
        add_text(slide, Inches(0.5), Inches(4.5), Inches(12.3), Inches(0.35),
                 "Структура проекта по бланку", size=16, bold=True, color=TEAL)
        add_bullets(slide, Inches(0.5), Inches(4.9), Inches(12.3), Inches(2.0), [
            "шаблоны — templates/; модели — app/models.py; маршруты — app/routes.py и app/admin.py;",
            "конфигурация — app/config.py, .env.example (пароль базы в git не кладётся);",
            "журнал — app/journal.py и таблица admin_actions; общий каркас — app/__init__.py;",
            "жёсткого отдельного «сервисного» слоя нет: для этого объёма хватает трёх уровней выше.",
        ], size=15, space=6)
        footer(slide, n, total)

    push(s_arch)

    def s_db(slide, n, total):
        header(slide, "База данных", "Подключение к MySQL и состав таблиц")
        add_paras(slide, Inches(0.5), Inches(1.15), Inches(12.3), Inches(0.7), [
            "Рабочий URI по умолчанию — mysql+pymysql://…svyazservice…. Автотесты ходят во временный SQLite, "
            "чтобы прогон не зависел от сервера MySQL.",
        ], size=15)
        add_table(slide, Inches(0.45), Inches(1.95), Inches(12.4), [
            ("Таблица", "Назначение"),
            ("users", "Логин, хеш пароля PBKDF2, ФИО, контакты, роль user / admin"),
            ("requests", "Заявка: адрес, квартира, телефон, проблема, визит, связи со справочниками"),
            ("work_types", "Вариант работ (подключение, ремонт линии, настройка, перенос)"),
            ("payment_types", "Способ оплаты (оплачено, рассрочка, по факту)"),
            ("statuses", "Статус заявки: код, название, порядок"),
            ("admin_actions", "Журнал диспетчера: кто, когда, вход / создание / изменение / удаление"),
        ], [Inches(2.6), Inches(9.8)], font_size=13, height=Inches(4.85))
        footer(slide, n, total)

    push(s_db)

    def shot_slide(kicker, title, caption, filename):
        def inner(slide, n, total, _k=kicker, _t=title, _c=caption, _f=filename):
            header(slide, _k, _t)
            add_text(slide, Inches(0.5), Inches(1.05), Inches(12.3), Inches(0.4),
                     _c, size=14, color=MUTED)
            add_picture_fit(slide, IMG / _f, Inches(0.7), Inches(1.45), Inches(11.9), Inches(5.65))
            footer(slide, n, total)
        return inner

    push(shot_slide(
        "Экраны  ·  предметная область",
        "Главная страница учебной ИС",
        "Абонент регистрируется и оставляет заявку; диспетчер ведёт статусы. Снимок живого сайта, 13.11.2026.",
        "01-home.png",
    ))
    push(shot_slide(
        "Экраны  ·  вход",
        "Аутентификация",
        "Форма входа. Диспетчер попадает в общий список, абонент — к своим заявкам. CSRF-токен скрытым полем.",
        "02-login.png",
    ))
    push(shot_slide(
        "Экраны  ·  списки",
        "Все заявки: таблица, фильтр, пагинация",
        "По 5 записей на страницу. Фильтр: статус, вариант работ, поиск по адресу / ФИО / телефону. Статус можно сменить в строке.",
        "03-admin-list.png",
    ))
    push(shot_slide(
        "Экраны  ·  фильтр",
        "Отбор заявок по статусу «Выполнена»",
        "Фильтр реально сужает выборку. Пустой результат показывает «заявок нет», а не ошибку сервера.",
        "04-admin-filter.png",
    ))
    push(shot_slide(
        "Экраны  ·  формы",
        "Добавление заявки диспетчером",
        "Обязательные поля, подписи, кнопка сохранения. Та же форма используется для редактирования с уже заполненными данными.",
        "06-request-new.png",
    ))
    push(shot_slide(
        "Экраны  ·  удаление",
        "Подтверждение удаления",
        "Удаление полное, не «мягкое». Отмена возвращает к списку. Восстановления нет.",
        "08-request-delete.png",
    ))
    push(shot_slide(
        "Экраны  ·  справочники",
        "Варианты работ, оплата, статусы",
        "CRUD справочников. Запись с заявками и последнюю строку справочника удалить нельзя.",
        "09-catalogs.png",
    ))

    def s_sec(slide, n, total):
        header(slide, "Безопасность", "Сессии, роль, CSRF, хеш пароля, экранирование")
        add_table(slide, Inches(0.45), Inches(1.15), Inches(6.3), [
            ("Мера", "Как устроено"),
            ("Вход", "Сессия после верного пароля"),
            ("Роль", "Только admin видит /admin"),
            ("Гость", "Редирект на /login"),
            ("Абонент", "403, без стека Python"),
            ("CSRF", "Все POST; без токена — 400"),
            ("Пароль", "PBKDF2-SHA256, не открытый текст"),
            ("Вывод", "Jinja2 экранирует поля заявок"),
        ], [Inches(1.7), Inches(4.6)], font_size=12, height=Inches(5.4))
        add_text(slide, Inches(7.0), Inches(1.15), Inches(5.8), Inches(0.5),
                 "Абонент открыл панель диспетчера", size=14, bold=True, color=TEAL)
        add_picture_fit(slide, IMG / "12-error-403.png", Inches(7.0), Inches(1.65), Inches(5.8), Inches(5.1))
        footer(slide, n, total)

    push(s_sec)

    def s_log(slide, n, total):
        header(slide, "Сбор данных об использовании ИС", "Журнал действий администратора")
        add_paras(slide, Inches(0.5), Inches(1.1), Inches(12.3), Inches(0.55), [
            "Пишет только роль диспетчера: вход, создание, изменение, удаление. Абонент журнал не видит. "
            "Это же материал для анализа использования системы (пункт опыта из бланка).",
        ], size=15)
        add_picture_fit(slide, IMG / "10-journal.png", Inches(0.7), Inches(1.7), Inches(11.9), Inches(5.15))
        footer(slide, n, total)

    push(s_log)

    def s_test(slide, n, total):
        header(slide, "Вид работ 5  ·  качество", "Методика тестирования и критерии надёжности")
        add_paras(slide, Inches(0.5), Inches(1.15), Inches(12.3), Inches(0.55), [
            "Прогон 13.11.2026: python -m unittest discover -s tests -t . -v → 23 теста, OK, 14 с. "
            "Полная таблица шаг → ожидание → факт — docs/testing.md.",
        ], size=15)
        add_table(slide, Inches(0.45), Inches(1.8), Inches(12.4), [
            ("Критерий", "Как считаем выполненным", "Факт"),
            ("Вход и роль", "Гость → /login; абонент → 403; после выхода панель закрыта", "пройден"),
            ("CRUD", "Создание, правка, удаление заявки и справочника видны в базе", "пройден"),
            ("Фильтр и страницы", "Выборка сужается; страница 2 ≠ страница 1", "пройден"),
            ("CSRF и пароль", "POST без токена — 400; в базе только pbkdf2:sha256", "пройден"),
            ("Ошибки и журнал", "400/403/404/503 без traceback; admin_actions пишется", "пройден"),
        ], [Inches(2.4), Inches(8.2), Inches(1.8)], font_size=13, height=Inches(4.35))
        add_text(slide, Inches(0.5), Inches(6.55), Inches(12.3), Inches(0.5),
                 "Ограничение честно: автотесты идут в SQLite, рабочий запуск — MySQL. Проваленных пунктов нет.",
                 size=14, color=MUTED, italic=True)
        footer(slide, n, total)

    push(s_test)

    def s_ops(slide, n, total):
        header(slide, "Документация по эксплуатации", "Как пользоваться панелью (кратко)")
        add_table(slide, Inches(0.45), Inches(1.2), Inches(12.4), [
            ("Шаг", "Что сделать"),
            ("Запуск", "Скопировать .env.example → .env; docker compose up -d; python run.py; открыть http://127.0.0.1:5000"),
            ("Вход диспетчера", "Учебный логин admin / Admin123!  →  /admin"),
            ("Список", "Фильтр и «Показать»; «Назад / Дальше»; статус в строке — «Сохранить»"),
            ("Заявка", "«Новая заявка» → заполнить → сохранить; «Изменить»; «Удалить» с подтверждением"),
            ("Справочники", "/admin/catalogs — работы, оплата, статусы"),
            ("Журнал", "/admin/journal — кто и что менял"),
            ("Если не открывается", "«База недоступна» — поднять MySQL и проверить .env; стек Python на экран не выводится"),
        ], [Inches(2.5), Inches(9.9)], font_size=13, height=Inches(5.05))
        add_text(slide, Inches(0.5), Inches(6.6), Inches(12.3), Inches(0.45),
                 "Полный текст: docs/operations.md. Учебные пароли на экране входа удобны для защиты, для реальной организации их убирают.",
                 size=13, color=MUTED, italic=True)
        footer(slide, n, total)

    push(s_ops)

    def s_econ(slide, n, total):
        header(slide, "Оценка", "Качество и экономическая эффективность")
        rounded(slide, Inches(0.5), Inches(1.2), Inches(6.05), Inches(5.5), CARD, LINE)
        add_text(slide, Inches(0.75), Inches(1.4), Inches(5.55), Inches(0.4),
                 "Качество (по критериям этапа 11)", size=16, bold=True, color=TEAL)
        add_bullets(slide, Inches(0.75), Inches(1.9), Inches(5.55), Inches(4.5), [
            "вход только для диспетчера;",
            "CRUD сохраняется через SQLAlchemy;",
            "фильтр и пагинация работают;",
            "CSRF, хеш пароля, экранирование;",
            "ошибки без traceback;",
            "журнал пишется и открывается диспетчеру;",
            "это учебный стенд, не промышленный контур.",
        ], size=15, space=7)
        rounded(slide, Inches(6.8), Inches(1.2), Inches(6.05), Inches(5.5), CARD, LINE)
        add_text(slide, Inches(7.05), Inches(1.4), Inches(5.55), Inches(0.4),
                 "Эффективность в рамках компетенции", size=16, bold=True, color=TEAL)
        add_bullets(slide, Inches(7.05), Inches(1.9), Inches(5.55), Inches(4.5), [
            "ставок и потока заявок организация не давала — рублей нет;",
            "смена статуса в таблице вместо SQL;",
            "поиск и страницы вместо просмотра всех строк;",
            "проверка полей снижает «битые» записи;",
            "журнал даёт след без разбора логов СУБД;",
            "нельзя закладывать «экономию закупки 1С».",
        ], size=15, space=7)
        footer(slide, n, total)

    push(s_econ)

    def s_reco(slide, n, total):
        header(slide, "Вид работ 5", "Сравнение теории и практики, предложения")
        add_table(slide, Inches(0.45), Inches(1.2), Inches(12.4), [
            ("Тема", "Вывод"),
            ("Что из учёбы пригодилось",
             "Клиент/сервер, Flask/Jinja2, ORM и MySQL, сессии и роль, CSRF, хеш, экранирование, три уровня."),
            ("Чего не хватило в задании",
             "Нет Приложения 1, готовой чужой MySQL и отдельной вёрстки админки; нет ставок для рублёвого эффекта."),
            ("Что сделали иначе",
             "Схема СвязьСервис с предыдущей практики перенесена на MySQL; вёрстка не рисовалась с нуля."),
            ("Улучшить панель",
             "Убрать учебные пароли с экрана входа; бэкап MySQL; run.py без debug; учётные записи диспетчера в панели; выгрузка журнала CSV; автотесты против живого MySQL."),
        ], [Inches(3.4), Inches(9.0)], font_size=13, height=Inches(5.4))
        footer(slide, n, total)

    push(s_reco)

    def s_exp(slide, n, total):
        header(slide, "Практический опыт из п. 4 бланка", "Девять формулировок — чем подтверждены")
        add_table(slide, Inches(0.4), Inches(1.15), Inches(12.5), [
            ("Пункт опыта", "Подтверждение"),
            ("Управление разработкой с инструментальными средствами", "Git, ветки по этапам, Docker Compose, Flask, SQLAlchemy"),
            ("Сбор данных об использовании и функционировании ИС", "Журнал admin_actions и экран /admin/journal"),
            ("Программирование по требованиям ТЗ", "П. 4 бланка: маршруты, CRUD, роль, MySQL"),
            ("Критерии качества и надёжности", "Таблица в docs/testing.md"),
            ("Методика тестирования", "unittest, 23 теста; ручная таблица шаг → факт"),
            ("Состав оборудования и ПО", "Слайд «Состав средств» и docs/testing.md"),
            ("Документация по эксплуатации", "docs/operations.md и слайд эксплуатации"),
            ("Оценка качества и экономической эффективности", "Критерии без второго прогона; без выдуманных рублей"),
            ("Модификация отдельных модулей", "Отдельно: вход, списки, формы, справочники, журнал, ошибки"),
        ], [Inches(5.5), Inches(7.0)], font_size=12, height=Inches(5.55))
        footer(slide, n, total)

    push(s_exp)

    def s_docs(slide, n, total):
        header(slide, "Вид работ 6", "Отчётные документы")
        add_table(slide, Inches(0.45), Inches(1.2), Inches(12.4), [
            ("Документ по бланку", "Статус в этом комплекте"),
            ("Презентация PowerPoint согласно Приложению 1",
             "Этот файл. Приложения 1 нет — структура по видам работ 1–6 и каркасу этапа 13."),
            ("Справка, заверенная подписью и печатью (при наличии) профильной организации",
             "Не оформляется здесь. Подпись и печать не выдумываются."),
            ("Полностью оформленный комплект в lms.synergy.ru руководителю практики",
             "Загрузка — действие обучающегося после заполнения Ф.И.О., дат и справки. В репозиторий не входит."),
        ], [Inches(5.5), Inches(6.9)], font_size=14, height=Inches(3.9))
        add_text(slide, Inches(0.5), Inches(5.5), Inches(12.3), Inches(1.4),
                 "Файл в репозитории: docs/pm05-otchet-praktiki.pptx\n"
                 "Снимки экранов: docs/images/report/\n"
                 "Код панели в бланке как обязательная загрузка не назван — уточнить у руководителя, нужен ли архив проекта.",
                 size=15, color=INK)
        footer(slide, n, total)

    push(s_docs)

    def s_end(slide, n, total):
        header(slide, "Итог", "Заключение")
        add_bullets(slide, Inches(0.5), Inches(1.2), Inches(12.3), Inches(3.6), [
            "Собрана работающая панель диспетчера: вход, роль, списки, фильтры, пагинация, CRUD заявок и справочников, журнал, ошибки.",
            "Стек бланка соблюдён: Python, Flask, Jinja2, SQLAlchemy, MySQL; вёрстка предыдущей практики встроена, не нарисована заново.",
            "Зафиксированы методика тестов, состав средств, эксплуатация, оценка качества и рекомендации без выдуманных цифр.",
            "Этот отчёт закрывает вид работ 6 в части презентации PowerPoint.",
        ], size=16, space=8)
        rounded(slide, Inches(0.5), Inches(4.7), Inches(12.3), Inches(2.0), CARD, LINE)
        add_text(slide, Inches(0.75), Inches(4.85), Inches(11.8), Inches(0.35),
                 "Остаётся обучающемуся (не входит в этот файл)", size=15, bold=True, color=TEAL)
        add_text(slide, Inches(0.75), Inches(5.25), Inches(11.8), Inches(1.25),
                 "вписать Ф.И.О., группу и даты; пройти и отметить инструктажи; получить справку "
                 "от профильной организации; загрузить комплект в lms.synergy.ru. "
                 "Если выдадут Приложение 1 — сверить порядок слайдов.",
                 size=15, color=INK)
        footer(slide, n, total)

    push(s_end)

    total = len(slides_meta)
    for i, fn in enumerate(slides_meta, start=1):
        slide = blank(prs)
        fn(slide, i, total)

    prs.save(OUT)
    print(f"wrote {OUT} ({total} slides, {OUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    missing = [name for name in (
        "01-home.png", "02-login.png", "03-admin-list.png", "04-admin-filter.png",
        "06-request-new.png", "08-request-delete.png", "09-catalogs.png",
        "10-journal.png", "12-error-403.png",
    ) if not (IMG / name).is_file()]
    if missing:
        raise SystemExit("нет снимков: " + ", ".join(missing))
    build()
