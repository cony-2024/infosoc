# Guía del proyecto — Beauty Corner

Guía del estado actual del código en la rama `database-rama`. Las secciones de despliegue y servicios externos describen configuración disponible, no certifican que una instancia de producción esté desplegada.

## 1. Requisitos y configuración local

- Python compatible con Django 6.1.
- Windows PowerShell (o una terminal equivalente), Git y las dependencias de `requirements.txt`.
- SQLite se usa por defecto. PostgreSQL/Supabase se configura mediante `DATABASE_URL`.

En Windows, desde la raíz del proyecto:

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
```

Sobre el archivo `.env`, fue compartido por discord, debes ponerlo en la raíz del proyecto.

Si no funciona la conexión con la bd, puedes aplicar las migraciones. Antes de ejecutar la migración `0007`, haz un respaldo: elimina el RUT de las clientas según el esquema nuevo y detiene la migración si encuentra teléfonos vacíos/inválidos o teléfonos/correos duplicados. Corrige esos registros antes de volver a intentarlo.

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

`seed_demo` carga o actualiza servicios de ejemplo y crea profesionales/horarios de demostración. No es necesario para ejecutar las migraciones.

Para dar acceso a un profesional, crea una cuenta de usuario desde `/admin/auth/user/add/` y luego asígnala al registro correspondiente en `/admin/servicios/profesional/`. Cada cuenta debe pertenecer a un solo profesional. El profesional inicia sesión en `/ingresar/`; las cuentas sin asociación activa no pueden abrir la agenda.

## 2. Funcionalidades implementadas

- Catálogo público de servicios activos, agrupado por categoría.
- Flujo de reserva para elegir servicio, profesional opcional, fecha y hora.
- Política de privacidad pública en `/privacidad/`, enlazada desde el formulario y el pie de página.
- Registro de clientas por teléfono normalizado; correo opcional y consentimiento de privacidad con fecha.
- Disponibilidad calculada en intervalos de 30 minutos, según duración del servicio, horario del profesional, reservas activas y bloqueos.
- Citas en estado inicial `pendiente`; cada profesional puede consultar solo sus citas y confirmarlas o cancelarlas desde la gestión diaria.
- Panel Django Admin para administrar servicios, clientes, profesionales, horarios, bloqueos y citas.
- Zona horaria `America/Santiago` y configuración de idioma `es-cl`.

## 3. Rutas web y API

| Método | Ruta | Acceso y descripción |
|---|---|---|
| GET | `/` | Catálogo público |
| GET | `/reservar/` | Formulario público de reserva |
| GET | `/privacidad/` | Política de privacidad |
| GET | `/ingresar/` | Inicio de sesión para profesionales |
| POST | `/salir/` | Cierra la sesión |
| GET | `/gestion/` | Agenda diaria del profesional autenticado |
| GET | `/admin/` | Administración de Django |
| GET | `/api/servicios/` | Servicios activos |
| GET | `/api/profesionales/?servicio=ID` | Profesionales activos; puede filtrarse por servicio |
| GET | `/api/disponibilidad/?servicio=ID&fecha=AAAA-MM-DD[&profesional=ID]` | Horas disponibles |
| POST | `/api/citas/` | Crea una reserva; responde `409` si no puede agendarse |
| GET | `/api/agenda/?fecha=AAAA-MM-DD` | Citas del día del profesional autenticado |
| POST | `/api/citas/ID/estado/` | Cambia el estado solo de una cita del profesional autenticado |

El formulario envía la creación de reservas como JSON y usa protección CSRF. La gestión requiere una cuenta de Django asociada a un profesional activo. La agenda y el cambio de estado verifican en el servidor que la cita pertenezca a ese profesional. Las cuentas administradoras siguen teniendo acceso al panel Django Admin como función administrativa separada.

## 4. Validación de datos y privacidad

- **Nombre y teléfono:** obligatorios. El teléfono se valida como número chileno de nueve dígitos y se almacena normalizado con prefijo `+56`; se acepta, por ejemplo, `9 1234 5678` o `+56 9 1234 5678`. Es el identificador de la clienta.
- **Correo:** opcional; los valores vacíos se guardan como `NULL`. Debe tener formato válido y es único sin distinguir mayúsculas/minúsculas.
- **RUT de clientas:** ya no se recopila ni almacena. El RUT de profesionales no cambia.
- **Consentimiento:** la casilla de privacidad es opcional; si se marca se guarda la fecha y hora. La base impide registrar una aceptación sin fecha. La política muestra campos del responsable y contacto pendientes de completar.
- Los errores se asocian al campo correspondiente en el formulario. La API repite las validaciones para no depender del navegador.
- La respuesta pública al crear una cita no devuelve datos del cliente. La agenda devuelve nombre y teléfono, sin correo. El panel Django Admin permite a administradores ver los datos del cliente y su estado de consentimiento.
- Las contraseñas de acceso se gestionan con el sistema de autenticación de Django; no se almacenan en el modelo `Profesional`. Crea cada cuenta de usuario desde Django Admin y asígnala a un solo profesional. No reutilices cuentas entre profesionales.
- No hay cifrado de correo o teléfono por campo ni verificación de propiedad del correo o teléfono.

## 5. Modelos y reglas de reserva

Los modelos principales son `Servicio`, `Cliente`, `Profesional`, `HorarioTrabajo`, `BloqueoHorario` y `Cita`.

Las citas deben coincidir con la duración del servicio, quedar dentro del horario del profesional y no solaparse con otra cita pendiente/confirmada ni con un bloqueo. La migración `0005_evitar_citas_solapadas` agrega una restricción de exclusión solo en PostgreSQL; en otras bases se aplican las validaciones de Django, pero no esa restricción concurrente de base de datos.

## 6. Migraciones, pruebas y documentación técnica

- Migraciones de la aplicación: `servicios/migrations/0001` a `0008`.
- Pruebas: `python manage.py test servicios` (11 pruebas).
- Comprobaciones útiles: `python manage.py check` y `python manage.py makemigrations --check --dry-run`.
- `Documentacion/schema.sql` y `Documentacion/dbdiagram.io` contienen documentación del esquema. El SQL completo y las migraciones son alternativas: no ejecutes ambos sobre la misma base.

## 7. Seguridad y pendientes

- El valor alternativo de `SECRET_KEY` en `settings.py` es solo para desarrollo. En producción, define una clave privada por variable de entorno, configura `DEBUG=False`, `ALLOWED_HOSTS` y despliega detrás de HTTPS.
- La configuración de la aplicación no cifra datos personales por campo. Revisa cifrado en reposo y respaldos de la base de datos, define retención y limita el acceso a datos de clientes.
- No se implementa confirmación de reservas por correo/WhatsApp ni verificación de correo/teléfono.
- La duración del intervalo de disponibilidad es fija en 30 minutos (`PASO_MINUTOS`).
- No hay imágenes individuales asociadas a servicios; el sitio sí incluye un logo.
- La guía no confirma el estado de despliegues, credenciales ni configuración real de Supabase; hay que verificar esos elementos en el entorno correspondiente.

## 8. Estructura principal

- `salon_de_belleza/settings.py`, `salon_de_belleza/urls.py`: configuración y rutas del proyecto.
- `servicios/models.py`, `servicios/validators.py`: modelos y validaciones.
- `servicios/api.py`, `servicios/views.py`, `servicios/disponibilidad.py`: API, páginas y cálculo de disponibilidad.
- `servicios/templates/servicios/` y `servicios/static/servicios/`: interfaz, JavaScript y estilos.
- `servicios/admin.py`: configuración del panel de administración.
- `servicios/management/commands/seed_demo.py`: datos de demostración.
- `servicios/tests.py`: pruebas de API y reglas de reserva.
