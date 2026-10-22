from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Cita, Cliente, HorarioTrabajo, Profesional, Servicio


class CitaValidationTests(TestCase):
    def setUp(self):
        self.servicio = Servicio.objects.create(
            nombre="Corte",
            precio="10000.00",
            duracion_minutos=60,
        )
        self.profesional = Profesional.objects.create(nombre="Ana", rut="11111111-1")
        self.profesional.servicios.add(self.servicio)
        self.cliente = Cliente.objects.create(nombre="Luis", rut="22222222-2")
        HorarioTrabajo.objects.create(
            profesional=self.profesional,
            dia=0,
            hora_entrada="09:00",
            hora_salida="17:00",
        )
        self.inicio = timezone.make_aware(datetime(2026, 10, 26, 10, 0))

    def crear_cita(self, inicio=None, fin=None):
        inicio = inicio or self.inicio
        fin = fin or inicio + timedelta(minutes=self.servicio.duracion_minutos)
        return Cita(
            cliente=self.cliente,
            profesional=self.profesional,
            servicio=self.servicio,
            inicio=inicio,
            fin=fin,
        )

    def test_acepta_cita_dentro_del_horario(self):
        self.crear_cita().full_clean()

    def test_rechaza_cita_fuera_del_horario(self):
        inicio = timezone.make_aware(datetime(2026, 10, 26, 16, 30))
        with self.assertRaises(ValidationError):
            self.crear_cita(inicio=inicio).full_clean()

    def test_rechaza_cita_si_profesional_no_ofrece_servicio(self):
        self.profesional.servicios.clear()
        with self.assertRaises(ValidationError):
            self.crear_cita().full_clean()

    def test_rechaza_cita_que_se_superpone_con_otra(self):
        existente = self.crear_cita()
        existente.full_clean()
        existente.save()

        inicio = timezone.make_aware(datetime(2026, 10, 26, 10, 30))
        with self.assertRaises(ValidationError):
            self.crear_cita(inicio=inicio).full_clean()
