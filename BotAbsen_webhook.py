
from flask import Flask, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

app = Flask(__name__)

# --- Konfigurasi ---
USERNAMES = {
    7211650376: "2015276831",
    5018276186: "2015021438",
    1313654563: "2015014805",
    1826365104: "2015291142",
    5162021253: "2015387831"
}
PASSWORD = "1234"
BOT_TOKEN = "8029031638:AAHHrCAbZZWD1eG3Nh9haBDGiIBT20D0B08"
URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# --- Utilitas ---
def escape_markdown(text):
    return re.sub(r'([*_`\[\]()])', r'\\\1', text)

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except:
        return None

def login(username):
    session = requests.Session()
    ip = get_public_ip()
    if not ip:
        return None
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "username": username,
        "password": PASSWORD,
        "ipaddr": ip
    }
    try:
        res = session.post("https://bicmdo.lalskomputer.my.id/idm_v2/req_masuk", data=payload, headers=headers, timeout=10)
        if "Logout" in res.text or "Keluar" in res.text:
            return session
    except:
        return None
    return None

def get_absensi_html(session):
    try:
        res = session.get("https://bicmdo.lalskomputer.my.id/idm_v2/Api/get_absen", timeout=10)
        return res.text
    except:
        return None

def parse_absen(html, filter_today=False):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "detailAbsen"})
    if not table:
        return []

    rows = table.find_all("tr")[1:]
    now = datetime.now()
    bulan_ini = now.strftime("%B %Y")
    today = now.strftime("%d %B %Y")
    data = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 7:
            tanggal = cols[3].get_text(strip=True)
            nama = cols[2].get_text(strip=True)
            status = cols[6].get_text(strip=True)
            if filter_today and tanggal == today:
                return [(tanggal, nama, status)]
            elif not filter_today and bulan_ini in tanggal:
                data.append((tanggal, nama, status))
    return data

def format_absensi(data, label="📋 *Rekap Absensi Bulan Ini*"):
    if not data:
        return f"{label}\nTidak ada data."
    lines = [label, ""]
    for i, (tgl, nama, status) in enumerate(data, 1):
        emoji = "❌" if "Mangkir" in status else "✅"
        lines.append(f"{i}. [{tgl}] {nama} - {status} {emoji}")
    return "\n".join(lines)

def send_message(chat_id, text):
    text = escape_markdown(text)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(URL + "sendMessage", data=payload, timeout=10)
    except Exception as e:
        print("[!] Gagal kirim pesan:", e)

def handle_command(chat_id, text):
    if text.lower() in ["/start", "/info"]:
        info = (
            "🚬 Selamat datang di Bot Absensi! 🚬\n"
            "\n"
            "ADA ROKOK PA NN???\n"
            "\n"
            "Gunakan perintah berikut:\n"
            "/absen - Melihat absensi hari ini\n"
            "/rekap - Melihat rekap absensi bulan ini\n"
            "/about atau /creator - Info pembuat bot\n"
            "\n"
            "Rekapan Mingguan Setiap Hari Sabtu 17:00"
        )
        send_message(chat_id, info)
        return
    if text.lower() in ["/about", "/creator"]:
        send_message(chat_id, "🤖 Bot Absensi dibuat oleh Brando.")
        return

    username = USERNAMES.get(chat_id)
    if not username:
        send_message(chat_id, "⚠️ Chat ID Anda belum terdaftar.")
        return

    session = login(username)
    if not session:
        send_message(chat_id, f"⚠️ Gagal login ke sistem absensi dengan username: {username}")
        return

    html = get_absensi_html(session)
    if not html:
        send_message(chat_id, "⚠️ Gagal mengambil data absensi.")
        return

    if text == "/absen":
        data = parse_absen(html, filter_today=True)
        msg = format_absensi(data, "📅 *Absensi Hari Ini*")
        send_message(chat_id, msg)
    elif text == "/rekap":
        data = parse_absen(html, filter_today=False)
        msg = format_absensi(data, "📋 *Rekap Absensi Bulan Ini*")
        send_message(chat_id, msg)
    else:
        send_message(chat_id, "Perintah tidak dikenal. Gunakan /absen atau /rekap.")

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = request.get_json()
        if "message" in update:
            chat_id = update["message"]["chat"]["id"]
            text = update["message"].get("text", "")
            if chat_id and text:
                handle_command(chat_id, text)
        return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
