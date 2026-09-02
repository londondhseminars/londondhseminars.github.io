"""Build the GitHub Pages artefact from JSON content and site sources."""

from datetime import date, datetime
from html import escape
import json
from pathlib import Path
import re
import shutil
import sys

import markdown


ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "site"
BRANDING_DIR = ROOT / "branding"
OUTPUT_DIR = ROOT / "_site"


def load_json(filename: str):
    with (SITE_DIR / filename).open(encoding="utf-8") as source:
        return json.load(source)


def validate_event(event: dict, index: int) -> date:
    label = f"events.json entry {index + 1}"
    event_date_value = event.get("date")
    event_time_value = event.get("time")
    if not isinstance(event_date_value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", event_date_value):
        raise ValueError(f"{label} has an invalid date; use YYYY-MM-DD")
    if not isinstance(event_time_value, str) or not re.fullmatch(r"\d{2}:\d{2}", event_time_value):
        raise ValueError(f"{label} has an invalid time; use 24-hour HH:MM")
    try:
        event_date = datetime.strptime(event_date_value, "%Y-%m-%d").date()
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{label} has an invalid date; use YYYY-MM-DD") from error
    try:
        datetime.strptime(event_time_value, "%H:%M")
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{label} has an invalid time; use 24-hour HH:MM") from error
    return event_date


def render_markdown(text: str) -> str:
    return markdown.markdown(text, output_format="html5")


def render_speakers(speakers: list[dict]) -> str:
    items = []
    for speaker in speakers:
        name = " ".join(filter(None, [speaker.get("first_name"), speaker.get("surname")]))
        details = " · ".join(filter(None, [speaker.get("role"), speaker.get("affiliation")]))
        if name or details:
            items.append(f"<li><strong>{escape(name)}</strong>{f'<span>{escape(details)}</span>' if details else ''}</li>")
    return f"<ul class=\"speaker-list\">{''.join(items)}</ul>" if items else ""


def render_events(events: list[dict], empty_message: str) -> str:
    if not events:
        return f'<p class="empty-state">{empty_message}</p>'
    cards = []
    for event in events:
        title = escape(str(event.get("title", "Untitled event")))
        display_date = datetime.strptime(event["date"], "%Y-%m-%d").strftime("%b %Y")
        details = []
        if event.get("time"):
            details.append(escape(event["time"]))
        if event.get("location"):
            details.append(escape(event["location"]))
        detail_line = f'<p class="event-meta">{" · ".join(details)}</p>' if details else ""
        registration = (
            f'<a class="button-link" href="{escape(event["registration_link"], quote=True)}">Register <span aria-hidden="true">&rarr;</span></a>'
            if event.get("registration_link") else ""
        )
        cards.append(
            f'<article class="event-card"><time datetime="{escape(event["date"])}"><span>{event["date"][8:10]}</span>{escape(display_date)}</time>'
            f'<div class="event-body"><h3>{title}</h3>{detail_line}'
            f'<p>{escape(str(event.get("description", "")))}</p>{render_speakers(event.get("speakers", []))}{registration}</div></article>'
        )
    return "".join(cards)


def initials(person: dict) -> str:
    return "".join(part[0] for part in [person.get("first_name", ""), person.get("surname", "")] if part).upper()


def render_people(people: list[dict]) -> str:
    if not people:
        return '<p class="empty-state">People and contact details will appear here soon.</p>'
    cards = []
    for index, person in enumerate(people):
        name = " ".join(filter(None, [person.get("first_name"), person.get("surname")]))
        image = ""
        if person.get("image_filename"):
            image_path = SITE_DIR / "assets" / "img" / person["image_filename"]
            if image_path.is_file():
                image = f'<img src="assets/img/{escape(person["image_filename"], quote=True)}" alt="Portrait of {escape(name, quote=True)}">'
        portrait = image or f'<span class="initials" aria-hidden="true">{escape(initials(person))}</span>'
        links = []
        if person.get("website"):
            links.append(f'<a href="{escape(person["website"], quote=True)}">Website</a>')
        if person.get("email"):
            links.append(f'<a href="mailto:{escape(person["email"], quote=True)}">Email</a>')
        cards.append(
            f'<article class="person-card accent-{index % 5}"><div class="person-image">{portrait}</div><div><h3>{escape(name)}</h3>'
            f'<p class="person-role">{escape(str(person.get("role", "")))}</p><p>{escape(str(person.get("affiliation", "")))}</p>'
            f'<p>{escape(str(person.get("bio", "")))}</p><p class="person-links">{" · ".join(links)}</p></div></article>'
        )
    return "".join(cards)


def copy_assets() -> None:
    assets_dir = OUTPUT_DIR / "assets"
    (assets_dir / "branding").mkdir(parents=True)
    (assets_dir / "img").mkdir(parents=True)
    (assets_dir / "fonts").mkdir(parents=True)
    for filename in ("LDHS_logo_mark_transparent.svg", "LDHS_logo_mark_dark_transparent.svg", "LDHS_logo_mark.png", "LDHS_logo_mark_dark_square.png", "LDHS_logo_mark_square.png"):
        shutil.copy2(BRANDING_DIR / filename, assets_dir / "branding" / filename)
    source_images = SITE_DIR / "assets" / "img"
    if source_images.is_dir():
        for image in source_images.iterdir():
            if image.is_file():
                shutil.copy2(image, assets_dir / "img" / image.name)
    shutil.copy2(SITE_DIR / "site.css", assets_dir / "site.css")
    shutil.copy2(SITE_DIR / "assets" / "underground-divider.svg", assets_dir / "underground-divider.svg")
    shutil.copy2(SITE_DIR / "assets" / "nav-network.svg", assets_dir / "nav-network.svg")
    for font in (SITE_DIR / "assets" / "fonts").glob("*.ttf"):
        shutil.copy2(font, assets_dir / "fonts" / font.name)


def build() -> None:
    events = load_json("events.json")
    people = load_json("people.json")
    about = load_json("about.json")
    today = date.today()
    dated_events = [(validate_event(event, index), event) for index, event in enumerate(events)]
    upcoming = [event for event_date, event in dated_events if event_date >= today]
    past = [event for event_date, event in dated_events if event_date < today]
    upcoming.sort(key=lambda event: (event["date"], event.get("time", "")))
    past.sort(key=lambda event: (event["date"], event.get("time", "")), reverse=True)
    about_html = "".join(render_markdown(paragraph) for paragraph in about.get("paragraphs", []) if paragraph)
    template = (SITE_DIR / "template.html").read_text(encoding="utf-8")
    replacements = {
        "{{ about_html }}": about_html,
        "{{ upcoming_count }}": str(len(upcoming)),
        "{{ past_count }}": str(len(past)),
        "{{ upcoming_html }}": render_events(upcoming, "No upcoming seminars are scheduled yet."),
        "{{ past_html }}": render_events(past, "Past seminars will be listed here."),
        "{{ people_html }}": render_people(people),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    if "{{" in template or "}}" in template:
        raise ValueError("Template contains an unresolved placeholder")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir()
    (OUTPUT_DIR / "index.html").write_text(template, encoding="utf-8")
    copy_assets()
    print(f"Built {OUTPUT_DIR / 'index.html'} ({len(upcoming)} upcoming, {len(past)} past)")


if __name__ == "__main__":
    try:
        build()
    except (json.JSONDecodeError, OSError, ValueError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        raise SystemExit(1)