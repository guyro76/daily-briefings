"""
daily-tv-cinema-briefing - GitHub Actions version
Runs at 04:00 UTC (07:00 IL) and 15:00 UTC (18:00 IL)
No paid APIs - uses free Hebrew RSS feeds
"""

import json
import smtplib
import sys
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import xml.etree.ElementTree as ET
import re
import pytz

# === CONFIG ===
TELEGRAM_TOKEN = "8556094142:AAF_LPLMUjOvUfLmTdLEe2_6RUTfigFs4Z4"
TELEGRAM_CHAT_ID = "8526599959"
WA_URL = "https://7107.api.greenapi.com/waInstance7107593091/sendMessage/c2ee48c174284d658f942d78126eea979cf3adbd8a33491f8d"
WA_CHAT_ID = "972546585113@c.us"
GMAIL_USER = "guyro76@gmail.com"
GMAIL_PASS = "yscqggafoomwrais"

MIN_REAL_ITEMS = 3  # מינימום כתבות אמיתיות לפני שליחה

TV_FEEDS = [
    "https://www.ynet.co.il/Integration/StoryRss3869.xml",
    "https://rotter.net/rss/rss.xml",
    "https://deadline.com/category/television/feed/",
]
CINEMA_FEEDS = [
    "https://www.ynet.co.il/Integration/StoryRss3869.xml",
    "https://variety.com/v/film/feed/",
    "https://deadline.com/category/film/feed/",
]
PLATFORM_FEEDS = [
    "https://www.ynet.co.il/Integration/StoryRss3869.xml",
    "https://variety.com/v/digital/feed/",
    "https://techcrunch.com/tag/netflix/feed/",
]

def fetch_rss(url, max_items=4):
    items = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=10).read()
        root = ET.fromstring(data)
        for item in root.iter("item"):
            title_el = item.find("title")
            desc_el = item.find("description")
            if title_el is not None:
                title = (title_el.text or "").strip()[:80]
                desc = (desc_el.text or "" if desc_el is not None else "").strip()
                desc = re.sub(r'<[^>]+>', '', desc).strip()[:150]
                if title:
                    items.append((title, desc or title))
                    if len(items) >= max_items:
                        break
    except Exception as e:
        print(f"RSS error {url}: {e}")
    return items

def get_news_items(feeds, count=3, keywords=None):
    """Returns only real news items - no placeholders ever."""
    seen = set()
    results = []
    for feed_url in feeds:
        items = fetch_rss(feed_url)
        for title, desc in items:
            if title not in seen:
                if keywords is None or any(k.lower() in title.lower() for k in keywords):
                    seen.add(title)
                    results.append((title, desc))
                    if len(results) >= count:
                        break
        if len(results) >= count:
            break
    return results[:count]

def validate_content(tv, cinema, platforms):
    """Validates enough real content exists before sending."""
    total_real = len(tv) + len(cinema) + len(platforms)
    if total_real < MIN_REAL_ITEMS:
        return False, f"only {total_real} real items (need {MIN_REAL_ITEMS})"
    if len(tv) == 0:
        return False, "TV section is empty"
    if len(cinema) == 0:
        return False, "Cinema section is empty"
    return True, "OK"

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
    print("Email sent successfully")

def main():
    il = pytz.timezone('Asia/Jerusalem')
    now = datetime.now(il)
    is_morning = now.hour < 12
    months = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
    date_he = f"{now.day} {months[now.month-1]} {now.year}"
    date_dmy = now.strftime("%d/%m/%Y")
    greeting = "בוקר טוב גיא!" if is_morning else "ערב טוב גיא!"
    session = "בוקר" if is_morning else "ערב"
    footer = "עדכון הבא ב-18:00" if is_morning else "עדכון הבא ב-07:00"
    tip_label = "המלצת הבוקר" if is_morning else "המלצת הערב"
    emoji = "\U0001f305" if is_morning else "\U0001f306"

    tv = get_news_items(TV_FEEDS, 3, keywords=["סדרה","טלוויזיה","ערוץ","Netflix","HBO","Disney","series","TV","show"])
    cinema = get_news_items(CINEMA_FEEDS, 3, keywords=["סרט","קולנוע","trailer","film","movie","box office"])
    platforms = get_news_items(PLATFORM_FEEDS, 2, keywords=["Netflix","HOT","Apple","Disney","streaming","פלטפורמה"])

    # === CONTENT VALIDATION - abort if not enough real content ===
    is_valid, reason = validate_content(tv, cinema, platforms)
    if not is_valid:
        print(f"SEND ABORTED - insufficient content: {reason}")
        print(f"TV: {len(tv)}, Cinema: {len(cinema)}, Platforms: {len(platforms)}")
        sys.exit(1)

    print(f"Content OK - sending ({len(tv)+len(cinema)+len(platforms)} real items)")

    # Pad display only after validation passes - never with placeholder garbage
    while len(tv) < 3:
        tv.append(("—", "אין עדכונים נוספים"))
    while len(cinema) < 3:
        cinema.append(("—", "אין עדכונים נוספים"))
    while len(platforms) < 2:
        platforms.append(("—", "אין עדכונים נוספים"))

    tips = [
        "Netflix מוסיפה תוכן חדש כל שבוע - כדאי לבדוק בימי שישי",
        "חפש סדרות ישראליות 2026 ב-YouTube",
        "Apple TV+ מציעה ניסיון חינם 7 ימים",
        "שימוש ב-JustWatch עוזר למצוא איפה זמין כל סרט",
        "HBO Max נקרא כעת Max - עדכן את הסימניות שלך",
        "Letterboxd הוא הרשת החברתית הכי טובה לאוהבי קולנוע",
        "פסטיבל קאן, ונציה ובברלין - שם מתגלים הסרטים הכי טובים",
    ]
    tip_text = tips[now.weekday()]

    def fmt(items):
        return "\n".join(f"* {t}: {d[:100]}" for t, d in items)

    plain = f"""{emoji} {greeting} - טלוויזיה וקולנוע {date_he}

טלוויזיה:
{fmt(tv)}

קולנוע:
{fmt(cinema)}

ערוצים ופלטפורמות:
{fmt(platforms)}

{tip_label}: {tip_text}
{footer}"""

    def html_items(items):
        html = ""
        for t, d in items:
            html += f'<div class="item"><div class="item-label">{t[:60]}</div><div class="item-text">{d[:150]}</div></div>'
        return html

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;800;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#f5f0fb;font-family:'Heebo',Arial,sans-serif;direction:rtl;text-align:right}}
.wrap{{padding:20px 12px}}
.card{{max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(74,20,140,.15)}}
.hdr{{background:linear-gradient(135deg,#2a0745 0%,#6a1b9a 60%,#9c27b0 100%);padding:20px 24px 18px}}
.hdr-meta{{font-size:12px;font-weight:700;color:#e1bee7;letter-spacing:1px;margin-bottom:6px}}
.hdr-title{{font-size:24px;font-weight:900;color:#fff;margin-bottom:4px}}
.hdr-sub{{font-size:14px;font-weight:700;color:#f3e5f5}}
.stripe{{height:4px;background:linear-gradient(90deg,#4a148c,#9c27b0,#ce93d8,#9c27b0,#4a148c)}}
.sec{{padding:18px 24px 14px;border-bottom:1px solid #f3e5f5}}
.sec-hdr{{display:flex;align-items:center;gap:10px;flex-direction:row-reverse;justify-content:flex-end;margin-bottom:14px}}
.sec-icon{{font-size:20px}}
.sec-title{{font-size:17px;font-weight:900;color:#4a148c}}
.item{{margin-bottom:10px;background:#fdf7ff;border-radius:10px;border-right:4px solid #9c27b0;padding:12px 14px}}
.item-label{{font-size:12px;font-weight:900;color:#6a1b9a;letter-spacing:1px;margin-bottom:4px}}
.item-text{{font-size:15px;color:#1a0a2e;line-height:1.65;font-weight:700}}
.tip{{margin:10px 24px 20px;background:#2a0745;border-radius:12px;padding:16px 18px}}
.tip-lbl{{font-size:11px;font-weight:900;color:#ce93d8;letter-spacing:2px;margin-bottom:8px}}
.tip-txt{{font-size:15px;color:#fff;line-height:1.65;font-weight:700}}
.ftr{{background:#f9f0ff;padding:14px 24px;text-align:center;font-size:12px;font-weight:700;color:#5B2C6F;border-top:2px solid #e1bee7}}
</style></head>
<body><div class="wrap"><div class="card">
<div class="hdr">
<div class="hdr-meta">&#x1F4C5; {date_he} | עדכון {session}</div>
<div class="hdr-title">{emoji} {greeting}</div>
<div class="hdr-sub">&#x1F3AC; טלוויזיה &#x2022; קולנוע &#x2022; ערוצים</div>
</div>
<div class="stripe"></div>
<div class="sec">
<div class="sec-hdr"><span class="sec-icon">&#x1F4FA;</span><span class="sec-title">טלוויזיה</span></div>
{html_items(tv)}
</div>
<div class="sec">
<div class="sec-hdr"><span class="sec-icon">&#x1F3AC;</span><span class="sec-title">קולנוע</span></div>
{html_items(cinema)}
</div>
<div class="sec">
<div class="sec-hdr"><span class="sec-icon">&#x1F4E1;</span><span class="sec-title">ערוצים ופלטפורמות</span></div>
{html_items(platforms)}
</div>
<div class="tip">
<div class="tip-lbl">&#x1F37F; {tip_label}</div>
<div class="tip-txt">{tip_text}</div>
</div>
<div class="ftr">גיא רוזנברג &#169;2026 | {footer}</div>
</div></div></body></html>"""

    subject = f"{emoji} עדכון בידור {session} | {date_dmy}"
    send_telegram(plain)
    try:
        send_whatsapp(plain)
    except Exception as e:
        print(f"WhatsApp error: {e}")
    try:
        send_email(subject, html)
    except Exception as e:
        print(f"Email error: {e}")
    print(f"Done - {date_he} {session}")

if __name__ == "__main__":
    main()
