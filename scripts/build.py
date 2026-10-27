#!/usr/bin/env python3
"""Genera il sito statico di IntermarketAndMore.

Legge il feed RSS del blog su FinanzaOnline e il feed del canale YouTube,
aggiorna l'archivio in data/ e riscrive index.html e focus-mercati/index.html.
Solo libreria standard. Uso: python3 scripts/build.py [--offline] [--pages N]
"""
import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ROME = ZoneInfo("Europe/Rome")

BLOG = "https://intermarketandmore.finanzaonline.com"
BLOG_FEED = BLOG + "/feed"
YT_CHANNEL_ID = "UCh5nSWks5XPovipy2vFtpBg"
YT_FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=" + YT_CHANNEL_ID
YT_CHANNEL = "https://www.youtube.com/channel/" + YT_CHANNEL_ID
INSTAGRAM = "https://www.instagram.com/intermarketandmore/"
BOOK_IT = "https://www.amazon.it/dp/B0GFXYXVMH"
LINKEDIN = "https://www.linkedin.com/in/danilo-riboldi-637421b/"
X_URL = "https://x.com/intermarketblog"
BOOK_EN = "https://www.amazon.com/dp/B0HD117W42"
UA = "Mozilla/5.0 (compatible; IntermarketAndMore-site-builder/1.0)"

MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
          "agosto", "settembre", "ottobre", "novembre", "dicembre"]
CATS = [("all", "Tutte"), ("mercati", "Analisi mercati"), ("trends", "TRENDS"), ("tecnica", "Analisi tecnica")]
CAT_LABEL = dict(CATS)

e = html.escape


# ------------------------------------------------------------------ fetch

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def clean_text(s, limit=200):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"The post .*? appeared first on .*$", "", s, flags=re.S)
    s = re.sub(r"\s*\[(…|&#8230;|\.\.\.)\]\s*$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0].rstrip(",;:.") + "…"
    return s


def classify(categories):
    low = [c.lower() for c in categories]
    if any("trends" in c for c in low):
        return "trends"
    if any(c in ("analisi tecnica", "trading room") for c in low):
        return "tecnica"
    return "mercati"


def parse_blog(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        if not link:
            continue
        pub = it.findtext("pubDate")
        try:
            when = email.utils.parsedate_to_datetime(pub).astimezone(ROME)
        except Exception:
            continue
        cats = [c.text or "" for c in it.findall("category")]
        out.append({
            "link": link,
            "title": html.unescape((it.findtext("title") or "").strip()),
            "date": when.isoformat(),
            "cat": classify(cats),
            "excerpt": clean_text(it.findtext("description")),
        })
    return out


NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}


def parse_youtube(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for en in root.findall("a:entry", NS):
        vid = en.findtext("yt:videoId", namespaces=NS)
        title = en.findtext("a:title", namespaces=NS) or ""
        if not vid or "focus mercati" not in title.lower():
            continue
        desc = en.findtext("media:group/media:description", namespaces=NS) or ""
        out.append({"id": vid, "title": title.strip(), "published": en.findtext("a:published", namespaces=NS),
                    "description": desc.strip()})
    return out


def merge(old, new, key):
    by = {x[key]: x for x in old}
    for x in new:
        by[x[key]] = {**by.get(x[key], {}), **x}
    return list(by.values())


def load(name):
    p = DATA / name
    return json.loads(p.read_text("utf-8")) if p.exists() else []


def save(name, items):
    DATA.mkdir(exist_ok=True)
    (DATA / name).write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", "utf-8")


def update(pages):
    posts, videos = load("posts.json"), load("videos.json")
    got_blog = []
    for n in range(1, pages + 1):
        url = BLOG_FEED + ("" if n == 1 else f"?paged={n}")
        try:
            batch = parse_blog(fetch(url))
        except Exception as ex:
            print(f"blog feed page {n}: {ex}", file=sys.stderr)
            break
        if not batch:
            break
        got_blog += batch
    posts = merge(posts, got_blog, "link")
    try:
        videos = merge(videos, parse_youtube(fetch(YT_FEED)), "id")
    except Exception as ex:
        print(f"youtube feed: {ex}", file=sys.stderr)
    posts.sort(key=lambda p: p["date"], reverse=True)
    videos.sort(key=lambda v: v.get("published") or "", reverse=True)
    save("posts.json", posts)
    save("videos.json", videos)
    print(f"blog: {len(got_blog)} letti, {len(posts)} in archivio; video: {len(videos)} in archivio")
    return posts, videos


# ------------------------------------------------------------------ helpers

def ddmmyyyy(iso):
    d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ROME)
    return d.strftime("%d/%m/%Y")


def edition_date(v):
    m = re.search(r"(\d{2}/\d{2}/\d{4})", v["title"])
    return m.group(1) if m else ddmmyyyy(v["published"])


def edition_month(v):
    d, m, y = edition_date(v).split("/")
    return f"{y}-{m}", f"{MONTHS[int(m) - 1].capitalize()} {y}"


def headlines(v):
    lines = []
    for ln in (v.get("description") or "").splitlines():
        ln = ln.strip().lstrip("•-–·*").strip()
        if not ln:
            continue
        if ln.lower().startswith(("fonti", "contenuto informativo", "http")):
            break
        lines.append(ln)
    return lines[:6]


PLAY = ('<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#F3F4F1" stroke-width="2" '
        'stroke-linejoin="round" aria-hidden="true"><path d="M7 5l12 7-12 7z"/></svg>')


def player(v, base):
    if not v:
        return ('<div class="player"><div class="empty-player"><b>FOCUS MERCATI</b>'
                '<span>Le edizioni arrivano qui ogni mattina, dal lunedì al sabato.</span></div></div>')
    return (f'<div class="player"><button class="facade" type="button" data-yt="{e(v["id"])}" '
            f'data-title="{e(v["title"])}" aria-label="Guarda {e(v["title"])}">'
            f'<span class="tag">ULTIMA EDIZIONE</span><span class="play">{PLAY}</span>'
            f'<span class="meta"><b>FOCUS MERCATI</b><span>Edizione del {e(edition_date(v))}</span><br>'
            f'<small>Il video si carica da YouTube al clic.</small></span></button></div>')


def vcard(v, month_attr=False):
    attr = f' data-month="{edition_month(v)[0]}"' if month_attr else ""
    heads = headlines(v)
    sub = heads[0] if heads else v["title"]
    return (f'<a class="vcard" href="https://www.youtube.com/watch?v={e(v["id"])}"{attr}>'
            f'<div class="thumb"><span>FOCUS MERCATI</span>{PLAY}</div>'
            f'<div><p class="date">Edizione del {e(edition_date(v))}</p><p class="title">{e(sub)}</p></div></a>')


def head(title, desc, base, canonical_path):
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<link rel="icon" href="{base}assets/logo.png">
<link rel="preload" href="{base}assets/fonts/archivo-latin-800-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{base}assets/style.css">
</head>
<body>"""


def header(base, current):
    def a(href, label, key):
        cur = ' aria-current="page"' if key == current else ""
        return f'<a href="{href}"{cur}>{label}</a>'
    return f"""<header class="site-header"><div class="wrap">
<a class="logo" href="{base}" aria-label="IntermarketAndMore – home"><img src="{base}assets/logo.png" alt="intermarket &amp; more – trading e finanza a 360°" width="253" height="52"></a>
<nav class="nav" aria-label="Navigazione principale">
{a(base + "focus-mercati/", "Focus Mercati", "fm")}
<a href="{BLOG}">Analisi ↗</a>
{a(base + "#metodo", "Metodo Fusion", "")}
{a(base + "#libro", "Il libro", "")}
{a(base + "#chi-sono", "Chi sono", "")}
</nav></div></header>"""


def footer(base):
    year = dt.datetime.now(ROME).year
    return f"""<footer class="site-footer"><div class="wrap">
<img src="{base}assets/logo.png" alt="IntermarketAndMore" width="195" height="40">
<p>I contenuti di questo sito hanno finalità esclusivamente informative e non costituiscono consulenza finanziaria, raccomandazione personalizzata né sollecitazione all’investimento. Le opinioni espresse sono personali. I video Focus Mercati sono realizzati con strumenti di intelligenza artificiale.</p>
<p>Questo sito non usa cookie né strumenti di tracciamento. I video di YouTube si caricano solo quando li avvii, dal dominio youtube-nocookie.com.</p>
<p class="mono">© {year} IntermarketAndMore · <a href="{BLOG}">Blog</a> · <a href="{YT_CHANNEL}">YouTube</a> · <a href="{LINKEDIN}">LinkedIn</a> · <a href="{X_URL}">X</a> · <a href="{INSTAGRAM}">Instagram</a></p>
</div></footer>
<script src="{base}assets/site.js" defer></script>
</body>
</html>
"""


# ------------------------------------------------------------------ pages

LENSES = [
    ("01", "Value investing", "Cosa vale un asset rispetto al prezzo a cui tratta."),
    ("02", "Analisi tecnica", "Dove sta il prezzo e cosa dice il suo comportamento."),
    ("03", "Analisi intermarket", "Come si influenzano azioni, tassi, valute e materie prime."),
    ("04", "Finanza comportamentale", "Quanto pesano emozioni e posizionamento degli investitori."),
]


def render_home(posts, videos):
    base = ""
    latest = videos[0] if videos else None
    eds = "".join(vcard(v) for v in videos[:6]) if videos else ""
    eds_block = (f'<div class="grid-cards">{eds}</div>' if eds else
                 '<p class="empty-note">Le prime edizioni del TG arriveranno qui a breve, ogni mattina dal lunedì al sabato.</p>')
    filters = "".join(f'<button class="pill" type="button" data-filter="{k}" aria-pressed="{"true" if k == "all" else "false"}">{lbl}</button>' for k, lbl in CATS)
    rows = "".join(
        f'<a class="post" href="{e(p["link"])}" data-cat="{p["cat"]}"><div class="when"><time datetime="{e(p["date"][:10])}">{ddmmyyyy(p["date"])}</time>'
        f'<span>{CAT_LABEL[p["cat"]]}</span></div><div class="what"><b>{e(p["title"])}</b>'
        + (f'<span>{e(p["excerpt"])}</span>' if p.get("excerpt") else "") + '</div></a>'
        for p in posts)
    lenses = "".join(f'<div class="lens"><span class="n">{n}</span><h3>{t}</h3><p>{d}</p></div>' for n, t, d in LENSES)
    return head("IntermarketAndMore – analisi macro e intermarket",
                "Analisi macro e intermarket indipendente: il TG Focus Mercati, le analisi del blog e il Metodo Fusion di Danilo Riboldi.",
                base, "") + header(base, "home") + f"""
<main>
<section class="dark hero"><div class="wrap">
<div class="hero-text">
<p class="kicker">Analisi macro e intermarket indipendente</p>
<h1>I mercati non si muovono da soli. Si muovono insieme.</h1>
<p class="lead">Azioni, tassi, valute e materie prime letti come un unico sistema. Da oltre vent’anni, con il Metodo Fusion.</p>
<div class="actions"><a class="btn btn-accent" href="focus-mercati/">Guarda l’ultimo Focus Mercati</a><a class="btn btn-ghost-dark" href="{BLOG}">Leggi le analisi sul blog ↗</a></div>
</div>
<div class="hero-media">{player(latest, base)}</div>
</div></section>

<section class="block" aria-labelledby="fm-title"><div class="wrap">
<div class="block-head"><div><p class="kicker">Video · dal lunedì al sabato</p><h2 id="fm-title">Focus Mercati</h2></div>
<a class="more" href="focus-mercati/">Tutte le edizioni →</a></div>
{eds_block}
</div></section>

<section class="block" aria-labelledby="blog-title" style="padding-top:0"><div class="wrap">
<div class="block-head top-rule"><div><p class="kicker">Dal blog</p><h2 id="blog-title">Le ultime analisi</h2></div>
<a class="more" href="{BLOG}">Vai al blog ↗</a></div>
<div class="filters" role="group" aria-label="Filtra per rubrica">{filters}</div>
<div class="posts" id="posts">{rows}</div>
<div class="posts-foot"><span>Aggiornato automaticamente dal blog su FinanzaOnline.</span>
<button class="btn btn-ghost" type="button" id="more-posts">Carica altre analisi</button></div>
</div></section>

<section class="block metodo" id="metodo" aria-labelledby="metodo-title"><div class="wrap">
<div class="intro"><p class="kicker">Il metodo</p><h2 id="metodo-title">Metodo Fusion</h2>
<p>Quattro lenti sullo stesso mercato. Nessuna basta da sola: il segnale nasce quando convergono.</p></div>
<div class="lenses">{lenses}</div>
</div></section>

<section class="block" id="libro" aria-labelledby="libro-title"><div class="wrap split">
<div class="book-cover" aria-hidden="true"><span>IL LIBRO</span><b>La Danza dei Mercati</b><span>DANILO RIBOLDI</span></div>
<div class="side">
<p class="kicker">Il libro</p>
<h2 id="libro-title">La Danza dei Mercati</h2>
<p>Il Metodo Fusion raccontato per intero: gli strumenti proprietari, le quattro lenti e la storia di Marco e Giulia che li mette alla prova sui mercati.</p>
<div class="actions"><a class="btn btn-dark" href="{BOOK_IT}">Edizione italiana su Amazon ↗</a><a class="btn btn-ghost" href="{BOOK_EN}">English edition ↗</a></div>
</div>
</div></section>

<section class="block about" id="chi-sono" aria-labelledby="chi-title"><div class="wrap split">
<div class="monogram" aria-hidden="true">DR</div>
<div class="side">
<p class="kicker">Chi sono</p>
<h2 id="chi-title">Danilo Riboldi</h2>
<p>Da oltre vent’anni curo IntermarketAndMore, piattaforma indipendente di analisi macro e finanziaria. Ideatore del Metodo Fusion e autore de “La Danza dei Mercati”.</p>
<div class="links"><a href="{YT_CHANNEL}">YouTube ↗</a><a href="{LINKEDIN}">LinkedIn ↗</a><a href="{X_URL}">X ↗</a><a href="{INSTAGRAM}">Instagram ↗</a><a href="{BLOG}">Blog ↗</a></div>
</div>
</div></section>
</main>
""" + footer(base)


def render_focus(videos):
    base = "../"
    latest = videos[0] if videos else None
    if latest:
        heads = headlines(latest)
        items = "".join(f"<li>{e(h)}</li>" for h in heads) or f"<li>{e(latest['title'])}</li>"
        ed = (f'<div class="ed"><p class="d">Edizione del {e(edition_date(latest))}</p><h2>In questa edizione</h2>'
              f'<ol>{items}</ol><p class="src">Fonti indicate nei titoli di coda del video.</p></div>')
    else:
        ed = ('<div class="ed"><h2>Ogni mattina, i mercati in pochi minuti</h2>'
              '<p class="d">Le notizie che contano per i portafogli: fatti, lettura alternativa, implicazioni.</p></div>')
    months = []
    for v in videos:
        m = edition_month(v)
        if m not in months:
            months.append(m)
    mf = ('<button class="pill" type="button" data-mfilter="all" aria-pressed="true">Tutte</button>'
          + "".join(f'<button class="pill" type="button" data-mfilter="{k}" aria-pressed="false">{lbl}</button>' for k, lbl in months))
    cards = "".join(vcard(v, True) for v in videos)
    archive = (f'<div class="filters" role="group" aria-label="Filtra per mese">{mf}</div><div class="grid-cards">{cards}</div>'
               if videos else '<p class="empty-note">L’archivio si riempie da solo a ogni nuova edizione pubblicata su YouTube.</p>')
    return head("Focus Mercati – il TG dei mercati | IntermarketAndMore",
                "Focus Mercati, il TG dei mercati di IntermarketAndMore: dal lunedì al sabato le notizie che contano per i portafogli.",
                base, "focus-mercati/") + header(base, "fm") + f"""
<main>
<section class="dark cat-hero"><div class="wrap">
<div class="block-head" style="margin:0">
<div style="max-width:640px"><p class="kicker">Il TG dei mercati · dal lunedì al sabato</p><h1>Focus Mercati</h1>
<p class="lead" style="margin:10px 0 0;font-size:19px;color:var(--on-dark-2)">Le notizie che contano per i portafogli, in pochi minuti. Fatti, lettura alternativa, implicazioni.</p></div>
<a class="btn btn-accent" href="{YT_CHANNEL}?sub_confirmation=1">Iscriviti al canale YouTube ↗</a>
</div>
<div class="cat-row">{player(latest, base)}{ed}</div>
</div></section>

<section class="block" aria-labelledby="archivio-title"><div class="wrap">
<div class="block-head"><h2 id="archivio-title">Archivio edizioni</h2></div>
{archive}
</div></section>
</main>
""" + footer(base)


def main():
    offline = "--offline" in sys.argv
    pages = 2
    if "--pages" in sys.argv:
        pages = int(sys.argv[sys.argv.index("--pages") + 1])
    if offline:
        posts, videos = load("posts.json"), load("videos.json")
    else:
        posts, videos = update(pages)
    (ROOT / "index.html").write_text(render_home(posts, videos), "utf-8")
    (ROOT / "focus-mercati").mkdir(exist_ok=True)
    (ROOT / "focus-mercati" / "index.html").write_text(render_focus(videos), "utf-8")
    print("pagine generate")


if __name__ == "__main__":
    main()
