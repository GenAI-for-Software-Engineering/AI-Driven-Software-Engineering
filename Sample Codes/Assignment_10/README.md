# GenAI Software Engineering Pipeline — Chrome Extension
## 1. Backend setup

```bash
cd server            # wherever you place server.py
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the same folder as `server.py`:

```
GROQ_API_KEY=your_groq_api_key_here
```

Run it:

```bash
uvicorn server:app --reload --port 8000
```

Leave this running. Visit `http://127.0.0.1:8000/health` — you
should see `{"status":"ok"}`.

## 2. Load the extension in Chrome

1. Go to `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the folder containing `manifest.json`,
   `background.js`, `sidepanel.html`, `sidepanel.js`, `style.css`
5. Click the extension's action icon in the toolbar — the side
   panel opens

## 3. Using it

- **Text spec:** paste the specification into the textarea, click
  **Generate Requirements**.
- **Audio spec:** choose a `.wav` file (must be an actual PCM WAV
  file, not mp3/webm renamed to `.wav`), leave the textarea empty,
  click **Generate Requirements**. It transcribes via Google's free
  speech API (needs internet) and then extracts requirements from
  the transcript.
- Then click through **Generate User Stories → Verify INVEST →
  Generate Prototype → Preview Prototype → Generate Test Cases** in
  order — each stage depends on the previous one's output.
- **Preview Prototype** opens the generated mini-app in a new tab
  using mock JSON data (no backend/database involved, per the
  assignment's constraints).
- **Download Artifact** saves whatever is currently shown in the
  output box as `artifact.txt`. Run it after each stage if you want
  to keep a copy of that stage's output, since each stage overwrites
  the previous one on screen.
