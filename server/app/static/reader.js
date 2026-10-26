(function () {
  var key = 'pos:' + location.pathname;
  var sizes = [0.95, 1.05, 1.125, 1.25, 1.4, 1.6];
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  var level = parseInt(store.get('textSize'), 10);
  if (isNaN(level)) level = 2;
  function applySize() {
    document.documentElement.style.setProperty('--text-size', sizes[level] + 'rem');
    store.set('textSize', String(level));
  }
  applySize();
  document.getElementById('smaller').addEventListener('click', function () { if (level > 0) { level--; applySize(); } });
  document.getElementById('bigger').addEventListener('click', function () { if (level < sizes.length - 1) { level++; applySize(); } });

})();
