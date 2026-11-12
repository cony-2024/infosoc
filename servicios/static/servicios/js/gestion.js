// Vista de gestión diaria para el profesional autenticado.
const $ = (id) => document.getElementById(id);
const csrf = () => document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] ?? "";
const hoy = () => new Date().toLocaleDateString("sv-SE");
const ETIQUETA = { pendiente: "Pendiente", confirmada: "Confirmada", cancelada: "Cancelada" };

function celda(texto) { const td = document.createElement("td"); td.textContent = texto; return td; }

async function cargar() {
  const r = await fetch(`/api/agenda/?fecha=${$("fecha").value}`);
  const tbody = $("citas");
  if (!r.ok) { tbody.innerHTML = '<tr><td colspan="6">No tienes permiso para consultar esta agenda.</td></tr>'; return; }
  const { citas } = await r.json();
  const activas = citas.filter((c) => c.estado !== "cancelada").length;
  $("resumen-dia").textContent = `${activas} cita(s) activa(s) · ${citas.length - activas} cancelada(s)`;
  if (!citas.length) { tbody.innerHTML = '<tr><td colspan="6">Sin citas para este día.</td></tr>'; return; }
  tbody.replaceChildren(...citas.map((c) => {
    const tr = document.createElement("tr");
    tr.className = "est-" + c.estado;
    tr.append(celda(c.hora), celda(`${c.cliente.nombre} (${c.cliente.telefono || "sin fono"})`),
              celda(c.servicio), celda(c.profesional));
    const est = document.createElement("td");
    est.innerHTML = `<span class="chip ${c.estado}"></span>`; est.firstChild.textContent = ETIQUETA[c.estado];
    const acc = document.createElement("td");
    for (const [estado, txt] of [["confirmada", "Confirmar"], ["cancelada", "Cancelar"]]) {
      if (c.estado === estado) continue;
      const b = document.createElement("button");
      b.className = "boton boton-chico"; b.textContent = txt;
      b.onclick = async () => {
        const respuesta = await fetch(`/api/citas/${c.id}/estado/`, {
          method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
          body: JSON.stringify({ estado }),
        });
        if (!respuesta.ok) { window.alert("No se pudo actualizar el estado de la cita."); return; }
        cargar();
      };
      acc.append(b, " ");
    }
    tr.append(est, acc);
    return tr;
  }));
}

function mover(dias) {
  const d = new Date($("fecha").value + "T12:00:00"); d.setDate(d.getDate() + dias);
  $("fecha").value = d.toLocaleDateString("sv-SE"); cargar();
}
$("fecha").value = hoy();
$("fecha").onchange = cargar;
$("ayer").onclick = () => mover(-1);
$("manana").onclick = () => mover(1);
$("hoy").onclick = () => { $("fecha").value = hoy(); cargar(); };
cargar();
