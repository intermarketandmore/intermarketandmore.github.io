// Player YouTube caricato solo al clic (youtube-nocookie): nessun contenuto di terzi finché il visitatore non avvia il video.
document.querySelectorAll("[data-yt]").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var id = btn.getAttribute("data-yt");
    var f = document.createElement("iframe");
    f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + "?autoplay=1&rel=0";
    f.title = btn.getAttribute("data-title") || "Focus Mercati";
    f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    f.allowFullscreen = true;
    btn.replaceWith(f);
  });
});

// Filtro per rubrica e "carica altre" sulle analisi del blog.
(function () {
  var list = document.getElementById("posts");
  if (!list) return;
  var items = Array.prototype.slice.call(list.querySelectorAll(".post"));
  var more = document.getElementById("more-posts");
  var step = 10, shown = step, cat = "all";
  function apply() {
    var match = items.filter(function (el) { return cat === "all" || el.getAttribute("data-cat") === cat; });
    items.forEach(function (el) { el.hidden = true; });
    match.slice(0, shown).forEach(function (el) { el.hidden = false; });
    if (more) more.hidden = match.length <= shown;
  }
  document.querySelectorAll("[data-filter]").forEach(function (b) {
    b.addEventListener("click", function () {
      cat = b.getAttribute("data-filter"); shown = step;
      document.querySelectorAll("[data-filter]").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      apply();
    });
  });
  if (more) more.addEventListener("click", function () { shown += step; apply(); });
  apply();
})();

// Filtro per mese nell'archivio Focus Mercati.
(function () {
  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-month]"));
  var btns = document.querySelectorAll("[data-mfilter]");
  btns.forEach(function (b) {
    b.addEventListener("click", function () {
      var m = b.getAttribute("data-mfilter");
      btns.forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      cards.forEach(function (c) { c.hidden = !(m === "all" || c.getAttribute("data-month") === m); });
    });
  });
})();
