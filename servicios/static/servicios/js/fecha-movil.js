// Selectores de día, mes y año para celular. El campo <input type="date" id="fecha">
// sigue siendo la fuente de verdad: reservar.js lo lee y escucha su evento "change".
(function () {
  // Si el script se carga dos veces, la segunda vez no hace nada
  if (window.__fechaMovilIniciado) return;
  window.__fechaMovilIniciado = true;

  const fecha = document.getElementById('fecha');
  const dia = document.getElementById('sel-dia');
  const mes = document.getElementById('sel-mes');
  const anio = document.getElementById('sel-anio');
  if (!fecha || !dia || !mes || !anio) return;

  const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
                 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
  const hoy = new Date();
  const anioActual = hoy.getFullYear();
  const dos = (n) => String(n).padStart(2, '0');


  anio.innerHTML = '';
  mes.innerHTML = '';
  [anioActual, anioActual + 1].forEach((a) => anio.add(new Option(a, a)));
  MESES.forEach((nombre, i) => mes.add(new Option(nombre, i + 1)));

  function llenarDias() {
    const elegido = Number(dia.value) || 1;
    const total = new Date(anio.value, mes.value, 0).getDate(); 
    dia.innerHTML = '';
    for (let d = 1; d <= total; d++) dia.add(new Option(d, d));
    dia.value = Math.min(elegido, total);
  }

  function desdeInput() {
    if (!fecha.value) return;
    const [a, m, d] = fecha.value.split('-').map(Number);
    anio.value = a;
    mes.value = m;
    llenarDias();
    dia.value = d;
  }


  function pasarAlInput() {
    let iso = `${anio.value}-${dos(mes.value)}-${dos(dia.value)}`;
    if (fecha.min && iso < fecha.min) iso = fecha.min;
    if (fecha.value !== iso) {
      fecha.value = iso;
      fecha.dispatchEvent(new Event('change', { bubbles: true }));
    }
    desdeInput(); 
  }

  function sincronizar() {
    [dia, mes, anio].forEach((s) => { s.disabled = fecha.disabled; });
    desdeInput();
  }

  [anio, mes].forEach((s) => s.addEventListener('change', () => { llenarDias(); pasarAlInput(); }));
  dia.addEventListener('change', pasarAlInput);
  fecha.addEventListener('change', desdeInput);

  new MutationObserver(sincronizar).observe(fecha, {
    attributes: true,
    attributeFilter: ['disabled', 'min'],
  });

  anio.value = anioActual;
  mes.value = hoy.getMonth() + 1;
  llenarDias();
  dia.value = hoy.getDate();
  sincronizar();
})();