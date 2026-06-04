import os
import json
import time
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import streamlit as st

# ─── Configuration page ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Coupe du Monde 2026",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Clés API (depuis st.secrets ou variables d'env) ─────────────────────────
def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

FOOTBALLDATA_KEY = get_secret("FOOTBALLDATA_KEY")
GEMINI_API_KEY   = get_secret("GEMINI_API_KEY")

API_BASE  = "https://api.football-data.org/v4"

# ─── CSS personnalisé ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }

.header-box {
    background: #0f4f2e;
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 14px;
}
.header-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: white;
    margin: 0;
}
.header-sub { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 2px; }

.match-card {
    background: white;
    border: 1px solid #e8e8e5;
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 10px;
}
.match-card.live { border-left: 3px solid #c0392b; }

.match-teams {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}
.team-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 18px;
    font-weight: 600;
}
.score {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 26px;
    font-weight: 700;
    color: #1a1a18;
    text-align: center;
    min-width: 70px;
}
.badge-live {
    background: #fdf0f0;
    color: #c0392b;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 5px;
    display: inline-block;
}
.badge-fini {
    background: #f5f5f3;
    color: #9e9e99;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 5px;
    display: inline-block;
}
.badge-prevu {
    background: #e9f1fb;
    color: #1a5fa8;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 5px;
    display: inline-block;
}
.venue { font-size: 11px; color: #9e9e99; margin-top: 6px; }
.round-label { font-size: 11px; color: #9e9e99; text-transform: uppercase; letter-spacing: .5px; }

.group-card {
    background: white;
    border: 1px solid #e8e8e5;
    border-radius: 12px;
    padding: .8rem 1rem;
    margin-bottom: 10px;
}
.group-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .7px;
    color: #1a7a4a;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid #e8e8e5;
}
.group-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 0;
    font-size: 13px;
    border-bottom: 1px solid #f5f5f3;
}
.group-row:last-child { border-bottom: none; }
.group-pts {
    margin-left: auto;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: #3d3d3a;
}
.group-pts.leader { color: #1a7a4a; }

.news-card {
    background: white;
    border: 1px solid #e8e8e5;
    border-radius: 12px;
    padding: .8rem 1rem;
    margin-bottom: 8px;
}
.news-source { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; color: #1a7a4a; }
.news-title { font-size: 14px; font-weight: 500; color: #1a1a18; line-height: 1.4; margin: 3px 0; }
.news-age { font-size: 11px; color: #9e9e99; }

.ai-box {
    background: #e4f5ed;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    color: #0f4f2e;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
}
.stat-val {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 32px;
    font-weight: 700;
    color: #1a1a18;
}
.stat-label { font-size: 11px; color: #9e9e99; text-transform: uppercase; letter-spacing: .5px; }

.sep {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 11px;
    color: #9e9e99;
    text-transform: uppercase;
    letter-spacing: .6px;
    margin: 12px 0 8px;
}
.sep-line { flex: 1; height: 1px; background: #e8e8e5; }

/* Masquer le menu hamburger et le footer Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# ─── Drapeaux ────────────────────────────────────────────────────────────────
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
    "Paraguay":"🇵🇾","South Africa":"🇿🇦","Mali":"🇲🇱","Indonesia":"🇮🇩",
    "New Zealand":"🇳🇿","Czech Republic":"🇨🇿","Slovakia":"🇸🇰",
    "Hungary":"🇭🇺","Romania":"🇷🇴","Norway":"🇳🇴","Sweden":"🇸🇪",
    "Georgia":"🇬🇪","Albania":"🇦🇱","Israel":"🇮🇱",
}
def flag(name): return DRAPEAUX.get(name, "🏳️")

# ─── Cache Streamlit ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_matches():
    if not FOOTBALLDATA_KEY:
        return None, "FOOTBALLDATA_KEY manquante"
    req = urllib.request.Request(
        f"{API_BASE}/competitions/WC/matches",
        headers={"X-Auth-Token": FOOTBALLDATA_KEY}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        return data.get("matches", []), None
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        try: msg = json.loads(msg).get("message", msg)
        except: pass
        return None, msg
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_standings():
    if not FOOTBALLDATA_KEY:
        return None, "FOOTBALLDATA_KEY manquante"
    req = urllib.request.Request(
        f"{API_BASE}/competitions/WC/standings",
        headers={"X-Auth-Token": FOOTBALLDATA_KEY}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        return data.get("standings", []), None
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        try: msg = json.loads(msg).get("message", msg)
        except: pass
        return None, msg
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=600, show_spinner=False)
def fetch_news(query):
    q = urllib.parse.quote(query + " coupe du monde 2026")
    url = f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8")
    except Exception:
        return []
    items = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)[:8]:
        title   = re.search(r"<title>(.*?)</title>", item)
        source  = re.search(r"<source[^>]*>(.*?)</source>", item)
        pubdate = re.search(r"<pubDate>(.*?)</pubDate>", item)
        if not title: continue
        titre = re.sub(r"<[^>]+>", "", title.group(1))
        titre = re.sub(r"\s*-\s*[^-]+$", "", titre).strip()
        src   = re.sub(r"<[^>]+>", "", source.group(1)) if source else ""
        age   = ""
        if pubdate:
            try:
                dt   = parsedate_to_datetime(pubdate.group(1))
                diff = int(time.time() - dt.timestamp())
                if diff < 3600:    age = f"il y a {diff//60} min"
                elif diff < 86400: age = f"il y a {diff//3600}h"
                else:              age = f"il y a {diff//86400}j"
            except: pass
        if titre:
            items.append({"titre": titre, "source": src, "age": age})
    return items

# ─── Helpers ──────────────────────────────────────────────────────────────────
MONTHS = ["jan","fév","mar","avr","mai","juin","juil","août","sep","oct","nov","déc"]

def utc_to_montreal(utc_str):
    if not utc_str: return "", ""
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        dt_mtl = dt + timedelta(hours=-4)  # EDT (juin-juillet)
        return dt_mtl.strftime("%Y-%m-%d"), dt_mtl.strftime("%H:%M")
    except:
        return utc_str[:10], utc_str[11:16]

def fmt_date(iso):
    if not iso: return ""
    try:
        y, mo, d = iso.split("-")
        return f"{int(d)} {MONTHS[int(mo)-1]}"
    except: return iso

def fmt_round(r):
    return (r or "").replace("GROUP_STAGE","Phase de groupes").replace(
        "ROUND_OF_16","Huitièmes").replace("QUARTER_FINALS","Quarts").replace(
        "SEMI_FINALS","Demi-finales").replace("THIRD_PLACE","3ᵉ place").replace(
        "FINAL","Finale").replace("_"," ")

def parse_statut(status):
    if status in ("IN_PLAY","PAUSED"): return "live"
    if status in ("FINISHED",):       return "fini"
    return "prevu"

def format_match(m):
    status = m.get("status","SCHEDULED")
    statut = parse_statut(status)
    home   = m.get("homeTeam",{})
    away   = m.get("awayTeam",{})
    score  = m.get("score",{}).get("fullTime",{})
    dt     = m.get("utcDate","") or ""
    date_mtl, heure_mtl = utc_to_montreal(dt)
    minute = m.get("minute")
    home_score = score.get("home") if statut in ("live","fini") else None
    away_score = score.get("away") if statut in ("live","fini") else None
    return {
        "id":      m.get("id"),
        "round":   fmt_round(m.get("stage","") + " " + (m.get("group") or "")),
        "statut":  statut,
        "minute":  minute,
        "home":    {"nom": home.get("name",""), "flag": flag(home.get("name","")), "score": home_score},
        "away":    {"nom": away.get("name",""), "flag": flag(away.get("name","")), "score": away_score},
        "stade":   m.get("venue",""),
        "date":    date_mtl,
        "heure":   heure_mtl,
    }

def ask_gemini(message, matches_ctx, groupes_ctx, news_ctx):
    if not GEMINI_API_KEY:
        return "❌ Clé GEMINI_API_KEY manquante dans les secrets Streamlit."
    system_prompt = (
        "Tu es un expert en football pour la Coupe du Monde 2026.\n\n"
        "MATCHS:\n" + json.dumps(matches_ctx[:20], ensure_ascii=False) + "\n\n"
        "CLASSEMENTS:\n" + json.dumps(groupes_ctx, ensure_ascii=False) + "\n\n"
        "ACTUALITÉS:\n" + json.dumps(news_ctx, ensure_ascii=False) + "\n\n"
        "Réponds en français, 3-5 phrases, sois enthousiaste et précis."
    )
    for model in ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.0-flash"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = json.dumps({
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": message}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7}
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                result = json.loads(r.read().decode())
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            try: last_err = json.loads(err).get("error",{}).get("message", err[:100])
            except: last_err = err[:100]
            continue
        except Exception as e:
            last_err = str(e)
            continue
    return f"❌ Erreur Gemini : {last_err}"

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-box">
  <span style="font-size:36px">🏆</span>
  <div>
    <div class="header-title">Coupe du Monde FIFA 2026</div>
    <div class="header-sub">États-Unis · Canada · Mexique &nbsp;|&nbsp; 11 juin – 19 juillet 2026 &nbsp;|&nbsp; Horaires Montréal (EDT)</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Chargement des données ───────────────────────────────────────────────────
with st.spinner("Chargement des données..."):
    raw_matches, err_m = fetch_matches()
    raw_standings, err_s = fetch_standings()

matches = []
if raw_matches:
    matches = [format_match(m) for m in raw_matches]
    matches.sort(key=lambda m: {"live":0,"fini":1,"prevu":2}.get(m["statut"],9))

# ─── Stats ────────────────────────────────────────────────────────────────────
joues = sum(1 for m in matches if m["statut"] in ("fini","live"))
buts  = sum((m["home"]["score"] or 0)+(m["away"]["score"] or 0)
             for m in matches if m["statut"] in ("fini","live"))
live  = sum(1 for m in matches if m["statut"] == "live")
moy   = round(buts/joues,1) if joues else 0

c1,c2,c3,c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-val">{joues}</div><div class="stat-label">Matchs joués / 104</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-val">{buts}</div><div class="stat-label">Buts · {moy}/match</div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-val">48</div><div class="stat-label">Équipes · 16 groupes</div>', unsafe_allow_html=True)
with c4:
    color = "#c0392b" if live else "#1a1a18"
    st.markdown(f'<div class="stat-val" style="color:{color}">{live}</div><div class="stat-label">Matchs en direct</div>', unsafe_allow_html=True)

st.divider()

# ─── Onglets ──────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["⚽ Résultats", "📊 Groupes", "📰 Actualités", "✨ Analyser avec Gemini"])

# ══ TAB 1 : Résultats ═════════════════════════════════════════════════════════
with tab1:
    if err_m:
        st.error(f"Erreur : {err_m}")
    elif not matches:
        st.info("Aucun match disponible pour le moment.")
    else:
        groups = {"live":[], "fini":[], "prevu":[]}
        for m in matches:
            groups[m["statut"]].append(m)

        labels = {"live":"🔴 En direct", "fini":"✅ Terminés", "prevu":"🕒 À venir"}

        for key in ["live","fini","prevu"]:
            if not groups[key]: continue
            st.markdown(f'<div class="sep"><div class="sep-line"></div><span>{labels[key]}</span><div class="sep-line"></div></div>', unsafe_allow_html=True)
            for m in groups[key]:
                live_cls = " live" if m["statut"]=="live" else ""

                # Badge statut
                if m["statut"] == "live":
                    min_txt = f"{m['minute']}'" if m['minute'] else "LIVE"
                    badge = f'<span class="badge-live">🔴 {min_txt}</span>'
                elif m["statut"] == "fini":
                    badge = '<span class="badge-fini">Terminé</span>'
                else:
                    info = " · ".join(filter(None, [fmt_date(m["date"]), m["heure"] + " EDT" if m["heure"] else ""]))
                    badge = f'<span class="badge-prevu">{info or "À venir"}</span>'

                # Score
                if m["home"]["score"] is not None:
                    score_html = f'<div class="score">{m["home"]["score"]} – {m["away"]["score"]}</div>'
                else:
                    score_html = '<div class="score" style="font-size:16px;color:#9e9e99">vs</div>'

                venue = m["stade"] or ""
                venue_html = f'<div class="venue">📍 {venue}</div>' if venue else ""

                st.markdown(f"""
                <div class="match-card{live_cls}">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span class="round-label">{m["round"]}</span>
                    {badge}
                  </div>
                  <div class="match-teams">
                    <div style="display:flex;align-items:center;gap:8px;flex:1">
                      <span style="font-size:22px">{m["home"]["flag"]}</span>
                      <span class="team-name">{m["home"]["nom"]}</span>
                    </div>
                    {score_html}
                    <div style="display:flex;align-items:center;gap:8px;flex:1;justify-content:flex-end">
                      <span class="team-name">{m["away"]["nom"]}</span>
                      <span style="font-size:22px">{m["away"]["flag"]}</span>
                    </div>
                  </div>
                  {venue_html}
                </div>
                """, unsafe_allow_html=True)

# ══ TAB 2 : Groupes ══════════════════════════════════════════════════════════
with tab2:
    if err_s:
        st.error(f"Erreur : {err_s}")
    elif not raw_standings:
        st.info("Classements pas encore disponibles — le tournoi démarre le 11 juin 2026.")
    else:
        total_groups = [s for s in raw_standings if s.get("type") == "TOTAL"]
        if not total_groups:
            st.info("Classements pas encore disponibles.")
        else:
            cols = st.columns(4)
            for i, s in enumerate(total_groups):
                lettre = s.get("group","").replace("GROUP_","").replace("GROUP ","").strip()
                table  = s.get("table", [])
                col    = cols[i % 4]
                with col:
                    rows = ""
                    for j, entry in enumerate(table):
                        team = entry.get("team",{})
                        pts  = entry.get("points",0)
                        leader_cls = " leader" if j < 2 and pts > 0 else ""
                        rows += f'''<div class="group-row">
                            <span style="font-size:14px">{flag(team.get("name",""))}</span>
                            <span style="font-size:13px">{team.get("name","")}</span>
                            <span class="group-pts{leader_cls}">{pts} pts</span>
                        </div>'''
                    st.markdown(f'''<div class="group-card">
                        <div class="group-title">Groupe {lettre}</div>
                        {rows}
                    </div>''', unsafe_allow_html=True)

# ══ TAB 3 : Actualités ═══════════════════════════════════════════════════════
with tab3:
    st.markdown("#### Actualités des équipes")
    query = st.text_input("🔍 Rechercher une équipe", placeholder="Ex: France, Brésil, Maroc…", label_visibility="collapsed")

    EQUIPE_FLAGS = {
        "france":"🇫🇷","brésil":"🇧🇷","brazil":"🇧🇷","argentine":"🇦🇷","argentina":"🇦🇷",
        "allemagne":"🇩🇪","germany":"🇩🇪","espagne":"🇪🇸","spain":"🇪🇸",
        "angleterre":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","england":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","portugal":"🇵🇹",
        "maroc":"🇲🇦","morocco":"🇲🇦","usa":"🇺🇸","mexique":"🇲🇽","canada":"🇨🇦",
    }

    search_q = query.strip() if query.strip() else "coupe du monde 2026"
    news = fetch_news(search_q)
    eflag = EQUIPE_FLAGS.get(search_q.lower(), "📰")

    if not news:
        st.info("Aucune actualité trouvée. Essayez un autre terme.")
    else:
        for n in news:
            st.markdown(f"""<div class="news-card">
                <div style="display:flex;gap:12px;align-items:flex-start">
                  <span style="font-size:24px;flex-shrink:0">{eflag}</span>
                  <div>
                    <div class="news-source">{n["source"]}</div>
                    <div class="news-title">{n["titre"]}</div>
                    <div class="news-age">{n["age"]}</div>
                  </div>
                </div>
            </div>""", unsafe_allow_html=True)

# ══ TAB 4 : IA Gemini ════════════════════════════════════════════════════════
with tab4:
    st.markdown("#### Analyser avec Gemini")

    col_btns = st.columns(5)
    quick_prompts = [
        ("🏅 Favoris",        "Qui sont les favoris du tournoi et pourquoi ?"),
        ("😮 Surprises",      "Quelles sont les surprises et déceptions des matchs joués ?"),
        ("🌍 Afrique",        "Quelles équipes africaines ont des chances de passer en huitièmes ?"),
        ("📋 Résumé",         "Fais un résumé complet de tous les matchs terminés"),
        ("🔜 Prochain choc",  "Quel est le prochain match le plus attendu ?"),
    ]

    if "ai_question" not in st.session_state:
        st.session_state.ai_question = ""

    for i, (label, prompt) in enumerate(quick_prompts):
        with col_btns[i]:
            if st.button(label, use_container_width=True):
                st.session_state.ai_question = prompt

    question = st.text_input(
        "Ta question",
        value=st.session_state.ai_question,
        placeholder="Pose ta question sur la Coupe du Monde…",
        label_visibility="collapsed",
        key="ai_input"
    )

    if st.button("Envoyer ✨", type="primary", use_container_width=False):
        if question.strip():
            # Préparer le contexte
            matches_ctx = [format_match(m) for m in (raw_matches or [])[:20]]
            groupes_ctx = []
            if raw_standings:
                for s in raw_standings:
                    if s.get("type") != "TOTAL": continue
                    lettre = s.get("group","").replace("GROUP_","").strip()
                    equipes = [{"nom": e.get("team",{}).get("name",""), "pts": e.get("points",0)}
                               for e in s.get("table",[])]
                    groupes_ctx.append({"lettre": lettre, "equipes": equipes})
            news_ctx = fetch_news(question[:80])

            with st.spinner("Gemini analyse..."):
                reponse = ask_gemini(question.strip(), matches_ctx, groupes_ctx, news_ctx)

            st.markdown(f'<div class="ai-box">✨ {reponse}</div>', unsafe_allow_html=True)

            if news_ctx:
                with st.expander("📰 Sources actualités utilisées"):
                    for n in news_ctx:
                        st.markdown(f"**{n['titre']}** — *{n['source']}* {n['age']}")
        else:
            st.warning("Entrez une question d'abord.")

# ─── Rafraîchissement ─────────────────────────────────────────────────────────
if live > 0:
    st.caption("🔴 Match en direct — la page se rafraîchit automatiquement toutes les 60s")
    time.sleep(1)
    st.rerun()
