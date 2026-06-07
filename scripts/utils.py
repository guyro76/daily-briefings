"""Shared utilities for daily briefings"""
import json, re, os, html as html_lib
import urllib.request, urllib.parse
from datetime import datetime
import pytz

HEBREW_CHARS = set('אבגדהוזחטיכלמנסעפצקרשתךםןףץ')
BANNED_HE = {'מלחמה','לבנון','עזה','ירי','טיל','אזעקה','חטופים','פיגוע','נפגעים','הרוגים','פוליטיקה','צה"ל','חמאס','הפגזה','פצועים'}

def is_hebrew(text, threshold=0.10):
    if not text: return False
    t = text.strip()
    if not t: return False
    heb = sum(1 for c in t if c in HEBREW_CHARS)
    return heb / len(t) >= threshold

def is_banned(text):
    return any(w in (text or '') for w in BANNED_HE)

def strip_cdata(raw_bytes):
    s = raw_bytes.decode('utf-8', 'replace')
    s = re.sub(r'<!\[CDATA\[', '', s)
    s = re.sub(r'\]\]>', '', s)
    return s.encode('utf-8')

def parse_rss(url, max_items=15):
    """Parse RSS. Returns list of (title, desc, link, image)."""
    import xml.etree.ElementTree as ET
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        raw = urllib.request.urlopen(req, timeout=10).read()
        root = ET.fromstring(strip_cdata(raw))
        results = []
        for item in root.iter('item'):
            t_el = item.find('title')
            d_el = item.find('description')
            l_el = item.find('link')
            # Use itertext() to handle mixed content / tail text
            title = ''.join(t_el.itertext()).strip() if t_el is not None else ''
            desc  = ''.join(d_el.itertext()).strip() if d_el is not None else ''
            link  = l_el.text.strip() if l_el is not None and l_el.text else ''
            # Extract image from RSS media tags
            img = None
            for ns in ['', '{http://search.yahoo.com/mrss/}']:
                mc = item.find(f'{ns}content')
                if mc is not None and mc.get('url'):
                    img = mc.get('url'); break
            if not img:
                enc = item.find('enclosure')
                if enc is not None and 'image' in enc.get('type',''):
                    img = enc.get('url')
            # Clean description HTML and extract inline image
            raw_desc = desc
            if not img:
                m = re.search(r'src=["\']?(https?://\S+?\.(?:jpg|jpeg|png|webp))["\'\s>]', raw_desc, re.I)
                if m: img = m.group(1)
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = html_lib.unescape(desc).strip()[:400]
            if title:
                results.append((title, desc, link, img))
            if len(results) >= max_items: break
        return results
    except Exception as e:
        print(f"RSS error {url}: {e}")
        return []

def fetch_article_meta(url, timeout=4):
    """Fetch og:image and og:description from article page."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        page = urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8','replace')
        img_m = (re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', page) or
                 re.search(r'<meta[^>]+name="twitter:image"[^>]+content="([^"]+)"', page) or
                 re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', page))
        desc_m = (re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', page) or
                  re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', page) or
                  re.search(r'<meta[^>]+content="([^"]+)"[^>]+name="description"', page))
        return (
            img_m.group(1) if img_m else None,
            html_lib.unescape(desc_m.group(1)) if desc_m else None
        )
    except:
        return None, None

def translate_he(text, max_chars=400):
    """Translate any language → Hebrew via Google Translate (unofficial)."""
    if not text or is_hebrew(text): return text
    try:
        url = ('https://translate.googleapis.com/translate_a/single'
               '?client=gtx&sl=auto&tl=he&dt=t&q=' + urllib.parse.quote(text[:max_chars]))
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = json.loads(urllib.request.urlopen(req, timeout=5).read())
        return ''.join(p[0] for p in res[0] if p[0])
    except Exception as e:
        print(f"Translate error: {e}")
        return text

# === Deduplication cache ===
CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', 'cache', 'sent_items.json')

def load_cache():
    try:
        with open(CACHE_FILE, encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_today_key():
    return datetime.now(pytz.timezone('Asia/Jerusalem')).strftime('%Y-%m-%d')

def current_session():
    return 'morning' if datetime.now(pytz.timezone('Asia/Jerusalem')).hour < 13 else 'evening'

def is_seen_morning(title, cache):
    day = cache.get(get_today_key(), {})
    return title in day.get('morning', [])

def mark_sent(titles, cache, session):
    key = get_today_key()
    if key not in cache:
        cache[key] = {'morning': [], 'evening': []}
    existing = cache[key].get(session, [])
    cache[key][session] = list(set(existing + [t for t in titles if t and t != '—']))
    for old in sorted(cache.keys())[:-7]:
        del cache[old]
    return cache
