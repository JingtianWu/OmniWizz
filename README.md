# OmniWizz — Multimodal Inspirational Tool

OmniWizz is a multimodal framework that accepts **text**, **images** and **audio** and can return any combination of these modalities.

## Mood Board Outputs
- **Music** — generative soundtrack built from your image’s theme
- **Inspirational Tags** — descriptive keywords extracted from the image
- **Inspirational Images** — complementary visuals generated from the tags

## Feature Pipeline
- **Image → Text** using OpenAI `GPT-4.1` for tags and descriptions
- **Text → Music** via Ace Step (PiAPI) using GPT-4.1 prompts & lyrics
- **Optional audio upload** analysed by MusicAI for key & chord progression
- **Text → Images** through Google Gemini (Nano Banana) for inspirational images
- POST `/generate` triggers selected pipelines via `modes` and `language`
- `/regenerate` re-runs music synthesis with custom prompt and lyrics
- Session and event logging stored in SQLite (`DATABASE_URL` configurable)
- Toggle `TEST_MODE` for offline demos (bundled mock data, no external API calls)

---

## Repository Structure

```text
OmniWizz/
├── backend/
│   ├── ace_step_module.py      ← music generation via PiAPI
│   ├── llm_processors.py       ← OpenAI GPT‑4.1 image processors
│   ├── musicai_module.py       ← optional chord transcription via MusicAI
│   ├── nano_banana_module.py   ← inspirational images through Gemini
│   ├── pipeline.py             ← orchestrates image→{music,tags,images}
│   ├── server.py               ← FastAPI API (`/generate`, `/regenerate`, `/output`)
│   ├── log_db.py               ← SQLModel session/event logging
│   ├── dev_tools.py            ← download log database
│   ├── requirements.txt        ← minimal backend dependencies
│   └── tests/                  ← unit tests
├── DiffRhythm/                 ← upstream music model (Apache 2.0)
├── frontend/
│   ├── public/
│   └── src/
├── docs/                       ← optional GitHub Pages build
├── requirements.txt            ← full stack deps (incl. DiffRhythm)
└── README.md
```

## Setup

### Backend

```bash
python3 -m venv omniwizz-env
source omniwizz-env/bin/activate
pip install -r backend/requirements.txt  # use requirements.txt for full DiffRhythm stack
```

Set environment variables before running:

- `OPENAI_API_KEY` – GPT‑4.1
- `PIAPI_KEY` – Ace Step via PiAPI
- `NANO_BANANA_API_KEY` – Google Gemini image generation
- `MUSIC_AI_API_KEY` – Music AI chord transcription
- `MUSICAI_CHORD_WORKFLOW` – optional workflow id for Music AI
- `DATABASE_URL` – optional SQLModel DB URL (defaults to `sqlite:///./omni_logs.db`)
- `LOG_DOWNLOAD_KEY` – API key for `/dev/download-logs`
- `TEST_MODE` – set `true` to use mock data; `false` to call real APIs

`.env` files are loaded via `python-dotenv`.

```bash
cd backend
uvicorn server:app --reload
```

The API listens on **http://localhost:8000** and writes run outputs to `output/<run_id>/`.

### Frontend

```bash
cd frontend
npm install
npm start
```

Open **http://localhost:3000** and drag an image (optionally with audio) to generate results.

## Deploying to GitHub Pages

```bash
cd frontend
npm run build
cd ..
rm -rf docs
cp -r frontend/build docs
git add .
git commit -m "Update textbox feature"
git push
```

After pushing, enable **Pages** → **Deploy from a branch** using `main` and `/docs`, then visit `https://<username>.github.io/<repository-name>/`.

## Testing

```bash
pytest
```

## Contributing & License

- Core orchestration code: **MIT License**
- **DiffRhythm**: Apache 2.0 – see `DiffRhythm/LICENSE.md`
- Contributions welcome: add new modality modules in `backend/pipeline.py` and UI components

