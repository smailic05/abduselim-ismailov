"""Text helpers: cleaning HTML from the editor or from Word files, headings, excerpts."""
import re
import subprocess
import tempfile
from collections import Counter

from bs4 import BeautifulSoup, NavigableString

ALLOWED = {'p', 'h2', 'h3', 'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del', 'span', 'a', 'hr', 'blockquote', 'ul', 'ol',
           'li', 'br', 'table', 'tr', 'td', 'th', 'tbody', 'thead', 'tfoot', 'caption', 'colgroup', 'col', 'sup', 'sub'}
BLOCKS = ('p', 'h2', 'h3', 'blockquote', 'ul', 'ol', 'table')
# formatting the editor may set; anything else in style="" is dropped
STYLE_PROPS = {'text-align', 'color', 'background-color', 'font-size', 'font-family', 'font-weight', 'font-style',
               'text-decoration', 'text-indent', 'padding-left', 'margin-left', 'line-height', 'vertical-align',
               'width', 'border-collapse', 'list-style-type'}
STYLE_VALUE = re.compile(r"^[#\w\s.,%'\"()+-]{1,120}$")
LOWER = re.compile(r'[a-zа-яё]')
LETTER = re.compile(r'[A-Za-zА-ЯЁа-яёӀ]')
SKIP = {'АБДУСЕЛИМ ИСМАИЛОВ', 'А Б Д У С Е Л И М И С М А И Л О В', 'ИЛИ', 'К О Н Е Ц', 'КОНЕЦ'}


def norm(t):
    return re.sub(r'\s+', ' ', t.replace('\xa0', ' ')).strip()


def clean_style(style):
    out = []
    for decl in (style or '').split(';'):
        prop, _, value = decl.partition(':')
        prop, value = prop.strip().lower(), value.strip()
        if prop in STYLE_PROPS and STYLE_VALUE.match(value) and not re.search(r'url|expression|javascript', value, re.I):
            out.append(f'{prop}: {value}')
    return '; '.join(out)


def sanitize(html):
    """Keep only simple text formatting, drop scripts, styles, links and attributes."""
    soup = BeautifulSoup(html or '', 'html.parser')
    for tag in soup.find_all(['script', 'style', 'img', 'figure', 'svg', 'iframe', 'object']):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.name in ('h1',):
            tag.name = 'h2'
        elif tag.name in ('h4', 'h5', 'h6'):
            tag.name = 'h3'
        if tag.name not in ALLOWED:
            tag.unwrap()
            continue
        attrs = {k: v for k, v in tag.attrs.items() if k in ('colspan', 'rowspan')}
        style = clean_style(tag.get('style', ''))
        if style:
            attrs['style'] = style
        if tag.name == 'a':
            href = (tag.get('href') or '').strip()
            if re.match(r'^(https?:|mailto:)', href, re.I):
                attrs.update(href=href, rel='noopener', target='_blank')
        tag.attrs = attrs
    # drop empty paragraphs and headings
    for tag in soup.find_all(['p', 'h2', 'h3']):
        if not norm(tag.get_text()) and not tag.find('br'):
            tag.decompose()
    return str(soup).strip()


def _is_heading_text(t):
    if not t or len(t) > 90 or LOWER.search(t):
        return False
    if t[0] in '-–—(«"' or t.endswith(','):
        return False
    if len(LETTER.findall(t)) < 4:
        return False
    return t.strip('*.: ') not in SKIP


def promote_headings(html, style='prose'):
    """Turn all-caps title lines from Word files into h2 headings."""
    soup = BeautifulSoup(html, 'html.parser')
    blocks = soup.find_all(['p', 'h2', 'h3'])
    texts = [norm(b.get_text()) for b in blocks]
    counts = Counter(texts)
    for b, t in zip(blocks, texts):
        if b.parent is None or not t:
            continue
        if b.find_parent(['td', 'li']):
            continue
        cand = _is_heading_text(t) and counts[t] <= 2
        if b.name in ('h2', 'h3') and len(t) <= 90 and t not in SKIP and counts[t] <= 2:
            cand = True
        if cand and style == 'play' and len(t.split()) == 1 and counts[t] > 1:
            cand = False
        if cand:
            b.name = 'h2'
            b.string = t.strip('*')
        elif b.name in ('h2', 'h3'):
            b.name = 'p'
    return str(soup)


def docx_to_html(data, style='prose', suffix='.docx'):
    """Convert an uploaded Word file to clean HTML. Old .doc files go through LibreOffice first."""
    with tempfile.TemporaryDirectory() as d:
        src = f'{d}/in{suffix}'
        with open(src, 'wb') as f:
            f.write(data)
        if suffix == '.doc':
            subprocess.run(['soffice', '--headless', '--convert-to', 'docx', '--outdir', d, src],
                           check=True, capture_output=True, timeout=300)
            src = f'{d}/in.docx'
        out = subprocess.run(['pandoc', src, '-t', 'html5', '--wrap=none'],
                             check=True, capture_output=True, timeout=300)
    return promote_headings(sanitize(out.stdout.decode('utf-8')), style)


def with_ids(html):
    """Give every h2 an id and return (html, [(id, title)])."""
    soup = BeautifulSoup(html, 'html.parser')
    heads = []
    for i, h in enumerate(soup.find_all('h2'), 1):
        h['id'] = f's{i}'
        heads.append((h['id'], norm(h.get_text())))
    return str(soup), heads


def headings(html):
    soup = BeautifulSoup(html, 'html.parser')
    return [norm(h.get_text()) for h in soup.find_all('h2')]


def excerpt(html, limit):
    """Return roughly the first `limit` characters of text, cut at a block boundary."""
    soup = BeautifulSoup(html, 'html.parser')
    seen, cut = 0, False
    for el in list(soup.contents):
        if cut:
            el.extract()
            continue
        if isinstance(el, NavigableString):
            continue
        if el.name in ('p', 'blockquote', 'ul', 'ol', 'table'):
            seen += len(norm(el.get_text()))
            if seen >= limit:
                cut = True
    return str(soup)


def char_count(html):
    return len(norm(BeautifulSoup(html, 'html.parser').get_text()))


def pages(chars):
    return max(1, round(chars / 1800))


def plural(n, forms):
    n = abs(n) % 100
    if 11 <= n <= 19:
        return forms[2]
    n %= 10
    return forms[0] if n == 1 else forms[1] if 2 <= n <= 4 else forms[2]


def slugify(title):
    table = str.maketrans({'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z',
                           'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
                           'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                           'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya', 'ӏ': '', 'i': 'i'})
    s = title.lower().translate(table)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s or 'work'
