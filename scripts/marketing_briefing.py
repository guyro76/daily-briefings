"""Marketing & AI Daily Briefing — Hebrew only, images, 3+ lines"""
import sys, os, json, smtplib, re
import urllib.request, urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from utils import (parse_rss, fetch_article_meta, translate_he, is_hebrew,
                   is_banned, load_cache, save_cache, current_session,
                   mark_sent, is_seen_morning)

TELEGRAM_TOKEN = "8556094142:AAF_LPLMUjOvUfLmTdLEe2_6RUTfigFs4Z4"
TELEGRAM_CHAT_ID = "8526599959"
WA_URL = "https://7107.api.greenapi.com/waInstance7107593091/sendMessage/c2ee48c174284d658f942d78126eea979cf3adbd8a33491f8d"
WA_CHAT_ID = "972546585113@c.us"
GMAIL_USER = "guyro76@gmail.com"
GMAIL_PASS = "yscqggafoomwrais"

FEEDS = ["https://techtime.co.il/feed/"]
AI_KW = ["AI","בינה","מלאכותי","GPT","LLM","מודל","Gemini","Claude","ChatGPT","סוכן","אוטומציה","ענן"]
MKTG_KW = ["שיווק","פרסום","קמפיין","מדיה","דיגיטלי","אפליקציה","פלטפורמה","משתמשים","סטארטאפ"]
SOCIAL_KW = ["סושיאל","אינסטגרם","פייסבוק","טיקטוק","רשתות","w�הילה","תוכן","אינפלואנסר"]

def get_items(feeds, kw, count, cache, session):
    seen = set()
    results = []
    for url in feeds:
        for title, desc, link, rss_img in parse_rss(url, 20):
            if not title or title in seen: continue
            if is_banned(title) or is_banned(desc): continue
            if kw and not any(k.lower() in title.lower() or k.lower() in desc.lower() for k in kw): continue
            if session == 'evening' and is_seen_morning(title, cache):
                print(f"SKIP dup: {title[:50]}"); continue
            # Translate if English
            if not is_hebrew(title): title = translate_he(title)
            if not is_hebrew(desc): desc = translate_he(desc)
            # Enrich with article meta
            img = rss_img
            if link:
                art_img, art_desc = fetch_article_meta(link)
                if art_img and not img: img = art_img
                if art_desc and len(art_desc) > len(desc):
                    if not is_hebrew(art_desc): art_desc = translate_he(art_desc)
                    desc = art_desc
            seen.add(title)
            results.append({"title": title, "desc": desc[:400], "link": link, "img": img})
            if len(results) >= count: break
        if len(results) >= count: break
    return results

FALLBACK = {"title": "—", "desc": "אין עדכונים נוספים כרגע.", "link": "", "img": None}

def html_item(item, border, bg):
    img_tag = (f'<img src="{item["img"]}" style="width:100%;border-radius:8px;margin-bottom:10px;'
               f'max-height:200px;object-fit:cover" onerror="this.style.display=\'none\'">'
               if item.get("img") else "")
    return (f'<div style="margin-bottom:12px;background:{bg};border-radius:10px;'
            f'border-right:4px solid {border};padding:14px 16px">'
            f'{img_tag}'
            f'<div style="font-size:13px;font-weight:900;color:{border};margin-bottom:6px">{item["title"][:80]}</div>'
            f'<div style="font-size:14px;color:#1a2e2c;line-height:1.75;font-weight:700">{item["desc"]}</div>'
            f'</div>')

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
    date_he = f"{now.day} {months[now.month-1]} {now.year}"
    date_dmy = now.strftime("%d/%m/%Y")
    greeting = "בוקר טוב גיא!" if is_morning else "ערב טוב גיא!"
    sess = "בוקר" if is_morning else "ערב"
    footer = "עדכון הבא ב-18:00" if is_morning else "עדכון הבא ב-07:00"
    emoji = "🌅" if is_morning else "🌆"
    tip_lbl = "טיפ הבוקר" if is_morning else "טיפ הערב"
    tips = ["השתמש ב-A/B testing על כותרות מיילים","בדוק את Instagram Insights השבוע",
            "תוכן וידאו קצר מייצר פי 3 engagement","השתמש ב-Google Trends לנושאים חמים",
            "פרסם Stories לפחות פעמיים ביום","LinkedIn מוביל ב-B2B — פרסם שם היום",
            "השבת היא לטעון אנרגיה — תנוח"]
    tip = tips[now.weekday()]
    cache = load_cache()
    ai   = get_items(FEEDS, AI_KW,   3, cache, session)
    mktg = get_items(FEEDS, MKTG_KW, 3, cache, session)
    soc  = get_items(FEEDS, SOCIAL_KW,3, cache, session)
    total = len([x for x in ai+mktg+soc if x['title'] != '—'])
    if total < 3:
        print(f"ABORT: only {total} real items"); sys.exit(1)
    while len(mitg)<3: mktg.append(FALLBACK)
    while len(ai)<3:   ai.append(FALLBACK)
    while len(soc)<3:  soc.append(FALLBACK)
    def fmt(items): return "\n".join(f"• {i['title']}: {i['desc'][:120]}" for i in items)
    plain = (f"{emoji} {greeting} — שיווק דיגיטלי | {date_he}\n\n"
             f"📢 שיווק דיגיטלי:\n{fmt(mktg)}\n\n"
             f"🤖 AI וטכנולוגיה:\n{fmt(ai)}\n\n"
             f"📱 סושיאל ורשתות:\n{fmt(soc)}\n\n"
             f"💡 {tip_lbl}: {tip}\n{footer}")
    html_body = f"""<!DOCTYPE html><html dir="rtl" lang="he">
<head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;900&display=swap" rel="stylesheet">
<style>body{{background:#f0f4f8;font-family:'Heebo'Arial,sans-serif;direction:rtl;margin:0;padding:20px 12px}}
.card{{max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.12)}}
.hdr{{background:linear-gradient(135deg,#004d40,#00897b,#26a69a);padding:20px 24px}}
.stripe{{height:4px;background:linear-gradient(90deg,#004d40,#26a69a,#6a1b9a,#26a69a,#004d40)}}
.sec{{padding:16px 24px 12px;border-bottom:1px solid #eee}}
.sec-title{{font-size:17px;font-weight:900;margin-bottom:12py}}
.tip{{margin:10px 24px 20px;background:#1a237e;border-radius:12px;padding:16px 18px}}
.ftr{{background:#f7f9fc;padding:14px;text-align:center;font-size:12px;font-weight:700;color:#5B2C6F}}</style>
</head><body><div class="card">
<div class="hdr">
  <div style="font-size:12px;font-weight:700;color:#b2dfdb;margin-bottom:6px">📅 {date_he} | עדכון {sess}</div>
  <div style="font-size:24px;font-weight:900;color:#fff;margin-bottom:4px">{emoji} {greeting}</div>
  <div style="font-size:14px;font-weight:700;color:#e0f2f1">⚡ שיווק דיגיטלי • AI • סושיאל</div>
</div><div class="stripe"></div>
<div class="sec"><div class="sec-title" style="color:#00695c">📢 שיווק דיגיטלי</div>
{''.join(html_item(i,'#00897b','#f5fffe') for i in mktg)}</div>
<div class="sec"><div class="sec-title" style="color:#6a1b9a">🤖 AI וטכנולוגיה</div>
{''.join(html_item(i,'#6a1b9a','#fdf7ff') for i in ai)}</div>
<div class="sec"><div class="sec-title" style="color:#1565c0">📱 סושיאל ורשתות</div>
{''.join(html_item(i,'#1565c0','#f0f7ff') for i in soc)}</div>
<div class="tip">
  <div style="font-size:11px;font-weight:900;color:#90caf9;letter-spacing:2px;margin-bottom:8px">💡 {tip_lbl}</div>
  <div style="font-size:16px;color:#fff;line-height:1.65;font-weight:700">{tip}</div>
</div>
<div class="ftr">גיא רוזנברג ©2026 | {footer}</div>
</div></body></html>"""
    subject = f"{emoji} עדכון {sess} — שיווק דיגיטלי | {date_dmy}"
    send_telegram(plain)
    try: send_whatsapp(plain)
    except Exception as e: print(f"WA: {e}")
    try: send_email(subject, html_body)
    except Exception as e: print(f"Email: {e}")
    all_titles = [i['title'] for i in mktg+ai+soc]
    save_cache(mark_sent(all_titles, cache, session))
    print(f"Done {date_he} {sess}")

if __name__ == "__main__":
    main()
