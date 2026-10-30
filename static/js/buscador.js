(function () {
    const input = document.getElementById('buscador');
    const tabla = document.querySelector('table.tabla');
    if (!input || !tabla) return;

    // quita mayúsculas y tildes para que "jose" encuentre "José"
    function normalizar(texto) {
        return texto.toLowerCase()
                    .normalize('NFD')
                    .replace(/[\u0300-\u036f]/g, '');
    }

    input.addEventListener('input', function () {
        const busqueda = normalizar(input.value.trim());

        tabla.querySelectorAll('tbody tr').forEach(function (fila) {
            const texto = normalizar(fila.textContent);
            fila.style.display = texto.includes(busqueda) ? '' : 'none';
        });
    });
})();