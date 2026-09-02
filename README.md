# London Digital Humanities Seminars

This repository contains the source content and generator for the London Digital Humanities Seminars GitHub Pages site. `index.html` is a generated artefact in `_site/`; edit the JSON and source files instead.

## Local build

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r branding/requirements.txt -r site/requirements.txt
python branding/render_assets.py
python site/generate.py
```

The generated site is in `_site/`. Open `_site/index.html` locally or serve it with a static HTTP server. Space Grotesk is vendored in `site/assets/fonts/` and copied into the published artefact so branding typography works offline.

## Content schemas

### `site/about.json`

An object with a `paragraphs` array. Each item is a Markdown string. Standard Markdown links are rendered as HTML links.

```json
{
  "paragraphs": ["A paragraph with a [link](https://example.org)."]
}
```

### `site/events.json`

An array of event objects. `title`, `date`, `time`, `description`, `speakers`, `location`, and `registration_link` are optional display fields. Dates must use ISO 8601 `YYYY-MM-DD`; times must use 24-hour `HH:MM`.

Each `speakers` item may contain `first_name`, `surname`, `role`, and `affiliation`. Events dated today are Upcoming. Other Upcoming events are chronological; Past events are reverse-chronological.

```json
[
  {
    "title": "Computer Vision in the Digital Humanities",
    "date": "2026-10-15",
    "time": "18:00",
    "description": "A seminar description.",
    "speakers": [{"first_name": "Jane", "surname": "Example", "role": "Associate Professor", "affiliation": "University College London"}],
    "location": "Room 101, Example Building",
    "registration_link": "https://example.org/register"
  }
]
```

### `site/people.json`

An array of people. `surname`, `first_name`, `affiliation`, `role`, `bio`, `image_filename`, `website`, and `email` are optional. `image_filename` must contain only a filename; matching images belong in `site/assets/img/`.

```json
[
  {
    "surname": "Example",
    "first_name": "Jane",
    "affiliation": "University College London",
    "role": "Co-organiser",
    "bio": "A short biography.",
    "image_filename": "jane-example.jpg",
    "website": "https://example.org",
    "email": "jane.example@example.org"
  }
]
```

The GitHub Actions workflow rebuilds on content and source changes, weekly to keep date-sensitive event tabs current, and on demand through `workflow_dispatch`.