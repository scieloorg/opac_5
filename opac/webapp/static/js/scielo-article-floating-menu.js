
document.addEventListener("DOMContentLoaded", function() {

    const tooltipTriggers = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggers.forEach(trigger => {
        if (!isTouchDevice()) {
            new bootstrap.Tooltip(trigger);
        }
    });
    
    tooltipTriggers.forEach(link => {
        link.addEventListener("click", function(event) {
            if (link.classList.contains("item-goto")) {
                const tooltipInstance = bootstrap.Tooltip.getInstance(link);
                if (tooltipInstance) {
                    tooltipInstance.hide();
                }
            } else {
                event.preventDefault();
    
                const modalTarget = document.querySelector(this.getAttribute("data-bs-target"));
                if (modalTarget) {
                    const modal = new bootstrap.Modal(modalTarget);
                    modal.show();
                }
            }
        });
    });
    
});

const btnOpen = document.querySelector('.fm-button-main');
const btnClose = document.querySelector('.fm-button-close');
const fmListDesktop = document.querySelector('.fm-list-desktop');
const fmListMobile = document.querySelector('.fm-list-mobile');

function isTouchDevice() {
    return window.matchMedia('(pointer: coarse)').matches;
}

function isMouseDevice() {
    return window.matchMedia('(pointer: fine)').matches;
}

function removerTooltipsVisiveis() {
    const fmListItems = document.querySelectorAll('.fm-list-desktop li a[data-bs-toggle="tooltip"]');
    fmListItems.forEach((item) => {
        const tooltipInstance = bootstrap.Tooltip.getInstance(item); 
        if (tooltipInstance) {
            tooltipInstance.hide(); 
            tooltipInstance.dispose(); 
        }
    });
}

function aplicarTransformacoes() {
    const isMobile = isTouchDevice();
    const fmListItems = Array.from(
        document.querySelectorAll(isMobile ? '.fm-list-mobile li' : '.fm-list-desktop li')
    ).filter(item => {
        const fmList = item.closest(isMobile ? '.fm-list-mobile' : '.fm-list-desktop');
        return fmList && window.getComputedStyle(fmList).display !== 'none';
    });

    fmListItems.forEach((item, index) => {
        const link = item.querySelector('a');
        if (link) {
            link.style.display = 'block';
            link.style.opacity = '0';
            link.style.transition = 'opacity 0.3s ease';

            requestAnimationFrame(() => {
                link.style.opacity = '1';
            });
        }

        const pos = (index + 1) * 47;
        item.style.transform = isMobile ? `translateY(-${pos}px)` : `translateX(${pos}px)`;
        item.style.transition = 'transform 0.3s ease';
    });


}

function resetarTransformacoes() {
    const isMobile = isTouchDevice();
    const fmListItems = Array.from(
        document.querySelectorAll(isMobile ? '.fm-list-mobile li' : '.fm-list-desktop li')
    );

    fmListItems.forEach((item, index) => {
        const link = item.querySelector('a');

        if (link) {
            link.style.opacity = '0'; 
            link.style.transition = 'opacity 0.3s ease'; 

            setTimeout(() => {
                link.style.display = 'none'; 
            }, 300); 
        }

        item.style.transform = 'translateY(0)';
        item.style.transition = 'transform 0.3s ease'; 
    });
}

function abrirLista() {
    fmListMobile.style.display = 'block';
    fmListDesktop.style.display = 'block';
    btnClose.style.display = 'block';
    btnOpen.style.display = 'none';

    aplicarTransformacoes();

    document.addEventListener('click', fecharAoClicarFora);
}

function fecharLista() {
    fmListMobile.style.display = 'none';
    fmListDesktop.style.display = 'none';
    btnClose.style.display = 'none';
    btnOpen.style.display = 'block';

    if (isTouchDevice()) {
        removerTooltipsVisiveis();
    }

    resetarTransformacoes();
    document.removeEventListener('click', fecharAoClicarFora);
}

function fecharAoClicarFora(event) {
    if (!fmListMobile.contains(event.target) && !btnOpen.contains(event.target) && !btnClose.contains(event.target)) {
        fecharLista();
    }
    if (!fmListDesktop.contains(event.target) && !btnOpen.contains(event.target) && !btnClose.contains(event.target)) {
        fecharLista();
    }
}

function configurarEventos() {
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    btnOpen.addEventListener('click', abrirLista);
    btnClose.addEventListener('click', fecharLista);
}

const menuItems = document.querySelectorAll('.fm-list-desktop');

menuItems.forEach(item => {
    item.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            item.click(); 
        }
    });
});

function init() {
    if ((btnOpen && fmListMobile) || (btnOpen && fmListDesktop)) {
        configurarEventos();
        window.addEventListener('resize', init);
    }
}

init();