"""Personal Briefing — Weather + Calendar + Medical + Webinars + Packages"""
import sys, os, json, smtplib, re, imaplib, email as emaillib
import urllib.request, urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
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

MEDICAL_KW   = ["רופא","מרפאה","בית חולים","בדיקה","קופת חולים","כללית","מאוחדת","ניתוח",
                "doctor","hospital","clinic","blood test","ultrasound","mri","ct scan","specialist"]
WEBINAR_KW   = ["וובינר","webinar","zoom","google meet","teams","workshop","הרצאה","כנס",
                "סדנה","seminar","conference","meetup","online","live","שידור"]
PACKAGE_SENDERS = ["aliexpress","alimail","israel post","israelpost","il post","hadomain",
                   "dhl","fedex","ups","usps","tracking","shipment","delivery","משלוח","חבילה"]
PACKAGE_SUBJECTS = ["tracking","shipment","delivery","your order","package","חבילה","משלוח",
                    "עדכון הזמנה","הזמנה שלך","נשלחה","הגיעה","collected"]

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

def parse_ical_all(ical_url, days_ahead=30):
    """Return all events in the next N days, categorized"""
    try:
        req = urllib.request.Request(ical_url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', 'replace')
        il = pytz.timezone('Asia/Jerusalem')
        now = datetime.now(il)
        today = now.date()
        end_date = today + timedelta(days=days_ahead)
        events = []
        for block in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', raw, re.DOTALL):
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
                if today <= event_date <= end_date:
                    if event_date == today:    day_label = f"היום {time_str}"
                    elif event_date == today+timedelta(1): day_label = f"מחר {time_str}"
                    else:
                        days_diff = (event_date - today).days
                        day_label = f"בעוד {days_diff} ימים {time_str} ({event_date.strftime('%d/%m')})"
                    events.append({"summary": summary, "date": event_date,
                                   "label": day_label, "time": time_str})
            except: continue
        return events
    except Exception as e:
        print(f"iCal error: {e}")
        return []

def filter_events(all_events, keywords, days=2):
    il = pytz.timezone('Asia/Jerusalem')
    today = datetime.now(il).date()
    cutoff = today + timedelta(days=days)
    result = []
    for ev in all_events:
        if ev["date"] > cutoff: continue
        text = ev["summary"].lower()
        if any(k.lower() in text for k in keywords):
            result.append(f"{ev['label']} — {ev['summary']}")
    return result

def get_calendar_general(all_events):
    """Today + tomorrow events only, excluding medical/webinar"""
    il = pytz.timezone('Asia/Jerusalem')
    today = datetime.now(il).date()
    tomorrow = today + timedelta(1)
    result = []
    for ev in all_events:
        if ev["date"] not in (today, tomorrow): continue
        text = ev["summary"].lower()
        is_medical = any(k.lower() in text for k in MEDICAL_KW)
        is_webinar  = any(k.lower() in text for k in WEBINAR_KW)
        result.append(f"{ev['label']} — {ev['summary']}")
    return result if result else ["אין אירועים להיום ומחר"]

def get_package_updates():
    """Search Gmail via IMAP for recent package tracking emails"""
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select('inbox')
        since_date = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
        packages = []
        _, msg_ids = mail.search(None, f'SINCE {since_date}')
        ids = msg_ids[0].split()[-50:] if msg_ids[0] else []  # last 50
        for mid in reversed(ids):
            _, data = mail.fetch(mid, '(RFC822.HEADER)')
            if not data or not data[0]: continue
            msg = emaillib.message_from_bytes(data[0][1])
            subject_raw = msg.get('Subject', '')
            from_raw    = msg.get('From', '').lower()
            # Decode subject
            parts = decode_header(subject_raw)
            subject = ''
            for part, enc in parts:
                if isinstance(part, bytes):
                    subject += part.decode(enc or 'utf-8', errors='replace')
                else:
                    subject += part
            subject_l = subject.lower()
            from_match = any(s in from_raw for s in PACKAGE_SENDERS)
            subj_match = any(s in subject_l for s in PACKAGE_SUBJECTS)
            if from_match or subj_match:
                packages.append(subject[:80])
            if len(packages) >= 3: break
        mail.logout()
        return packages
    except Exception as e:
        print(f"Package IMAP error: {e}")
        return []

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

def item_html(text, border='#1976d2', bg='#f4f9ff'):
    return (f'<div style="margin-bottom:8px;background:{bg};border-radius:10px;'
            f'border-right:4px solid {border};padding:11px 14px;'
            f'font-size:15px;font-weight:700;color:#0d1b2a">{text}</div>')

def section_html(icon, title, items, border='#1976d2', bg='#f4f9ff', color='#0d2d5e'):
    if not items: return ''
    items_html = ''.join(item_html(i, border, bg) for i in items)
    return (f'<div style="padding:16px 24px 12px;border-bottom:1px solid #e8f4fd">'
            f'<div style="font-size:16px;font-weight:900;color:{color};margin-bottom:12px">{icon} {title}</div>'
            f'{items_html}</div>')

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

    # Weather
    weather_harish = get_weather("Harish, Israel", "חריש")
    weather_ta     = get_weather("Tel Aviv, Israel", "תל אביב")

    # Calendar — load all events once
    ical_url = os.environ.get('GCAL_ICAL_URL', '')
    all_events = parse_ical_all(ical_url, days_ahead=30) if ical_url else []

    calendar_events = get_calendar_general(all_events) if ical_url else ["יומן לא מוגדר — הוסף GCAL_ICAL_URL לסודות GitHub"]
    medical_events  = filter_events(all_events, MEDICAL_KW, days=30)
    webinar_events  = filter_events(all_events, WEBINAR_KW, days=14)

    # Packages via Gmail IMAP
    package_items = get_package_updates()

    # Evening: filter out morning items
    cache = load_cache()
    if session == 'evening':
        calendar_events = [e for e in calendar_events if not is_seen_morning(e, cache)]

    # Plain text
    def fmt_list(items, empty="אין עדכונים"):
        return "\n".join(f"  • {i}" for i in items) if items else f"  {empty}"

    plain = (f"{emoji} {greeting}\n{day_name} | {date_he}\n\n"
             f"🌤 מזג אוויר:\n  {weather_harish}\n  {weather_ta}\n\n"
             f"📅 סדר יום:\n{fmt_list(calendar_events)}\n")
    if medical_events:
        plain += f"\n🏥 בדיקות רפואיות:\n{fmt_list(medical_events)}\n"
    if webinar_events:
        plain += f"\n🎓 וובינרים קרובים:\n{fmt_list(webinar_events)}\n"
    if package_items:
        plain += f"\n📦 משלוחים:\n{fmt_list(package_items)}\n"
    plain += f"\n💡 {tip_lbl}: {tip}\n\n{footer}"

    # HTML
    weather_html = (item_html(weather_harish, '#1976d2', '#f4f9ff') +
                    item_html(weather_ta,     '#1976d2', '#f4f9ff'))
    cal_html = ''.join(item_html(e) for e in calendar_events)

    medical_sec = section_html('🏥', 'בדיקות רפואיות', medical_events, '#c62828', '#fff5f5', '#b71c1c') if medical_events else ''
    webinar_sec = section_html('🎓', 'וובינרים קרובים', webinar_events, '#6a1b9a', '#fdf4ff', '#6a1b9a') if webinar_events else ''
    package_sec = section_html('📦', 'משלוחים', package_items, '#e65100', '#fff8f0', '#bf360c') if package_items else ''

    html_body = f"""<!DOCTYPE html><html dir="rtl" lang="he">
<head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;900&display=swap" rel="stylesheet">
<style>body{{background:#eef2f7;font-family:'Heebo',Arial,sans-serif;direction:rtl;margin:0;padding:20px 12px}}
.card{{max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(21,101,192,.15)}}
.hdr{{background:linear-gradient(135deg,#0d2d5e,#1565c0,#1976d2);padding:20px 24px}}
.stripe{{height:4px;background:linear-gradient(90deg,#0d47a1,#1976d2,#42a5f5,#1976d2,#0d47a1)}}
.tip{{margin:10px 24px 20px;background:#0d2d5e;border-radius:12px;padding:16px 18px}}
.ftr{{background:#f7f9fc;padding:14px;text-align:center;font-size:12px;font-weight:700;color:#1565c0}}</style>
</head><body><div class="card">
<div class="hdr">
  <div style="font-size:12px;font-weight:700;color:#90caf9;margin-bottom:6px">📅 {date_dmy} | {date_he} | {day_name}</div>
  <div style="font-size:24px;font-weight:900;color:#fff;margin-bottom:4px">{emoji} {greeting}</div>
  <div style="font-size:14px;font-weight:700;color:#bbdefb">📋 סדר היום האישי שלך</div>
</div><div class="stripe"></div>
<div style="padding:16px 24px 12px;border-bottom:1px solid #e8f4fd">
  <div style="font-size:16px;font-weight:900;color:#0d2d5e;margin-bottom:12px">🌤 מזג אוויר</div>
  {weather_html}</div>
<div style="padding:16px 24px 12px;border-bottom:1px solid #e8f4fd">
  <div style="font-size:16px;font-weight:900;color:#0d2d5e;margin-bottom:12px">📅 סדר יום</div>
  {cal_html}</div>
{medical_sec}{webinar_sec}{package_sec}
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
