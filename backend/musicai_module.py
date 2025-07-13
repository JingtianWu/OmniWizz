import os
import time
import requests
from pathlib import Path
from config import TEST_MODE, MUSIC_AI_API_KEY, MUSICAI_CHORD_WORKFLOW

API_BASE = 'https://api.music.ai/v1'

HEADERS = {'Authorization': MUSIC_AI_API_KEY}


def _get_signed_urls():
    r = requests.get(f'{API_BASE}/upload', headers=HEADERS)
    r.raise_for_status()
    j = r.json()
    return j['uploadUrl'], j['downloadUrl']


def _upload_file(path: str, url: str):
    with open(path, 'rb') as f:
        r = requests.put(url, data=f)
    r.raise_for_status()


def _create_job(download_url: str, workflow: str, name: str):
    payload = {
        'workflow': workflow,
        'params': {'inputUrl': download_url},
        'name': name,
    }
    h = {**HEADERS, 'Content-Type': 'application/json'}
    r = requests.post(f'{API_BASE}/job', json=payload, headers=h)
    r.raise_for_status()
    return r.json()['id']


def _get_job(job_id: str):
    r = requests.get(f'{API_BASE}/job/{job_id}', headers=HEADERS)
    r.raise_for_status()
    return r.json()


def _parse_progressions(data):
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


def _clean_chord_label(chord: str) -> str:
    return "No chord" if chord == "N" else chord


def transcribe_chords(audio_path: str):
    """Return dict with 'key' and 'chords' list from Music AI transcription."""
    if TEST_MODE:
        return {'key': 'C major', 'chords': ['C', 'G', 'Am', 'F']}

    if not MUSIC_AI_API_KEY:
        raise RuntimeError('MUSIC_AI_API_KEY not set')

    up_url, dl_url = _get_signed_urls()
    _upload_file(audio_path, up_url)
    job_id = _create_job(dl_url, MUSICAI_CHORD_WORKFLOW, 'omniwizz_chords')

    while True:
        job = _get_job(job_id)
        status = job.get('status')
        if status == 'SUCCEEDED':
            break
        if status == 'FAILED':
            raise RuntimeError('MusicAI job failed: ' + job.get('error', {}).get('message', ''))
        time.sleep(5)

    chord_url = job.get('result', {}).get('chords')
    if not chord_url:
        return {'key': '', 'chords': []}

    r = requests.get(chord_url)
    r.raise_for_status()
    data = r.json()
    progression = _parse_progressions(data)
    key = ''
    for seg in data:
        key = seg.get('key_simple') or seg.get('key', {}).get('simple') or key
    chords = [_clean_chord_label(ch) for ch in progression]
    return {'key': key, 'chords': chords}
