/**
 * main.js
 * -------
 * Lógica del formulario de registro/edición de movimientos:
 * al cambiar el tipo de movimiento (Ingreso/Gasto/Ahorro),
 * recarga vía API solo las categorías correspondientes a ese tipo.
 */

document.addEventListener("DOMContentLoaded", function () {
    const radios = document.querySelectorAll('input[name="type"]');
    const selectCategoria = document.getElementById("selectCategoria");

    if (!radios.length || !selectCategoria) return;

    async function cargarCategorias(tipo) {
        try {
            const resp = await fetch(`/api/categorias/${tipo}`);
            const data = await resp.json();
            selectCategoria.innerHTML = "";
            data.forEach((cat) => {
                const option = document.createElement("option");
                option.value = cat.id;
                option.textContent = cat.name;
                selectCategoria.appendChild(option);
            });
            if (data.length === 0) {
                const option = document.createElement("option");
                option.textContent = "No hay categorías activas para este tipo";
                option.disabled = true;
                selectCategoria.appendChild(option);
            }
        } catch (err) {
            console.error("No se pudieron cargar las categorías:", err);
        }
    }

    radios.forEach((radio) => {
        radio.addEventListener("change", (e) => cargarCategorias(e.target.value));
    });
});
