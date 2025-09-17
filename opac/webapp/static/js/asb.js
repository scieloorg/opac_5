/**
 * ASB - Accessibility Settings Bar
 * version 0.5
 * Copyright (c) 2019 Breno Novelli
 * 
 * Modificado 2025 - SciELO - Ramon Cordini
 */

(function() {
  /**
   * Content
   */
  
   // Tecla que será usada para complementar o atalho do teclado.
  const accessKey = 4;

  // Definição dos textos para tradução
  const translateAcessibilityBar = window.accessibilityTranslations;

  // Definições dos botões
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
      icon: "dark_mode", // Aqui vai o conteúdo que aparecerá no botão
      iconClass: "material-icons-outlined", // Ou 'material-icons-outlined'
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
  }

  /**
   * Creating the bar
   */

  const accessibilityBar = document.createElement("div");
  accessibilityBar.id = "accessibilityBar";
  document.body.insertBefore(accessibilityBar, document.body.firstChild);

  /**
   * Creating main button
   */
  let btnAccessibilityBar;

  function createMainButton() {
    btnAccessibilityBar = document.createElement("button");
    btnAccessibilityBar.id = "universalAccessBtn";
    btnAccessibilityBar.type = "button";
    btnAccessibilityBar.accessKey = accessKey;
    accessibilityBar.appendChild(btnAccessibilityBar);

    const icon = document.createElement("i");
    btnAccessibilityBar.appendChild(icon);
    icon.classList.add("material-icons-outlined", "mt-1");
    icon.textContent = "accessibility_new";

    const spanText = document.createElement("span");
    const spanTextNode = document.createTextNode(translateAcessibilityBar.accessibilityMenu);
    spanText.appendChild(spanTextNode);
    btnAccessibilityBar.appendChild(spanText);
  }
  createMainButton();

  /**
   * Creating anothers button
   */

  function createButtons(el) {
    const button = document.createElement("button");
    button.type = "button";
    button.classList.add(el.class);
    button.setAttribute('data-accessibility', el.dataAccessibility);
    accessibilityBar.appendChild(button);

    const wrapIcon = document.createElement("strong");
    button.appendChild(wrapIcon);

    if (el.icon === "FontAwesome") {
      const icon = document.createElement("i");
      wrapIcon.appendChild(icon);
      icon.classList.add(...el.iconClass);
    } else if (el.iconClass && typeof el.iconClass === "string") {
      const icon = document.createElement("i");
      icon.className = el.iconClass;
      icon.textContent = el.icon;
      wrapIcon.appendChild(icon);
    } else {
      const textIcon = document.createTextNode(el.icon);
      wrapIcon.appendChild(textIcon);
    }

    const textButton = document.createTextNode(el.text);
    button.appendChild(textButton);
  }
  Object.keys(btns).forEach(function (item) {
    if(btns[item].active){
      createButtons(btns[item]);
    }
   });
 

  const html = document.documentElement; //<html> for font-size settings
  const body = document.body; //<body> for the adjusts classes
  const btnAccessibility = document.querySelectorAll(".setAccessibility"); // Getting settings buttons

  if (btnAccessibilityBar) {
    setTimeout(function() {
      btnAccessibilityBar.classList.add("collapsed");
    }, 2000);
  }

  /**
   * ReadingLine
   */

  const readingLine = document.createElement("div");
  readingLine.id = "readingLine";
  document.body.insertBefore(readingLine, document.body.firstChild);

  html.addEventListener("mousemove", function(e) {
    if (body.classList.contains("accessibility_readingLine")) {
      let linePositionY = e.pageY - 20;
      // console.log(linePositionY);
      const elReadingLine = document.querySelector("#readingLine"); // Toggle button
      elReadingLine.style.top = `${linePositionY}px`;
    }
  });

  /**
   * MarkerLine
   */

  const markerLine = document.createElement("div");
  markerLine.id = "markerLine";
  document.body.insertBefore(markerLine, document.body.firstChild);

  html.addEventListener("mousemove", function(e) {
    if (body.classList.contains("accessibility_markerLine")) {
      let linePositionY = e.pageY - 20;
      // console.log(linePositionY);
      const elmarkerLine = document.querySelector("#markerLine"); // Toggle button
      elmarkerLine.style.top = `${linePositionY}px`;
    }
  });


    /**
     * Criar skip-link
     */

    const skipLink = document.createElement("a");
    skipLink.href = "#content";    // destino do skip-link
    skipLink.textContent = translateAcessibilityBar.skipLinkText; // texto do link
    skipLink.className = "skip-link visually-hidden-focusable"; // classes para estilo e foco
    skipLink.setAttribute("aria-label", translateAcessibilityBar.skipLinkText); // opcional, reforço de acessibilidade
    
    // Inserir antes do primeiro elemento do body
    document.body.insertBefore(skipLink, document.body.firstChild);




  /*
=== === === === === === === === === === === === === === === === === ===
=== === === === === === === === openBar === === === === === === === ===
=== === === === === === === === === === === === === === === === === ===
*/

  btnAccessibilityBar.addEventListener("click", () =>
    accessibilityBar.classList.toggle("active")
  );

  /*
=== === === === === === === === === === === === === === === === === ===
=== === === === === ===  toggleAccessibilities  === === === === === ===
=== === === === === === === === === === === === === === === === === ===
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
        window.toggleFontSize(action);
        break;
      case "oriFont":
        window.toggleFontSize(action);
        break;
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
      default:
        break;
    }
    accessibilityBar.classList.toggle("active");
  }

  btnAccessibility.forEach(button =>
    button.addEventListener("click", () =>
      toggleAccessibilities(button.dataset.accessibility)
    )
  );

  /*
=== === === === === === === === === === === === === === === === === ===
=== === === === === === ===  FontSize   === === === === === === === ===
=== === === === === === === === === === === === === === === === === ===
*/

  const htmlFontSize = parseFloat(
    getComputedStyle(document.documentElement).getPropertyValue("font-size")
  );
  let FontSize = {
    storage: "fontSizeState",
    cssClass: "fontSize",
    currentState: null,
    check: checkFontSize,
    getState: getFontSizeState,
    setState: setFontSizeState,
    toggle: toggleFontSize,
    updateView: updateViewFontSize
  };

  window.toggleFontSize = function(action) {
    FontSize.toggle(action);
  };

  FontSize.check();

  function checkFontSize() {
    this.updateView();
  }

  function getFontSizeState() {
    return sessionStorage.getItem(this.storage)
      ? sessionStorage.getItem(this.storage)
      : 100;
  }

  function setFontSizeState(state) {
    sessionStorage.setItem(this.storage, "" + state);
    this.currentState = state;
    this.updateView();
  }

  function updateViewFontSize() {
    if (this.currentState === null) this.currentState = this.getState();

    this.currentState
      ? (html.style.fontSize = (this.currentState / 100) * htmlFontSize + "px")
      : "";

    this.currentState
      ? body.classList.add(this.cssClass + this.currentState)
      : "";
  }

  function toggleFontSize(action) {
    switch (action) {
      case "incFont":
        if (parseFloat(this.currentState) < 200) {
          body.classList.remove(this.cssClass + this.currentState);
          this.setState(parseFloat(this.currentState) + 20);
        } else {
          alert("Limite atingido!");
        }
        break;
      case "oriFont":
        body.classList.remove(this.cssClass + this.currentState);
        this.setState(100);
        break;
      case "decFont":
        if (parseFloat(this.currentState) > 40) {
          body.classList.remove(this.cssClass + this.currentState);
          this.setState(parseFloat(this.currentState) - 20);
        } else {
          alert("Limite atingido!");
        }
        break;
      default:
        break;
    }
  }

  /*
=== === === === === === === === === === === === === === === === === ===
=== === === === === ===  HighConstrast  === === === === === === === ===
=== === === === === === === === === === === === === === === === === ===
*/
  let Contrast = {
    storage: "contrastState",
    cssClass: "contrast",
    currentState: null,
    check: checkContrast,
    getState: getContrastState,
    setState: setContrastState,
    toggle: toggleContrast,
    updateView: updateViewContrast
  };

  window.toggleContrast = function() {
    Contrast.toggle();
  };

  Contrast.check();

  function checkContrast() {
    this.updateView();
  }

  function getContrastState() {
    return sessionStorage.getItem(this.storage) === "true";
  }

  function setContrastState(state) {
    sessionStorage.setItem(this.storage, "" + state);
    this.currentState = state;
    this.updateView();
  }

  function updateViewContrast() {
    if (this.currentState === null) this.currentState = this.getState();

    this.currentState
      ? body.classList.add(this.cssClass)
      : body.classList.remove(this.cssClass);
  }

  function toggleContrast() {
    this.setState(!this.currentState);
    Dark.currentState === true ? Dark.setState(false) : null;
  }

  /*
=== === === === === === === === === === === === === === === === === ===
=== === === === === === ===   DarkMode  === === === === === === === ===
=== === === === === === === === === === === === === === === === === ===
*/
  let Dark = {
    storage: "darkState",
    cssClass: "scielo__theme--dark",
    currentState: null,
    check: checkDark,
    getState: getDarkState,
    setState: setDarkState,
    toggle: toggleDark,
    updateView: updateViewDark
  };

  window.toggleDark = function() {
    Dark.toggle();
  };

  Dark.check();

  function checkDark() {
    this.updateView();
  }

  function getDarkState() {
    return sessionStorage.getItem(this.storage) === "true";
  }

  function setDarkState(state) {
    sessionStorage.setItem(this.storage, "" + state);
    this.currentState = state;
    this.updateView();
  }

  function updateViewDark() {
    if (this.currentState === null) this.currentState = this.getState();

    this.currentState
      ? body.classList.add(this.cssClass)
      : body.classList.remove(this.cssClass);
  }

  function toggleDark() {
    this.setState(!this.currentState);
    Contrast.currentState === true ? Contrast.setState(false) : null;
  }
})();
