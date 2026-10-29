(function () {
  const root = document.querySelector("[data-slider]");
  if (root) {
    const slides = Array.from(root.querySelectorAll(".slider__slide"));
    const dots = Array.from(root.querySelectorAll("[data-go]"));
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const interval = Number(root.dataset.interval) || 3000;
    let index = 0;
    let timer = null;

    function show(next) {
      index = (next + slides.length) % slides.length;
      slides.forEach(function (slide, i) {
        const active = i === index;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", active ? "false" : "true");
      });
      dots.forEach(function (dot, i) {
        if (i === index) dot.setAttribute("aria-current", "true");
        else dot.removeAttribute("aria-current");
      });
    }

    function stop() {
      if (timer) clearInterval(timer);
      timer = null;
    }

    function start() {
      if (reduce) return;
      stop();
      timer = setInterval(function () { show(index + 1); }, interval);
    }

    const prev = root.querySelector("[data-prev]");
    const next = root.querySelector("[data-next]");
    if (prev) prev.addEventListener("click", function () { show(index - 1); start(); });
    if (next) next.addEventListener("click", function () { show(index + 1); start(); });
    dots.forEach(function (dot) {
      dot.addEventListener("click", function () {
        show(Number(dot.dataset.go));
        start();
      });
    });
    root.addEventListener("mouseenter", stop);
    root.addEventListener("mouseleave", start);
    root.addEventListener("focusin", stop);
    root.addEventListener("focusout", start);
    root.addEventListener("keydown", function (event) {
      if (event.key === "ArrowLeft") show(index - 1);
      if (event.key === "ArrowRight") show(index + 1);
    });
    show(0);
    start();
  }

  const login = document.querySelector("[data-login-check]");
  const hint = document.querySelector("[data-login-hint]");
  if (login && hint) {
    const format = /^[A-Za-z][A-Za-z0-9_]{2,31}$/;
    let wait = null;
    login.addEventListener("input", function () {
      clearTimeout(wait);
      wait = setTimeout(async function () {
        const value = login.value.trim();
        if (!format.test(value)) {
          hint.hidden = true;
          return;
        }
        const response = await fetch("/api/login-available?login=" + encodeURIComponent(value));
        const data = await response.json();
        hint.hidden = false;
        hint.textContent = data.available ? "Логин свободен" : "Логин уже занят";
        hint.classList.toggle("is-ok", data.available);
        hint.classList.toggle("is-bad", !data.available);
      }, 300);
    });
  }

  document.querySelectorAll(".toast").forEach(function (toast) {
    const close = function () { toast.remove(); };
    const timer = setTimeout(close, 4200);
    const button = toast.querySelector("[data-close]");
    if (button) {
      button.addEventListener("click", function () {
        clearTimeout(timer);
        close();
      });
    }
  });
})();
