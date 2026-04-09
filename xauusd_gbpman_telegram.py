"""
╔══════════════════════════════════════════════════════════════════════╗
║       XAU/USD — STRATÉGIE GBP MAN                                   ║
║       Source : TradingView / OANDA (données Forex réelles)          ║
║       Alertes : Telegram (messages redesignés)                      ║
║       Serveur : PythonAnywhere                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

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
    raise ImportError("pip install ta")


# ─────────────────────────────────────────────────────────────────────
# ⚙️  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = "METS_TON_TOKEN_ICI"
TELEGRAM_CHAT_ID = "1929037755"

# TradingView
TV_USERNAME  = ""           # Laisser vide = connexion anonyme
TV_PASSWORD  = ""

# Paire Gold OANDA sur TradingView
TV_SYMBOL    = "XAUUSD"
TV_EXCHANGE  = "OANDA"
TV_INTERVAL  = Interval.in_1_hour if TV_AVAILABLE else None
N_BARS       = 300

# Paramètres stratégie GBP Man
MA_PERIODS   = [50, 100, 200]
SL_PIPS      = 100
TP1_PIPS     = 100
TP2_PIPS     = 300
PIP_VALUE    = 0.10          # 1 pip = 0.10 sur XAU/USD

# Analyse toutes les X secondes
INTERVAL_SEC = 300           # 5 minutes


# ─────────────────────────────────────────────────────────────────────
# 📡 CONNEXION TRADINGVIEW
# ─────────────────────────────────────────────────────────────────────
def connect_tv():
    if not TV_AVAILABLE:
        raise ImportError("tvdatafeed non installé : pip install git+https://github.com/StreamAlpha/tvdatafeed.git")
    if TV_USERNAME and TV_PASSWORD:
        tv = TvDatafeed(username=TV_USERNAME, password=TV_PASSWORD)
    else:
        tv = TvDatafeed()
    return tv


def get_data(tv) -> pd.DataFrame:
    print(f"📡 [{now()}] Chargement {TV_SYMBOL} / {TV_EXCHANGE} (TradingView)...")
    df = tv.get_hist(
        symbol   = TV_SYMBOL,
        exchange = TV_EXCHANGE,
        interval = TV_INTERVAL,
        n_bars   = N_BARS
    )
    if df is None or df.empty:
        raise ValueError(f"Aucune donnée reçue pour {TV_SYMBOL} sur {TV_EXCHANGE}")
    df.index   = pd.to_datetime(df.index)
    df.columns = [c.lower() for c in df.columns]
    df         = df[["open", "high", "low", "close", "volume"]].dropna()
    print(f"✅ {len(df)} bougies chargées — Dernière : {df.index[-1]}")
    return df


# ─────────────────────────────────────────────────────────────────────
# 🛠️  UTILITAIRES
# ─────────────────────────────────────────────────────────────────────
def now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


# ─────────────────────────────────────────────────────────────────────
# 📊 INDICATEURS
# ─────────────────────────────────────────────────────────────────────
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    for p in MA_PERIODS:
        df[f"ma_{p}"] = df["close"].rolling(window=p).mean()
    return df


def detect_swing_points(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    df["is_swing_high"] = False
    df["is_swing_low"]  = False
    for i in range(window, len(df) - window):
        if df["high"].iloc[i] == df["high"].iloc[i-window:i+window+1].max():
            df.at[df.index[i], "is_swing_high"] = True
        if df["low"].iloc[i] == df["low"].iloc[i-window:i+window+1].min():
            df.at[df.index[i], "is_swing_low"] = True
    return df


# ─────────────────────────────────────────────────────────────────────
# 1️⃣  SENTIMENT DOMINANT
# ─────────────────────────────────────────────────────────────────────
def determine_sentiment(df: pd.DataFrame) -> str:
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


# ─────────────────────────────────────────────────────────────────────
# 2️⃣  REPÈRE DU MARCHÉ
# ─────────────────────────────────────────────────────────────────────
def detect_phase(df: pd.DataFrame, sentiment: str) -> str:
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


# ─────────────────────────────────────────────────────────────────────
# 3️⃣  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────
def detect_config(df: pd.DataFrame, sentiment: str) -> dict:
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


# ─────────────────────────────────────────────────────────────────────
# 4️⃣  MOYENNE MOBILE
# ─────────────────────────────────────────────────────────────────────
def analyze_ma(df: pd.DataFrame, sentiment: str) -> dict:
    price = df["close"].iloc[-1]
    conf  = 0
    for p in MA_PERIODS:
        v = df[f"ma_{p}"].iloc[-1]
        if pd.isna(v): continue
        if (price > v and sentiment == "HAUSSIER") or (price < v and sentiment == "BAISSIER"):
            conf += 1
    return {"confirmations": conf, "total": 3}


# ─────────────────────────────────────────────────────────────────────
# 5️⃣  NIVEAU PSYCHOLOGIQUE
# ─────────────────────────────────────────────────────────────────────
def find_psy_level(price: float, sentiment: str) -> dict:
    base   = round(price / 50) * 50
    levels = [base + i * 50 for i in range(-4, 5)]
    if sentiment == "HAUSSIER":
        cands = [l for l in levels if l < price]
    elif sentiment == "BAISSIER":
        cands = [l for l in levels if l > price]
    else:
        cands = levels
    if not cands:
        return {"niveau": None, "type": "", "dist": None, "entree": None}
    best  = min(cands, key=lambda l: abs(price - l))
    btype = "FORT (×100)" if best % 100 == 0 else "MODÉRÉ (×50)"
    dist  = round(abs(price - best) / PIP_VALUE, 1)
    marge = 10 * PIP_VALUE
    entree = round(best + marge, 2) if sentiment == "HAUSSIER" else round(best - marge, 2)
    return {"niveau": best, "type": btype, "dist": dist, "entree": entree}


# ─────────────────────────────────────────────────────────────────────
# 💰 NIVEAUX SL / TP
# ─────────────────────────────────────────────────────────────────────
def calc_levels(entry: float, direction: str) -> dict:
    s = SL_PIPS  * PIP_VALUE
    t1= TP1_PIPS * PIP_VALUE
    t2= TP2_PIPS * PIP_VALUE
    if direction == "BUY":
        return {"entree": round(entry,2), "sl": round(entry-s,2),
                "tp1": round(entry+t1,2), "tp2": round(entry+t2,2)}
    return {"entree": round(entry,2), "sl": round(entry+s,2),
            "tp1": round(entry-t1,2), "tp2": round(entry-t2,2)}


# ─────────────────────────────────────────────────────────────────────
# 🧠 ANALYSE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────
def analyze(df: pd.DataFrame) -> dict:
    price     = df["close"].iloc[-1]
    sentiment = determine_sentiment(df)
    phase     = detect_phase(df, sentiment)
    config    = detect_config(df, sentiment)
    ma        = analyze_ma(df, sentiment)
    psy       = find_psy_level(price, sentiment)

    score = 0
    items = []

    # 1 — Sentiment
    if sentiment != "NEUTRE":
        score += 1; items.append(("✅", f"Sentiment {sentiment}"))
    else:
        items.append(("❌", "Sentiment NEUTRE — consolidation"))

    # 2 — Phase
    if phase == "CORRECTION":
        score += 1; items.append(("✅", "Marché en CORRECTION"))
    elif phase == "TRANSITION":
        score += 0.5; items.append(("⚠️", "Marché en TRANSITION"))
    else:
        items.append(("❌", f"Marché en {phase} — attendre"))

    # 3 — Configuration
    if config["type"] != "AUCUNE":
        score += 1; items.append(("✅", f"Config {config['type']} — {config['desc']}"))
    else:
        items.append(("❌", "Pas de configuration valide"))

    # 4 — MA
    if ma["confirmations"] >= 2:
        score += 1; items.append(("✅", f"MA confirme ({ma['confirmations']}/3)"))
    elif ma["confirmations"] == 1:
        score += 0.5; items.append(("⚠️", "MA partielle (1/3)"))
    else:
        items.append(("❌", "MA ne confirme pas"))

    # 5 — Niveau psy
    if psy["niveau"] and psy["dist"] and psy["dist"] <= 100:
        score += 1; items.append(("✅", f"Niv. Psy {psy['type']} @ {psy['niveau']}"))
    elif psy["niveau"]:
        score += 0.5; items.append(("⚠️", f"Niv. Psy loin ({psy['dist']} pips)"))
    else:
        items.append(("❌", "Pas de niveau psychologique"))

    # Signal
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
        "ts"       : now(),
        "price"    : round(price, 2),
        "sentiment": sentiment,
        "phase"    : phase,
        "config"   : config,
        "ma"       : ma,
        "psy"      : psy,
        "score"    : round(score, 1),
        "signal"   : signal,
        "direction": direction,
        "levels"   : levels,
        "items"    : items,
        "ma_50"    : round(df["ma_50"].iloc[-1],  2) if not pd.isna(df["ma_50"].iloc[-1])  else None,
        "ma_100"   : round(df["ma_100"].iloc[-1], 2) if not pd.isna(df["ma_100"].iloc[-1]) else None,
        "ma_200"   : round(df["ma_200"].iloc[-1], 2) if not pd.isna(df["ma_200"].iloc[-1]) else None,
    }


# ─────────────────────────────────────────────────────────────────────
# 🎨 FORMAT TELEGRAM — DESIGN ATTRACTIF
# ─────────────────────────────────────────────────────────────────────
def format_message(r: dict) -> str:

    # Badges signal
    badge = {
        "BUY"       : "🟢 ACHAT CONFIRMÉ",
        "SELL"      : "🔴 VENTE CONFIRMÉE",
        "SURVEILLER": "🟡 ZONE À SURVEILLER",
        "ATTENDRE"  : "⚪ EN ATTENTE",
    }.get(r["signal"], "⚪")

    # Barre de score visuelle
    filled  = int(r["score"])
    partial = 1 if r["score"] % 1 >= 0.5 else 0
    empty   = 5 - filled - partial
    bar     = "█" * filled + "▓" * partial + "░" * empty

    # Header
    msg = f"""
╔══════════════════════════════╗
     🥇  <b>XAU / USD — GOLD</b>
     📡  TradingView · OANDA · H1
╚══════════════════════════════╝

⏰  <b>{r['ts']}</b>
💵  Prix actuel :  <b>{r['price']}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊  <b>ANALYSE — 5 CONFLUENCES</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    for icon, text in r["items"]:
        msg += f"{icon}  {text}\n"

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯  Score  :  <b>{bar}  {r['score']}/5</b>
📣  Signal :  <b>{badge}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # Bloc entrée si signal actionnable
    if r["levels"] and r["signal"] in ["BUY", "SELL"]:
        n   = r["levels"]
        dir_icon = "📈" if r["direction"] == "BUY" else "📉"
        msg += f"""
{dir_icon}  <b>ORDRE LIMITE</b>

┌─────────────────────────────
│  🎯  Entrée   →   <b>{n['entree']}</b>
│  🛡️   Stop Loss →   <b>{n['sl']}</b>  <i>({SL_PIPS} pips)</i>
├─────────────────────────────
│  ✅  TP1  →  <b>{n['tp1']}</b>  <i>({TP1_PIPS} pips · 1:1)</i>
│  🚀  TP2  →  <b>{n['tp2']}</b>  <i>({TP2_PIPS} pips · 3:1)</i>
└─────────────────────────────

💡  <i>Fermer 50% de la position au TP1
    Conserver le reste pour le swing</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # Bloc surveiller
    elif r["signal"] == "SURVEILLER":
        msg += f"""
👁️  <b>ZONE À SURVEILLER</b>
<i>Tous les éléments ne sont pas encore
alignés. Surveiller la confirmation
du {r['direction']} sur le prochain signal.</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # Moyennes mobiles
    msg += f"""
📉  <b>Moyennes Mobiles</b>
  MA  50  →  {r['ma_50']}
  MA 100  →  {r['ma_100']}
  MA 200  →  {r['ma_200']}

🔢  <b>Niv. Psychologique</b>
  {r['psy']['niveau']}  <i>({r['psy']['type']} · {r['psy']['dist']} pips)</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>🤖 GBP Man Strategy · Auto-Signal</i>
"""
    return msg.strip()


def format_startup_message() -> str:
    return f"""
╔══════════════════════════════╗
     🥇  <b>XAU / USD SIGNAL BOT</b>
     🤖  <b>Stratégie GBP Man</b>
╚══════════════════════════════╝

✅  Bot démarré avec succès !
📡  Source  :  TradingView / OANDA
⏱️   Timeframe :  H1
🔄  Analyse  :  toutes les 5 minutes

<b>Les 5 confluences :</b>
1️⃣  Sentiment dominant
2️⃣  Repère du marché
3️⃣  Configuration prix
4️⃣  Moyennes mobiles (50/100/200)
5️⃣  Niveau psychologique

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>En attente du premier signal... 🎯</i>
"""


# ─────────────────────────────────────────────────────────────────────
# 📲 ENVOI TELEGRAM
# ─────────────────────────────────────────────────────────────────────
def send_telegram(message: str) -> bool:
    if TELEGRAM_TOKEN == "METS_TON_TOKEN_ICI":
        print("⚠️  Configure ton TOKEN Telegram !")
        return False
    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, data={
            "chat_id"   : TELEGRAM_CHAT_ID,
            "text"      : message,
            "parse_mode": "HTML"
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"⚠️  Telegram erreur : {e}")
        return False


# ─────────────────────────────────────────────────────────────────────
# 💾 SAUVEGARDE CSV
# ─────────────────────────────────────────────────────────────────────
def save_csv(r: dict, path: str = "signals_xauusd.csv"):
    row = {
        "date"        : r["ts"],
        "prix"        : r["price"],
        "sentiment"   : r["sentiment"],
        "phase"       : r["phase"],
        "config"      : r["config"]["type"],
        "ma_conf"     : r["ma"]["confirmations"],
        "niv_psy"     : r["psy"]["niveau"],
        "score"       : r["score"],
        "signal"      : r["signal"],
        "entree"      : r["levels"]["entree"] if r["levels"] else "",
        "sl"          : r["levels"]["sl"]     if r["levels"] else "",
        "tp1"         : r["levels"]["tp1"]    if r["levels"] else "",
        "tp2"         : r["levels"]["tp2"]    if r["levels"] else "",
        "ma_50"       : r["ma_50"],
        "ma_100"      : r["ma_100"],
        "ma_200"      : r["ma_200"],
    }
    pd.DataFrame([row]).to_csv(path, mode="a", header=not os.path.exists(path), index=False)


# ─────────────────────────────────────────────────────────────────────
# 🖥️  AFFICHAGE CONSOLE
# ─────────────────────────────────────────────────────────────────────
def print_console(r: dict):
    print(f"\n{'═'*52}")
    print(f"  🥇 XAU/USD  ·  {r['ts']}  ·  {r['price']}")
    print(f"  Sentiment : {r['sentiment']}  |  Phase : {r['phase']}")
    print(f"  Score : {r['score']}/5  |  Signal : {r['signal']}")
    for icon, text in r["items"]:
        print(f"  {icon} {text}")
    if r["levels"]:
        n = r["levels"]
        print(f"  → Entrée {n['entree']} | SL {n['sl']} | TP1 {n['tp1']} | TP2 {n['tp2']}")
    print(f"{'═'*52}\n")


# ─────────────────────────────────────────────────────────────────────
# 🚀 BOUCLE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────
def run():
    print("\n" + "═"*52)
    print("  🥇 XAU/USD GBP MAN STRATEGY")
    print("  TradingView OANDA · Telegram · PythonAnywhere")
    print("="*52 + "\n")

    # Connexion TradingView
    tv = connect_tv()
    print("✅ TradingView connecté\n")

    # Message de démarrage Telegram
    send_telegram(format_startup_message())
    print("✅ Message démarrage envoyé sur Telegram\n")

    last_signal = None

    while True:
        try:
            df = get_data(tv)
            df = compute_indicators(df)
            df = detect_swing_points(df)
            r  = analyze(df)

            print_console(r)
            save_csv(r)

            # Envoyer sur Telegram si signal important
            if r["signal"] in ["BUY", "SELL"]:
                if r["signal"] != last_signal:
                    send_telegram(format_message(r))
                    print(f"  📲 Signal {r['signal']} envoyé sur Telegram !\n")
                    last_signal = r["signal"]
            elif r["signal"] == "SURVEILLER":
                send_telegram(format_message(r))
                print("  📲 Alerte SURVEILLER envoyée\n")

        except Exception as e:
            print(f"\n⚠️  Erreur : {e}")
            import traceback
            traceback.print_exc()
            send_telegram(f"⚠️ <b>Erreur bot XAU/USD</b>\n<code>{str(e)}</code>")

        print(f"⏳ Prochaine analyse dans {INTERVAL_SEC // 60} min...\n")
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    run()