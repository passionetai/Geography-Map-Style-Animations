"""Collect CC0 / CC-BY instrumental music beds from Jamendo and Freesound (via Openverse) into audio_lib/music.
Use this when Wikimedia rate-limits (HTTP 429) collect_music_wikimedia.py.
Only CC0 and CC-BY are taken: BY-SA would force the whole video under BY-SA, and BY-ND forbids syncing it to video.
Each track gives up to 2 beds of 95 s with fades; quiet beds are dropped. Credits are saved after every bed.
Credit CC-BY tracks in the video description."""
import json, os, subprocess, urllib.request, urllib.parse, time, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audio_lib'); CRED = os.path.join(ROOT, 'CREDITS.json')
os.makedirs(ROOT + '/music', exist_ok=True)
credits = json.load(open(CRED)) if os.path.exists(CRED) else {}
UA = {'User-Agent': 'geo-style-pipeline/1.0'}
QUERIES = [('jamendo', 'documentary'), ('jamendo', 'filmscore'), ('jamendo', 'cinematic'), ('freesound', 'cinematic documentary'),
           ('jamendo', 'orchestral'), ('freesound', 'ambient piano'), ('jamendo', 'ambient'), ('freesound', 'cinematic')]
BAD = ['vocal', 'song', 'sung', 'lyrics', 'rap', 'podcast', 'interview', 'voice', 'radio', 'trance', 'dubstep', 'remix', 'field recording', 'room tone', 'soundscape']
WANT = int(sys.argv[1]) if len(sys.argv) > 1 else 12  # beds
def beds(): return sum(1 for v in credits.values() if v['category'] == 'music')
seen = {v['source'] for v in credits.values()}
for src, q in QUERIES:
    if beds() >= WANT: break
    u = f'https://api.openverse.org/v1/audio/?q={urllib.parse.quote(q)}&license=cc0,by&page_size=20&source={src}&length=medium'
    time.sleep(1.5)
    try: res = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))['results']
    except Exception as e: print('api', q, e); continue
    for r in res:
        if beds() >= WANT: break
        t = (r['title'] + ' ' + ' '.join(r.get('genres') or [])).lower(); d = (r.get('duration') or 0) / 1000
        if any(b in t for b in BAD) or r['foreign_landing_url'] in seen or not 100 <= d <= 600: continue
        raw = os.path.join(ROOT, 'music', 'tmp.src'); time.sleep(3)
        try: open(raw, 'wb').write(urllib.request.urlopen(urllib.request.Request(r['url'], headers=UA), timeout=180).read())
        except Exception as e: print('dl fail', r['title'][:40], e); continue
        seen.add(r['foreign_landing_url']); n = 0
        for start in ([d * 0.1, d * 0.5] if d >= 200 else [min(5, d * 0.05)]):
            name = f"music_{r['id'][:8]}_{n}.mp3"; out = os.path.join(ROOT, 'music', name)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(start), '-t', '95', '-i', raw, '-af', 'afade=t=in:d=1.5,afade=t=out:st=92:d=3,loudnorm=I=-20:TP=-2', '-ar', '44100', '-ac', '2', '-b:a', '192k', out])
            vol = subprocess.run(['ffmpeg', '-i', out, '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True).stderr
            mean = float(vol.split('mean_volume:')[1].split('dB')[0]) if 'mean_volume' in vol else -99
            if mean < -35: os.remove(out); continue
            credits[name] = dict(title=r['title'], creator=r.get('creator'), license=r['license'] + ' ' + (r.get('license_version') or ''),
                                 source=r['foreign_landing_url'], seconds=95, category='music', used_in=None, origin=src, genres=r.get('genres'))
            json.dump(credits, open(CRED, 'w'), indent=1); n += 1
        os.remove(raw); print('music', src, r['title'][:55], '|', r.get('creator'), r['license'], f'({n} beds)')
print(beds(), 'music beds')
