/* PhysioScan — UI interactions (navbar toggle, password visibility) */
(function () {
  "use strict";

  // ── Navbar toggle (mobile) ────────────────────────────────────────────────
  var btn  = document.querySelector(".navbar__toggle");
  var menu = document.querySelector(".navbar__menu");
  if (btn && menu) {
    btn.addEventListener("click", function () {
      var open = menu.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", String(open));
    });

    // Cerrar al hacer clic fuera
    document.addEventListener("click", function (e) {
      if (!btn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.remove("is-open");
        btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  // ── Toggle visibilidad de contraseña ─────────────────────────────────────
  document.querySelectorAll(".btn-toggle-pwd").forEach(function (toggle) {
    toggle.addEventListener("click", function () {
      var wrap  = toggle.closest(".input-password-wrap");
      var input = wrap && wrap.querySelector(".form-input");
      if (!input) return;
      var shown = input.type === "text";
      input.type = shown ? "password" : "text";
      var icon = toggle.querySelector("svg");
      if (icon) {
        icon.innerHTML = shown
          ? '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'
          : '<path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24M1 1l22 22"/>';
      }
      toggle.setAttribute("aria-label", shown ? "Mostrar contraseña" : "Ocultar contraseña");
    });
  });

  // ── Indicador de seguridad de contraseña ─────────────────────────────────
  var pwdField = document.getElementById("password");
  var strengthBar = document.querySelector(".pwd-strength");
  if (pwdField && strengthBar) {
    pwdField.addEventListener("input", function () {
      var v = pwdField.value;
      var score = 0;
      if (v.length >= 12) score++;
      if (/[A-Z]/.test(v)) score++;
      if (/[a-z]/.test(v)) score++;
      if (/\d/.test(v)) score++;
      var levels = ["", "weak", "fair", "good", "strong"];
      strengthBar.className = "pwd-strength" + (score ? " pwd-strength--" + levels[score] : "");
    });
  }

  // ── Auto-cierre de flash messages ─────────────────────────────────────────
  document.querySelectorAll(".flash").forEach(function (el) {
    setTimeout(function () {
      if (el.parentElement) el.remove();
    }, 6000);
  });

  // ── Scroll: revelar elementos .fade-up con IntersectionObserver ───────────
  if (typeof IntersectionObserver !== "undefined") {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var delay = parseInt(entry.target.getAttribute("data-delay") || "0", 10);
          setTimeout(function () {
            entry.target.classList.add("visible");
          }, delay);
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.14 });

    document.querySelectorAll(".fade-up").forEach(function (el) {
      io.observe(el);
    });
  } else {
    document.querySelectorAll(".fade-up").forEach(function (el) {
      el.classList.add("visible");
    });
  }
})();
