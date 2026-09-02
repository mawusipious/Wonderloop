# WonderLoop v1.2.1 — Launch Candidate

WonderLoop v1.2 is the launch candidate / deployment-ready prototype of the free/local-first children's video creator prototype for Android and Web.

## Finalized features
- One-prompt video workflow
- Character Library and Story Bible
- Local illustrated scene generation
- Local narration with eSpeak
- Local music bed with FFmpeg
- Captions and MP4 assembly
- Scene editor and rebuild
- Persistent local creator profile and projects
- YouTube 16:9, Shorts 9:16 and Square 1:1
- Eight language selections
- Kids-safe prompt guard
- Backend health diagnostics
- Configurable CORS origins via `WONDERLOOP_ALLOWED_ORIGINS`
- Project cleanup on delete

## Important
This is a production-structured prototype, not a hosted commercial AI service. Current media generation is local/lightweight: illustrated scene cards, eSpeak narration and an FFmpeg music bed. Real cloud generative video, premium voices, authentication, cloud storage and scalable workers require additional infrastructure.

## Run backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Optional production CORS setting:
```bash
WONDERLOOP_ALLOWED_ORIGINS=https://your-site.example
```

## Run Flutter
```bash
flutter pub get
flutter run -d chrome
```

For Android, change `baseUrl` in `lib/main.dart` from `http://127.0.0.1:8000` to the computer's LAN IP and keep both devices on the same network.

## v1.2 acceptance test
1. Start backend.
2. Open app.
3. Confirm Health reports API, FFmpeg and eSpeak.
4. Enter a child-friendly prompt and generate.
5. Wait for 100%.
6. Open editor, edit a scene, save and rebuild.
7. Confirm project history updates.
8. Rename and delete a project.


## Production deployment

This repository includes `Dockerfile`, `docker-compose.yml`, `.env.example`, and `nginx/wonderloop.conf.example`. See `docs/LAUNCH_CHECKLIST.md` before exposing the service to the public internet. Authentication, a real database, object storage, scalable workers and a production AI media provider are still required for a true multi-user worldwide service.
