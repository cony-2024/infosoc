"""Lógica de disponibilidad: calcula qué horas se pueden reservar."""
from datetime import datetime, timedelta

from django.utils import timezone

from .models import BloqueoHorario, Cita, HorarioTrabajo, Profesional

PASO_MINUTOS = 30  # cada cuántos minutos se ofrece una hora de inicio


def _aware(fecha, hora):
    return timezone.make_aware(datetime.combine(fecha, hora))


def horas_libres(profesional, servicio, fecha):
    """Lista de datetimes de inicio disponibles para un profesional en una fecha."""
    duracion = timedelta(minutes=servicio.duracion_minutos)
    ahora = timezone.now()

    # Citas y bloqueos del día que ocupan al profesional
    dia_ini, dia_fin = _aware(fecha, datetime.min.time()), _aware(fecha, datetime.min.time()) + timedelta(days=1)
    ocupado = [
        (c.inicio, c.fin)
        for c in Cita.objects.filter(
            profesional=profesional,
            estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
            inicio__lt=dia_fin, fin__gt=dia_ini,
        )
    ] + [
        (b.inicio, b.fin)
        for b in BloqueoHorario.objects.filter(profesional=profesional, inicio__lt=dia_fin, fin__gt=dia_ini)
    ]

    libres = []
    for turno in HorarioTrabajo.objects.filter(profesional=profesional, dia=fecha.weekday()):
        inicio = _aware(fecha, turno.hora_entrada)
        limite = _aware(fecha, turno.hora_salida)
        while inicio + duracion <= limite:
            fin = inicio + duracion
            if inicio > ahora and not any(inicio < o_fin and fin > o_ini for o_ini, o_fin in ocupado):
                libres.append(inicio)
            inicio += timedelta(minutes=PASO_MINUTOS)
    return libres


def disponibilidad(servicio, fecha, profesional=None):
    """Devuelve [{'inicio': dt, 'profesionales': [ids]}] ordenado por hora.

    Si no se elige profesional, une los horarios de todos los que ofrecen el servicio.
    """
    profesionales = Profesional.objects.filter(activo=True, servicios=servicio)
    if profesional:
        profesionales = profesionales.filter(pk=profesional.pk)

    por_hora = {}
    for p in profesionales:
        for h in horas_libres(p, servicio, fecha):
            por_hora.setdefault(h, []).append(p.pk)
    return [{"inicio": h, "profesionales": ids} for h, ids in sorted(por_hora.items())]
