# Multisense — Multimodal Media Transformation Pipeline

**Multisense** is a comprehensive multimodal framework—accepting **text**, **images**, and **audio** inputs and producing any combination of these outputs.

> **Ultimate Goal:** Let users supply any combination of text, image, or audio as input, and receive any combination of these modalities as output, according to their creative or analytic needs.

> **Current Stage:** Initial **image → music** prototype complete.

---

## Repository Structure

```
multisense/
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

---

## Quickstart (Image → Music Prototype)

1. **Clone the repo**

   ```bash
   git clone https://github.com/JingtianWu/Multisense.git
   cd Multisense
   ```

2. **Backend setup**

   ```bash
   # Python environment
   python3 -m venv multisense-env
   source multisense-env/bin/activate

   # Install deps
   pip install -r requirements.txt
   ```

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

---

## Contributing & License

- Core orchestration code: **MIT License**.  
- **DiffRhythm** (full music generation model): included under Apache 2.0 — see `DiffRhythm/LICENSE.md`.  
  - Upstream repository: https://github.com/ASLP-lab/DiffRhythm  
- Contributions welcome: add new modality modules in `backend/pipeline.py` and UI components.

---
