"""Рисует 4 слайда одного размера и сохраняет несжатый PNG и сжатые копии."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 675
CREAM = (244, 240, 230)
AMBER = (231, 177, 90)
INK = (8, 40, 38)


def load_font(size, bold=False):
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path(r"C:\Windows\Fonts") / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def canvas(color):
    image = Image.new("RGB", (W, H), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, H - 150, W, H), fill=INK)
    return image, draw


def slide_connect():
    image, draw = canvas((11, 79, 74))
    draw.line((80, 340, 460, 340), fill=AMBER, width=14)
    draw.rectangle((460, 250, 740, 400), fill=CREAM)
    draw.polygon([(440, 250), (600, 130), (760, 250)], fill=AMBER)
    draw.rectangle((560, 310, 640, 400), fill=(11, 79, 74))
    draw.rectangle((500, 290, 560, 350), fill=(11, 79, 74))
    return image


def slide_repair():
    image, draw = canvas((20, 60, 79))
    draw.line((120, 330, 500, 330), fill=CREAM, width=16)
    draw.line((700, 330, 1080, 330), fill=CREAM, width=16)
    draw.rounded_rectangle((520, 270, 680, 390), radius=24, fill=AMBER)
    draw.ellipse((250, 250, 330, 330), outline=CREAM, width=8)
    draw.ellipse((860, 250, 940, 330), outline=CREAM, width=8)
    return image


def slide_router():
    image, draw = canvas((29, 70, 52))
    draw.rounded_rectangle((300, 250, 900, 430), radius=28, fill=CREAM)
    for x in (380, 470, 560, 650):
        draw.ellipse((x, 310, x + 36, 346), fill=(11, 79, 74))
    draw.line((470, 250, 430, 140), fill=AMBER, width=10)
    draw.line((730, 250, 770, 140), fill=AMBER, width=10)
    return image


def slide_visit():
    image, draw = canvas((61, 52, 40))
    draw.ellipse((250, 150, 490, 390), outline=CREAM, width=18)
    draw.ellipse((330, 230, 410, 310), fill=AMBER)
    draw.polygon([(370, 390), (330, 470), (410, 470)], fill=CREAM)
    draw.rounded_rectangle((620, 170, 980, 470), radius=20, fill=CREAM)
    draw.rectangle((620, 170, 980, 250), fill=AMBER)
    return image


def main():
    slides = [slide_connect(), slide_repair(), slide_router(), slide_visit()]
    before = ROOT / "docs" / "images" / "before"
    after = ROOT / "docs" / "images" / "after"
    public = ROOT / "static" / "img"
    for folder in (before, after, public):
        folder.mkdir(parents=True, exist_ok=True)

    rows = []
    for index, image in enumerate(slides, start=1):
        raw = before / f"slide-{index}.png"
        jpg = after / f"slide-{index}.jpg"
        webp = after / f"slide-{index}.webp"
        image.save(raw, format="PNG", compress_level=0)
        image.save(jpg, format="JPEG", quality=78, optimize=True)
        image.save(webp, format="WEBP", quality=78, method=6)
        public_jpg = public / f"slide-{index}.jpg"
        public_jpg.write_bytes(jpg.read_bytes())
        rows.append((index, raw.stat().st_size, jpg.stat().st_size, webp.stat().st_size))

    lines = [
        "# Оптимизация изображений",
        "",
        "Все четыре слайда имеют размер 1200×675 px. В интерфейсе стоит JPEG: он заметно легче несжатого PNG и выглядит так же, потому что рисунок плоский.",
        "",
        "| Слайд | PNG до, байт | JPEG после, байт | WebP, байт |",
        "| --- | ---: | ---: | ---: |",
    ]
    for index, raw, jpg, webp in rows:
        lines.append(f"| {index} | {raw} | {jpg} | {webp} |")
    lines.append("")
    lines.append("Исходники: `docs/images/before`. Сжатые копии: `docs/images/after` и `static/img`.")
    lines.append("")
    (ROOT / "docs" / "images" / "optimization.md").write_text("\n".join(lines), encoding="utf-8")
    for index, raw, jpg, webp in rows:
        print(f"slide {index}: png {raw} jpg {jpg} webp {webp}")


if __name__ == "__main__":
    main()
