// Client-side search. Loads search-index.json once (built at generation time, not at request time, there is no server here) and does a small
// scored token match: title hits count for more than body-text hits. Deliberately hand-rolled rather than pulling in a search library, the
// whole corpus is (and will remain) a few dozen pages, so a full inverted index would be overkill.
(function () {
  "use strict";

  var input = document.getElementById("searchInput");
  var resultsBox = document.getElementById("searchResults");
  if (!input || !resultsBox) return;

  var indexPromise = null;
  var selectedIndex = -1;
  var currentResults = [];

  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch(window.__SEARCH_INDEX_URL)
        .then(function (r) { return r.json(); })
        .catch(function () { return []; });
    }
    return indexPromise;
  }

  function score(doc, terms) {
    var title = (doc.title || "").toLowerCase();
    var text = (doc.text || "").toLowerCase();
    var total = 0;
    for (var i = 0; i < terms.length; i++) {
      var t = terms[i];
      if (!t) continue;
      if (title.indexOf(t) !== -1) total += title === t ? 12 : 6;
      var idx = text.indexOf(t);
      if (idx !== -1) total += 1 + Math.max(0, 3 - idx / 200);
    }
    return total;
  }

  function render(results, query) {
    currentResults = results;
    selectedIndex = -1;
    if (!query) {
      resultsBox.hidden = true;
      resultsBox.innerHTML = "";
      return;
    }
    if (!results.length) {
      resultsBox.innerHTML = '<p class="site-search__empty">No matches for "' + escapeHtml(query) + '"</p>';
      resultsBox.hidden = false;
      return;
    }
    var prefix = window.__SEARCH_INDEX_URL.replace(/search-index\.json$/, "");
    resultsBox.innerHTML = results.slice(0, 8).map(function (r, i) {
      return '<a href="' + prefix + r.url + '" data-idx="' + i + '">' +
        escapeHtml(r.title) +
        '<span class="site-search__result-kind">' + escapeHtml(r.kind) + (r.repo ? " · " + escapeHtml(r.repo) : "") + '</span>' +
        '</a>';
    }).join("");
    resultsBox.hidden = false;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  var debounceTimer = null;
  input.addEventListener("input", function () {
    var query = input.value.trim().toLowerCase();
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () {
      if (!query) { render([], ""); return; }
      loadIndex().then(function (docs) {
        var terms = query.split(/\s+/).filter(Boolean);
        var scored = docs
          .map(function (d) { return { doc: d, s: score(d, terms) }; })
          .filter(function (x) { return x.s > 0; })
          .sort(function (a, b) { return b.s - a.s; })
          .map(function (x) { return x.doc; });
        render(scored, query);
      });
    }, 120);
  });

  input.addEventListener("focus", loadIndex);

  input.addEventListener("keydown", function (e) {
    var links = resultsBox.querySelectorAll("a");
    if (!links.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIndex = Math.min(selectedIndex + 1, links.length - 1);
      updateSelection(links);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIndex = Math.max(selectedIndex - 1, 0);
      updateSelection(links);
    } else if (e.key === "Enter") {
      if (selectedIndex >= 0 && links[selectedIndex]) {
        e.preventDefault();
        window.location.href = links[selectedIndex].href;
      }
    } else if (e.key === "Escape") {
      render([], "");
      input.blur();
    }
  });

  function updateSelection(links) {
    links.forEach(function (l, i) { l.classList.toggle("is-selected", i === selectedIndex); });
    if (links[selectedIndex]) links[selectedIndex].scrollIntoView({ block: "nearest" });
  }

  document.addEventListener("click", function (e) {
    if (!resultsBox.contains(e.target) && e.target !== input) {
      resultsBox.hidden = true;
    }
  });
})();
