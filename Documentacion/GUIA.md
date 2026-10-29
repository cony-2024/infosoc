# Guía de avance — Beauty Corner (Arquitectura/Backend + Frontend)

## 0. Diagnóstico de lo que había
| Tema | Estado inicial |
|---|---|
| Supabase | **No estaba conectado.** `settings.py` usaba SQLite (`db.sqlite3`) y no había rastro de Supabase. |
| Modelos | Bien: Servicio, Cliente, Profesional, HorarioTrabajo, BloqueoHorario, Cita, con validaciones. |
| Backend | Sin API. Solo una vista `index`. |
| Frontend | Una landing estática; los servicios estaban escritos a mano en el HTML. |
| Rama `main` | Vacía (plantilla de Django). Todo el trabajo estaba en `infosoc-database-rama`. |
| Seguridad | `SECRET_KEY` escrita en el código; `admin.py` vacío. |

## 1. Conectar Supabase (paso a paso)
1. En [supabase.com](https://supabase.com) crea un proyecto. Guarda la **contraseña de la base de datos**.
2. Botón **Connect** → **Session pooler** → copia la cadena `postgresql://postgres.xxxx:[YOUR-PASSWORD]@...:5432/postgres`.
   Usa *Session pooler* (no *Direct*): la conexión directa suele requerir IPv6 y falla en muchas redes.
3. En la carpeta del proyecto: `cp .env.example .env` y pega la cadena en `DATABASE_URL`.
4. Instala y migra:
   ```bash
   python -m venv env && source env/bin/activate      # Windows: env\Scripts\activate
   pip install -r requirements.txt
   python manage.py migrate        # crea las tablas EN Supabase
   python manage.py seed_demo      # servicios, profesionales y horarios de ejemplo
   python manage.py createsuperuser
   python manage.py runserver
   ```
5. Verifica en Supabase → **Table Editor**: deben aparecer `servicios_servicio`, `servicios_cita`, etc.
   Si no defines `DATABASE_URL`, el proyecto sigue funcionando con SQLite local.

> Si un compañero no tiene `.env`, trabajará con SQLite. Para compartir la base, pasen la contraseña por privado (nunca por git).

## 2. Qué archivos se modificaron / crearon
**Backend (Franco)**
- `salon_de_belleza/settings.py` → `DATABASE_URL`, `.env`, zona horaria `America/Santiago`, idioma `es-cl`.
- `servicios/models.py` → campo `categoria` en Servicio; `Cita.save()` ahora valida (antes `clean()` no se ejecutaba al guardar).
- `servicios/migrations/0004…` y `0005…` → categoría + restricción anti-solapamiento en PostgreSQL.
- `servicios/disponibilidad.py` → **algoritmo de horas libres**.
- `servicios/api.py` → **API REST**. `salon_de_belleza/urls.py` → rutas.
- `servicios/admin.py` → panel `/admin/` para gestionar todo.
- `servicios/management/commands/seed_demo.py`, `servicios/tests.py` (4 tests, pasan).
- `requirements.txt`, `.env.example`, `.gitignore`.
- `Documentacion/schema.sql` (DDL) y `Documentacion/dbdiagram.io` (ER).

**Frontend (Constanza)**
- `templates/servicios/base.html` (layout común), `index.html` (catálogo desde la BD), `reservar.html`, `gestion.html`.
- `static/servicios/js/reservar.js` y `gestion.js`; `static/servicios/css/styles.css` (estilos añadidos al final).

## 3. API REST
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/servicios/` | Catálogo de servicios activos |
| GET | `/api/profesionales/?servicio=ID` | Profesionales que ofrecen el servicio |
| GET | `/api/disponibilidad/?servicio=ID&fecha=AAAA-MM-DD[&profesional=ID]` | **Horas libres** del día |
| POST | `/api/citas/` | Crea cita (valida horario, solapamientos y bloqueos; 409 si está ocupada) |
| GET | `/api/agenda/?fecha=AAAA-MM-DD` | Citas del día (solo admin) |
| POST | `/api/citas/ID/estado/` | `{"estado":"confirmada"}` o `cancelada` (solo admin) |

Cómo calcula la disponibilidad: toma los turnos del profesional ese día de la semana, genera horas de inicio cada 30 min (`PASO_MINUTOS`) mientras el servicio quepa en el turno, y descarta las que chocan con citas activas, bloqueos o que ya pasaron.

## 4. Modelo ER
```mermaid
erDiagram
  SERVICIO ||--o{ CITA : "se reserva en"
  CLIENTE ||--o{ CITA : agenda
  PROFESIONAL ||--o{ CITA : atiende
  PROFESIONAL }o--o{ SERVICIO : ofrece
  PROFESIONAL ||--o{ HORARIO_TRABAJO : tiene
  PROFESIONAL ||--o{ BLOQUEO_HORARIO : tiene
```
Para el diagrama visual: pega `Documentacion/dbdiagram.io` en dbdiagram.io y acomódalo.

## 5. Cómo probarlo
- `python manage.py test servicios` → 4 tests (catálogo, disponibilidad, doble reserva, permisos de admin).
- `http://localhost:8000/` catálogo · `/reservar/` selector · `/gestion/` agenda diaria (login de admin) · `/admin/`.
- Prueba la API en el navegador: `/api/disponibilidad/?servicio=1&fecha=<un lunes>`.

## 6. Pendiente / siguientes pasos (honesto)
- No lo probé contra **tu** Supabase (no tengo tus credenciales); sí contra SQLite y la lógica es la misma. La restricción `0005` solo corre en PostgreSQL: si `migrate` falla ahí, avísame el error.
- Cita nueva queda **pendiente**; el admin la confirma en `/gestion/`.
- Falta: imágenes por servicio, correo/WhatsApp de confirmación, validar formato de RUT, paso del slot configurable por servicio, publicar (Render/Railway) con `DEBUG=False`.
- Seguridad: la `SECRET_KEY` antigua estaba en git; genera una nueva para producción. Activa RLS en Supabase si algún día usas su API pública (Django conecta como `postgres` y no la necesita).
- Git: haz merge de la rama a `main` (hoy `main` está vacía).