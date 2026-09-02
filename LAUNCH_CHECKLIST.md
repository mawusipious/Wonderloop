# WonderLoop Worldwide Launch Checklist

## Required before public launch
- [ ] Register a domain.
- [ ] Deploy the backend to a server with persistent storage.
- [ ] Put the backend behind HTTPS and a reverse proxy.
- [ ] Set `WONDERLOOP_ALLOWED_ORIGINS` to the exact web origin.
- [ ] Add a real database for users/projects instead of local JSON.
- [ ] Add authentication and authorization before multi-user deployment.
- [ ] Add object storage/CDN for generated MP4 files.
- [ ] Move video generation into a worker queue; do not rely on FastAPI background tasks for large-scale jobs.
- [ ] Add rate limiting, abuse monitoring, logging and backups.
- [ ] Add stronger child-safety moderation and human review procedures.
- [ ] Publish Privacy Policy, Terms, and contact/support details.
- [ ] Test data deletion/export and retention rules.
- [ ] Build and sign the Android release (AAB/APK) with Flutter on a release machine.
- [ ] Run `flutter build web` and deploy the resulting `build/web` directory.
- [ ] Test Chrome, Android, small screens, slow networks and failed jobs.

## Current media-engine limitation
The bundled engine is local/lightweight: illustrated scenes, eSpeak narration and an FFmpeg music bed. It is not a cloud generative-video model. For a Fliki-like product, connect an appropriate licensed/open model service behind a provider interface and budget for GPU/storage/egress.
