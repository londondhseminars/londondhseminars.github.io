# Branding asset generation

Create the square logo mark variants and PNG exports with:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r branding/requirements.txt
python branding/render_assets.py
```

The script exports a PNG beside every SVG in this directory. The square mark variants use a centered, padded version of the standalone mark for circular avatar cropping. Branding headings and lockups use Space Grotesk, matching the website; the website build vendors the font under `site/assets/fonts/`.