---
name: relink-archive
description: Automatically updates media paths in FilmCraft (.fcproj), project_manifest.json, and DaVinci Resolve Studio when a YEAR or YYYY-MM-DD project folder is moved between local ~/Movies/YEAR/ and external /Volumes/Crucial-4T/Movies/YEAR/.
---

# Relink Archived Media Between `~/Movies` and `/Volumes/Crucial-4T/Movies` (`/relink-archive`)

## Execution Instructions
Whenever an older `~/Movies/YEAR/YYYY-MM-DD_<name>` folder is moved to `/Volumes/Crucial-4T/Movies/YEAR/YYYY-MM-DD_<name>` to free local SSD space (or moved back to local disk for editing), run:

```bash
python3 ~/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/.agents/skills/relink-archive/scripts/relink_project_media.py \
  --project-catalog-dir "~/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/04_Project_Catalog/YEAR/YYYY-MM-DD_<name>" \
  --media-subfolder "YEAR/YYYY-MM-DD_<name>" \
  --direction to-external
```

*(Pass `--direction to-local` if moving a folder back from Crucial-4T to `~/Movies/YEAR/`).*
