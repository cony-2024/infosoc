import json
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import Cliente, Profesional


def proximo_lunes():
    d = timezone.localdate() + timedelta(days=1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


class ApiAgendaTests(TestCase):
    def setUp(self):
        call_command("seed_demo", verbosity=0)
        self.fecha = proximo_lunes().isoformat()

    def test_politica_de_privacidad_publica_y_enlazada_en_reserva(self):
        politica = self.client.get("/privacidad/")
        reserva = self.client.get("/reservar/")

        self.assertEqual(politica.status_code, 200)
        self.assertContains(politica, "Política de privacidad")
        self.assertContains(politica, "[Completar correo de contacto]")
        self.assertEqual(reserva.status_code, 200)
        self.assertContains(reserva, 'href="/privacidad/"')
        self.assertContains(reserva, 'name="acepta_politica_privacidad"')
        self.assertNotContains(reserva, 'name="acepta_politica_privacidad" required')

    def _horas(self, **extra):
        r = self.client.get("/api/disponibilidad/", {"servicio": 1, "fecha": self.fecha, **extra})
        self.assertEqual(r.status_code, 200)
        return r.json()["horas"]

    def _reservar(
        self,
        hora,
        prof,
        email="",
        telefono="912345678",
        acepta_politica_privacidad=False,
    ):
        return self.client.post("/api/citas/", json.dumps({
            "servicio": 1, "profesional": prof, "inicio": hora["inicio"],
            "cliente": {
                "nombre": "Ana",
                "email": email,
                "telefono": telefono,
                "acepta_politica_privacidad": acepta_politica_privacidad,
            }}), content_type="application/json")

    def test_catalogo_y_horas(self):
        self.assertEqual(len(self.client.get("/api/servicios/").json()["servicios"]), 5)
        horas = self._horas()
        self.assertEqual(horas[0]["hora"], "10:00")
        self.assertEqual(len(horas[0]["profesionales"]), 2)

    def test_reserva_quita_hora_y_evita_doble_reserva(self):
        h = self._horas()[0]
        p1, p2 = h["profesionales"]
        self.assertEqual(self._reservar(h, p1).status_code, 201)
        self.assertEqual(self._reservar(h, p1, telefono="987654321").status_code, 409)  # mismo profesional
        self.assertEqual(self._reservar(h, p2, telefono="987654322").status_code, 201)  # otro profesional sí
        self.assertNotIn(h["hora"], [x["hora"] for x in self._horas()[:1]])

    def test_fuera_de_horario_rechazado(self):
        h = {"inicio": f"{self.fecha}T23:00:00-03:00"}
        self.assertEqual(self._reservar(h, 1).status_code, 409)

    def test_email_invalido_no_se_guarda(self):
        h = self._horas()[0]
        profesional = h["profesionales"][0]

        respuesta_email = self._reservar(h, profesional, email="no-es-un-correo")

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
            "cliente": {"nombre": " ", "telefono": ""},
        }), content_type="application/json")

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["detalles"], {
            "nombre": ["Escribe tu nombre."],
            "telefono": ["Escribe tu teléfono."],
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

        for indice, telefono in enumerate(("9 1234 5678", "+56 9 1234 5678")):
            respuesta = self._reservar(
                hora, hora["profesionales"][indice], telefono=telefono,
            )
            self.assertEqual(respuesta.status_code, 201)

    def test_telefono_se_normaliza_y_consentimiento_queda_registrado(self):
        h = self._horas()[0]

        respuesta = self._reservar(
            h,
            h["profesionales"][0],
            email="ana@example.com",
            telefono="9 1234 5678",
            acepta_politica_privacidad=True,
        )

        self.assertEqual(respuesta.status_code, 201)
        cliente = Cliente.objects.get(telefono="+56912345678")
        self.assertEqual(cliente.email, "ana@example.com")
        self.assertTrue(cliente.acepta_politica_privacidad)
        self.assertIsNotNone(cliente.acepta_politica_en)
        self.assertNotIn("cliente", respuesta.json()["cita"])

    def test_email_vacio_es_null_y_sin_consentimiento_no_hay_fecha(self):
        hora = self._horas()[0]

        respuesta = self._reservar(hora, hora["profesionales"][0], email="  ")

        self.assertEqual(respuesta.status_code, 201)
        cliente = Cliente.objects.get(telefono="+56912345678")
        self.assertIsNone(cliente.email)
        self.assertFalse(cliente.acepta_politica_privacidad)
        self.assertIsNone(cliente.acepta_politica_en)

    def test_email_es_unico_sin_distinguir_mayusculas(self):
        hora = self._horas()[0]
        profesionales = hora["profesionales"]

        primera = self._reservar(
            hora, profesionales[0], email="ana@example.com", telefono="912345678",
        )
        segunda = self._reservar(
            hora, profesionales[1], email="ANA@example.com", telefono="987654321",
        )

        self.assertEqual(primera.status_code, 201)
        self.assertEqual(segunda.status_code, 400)
        self.assertIn("email", segunda.json()["detalles"])
        self.assertEqual(Cliente.objects.count(), 1)

    def test_agenda_y_cambios_solo_para_el_profesional_asociado(self):
        self.assertEqual(self.client.get("/api/agenda/").status_code, 403)
        usuario_1 = User.objects.create_user("profesional1", password="una-clave-segura-123")
        usuario_2 = User.objects.create_user("profesional2", password="otra-clave-segura-123")
        profesional_1 = Profesional.objects.get(pk=1)
        profesional_2 = Profesional.objects.get(pk=2)
        profesional_1.usuario = usuario_1
        profesional_1.save()
        profesional_2.usuario = usuario_2
        profesional_2.save()
        h = self._horas()[0]
        cita_1 = self._reservar(h, profesional_1.pk, telefono="912345678").json()["cita"]
        cita_2 = self._reservar(h, profesional_2.pk, telefono="987654321").json()["cita"]

        self.client.login(username="profesional1", password="una-clave-segura-123")
        agenda = self.client.get("/api/agenda/", {"fecha": self.fecha})
        self.assertEqual(agenda.status_code, 200)
        self.assertEqual([c["id"] for c in agenda.json()["citas"]], [cita_1["id"]])
        self.assertNotIn("email", agenda.json()["citas"][0]["cliente"])

        ajena = self.client.post(
            f"/api/citas/{cita_2['id']}/estado/",
            json.dumps({"estado": "confirmada"}),
            content_type="application/json",
        )
        self.assertEqual(ajena.status_code, 404)

        propia = self.client.post(
            f"/api/citas/{cita_1['id']}/estado/",
            json.dumps({"estado": "confirmada"}),
            content_type="application/json",
        )
        self.assertEqual(propia.status_code, 200)
        self.assertEqual(propia.json()["cita"]["estado"], "confirmada")

    def test_cuenta_staff_sin_profesional_no_accede(self):
        usuario = User.objects.create_user(
            "staff", password="una-clave-segura-123", is_staff=True,
        )
        self.client.login(username=usuario.username, password="una-clave-segura-123")
        self.assertEqual(self.client.get("/api/agenda/").status_code, 403)
        self.assertEqual(self.client.get("/gestion/").status_code, 403)

    def test_gestion_requiere_login_y_profesional_activo(self):
        respuesta = self.client.get("/gestion/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/ingresar/", respuesta.url)

        usuario = User.objects.create_user("profesional", password="una-clave-segura-123")
        Profesional.objects.filter(pk=1).update(usuario=usuario, activo=False)
        self.client.login(username=usuario.username, password="una-clave-segura-123")
        self.assertEqual(self.client.get("/gestion/").status_code, 403)

    def test_gestion_enlaza_al_admin(self):
        usuario = User.objects.create_user("profesional", password="una-clave-segura-123")
        Profesional.objects.filter(pk=1).update(usuario=usuario)
        self.client.login(username=usuario.username, password="una-clave-segura-123")

        respuesta = self.client.get("/gestion/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'href="/admin/"')
        self.assertContains(respuesta, "Administración")

    def test_profesional_autenticado_alcanza_gestion_sin_reingresar(self):
        usuario = User.objects.create_user("profesional", password="una-clave-segura-123")
        Profesional.objects.filter(pk=1).update(usuario=usuario)
        self.client.force_login(usuario)

        respuesta = self.client.get("/ingresar/?next=/gestion/")

        self.assertRedirects(respuesta, "/gestion/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/gestion/").status_code, 200)
