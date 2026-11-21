"""Collect CC0/CC-BY sound effects and music from Openverse into audio_lib/. Logs licenses to audio_lib/CREDITS.json."""
import json, os, subprocess, urllib.request, urllib.parse, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audio_lib'); CRED = os.path.join(ROOT, 'CREDITS.json')
credits = json.load(open(CRED)) if os.path.exists(CRED) else {}
SFX = {  # category: (queries, max_seconds, how many)
 'pop': (['pop', 'bubble pop', 'blip pop'], 1.2, 6), 'whoosh': (['whoosh', 'swoosh', 'swish fast'], 2.0, 6),
 'whip': (['whip pan whoosh', 'fast swoosh transition'], 1.5, 3), 'boom': (['explosion', 'distant explosion', 'boom'], 4.0, 5),
 'artillery': (['cannon shot', 'artillery'], 3.5, 4), 'type': (['typewriter key', 'keyboard click'], 0.6, 5),
 'ding': (['ding', 'bell ding'], 2.0, 3), 'impact': (['impact hit', 'thud'], 2.0, 4), 'riser': (['riser', 'rising tension'], 4.0, 3),
 'paper': (['paper rustle', 'page turn'], 2.5, 4), 'stamp': (['stamp', 'rubber stamp'], 1.5, 3), 'rifle': (['rifle shot', 'gunshot'], 2.0, 4),
 'plane': (['propeller plane flyby', 'airplane flyby'], 6.0, 3), 'shimmer': (['sparkle', 'magic shimmer'], 2.5, 3), 'fire': (['fire crackle'], 8.0, 2),
}
MUSIC = (['documentary background music', 'cinematic ambient', 'orchestral tension', 'calm background music', 'epic cinematic', 'inspiring background'], 60, 14)
UA={'User-Agent':'geo-style-pipeline/1.0 (curl compatible)'}
def fetch(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60)
def api(q, lic, extra=''):
    u = f'https://api.openverse.org/v1/audio/?q={urllib.parse.quote(q)}&license={lic}&page_size=20{extra}'
    import time; time.sleep(1.2)
    try: return json.load(fetch(u))['results']
    except Exception as e: print('api fail', q, e); return []
def dur(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True); return float(r.stdout or 0)
def grab(cat, rec, folder, maxd=None, mind=None):
    import time; time.sleep(2)  # be polite to hosts
    if (rec.get('duration') or 0) and maxd and rec['duration'] / 1000 > maxd: return False
    if (rec.get('duration') or 0) and mind and rec['duration'] / 1000 < mind: return False
    if folder.endswith('sfx') and (rec.get('duration') or 0) and rec['duration'] < 80: return False  # near-empty clips
    name = f"{cat}_{rec['id'][:8]}"; raw = os.path.join(folder, name + '.src')
    try: open(raw, 'wb').write(fetch(rec['url']).read())
    except Exception as e: return False
    out = os.path.join(folder, name + ('.wav' if folder.endswith('sfx') else '.mp3'))
    args = ['ffmpeg', '-v', 'error', '-y', '-i', raw] + (['-af', 'silenceremove=start_periods=1:start_threshold=-45dB,loudnorm=I=-16:TP=-1.5', '-ar', '44100', '-ac', '2'] if folder.endswith('sfx') else ['-ar', '44100', '-b:a', '192k']) + [out]
    ok = subprocess.run(args).returncode == 0; os.remove(raw)
    d = dur(out) if ok else 0
    if not ok or d == 0 or (maxd and folder.endswith('sfx') and d > maxd * 1.2) or (mind and d < mind):
        if os.path.exists(out): os.remove(out); return False
    credits[os.path.basename(out)] = dict(title=rec['title'], creator=rec.get('creator'), license=rec['license'] + ' ' + (rec.get('license_version') or ''), source=rec.get('foreign_landing_url'), seconds=round(d, 2), category=cat)
    json.dump(credits, open(CRED, 'w'), indent=1)  # save as we go so a timeout keeps credits
    return True
for cat, (qs, maxd, n) in SFX.items():
    have = sum(1 for v in credits.values() if v['category'] == cat)
    for q in qs:
        if have >= n: break
        for rec in api(q, 'cc0', '&length=shortest'):  # 'short' is 30s-2min on Openverse; SFX need <30s
            if have >= n: break
            if any(v['source'] == rec.get('foreign_landing_url') for v in credits.values()): continue
            if grab(cat, rec, os.path.join(ROOT, 'sfx'), maxd): have += 1; print(cat, rec['title'])
qs, mind, n = MUSIC; have = sum(1 for v in credits.values() if v['category'] == 'music')
for q in qs:
    for rec in api(q, 'cc0,by', '&length=long'):
        if have >= n: break
        if any(v['source'] == rec.get('foreign_landing_url') for v in credits.values()): continue
        if grab('music', rec, os.path.join(ROOT, 'music'), None, mind): have += 1; print('music', rec['title'], rec['license'])
json.dump(credits, open(CRED, 'w'), indent=1)
print(len(credits), 'files')
