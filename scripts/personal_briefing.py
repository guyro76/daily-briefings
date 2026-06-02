"""
personal-briefing - סדר יום אישי
מזג אוויר + מידע יומי בעברית
"""

import json
import smtplib
import sys
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

# === CONFIG ===
TELEGRAM_TOKEN = "8556094142:AAF_LPLMUjOvUfLmTdLEe2_6RUTfigFs4Z4"
TELEGRAM_CHAT_ID = "8526599959"
WA_URL = "https://7107.api.greenapi.com/waInstance7107593091/sendMessage/c2ee48c174284d658f942d78126eea979cf3adbd8a33491f8d"
WA_CHAT_ID = "972546585113@c.us"
GMAIL_USER = "guyro76@gmail.com"
GMAIL_PASS = "yscqggafoomwrais"

def get_weather(city_en, city_he):
    """שולף מזג אוויר מ-wttr.in ללא API key"""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city_en)}?format=j1&lang=he"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        current = data["current_condition"][0]
        today = data["weather"][0]
        
        temp_c = current["temp_C"]
        feels = current["FeelsLikeC"]
        desc = current.get("lang_he", [{}])[0].get("value", current["weatherDesc"][0]["value"])
        min_t = today["mintempC"]
        max_t = today["maxtempC"]
        
        return f"{city_he}: {min_t}–{max_t}°C, {desc}"
    except Exception as e:
        print(f"שגיאת מזג אוויר {city_he}: {e}")
        return f"{city_he}: מזג האוויר אינו זמין כרגע"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": message}).encode()
    req = urllib.request.Request(url, data=data)
    res = json.loads(urllib.request.urlopen(req, timeout=15).read())
    print(f"Telegram: ok={res.get('ok')}")

def send_whatsapp(message):
    data = json.dumps({"chatId": WA_CHAT_ID, "message": message}).encode()
    req = urllib.request.Request(WA_URL, data=data, headers={"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=15).read())
    print(f"WhatsApp: {res.get('idMessage', res)}")

def send_email(subject, html_body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = GMAIL_USER
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
    print("אימייל נשלח בהצלחה")

def main():
    il = pytz.timezone('Asia/Jerusalem')
    now = datetime.now(il)
    is_morning = now.hour < 12

    months = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
    days = ["יום שני","יום שלישי","יום רביעי","יום חמישי","יום שישי","יום שבת","יום ראשון"]
    date_he = f"{now.day} {months[now.month-1]} {now.year}"
    date_dmy = now.strftime("%d.%m.%Y")
    day_name = days[now.weekday()]
    greeting = "בוקר טוב גיא!" if is_morning else "ערב טוב גיא!"
    session = "בוקר" if is_morning else "ערב"
    footer = "עדכון הבא ב-18:00" if is_morning else "עדכון הבא ב-07:00"
    emoji = "\U0001f305" if is_morning else "\U0001f306"

    # מזג אוויר
    weather_harish = get_weather("Harish, Israel", "חריש")
    weather_ta = get_weather("Tel Aviv, Israel", "תל אביב")

    # טיפ יומי בעברית
    tips = [
        "מכינים רשימת משימות? התחל עם הדבר הכי קשה — שאר היום יהיה קל יותר",
        "שתה כוס מים לפני הקפה הבוקר — הגוף מתייבש בלילה",
        "10 דקות הליכה בחוץ שוות שעת פגישה מבחינת פרודוקטיביות",
        "שלח הודעת תודה לאדם אחד היום — זה מחזיר",
        "גבה קבצים חשובים — אם לא עשית את זה השבוע, עשה את זה עכשיו",
        "יום שישי טוב לסיום משימות ולא להתחלת חדשות",
        "השבת היא להטעין, לא לדאוג — שמור על זה",
    ]
    tip_text = tips[now.weekday()]

    plain = f"""{emoji} {greeting}
{day_name} | {date_he}

\U0001f324 מזג אוויר:
{weather_harish}
{weather_ta}

\U0001f4cb סדר יום:
(סנכרון לוח שנה — בקרוב)

\U0001f4a1 טיפ היום:
{tip_text}

{footer}"""

    # HTML
    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#eef2f7;font-family:'Heebo',Arial,sans-serif;direction:rtl;text-align:right}}
.wrap{{padding:20px 12px}}
.card{{max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(21,101,192,.15)}}
.hdr{{background:linear-gradient(135deg,#0d2d5e,#1565c0,#1976d2);padding:20px 24px 18px}}
.hdr-date{{font-size:12px;font-weight:700;color:#90caf9;margin-bottom:6px}}
.hdr-title{{font-size:24px;font-weight:900;color:#fff;margin-bottom:4px}}
.hdr-sub{{font-size:14px;font-weight:700;color:#bbdefb}}
.stripe{{height:4px;background:linear-gradient(90deg,#0d47a1,#1976d2,#42a5f5,#1976d2,#0d47a1)}}
.sec{{padding:16px 24px 12px;border-bottom:1px solid #e8f4fd}}
.sec-title{{font-size:16px;font-weight:900;color:#0d2d5e;margin-bottom:12px}}
.row{{margin-bottom:8px;background:#f4f9ff;border-radius:10px;border-right:4px solid #1976d2;padding:11px 14px;font-size:15px;font-weight:700;color:#0d1b2a;line-height:1.6}}
.tip-box{{margin:10px 24px 20px;background:#0d2d5e;border-radius:12px;padding:16px 18px}}
.tip-lbl{{font-size:11px;font-weight:900;color:#90caf9;letter-spacing:2px;margin-bottom:8px}}
.tip-txt{{font-size:15px;color:#fff;line-height:1.65;font-weight:700}}
.ftr{{background:#f7f9fc;padding:14px 24px;text-align:center;font-size:12px;font-weight:700;color:#1565c0;border-top:2px solid #e3f2fd}}
</style>
</head>
<body><div class="wrap"><div class="card">
<div class="hdr">
  <div class="hdr-date">\U0001f4c5 {date_dmy} | {date_he} | {day_name}</div>
  <div class="hdr-title">{emoji} {greeting}</div>
  <div class="hdr-sub">\U0001f4cb סדר היום האישי שלך</div>
</div>
<div class="stripe"></div>
<div class="sec">
  <div class="sec-title">\U0001f324 מזג אוויר</div>
  <div class="row">{weather_harish}</div>
  <div class="row">{weather_ta}</div>
</div>
<div class="sec">
  <div class="sec-title">\U0001f4c5 סדר יום היום</div>
  <div class="row" style="color:#888;font-style:italic">סנכרון לוח שנה — בקרוב</div>
</div>
<div class="tip-box">
  <div class="tip-lbl">\U0001f4a1 טיפ {session}</div>
  <div class="tip-txt">{tip_text}</div>
</div>
<div class="ftr">גיא רוזנברג ©2026 | {footer}</div>
</div></div></body></html>"""

    subject = f"{emoji} {greeting} — סדר יום {date_dmy}"
    send_telegram(plain)
    try:
        send_whatsapp(plain)
    except Exception as e:
        print(f"שגיאת WhatsApp: {e}")
    try:
        send_email(subject, html)
    except Exception as e:
        print(f"שגיאת אימייל: {e}")
    print(f"סיום — {date_he} {session}")

if __name__ == "__main__":
    main()
