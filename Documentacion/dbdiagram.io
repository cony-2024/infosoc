// si quieren usar este codigo copienlo y peguendo en https://dbdiagram.io/ ahi se genera el diagrama pero desordenado, ahi yo lo ordene y le tome captura, es la imagen modelo_propuesto_copilot.png

Table servicios_servicio {
  id bigint [pk, increment]
  nombre varchar(100) [not null]
  descripcion text [not null]
  precio decimal(10,2) [not null]
  duracion_minutos smallint [not null]
  activo boolean [not null, default: true]
  creado_en datetime [not null]
}

Table servicios_cliente {
  id bigint [pk, increment]
  nombre varchar(150) [not null]
  rut varchar(12) [not null, unique]
  email varchar(254) [not null]
  telefono varchar(20) [not null]
}

Table servicios_profesional {
  id bigint [pk, increment]
  nombre varchar(150) [not null]
  rut varchar(12) [not null, unique]
  activo boolean [not null, default: true]
}

// Tabla intermedia que Django crea para la relación muchos a muchos
// entre Profesional y Servicio.
Table servicios_profesional_servicios {
  id bigint [pk, increment]
  profesional_id bigint [not null]
  servicio_id bigint [not null]

  indexes {
    (profesional_id, servicio_id) [unique]
  }
}

Table servicios_horariotrabajo {
  id bigint [pk, increment]
  profesional_id bigint [not null]
  dia smallint [not null, note: '0=Lunes, 1=Martes, ..., 6=Domingo']
  hora_entrada time [not null]
  hora_salida time [not null]
}

Table servicios_bloqueohorario {
  id bigint [pk, increment]
  profesional_id bigint [not null]
  inicio datetime [not null]
  fin datetime [not null]
  motivo varchar(200) [not null]
}

Table servicios_cita {
  id bigint [pk, increment]
  cliente_id bigint [not null]
  profesional_id bigint [not null]
  servicio_id bigint [not null]
  inicio datetime [not null]
  fin datetime [not null]
  estado varchar(12) [not null, default: 'pendiente', note: 'pendiente, confirmada o cancelada']
  creado_en datetime [not null]
}

Ref: servicios_profesional_servicios.profesional_id > servicios_profesional.id
Ref: servicios_profesional_servicios.servicio_id > servicios_servicio.id

Ref: servicios_horariotrabajo.profesional_id > servicios_profesional.id
Ref: servicios_bloqueohorario.profesional_id > servicios_profesional.id

Ref: servicios_cita.cliente_id > servicios_cliente.id
Ref: servicios_cita.profesional_id > servicios_profesional.id
Ref: servicios_cita.servicio_id > servicios_servicio.id