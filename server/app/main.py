import hmac
import os
import secrets
import shutil
import sqlite3
import tempfile
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import db, render

HERE = os.path.dirname(__file__)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
SECRET = os.environ.get('SESSION_SECRET') or secrets.token_hex(32)
SECURE_COOKIE = os.environ.get('SECURE_COOKIE', '1') == '1'

SECTIONS = [('books', 'Книги'), ('prose', 'Повести и рассказы'), ('plays', 'Пьесы')]
LANGS = {'ru': 'На русском', 'lez': 'На лезгинском', 'mix': 'Лезгинский и русский'}
STYLES = {'prose': 'Проза', 'verse': 'Стихи', 'play': 'Пьеса'}
VISIBILITY = {'excerpt': 'Только начало', 'full': 'Полный текст', 'hidden': 'Скрыто'}

@asynccontextmanager
async def lifespan(app):
    db.init()
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET, same_site='strict', https_only=SECURE_COOKIE,
                   session_cookie='admin_session', max_age=60 * 60 * 24 * 14)
app.mount('/static', StaticFiles(directory=os.path.join(HERE, 'static')), name='static')
templates = Jinja2Templates(directory=os.path.join(HERE, 'templates'))
templates.env.globals.update(LANGS=LANGS, STYLES=STYLES, VISIBILITY=VISIBILITY, SECTIONS=SECTIONS,
                             plural=render.plural)


def is_admin(request):
    return request.session.get('admin') is True


def require_admin(request):
    if not is_admin(request):
        raise HTTPException(status_code=303, headers={'Location': '/admin/login'})


def back(url):
    return RedirectResponse(url, status_code=303)


def stats_list(value, count):
    out = []
    for line in value.splitlines():
        if '|' in line:
            num, label = line.split('|', 1)
            out.append((num.strip().replace('{count}', str(count)), label.strip()))
    return out


# ---------- Public site ----------

@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    with db.session() as c:
        s = db.settings(c)
        if s.get('photo') and not c.execute('SELECT 1 FROM files WHERE name = ?', (s['photo'],)).fetchone():
            s['photo'] = ''
        works = c.execute("SELECT * FROM works WHERE visibility != 'hidden' ORDER BY section, position, id").fetchall()
        timeline = c.execute('SELECT * FROM timeline ORDER BY position, id').fetchall()
    groups = {k: [] for k, _ in SECTIONS}
    for w in works:
        chars = render.char_count(w['body'])
        groups.setdefault(w['section'], []).append({**dict(w), 'pages': render.pages(chars)})
    return templates.TemplateResponse(request, 'index.html', {
        's': s, 'groups': groups, 'timeline': timeline,
        'stats': stats_list(s.get('stats', ''), len(works)),
    })


@app.get('/read/{slug}', response_class=HTMLResponse)
def read(request: Request, slug: str):
    slug = slug.removesuffix('.html')
    with db.session() as c:
        s = db.settings(c)
        w = c.execute('SELECT * FROM works WHERE slug = ?', (slug,)).fetchone()
        if not w or (w['visibility'] == 'hidden' and not is_admin(request)):
            raise HTTPException(404)
        siblings = c.execute("SELECT slug, title FROM works WHERE section = ? AND visibility != 'hidden' ORDER BY position, id",
                             (w['section'],)).fetchall()
    full = w['visibility'] == 'full'
    toc_titles = render.headings(w['body'])
    body = w['body'] if full else render.excerpt(w['body'], w['excerpt_chars'])
    body, heads = render.with_ids(body)
    idx = next((i for i, x in enumerate(siblings) if x['slug'] == slug), None)
    prev_w = siblings[idx - 1] if idx else None
    next_w = siblings[idx + 1] if idx is not None and idx + 1 < len(siblings) else None
    return templates.TemplateResponse(request, 'read.html', {
        's': s, 'w': w, 'body': body, 'full': full, 'heads': heads, 'toc_titles': toc_titles,
        'pages': render.pages(render.char_count(w['body'])), 'prev': prev_w, 'next': next_w,
    })


# Old static links from GitHub Pages: /read/slug.html and /index.html
@app.get('/index.html')
def index_html():
    return back('/')


@app.get('/uploads/{name}')
def uploads(name: str):
    with db.session() as c:
        f = c.execute('SELECT mime, data FROM files WHERE name = ?', (os.path.basename(name),)).fetchone()
    if not f:
        raise HTTPException(404)
    return Response(f['data'], media_type=f['mime'], headers={'Cache-Control': 'public, max-age=86400'})


# ---------- Admin: login ----------

_attempts = {}


@app.get('/admin/login', response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, 'admin/login.html', {'error': None, 'configured': bool(ADMIN_PASSWORD)})


@app.post('/admin/login')
def login(request: Request, password: str = Form('')):
    ip = request.client.host if request.client else '-'
    now = time.time()
    recent = [t for t in _attempts.get(ip, []) if now - t < 600]
    if len(recent) >= 10:
        return templates.TemplateResponse(request, 'admin/login.html',
                                          {'error': 'Слишком много попыток. Попробуйте через 10 минут.', 'configured': True}, status_code=429)
    if ADMIN_PASSWORD and hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode()):
        request.session.clear()
        request.session['admin'] = True
        _attempts.pop(ip, None)
        return back('/admin')
    _attempts[ip] = recent + [now]
    return templates.TemplateResponse(request, 'admin/login.html',
                                      {'error': 'Неверный пароль.', 'configured': bool(ADMIN_PASSWORD)}, status_code=401)


@app.post('/admin/logout')
def logout(request: Request):
    request.session.clear()
    return back('/')


# ---------- Admin: works ----------

@app.get('/admin', response_class=HTMLResponse)
def dashboard(request: Request, saved: str = ''):
    require_admin(request)
    with db.session() as c:
        works = c.execute('SELECT * FROM works ORDER BY section, position, id').fetchall()
    groups = {k: [] for k, _ in SECTIONS}
    for w in works:
        groups.setdefault(w['section'], []).append(w)
    return templates.TemplateResponse(request, 'admin/dashboard.html', {'groups': groups, 'saved': saved})


def _form_fields(title, subtitle, section, lang, style, color, visibility, excerpt_chars):
    if section not in dict(SECTIONS) or lang not in LANGS or style not in STYLES or visibility not in VISIBILITY:
        raise HTTPException(400, 'Неверное значение в форме')
    return {
        'title': title.strip() or 'Без названия', 'subtitle': subtitle.strip(), 'section': section, 'lang': lang,
        'style': style, 'color': max(0, min(7, color)), 'visibility': visibility,
        'excerpt_chars': max(300, min(50000, excerpt_chars)),
    }


async def _body_from(upload, body, style):
    if upload is not None and upload.filename:
        name = upload.filename.lower()
        suffix = '.doc' if name.endswith('.doc') else '.docx' if name.endswith('.docx') else None
        if not suffix:
            raise HTTPException(400, 'Загрузите файл Word: .doc или .docx')
        data = await upload.read()
        if len(data) > 30 * 1024 * 1024:
            raise HTTPException(400, 'Файл больше 30 МБ')
        return render.docx_to_html(data, style, suffix)
    return render.sanitize(body)


@app.get('/admin/works/new', response_class=HTMLResponse)
def new_work(request: Request, section: str = 'books'):
    require_admin(request)
    w = {'id': None, 'slug': '', 'title': '', 'subtitle': '', 'section': section, 'lang': 'ru', 'style': 'prose',
         'color': 0, 'visibility': 'excerpt', 'excerpt_chars': 2200, 'body': ''}
    return templates.TemplateResponse(request, 'admin/work.html', {'w': w, 'error': None})


@app.post('/admin/works/new')
async def create_work(request: Request, title: str = Form(''), subtitle: str = Form(''), section: str = Form('books'),
                      lang: str = Form('ru'), style: str = Form('prose'), color: int = Form(0),
                      visibility: str = Form('excerpt'), excerpt_chars: int = Form(2200), body: str = Form(''),
                      docx: UploadFile | None = File(None)):
    require_admin(request)
    f = _form_fields(title, subtitle, section, lang, style, color, visibility, excerpt_chars)
    f['body'] = await _body_from(docx, body, style)
    with db.session() as c:
        base = render.slugify(f['title'])
        slug, n = base, 2
        while c.execute('SELECT 1 FROM works WHERE slug = ?', (slug,)).fetchone():
            slug, n = f'{base}-{n}', n + 1
        pos = c.execute('SELECT COALESCE(MAX(position), 0) + 1 FROM works WHERE section = ?', (section,)).fetchone()[0]
        cur = c.execute('INSERT INTO works (slug, title, subtitle, section, lang, style, color, visibility, excerpt_chars, body, position) '
                        'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (slug, f['title'], f['subtitle'], f['section'], f['lang'], f['style'], f['color'],
                         f['visibility'], f['excerpt_chars'], f['body'], pos))
        wid = cur.lastrowid
    return back(f'/admin/works/{wid}?saved=1')


@app.get('/admin/works/{wid}', response_class=HTMLResponse)
def edit_work(request: Request, wid: int, saved: str = ''):
    require_admin(request)
    with db.session() as c:
        w = c.execute('SELECT * FROM works WHERE id = ?', (wid,)).fetchone()
    if not w:
        raise HTTPException(404)
    return templates.TemplateResponse(request, 'admin/work.html', {'w': w, 'error': None, 'saved': saved})


@app.post('/admin/works/{wid}')
async def update_work(request: Request, wid: int, title: str = Form(''), subtitle: str = Form(''),
                      section: str = Form('books'), lang: str = Form('ru'), style: str = Form('prose'),
                      color: int = Form(0), visibility: str = Form('excerpt'), excerpt_chars: int = Form(2200),
                      body: str = Form(''), docx: UploadFile | None = File(None)):
    require_admin(request)
    f = _form_fields(title, subtitle, section, lang, style, color, visibility, excerpt_chars)
    f['body'] = await _body_from(docx, body, style)
    with db.session() as c:
        if not c.execute('SELECT 1 FROM works WHERE id = ?', (wid,)).fetchone():
            raise HTTPException(404)
        c.execute("UPDATE works SET title=?, subtitle=?, section=?, lang=?, style=?, color=?, visibility=?, excerpt_chars=?, "
                  "body=?, updated_at=datetime('now') WHERE id=?",
                  (f['title'], f['subtitle'], f['section'], f['lang'], f['style'], f['color'], f['visibility'],
                   f['excerpt_chars'], f['body'], wid))
    return back(f'/admin/works/{wid}?saved=1')


@app.post('/admin/works/{wid}/delete')
def delete_work(request: Request, wid: int):
    require_admin(request)
    with db.session() as c:
        c.execute('DELETE FROM works WHERE id = ?', (wid,))
    return back('/admin?saved=deleted')


@app.post('/admin/works/{wid}/move')
def move_work(request: Request, wid: int, direction: str = Form('up')):
    require_admin(request)
    with db.session() as c:
        w = c.execute('SELECT id, section FROM works WHERE id = ?', (wid,)).fetchone()
        if not w:
            raise HTTPException(404)
        ids = [r['id'] for r in c.execute('SELECT id FROM works WHERE section = ? ORDER BY position, id', (w['section'],))]
        i = ids.index(wid)
        j = i - 1 if direction == 'up' else i + 1
        if 0 <= j < len(ids):
            ids[i], ids[j] = ids[j], ids[i]
        for pos, x in enumerate(ids):
            c.execute('UPDATE works SET position = ? WHERE id = ?', (pos, x))
    return back(f'/admin#w{wid}')


# ---------- Admin: about the author ----------

@app.get('/admin/about', response_class=HTMLResponse)
def about_form(request: Request, saved: str = ''):
    require_admin(request)
    with db.session() as c:
        s = db.settings(c)
        timeline = c.execute('SELECT * FROM timeline ORDER BY position, id').fetchall()
    tl_text = '\n'.join(f"{r['year']} | {r['text']}" for r in timeline)
    return templates.TemplateResponse(request, 'admin/about.html', {'s': s, 'timeline': tl_text, 'saved': saved})


@app.post('/admin/about')
async def about_save(request: Request, name: str = Form(''), eyebrow: str = Form(''), tagline: str = Form(''),
                     quote: str = Form(''), quote_source: str = Form(''), bio_lede: str = Form(''), bio: str = Form(''),
                     stats: str = Form(''), footer: str = Form(''), timeline: str = Form(''),
                     photo: UploadFile | None = File(None)):
    require_admin(request)
    values = {'name': name.strip(), 'eyebrow': eyebrow.strip(), 'tagline': tagline.strip(), 'quote': quote.strip(),
              'quote_source': quote_source.strip(), 'bio_lede': bio_lede.strip(), 'bio': render.sanitize(bio),
              'stats': stats.strip(), 'footer': footer.strip()}
    if photo is not None and photo.filename:
        data = await photo.read()
        if len(data) > 15 * 1024 * 1024:
            raise HTTPException(400, 'Фото больше 15 МБ')
        ext = db.sniff_image(data)
        if not ext:
            raise HTTPException(400, 'Фото должно быть в формате JPG, PNG или WebP. Фото с iPhone (HEIC) сначала сохраните как JPG.')
        fname = f'author-{int(time.time())}{ext}'
        values['photo'] = fname
    with db.session() as c:
        if 'photo' in values:
            c.execute('INSERT INTO files (name, mime, data) VALUES (?, ?, ?)', (fname, db.MIME[ext], data))
        for k, v in values.items():
            c.execute('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value', (k, v))
        c.execute('DELETE FROM timeline')
        for pos, line in enumerate(l for l in timeline.splitlines() if l.strip()):
            year, _, text = line.partition('|')
            c.execute('INSERT INTO timeline (year, text, position) VALUES (?, ?, ?)', (year.strip(), text.strip(), pos))
    return back('/admin/about?saved=1')


# ---------- Admin: backup ----------

@app.get('/admin/backup')
def backup(request: Request):
    require_admin(request)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    tmp.close()
    src = db.connect()
    dst = sqlite3.connect(tmp.name)
    src.backup(dst)
    dst.close()
    src.close()
    stamp = time.strftime('%Y-%m-%d')
    return FileResponse(tmp.name, filename=f'ismailov-site-{stamp}.db', media_type='application/octet-stream')


@app.post('/admin/restore')
async def restore(request: Request, dbfile: UploadFile = File(...)):
    require_admin(request)
    data = await dbfile.read()
    if not data.startswith(b'SQLite format 3\x00'):
        raise HTTPException(400, 'Это не файл резервной копии сайта')
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        tmp.write(data)
    try:
        check = sqlite3.connect(tmp.name)
        check.execute('SELECT slug, title, body FROM works LIMIT 1')
        check.execute('SELECT key, value FROM settings LIMIT 1')
        check.close()
    except sqlite3.Error:
        os.unlink(tmp.name)
        raise HTTPException(400, 'В файле нет данных сайта')
    if os.path.exists(db.DB_PATH):
        shutil.copy(db.DB_PATH, db.DB_PATH + f'.before-restore-{int(time.time())}')
    shutil.move(tmp.name, db.DB_PATH)
    db.init()
    return back('/admin?saved=restored')


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if exc.status_code == 303:
        return RedirectResponse(exc.headers['Location'], status_code=303)
    if request.url.path.startswith('/admin') and exc.status_code == 400:
        return templates.TemplateResponse(request, 'admin/error.html', {'message': exc.detail}, status_code=400)
    return templates.TemplateResponse(request, 'error.html', {'code': exc.status_code}, status_code=exc.status_code)
