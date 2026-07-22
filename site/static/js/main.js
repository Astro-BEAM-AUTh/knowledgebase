// Theme toggle, mobile nav drawer, and small keyboard affordances. This is the whole client-side runtime besides search.js.
(function () {
  "use strict";

  var root = document.documentElement;
  var themeBtn = document.getElementById("themeToggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("kb-theme", next); } catch (e) {}
    });
  }

  var navToggle = document.getElementById("navToggle");
  var sidebar = document.getElementById("sidebar");
  if (navToggle && sidebar) {
    navToggle.addEventListener("click", function () {
      var open = sidebar.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("click", function (e) {
      if (sidebar.classList.contains("is-open") &&
          !sidebar.contains(e.target) && e.target !== navToggle && !navToggle.contains(e.target)) {
        sidebar.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  // "/" focuses search from anywhere on the page, unless already typing
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
      var input = document.getElementById("searchInput");
      if (input) { e.preventDefault(); input.focus(); }
    }
    if (e.key === "Escape") {
      if (sidebar) sidebar.classList.remove("is-open");
    }
  });
})();
