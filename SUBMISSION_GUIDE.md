# RailSync SIH26027 Submission Guide

Use this checklist before the repository and prototype are submitted to evaluators.

## Repository and Documentation

- [x] Working source code is present in the real `frontend/`, `backend/`, `optimizer/`, `data/`, `ml/`, `models/`, and `tests/` structure.
- [x] Evaluator-facing `README.md` is complete.
- [x] PS ID **SIH26027** is visible.
- [x] The exact problem statement title is visible.
- [x] Category **Software** and theme **Transportation & Logistics** are visible.
- [x] The problem and proposed solution are explained.
- [x] Implemented features are grouped and documented.
- [x] Actual architecture is documented in [docs/architecture.md](docs/architecture.md).
- [ ] Replace the team-member/role placeholder in `README.md` with confirmed information.
- [ ] Repository owner must select and add an appropriate license.

## Evidence and Submission Assets

- [x] Working screenshots are included in [assets/screenshots/](assets/screenshots/README.md).
- [x] The final PDF presentation is accessible through [submission/PRESENTATION.md](submission/PRESENTATION.md).
- [x] The live application URL is documented.
- [x] Demo/video status is stated accurately in [submission/DEMO.md](submission/DEMO.md).
- [ ] Replace the broken 2-byte `INTRO_VIDEO.mp4` if a standalone video is required by the submission portal.

## Setup and Verification

- [ ] Re-run `python -m data.validate_data` immediately before submission.
- [ ] Re-run `python -m pytest -q -p no:cacheprovider` immediately before submission.
- [ ] In `frontend/`, re-run `npm test -- --run`, `npm run lint`, and `npm run build`.
- [ ] Follow the README setup instructions on a clean machine or clean environment.
- [ ] Confirm no secrets, credentials, personal `.env` files, service-account files, archives, or generated build directories are committed.

## Public Access and Deployment

- [ ] Confirm the GitHub repository is public and readable while logged out/incognito.
- [ ] Test every repository link while logged out/incognito.
- [ ] Confirm [the Vercel frontend](https://rail-sync-eosin.vercel.app) loads and its primary workflow works.
- [ ] Confirm the Render backend/API is reachable through the production frontend path.
- [ ] Confirm the Vercel project-level CDN routing rule remains active.
- [ ] Do not change the relative `VITE_API_BASE_URL=/api` convention or repository deployment configuration during submission checks.
