# OmniWizz — Multimodal Media Transformation Pipeline

**OmniWizz** is a comprehensive multimodal framework—accepting **text**, **images**, and **audio** inputs and producing any combination of these outputs.

> **Ultimate Goal:** Let users supply any combination of text, image, or audio as input, and receive any combination of these modalities as output, according to their creative or analytic needs.

> **Current Stage:** Initial **image → music** prototype complete.


## Features
- **Image → Music** via DiffRhythm API and GPT‑4.1‑nano with timestamped lyrics
- **Image → Tags** for creativity prompts
- **Image → Related Images** via SerpAPI (`SERPAPI_API_KEY` required)
- REST endpoint `/generate` wraps all pipelines
- Toggle `TEST_MODE` in `backend/config.py` for offline demos. When enabled, the
  backend uses bundled mock data and avoids contacting the GPT‑4.1‑nano and
  DiffRhythm APIs, suitable for memory‑constrained deployments.

---

## Repository Structure

```
omniwizz/
├── backend/                 
│   ├── llm_module.py        ← LLM wrapper for multimodal understanding
│   ├── diffrhythm_module.py ← post-process lyrics & invoke singing synthesis
│   ├── pipeline.py          ← core logic: routes inputs through modules
│   └── server.py            ← REST API endpoint (`POST /generate`)
│
├── DiffRhythm/              
│
├── frontend/                
│   ├── public/
│   └── src/
│       ├── App.jsx          ← main interface (inputs → outputs, includes VinylIcon)
│       ├── components/      ← EditorCanvas, etc.
│       └── index.css        ← minimal styling
│
├── requirements.txt         
└── README.md                
```

   source omniwizz-env/bin/activate

   # Install deps
   pip install -r requirements.txt
   ```

   Set the `OPENAI_API_KEY` and `DIFFRHYTHM_API_KEY` environment variables
   before running the backend in production mode. You can export them in your
   shell or place them in a `.env` file that your process reads.

3. **Run the API**

   ```bash
   cd backend
   uvicorn server:app --reload
   ```

   The API listens on **[http://localhost:8000](http://localhost:8000)**.

4. **Frontend**

   ```bash
   cd frontend
   npm install
   npm start
   ```


   Open **[http://localhost:3000](http://localhost:3000)**, then drag & drop an image to generate music.

## Deploying to GitHub Pages

1. Build the production bundle:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
2. Copy the contents of `frontend/build/` into a new folder named `docs/` at the repository root. Commit this folder to `main`.
3. On GitHub, open the repository settings → **Pages** and choose **Deploy from a branch** with the `main` branch and `/docs` folder.
4. Visit `https://<username>.github.io/<repository-name>/` to access OmniWizz.


For offline demos or memory-constrained deployments, enable `TEST_MODE` in
`backend/config.py`. This skips calling the remote GPT and DiffRhythm services
and uses bundled mock data so the API and frontend can run without external
dependencies.

---

## Contributing & License

- Core orchestration code: **MIT License**.  
- **DiffRhythm** (full music generation model): included under Apache 2.0 — see `DiffRhythm/LICENSE.md`.  
  - Upstream repository: https://github.com/ASLP-lab/DiffRhythm  
- Contributions welcome: add new modality modules in `backend/pipeline.py` and UI components.

---
