// Word-like editor for work texts and the biography. Formatting it produces is kept by render.sanitize on the server.
function initEditor(selector, opts) {
  var dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  var full = !opts || opts.full !== false;
  tinymce.init({
    selector: selector,
    base_url: '/static/vendor/tinymce',
    suffix: '.min',
    language: 'ru',
    language_url: '/static/vendor/tinymce/langs/ru.js',
    skin: dark ? 'oxide-dark' : 'oxide',
    content_css: [dark ? 'dark' : 'default', '/static/fonts/fonts.css', '/static/editor-content.css'],
    height: full ? 720 : 380,
    menubar: full ? 'edit view insert format table' : false,
    plugins: 'lists advlist table link charmap searchreplace wordcount fullscreen code visualblocks',
    toolbar: full
      ? 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | forecolor backcolor | ' +
        'alignleft aligncenter alignright alignjustify | bullist numlist outdent indent lineheight | ' +
        'table hr charmap link | searchreplace removeformat | fullscreen'
      : 'undo redo | bold italic underline | alignleft aligncenter alignjustify | bullist numlist | link removeformat',
    toolbar_mode: 'wrap',
    toolbar_sticky: true,
    toolbar_sticky_offset: 56,
    block_formats: 'Обычный текст=p; Заголовок раздела=h2; Подзаголовок=h3; Цитата=blockquote',
    font_family_formats: 'PT Serif (текст сайта)=PT Serif, Georgia, serif; Cormorant Garamond (заголовки)=Cormorant Garamond, Georgia, serif; ' +
      'Georgia=Georgia, serif; Times New Roman=Times New Roman, serif; Arial=Arial, sans-serif',
    font_size_formats: '10pt 11pt 12pt 13pt 14pt 16pt 18pt 20pt 24pt 28pt 36pt',
    line_height_formats: '1 1.15 1.3 1.5 1.75 2',
    invalid_elements: 'img,script,iframe,object,embed,video,audio,form,input',
    entity_encoding: 'raw',
    convert_urls: false,
    browser_spellcheck: true,
    contextmenu: false,
    promotion: false,
    branding: false,
    resize: true,
    table_default_styles: { 'border-collapse': 'collapse', width: '100%' },
    setup: function (ed) {
      ed.on('init', function () { document.documentElement.classList.add('editor-ready'); });
    }
  });
}
