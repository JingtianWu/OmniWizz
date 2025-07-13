import os
import time
import json
import requests
from pathlib import Path
from config import TEST_MODE, MUSIC_AI_API_KEY

API_BASE = 'https://api.music.ai/v1'
HEADERS = {'Authorization': MUSIC_AI_API_KEY}

def _get_signed_urls():
    r = requests.get(f'{API_BASE}/upload', headers=HEADERS)
    r.raise_for_status()
    j = r.json()
    return j['uploadUrl'], j['downloadUrl']


def _upload_file(path, url):
    with open(path, 'rb') as f:
        r = requests.put(url, data=f)
    r.raise_for_status()


def _create_job(dl_url, workflow):
    payload = {
        'workflow': workflow,
        'params': {'inputUrl': dl_url},
        'name': 'musicai_job'
    }
    h = {**HEADERS, 'Content-Type': 'application/json'}
    r = requests.post(f'{API_BASE}/job', json=payload, headers=h)
    r.raise_for_status()
    return r.json()['id']


def _poll_job(job_id):
    while True:
        r = requests.get(f'{API_BASE}/job/{job_id}', headers=HEADERS)
        r.raise_for_status()
        j = r.json()
        status = j['status']
        if status in ('SUCCEEDED', 'FAILED'):
            return j
        time.sleep(5)


def _fetch_chord_json(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def parse_progressions(data):
    bars = {}
    for seg in data:
        bar = seg.get('start_bar')
        beat = seg.get('start_beat')
        simple = seg.get('chord_simple_pop')
        if bar is None or beat is None or not simple:
            continue
        if bar not in bars or beat < bars[bar][0]:
            bars[bar] = (beat, simple)
    return [bars[b][1] for b in sorted(bars)]


def clean_chord_label(chord):
    return 'No chord' if chord == 'N' else chord


def transcribe_chords(audio_path: str, workflow: str = 'chord-transcriber'):
    """Return list of chords from the given audio file."""
    if TEST_MODE:
        mock_fp = Path(__file__).parent / 'mock_data' / 'mock_chords.json'
        if mock_fp.exists():
            with open(mock_fp) as f:
                return json.load(f)
        return ['C', 'G', 'Am', 'F']

    if not MUSIC_AI_API_KEY:
        raise RuntimeError('MUSIC_AI_API_KEY not set')

    up_url, dl_url = _get_signed_urls()
    _upload_file(audio_path, up_url)
    job_id = _create_job(dl_url, workflow)

    job = _poll_job(job_id)
    if job['status'] != 'SUCCEEDED':
        raise RuntimeError(f"MusicAI job failed: {job.get('error', {}).get('message', '')}")

    chord_url = job['result'].get('chords')
    if not chord_url:
        return []

    data = _fetch_chord_json(chord_url)
    return [clean_chord_label(ch) for ch in parse_progressions(data)]
