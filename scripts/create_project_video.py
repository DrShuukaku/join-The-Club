"""Render a short, self-contained animated overview of the school app."""

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "attached_assets" / "school_paperwork_overview.mp4"
W, H, FPS = 1280, 720, 15
SCENE_SECONDS = 4
SCENES = 7
BG = "#101c2a"
PANEL = "#1c2b3b"
WHITE = "#f8f4ec"
MUTED = "#afbbc7"
RED = "#d84755"
GOLD = "#f1d28b"
GREEN = "#9dd9bf"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
REGULAR = str(FONT_DIR / "DejaVuSans.ttf")
BOLD = str(FONT_DIR / "DejaVuSans-Bold.ttf")
FONTS = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in FONTS:
        FONTS[key] = ImageFont.truetype(BOLD if bold else REGULAR, size)
    return FONTS[key]


def smooth(x):
    x = max(0, min(1, x))
    return x * x * (3 - 2 * x)


def text(draw, xy, value, size=30, color=WHITE, bold=False, anchor=None):
    draw.text(xy, value, fill=color, font=font(size, bold), anchor=anchor)


def box(draw, coords, fill=PANEL, radius=20, outline=None, width=2):
    draw.rounded_rectangle(coords, radius=radius, fill=fill, outline=outline, width=width)


def top(draw, section, index, progress):
    text(draw, (70, 51), "SCHOOL  /  PAPERWORK", 19, GOLD, True)
    text(draw, (1210, 51), section.upper(), 15, MUTED, True, "ra")
    draw.rectangle((70, 672, 1210, 675), fill="#344251")
    draw.rectangle((70, 672, 70 + 1140 * progress, 675), fill=RED)
    text(draw, (70, 692), f"{index + 1:02d} / 07", 14, MUTED)
    text(draw, (1210, 692), "ILLUSTRATIVE OVERVIEW", 12, MUTED, anchor="ra")


def heading(draw, title, subtitle, entered):
    y = int(100 + 24 * (1 - entered))
    text(draw, (70, y), title, 47, WHITE, True)
    text(draw, (72, y + 68), subtitle, 21, MUTED)


def pill(draw, x, y, label, active=False, width=None):
    width = width or (len(label) * 12 + 40)
    box(draw, (x, y, x + width, y + 48),
        fill=RED if active else "#2d3b49", radius=24)
    text(draw, (x + width / 2, y + 24), label, 18,
         WHITE if active else MUTED, True, "mm")
    return width


def card(draw, x, y, w, h, tag, title, body, accent=RED):
    box(draw, (x, y, x + w, y + h), outline="#415061")
    draw.rounded_rectangle((x + 22, y + 23, x + 29, y + 60),
                           radius=3, fill=accent)
    text(draw, (x + 46, y + 29), tag.upper(), 16, accent, True)
    text(draw, (x + 24, y + 90), title, 25, WHITE, True)
    for line_no, line in enumerate(body):
        text(draw, (x + 24, y + 136 + 29 * line_no), line, 19, MUTED)


def draw_scene(draw, scene, local, frame):
    enter = smooth(local / 0.8)
    reveal = smooth((local - 0.55) / 0.7)
    drift = math.sin(frame / FPS * 1.5)

    if scene == 0:
        top(draw, "A simpler school day", scene, (scene + local / 4) / SCENES)
        draw.ellipse((805 + 12 * drift, 155, 1125 + 12 * drift, 475),
                     outline="#4d3744", width=2)
        draw.ellipse((848 + 8 * drift, 198, 1082 + 8 * drift, 432),
                     outline=RED, width=4)
        box(draw, (903 + 8 * drift, 258, 1027 + 8 * drift, 378),
            fill=RED, radius=29)
        text(draw, (965 + 8 * drift, 318), "✓", 75, WHITE, True, "mm")
        text(draw, (70, 168 + 28 * (1 - enter)), "One place for", 58, WHITE, True)
        text(draw, (70, 246 + 28 * (1 - enter)), "school paperwork", 58, WHITE, True)
        text(draw, (70, 324 + 28 * (1 - enter)), "and volunteering.", 58, GOLD, True)
        text(draw, (73, 444), "A quick look at the parent and admin experience.",
             23, MUTED)
        pill(draw, 73, 513, "PARENTS", True, 145)
        pill(draw, 230, 513, "ADMINISTRATORS", False, 245)

    elif scene == 1:
        top(draw, "For parents", scene, (scene + local / 4) / SCENES)
        heading(draw, "A dashboard built for parents",
                "Everything important is easy to find.", enter)
        box(draw, (70, 250, 1210, 600), outline="#415061")
        text(draw, (100, 284), "Dashboard", 23, GOLD, True)
        text(draw, (950, 285), "Notifications", 17, MUTED)
        text(draw, (1125, 285), "Parent name", 16, MUTED)
        draw.line((100, 326, 1180, 326), fill="#415061", width=2)
        labels = [("My Forms", 170), ("Jobs", 115), ("Labor Hours", 185),
                  ("Profile", 145)]
        x = 100
        for i, (label, width) in enumerate(labels):
            pill(draw, x, 355, label, i == int(local * 1.1) % 4, width)
            x += width + 18
        text(draw, (102, 456), "Welcome to your school hub", 31, WHITE, True)
        text(draw, (102, 514), "Forms, opportunities, hours and profile — together.",
             21, MUTED)

    elif scene == 2:
        top(draw, "Forms + jobs", scene, (scene + local / 4) / SCENES)
        heading(draw, "Stay on top of what matters",
                "Complete forms and discover volunteer opportunities.", enter)
        slide = int(36 * (1 - reveal))
        card(draw, 70, 274 + slide, 540, 284, "My Forms",
             "Review & submit", ["See pending forms and deadlines.",
                                  "Revisit what you have submitted."], GOLD)
        card(draw, 640, 274 + slide, 570, 284, "Jobs",
             "Find a way to help", ["Explore posted volunteer jobs.",
                                    "Sign up for eligible opportunities."], GREEN)
        pill(draw, 84, 584, "PARENT EXPERIENCE", True, 255)

    elif scene == 3:
        top(draw, "Labor hours", scene, (scene + local / 4) / SCENES)
        heading(draw, "Make every hour count",
                "Parents record sessions; admins verify them.", enter)
        steps = [("01", "Check in", "Start a work session."),
                 ("02", "Check out", "Record time worked."),
                 ("03", "Verify", "Admin confirms hours.")]
        for i, (num, title, sub) in enumerate(steps):
            x = 70 + i * 388
            active = local >= i * 0.82
            box(draw, (x, 295, x + 355, 544), outline=RED if active else "#415061",
                width=3 if active else 2)
            text(draw, (x + 26, 330), num, 23, GOLD, True)
            text(draw, (x + 26, 402), title, 29, WHITE, True)
            text(draw, (x + 26, 460), sub, 17, MUTED)
            if i < 2:
                text(draw, (x + 371, 403), "›", 35, GOLD, True, "mm")
        text(draw, (72, 590), "A clear record for parents and school staff.",
             20, MUTED)

    elif scene == 4:
        top(draw, "For administrators", scene, (scene + local / 4) / SCENES)
        heading(draw, "An organized admin dashboard",
                "Key reviews are gathered under Dashboard.", enter)
        box(draw, (70, 250, 1210, 607), outline="#415061")
        x = 99
        for i, (label, width) in enumerate(
            [("Overview", 165), ("Applications", 198), ("Verify Parents", 226),
             ("Labor Verification", 276)]
        ):
            pill(draw, x, 289, label, int(local * 0.95) % 4 == i, width)
            x += width + 12
        draw.line((100, 363, 1180, 363), fill="#415061", width=2)
        text(draw, (103, 401), "Review forms", 27, WHITE, True)
        text(draw, (103, 452), "Manage applications", 27, WHITE, True)
        text(draw, (103, 503), "Verify eligibility & hours", 27, WHITE, True)
        box(draw, (797, 399, 1158, 550), fill="#283b4a")
        text(draw, (825, 440), "JOBS", 18, GOLD, True)
        text(draw, (825, 481), "SERVICE HOURS", 18, GOLD, True)
        text(draw, (825, 523), "AT A GLANCE", 18, GREEN, True)

    elif scene == 5:
        top(draw, "Service hours", scene, (scene + local / 4) / SCENES)
        heading(draw, "See service activity clearly",
                "Admin summaries and records stay connected.", enter)
        box(draw, (70, 251, 1210, 599), outline="#415061")
        text(draw, (102, 285), "SERVICE HOURS  /  OVERVIEW", 19, GOLD, True)
        draw.line((102, 334, 1175, 334), fill="#415061", width=2)
        for i, (name, descriptor) in enumerate(
            [("Parent summaries", "Hours across families"),
             ("Recent activity", "Session history"),
             ("Verification", "Confirm recorded work")]
        ):
            y = 356 + i * 73
            draw.ellipse((103, y + 11, 133, y + 41), fill=RED if i == 0 else "#3c5360")
            text(draw, (155, y + 6), name, 24, WHITE, True)
            text(draw, (1136, y + 11), descriptor, 17, MUTED, anchor="ra")
            if i < 2:
                draw.line((102, y + 61, 1175, y + 61), fill="#334453", width=1)

    else:
        top(draw, "School Paperwork", scene, (scene + local / 4) / SCENES)
        cx, cy = 640, 218
        draw.ellipse((cx - 68, cy - 68, cx + 68, cy + 68), fill=RED)
        text(draw, (cx, cy), "✓", 77, WHITE, True, "mm")
        text(draw, (640, 339), "Less paperwork.", 59, WHITE, True, "mm")
        text(draw, (640, 419), "More time for school.", 59, GOLD, True, "mm")
        text(draw, (640, 523), "Forms  •  Jobs  •  Labor hours  •  Verification",
             22, MUTED, anchor="mm")


def render():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
        "-pixel_format", "rgb24", "-video_size", f"{W}x{H}",
        "-framerate", str(FPS), "-i", "-", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(OUTPUT),
    ]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for frame in range(SCENES * SCENE_SECONDS * FPS):
            scene = frame // (SCENE_SECONDS * FPS)
            local = frame % (SCENE_SECONDS * FPS) / FPS
            image = Image.new("RGB", (W, H), BG)
            draw = ImageDraw.Draw(image)
            draw_scene(draw, scene, local, frame)
            # Brief dark crossfade at scene boundaries.
            edge = min(local, SCENE_SECONDS - local)
            if edge < 0.23:
                alpha = int(125 * (1 - smooth(edge / 0.23)))
                image = Image.blend(image, Image.new("RGB", (W, H), BG), alpha / 255)
            process.stdin.write(image.tobytes())
    except Exception:
        process.kill()
        raise
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("ffmpeg failed to encode the video")
    print(OUTPUT)


if __name__ == "__main__":
    render()