import json
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone


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

    def _reservar(self, hora, prof, rut="1-9"):
        return self.client.post("/api/citas/", json.dumps({
            "servicio": 1, "profesional": prof, "inicio": hora["inicio"],
            "cliente": {"nombre": "Ana", "rut": rut, "telefono": "9"}}), content_type="application/json")

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

    def test_agenda_solo_staff(self):
        self.assertEqual(self.client.get("/api/agenda/").status_code, 403)
        User.objects.create_user("admin", password="x", is_staff=True)
        self.client.login(username="admin", password="x")
        h = self._horas()[0]
        self._reservar(h, h["profesionales"][0])
        r = self.client.get("/api/agenda/", {"fecha": self.fecha}).json()
        self.assertEqual(len(r["citas"]), 1)
        cid = r["citas"][0]["id"]
        r = self.client.post(f"/api/citas/{cid}/estado/", json.dumps({"estado": "confirmada"}), content_type="application/json")
        self.assertEqual(r.json()["cita"]["estado"], "confirmada")
