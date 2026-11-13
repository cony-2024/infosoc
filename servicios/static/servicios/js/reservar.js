// Selector de reserva: servicio → profesional → fecha → hora → datos.
const $ = (id) => document.getElementById(id);
const estado = { servicio: null, profesional: null, hora: null, servicios: [] };
const csrf = () => document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] ?? "";
const clp = (n) => "$" + n.toLocaleString("es-CL");
const get = (url) => fetch(url).then((r) => r.json());

function boton(texto, sub, activo, onclick) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "opcion" + (activo ? " activa" : "");
  b.innerHTML = `<strong></strong><small></small>`;
  b.firstChild.textContent = texto;
  b.lastChild.textContent = sub || "";
  b.onclick = onclick;
  return b;
}

// ===== Servicios en celular: categorías + menú desplegable =====
const esMovil = window.matchMedia("(pointer: coarse)").matches;
// Categorías tal como están en la base de datos (el orden es el de los botones)
const CATEGORIAS = { depilacion: "Depilación", manos: "Manos", pies: "Pies", otros: "Otros" };
const ORDEN_CATEGORIAS = Object.values(CATEGORIAS);
let reflejarMovil = () => {};

const sinTildes = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

// Usa la categoría que viene del backend (s.categoria), venga como código o como
// texto. Solo si el servicio no la trae, la deduce del nombre.
function categoriaDe(s) {
  if (s.categoria) {
    return CATEGORIAS[sinTildes(String(s.categoria))] ?? String(s.categoria);
  }
  const n = s.nombre.toLowerCase();
  if (/promo/.test(n)) return CATEGORIAS.otros;
  if (/pedicur/.test(n)) return CATEGORIAS.pies;
  if (/manicur|kapping|soft gel|polygel|rubber|extension/.test(n)) return CATEGORIAS.manos;
  if (/abdomen|axila|bozo|brazo|espalda|pierna|rebaje|depil/.test(n)) return CATEGORIAS.depilacion;
  return CATEGORIAS.otros;
}

function dibujarServiciosMovil(cont, servicios) {
  const porCategoria = {};
  servicios.forEach((s) => (porCategoria[categoriaDe(s)] ??= []).push(s));
  const indice = (c) => (ORDEN_CATEGORIAS.includes(c) ? ORDEN_CATEGORIAS.indexOf(c) : ORDEN_CATEGORIAS.length);
  const categorias = Object.keys(porCategoria).sort((a, b) => indice(a) - indice(b));

  const chips = document.createElement("div");
  chips.className = "cats-movil";
  const select = document.createElement("select");
  select.className = "select-servicio";
  select.setAttribute("aria-label", "Servicio");
  const elegido = document.createElement("p");
  elegido.className = "seleccion-movil";

  const mostrar = (s) => {
    elegido.textContent = s ? `Elegido: ${s.nombre} · ${s.duracion_minutos} min · ${clp(s.precio)}` : "";
  };

  function llenar(cat, actual) {
    chips.querySelectorAll(".cat-chip").forEach((b) => b.classList.toggle("activa", b.dataset.cat === cat));
    select.replaceChildren();
    const guia = new Option("Elige un servicio", "");
    guia.disabled = true;
    guia.hidden = true;
    select.add(guia);
    porCategoria[cat].forEach((s) => select.add(new Option(`${s.nombre} · ${clp(s.precio)}`, s.id)));
    if (actual) select.value = String(actual.id);
    else select.selectedIndex = 0;
  }

  categorias.forEach((cat) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cat-chip";
    b.dataset.cat = cat;
    b.textContent = cat;
    b.onclick = () => llenar(cat, estado.servicio && categoriaDe(estado.servicio) === cat ? estado.servicio : null);
    chips.append(b);
  });

  select.onchange = () => {
    const s = servicios.find((x) => String(x.id) === select.value);
    if (!s) return;
    mostrar(s);
    elegirServicio(s);
  };

  reflejarMovil = (s) => { llenar(categoriaDe(s), s); mostrar(s); };

  cont.className = "servicios-movil";
  cont.replaceChildren(chips, select, elegido);
  llenar(categorias[0], null);
}

async function cargarServicios() {
  const { servicios } = await get("/api/servicios/");
  estado.servicios = servicios;
  const cont = $("servicios");
  if (esMovil) {
    dibujarServiciosMovil(cont, servicios);
  } else {
    cont.replaceChildren(...servicios.map((s) =>
      boton(s.nombre, `${s.duracion_minutos} min · ${clp(s.precio)}`, estado.servicio?.id === s.id, () => elegirServicio(s))));
  }
  const pre = Number($("app").dataset.servicio);
  if (pre && !estado.servicio) {
    const s = servicios.find((x) => x.id === pre);
    if (s) {
      elegirServicio(s);
      if (esMovil) reflejarMovil(s);
    }
  }
}

async function elegirServicio(s) {
  estado.servicio = s; estado.profesional = null; estado.hora = null;
  document.querySelectorAll("#servicios .opcion").forEach((b, i) =>
    b.classList.toggle("activa", estado.servicios[i].id === s.id));
  const { profesionales } = await get(`/api/profesionales/?servicio=${s.id}`);
  const cont = $("profesionales");
  cont.replaceChildren(
    boton("Cualquiera", "Primera hora libre", true, () => elegirProfesional(null, cont)),
    ...profesionales.map((p) => boton(p.nombre, "", false, () => elegirProfesional(p, cont))));
  const f = $("fecha");
  f.disabled = false;
  f.min = new Date().toLocaleDateString("sv-SE");
  if (!f.value) f.value = f.min;
  cargarHoras();
}

function elegirProfesional(p, cont) {
  estado.profesional = p;
  [...cont.children].forEach((b, i) => b.classList.toggle("activa", p ? b.firstChild.textContent === p.nombre : i === 0));
  cargarHoras();
}

async function cargarHoras() {
  estado.hora = null; actualizarResumen();
  if (!estado.servicio || !$("fecha").value) return;
  let url = `/api/disponibilidad/?servicio=${estado.servicio.id}&fecha=${$("fecha").value}`;
  if (estado.profesional) url += `&profesional=${estado.profesional.id}`;
  const { horas } = await get(url);
  const cont = $("horas");
  if (!horas.length) { cont.innerHTML = '<p class="nota">No hay horas disponibles ese día. Prueba otra fecha.</p>'; return; }
  cont.replaceChildren(...horas.map((h) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "hora"; b.textContent = h.hora;
    b.onclick = () => {
      estado.hora = h;
      cont.querySelectorAll(".hora").forEach((x) => x.classList.toggle("activa", x === b));
      actualizarResumen();
    };
    return b;
  }));
}

function actualizarResumen() {
  const r = $("resumen"), ok = estado.servicio && estado.hora;
  r.hidden = !ok; $("enviar").disabled = !ok;
  if (ok) r.textContent = `${estado.servicio.nombre} · ${$("fecha").value} a las ${estado.hora.hora} · ${clp(estado.servicio.precio)}`;
}

function limpiarErrores() {
  for (const campo of ["nombre", "telefono", "email"]) {
    const input = document.querySelector(`[name="${campo}"]`);
    input.setCustomValidity("");
    input.removeAttribute("aria-invalid");
    $(`error-${campo}`).textContent = "";
  }
}

function mostrarErrores(data) {
  limpiarErrores();
  const campos = { nombre: "Nombre", telefono: "Teléfono", email: "Email" };
  const detalles = data.detalles;
  if (detalles && !Array.isArray(detalles) && typeof detalles === "object") {
    const generales = [];
    for (const [campo, mensajes] of Object.entries(detalles)) {
      const texto = Array.isArray(mensajes) ? mensajes.join(" ") : String(mensajes);
      if (campos[campo]) {
        const input = document.querySelector(`[name="${campo}"]`);
        input.setCustomValidity(texto);
        input.setAttribute("aria-invalid", "true");
        $(`error-${campo}`).textContent = texto;
      } else {
        generales.push(texto);
      }
    }
    const conError = Object.keys(campos).find((campo) => $(`error-${campo}`).textContent);
    $("mensaje").textContent = generales[0] || (conError ? "Corrige el campo indicado." : data.error);
    if (conError) document.querySelector(`[name="${conError}"]`).reportValidity();
    return;
  }
  $("mensaje").textContent = Array.isArray(detalles) ? detalles.join(" ") : data.error || "No se pudo agendar.";
}

const mensajesRequeridos = {
  nombre: "Escribe tu nombre.",
  telefono: "Escribe tu teléfono.",
};

for (const campo of ["nombre", "telefono", "email"]) {
  const input = document.querySelector(`[name="${campo}"]`);
  input.addEventListener("invalid", () => {
    if (!input.validity.customError) {
      if (input.validity.valueMissing) {
        input.setCustomValidity(mensajesRequeridos[campo] || `Completa el campo ${campo}.`);
      } else if (input.validity.typeMismatch && campo === "email") {
        input.setCustomValidity("Ingresa un correo válido, por ejemplo nombre@dominio.cl.");
      } else if (input.validity.patternMismatch && campo === "telefono") {
        input.setCustomValidity("Teléfono inválido. Ingresa 9 dígitos chilenos, por ejemplo 9 1234 5678 o +56 9 1234 5678.");
      }
    }
    input.setAttribute("aria-invalid", "true");
    $(`error-${campo}`).textContent = input.validationMessage;
  });
}

$("fecha").addEventListener("change", cargarHoras);

$("form-cita").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target), msg = $("mensaje");
  limpiarErrores();
  msg.textContent = "";
  const profesional = estado.profesional?.id ?? estado.hora.profesionales[0];
  $("enviar").disabled = true;
  const r = await fetch("/api/citas/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
    body: JSON.stringify({
      servicio: estado.servicio.id, profesional, inicio: estado.hora.inicio,
      cliente: {
        ...Object.fromEntries(f),
        acepta_politica_privacidad: f.has("acepta_politica_privacidad"),
      },
    }),
  });
  const data = await r.json();
  if (r.status === 201) {
    msg.className = "ok";
    msg.textContent = `¡Listo! Tu hora quedó agendada para el ${$("fecha").value} a las ${estado.hora.hora}. Estado: pendiente de confirmación.`;
    e.target.reset(); estado.hora = null; actualizarResumen();
  } else {
    msg.className = "error";
    mostrarErrores(data);
    cargarHoras();
  }
});

for (const campo of ["nombre", "telefono", "email"]) {
  const input = document.querySelector(`[name="${campo}"]`);
  input.addEventListener("input", () => {
    input.setCustomValidity("");
    if (input.validity.valid) input.removeAttribute("aria-invalid");
    else input.setAttribute("aria-invalid", "true");
    $(`error-${campo}`).textContent = "";
  });
}

cargarServicios();
