# Expanded fictional sample activity

Run from the repository root:

```powershell
backend/.venv/Scripts/python.exe backend/seed_expanded.py
```

This adds 12 fictional profiles (six students, three faculty, three industry mentors),
three projects, 15 posts including three weekly logs, and 24 comments. CircuitBench
is completed and appears in the showcase; SolarScope and Greenhouse Watch are active.
Profiles and posts explicitly identify the fictional sample context. Existing real
accounts and their contributions are never overwritten. Rerunning inserts only
missing sample records, in one transaction.

Media is embedded in the sample posts so it is available immediately without a
separate asset deployment. Each project has a relevant reference photograph, an
original dashboard still, and an eight-second prototype video using simulated data.
Photo attribution and source/license links are in
`frontend/public/demo-posts/photo-credits.json` and the photo-post captions.

To regenerate the three dashboard videos and stills, install the development-only
`Pillow` and `imageio-ffmpeg` packages, then run:

```powershell
backend/.venv/Scripts/python.exe backend/build_expanded_sample_media.py
```

The earlier sample-media updater remains available as:

```powershell
backend/.venv/Scripts/python.exe backend/seed_home.py --refresh-media
```

It only replaces the known unrelated stock media on exact original sample posts.
