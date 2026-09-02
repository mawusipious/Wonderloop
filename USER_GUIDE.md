# WonderLoop v1.2 User Guide

## What WonderLoop is
WonderLoop is a free/local-first children's video creator for Android and Web. Enter one idea and it plans scenes, creates illustrated visuals, adds local narration and music, burns captions, and assembles an MP4.

## Quick start
### 1. Install prerequisites
- Python 3.10+ recommended
- Flutter 3.x
- FFmpeg available on PATH
- eSpeak available on PATH

### 2. Start the backend
```bash
cd backend
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Start the app
```bash
flutter pub get
flutter run -d chrome
```

For Android, change `baseUrl` in `lib/main.dart` from `http://127.0.0.1:8000` to the computer's local IP address. Keep the phone and computer on the same network.

## Create a video
1. Enter a simple idea, e.g. **Make a fun song teaching children to eat fruits.**
2. Choose duration: 1, 3, or 5 minutes.
3. Choose 2D Cartoon, 3D Cartoon, or Storybook.
4. Choose YouTube, Shorts, or Square format.
5. Choose a language.
6. Optionally select a saved Character and Story Bible.
7. Press **CREATE VIDEO**.
8. Wait for generation to reach 100%.
9. Open **EDIT VIDEO** if you want to change scenes.

## Characters and Story Bible
Use **Characters** to create reusable characters with a name, species, personality and appearance.

Use **Story Bible** to describe a series world and its rules. Selecting the same character and story bible in later videos helps the planner keep the series consistent.

## Editing
Open a completed project and choose **EDIT VIDEO**. Select a scene, edit its narration/caption text, save it, then choose **REBUILD VIDEO**. The complete MP4 is regenerated using the edited scene plan.

## Projects
The project list supports:
- Open
- Rename
- Delete

Project metadata is stored locally under `backend/data/` and generated media under `backend/output/`.

## Health check
The **Health** button reports whether the API is reachable and whether FFmpeg and eSpeak are available.

## Kids-safe mode
WonderLoop checks prompts before generation and blocks a small set of clearly inappropriate categories. This is a lightweight local guard, not a replacement for professional production moderation.

## Important limitation
v1.2 is the public-ready **prototype milestone**, not a hosted Fliki-scale service. Visuals are illustrated scene cards; narration uses local eSpeak; music uses a lightweight FFmpeg-generated bed. Cloud accounts, cloud storage, high-end generative video models, premium voices, scalable workers and production-grade moderation would be the next commercial infrastructure layer.

## Production configuration
Set allowed web origins instead of using `*` when deploying:
```bash
WONDERLOOP_ALLOWED_ORIGINS=https://your-domain.example
```
