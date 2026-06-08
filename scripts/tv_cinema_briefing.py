"""TV & Cinema Daily Briefing — Hebrew only, translated, with images"""
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

BANNED_ENT = {'war','military','combat','attack','hostage','massacre','shooting','bombing'}
TV_FEEDS   = ["https://www.hollywoodreporter.com/feed/", "https://deadline.com/category/television/feed/"]
FILM_FEEDS = ["https://www.hollywoodreporter.com/feed/", "https://deadline.com/category/film/feed/"]
STREAM_FEEDS = ["https://variety.com/v/television/feed/", "https://deadline.com/category/streaming/feed/"]

TV_KW    = ["series","season","episode","premiere","TV","show","drama","comedy","HBO","Netflix","Disney","Apple","streaming"]
FILM_KW  = ["film","movie","cinema","box office","feature","documentary","thriller","director","cast","trailer"]
STREAM_KW= ["Netflix","Disney+","HBO Max","Apple TV","Prime Video","Hulu","streaming","release","debut"]

def banned_en(text):
    tl = (text or '').lower()
    return any(w in tl for w in BANNED_ENT) or is_banned(text)

def get_items(feeds, kw, count, cache, session, global_seen=None):
    if global_seen is None: global_seen = set()
    seen = set()
    results = []
    for url in feeds:
        for title, desc, link, rss_img in parse_rss(url, 20):
            if not title or title in seen or title in global_seen: continue
            if banned_en(title) or banned_en(desc): continue
            if kw and not any(k.lower() in title.lower() or k.lower() in desc.lower() for k in kw): continue
            if session == 'evening' and is_seen_morning(title, cache):
                print(f"SKIP dup: {title[:50]}"); continue
            # Translate
            title_he = translate_he(title) if not is_hebrew(title) else title
            desc_he  = translate_he(desc)  if not is_hebrew(desc)  else desc
            # Enrich
            img = rss_img
            if link:
                art_img, art_desc = fetch_article_meta(link)
                if art_img and not img: img = art_img
                if art_desc and len(art_desc) > len(desc_he):
                    art_desc_he = translate_he(art_desc) if not is_hebrew(art_desc) else art_desc
                    desc_he = art_desc_he
            seen.add(title)
            global_seen.add(title)
            results.append({"title": title_he, "desc": desc_he[:400], "link": link, "img": img})
            if len(results) >= count: break
        if len(results) >= count: break
    return results

FALLBACK = {"title": "—", "desc": "אין עדכונים בידורניים נוספים כרגע.", "link": "", "img": None}

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
    date_he  = f"{now.day} {months[now.month-1]} {now.year}"
    date_dmy = now.strftime("%d/%m/%Y")
    greeting = "בוקר טוב גיא!" if is_morning else "ערב טוב גיא!"
    sess     = "בוקר" if is_morning else "ערב"
    footer   = "עדכון הבא ב-18:00" if is_morning else "עדכון הבא ב-07:00"
    emoji    = "🌅" if is_morning else "🌆"
    tip_lbl  = "טיפ הבוקר" if is_morning else "טיפ הערב"
    tips = ["סדרות קצרות (6–8 פרקים) מקבלות ביקורות טובות יותר בממוצע",
            "הרישום ל-JustWatch עוזר לעקוב אחרי מה שיצא בכל הפלטפורמות",
            "Netflix ישראל משחררת תוכן ישראלי בדרך כלל ביום רביעי",
            "Letterboxd היא הרשת החברתית הטובה ביותר לחובבי קולנוע",
            "HOT VOD מוסיפה סדרות חדשות בכל שישי",
            "כאן 11 מפרסמת לוח שידורים שבועי באתר שלה",
            "יום ראשון הוא היום עם הכי הרבה פרמיירות בנטפליקס העולמי"]
    tip = tips[now.weekday()]
    cache = load_cache()
    global_seen = set()
    tv_items     = get_items(TV_FEEDS,     TV_KW,     3, cache, session, global_seen)
    film_items   = get_items(FILM_FEEDS,   FILM_KW,   3, cache, session, global_seen)
    stream_items = get_items(STREAM_FEEDS, STREAM_KW, 3, cache, session, global_seen)
    total = len([x for x in tv_items+film_items+stream_items if x['title'] != '—'])
    if total < 3:
        print(f"ABORT: only {total} real items"); sys.exit(1)
    while len(tv_items)<3:     tv_items.append(FALLBACK)
    while len(film_items)<3:   film_items.append(FALLBACK)
    while len(stream_items)<3: stream_items.append(FALLBACK)
    def fmt(items): return "\n".join(f"• {i['title']}: {i['desc'][:120]}" for i in items)
    plain = (f"{emoji} {greeting} — טלוויזיה וקולנוע | {date_he}\n\n"
             f"📺 סדרות טלוויזיה:\n{fmt(tv_items)}\n\n"
             f"🎬 קולנוע:\n{fmt(film_items)}\n\n"
             f"🎞 פלטפורמות סטרימינג:\n{fmt(stream_items)}\n\n"
             f"💡 {tip_lbl}: {tip}\n{footer}")
    html_body = f"""<!DOCTYPE html><html dir="rtl" lang="he">
<head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;900&display=swap" rel="stylesheet">
<style>body{{background:#f0f4f8;font-family:'Heebo',Arial,sans-serif;direction:rtl;margin:0;padding:20px 12px}}
.card{{max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.12)}}
.hdr{{background:linear-gradient(135deg,#1a237e,#283593,#3949ab);padding:20px 24px}}
.stripe{{height:4px;background:linear-gradient(90deg,#1a237e,#7986cb,#e040fb,#7986cb,#1a237e)}}
.sec{{padding:16px 24px 12px;border-bottom:1px solid #eee}}
.sec-title{{font-size:17px;font-weight:900;margin-bottom:12px}}
.tip{{margin:10px 24px 20px;background:#1a237e;border-radius:12px;padding:16px 18px}}
.ftr{{background:#f7f9fc;padding:14px;text-align:center;font-size:12px;font-weight:700;color:#5B2C6F}}</style>
</head><body><div class="card">
<div class="hdr">
  <div style="font-size:12px;font-weight:700;color:#9fa8da;margin-bottom:6px">📅 {date_he} | עדכון {sess}</div>
  <div style="font-size:24px;font-weight:900;color:#fff;margin-bottom:4px">{emoji} {greeting}</div>
  <div style="font-size:14px;font-weight:700;color:#c5cae9">🎬 טלוויזיה • קולנוע • סטרימינג</div>
</div><div class="stripe"></div>
<div class="sec"><div class="sec-title" style="color:#283593">📺 סדרות טלוויזיה</div>
{''.join(html_item(i,'#3949ab','#f0f2ff') for i in tv_items)}</div>
<div class="sec"><div class="sec-title" style="color:#6a1b9a">🎬 קולנוע</div>
{''.join(html_item(i,'#8e24aa','#fdf4ff') for i in film_items)}</div>
<div class="sec"><div class="sec-title" style="color:#c62828">🎞 פלטפורמות סטרימינג</div>
{''.join(html_item(i,'#e53935','#fff5f5') for i in stream_items)}</div>
<div class="tip">
  <div style="font-size:11px;font-weight:900;color:#9fa8da;letter-spacing:2px;margin-bottom:8px">💡 {tip_lbl}</div>
  <div style="font-size:16px;color:#fff;line-height:1.65;font-weight:700">{tip}</div>
</div>
  <div class="ftr">גיא רוזנברג ©2026 | {footer}</div>
</div></body></html>"""
    subject = f"{emoji} עדכון {sess} — טלוויזיה וקולנוע | {date_dmy}"
    send_telegram(plain)
    try: send_whatsapp(plain)
    except Exception as e: print(f"WA: {e}")
    try: send_email(subject, html_body)
    except Exception as e: print(f"Email: {e}")
    all_titles = [i['title'] for i in tv_items+film_items+stream_items]
    save_cache(mark_sent(all_titles, cache, session))
    print(f"Done {date_he} {sess}")

if __name__ == "__main__":
    main()

