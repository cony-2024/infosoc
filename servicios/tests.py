import json
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import Cliente


def proximo_lunes():
    d = timezone.localdate() + timedelta(days=1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


class ApiAgendaTests(TestCase):
    def setUp(self):
        call_command("seed_demo", verbosity=0)
        self.fecha = proximo_lunes().isoformat()

    def _horas(self, **extra):
        r = self.client.get("/api/disponibilidad/", {"servicio": 1, "fecha": self.fecha, **extra})
        self.assertEqual(r.status_code, 200)
        return r.json()["horas"]

    def _reservar(self, hora, prof, rut="1-9", email="", telefono="912345678"):
        return self.client.post("/api/citas/", json.dumps({
            "servicio": 1, "profesional": prof, "inicio": hora["inicio"],
            "cliente": {"nombre": "Ana", "rut": rut, "email": email, "telefono": telefono}}), content_type="application/json")

    def test_catalogo_y_horas(self):
        self.assertEqual(len(self.client.get("/api/servicios/").json()["servicios"]), 5)
        horas = self._horas()
        self.assertEqual(horas[0]["hora"], "10:00")
        self.assertEqual(len(horas[0]["profesionales"]), 2)

    def test_reserva_quita_hora_y_evita_doble_reserva(self):
        h = self._horas()[0]
        p1, p2 = h["profesionales"]
        self.assertEqual(self._reservar(h, p1).status_code, 201)
        self.assertEqual(self._reservar(h, p1, "2-7").status_code, 409)  # mismo profesional
        self.assertEqual(self._reservar(h, p2, "3-5").status_code, 201)  # otro profesional sí
        self.assertNotIn(h["hora"], [x["hora"] for x in self._horas()[:1]])

    def test_fuera_de_horario_rechazado(self):
        h = {"inicio": f"{self.fecha}T23:00:00-03:00"}
        self.assertEqual(self._reservar(h, 1).status_code, 409)

    def test_rut_y_email_invalidos_no_se_guardan(self):
        h = self._horas()[0]
        profesional = h["profesionales"][0]

        respuesta_rut = self._reservar(h, profesional, rut="12.345.678-9")
        respuesta_email = self._reservar(h, profesional, rut="12.345.678-5", email="no-es-un-correo")

        self.assertEqual(respuesta_rut.status_code, 400)
        self.assertEqual(
            respuesta_rut.json()["detalles"]["rut"],
            ["RUT inválido. Revisa el número y su dígito verificador (ej.: 12.345.678-5)."],
        )
        self.assertEqual(respuesta_email.status_code, 400)
        self.assertEqual(
            respuesta_email.json()["detalles"]["email"],
            ["Ingresa un correo válido, por ejemplo nombre@dominio.cl."],
        )
        self.assertFalse(Cliente.objects.exists())

    def test_campos_obligatorios_indican_cual_falta(self):
        hora = self._horas()[0]
        respuesta = self.client.post("/api/citas/", json.dumps({
            "servicio": 1,
            "profesional": hora["profesionales"][0],
            "inicio": hora["inicio"],
            "cliente": {"nombre": " ", "rut": ""},
        }), content_type="application/json")

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["detalles"], {
            "nombre": ["Escribe tu nombre."],
            "rut": ["Escribe tu RUT."],
        })

    def test_telefono_chileno_invalido_se_indica_en_el_campo(self):
        hora = self._horas()[0]

        respuesta = self._reservar(hora, hora["profesionales"][0], telefono="12345abc")

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json()["detalles"]["telefono"],
            ["Teléfono inválido. Ingresa 9 dígitos chilenos, por ejemplo 9 1234 5678 o +56 9 1234 5678."],
        )
        self.assertFalse(Cliente.objects.exists())

    def test_telefono_chileno_acepta_formatos_local_e_internacional(self):
        hora = self._horas()[0]

        ruts = ("1-9", "2-7")
        for indice, telefono in enumerate(("9 1234 5678", "+56 9 1234 5678")):
            respuesta = self._reservar(
                hora, hora["profesionales"][indice], rut=ruts[indice], telefono=telefono,
            )
            self.assertEqual(respuesta.status_code, 201)

    def test_rut_se_normaliza_y_no_se_devuelve_en_respuesta_publica(self):
        h = self._horas()[0]

        respuesta = self._reservar(h, h["profesionales"][0], rut="12.345.678-5", email="ana@example.com")

        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(Cliente.objects.filter(rut="12345678-5").exists())
        self.assertNotIn("cliente", respuesta.json()["cita"])

    def test_agenda_solo_staff(self):
        self.assertEqual(self.client.get("/api/agenda/").status_code, 403)
        User.objects.create_user("admin", password="x", is_staff=True)
        self.client.login(username="admin", password="x")
        h = self._horas()[0]
        self._reservar(h, h["profesionales"][0])
        r = self.client.get("/api/agenda/", {"fecha": self.fecha}).json()
        self.assertEqual(len(r["citas"]), 1)
        self.assertNotIn("rut", r["citas"][0]["cliente"])
        cid = r["citas"][0]["id"]
        r = self.client.post(f"/api/citas/{cid}/estado/", json.dumps({"estado": "confirmada"}), content_type="application/json")
        self.assertEqual(r.json()["cita"]["estado"], "confirmada")
