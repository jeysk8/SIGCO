(function () {
    const contenedor = document.getElementById('datos-asignados');
    const selUsuario = document.getElementById('selUsuario');
    const selRol = document.getElementById('selRol');
    if (!contenedor || !selUsuario || !selRol) return;

    const datosAsignados = JSON.parse(contenedor.dataset.asignados);

    selUsuario.addEventListener('change', function () {
        const idu = parseInt(this.value);
        const yaTiene = datosAsignados.filter(a => a[0] === idu).map(a => a[1]);

        selRol.querySelectorAll('option').forEach(op => {
            if (!op.value) return;
            const ocultar = yaTiene.includes(parseInt(op.value));
            op.hidden = ocultar;
            op.disabled = ocultar;
        });
        selRol.value = '';
    });
})();