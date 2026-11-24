/* CareLedger front-end behaviour: toasts, confirmations, motion, prescription rows. */
(() => {
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hasGsap = typeof gsap !== "undefined" && !calm;
  const FAST = 0.18; // seconds, stays under 200ms

  if (window.lucide) lucide.createIcons();

  /* ---- toasts (Django messages -> SweetAlert2) ---- */
  const toast = Swal.mixin({ toast: true, position: "top-end", showConfirmButton: false, timer: 3800, timerProgressBar: true });
  document.querySelectorAll("#flash [data-level]").forEach((el) => {
    const level = el.dataset.level;
    toast.fire({ icon: level === "error" ? "error" : level === "warning" ? "warning" : level === "info" ? "info" : "success", title: el.textContent.trim() });
  });

  /* ---- confirmation dialogs for irreversible actions ---- */
  document.addEventListener("submit", (e) => {
    const form = e.target.closest("form[data-confirm]");
    if (!form || form.dataset.confirmed) return;
    e.preventDefault();
    const danger = form.dataset.tone === "danger";
    const body = document.createElement("div");
    if (form.dataset.text) {
      const p = document.createElement("p");
      p.textContent = form.dataset.text;
      body.append(p);
    }
    const list = form.querySelector(".confirm-items");
    if (list) { const copy = list.cloneNode(true); copy.hidden = false; body.append(copy); }
    Swal.fire({
      title: form.dataset.title,
      html: body,
      icon: danger ? "warning" : "question",
      showCancelButton: true,
      confirmButtonText: form.dataset.button || "Confirm",
      cancelButtonText: "Go back",
      confirmButtonColor: danger ? "#DC2626" : "#0F766E",
      cancelButtonColor: "#64748B",
      focusCancel: danger,
      showClass: { popup: "swal2-noanimation" }, hideClass: { popup: "" },
    }).then((r) => { if (r.isConfirmed) { form.dataset.confirmed = "1"; form.submit(); } });
  });

  /* ---- sidebar on small screens ---- */
  const sidebar = document.getElementById("sidebar"), scrim = document.getElementById("scrim");
  const setNav = (open) => { sidebar?.classList.toggle("-translate-x-full", !open); scrim?.classList.toggle("hidden", !open); };
  document.getElementById("nav-toggle")?.addEventListener("click", () => setNav(true));
  scrim?.addEventListener("click", () => setNav(false));

  /* ---- dashboard: quick stagger on KPI cards ---- */
  if (hasGsap && document.querySelector(".kpi")) {
    gsap.from(".kpi", { opacity: 0, y: 6, duration: FAST, stagger: 0.04, ease: "power2.out", clearProps: "all" });
  }

  /* ---- print receipt ---- */
  document.querySelectorAll("[data-print]").forEach((b) => b.addEventListener("click", () => window.print()));

  /* ---- visit form: allergy warning ---- */
  const patientSelect = document.getElementById("id_patient"), mapEl = document.getElementById("allergy-map"), box = document.getElementById("allergy-alert");
  if (patientSelect && mapEl && box) {
    const map = JSON.parse(mapEl.textContent);
    const show = () => {
      const a = map[patientSelect.value];
      box.hidden = !a;
      if (a) box.querySelector("span").textContent = a;
    };
    patientSelect.addEventListener("change", show);
    show();
  }

  /* ---- visit form: dynamic prescription rows ---- */
  const rows = document.getElementById("rx-rows"), tpl = document.getElementById("rx-empty"), hint = document.getElementById("rx-hint");
  if (rows && tpl) {
    const total = document.querySelector('[name="items-TOTAL_FORMS"]');
    const sync = () => { if (hint) hint.hidden = rows.children.length > 0; };
    const reindex = () => {
      [...rows.children].forEach((row, i) => {
        row.querySelectorAll("[name],[id],[for]").forEach((el) => {
          ["name", "id", "for"].forEach((attr) => {
            const v = el.getAttribute(attr);
            if (v) el.setAttribute(attr, v.replace(/items-\d+-/, `items-${i}-`));
          });
        });
      });
      total.value = rows.children.length;
      sync();
    };
    document.getElementById("add-drug").addEventListener("click", () => {
      const holder = document.createElement("div");
      holder.innerHTML = tpl.innerHTML.replace(/__prefix__/g, total.value).trim();
      const row = holder.firstElementChild;
      rows.append(row);
      total.value = rows.children.length;
      sync();
      if (hasGsap) gsap.fromTo(row, { opacity: 0, y: -8, height: 0 }, { opacity: 1, y: 0, height: "auto", duration: FAST, ease: "power2.out", clearProps: "height" });
      row.querySelector("select").focus();
    });
    rows.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-remove-row]");
      if (!btn) return;
      const row = btn.closest(".rx-row");
      const done = () => { row.remove(); reindex(); };
      hasGsap ? gsap.to(row, { opacity: 0, height: 0, duration: FAST, onComplete: done }) : done();
    });
    sync();
  }
})();
