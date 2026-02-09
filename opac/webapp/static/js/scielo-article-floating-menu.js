document.addEventListener("DOMContentLoaded", function() {

    // Desabilita tooltips completamente
    const tooltipTriggers = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggers.forEach(trigger => {
        const tooltipInstance = bootstrap.Tooltip.getInstance(trigger);
        if (tooltipInstance) tooltipInstance.dispose();
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
const fmList = document.querySelector('.fm-list-mobile'); // usa sempre o menu mobile

function removerTooltipsVisiveis() {
    const fmListItems = document.querySelectorAll('.fm-list-mobile li a[data-bs-toggle="tooltip"]');
    fmListItems.forEach((item) => {
        const tooltipInstance = bootstrap.Tooltip.getInstance(item); 
        if (tooltipInstance) {
            tooltipInstance.hide(); 
            tooltipInstance.dispose(); 
        }
    });
}

function aplicarTransformacoes() {
    const fmListItems = Array.from(document.querySelectorAll('.fm-list-mobile li')).filter(item => {
        const fmList = item.closest('.fm-list-mobile');
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
        item.style.transform = `translateY(-${pos}px)`; // sempre vertical
        item.style.transition = 'transform 0.3s ease';
    });
}

function resetarTransformacoes() {
    const fmListItems = Array.from(document.querySelectorAll('.fm-list-mobile li'));
    fmListItems.forEach((item) => {
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
    fmList.style.display = 'block';
    btnClose.style.display = 'block';
    btnOpen.style.display = 'none';
    aplicarTransformacoes();
    document.addEventListener('click', fecharAoClicarFora);
}

function fecharLista() {
    fmList.style.display = 'none';
    btnClose.style.display = 'none';
    btnOpen.style.display = 'block';
    removerTooltipsVisiveis();
    resetarTransformacoes();
    document.removeEventListener('click', fecharAoClicarFora);
}

function fecharAoClicarFora(event) {
    if (!fmList.contains(event.target) && !btnOpen.contains(event.target) && !btnClose.contains(event.target)) {
        fecharLista();
    }
}

function configurarEventos() {
    btnOpen.addEventListener('click', abrirLista);
    btnClose.addEventListener('click', fecharLista);
}

function init() {
    if (btnOpen && fmList) {
        configurarEventos();
        window.addEventListener('resize', init);
    }
}

init();
