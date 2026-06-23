// Shared app chrome: sidebar, mobile tab bar, top bar tools (theme + accent + units).
// Persists tweak choices to localStorage so every page shares state.
// Usage: <body data-page="today"><script src="assets/chrome.js"></script>

(function () {
  const NAV = [
    { id: "today",     href: "today.html",     label: "Today",     icon: "calendar" },
    { id: "workouts",  href: "workouts.html",  label: "Workouts",  icon: "dumbbell" },
    { id: "programs",  href: "programs.html",  label: "Programs",  icon: "list" },
    { id: "nutrition", href: "nutrition.html", label: "Nutrition", icon: "utensils" },
    { id: "analytics", href: "analytics.html", label: "Insights",  icon: "chart" },
    { id: "settings",  href: "settings.html",  label: "Settings",  icon: "settings", footer: true },
  ];

  const ICONS = {
    calendar: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4.5" width="18" height="17" rx="3"/><path d="M3 9h18M8 3v3M16 3v3"/></svg>',
    dumbbell: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8v8M3 10v4M18 8v8M21 10v4M6 12h12"/></svg>',
    list: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1.2"/><circle cx="4.5" cy="12" r="1.2"/><circle cx="4.5" cy="18" r="1.2"/></svg>',
    utensils: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 3v8a2 2 0 0 0 2 2v8M9 3v6M5 3v6M17 14v7M17 14c-2 0-3-2-3-5 0-4 1.5-6 3-6s3 2 3 6c0 3-1 5-3 5z"/></svg>',
    chart: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5M4 19h16M8 15l3-4 3 3 5-7"/></svg>',
    settings: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1A2 2 0 1 1 4.3 17l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1A2 2 0 1 1 7 4.3l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1A2 2 0 1 1 19.7 7l-.1.1a1.7 1.7 0 0 0-.3 1.8V9c.3.6.9 1 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>',
    sun: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/></svg>',
    moon: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
    auto: '<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12c4 0 9 4 9 9M21 12c-4 0-9 4-9 9"/></svg>',
  };

  // Apply persisted tweaks before paint
  function applyTweaks() {
    const theme = localStorage.getItem("om.theme") || "system";
    const accent = localStorage.getItem("om.accent") || "blue";
    const units = localStorage.getItem("om.units") || "kg";
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    root.setAttribute("data-accent", accent);
    root.setAttribute("data-units", units);
  }
  applyTweaks();

  function render() {
    const page = document.body.dataset.page;
    const sidebar = NAV.filter(n => !n.footer).map(n => `
      <a class="nav-item ${n.id === page ? "active" : ""}" href="${n.href}">
        ${ICONS[n.icon]}
        <span>${n.label}</span>
      </a>`).join("");
    const sideFoot = NAV.filter(n => n.footer).map(n => `
      <a class="nav-item ${n.id === page ? "active" : ""}" href="${n.href}">
        ${ICONS[n.icon]}<span>${n.label}</span>
      </a>`).join("");

    const sidebarHTML = `
      <aside class="sidebar" aria-label="Primary navigation">
        <div class="sidebar-brand">
          <span class="mark">G</span>
          <span class="name">gym</span>
        </div>
        <nav class="sidebar-nav">${sidebar}</nav>
        <div style="margin-top:auto;display:flex;flex-direction:column;gap:2px;">
          ${sideFoot}
        </div>
        <div class="sidebar-foot">
          <span class="avatar">AC</span>
          <div class="profile-mini">
            <div class="who">Alex Chen</div>
            <div class="what">Week 4 of 8 · PPL</div>
          </div>
        </div>
      </aside>`;

    const mobileBar = `
      <nav class="mobile-tabbar" aria-label="Mobile navigation">
        ${NAV.filter(n => !n.footer).map(n => `
          <a href="${n.href}" class="${n.id === page ? "active" : ""}">
            ${ICONS[n.icon]}
            <span>${n.label}</span>
          </a>`).join("")}
      </nav>`;

    // Theme + accent + units pill in top bar — global toolbar
    const tools = `
      <div class="tools">
        <div class="tb-pill" id="tbAccent" title="Accent color">
          <span class="dot"></span>
          <span id="tbAccentLabel">Clay</span>
        </div>
        <div class="tb-pill" id="tbUnits" title="Units">
          <span id="tbUnitsLabel">kg</span>
        </div>
        <div class="tb-pill" id="tbTheme" title="Theme" style="gap:6px;padding:0 10px;">
          <span id="tbThemeIcon" style="display:inline-flex;width:14px;height:14px;"></span>
          <span id="tbThemeLabel">Auto</span>
        </div>
      </div>`;

    // Slot into shell — if the page didn't set up an .app shell, wrap its content
    const root = document.getElementById("app-root");
    if (!root) return;
    const pageContent = root.innerHTML;
    const title = root.dataset.title || "";
    const crumb = root.dataset.crumb || "";
    const headerExtra = root.dataset.headerExtra || "";

    root.outerHTML = `
      <div class="app">
        ${sidebarHTML}
        <main class="main">
          <div class="topbar">
            ${crumb ? `<span class="crumb">${crumb}</span>` : ""}
            <h1>${title}</h1>
            <div class="spacer"></div>
            ${headerExtra}
            ${tools}
          </div>
          <div id="app-root">${pageContent}</div>
        </main>
        ${mobileBar}
      </div>`;

    // Wire toggles
    const accentOrder = ["blue", "indigo", "mint", "orange", "pink"];
    const accentLabel = { blue: "Clay", indigo: "Slate", mint: "Teal", orange: "Ochre", pink: "Rose" };
    const themeOrder = ["system", "light", "dark"];
    const themeIcon = { system: ICONS.auto, light: ICONS.sun, dark: ICONS.moon };
    const themeLabel = { system: "Auto", light: "Light", dark: "Dark" };

    function syncLabels() {
      const accent = localStorage.getItem("om.accent") || "blue";
      const units = localStorage.getItem("om.units") || "kg";
      const theme = localStorage.getItem("om.theme") || "system";
      document.getElementById("tbAccentLabel").textContent = accentLabel[accent];
      document.getElementById("tbUnitsLabel").textContent = units;
      document.getElementById("tbThemeLabel").textContent = themeLabel[theme];
      document.getElementById("tbThemeIcon").innerHTML = themeIcon[theme].replace('class="ic"', 'style="width:14px;height:14px;"');
    }
    syncLabels();

    document.getElementById("tbAccent").addEventListener("click", () => {
      const cur = localStorage.getItem("om.accent") || "blue";
      const next = accentOrder[(accentOrder.indexOf(cur) + 1) % accentOrder.length];
      localStorage.setItem("om.accent", next);
      applyTweaks();
      syncLabels();
    });
    document.getElementById("tbUnits").addEventListener("click", () => {
      const cur = localStorage.getItem("om.units") || "kg";
      const next = cur === "kg" ? "lb" : "kg";
      localStorage.setItem("om.units", next);
      applyTweaks();
      syncLabels();
      // notify pages that show weights
      document.dispatchEvent(new CustomEvent("om:units-changed", { detail: next }));
    });
    document.getElementById("tbTheme").addEventListener("click", () => {
      const cur = localStorage.getItem("om.theme") || "system";
      const next = themeOrder[(themeOrder.indexOf(cur) + 1) % themeOrder.length];
      localStorage.setItem("om.theme", next);
      applyTweaks();
      syncLabels();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
})();
