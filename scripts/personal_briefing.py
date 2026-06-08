"""Personal Briefing — Weather + Calendar (iCal) + Daily Tip"""
import sys, os, json, smtplib, re
import urllib.request, urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date, timedelta
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from utils import load_cache, save_cache, current_session, mark_sent, is_seen_morning

TELEGRAM_TOKEN = "8556094142:AAF_LPLMUjOvUfLmTdLEe2_6RUTfigFs4Z4"
TELEGRAM_CHAT_ID = "8526599959"
WA_URL = "https://7107.api.greenapi.com/waInstance7107593091/sendMessage/c2ee48c174284d658f942d78126eea979cf3adbd8a33491f8d"
WA_CHAT_ID = "972546585113@c.us"
GMAIL_USER = "guyro76@gmail.com"
GMAIL_PASS = "yscqggafoomwrais"

def get_weather(city_en, city_he):
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city_en)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        cur  = data["current_condition"][0]
        tod  = data["weather"][0]
        desc_list = cur.get("lang_he", [{}])
        desc = desc_list[0].get("value", cur["weatherDesc"][0]["value"]) if desc_list else cur["weatherDesc"][0]["value"]
        return f"{city_he}: {tod['mintempC']}–{tod['maxtempC']}°C, {desc}"
    except Exception as e:
        print(f"Weather error {city_he}: {e}")
        return f"{city_he}: מזג האוויר אינו זמין"

def parse_ical_events(ical_url):
    """Parse iCal URL and return today + tomorrow events"""
    try:
        req = urllib.request.Request(ical_url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', 'replace')
        
        il = pytz.timezone('Asia/Jerusalem')
        now = datetime.now(il)
        today = now.date()
        tomorrow = today + timedelta(days=1)
        
        events = []
        # Parse VEVENT blocks manually (no external library needed)
        vevent_blocks = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', raw, re.DOTALL)
        for block in vevent_blocks:
            summary_m = re.search(r'SUMMARY[^:]*:(.*?)(?:\r?\n[A-Z])', block + '\nX', re.DOTALL)
            dtstart_m = re.search(r'DTSTART[^:]*:([\dTZ]+)', block)
            if not summary_m or not dtstart_m: continue
            summary = re.sub(r'\s+', ' ', summary_m.group(1)).strip()
            dtstart_raw = dtstart_m.group(1)
            try:
                if 'T' in dtstart_raw:
                    dt = datetime.strptime(dtstart_raw.rstrip('Z'), '%Y%m%dT%H%M%S')
                    if dtstart_raw.endswith('Z'):
                        dt = pytz.utc.localize(dt).astimezone(il)
                    event_date = dt.date()
                    time_str = dt.strftime('%H:%M')
                else:
                    event_date = datetime.strptime(dtstart_raw[:8], '%Y%m%d').date()
                    time_str = 'כל היום'
                if event_date == today:
                    events.append(f"היום {time_str} — {summary}")
                elif event_date == tomorrow:
                    events.append(f"מחר {time_str} — {summary}")
            except:
                continue
        return events if events else ["אין אירועים קרובים ביומן"]
    except Exception as e:
        print(f"iCal error: {e}")
        return ["לא ניתן לטעון את היומן — בדוק את GCAL_ICAL_URL"]

def get_calendar_events():
    ical_url = os.environ.get('GCAL_ICAL_URL', '')
    if not ical_url:
        return ["יומן לא מוגדר — הוסף GCAL_ICAL_URL לסודות GitHub"]
    return parse_ical_events(ical_url)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": msg}).encode()
    res = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15).read())
    print(f"Telegram: ok={res.get('ok')}")

def send_whatsapp(msg):
    data = json.dumps({"chatId": WA_CHAT_ID, "message": msg}).encode()
    req = urllib.request.Request(WA_URL, data=data, headers={"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=15).read())
    print(f"WhatsApp: {res.get('idMessage','?')}")

def send_email(subject, html_body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject; msg['From'] = GMAIL_USER; msg['To'] = GMAIL_USER
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
        s.login(GMAIL_USER, GMAIL_PASS)
        s.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
    print("Email sent")

def main():
    il = pytz.timezone('Asia/Jerusalem')
    now = datetime.now(il)
    session = current_session()
    is_morning = session == 'morning'
    months = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
    days   = ["יום שני","יום שלישי","יום רביעי","יום חמישי","יום שישי","יום שבת","יום ראשון"]
    date_he  = f"{now.day} {months[now.month-1]} {now.year}"
    date_dmy = now.strftime("%d.%m.%Y")
    day_name = days[now.weekday()]
    greeting = "בוקר טוב גיא!" if is_morning else "ערב טוב גיא!"
    sess     = "בוקר" if is_morning else "ערב"
    footer   = "עדכון הבא ב-18:00" if is_morning else "עדכון הבא ב-07:00"
    emoji    = "🌅" if is_morning else "🌆"
    tip_lbl  = "טיפ הבוקר" if is_morning else "טיפ הערב"
    tips = ["מכין רשימת משימות? התחל עם הדבר הכי קשה — שאר היום יהיה קל",
            "שתה כוס מים לפני הקפה — הגוף מתייבש בלילה",
            "10 דקות הליכה בחוץ שוות שעת פגישה מבחינת פרודוקטיביות",
            "שלח הודעת תודה לאדם אחד היום — זה מחזיר",
            "גבה קבצים חשובים — אם לא עשית השבוע, עשה עכשיו",
            "יום שישי טוב לסיים משימות, לא להתחיל חדשות",
            "השבת היא להטעין, לא לדאוג — שמור על זה"]
    tip = tips[now.weekday()]

    weather_harish = get_weather("Harish, Israel", "חריש")
    weather_ta     = get_weather("Tel Aviv, Israel", "תל אביב")
    calendar_events = get_calendar_events()

    # For evening: filter out events already shown in morning
    cache = load_cache()
    if session == 'evening':
        calendar_events = [e for e in calendar_events if not is_seen_morning(e, cache)]

    events_str = "\n".join(f"  • {e}" for e in calendar_events)

    plain = (f"{emoji} {greeting}\n{day_name} | {date_he}\n\n"
             f"🌤 מזג אוויר:\n  {weather_harish}\n  {weather_ta}\n\n"
             f"📅 סדר יום:\n{events_str}\n\n"
             f"💡 {tip_lbl}: {tip}\n\n{footer}")

    events_html = "".join(
        f'<div style="margin-bottom:8px;background:#f4f9ff;border-radius:10px;'
        f'border-right:4px solid #1976d2;padding:11px 14px;font-size:15px;font-weight:700;color:#0d1b2a">{e}</div>'
        for e in calendar_events
    )

    html_body = f"""<!DOCTYPE html><html dir="rtl" lang="he">
<head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;900&display=swap" rel="stylesheet">
<style>body{{background:#eef2f7;font-family:'Heebo',Arial,sans-serif;direction:rtl;margin:0;padding:20px 12px}}
.card{{max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(21,101,192,.15)}}
.hdr{{background:linear-gradient(135deg,#0d2d5e,#1565c0,#1976d2);padding:20px 24px}}
.stripe{{height:4px;background:linear-gradient(90deg,#0d47a1,#1976d2,#42a5f5,#1976d2,#0d47a1)}}
.sec{{padding:16px 24px 12px;border-bottom:1px solid #e8f4fd}}
.sec-title{{font-size:16px;font-weight:900;color:#0d2d5e;margin-bottom:12px}}
.weather{{margin-bottom:8px;background:#f4f9ff;border-radius:10px;border-right:4px solid #1976d2;padding:11px 14px;font-size:15px;font-weight:700;color:#0d1b2a}}
.tip{{margin:10px 24px 20px;background:#0d2d5e;border-radius:12px;padding:16px 18px}}
.ftr{{background:#f7f9fc;padding:14px;text-align:center;font-size:12px;font-weight:700;color:#1565c0}}</style>
</head><body><div class="card">
<div class="hdr">
  <div style="font-size:12px;font-weight:700;color:#90caf9;margin-bottom:6px">📅 {date_dmy} | {date_he} | {day_name}</div>
  <div style="font-size:24px;font-weight:900;color:#fff;margin-bottom:4px">{emoji} {greeting}</div>
  <div style="font-size:14px;font-weight:700;color:#bbdefb">📋 סדר היום האישי שלך</div>
</div><div class="stripe"></div>
<div class="sec"><div class="sec-title">🌤 מזג אוויר</div>
<div class="weather">{weather_harish}</div>
<div class="weather">{weather_ta}</div></div>
<div class="sec"><div class="sec-title">📅 סדר יום</div>
{events_html}</div>
<div class="tip">
  <div style="font-size:11px;font-weight:900;color:#90caf9;letter-spacing:2px;margin-bottom:8px">💡 {tip_lbl}</div>
  <div style="font-size:15px;color:#fff;line-height:1.65;font-weight:700">{tip}</div>
</div>
<div class="ftr">גיא רוזנברג ©2026 | {footer}</div>
</div></body></html>"""

    subject = f"{emoji} {greeting} — סדר יום {date_dmy}"
    send_telegram(plain)
    try: send_whatsapp(plain)
    except Exception as e: print(f"WA: {e}")
    try: send_email(subject, html_body)
    except Exception as e: print(f"Email: {e}")
    save_cache(mark_sent(calendar_events, cache, session))
    print(f"Done {date_he} {sess}")

if __name__ == "__main__":
    main()
