"""
daily-marketing-briefing - GitHub Actions version
Runs at 04:00 UTC (07:00 IL) and 15:00 UTC (18:00 IL)
No paid APIs - uses free Hebrew RSS feeds
"""

import json
import smtplib
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import xml.etree.ElementTree as ET
import pytz

# === CONFIG ===
TELEGRAM_TOKEN = "8556094142:AAF_LPLMUjOvUfLmTdLEe2_6RUTfigFs4Z4"
TELEGRAM_CHAT_ID = "8526599959"
WA_URL = "https://7107.api.greenapi.com/waInstance7107593091/sendMessage/c2ee48c174284d658f942d78126eea979cf3adbd8a33491f8d"
WA_CHAT_ID = "972546585113@c.us"
GMAIL_USER = "guyro76@gmail.com"
GMAIL_PASS = "yscqggafoomwrais"

# === RSS SOURCES ===
MARKETING_FEEDS = [
    "https://www.geektime.co.il/feed/",
    "https://www.calcalistech.com/rss/",
    "https://nocamels.com/feed/",
]
SOCIAL_FEEDS = [
    "https://www.geektime.co.il/feed/",
    "https://www.the7eye.org.il/feed",
    "https://digital.calcalist.co.il/feed.xml",
]
AI_FEEDS = [
    "https://www.geektime.co.il/feed/",
    "https://nocamels.com/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
]

def fetch_rss(url, max_items=3):
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
                desc = (desc_el.text or title if desc_el is not None else title).strip()
                import re
                desc = re.sub(r'<[^>]+>', '', desc).strip()[:150]
                if title:
                    items.append((title, desc or title))
            if len(items) >= max_items:
                break
    except Exception as e:
        print(f"RSS error {url}: {e}")
    return items

def get_news_items(feeds, count=3, keywords=None):
    seen = set()
    results = []
    for feed_url in feeds:
        items = fetch_rss(feed_url, max_items=5)
        for title, desc in items:
            if title not in seen:
                if keywords is None or any(k.lower() in title.lower() or k.lower() in desc.lower() for k in keywords):
                    seen.add(title)
                    results.append((title, desc))
            if len(results) >= count:
                break
        if len(results) >= count:
            break
    while len(results) < count:
        results.append(("עדכון שיווק דיגיטלי", "בדוק את הפיד שלך לעדכונים נוספים"))
    return results[:count]

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
    tip_label = "טיפ הבוקר" if is_morning else "טיפ הערב"
    emoji = "🌅" if is_morning else "🌆"

    marketing = get_news_items(MARKETING_FEEDS, 3)
    social = get_news_items(SOCIAL_FEEDS, 3)
    ai_news = get_news_items(AI_FEEDS, 3, keywords=["AI","בינה","מלאכותי","GPT","LLM","אוטומציה"])

    tips = [
        "השתמש ב-A/B testing על כותרות מיילים",
        "בדוק את Instagram Insights כל שבוע",
        "תוכן וידאו קצר מייצר פי 3 engagement",
        "השתמש ב-Google Trends לזיהוי נושאים חמים",
        "פרסם Stories לפחות פעמיים ביום",
        "LinkedIn מוביל ב-B2B",
        "השתמש ב-Canva AI לעיצוב מהיר",
    ]
    tip_text = tips[now.weekday()]

    def fmt(items):
        return "\n".join(f"* {t}: {d[:100]}" for t, d in items)

    plain = f"""{emoji} {greeting} - שיווק דיגיטלי {date_he}

שיווק דיגיטלי:
{fmt(marketing)}

סושיאל ורשתות:
{fmt(social)}

AI וטרנדים:
{fmt(ai_news)}

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
body{{background:#f0f4f8;font-family:'Heebo',Arial,sans-serif;direction:rtl;text-align:right}}
.wrap{{padding:20px 12px}}
.card{{max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.12)}}
.hdr{{background:linear-gradient(135deg,#004d40 0%,#00897b 60%,#26a69a 100%);padding:20px 24px 18px}}
.hdr-meta{{font-size:12px;font-weight:700;color:#b2dfdb;letter-spacing:1px;margin-bottom:6px}}
.hdr-title{{font-size:24px;font-weight:900;color:#fff;margin-bottom:4px}}
.hdr-sub{{font-size:14px;font-weight:700;color:#e0f2f1}}
.stripe{{height:4px;background:linear-gradient(90deg,#004d40,#26a69a,#80cbc4,#26a69a,#004d40)}}
.sec{{padding:18px 24px 14px;border-bottom:1px solid #edf5f4}}
.sec-hdr{{display:flex;align-items:center;gap:10px;flex-direction:row-reverse;justify-content:flex-end;margin-bottom:14px}}
.sec-icon{{font-size:20px}}
.sec-title{{font-size:17px;font-weight:900;color:#004d40}}
.item{{margin-bottom:10px;background:#f5fffe;border-radius:10px;border-right:4px solid #00897b;padding:12px 14px}}
.item-label{{font-size:12px;font-weight:900;color:#00695c;letter-spacing:1px;margin-bottom:4px}}
.item-text{{font-size:15px;color:#1a2e2c;line-height:1.65;font-weight:700}}
.tip{{margin:10px 24px 20px;background:#004d40;border-radius:12px;padding:16px 18px}}
.tip-lbl{{font-size:11px;font-weight:900;color:#80cbc4;letter-spacing:2px;margin-bottom:8px}}
.tip-txt{{font-size:15px;color:#fff;line-height:1.65;font-weight:700}}
.ftr{{background:#f7f9fc;padding:14px 24px;text-align:center;font-size:12px;font-weight:700;color:#5B2C6F;border-top:2px solid #e0f2f1}}
</style></head>
<body><div class="wrap"><div class="card">
<div class="hdr">
  <div class="hdr-meta">&#x1F4C5; {date_he} | עדכון {session}</div>
  <div class="hdr-title">{emoji} {greeting}</div>
  <div class="hdr-sub">&#x26A1; שיווק דיגיטלי &#x2022; סושיאל &#x2022; AI</div>
</div>
<div class="stripe"></div>
<div class="sec">
  <div class="sec-hdr"><span class="sec-icon">&#x1F4E2;</span><span class="sec-title">שיווק דיגיטלי</span></div>
  {html_items(marketing)}
</div>
<div class="sec">
  <div class="sec-hdr"><span class="sec-icon">&#x1F4F1;</span><span class="sec-title">סושיאל ורשתות</span></div>
  {html_items(social)}
</div>
<div class="sec">
  <div class="sec-hdr"><span class="sec-icon">&#x1F525;</span><span class="sec-title">AI וטרנדים</span></div>
  {html_items(ai_news)}
</div>
<div class="tip">
  <div class="tip-lbl">&#x1F4A1; {tip_label}</div>
  <div class="tip-txt">{tip_text}</div>
</div>
<div class="ftr">גיא רוזנברג &#169;2026 | {footer}</div>
</div></div></body></html>"""

    subject = f"{emoji} עדכון {session} - שיווק דיגיטלי | {date_dmy}"
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
