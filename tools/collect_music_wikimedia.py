"""Collect CC-licensed instrumental music from Wikimedia (via Openverse) and cut it into ~90 s beds.
Each bed is logged in audio_lib/CREDITS.json with its license and source (credit CC-BY tracks in the video description)."""
import json, os, subprocess, urllib.request, urllib.error, urllib.parse, time
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audio_lib'); CRED = os.path.join(ROOT, 'CREDITS.json'); os.makedirs(ROOT + '/music', exist_ok=True)
credits = json.load(open(CRED)) if os.path.exists(CRED) else {}
UA = {'User-Agent': 'geo-style-pipeline/1.0'}
QUERIES = ['ambient background music', 'calm instrumental', 'orchestral suite', 'galactic ambient', 'dark ambient', 'piano instrumental', 'cinematic score', 'documentary music']
BAD = ['episode', 'podcast', 'inleiding', 'interview', 'radio', 'lecture', 'spoken', 'voz de']
want = 12; have = {v['source'] for v in credits.values() if v['category'] == 'music'}
for q in QUERIES:
    if len(have) >= want: break
    u = f'https://api.openverse.org/v1/audio/?q={urllib.parse.quote(q)}&license_type=commercial&page_size=20&source=wikimedia_audio&length=long'
    time.sleep(1.2)
    try: res = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))['results']
    except Exception as e: print('api', e); continue
    for r in res:
        if len(have) >= want: break
        t = r['title'].lower(); d = (r.get('duration') or 0) / 1000
        if any(b in t for b in BAD) or r['foreign_landing_url'] in have or d < 120 or d > 5000: continue
        raw = os.path.join(ROOT, 'music', 'tmp.src')
        data = None
        for wait in (8, 30, 90):  # Wikimedia rate-limits fast downloads (HTTP 429): pause, then back off
            time.sleep(wait)
            try: data = urllib.request.urlopen(urllib.request.Request(r['url'], headers=UA), timeout=180).read(); break
            except urllib.error.HTTPError as e:
                if e.code != 429: print('dl fail', r['title'][:40], e.code); break
            except Exception as e: print('dl fail', r['title'][:40], e); break
        if data is None: print('dl fail', r['title'][:40]); continue
        open(raw, 'wb').write(data)
        # cut up to 3 beds of 95 s from different parts, each with fades; skip quiet parts
        n = 0
        for start in [d * 0.12, d * 0.45, d * 0.75]:
            if n >= 2: break
            name = f"music_{r['id'][:8]}_{n}.mp3"; out = os.path.join(ROOT, 'music', name)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(start), '-t', '95', '-i', raw, '-af', 'afade=t=in:d=1.5,afade=t=out:st=92:d=3,loudnorm=I=-20:TP=-2', '-ar', '44100', '-ac', '2', '-b:a', '192k', out])
            vol = subprocess.run(['ffmpeg', '-i', out, '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True).stderr
            mean = float(vol.split('mean_volume:')[1].split('dB')[0]) if 'mean_volume' in vol else -99
            if mean < -35: os.remove(out); continue
            credits[name] = dict(title=r['title'], creator=r.get('creator'), license=r['license'] + ' ' + (r.get('license_version') or ''), source=r['foreign_landing_url'], seconds=95, category='music', used_in=None); n += 1
        os.remove(raw); have.add(r['foreign_landing_url']); print('music', r['title'][:60], r['license'])
json.dump(credits, open(CRED, 'w'), indent=1); print(sum(1 for v in credits.values() if v['category'] == 'music'), 'music beds')
