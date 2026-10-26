"""Fill a fresh database from the Word files converted with pandoc (one <drive-id>.html per work).

Usage: python -m tools.seed <html_dir> <author_photo.jpg>
Run from the server/ folder. Writes data/site.db (and data/uploads/author.jpg).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app import db, render  # noqa: E402

# slug, Google Drive file id, title, subtitle, lang, style
BOOKS = [
    ('veshchiy-son', '1y5-GRXxE1cf5lzSt_V9N7_M3S4srG-SA', 'Вещий сон', 'Повести и рассказы. Перевод с лезгинского', 'ru', 'prose'),
    ('vo-veki-vekov', '1WfZzHsZ303ttEUldTs4pvg6SWsxh5VnO', 'Во веки веков', 'Рассказы, новеллы и публицистика', 'ru', 'prose'),
    ('lastochkin-dom', '1DMd5ZWwXtRPimarRdztbJDF-QVE1cC0B', 'Ласточкин дом', 'Книга для детей: стихи, сказки, поэма «Дедушкин май»', 'ru', 'verse'),
    ('everzava-emina-zaz', '17uXIiv6bN7sK8j0Pn2topRlygnVwtV3s', 'Эверзава Эмина заз', 'Шиирар, поэмаяр, драма · Махачкала, 2009', 'lez', 'verse'),
    ('vahtarin-kyul', '12sRDegAKGaZWeFsd_ahQDBFjAiyGbCd2', 'Вахтарин кьуьл', 'Шиирар ва поэмаяр', 'lez', 'verse'),
    ('terg-hayibur', '1y9lZ34rM9QhPg63wafbH6btv2yAYekoo', 'Терг хьайибур', 'Рассказар, гьикаяяр, повестар ва пьесаяр', 'lez', 'prose'),
    ('sto-priznaniy', '1xrHfTAoAtyyZHbj_wMgM0G3inbGut6ie', 'Сто признаний в любви', 'Стихи о любви', 'lez', 'verse'),
    ('samurdin-lepeyar', '1_ecE2V4ebiB8KyvnBbzHX123LKRjuSP0', 'Самурдин лепеяр', '«Волны Самура». Песни и стихи для детей', 'mix', 'verse'),
]
PROSE = [
    ('prodelki-shaytana', '1R3m3b2j-i6lTlUa4rcxD6pB-3TjYkIg4', 'Проделки шайтана', 'Повесть об оскорбленном духе и о времени, сошедшем с ума', 'ru', 'prose'),
    ('veshchiy-son-povest', '1mP5SMrK-xQSrqGDYPeBKAVRyJTUv1Iw3', 'Вещий сон', 'Повесть', 'ru', 'prose'),
    ('moy-belyy-kon', '1ErMPadXGv9ARGGafvbWcF36Evt5OCLJj', 'Мой белый конь', 'Повесть', 'ru', 'prose'),
    ('posledniy-voy', '1DHgW38-gugYKid2NY_QK3C2YkbfPIzJd', 'Последний вой', 'Повесть', 'ru', 'prose'),
    ('trevozhnye-besedy', '12gYqpdlHXyTaP-GnoE1B813ueV9rLCol', 'Тревожные беседы', 'Повесть', 'ru', 'prose'),
    ('gvedek', '10ZKgFIbND6hRbkg8mxIRwLNc49f-o5v-', 'Гведек', 'Рассказ', 'ru', 'prose'),
    ('most-amahana', '1hNGNHYMuKUMkTxBtJcINxESoe2yrWtEr', 'Мост Амахана', 'Рассказ', 'ru', 'prose'),
    ('svadba-karatista', '1cAD_RaCqZuUor5_J1s-NwW_xUJvcmcmS', 'Свадьба каратиста', 'Рассказ', 'ru', 'prose'),
    ('shelkovica', '1xewyU_A7Uu448hivSy7JKNnzxx1D3xux', 'Шелковица старухи Залму', 'Рассказ', 'ru', 'prose'),
    ('legenda', '13fQvQLhX3cdowy-4WdI0H16yhZ7iplc0', 'Легенда о Говорящем камне и шахе Албурзе', 'Легенда', 'ru', 'prose'),
    ('kuchi-kamney', '1EbVvayP3G1Vlv_yFq-3fOAbPJt93_1GE', 'Кучи камней. Кровь жеребца. Убийца', 'Рассказы', 'ru', 'prose'),
    ('mgnoveniya', '1XppSU5lgwNgbjr-NjImWx74cNXp8fUmG', 'Мгновения', 'Короткие новеллы', 'ru', 'prose'),
]
PLAYS = [
    ('chigali', '1sJFgX56LrlCxgReKvBtBwY6AFnDyQHeS', 'Чигали', 'Сказка в двух действиях. Перевод с лезгинского', 'ru', 'play'),
    ('mamrachrin-bagda-yif', '1P_gnKll2ZLIi_r3rMEEXLz0JxBxCIvZS', 'Мамрачрин багъда йиф', 'Драма о поэте Етиме Эмине', 'lez', 'play'),
    ('pud-yug', '1PvG1cgqxzcjc9tNSgEZJy1buQAEel1km', 'Пуд югъ', 'Драма в двух частях', 'lez', 'play'),
    ('kiri-buba', '1fxA9_-RJJw5w9R_b2PeSgY8VD0D9JqJp', 'КӀири буба', 'Драма', 'lez', 'play'),
    ('karachiyar', '1mMrvaA8tHzzcutRvtQMHe-jnR0zVl1Fw', 'Къарачияр', 'Драма', 'lez', 'play'),
    ('dustagda-meher', '1HFpRCLUw7ALiHVkU_UxnW3CwegsijUWO', 'Дустагъда мехъер', 'Пьеса', 'lez', 'play'),
    ('kval-hitkinna', '1CBUDI317C_aXQgWccrhsXwH2yTp4Y02D', 'КӀвал хъиткьинна', 'Пьеса', 'lez', 'play'),
]

SECTIONS = [('books', BOOKS), ('prose', PROSE), ('plays', PLAYS)]

SETTINGS = {
    'name': 'Абдуселим Исмаилов',
    'eyebrow': 'Народный писатель Дагестана',
    'tagline': 'Лезгинский поэт, прозаик и драматург. Стихи, повести, рассказы и пьесы на родном языке и в переводе на русский.',
    'quote': 'Детство — это конь под седлом, всегда готовый к твоим услугам. Держись за свое детство',
    'quote_source': 'Из повести «Мой белый конь»',
    'bio_lede': 'Заслуженный деятель искусств и народный писатель Республики Дагестан.',
    'bio': (
        '<p>Абдуселим Абумислимович Исмаилов — дагестанский поэт, прозаик и драматург, лезгин по национальности. '
        'Родился 16 декабря 1947 года в селе Келе Магарамкентского района Дагестана. Окончил филологический факультет '
        'Дагестанского государственного университета.</p>'
        '<p>Работал учителем в школе, редактором Дагестанского радио, заведовал отделом республиканской газеты «Коммунист», '
        'был редактором литературного журнала «Самур» и заместителем главного редактора журналов «Соколёнок» и '
        '«Литературный Дагестан». Член Союза писателей России.</p>'
        '<p>Пишет на лезгинском языке. Его проза в переводе на русский вошла в альманахи «Лира Кавказа», «Голос Кавказа» и '
        '«Дагестан литературный», публикуется в журнале «Дагестан». Стихи, поэмы, рассказы и повести переведены на языки '
        'народов Дагестана и включены в программы школ и вузов, где изучается литература на языках Дагестана.</p>'
        '<p>Автор более двадцати поэтических и прозаических книг на родном и русском языках и восьми пьес, поставленных '
        'на сцене национального театра.</p>'),
    'stats': '1947 | год рождения\n20+ | книг на лезгинском и русском\n8 | пьес на сцене национального театра\n{count} | произведений на этом сайте',
    'footer': 'Тексты из семейного архива писателя. Полные версии произведений хранятся в семье автора.',
}

TIMELINE = [
    ('1947', '16 декабря родился в селе Келе Магарамкентского района.'),
    ('1979', 'Участник VII Всесоюзного совещания молодых писателей. На семинаре Агнии Барто рекомендован в Союз писателей СССР.'),
    ('1981', 'Детские стихи в сборниках «Какое хорошее утро» и «Апрельский дождь» («Малыш», «Детская литература», 1981 и 1986).'),
    ('1985', 'В издательстве «Малыш» вышла книжка стихов «Большой человек».'),
    ('1990', 'Лезгинский театр поставил пьесу-сказку «Чигали». Позже шли «КӀвал хъиткьинна» и «Дустагъда мехъер» (1994), «Къарачияр» (2001).'),
    ('2006', 'Проза в московских сборниках северокавказских писателей «Война длиною в жизнь» (2006) и «Дорога домой» (2011).'),
    ('2008', 'Рассказ «Гведек» включён в антологию современной литературы народов России.'),
    ('2013', 'Вышла книга повестей и рассказов «Ночь перед новолунием» в переводе с лезгинского.'),
]


def main(html_dir, photo):
    if os.path.exists(db.DB_PATH):
        sys.exit(f'{db.DB_PATH} already exists, remove it first')
    db.init()
    with db.session() as c:
        c.execute('INSERT INTO files (name, mime, data) VALUES (?, ?, ?)', ('author.jpg', 'image/jpeg', open(photo, 'rb').read()))
        for k, v in {**SETTINGS, 'photo': 'author.jpg'}.items():
            c.execute('UPDATE settings SET value = ? WHERE key = ?', (v, k))
        for pos, (year, text) in enumerate(TIMELINE):
            c.execute('INSERT INTO timeline (year, text, position) VALUES (?, ?, ?)', (year, text, pos))
        for section, items in SECTIONS:
            for pos, (slug, fid, title, sub, lang, style) in enumerate(items):
                raw = open(os.path.join(html_dir, fid + '.html'), encoding='utf-8').read()
                body = render.promote_headings(render.sanitize(raw), style)
                c.execute('INSERT INTO works (slug, title, subtitle, section, lang, style, color, visibility, body, position) '
                          'VALUES (?,?,?,?,?,?,?,?,?,?)',
                          (slug, title, sub, section, lang, style, pos % 8, 'excerpt', body, pos))
                print(f'{section:6s} {title}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
