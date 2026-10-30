
const settingsBtn = document.getElementById('settings-btn');
const settingsDropdown = document.getElementById('settings-dropdown');

const vistaBtn = document.getElementById('vista-btn');
const vistaDropdown = document.getElementById('vista-dropdown');

// Abrir y cerrar el menú de configuración
if (settingsBtn && settingsDropdown) {
    settingsBtn.addEventListener('click', (e) => {
        e.stopPropagation();

        // Cerrar el menú de cambio de vista, si existe
        if (vistaDropdown && vistaBtn) {
            vistaDropdown.classList.remove('open');
            vistaBtn.setAttribute('aria-expanded', 'false');
        }

        const abierto = settingsDropdown.classList.toggle('open');
        settingsBtn.setAttribute('aria-expanded', String(abierto));
    });
}

// Abrir y cerrar el menú para cambiar de vista
if (vistaBtn && vistaDropdown) {
    vistaBtn.addEventListener('click', (e) => {
        e.stopPropagation();

        // Cerrar el menú de configuración
        if (settingsDropdown && settingsBtn) {
            settingsDropdown.classList.remove('open');
            settingsBtn.setAttribute('aria-expanded', 'false');
        }

        const abierto = vistaDropdown.classList.toggle('open');
        vistaBtn.setAttribute('aria-expanded', String(abierto));
    });
}

// Cerrar los menús al hacer clic fuera de ellos
document.addEventListener('click', (e) => {
    if (
        settingsDropdown &&
        settingsBtn &&
        !settingsDropdown.contains(e.target) &&
        !settingsBtn.contains(e.target)
    ) {
        settingsDropdown.classList.remove('open');
        settingsBtn.setAttribute('aria-expanded', 'false');
    }

    if (
        vistaDropdown &&
        vistaBtn &&
        !vistaDropdown.contains(e.target) &&
        !vistaBtn.contains(e.target)
    ) {
        vistaDropdown.classList.remove('open');
        vistaBtn.setAttribute('aria-expanded', 'false');
    }
});
