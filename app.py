import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import re
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="public")

GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
FOOTBALLDATA_KEY = os.environ.get("FOOTBALLDATA_KEY", "")

# football-data.org — Coupe du Monde = code "WC"
API_BASE = "https://api.football-data.org/v4"

# ─── Drapeaux emoji ───────────────────────────────────────────────────────────
DRAPEAUX = {
    "France":"🇫🇷","Brazil":"🇧🇷","Argentina":"🇦🇷","Germany":"🇩🇪",
    "Spain":"🇪🇸","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Portugal":"🇵🇹","Netherlands":"🇳🇱",
    "Belgium":"🇧🇪","Croatia":"🇭🇷","Morocco":"🇲🇦","Senegal":"🇸🇳",
    "Japan":"🇯🇵","South Korea":"🇰🇷","United States":"🇺🇸","USA":"🇺🇸",
    "Mexico":"🇲🇽","Canada":"🇨🇦","Saudi Arabia":"🇸🇦","Nigeria":"🇳🇬",
    "Cameroon":"🇨🇲","Uruguay":"🇺🇾","Colombia":"🇨🇴","Ecuador":"🇪🇨",
    "Peru":"🇵🇪","Chile":"🇨🇱","Poland":"🇵🇱","Serbia":"🇷🇸",
    "Denmark":"🇩🇰","Switzerland":"🇨🇭","Austria":"🇦🇹","Turkey":"🇹🇷",
    "Ukraine":"🇺🇦","Ghana":"🇬🇭","Ivory Coast":"🇨🇮","Egypt":"🇪🇬",
    "Tunisia":"🇹🇳","Algeria":"🇩🇿","Iran":"🇮🇷","Australia":"🇦🇺",
    "Costa Rica":"🇨🇷","Panama":"🇵🇦","Jamaica":"🇯🇲","Qatar":"🇶🇦",
    "Kazakhstan":"🇰🇿","Suriname":"🇸🇷","Venezuela":"🇻🇪","Bolivia":"🇧🇴",
    "Paraguay":"🇵🇾","South Africa":"🇿🇦","Mali":"🇲🇱","Benin":"🇧🇯",
    "Czech Republic":"🇨🇿","Slovakia":"🇸🇰","Slovenia":"🇸🇮","Hungary":"🇭🇺",
    "Romania":"🇷🇴","Norway":"🇳🇴","Sweden":"🇸🇪","Finland":"🇫🇮",
    "Georgia":"🇬🇪","Albania":"🇦🇱","Israel":"🇮🇱","Wales":"🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","Indonesia":"🇮🇩","New Zealand":"🇳🇿",
}

def utc_to_montreal(utc_str):
    """Convertit une date ISO UTC vers l'heure de Montréal (America/Montreal).
    EDT = UTC-4 (2e dim mars → 1er dim nov)
    EST = UTC-5 (reste de l'année)
    La Coupe du Monde 2026 se joue juin-juillet → toujours EDT (UTC-4).
    """
    if not utc_str:
        return "", ""
    try:
        # format: 2026-06-11T20:00:00Z  ou  2026-06-11T20:00:00+00:00
        utc_str_clean = utc_str.replace("Z", "+00:00")
        dt_utc = datetime.fromisoformat(utc_str_clean)
        # EDT = UTC-4 (juin-juillet = toujours EDT pour Montréal)
        montreal_offset = timedelta(hours=-4)
        dt_mtl = dt_utc + montreal_offset
        return dt_mtl.strftime("%Y-%m-%d"), dt_mtl.strftime("%H:%M")
    except Exception:
        return utc_str[:10], utc_str[11:16]


def get_drapeau(nom):
    return DRAPEAUX.get(nom, "🏳️")

# ─── Cache mémoire ────────────────────────────────────────────────────────────
_cache = {}

def cache_get(key):
    e = _cache.get(key)
    if e and time.time() - e["ts"] < e["ttl"]:
        return e["data"]
    return None

def cache_set(key, data, ttl=60):
    _cache[key] = {"data": data, "ts": time.time(), "ttl": ttl}

# ─── Appel API football-data.org ─────────────────────────────────────────────
def api_call(endpoint, params=None):
    if not FOOTBALLDATA_KEY:
        return None, "FOOTBALLDATA_KEY manquante dans les variables d'environnement."

    url = f"{API_BASE}/{endpoint}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"

    req = urllib.request.Request(url, headers={
        "X-Auth-Token": FOOTBALLDATA_KEY,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            msg = json.loads(body).get("message", f"HTTP {e.code}")
        except Exception:
            msg = f"HTTP {e.code}: {e.reason}"
        return None, msg
    except Exception as e:
        return None, str(e)

# ─── Statut match ─────────────────────────────────────────────────────────────
# football-data statuses: SCHEDULED, TIMED, IN_PLAY, PAUSED, FINISHED, SUSPENDED, POSTPONED, CANCELLED
def parse_statut(status):
    if status in ("IN_PLAY", "PAUSED"):
        return "live"
    if status in ("FINISHED",):
        return "fini"
    return "prevu"

def format_match(m):
    status  = m.get("status", "SCHEDULED")
    statut  = parse_statut(status)
    home    = m.get("homeTeam", {})
    away    = m.get("awayTeam", {})
    score   = m.get("score", {})
    ft      = score.get("fullTime", {})
    ht_sc   = score.get("halfTime", {})
    minute  = m.get("minute")  # pas toujours fourni
    dt      = m.get("utcDate", "") or ""

    # Score selon le statut
    home_score = ft.get("home") if statut in ("live","fini") else None
    away_score = ft.get("away") if statut in ("live","fini") else None

    date_mtl, heure_mtl = utc_to_montreal(dt)
    return {
        "id":      m.get("id"),
        "groupe":  m.get("stage", "") + " — " + (m.get("group") or m.get("matchday","") or ""),
        "statut":  statut,
        "minute":  minute,
        "domicile": {
            "nom":     home.get("name", ""),
            "drapeau": get_drapeau(home.get("name", "")),
            "score":   home_score,
        },
        "exterieur": {
            "nom":     away.get("name", ""),
            "drapeau": get_drapeau(away.get("name", "")),
            "score":   away_score,
        },
        "stade":  m.get("venue", ""),
        "ville":  "",
        "date":   date_mtl,
        "heure":  heure_mtl + " EDT",
        "status_raw": status,
    }

# ─── Routes API ───────────────────────────────────────────────────────────────

@app.route("/api/matches")
def api_matches():
    cached = cache_get("matches")
    if cached is not None:
        return jsonify(cached)

    data, err = api_call("competitions/WC/matches")
    if err:
        return jsonify({"error": err}), 500

    matches_raw = data.get("matches", [])
    result = [format_match(m) for m in matches_raw]

    order = {"live": 0, "fini": 1, "prevu": 2}
    result.sort(key=lambda m: (order.get(m["statut"], 9), m["date"]))

    has_live = any(m["statut"] == "live" for m in result)
    cache_set("matches", result, ttl=30 if has_live else 300)
    return jsonify(result)


@app.route("/api/groupes")
def api_groupes():
    cached = cache_get("groupes")
    if cached is not None:
        return jsonify(cached)

    data, err = api_call("competitions/WC/standings")
    if err:
        return jsonify({"error": err}), 500

    standings = data.get("standings", [])
    groupes = []
    for s in standings:
        if s.get("type") != "TOTAL":
            continue
        group_name = s.get("group", "")
        lettre = group_name.replace("GROUP_", "").replace("GROUP ", "").strip()
        equipes = []
        for entry in s.get("table", []):
            team = entry.get("team", {})
            equipes.append({
                "nom":     team.get("name", ""),
                "drapeau": get_drapeau(team.get("name", "")),
                "pts": entry.get("points", 0),
                "j":  entry.get("playedGames", 0),
                "g":  entry.get("won", 0),
                "n":  entry.get("draw", 0),
                "p":  entry.get("lost", 0),
                "bp": entry.get("goalsFor", 0),
                "bc": entry.get("goalsAgainst", 0),
            })
        groupes.append({"lettre": lettre, "equipes": equipes})

    cache_set("groupes", groupes, ttl=300)
    return jsonify(groupes)


@app.route("/api/stats")
def api_stats():
    cached = cache_get("stats")
    if cached is not None:
        return jsonify(cached)

    matches = cache_get("matches") or []
    joues = sum(1 for m in matches if m["statut"] in ("fini","live"))
    buts  = sum(
        (m["domicile"]["score"] or 0) + (m["exterieur"]["score"] or 0)
        for m in matches if m["statut"] in ("fini","live")
    )
    live  = sum(1 for m in matches if m["statut"] == "live")
    moy   = round(buts / joues, 1) if joues else 0

    result = {"joues": joues, "buts": buts, "live": live, "moy": moy, "equipes": 48, "total": 104}
    cache_set("stats", result, ttl=60)
    return jsonify(result)


# ─── Actualités via Google News RSS (sans clé) ───────────────────────────────
def fetch_news(query, max_items=6):
    cached = cache_get(f"news:{query}")
    if cached is not None:
        return cached
    q = urllib.parse.quote(query + " coupe du monde 2026")
    url = f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml = resp.read().decode("utf-8")
    except Exception:
        return []
    items = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)[:max_items]:
        title   = re.search(r"<title>(.*?)</title>", item)
        source  = re.search(r"<source[^>]*>(.*?)</source>", item)
        pubdate = re.search(r"<pubDate>(.*?)</pubDate>", item)
        if not title:
            continue
        titre = re.sub(r"<[^>]+>", "", title.group(1))
        titre = re.sub(r"\s*-\s*[^-]+$", "", titre).strip()
        src   = re.sub(r"<[^>]+>", "", source.group(1)) if source else ""
        age   = ""
        if pubdate:
            try:
                from email.utils import parsedate_to_datetime
                dt  = parsedate_to_datetime(pubdate.group(1))
                diff = int(time.time() - dt.timestamp())
                if diff < 3600:   age = f"il y a {diff // 60} min"
                elif diff < 86400: age = f"il y a {diff // 3600}h"
                else:              age = f"il y a {diff // 86400}j"
            except Exception:
                pass
        if titre:
            items.append({"titre": titre, "source": src, "age": age})
    cache_set(f"news:{query}", items, ttl=600)
    return items


@app.route("/api/news")
def api_news():
    q = request.args.get("q", "coupe du monde 2026")
    return jsonify(fetch_news(q))


@app.route("/api/gemini", methods=["POST"])
def api_gemini():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Clé API Gemini manquante."}), 500
    body    = request.get_json() or {}
    message = body.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message vide."}), 400

    matches_ctx = cache_get("matches") or []
    groupes_ctx = cache_get("groupes") or []
    news_ctx    = fetch_news(message[:80])

    system_prompt = f"""Tu es un expert en football et analyste sportif pour la Coupe du Monde 2026.

DONNÉES EN TEMPS RÉEL — MATCHS :
{json.dumps(matches_ctx[:20], ensure_ascii=False)}

CLASSEMENTS DES GROUPES :
{json.dumps(groupes_ctx, ensure_ascii=False)}

ACTUALITÉS RÉCENTES (Google News) :
{json.dumps(news_ctx, ensure_ascii=False)}

Réponds en français. Sois précis, complet et enthousiaste.
Si les actualités contiennent des infos pertinentes, mentionne-les.
Développe ta réponse en 3 à 5 phrases bien construites."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = json.dumps({
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": message}]}],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7}
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"reponse": text, "news": news_ctx})
    except urllib.error.HTTPError as e:
        err_body = json.loads(e.read().decode())
        return jsonify({"error": err_body.get("error", {}).get("message", "Erreur Gemini")}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"\n🏆  Coupe du Monde 2026 — football-data.org")
    print(f"    → http://localhost:{port}\n")
    if not FOOTBALLDATA_KEY:
        print("    ⚠️  FOOTBALLDATA_KEY non configurée\n")
    if not GEMINI_API_KEY:
        print("    ⚠️  GEMINI_API_KEY non configurée\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
