/**
 * ASB - Accessibility Settings Bar
 * version 0.5
 * Copyright (c) 2019 Breno Novelli
 * 
 * Modificado 2025/2026 - SciELO - Ramon Cordini
 * Modificado para exibição em modal
 */

 (function() {
  const accessKey = 4;
  const translateAcessibilityBar = window.accessibilityTranslations;

  // ===== MODAL PATCH - Dynamic Modal Creation =====
  function createAccessibilityModal() {
    if (document.getElementById("accessibilityModal")) return;
  
    const modalWrapper = document.createElement("div");
    modalWrapper.innerHTML = `
      <div 
        class="modal fade" 
        id="accessibilityModal" 
        tabindex="-1"
        role="dialog"
        aria-modal="true"
        aria-labelledby="accessibilityModalLabel">
        <div class="modal-dialog modal-dialog-centered" style="max-width:380px; margin: 0 auto;">
          <div class="modal-content">
            <div class="modal-header">
              <h5 
                id="accessibilityModalLabel" 
                class="modal-title"
              >
                ${translateAcessibilityBar.accessibilityMenu}
              </h5>
              <button 
                type="button" 
                class="btn-close" 
                data-bs-dismiss="modal" 
                aria-label="Close"
              ></button>
            </div>
            <div class="modal-body">
              <div id="accessibilityBarModal" class="d-flex flex-column gap-2"></div>
            </div>
          </div>
        </div>
      </div>
    `;
  
    document.body.appendChild(modalWrapper.firstElementChild);
  }
  

  // Create modal before anything else uses it
  createAccessibilityModal();
  

  const btns = {
    btnHighContrast: {
      active: false,
      dataAccessibility: "contrast",
      class: "setAccessibility",
      icon: "FontAwesome",
      iconClass: ["fas", "fa-adjust"],
      text: "Alto contraste",
    },
    btnDarkMode: {
      active: true,
      dataAccessibility: "dark",
      class: "setAccessibility",
      icon: "dark_mode",
      iconClass: "material-icons-outlined",
      text: translateAcessibilityBar.darkMode,
    },
    btnIncFont: {
      active: true,
      dataAccessibility: "incFont",
      class: "setAccessibility",
      icon: "A+",
      iconClass: "",
      text: translateAcessibilityBar.increaseText,
    },
    btnOriFont: {
      active: true,
      dataAccessibility: "oriFont",
      class: "setAccessibility",
      icon: "Aa",
      iconClass: "",
      text: translateAcessibilityBar.originalText,
    },
    btnDecFont: {
      active: true,
      dataAccessibility: "decFont",
      class: "setAccessibility",
      icon: "A-",
      iconClass: "",
      text: translateAcessibilityBar.decreaseText,
    },
    btnMarkerLine: {
      active: true,
      dataAccessibility: "markerLine",
      class: "setAccessibility",
      icon: "straighten",
      iconClass: "material-icons-outlined",
      text: translateAcessibilityBar.markerLine,
    },
    btnReadingLine: {
      active: true,
      dataAccessibility: "readingLine",
      class: "setAccessibility",
      icon: "straighten",
      iconClass: "material-icons-outlined",
      text: translateAcessibilityBar.readingLine,
    },
    btnReset: {
      active: true,
      dataAccessibility: "reset",
      class: "setAccessibility",
      icon: "refresh",
      iconClass: "material-icons-outlined",
      text: translateAcessibilityBar.reset,
    },
  };

  // ===== MODAL PATCH =====
  const accessibilityBar = document.getElementById("accessibilityBarModal");

  /**
   * Creating main floating button
   */
  let btnAccessibilityBar;

  function createMainButton() {
    btnAccessibilityBar = document.createElement("button");
    btnAccessibilityBar.id = "universalAccessBtn";
    btnAccessibilityBar.type = "button";
    btnAccessibilityBar.className = "btn btn-primary position-fixed bottom-0 end-0 m-3 rounded-circle shadow";
    btnAccessibilityBar.accessKey = accessKey;

    const icon = document.createElement("i");
    icon.classList.add("material-icons-outlined", "mt-1");
    icon.textContent = "accessibility_new";
    btnAccessibilityBar.appendChild(icon);

    const spanText = document.createElement("span");
    spanText.textContent = translateAcessibilityBar.accessibilityMenu;
    spanText.className = "visually-hidden";
    btnAccessibilityBar.appendChild(spanText);

    document.body.appendChild(btnAccessibilityBar);
  }
  createMainButton();

  /**
   * Creating settings buttons (inside modal)
   */
  function createButtons(el) {
    if (!accessibilityBar) return;

    const button = document.createElement("button");
    button.type = "button";
    button.classList.add(el.class, "btn", "btn-secondary", "text-start");
    button.setAttribute("data-accessibility", el.dataAccessibility);
    accessibilityBar.appendChild(button);

    const wrapIcon = document.createElement("strong");
    wrapIcon.classList.add("me-2");
    button.appendChild(wrapIcon);

    if (el.icon === "FontAwesome") {
      const icon = document.createElement("i");
      icon.classList.add(...el.iconClass);
      wrapIcon.appendChild(icon);
    } else if (el.iconClass && typeof el.iconClass === "string") {
      const icon = document.createElement("i");
      icon.className = el.iconClass;
      icon.textContent = el.icon;
      wrapIcon.appendChild(icon);
    } else {
      wrapIcon.textContent = el.icon;
    }

    const textButton = document.createTextNode(el.text);
    button.appendChild(textButton);
  }

  Object.keys(btns).forEach(function(item) {
    if (btns[item].active) {
      createButtons(btns[item]);
    }
  });

  const html = document.documentElement;
  const body = document.body;
  const btnAccessibility = document.querySelectorAll(".setAccessibility");

  if (btnAccessibilityBar) {
    setTimeout(function() {
      btnAccessibilityBar.classList.add("collapsed");
    }, 2000);
  }

  /**
   * Skip link
   */
  const skipLink = document.createElement("a");
  skipLink.href = "#content";
  skipLink.textContent = translateAcessibilityBar.skipLinkText;
  skipLink.className = "skip-link visually-hidden-focusable";
  skipLink.setAttribute("aria-label", translateAcessibilityBar.skipLinkText);
  document.body.insertBefore(skipLink, document.body.firstChild);

  /**
   * Reading + Marker lines
   */
  const readingLine = document.createElement("div");
  readingLine.id = "readingLine";
  document.body.insertBefore(readingLine, document.body.firstChild);

  const markerLine = document.createElement("div");
  markerLine.id = "markerLine";
  document.body.insertBefore(markerLine, document.body.firstChild);

  html.addEventListener("mousemove", function(e) {
    const y = e.pageY - 20;
    if (body.classList.contains("accessibility_readingLine")) {
      readingLine.style.top = `${y}px`;
    }
    if (body.classList.contains("accessibility_markerLine")) {
      markerLine.style.top = `${y}px`;
    }
  });

  // ===== MODAL PATCH (BS4 + BS5 SAFE) =====
  btnAccessibilityBar.addEventListener("click", () => {
    const modalEl = document.getElementById("accessibilityModal");
    if (!modalEl) return;

    // Bootstrap 5 (no getOrCreateInstance)
    if (window.bootstrap && bootstrap.Modal) {
      try {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
        return;
      } catch (e) {}
    }

    // Bootstrap 4 (jQuery)
    if (window.jQuery) {
      jQuery(modalEl).modal('show');
    }
  });

  /**
   * Toggle Accessibilities
   */
  function toggleAccessibilities(action) {
    switch (action) {
      case "contrast":
        window.toggleContrast();
        break;
      case "dark":
        window.toggleDark();
        break;
      case "incFont":
      case "oriFont":
      case "decFont":
        window.toggleFontSize(action);
        break;
      case "readingLine":
        body.classList.toggle("accessibility_readingLine");
        break;
      case "markerLine":
        body.classList.toggle("accessibility_markerLine");
        break;
      case "reset":
        Dark.currentState === true ? Dark.setState(false) : null;
        Contrast.currentState === true ? Contrast.setState(false) : null;
        window.toggleFontSize("oriFont");
        body.classList.remove("accessibility_readingLine");
        body.classList.remove("accessibility_markerLine");
        break;
    }
  }

  btnAccessibility.forEach(button =>
    button.addEventListener("click", () =>
      toggleAccessibilities(button.dataset.accessibility)
    )
  );

  /**
   * Font Size
   */
  const htmlFontSize = parseFloat(
    getComputedStyle(document.documentElement).getPropertyValue("font-size")
  );

  let FontSize = {
    storage: "fontSizeState",
    currentState: null,
    getState() {
      return sessionStorage.getItem(this.storage)
        ? parseFloat(sessionStorage.getItem(this.storage))
        : 100;
    },
    setState(state) {
      sessionStorage.setItem(this.storage, "" + state);
      this.currentState = state;
      this.updateView();
    },
    updateView() {
      if (this.currentState === null) this.currentState = this.getState();
      html.style.fontSize =
        (this.currentState / 100) * htmlFontSize + "px";
    },
    toggle(action) {
      if (this.currentState === null) this.currentState = this.getState();
      switch (action) {
        case "incFont":
          if (this.currentState < 200) this.setState(this.currentState + 20);
          else alert("Limite atingido!");
          break;
        case "decFont":
          if (this.currentState > 40) this.setState(this.currentState - 20);
          else alert("Limite atingido!");
          break;
        case "oriFont":
          this.setState(100);
          break;
      }
    },
  };

  FontSize.updateView();
  window.toggleFontSize = action => FontSize.toggle(action);

  /**
   * Contrast
   */
  let Contrast = {
    storage: "contrastState",
    cssClass: "contrast",
    currentState: null,
    getState() {
      return sessionStorage.getItem(this.storage) === "true";
    },
    setState(state) {
      sessionStorage.setItem(this.storage, "" + state);
      this.currentState = state;
      this.updateView();
    },
    updateView() {
      if (this.currentState === null) this.currentState = this.getState();
      body.classList.toggle(this.cssClass, this.currentState);
    },
    toggle() {
      this.setState(!this.currentState);
      if (Dark.currentState) Dark.setState(false);
    },
  };

  Contrast.updateView();
  window.toggleContrast = () => Contrast.toggle();

  /**
   * Dark Mode
   */
  let Dark = {
    storage: "darkState",
    cssClass: "scielo__theme--dark",
    currentState: null,
    getState() {
      return sessionStorage.getItem(this.storage) === "true";
    },
    setState(state) {
      sessionStorage.setItem(this.storage, "" + state);
      this.currentState = state;
      this.updateView();
    },
    updateView() {
      if (this.currentState === null) this.currentState = this.getState();
      body.classList.toggle(this.cssClass, this.currentState);
    },
    toggle() {
      this.setState(!this.currentState);
      if (Contrast.currentState) Contrast.setState(false);
    },
  };

  Dark.updateView();
  window.toggleDark = () => Dark.toggle();

})();