"""
╔══════════════════════════════════════════════════════════════════════╗
║       XAU/USD — STRATÉGIE GBP MAN — STREAMLIT DASHBOARD            ║
║       Source : TradingView / OANDA (données Forex réelles)          ║
║       Alertes : Telegram                                             ║
║       Serveur : Streamlit Community Cloud                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import os
from datetime import datetime

try:
    from tvdatafeed import TvDatafeed, Interval
    TV_AVAILABLE = True
except ImportError:
    TV_AVAILABLE = False

try:
    import ta
except ImportError:
    st.error("pip install ta")
    st.stop()

# ─────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="XAU/USD · GBP Man Strategy",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────
# CSS CUSTOM
# ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0f;
    color: #e8e6df;
}

.stApp { background-color: #0a0a0f; }

.main-header {
    font-family: 'Space Mono', monospace;
    font-size: 2.2rem;
    font-weight: 700;
    color: #f5c842;
    letter-spacing: -0.02em;
    margin-bottom: 0;
}

.sub-header {
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    color: #5a5a6e;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 0;
}

.signal-card {
    background: #12121a;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
}

.signal-buy {
    border-left: 4px solid #22c55e;
    background: linear-gradient(135deg, #0f1f14 0%, #12121a 100%);
}

.signal-sell {
    border-left: 4px solid #ef4444;
    background: linear-gradient(135deg, #1f0f0f 0%, #12121a 100%);
}

.signal-watch {
    border-left: 4px solid #f5c842;
    background: linear-gradient(135deg, #1f1a0a 0%, #12121a 100%);
}

.signal-wait {
    border-left: 4px solid #3a3a4e;
    background: #12121a;
}

.price-display {
    font-family: 'Space Mono', monospace;
    font-size: 3rem;
    font-weight: 700;
    color: #f5c842;
    line-height: 1;
}

.signal-badge {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 999px;
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}

.badge-buy  { background: #16a34a22; color: #22c55e; border: 1px solid #22c55e55; }
.badge-sell { background: #dc262622; color: #ef4444; border: 1px solid #ef444455; }
.badge-watch{ background: #ca8a0422; color: #f5c842; border: 1px solid #f5c84255; }
.badge-wait { background: #3a3a4e22; color: #6b7280; border: 1px solid #3a3a4e55; }

.confluence-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: #0d0d14;
    border-radius: 8px;
    margin-bottom: 8px;
    border: 1px solid #1a1a2a;
    font-size: 0.9rem;
}

.ok   { color: #22c55e; }
.warn { color: #f5c842; }
.ko   { color: #ef4444; }

.level-block {
    background: #0d0d14;
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    padding: 16px 20px;
    margin-top: 12px;
}

.level-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #1a1a2a;
    font-size: 0.9rem;
}

.level-row:last-child { border-bottom: none; }

.level-label { color: #6b7280; font-size: 0.8rem; }
.level-value { font-family: 'Space Mono', monospace; font-weight: 700; }
.tp1-val  { color: #22c55e; }
.tp2-val  { color: #16a34a; }
.sl-val   { color: #ef4444; }
.entry-val{ color: #f5c842; }

.score-bar {
    display: flex;
    gap: 6px;
    margin: 8px 0;
}

.score-pip {
    height: 8px;
    flex: 1;
    border-radius: 4px;
    background: #1e1e2e;
}

.score-pip.filled  { background: #f5c842; }
.score-pip.partial { background: #78490a; }

.ma-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 8px;
}

.ma-item {
    background: #0d0d14;
    border: 1px solid #1e1e2e;
    border-radius: 8px;
    padding: 10px;
    text-align: center;
}

.ma-label { font-size: 0.7rem; color: #5a5a6e; text-transform: uppercase; letter-spacing: 0.1em; }
.ma-value { font-family: 'Space Mono', monospace; font-size: 0.9rem; color: #e8e6df; font-weight: 700; }

.timestamp {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: #3a3a4e;
    letter-spacing: 0.1em;
}

.stat-card {
    background: #12121a;
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
}

.stat-label { font-size: 0.7rem; color: #5a5a6e; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }
.stat-value { font-family: 'Space Mono', monospace; font-size: 1.4rem; font-weight: 700; color: #f5c842; }

.divider { border: none; border-top: 1px solid #1e1e2e; margin: 16px 0; }

.telegram-sent {
    background: #0f2218;
    border: 1px solid #22c55e33;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 0.8rem;
    color: #22c55e;
    margin-top: 12px;
}

.error-block {
    background: #1f0f0f;
    border: 1px solid #ef444433;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.85rem;
    color: #ef4444;
}

/* Streamlit overrides */
div[data-testid="stVerticalBlock"] > div { gap: 0 !important; }
.stButton > button {
    background: #12121a;
    border: 1px solid #f5c842;
    color: #f5c842;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.05em;
    border-radius: 8px;
    padding: 8px 20px;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #f5c842;
    color: #0a0a0f;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = st.secrets.get("TELEGRAM_TOKEN",   "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

TV_SYMBOL   = "XAUUSD"
TV_EXCHANGE = "OANDA"
MA_PERIODS  = [50, 100, 200]
SL_PIPS     = 100
TP1_PIPS    = 100
TP2_PIPS    = 300
PIP_VALUE   = 0.10
REFRESH_SEC = 300

# ─────────────────────────────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────────────────────────────
def now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def send_telegram(message: str) -> bool:
    if not TELEGRAM_TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        return r.status_code == 200
    except:
        return False

# ─────────────────────────────────────────────────────────────────────
# DONNÉES
# ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_data():
    if not TV_AVAILABLE:
        st.error("tvdatafeed non disponible. Installez : pip install git+https://github.com/StreamAlpha/tvdatafeed.git")
        return None
    try:
        tv = TvDatafeed()
        df = tv.get_hist(
            symbol=TV_SYMBOL,
            exchange=TV_EXCHANGE,
            interval=Interval.in_1_hour,
            n_bars=300
        )
        if df is None or df.empty:
            return None
        df.index = pd.to_datetime(df.index)
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        return df
    except Exception as e:
        st.error(f"Erreur données : {e}")
        return None

# ─────────────────────────────────────────────────────────────────────
# INDICATEURS
# ─────────────────────────────────────────────────────────────────────
def compute_indicators(df):
    for p in MA_PERIODS:
        df[f"ma_{p}"] = df["close"].rolling(window=p).mean()
    return df

def detect_swing_points(df, window=5):
    df["is_swing_high"] = False
    df["is_swing_low"]  = False
    for i in range(window, len(df) - window):
        if df["high"].iloc[i] == df["high"].iloc[i-window:i+window+1].max():
            df.at[df.index[i], "is_swing_high"] = True
        if df["low"].iloc[i] == df["low"].iloc[i-window:i+window+1].min():
            df.at[df.index[i], "is_swing_low"] = True
    return df

# ─────────────────────────────────────────────────────────────────────
# ANALYSE
# ─────────────────────────────────────────────────────────────────────
def determine_sentiment(df):
    recent = df.tail(60)
    lows   = recent[recent["is_swing_low"] ]["low"].values
    highs  = recent[recent["is_swing_high"]]["high"].values
    if len(lows) < 2 or len(highs) < 2:
        return "NEUTRE"
    sl = np.polyfit(np.arange(len(lows)),  lows,  1)[0]
    sh = np.polyfit(np.arange(len(highs)), highs, 1)[0]
    if sl > 0 and sh > 0: return "HAUSSIER"
    if sl < 0 and sh < 0: return "BAISSIER"
    if sl > 0: return "HAUSSIER"
    if sh < 0: return "BAISSIER"
    return "NEUTRE"

def detect_phase(df, sentiment):
    recent   = df.tail(20)
    slope    = np.polyfit(np.arange(len(recent)), recent["close"].values, 1)[0]
    momentum = (recent["high"] - recent["low"]).mean() / (df["high"].tail(100) - df["low"].tail(100)).mean()
    if sentiment == "HAUSSIER":
        if slope > 0 and momentum > 1.2: return "IMPULSION"
        if slope < 0 or momentum <= 1.0: return "CORRECTION"
    elif sentiment == "BAISSIER":
        if slope < 0 and momentum > 1.2: return "IMPULSION"
        if slope > 0 or momentum <= 1.0: return "CORRECTION"
    return "TRANSITION"

def detect_config(df, sentiment):
    sl = df[df["is_swing_low"] ].tail(5)
    sh = df[df["is_swing_high"]].tail(5)
    c  = {"type": "AUCUNE", "zone": None, "desc": ""}
    if sentiment == "HAUSSIER" and len(sl) >= 2:
        if sl["low"].iloc[-1] > sl["low"].iloc[-2]:
            c = {"type": "ACHETEUSE", "zone": round(sl["low"].iloc[-1], 2),
                 "desc": f"Higher Low @ {sl['low'].iloc[-1]:.2f}"}
    elif sentiment == "BAISSIER" and len(sh) >= 2:
        if sh["high"].iloc[-1] < sh["high"].iloc[-2]:
            c = {"type": "VENDEUSE", "zone": round(sh["high"].iloc[-1], 2),
                 "desc": f"Lower High @ {sh['high'].iloc[-1]:.2f}"}
    return c

def analyze_ma(df, sentiment):
    price = df["close"].iloc[-1]
    conf  = 0
    for p in MA_PERIODS:
        v = df[f"ma_{p}"].iloc[-1]
        if pd.isna(v): continue
        if (price > v and sentiment == "HAUSSIER") or (price < v and sentiment == "BAISSIER"):
            conf += 1
    return {"confirmations": conf, "total": 3}

def find_psy_level(price, sentiment):
    base   = round(price / 50) * 50
    levels = [base + i * 50 for i in range(-4, 5)]
    if sentiment == "HAUSSIER":   cands = [l for l in levels if l < price]
    elif sentiment == "BAISSIER": cands = [l for l in levels if l > price]
    else:                          cands = levels
    if not cands:
        return {"niveau": None, "type": "", "dist": None, "entree": None}
    best  = min(cands, key=lambda l: abs(price - l))
    btype = "FORT (×100)" if best % 100 == 0 else "MODÉRÉ (×50)"
    dist  = round(abs(price - best) / PIP_VALUE, 1)
    marge = 10 * PIP_VALUE
    entree = round(best + marge, 2) if sentiment == "HAUSSIER" else round(best - marge, 2)
    return {"niveau": best, "type": btype, "dist": dist, "entree": entree}

def calc_levels(entry, direction):
    s  = SL_PIPS  * PIP_VALUE
    t1 = TP1_PIPS * PIP_VALUE
    t2 = TP2_PIPS * PIP_VALUE
    if direction == "BUY":
        return {"entree": round(entry,2), "sl": round(entry-s,2),
                "tp1": round(entry+t1,2), "tp2": round(entry+t2,2)}
    return {"entree": round(entry,2), "sl": round(entry+s,2),
            "tp1": round(entry-t1,2), "tp2": round(entry-t2,2)}

def full_analysis(df):
    price     = df["close"].iloc[-1]
    sentiment = determine_sentiment(df)
    phase     = detect_phase(df, sentiment)
    config    = detect_config(df, sentiment)
    ma        = analyze_ma(df, sentiment)
    psy       = find_psy_level(price, sentiment)

    score = 0
    items = []

    if sentiment != "NEUTRE":
        score += 1; items.append(("ok",   f"Sentiment {sentiment}"))
    else:
        items.append(("ko", "Sentiment NEUTRE — consolidation"))

    if phase == "CORRECTION":
        score += 1; items.append(("ok",   "Marché en CORRECTION"))
    elif phase == "TRANSITION":
        score += 0.5; items.append(("warn", "Marché en TRANSITION"))
    else:
        items.append(("ko", f"Marché en {phase} — attendre"))

    if config["type"] != "AUCUNE":
        score += 1; items.append(("ok",   f"Config {config['type']} — {config['desc']}"))
    else:
        items.append(("ko", "Pas de configuration valide"))

    if ma["confirmations"] >= 2:
        score += 1; items.append(("ok",   f"MA confirme ({ma['confirmations']}/3)"))
    elif ma["confirmations"] == 1:
        score += 0.5; items.append(("warn", "MA partielle (1/3)"))
    else:
        items.append(("ko", "MA ne confirme pas"))

    if psy["niveau"] and psy["dist"] and psy["dist"] <= 100:
        score += 1; items.append(("ok",   f"Niv. Psy {psy['type']} @ {psy['niveau']}"))
    elif psy["niveau"]:
        score += 0.5; items.append(("warn", f"Niv. Psy loin ({psy['dist']} pips)"))
    else:
        items.append(("ko", "Pas de niveau psychologique"))

    if score >= 4 and sentiment == "HAUSSIER" and config["type"] == "ACHETEUSE":
        signal, direction = "BUY", "BUY"
    elif score >= 4 and sentiment == "BAISSIER" and config["type"] == "VENDEUSE":
        signal, direction = "SELL", "SELL"
    elif score >= 3:
        signal    = "SURVEILLER"
        direction = "BUY" if sentiment == "HAUSSIER" else "SELL"
    else:
        signal, direction = "ATTENDRE", None

    levels = calc_levels(psy["entree"], direction) if direction and psy["entree"] else None

    return {
        "ts": now_str(), "price": round(price, 2),
        "sentiment": sentiment, "phase": phase,
        "config": config, "ma": ma, "psy": psy,
        "score": round(score, 1), "signal": signal,
        "direction": direction, "levels": levels, "items": items,
        "ma_50":  round(df["ma_50"].iloc[-1],  2) if not pd.isna(df["ma_50"].iloc[-1])  else None,
        "ma_100": round(df["ma_100"].iloc[-1], 2) if not pd.isna(df["ma_100"].iloc[-1]) else None,
        "ma_200": round(df["ma_200"].iloc[-1], 2) if not pd.isna(df["ma_200"].iloc[-1]) else None,
    }

def format_telegram(r):
    badge = {"BUY": "🟢 ACHAT CONFIRMÉ", "SELL": "🔴 VENTE CONFIRMÉE",
             "SURVEILLER": "🟡 À SURVEILLER", "ATTENDRE": "⚪ EN ATTENTE"}.get(r["signal"], "")
    msg = (f"🥇 <b>XAU/USD · GBP Man Strategy</b>\n"
           f"⏰ {r['ts']}\n💵 Prix : <b>{r['price']}</b>\n\n"
           f"📣 Signal : <b>{badge}</b>\n"
           f"🎯 Score : <b>{r['score']}/5</b>\n\n"
           f"<b>Confluences :</b>\n")
    icons = {"ok": "✅", "warn": "⚠️", "ko": "❌"}
    for typ, text in r["items"]:
        msg += f"{icons[typ]} {text}\n"
    if r["levels"] and r["signal"] in ["BUY", "SELL"]:
        n = r["levels"]
        msg += (f"\n📊 <b>Niveaux :</b>\n"
                f"🎯 Entrée : <b>{n['entree']}</b>\n"
                f"🛡️ SL : <b>{n['sl']}</b>\n"
                f"✅ TP1 : <b>{n['tp1']}</b>\n"
                f"🚀 TP2 : <b>{n['tp2']}</b>")
    return msg

# ─────────────────────────────────────────────────────────────────────
# INTERFACE STREAMLIT
# ─────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-header">🥇 XAU/USD</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">GBP Man Strategy · TradingView OANDA · H1</p>', unsafe_allow_html=True)

# Boutons de contrôle
col_btn1, col_btn2, col_spacer = st.columns([1, 1, 5])
with col_btn1:
    refresh = st.button("⟳ Actualiser")
with col_btn2:
    auto = st.toggle("Auto (5min)", value=False)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# Chargement des données
with st.spinner("Connexion TradingView · OANDA..."):
    df = get_data()

if df is None:
    st.markdown('<div class="error-block">Impossible de charger les données TradingView. Vérifiez la connexion.</div>', unsafe_allow_html=True)
    st.stop()

df = compute_indicators(df)
df = detect_swing_points(df)
r  = full_analysis(df)

# ── LIGNE 1 : PRIX + SIGNAL + SCORE ──────────────────────────────────
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    card_class = {"BUY": "signal-buy", "SELL": "signal-sell",
                  "SURVEILLER": "signal-watch", "ATTENDRE": "signal-wait"}.get(r["signal"], "signal-wait")
    badge_class = {"BUY": "badge-buy", "SELL": "badge-sell",
                   "SURVEILLER": "badge-watch", "ATTENDRE": "badge-wait"}.get(r["signal"], "badge-wait")
    badge_text  = {"BUY": "▲ ACHAT", "SELL": "▼ VENTE",
                   "SURVEILLER": "◉ SURVEILLER", "ATTENDRE": "○ ATTENDRE"}.get(r["signal"], "")
    st.markdown(f"""
    <div class="signal-card {card_class}">
        <div class="timestamp">{r['ts']}</div>
        <div class="price-display">{r['price']}</div>
        <div style="margin-top:10px;">
            <span class="signal-badge {badge_class}">{badge_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">Score</div>
        <div class="stat-value">{r['score']}/5</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">Sentiment</div>
        <div class="stat-value" style="font-size:1rem;color:{'#22c55e' if r['sentiment']=='HAUSSIER' else '#ef4444' if r['sentiment']=='BAISSIER' else '#6b7280'}">{r['sentiment']}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">Phase</div>
        <div class="stat-value" style="font-size:1rem;color:{'#22c55e' if r['phase']=='CORRECTION' else '#f5c842' if r['phase']=='TRANSITION' else '#ef4444'}">{r['phase']}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── LIGNE 2 : CONFLUENCES + NIVEAUX ─────────────────────────────────
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("**Confluences**")
    icons_map = {"ok": ("✅", "#22c55e"), "warn": ("⚠️", "#f5c842"), "ko": ("❌", "#ef4444")}
    confluence_html = ""
    for typ, text in r["items"]:
        icon, color = icons_map[typ]
        confluence_html += f'<div class="confluence-item"><span class="{typ}">{icon}</span><span style="color:{color if typ!="ok" else "#e8e6df"}">{text}</span></div>'

    # Score bar
    filled  = int(r["score"])
    partial = 1 if r["score"] % 1 >= 0.5 else 0
    empty   = 5 - filled - partial
    pips_html = ""
    for _ in range(filled):  pips_html += '<div class="score-pip filled"></div>'
    for _ in range(partial): pips_html += '<div class="score-pip partial"></div>'
    for _ in range(empty):   pips_html += '<div class="score-pip"></div>'

    st.markdown(f"""
    <div class="signal-card">
        <div class="score-bar">{pips_html}</div>
        {confluence_html}
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.markdown("**Niveaux d'entrée**")
    if r["levels"] and r["signal"] in ["BUY", "SELL"]:
        n = r["levels"]
        dir_color = "#22c55e" if r["direction"] == "BUY" else "#ef4444"
        dir_label = "📈 ORDRE BUY LIMITE" if r["direction"] == "BUY" else "📉 ORDRE SELL LIMITE"
        st.markdown(f"""
        <div class="signal-card">
            <div style="color:{dir_color};font-weight:600;margin-bottom:12px;font-size:0.9rem;">{dir_label}</div>
            <div class="level-block">
                <div class="level-row">
                    <span class="level-label">🎯 Entrée</span>
                    <span class="level-value entry-val">{n['entree']}</span>
                </div>
                <div class="level-row">
                    <span class="level-label">🛡️ Stop Loss</span>
                    <span class="level-value sl-val">{n['sl']} <span style="font-size:0.7rem;color:#6b7280">({SL_PIPS} pips)</span></span>
                </div>
                <div class="level-row">
                    <span class="level-label">✅ TP1</span>
                    <span class="level-value tp1-val">{n['tp1']} <span style="font-size:0.7rem;color:#6b7280">({TP1_PIPS} pips · 1:1)</span></span>
                </div>
                <div class="level-row">
                    <span class="level-label">🚀 TP2</span>
                    <span class="level-value tp2-val">{n['tp2']} <span style="font-size:0.7rem;color:#6b7280">({TP2_PIPS} pips · 3:1)</span></span>
                </div>
            </div>
            <div style="font-size:0.75rem;color:#5a5a6e;margin-top:10px;font-style:italic;">
                Fermer 50% au TP1 · Laisser courir le reste
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        watch_text = "Tous les éléments ne sont pas encore alignés. Continuez à surveiller." if r["signal"] == "SURVEILLER" else "Score insuffisant. Attendez la prochaine analyse."
        st.markdown(f"""
        <div class="signal-card signal-wait" style="text-align:center;padding:40px 20px;">
            <div style="font-size:2rem;margin-bottom:10px;">{"👁️" if r["signal"]=="SURVEILLER" else "⏳"}</div>
            <div style="color:#6b7280;font-size:0.9rem;">{watch_text}</div>
        </div>
        """, unsafe_allow_html=True)

    # Moyennes mobiles
    st.markdown(f"""
    <div style="margin-top:16px;">
    <div style="font-size:0.75rem;color:#5a5a6e;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">Moyennes Mobiles</div>
    <div class="ma-grid">
        <div class="ma-item"><div class="ma-label">MA 50</div><div class="ma-value">{r['ma_50'] or '—'}</div></div>
        <div class="ma-item"><div class="ma-label">MA 100</div><div class="ma-value">{r['ma_100'] or '—'}</div></div>
        <div class="ma-item"><div class="ma-label">MA 200</div><div class="ma-value">{r['ma_200'] or '—'}</div></div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # Niveau psychologique
    if r["psy"]["niveau"]:
        st.markdown(f"""
        <div style="margin-top:12px;background:#0d0d14;border:1px solid #1e1e2e;border-radius:8px;padding:12px 16px;">
            <div style="font-size:0.7rem;color:#5a5a6e;text-transform:uppercase;letter-spacing:0.1em;">Niveau Psychologique</div>
            <div style="font-family:'Space Mono',monospace;font-size:1.1rem;font-weight:700;color:#f5c842;margin-top:4px;">{r['psy']['niveau']}</div>
            <div style="font-size:0.75rem;color:#6b7280;">{r['psy']['type']} · {r['psy']['dist']} pips</div>
        </div>
        """, unsafe_allow_html=True)

# ── TELEGRAM ─────────────────────────────────────────────────────────
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
col_tg1, col_tg2 = st.columns([1, 3])
with col_tg1:
    if st.button("📲 Envoyer sur Telegram"):
        msg  = format_telegram(r)
        sent = send_telegram(msg)
        if sent:
            st.markdown('<div class="telegram-sent">✅ Signal envoyé sur Telegram !</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-block">❌ Erreur Telegram — vérifiez le token dans Secrets.</div>', unsafe_allow_html=True)

# ── DERNIER TIMESTAMP ────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:24px;text-align:center;font-size:0.7rem;color:#3a3a4e;font-family:'Space Mono',monospace;">
    Dernière analyse : {r['ts']} · Source : TradingView OANDA H1 · GBP Man Strategy
</div>
""", unsafe_allow_html=True)

# ── AUTO-REFRESH ─────────────────────────────────────────────────────
if auto:
    time.sleep(REFRESH_SEC)
    st.rerun()