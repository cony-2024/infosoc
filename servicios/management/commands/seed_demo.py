from datetime import time

from django.core.management.base import BaseCommand

from servicios.models import HorarioTrabajo, Profesional, Servicio

SERVICIOS = [
    ("manos", "Manicure rusa", "Limpieza profunda de cutícula y esmaltado.", 18000, 60),
    ("manos", "Kapping", "Refuerzo de uña natural con acrílico.", 22000, 75),
    ("manos", "Soft gel", "Uñas con gel suave, acabado natural.", 28000, 90),
    ("manos", "Extensiones", "Extensiones esculpidas a tu medida.", 35000, 120),
    ("pies", "Pedicure", "Pedicure completo con esmaltado.", 20000, 60),
]


class Command(BaseCommand):
    help = "Carga servicios, profesionales y horarios de ejemplo."

    def handle(self, *args, **opts):
        servicios = [Servicio.objects.update_or_create(nombre=n, defaults=dict(
            categoria=c, descripcion=d, precio=p, duracion_minutos=m))[0] for c, n, d, p, m in SERVICIOS]
        for nombre, rut in [("Camila Rojas", "11.111.111-1"), ("Valentina Soto", "22.222.222-2")]:
            prof, _ = Profesional.objects.get_or_create(rut=rut, defaults={"nombre": nombre})
            prof.servicios.set(servicios)
            if not prof.horarios.exists():
                for dia in range(0, 6):  # lunes a sábado
                    HorarioTrabajo.objects.create(profesional=prof, dia=dia, hora_entrada=time(10), hora_salida=time(14))
                    if dia < 5:
                        HorarioTrabajo.objects.create(profesional=prof, dia=dia, hora_entrada=time(15), hora_salida=time(19))
        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados."))
