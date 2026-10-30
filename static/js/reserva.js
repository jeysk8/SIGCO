(function () {
    const MAX_PISCINA = 5;

    document.querySelectorAll('select[name="tipo_servicio"]').forEach(function (selServicio) {
        const idInput = selServicio.dataset.invitados;
        const inputInvitados = document.getElementById(idInput);
        if (!inputInvitados) return;

        function ajustar() {
            if (selServicio.value === 'piscina') {
                inputInvitados.max = MAX_PISCINA;
                if (parseInt(inputInvitados.value) > MAX_PISCINA) {
                    inputInvitados.value = MAX_PISCINA;
                }
            } else {
                inputInvitados.removeAttribute('max');
            }
        }

        selServicio.addEventListener('change', ajustar);
        ajustar();
    });
})();