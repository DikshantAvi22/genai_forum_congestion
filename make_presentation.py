from __future__ import annotations

import math
import os
import shutil
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "presentation"
SLIDE_DIR = OUT_DIR / "rendered"
TEMPLATE = ROOT / "Minproject-Presentation Slide Template.pptx"
PPTX_OUT = OUT_DIR / "Selective_Response_Forum_Congestion_Presentation.pptx"
PDF_OUT = OUT_DIR / "Selective_Response_Forum_Congestion_Presentation.pdf"
NOTES_OUT = OUT_DIR / "speaker_notes.md"

W, H = 1920, 1080
EMU_W, EMU_H = 12192000, 6858000

BLUE = "#1f4e79"
MID_BLUE = "#4472C4"
ACCENT = "#d97706"
RED = "#b91c1c"
GREEN = "#166534"
TEXT = "#14213d"
MUTED = "#5f6b7a"
BG = "#f6f8fc"
PANEL = "#ffffff"
LIGHT_BLUE = "#eaf1fb"
LIGHT_ORANGE = "#fff3e8"
LIGHT_GREEN = "#edf8f1"
LIGHT_RED = "#fdecec"
GRID = "#d9e3f0"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE_FONT = font(58, bold=True)
SUBTITLE_FONT = font(26)
BODY_FONT = font(32)
BODY_BOLD = font(32, bold=True)
SMALL_FONT = font(24)
REF_FONT = font(18)
BIG_NUM_FONT = font(44, bold=True)
BADGE_FONT = font(18, bold=True)


@dataclass
class FigureSpec:
    path: str
    x: int
    y: int
    w: int
    h: int
    caption: str | None = None
    bg: str = PANEL


def ensure_dirs() -> None:
    SLIDE_DIR.mkdir(parents=True, exist_ok=True)


def new_slide() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((40, 34, W - 40, H - 34), radius=28, fill=BG, outline="#dbe5f1", width=3)
    draw.rectangle((60, 60, W - 60, 74), fill=BLUE)
    draw.rectangle((60, H - 88, W - 60, H - 86), fill=GRID)
    return img, draw


def text_size(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    text = sanitize(text)
    box = draw.textbbox((0, 0), text, font=use_font)
    return box[2] - box[0], box[3] - box[1]


def draw_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    use_font: ImageFont.FreeTypeFont,
    fill: str = TEXT,
    max_width: int | None = None,
    line_gap: int = 8,
) -> int:
    text = sanitize(text)
    if max_width is None:
        draw.text((x, y), text, font=use_font, fill=fill)
        return text_size(draw, text, use_font)[1]

    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        w, _ = text_size(draw, candidate, use_font)
        if w <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    y_cur = y
    total = 0
    for line in lines:
        draw.text((x, y_cur), line, font=use_font, fill=fill)
        h = text_size(draw, line, use_font)[1]
        y_cur += h + line_gap
        total += h + line_gap
    return total - line_gap if total else 0


def sanitize(text: str) -> str:
    replacements = {
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "-",
        "\u2248": "~",
        "\u03c1": "rho",
        "\u0394": "Delta",
        "\u2212": "-",
        "\u03be": "xi",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def bullet_list(
    draw: ImageDraw.ImageDraw,
    items: Iterable[str],
    x: int,
    y: int,
    width: int,
    fill: str = TEXT,
    bullet_fill: str = MID_BLUE,
    use_font: ImageFont.FreeTypeFont = BODY_FONT,
    gap: int = 18,
) -> int:
    y_cur = y
    for item in items:
        draw.ellipse((x, y_cur + 12, x + 12, y_cur + 24), fill=bullet_fill)
        h = draw_text(draw, item, x + 28, y_cur, use_font, fill=fill, max_width=width - 28, line_gap=6)
        y_cur += h + gap
    return y_cur - y


def add_title(draw: ImageDraw.ImageDraw, title: str, subtitle: str | None = None) -> None:
    draw_text(draw, title, 86, 102, TITLE_FONT, fill=TEXT, max_width=1150, line_gap=6)
    if subtitle:
        draw_text(draw, subtitle, 88, 162, SUBTITLE_FONT, fill=MUTED, max_width=1250, line_gap=6)


def badge(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, fill: str, text_fill: str = "white") -> int:
    tw, th = text_size(draw, text, BADGE_FONT)
    draw.rounded_rectangle((x, y, x + tw + 28, y + th + 14), radius=14, fill=fill)
    draw.text((x + 14, y + 6), text, font=BADGE_FONT, fill=text_fill)
    return tw + 28


def panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, fill: str = PANEL, outline: str = "#d7e0eb") -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=24, fill=fill, outline=outline, width=3)


def add_footer(draw: ImageDraw.ImageDraw, refs: str, slide_no: int) -> None:
    draw_text(draw, refs, 78, H - 74, REF_FONT, fill=MUTED, max_width=1500, line_gap=4)
    n = str(slide_no)
    tw, th = text_size(draw, n, SMALL_FONT)
    draw.rounded_rectangle((W - 118, H - 82, W - 70, H - 42), radius=12, fill=LIGHT_BLUE, outline=GRID, width=2)
    draw.text((W - 94 - tw // 2, H - 71), n, font=SMALL_FONT, fill=BLUE)


def cover_image(path: str, box_w: int, box_h: int, background: str = PANEL) -> Image.Image:
    img = Image.open(ROOT / path).convert("RGB")
    src_ratio = img.width / img.height
    dst_ratio = box_w / box_h
    if src_ratio > dst_ratio:
        new_h = box_h
        new_w = int(box_h * src_ratio)
    else:
        new_w = box_w
        new_h = int(box_w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - box_w) // 2
    top = (new_h - box_h) // 2
    return img.crop((left, top, left + box_w, top + box_h))


def paste_figure(base: Image.Image, draw: ImageDraw.ImageDraw, spec: FigureSpec) -> None:
    panel(draw, spec.x, spec.y, spec.w, spec.h, fill=spec.bg)
    inner_pad = 14
    cap_h = 0 if not spec.caption else 48
    fig = cover_image(spec.path, spec.w - inner_pad * 2, spec.h - inner_pad * 2 - cap_h)
    base.paste(fig, (spec.x + inner_pad, spec.y + inner_pad))
    if spec.caption:
        draw_text(
            draw,
            spec.caption,
            spec.x + 18,
            spec.y + spec.h - 38,
            REF_FONT,
            fill=MUTED,
            max_width=spec.w - 36,
            line_gap=2,
        )


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: str = MID_BLUE, width: int = 8) -> None:
    draw.line((start, end), fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = 18
    left = (end[0] - head * math.cos(angle - math.pi / 6), end[1] - head * math.sin(angle - math.pi / 6))
    right = (end[0] - head * math.cos(angle + math.pi / 6), end[1] - head * math.sin(angle + math.pi / 6))
    draw.polygon([end, left, right], fill=fill)


def icon_box(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, body: str, fill: str, icon_fill: str) -> None:
    panel(draw, x, y, w, h, fill=fill, outline=icon_fill)
    draw.ellipse((x + 20, y + 20, x + 72, y + 72), fill=icon_fill)
    draw_text(draw, title, x + 92, y + 18, BODY_BOLD, fill=TEXT, max_width=w - 110)
    draw_text(draw, body, x + 24, y + 90, SMALL_FONT, fill=TEXT, max_width=w - 48, line_gap=4)


def build_title_slide(slide_no: int) -> Image.Image:
    img, draw = new_slide()
    title_h = draw_text(draw, "Selective Response for GenAI Under Forum Congestion", 86, 104, TITLE_FONT, fill=TEXT, max_width=770, line_gap=0)
    draw_text(draw, "Game Theory 2026 mini project", 88, 104 + title_h + 12, SUBTITLE_FONT, fill=MUTED, max_width=700, line_gap=4)
    badge_y = 104 + title_h + 68
    badge(draw, "Base paper: Taitler et al. (2025)", 88, badge_y, BLUE)
    badge(draw, "Our work: congestion + mechanism tests", 430, badge_y, ACCENT)

    draw_text(draw, "Dikshant Gupta (24108)   |   Paras Raina (24170)", 88, badge_y + 68, BODY_FONT, fill=TEXT)
    draw_text(draw, "Speaker split: Dikshant slides 1-4, Paras slides 5-9", 88, badge_y + 112, SMALL_FONT, fill=MUTED)

    panel(draw, 88, 430, 784, 430, fill=PANEL)
    draw_text(draw, "Talk in one line", 118, 458, BODY_BOLD, fill=BLUE)
    bullet_list(
        draw,
        [
            "Selective response can help long-run learning, but forums are not infinite-capacity resources.",
            "We replicate the base paper’s selective-response intuition and extend it with forum congestion and endogenous capacity.",
            "Main finding: novelty-aware routing outperforms uniform throttling, and the gain survives stricter controls.",
        ],
        118,
        506,
        720,
    )

    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/extra/seed_robustness_ST.png", 930, 250, 420, 292, "Learning gains across regimes"),
    )
    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/extra/collapse_boundary_c1_xi.png", 1390, 250, 430, 292, "Congestion creates a collapse boundary"),
    )
    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/timeseries_collapse.png", 930, 576, 890, 286, "Collapse regime example"),
    )
    add_footer(draw, "Refs: Taitler et al. (2025); Ostrom (1990); Vickrey (1969)", slide_no)
    return img


def build_problem_slide(slide_no: int) -> Image.Image:
    img, draw = new_slide()
    add_title(draw, "Problem And Why It Matters", "Routing users between GenAI and human forums changes both current service and future knowledge creation.")

    panel(draw, 86, 224, 760, 670, fill=PANEL)
    draw_text(draw, "Core problem", 116, 252, BODY_BOLD, fill=BLUE)
    bullet_list(
        draw,
        [
            "If GenAI answers everything, fewer high-value forum discussions happen, so future training signal shrinks.",
            "If GenAI defers too much, forum load rises, response quality drops, and expert capacity can collapse.",
            "The planner must manage both traffic volume and traffic composition.",
        ],
        116,
        302,
        690,
    )

    for idx, (title, body) in enumerate(
        [
            ("Course forums", "Hard questions create reusable explanations for later students."),
            ("Developer communities", "Stack Overflow style forums can be swamped by redirected users."),
            ("Product support", "Short-term automation can reduce the human knowledge pipeline."),
        ]
    ):
        y = 560 + idx * 96
        draw.rounded_rectangle((116, y, 800, y + 76), radius=16, fill=LIGHT_BLUE if idx == 0 else "#f9fbfe", outline=GRID, width=2)
        draw_text(draw, title, 138, y + 10, SMALL_FONT, fill=TEXT, max_width=170)
        draw_text(draw, body, 320, y + 10, SMALL_FONT, fill=MUTED, max_width=450, line_gap=3)

    panel(draw, 896, 224, 934, 670, fill=PANEL)
    icon_box(draw, 938, 274, 220, 160, "Users", "Choose GenAI or forum based on relative utility.", LIGHT_BLUE, MID_BLUE)
    icon_box(draw, 1250, 274, 248, 160, "GenAI", "Improves when it learns from external human knowledge.", LIGHT_ORANGE, ACCENT)
    icon_box(draw, 1580, 274, 210, 160, "Forum", "Produces knowledge, but only if capacity remains healthy.", LIGHT_GREEN, GREEN)
    draw_arrow(draw, (1160, 355), (1246, 355), fill=MID_BLUE)
    draw_arrow(draw, (1498, 355), (1574, 355), fill=ACCENT)
    draw_arrow(draw, (1685, 442), (1340, 560), fill=GREEN)

    draw.rounded_rectangle((1040, 534, 1688, 710), radius=22, fill=LIGHT_RED, outline=RED, width=3)
    draw_text(draw, "Congestion risk", 1074, 560, BODY_BOLD, fill=RED)
    bullet_list(
        draw,
        [
            "Load above capacity reduces useful throughput.",
            "Repeated overload damages future capacity.",
            "This creates tipping behavior instead of smooth decline.",
        ],
        1074,
        610,
        560,
        bullet_fill=RED,
        use_font=SMALL_FONT,
        gap=10,
    )

    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/timeseries_stable.png", 930, 736, 430, 128, "Healthy regime"),
    )
    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/timeseries_collapse.png", 1394, 736, 426, 128, "Collapsed regime"),
    )
    add_footer(draw, "Refs: Taitler et al. (2025); Hardin (1968); Ostrom (1990); Vickrey (1969)", slide_no)
    return img


def build_literature_slide(slide_no: int) -> Image.Image:
    img, draw = new_slide()
    add_title(draw, "Literature Review", "Our project sits at the intersection of selective response, human-AI delegation, and congestion economics.")

    icon_box(draw, 86, 250, 552, 540, "Selective response / reject option", "Chow (1970), El-Yaniv (2010), Geifman and El-Yaniv (2017): when not to answer is part of the decision rule.", LIGHT_BLUE, MID_BLUE)
    icon_box(draw, 684, 250, 552, 540, "Learning to defer / human-AI systems", "Madras et al. (2018), Mozannar and Sontag (2020), Kleinberg et al. (2018), Amershi et al. (2014): defer to humans when they add value.", LIGHT_ORANGE, ACCENT)
    icon_box(draw, 1282, 250, 552, 540, "Congestion / shared-resource view", "Hardin (1968), Ostrom (1990), Kleinrock (1975), Vickrey (1969), Roughgarden and Tardos (2006): overloaded shared systems degrade.", LIGHT_GREEN, GREEN)

    draw.rounded_rectangle((250, 828, 1420, 912), radius=24, fill=PANEL, outline=GRID, width=2)
    draw_text(draw, "Gap addressed by this project: prior selective-response work models knowledge creation, but not forum congestion and endogenous capacity loss.", 286, 850, BODY_BOLD, fill=TEXT, max_width=1090, line_gap=5)
    badge(draw, "This gap motivates our extension", 1464, 840, ACCENT)

    add_footer(draw, "Refs: Chow (1970); El-Yaniv (2010); Madras et al. (2018); Mozannar and Sontag (2020); Hardin (1968); Ostrom (1990); Kleinrock (1975)", slide_no)
    return img


def build_base_paper_slide(slide_no: int) -> Image.Image:
    img, draw = new_slide()
    add_title(draw, "Base Paper: Idea And Limits", "Selective-response intuition comes from the prior paper; congestion modeling does not.")
    badge(draw, "Replication / prior work", 88, 214, BLUE)

    panel(draw, 86, 258, 576, 610)
    draw_text(draw, "What the base paper studies", 118, 286, BODY_BOLD, fill=BLUE)
    bullet_list(
        draw,
        [
            "Question: should GenAI answer every query, or selectively defer some users to human communities?",
            "Key claim: answering less can improve long-run learning because deferred interactions create future human-generated knowledge.",
            "Interpretation: abstention is not only about current accuracy; it also shapes the future data ecosystem.",
        ],
        118,
        336,
        500,
    )

    panel(draw, 702, 258, 510, 610, fill=LIGHT_BLUE)
    draw_text(draw, "Base paper takeaway", 734, 286, BODY_BOLD, fill=BLUE)
    draw.rounded_rectangle((776, 388, 1138, 500), radius=28, fill="#ffffff", outline=MID_BLUE, width=4)
    draw_text(draw, "Always answer", 818, 414, SMALL_FONT, fill=TEXT, max_width=250)
    draw_text(draw, "Less human discussion", 818, 452, SMALL_FONT, fill=MUTED, max_width=260)
    draw.rounded_rectangle((776, 612, 1138, 724), radius=28, fill="#ffffff", outline=GREEN, width=4)
    draw_text(draw, "Selective response", 812, 638, SMALL_FONT, fill=TEXT, max_width=270)
    draw_text(draw, "More future signal", 812, 676, SMALL_FONT, fill=MUTED, max_width=230)
    draw_arrow(draw, (958, 608), (958, 506), fill=GREEN)
    draw_text(draw, "Qualitative result: some deferral can beat always-answering in long-run learning.", 734, 770, SMALL_FONT, fill=TEXT, max_width=430, line_gap=4)

    panel(draw, 1252, 258, 578, 610, fill=LIGHT_RED)
    draw_text(draw, "Why that is not enough for our setting", 1284, 286, BODY_BOLD, fill=RED, max_width=500)
    bullet_list(
        draw,
        [
            "Forum is treated as an implicit knowledge source, not a congestible shared resource.",
            "No endogenous forum capacity or collapse dynamics.",
            "No test of whether targeted gains survive when answered share is matched.",
            "No mechanism ablation to verify that novelty is the real source of the gain.",
        ],
        1284,
        352,
        500,
        bullet_fill=RED,
    )
    add_footer(draw, "Refs: Taitler et al. (2025); Chow (1970); El-Yaniv (2010)", slide_no)
    return img


def build_method_slide(slide_no: int) -> Image.Image:
    img, draw = new_slide()
    add_title(draw, "Our Original Work: Methodology", "We extend the base idea with congestion dynamics, new baselines, and mechanism-validation experiments.")
    badge(draw, "Our extension", 88, 214, ACCENT)

    panel(draw, 86, 258, 1160, 610)
    draw_text(draw, "Extended simulator", 118, 286, BODY_BOLD, fill=ACCENT)
    draw.rounded_rectangle((130, 354, 380, 484), radius=22, fill=LIGHT_BLUE, outline=MID_BLUE, width=3)
    draw_text(draw, "Users", 190, 388, BODY_BOLD, fill=TEXT)
    draw_text(draw, "choice share", 168, 430, SMALL_FONT, fill=MUTED)
    draw.rounded_rectangle((410, 354, 674, 484), radius=22, fill=LIGHT_ORANGE, outline=ACCENT, width=3)
    draw_text(draw, "GenAI", 500, 388, BODY_BOLD, fill=TEXT)
    draw_text(draw, "answered share", 458, 430, SMALL_FONT, fill=MUTED)
    draw.rounded_rectangle((754, 354, 1040, 484), radius=22, fill=LIGHT_GREEN, outline=GREEN, width=3)
    draw_text(draw, "Forum", 858, 388, BODY_BOLD, fill=TEXT)
    draw_text(draw, "throughput + novelty", 792, 430, SMALL_FONT, fill=MUTED)
    draw.rounded_rectangle((1028, 354, 1208, 484), radius=22, fill=LIGHT_RED, outline=RED, width=3)
    draw_text(draw, "C_t", 1088, 388, BODY_BOLD, fill=TEXT)
    draw_text(draw, "capacity", 1064, 430, SMALL_FONT, fill=MUTED)
    draw_arrow(draw, (382, 420), (408, 420), fill=MID_BLUE)
    draw_arrow(draw, (676, 420), (752, 420), fill=ACCENT)
    draw_arrow(draw, (1042, 420), (1210, 420), fill=GREEN)
    draw_arrow(draw, (1120, 494), (918, 552), fill=RED)
    draw_text(draw, "Overload damages future capacity", 808, 560, SMALL_FONT, fill=RED)

    draw.rounded_rectangle((130, 610, 1072, 804), radius=20, fill="#ffffff", outline=GRID, width=2)
    draw_text(draw, "Key policies compared", 156, 632, BODY_BOLD, fill=TEXT)
    bullet_list(
        draw,
        [
            "Uniform throttling: fixed answer rate.",
            "Targeted novelty policy: answer low-novelty items, defer high-novelty items.",
            "Capacity-aware baseline: answer more when recent overload is high.",
            "Novelty+capacity baseline: combine composition and congestion feedback.",
        ],
        156,
        678,
        970,
        bullet_fill=ACCENT,
        use_font=SMALL_FONT,
        gap=10,
    )

    panel(draw, 1290, 258, 540, 610)
    draw_text(draw, "Experiment design", 1322, 286, BODY_BOLD, fill=ACCENT)
    draw_text(draw, "40-round deterministic simulator", 1322, 346, BODY_BOLD, fill=TEXT, max_width=430, line_gap=4)
    draw_text(draw, "30 novelty seeds per comparison", 1322, 406, BODY_BOLD, fill=TEXT, max_width=430, line_gap=4)
    draw_text(draw, "3 regimes: stable, mid, collapse", 1322, 466, BODY_BOLD, fill=TEXT, max_width=430, line_gap=4)
    draw_text(draw, "New checks we added", 1322, 570, BODY_BOLD, fill=TEXT)
    bullet_list(
        draw,
        [
            "Matched answered-share control",
            "rho=0 ablation to switch off novelty",
            "Collapse boundary in (C1, xi) plane",
        ],
        1322,
        620,
        430,
        bullet_fill=ACCENT,
        use_font=SMALL_FONT,
        gap=10,
    )
    add_footer(draw, "Refs: Taitler et al. (2025); project simulator in sim/model.py, sim/policies.py, sim/run_experiments.py", slide_no)
    return img


def build_main_results_slide(slide_no: int) -> Image.Image:
    img, draw = new_slide()
    add_title(draw, "Main Results", "Novelty-aware targeting beats uniform throttling across stable, mid, and collapse regimes.")
    badge(draw, "Our result", 88, 214, ACCENT)

    panel(draw, 86, 260, 520, 604)
    draw_text(draw, "Headline numbers", 118, 288, BODY_BOLD, fill=ACCENT)
    bullet_list(
        draw,
        [
            "Stable regime: S_T rises from 26.15 to 36.29.",
            "Mid regime: S_T rises from 19.60 to 31.56 and overload drops from 40 to 25 rounds.",
            "Collapse regime: learning still improves from 6.68 to 9.54, but overload remains saturated.",
        ],
        118,
        338,
        450,
        bullet_fill=ACCENT,
    )
    draw_text(draw, "Interpretation", 118, 578, BODY_BOLD, fill=TEXT)
    draw_text(draw, "Targeting helps most when the forum is still productive enough for traffic composition to matter.", 118, 628, SMALL_FONT, fill=MUTED, max_width=440, line_gap=4)

    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/extra/seed_robustness_ST.png", 646, 260, 568, 604, "Final learning across 30 seeds"),
    )
    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/extra/seed_robustness_overload.png", 1254, 260, 578, 604, "Overload-time comparison"),
    )
    add_footer(draw, "Refs: seed_robustness.csv; Taitler et al. (2025)", slide_no)
    return img


def build_validation_slide(slide_no: int) -> Image.Image:
    img, draw = new_slide()
    add_title(draw, "Mechanism Validation", "We tested whether the targeted gain is real, not just an artifact of adoption or answer volume.")
    badge(draw, "Our result", 88, 214, ACCENT)

    panel(draw, 86, 260, 520, 604)
    draw_text(draw, "Two strongest checks", 118, 288, BODY_BOLD, fill=ACCENT)
    bullet_list(
        draw,
        [
            "Matched answered share: both policies answer about 0.178 of users, but targeted still reaches S_T = 31.35 vs 20.58 for uniform.",
            "rho ablation: when novelty has no effect (rho = 0), the targeted advantage becomes exactly zero.",
            "Conclusion: the gain comes from sending better traffic to the forum, not just changing total answered volume.",
        ],
        118,
        338,
        450,
        bullet_fill=ACCENT,
    )

    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/extra/matched_answered_compare_ST.png", 646, 260, 568, 604, "Matched answered-share control"),
    )
    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/extra/rho_ablation_gap_ST.png", 1254, 260, 578, 604, "rho ablation"),
    )
    add_footer(draw, "Refs: matched_answered_compare.csv; rho_ablation.csv", slide_no)
    return img


def build_extended_slide(slide_no: int) -> Image.Image:
    img, draw = new_slide()
    add_title(draw, "Stronger Baselines And Tipping", "Congestion feedback helps, but novelty+capacity performs best in the mid regime.")
    badge(draw, "Our result", 88, 214, ACCENT)

    panel(draw, 86, 260, 520, 604)
    draw_text(draw, "Mid-regime policy ranking", 118, 288, BODY_BOLD, fill=ACCENT)
    bullet_list(
        draw,
        [
            "Uniform: S_T = 19.60, overload = 40.",
            "Capacity-aware: S_T = 22.52, overload = 25.",
            "Targeted novelty: S_T = 31.56, overload = 25.",
            "Novelty+capacity: S_T = 33.23, overload = 18.",
        ],
        118,
        336,
        450,
        bullet_fill=ACCENT,
        use_font=SMALL_FONT,
        gap=10,
    )
    draw_text(draw, "Phase transition", 118, 602, BODY_BOLD, fill=TEXT)
    draw_text(draw, "First collapse points appear near C1 ≈ 0.364 and xi ≈ 0.074. Higher overload damage requires higher initial forum capacity.", 118, 650, SMALL_FONT, fill=MUTED, max_width=430, line_gap=4)

    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/extra/policy_compare_extended_ST.png", 646, 260, 568, 604, "Extended policy comparison"),
    )
    paste_figure(
        img,
        draw,
        FigureSpec("sim/figs/extra/collapse_boundary_c1_xi.png", 1254, 260, 578, 604, "Explicit collapse boundary"),
    )
    add_footer(draw, "Refs: policy_compare_extended.csv; collapse_boundary_c1_xi.csv", slide_no)
    return img


def build_summary_slide(slide_no: int) -> Image.Image:
    img, draw = new_slide()
    add_title(draw, "Summary And Future Work", "References are listed on this slide; our contribution remains distinct from the base paper.")

    panel(draw, 86, 250, 580, 650)
    draw_text(draw, "Summary", 118, 278, BODY_BOLD, fill=BLUE)
    bullet_list(
        draw,
        [
            "Base paper insight: answering less can improve long-run learning.",
            "Our extension: forums are congestible, so routing must consider both quantity and quality of deferred traffic.",
            "Main result: novelty-aware routing dominates uniform throttling and survives strict controls.",
            "Best baseline in our mid regime combines novelty with congestion feedback.",
        ],
        118,
        328,
        500,
        bullet_fill=BLUE,
        use_font=SMALL_FONT,
        gap=12,
    )

    panel(draw, 712, 250, 540, 650, fill=LIGHT_ORANGE)
    draw_text(draw, "Future work", 744, 278, BODY_BOLD, fill=ACCENT)
    bullet_list(
        draw,
        [
            "Estimate parameters from real forum data instead of reduced-form calibration.",
            "Replace hand-designed rules with learned routing policies.",
            "Model heterogeneous experts, delayed retraining, and multiple forums.",
            "Optimize jointly for learning, welfare, and revenue instead of one metric.",
        ],
        744,
        328,
        460,
        bullet_fill=ACCENT,
        use_font=SMALL_FONT,
        gap=12,
    )

    panel(draw, 1298, 250, 532, 650, fill=LIGHT_GREEN)
    draw_text(draw, "References used in the talk", 1330, 278, BODY_BOLD, fill=GREEN, max_width=460)
    refs = [
        "Taitler et al. (2025)",
        "Chow (1970)",
        "El-Yaniv (2010)",
        "Madras et al. (2018)",
        "Mozannar and Sontag (2020)",
        "Hardin (1968)",
        "Ostrom (1990)",
        "Vickrey (1969)",
        "Kleinrock (1975)",
    ]
    y = 336
    for ref in refs:
        draw_text(draw, f"• {ref}", 1334, y, SMALL_FONT, fill=TEXT, max_width=430, line_gap=4)
        y += 48

    draw.rounded_rectangle((86, 924, 1748, 984), radius=20, fill=PANEL, outline=GRID, width=2)
    draw_text(draw, "Practice target for 8 minutes: ~45-55 seconds per slide. Keep slide 4 explicitly labeled as prior work and slides 5-8 as our contribution.", 116, 942, SMALL_FONT, fill=MUTED, max_width=1590, line_gap=3)
    add_footer(draw, "Refs: full bibliography in refs.bib; slide cites shown inline throughout the deck", slide_no)
    return img


def build_notes() -> str:
    return """# Speaker Notes And Timing

Total target: 8 minutes

1. Slide 1 (0:00-0:45) - Dikshant
   Introduce the question, the base paper, and the main message of our extension.
2. Slide 2 (0:45-1:35) - Dikshant
   Explain why always-answer vs always-defer is a systems problem with real examples.
3. Slide 3 (1:35-2:15) - Dikshant
   Place the work in selective response, defer-to-human, and congestion literature.
4. Slide 4 (2:15-3:00) - Dikshant
   State clearly what belongs to the base paper and what its limitations are.
5. Slide 5 (3:00-3:55) - Paras
   Present our simulator extension, policies, and evaluation design.
6. Slide 6 (3:55-4:50) - Paras
   Present the main results across stable, mid, and collapse regimes.
7. Slide 7 (4:50-5:45) - Paras
   Explain matched answered-share and rho=0 as mechanism-validation checks.
8. Slide 8 (5:45-6:40) - Paras
   Present stronger baselines and the collapse boundary.
9. Slide 9 (6:40-8:00) - Both
   Paras gives summary and future work; Dikshant closes with contribution split and references.
"""


def build_slides() -> list[Path]:
    builders = [
        build_title_slide,
        build_problem_slide,
        build_literature_slide,
        build_base_paper_slide,
        build_method_slide,
        build_main_results_slide,
        build_validation_slide,
        build_extended_slide,
        build_summary_slide,
    ]
    paths: list[Path] = []
    for i, builder in enumerate(builders, start=1):
        img = builder(i)
        out = SLIDE_DIR / f"slide_{i:02d}.png"
        img.save(out, quality=95)
        paths.append(out)
    return paths


def build_pdf(slides: list[Path]) -> None:
    imgs = [Image.open(path).convert("RGB") for path in slides]
    first, rest = imgs[0], imgs[1:]
    first.save(PDF_OUT, save_all=True, append_images=rest, resolution=200.0)


def slide_xml(rel_id: str = "rId2") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:pic>
        <p:nvPicPr><p:cNvPr id="2" name="SlideImage"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>
        <p:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
        <p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{EMU_W}" cy="{EMU_H}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
      </p:pic>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


def slide_rels_xml(target: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{target}"/>
</Relationships>
"""


def update_pptx(slides: list[Path]) -> None:
    ensure_dirs()
    tmp = OUT_DIR / "_tmp_template.pptx"
    shutil.copyfile(TEMPLATE, tmp)

    ns_rel = "http://schemas.openxmlformats.org/package/2006/relationships"
    ns_p = "http://schemas.openxmlformats.org/presentationml/2006/main"
    ET.register_namespace("", ns_rel)
    ET.register_namespace("a", "http://schemas.openxmlformats.org/drawingml/2006/main")
    ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
    ET.register_namespace("p", ns_p)

    with zipfile.ZipFile(tmp, "r") as zin, zipfile.ZipFile(PPTX_OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        skip_prefixes = {"ppt/slides/", "ppt/media/slide_", "ppt/slides/_rels/"}
        for item in zin.infolist():
            if any(item.filename.startswith(prefix) for prefix in skip_prefixes):
                continue
            if item.filename in {"ppt/presentation.xml", "ppt/_rels/presentation.xml.rels", "[Content_Types].xml", "docProps/app.xml"}:
                continue
            zout.writestr(item, zin.read(item.filename))

        # Content types
        ct_root = ET.fromstring(zin.read("[Content_Types].xml"))
        ns_ct = {"ct": "http://schemas.openxmlformats.org/package/2006/content-types"}
        for override in list(ct_root.findall("ct:Override", ns_ct)):
            part = override.attrib.get("PartName", "")
            if part.startswith("/ppt/slides/slide"):
                ct_root.remove(override)
        for i in range(1, len(slides) + 1):
            el = ET.Element("{http://schemas.openxmlformats.org/package/2006/content-types}Override")
            el.attrib["PartName"] = f"/ppt/slides/slide{i}.xml"
            el.attrib["ContentType"] = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
            ct_root.append(el)
        zout.writestr("[Content_Types].xml", ET.tostring(ct_root, encoding="utf-8", xml_declaration=True))

        # Presentation rels
        rel_root = ET.fromstring(zin.read("ppt/_rels/presentation.xml.rels"))
        for rel in list(rel_root):
            if rel.attrib.get("Type", "").endswith("/slide"):
                rel_root.remove(rel)
        slide_rel_ids: list[str] = []
        for i in range(1, len(slides) + 1):
            rel = ET.Element("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
            rel_id = f"rId{20 + i}"
            slide_rel_ids.append(rel_id)
            rel.attrib.update(
                {
                    "Id": rel_id,
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
                    "Target": f"slides/slide{i}.xml",
                }
            )
            rel_root.append(rel)
        zout.writestr("ppt/_rels/presentation.xml.rels", ET.tostring(rel_root, encoding="utf-8", xml_declaration=True))

        # Presentation xml
        pres_root = ET.fromstring(zin.read("ppt/presentation.xml"))
        sld_id_lst = pres_root.find(f"{{{ns_p}}}sldIdLst")
        assert sld_id_lst is not None
        for child in list(sld_id_lst):
            sld_id_lst.remove(child)
        for i, rel_id in enumerate(slide_rel_ids, start=1):
            el = ET.Element(f"{{{ns_p}}}sldId")
            el.attrib["id"] = str(255 + i)
            el.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"] = rel_id
            sld_id_lst.append(el)
        zout.writestr("ppt/presentation.xml", ET.tostring(pres_root, encoding="utf-8", xml_declaration=True))

        # app.xml
        app_root = ET.fromstring(zin.read("docProps/app.xml"))
        ns_app = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"
        slides_el = app_root.find(f"{ns_app}Slides")
        if slides_el is not None:
            slides_el.text = str(len(slides))
        zout.writestr("docProps/app.xml", ET.tostring(app_root, encoding="utf-8", xml_declaration=True))

        # Write slides and media
        for i, slide_path in enumerate(slides, start=1):
            media_name = f"slide_{i:02d}.png"
            zout.writestr(f"ppt/slides/slide{i}.xml", slide_xml())
            zout.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", slide_rels_xml(media_name))
            with open(slide_path, "rb") as fh:
                zout.writestr(f"ppt/media/{media_name}", fh.read())

    tmp.unlink(missing_ok=True)


def main() -> None:
    ensure_dirs()
    slides = build_slides()
    build_pdf(slides)
    update_pptx(slides)
    NOTES_OUT.write_text(build_notes(), encoding="utf-8")
    print(f"Wrote {len(slides)} slides")
    print(PPTX_OUT)
    print(PDF_OUT)
    print(NOTES_OUT)


if __name__ == "__main__":
    main()
