"""API REST (JSON) de servicios, disponibilidad y citas."""
import json
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET, require_POST

from .disponibilidad import disponibilidad
from .models import Cita, Cliente, Profesional, Servicio


def _servicio(s):
    return {
        "id": s.id, "nombre": s.nombre, "descripcion": s.descripcion,
        "categoria": s.categoria, "precio": int(s.precio), "duracion_minutos": s.duracion_minutos,
    }


def _cita(c):
    ini, fin = timezone.localtime(c.inicio), timezone.localtime(c.fin)
    return {
        "id": c.id, "inicio": ini.isoformat(), "fin": fin.isoformat(),
        "hora": f"{ini:%H:%M}–{fin:%H:%M}", "estado": c.estado,
        "cliente": {"nombre": c.cliente.nombre, "telefono": c.cliente.telefono, "rut": c.cliente.rut},
        "servicio": c.servicio.nombre, "profesional": c.profesional.nombre,
    }


def _error(msg, status=400, **extra):
    return JsonResponse({"error": msg, **extra}, status=status)


def _fecha(valor):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


@require_GET
def servicios(request):
    qs = Servicio.objects.filter(activo=True).order_by("categoria", "nombre")
    return JsonResponse({"servicios": [_servicio(s) for s in qs]})


@require_GET
def profesionales(request):
    qs = Profesional.objects.filter(activo=True)
    if request.GET.get("servicio"):
        qs = qs.filter(servicios__pk=request.GET["servicio"])
    return JsonResponse({"profesionales": [{"id": p.id, "nombre": p.nombre} for p in qs]})


@require_GET
def disponibilidad_api(request):
    """GET /api/disponibilidad/?servicio=1&fecha=2026-11-03[&profesional=2]"""
    servicio = Servicio.objects.filter(pk=request.GET.get("servicio") or 0, activo=True).first()
    fecha = _fecha(request.GET.get("fecha"))
    if not servicio or not fecha:
        return _error("Parámetros requeridos: servicio (id válido) y fecha (AAAA-MM-DD).")
    prof = None
    if request.GET.get("profesional"):
        prof = Profesional.objects.filter(pk=request.GET["profesional"], activo=True).first()
        if not prof:
            return _error("Profesional no encontrado.", 404)
    horas = disponibilidad(servicio, fecha, prof)
    return JsonResponse({
        "fecha": fecha.isoformat(), "servicio": _servicio(servicio),
        "horas": [
            {"inicio": timezone.localtime(h["inicio"]).isoformat(),
             "hora": f"{timezone.localtime(h['inicio']):%H:%M}", "profesionales": h["profesionales"]}
            for h in horas
        ],
    })


@require_POST
def crear_cita(request):
    """POST /api/citas/  {servicio, profesional, inicio, cliente:{nombre,rut,email,telefono}}"""
    try:
        d = json.loads(request.body)
        cli = d["cliente"]
        servicio = get_object_or_404(Servicio, pk=d["servicio"], activo=True)
        prof = get_object_or_404(Profesional, pk=d["profesional"], activo=True)
        inicio = parse_datetime(d["inicio"])
        if inicio is None:
            raise ValueError
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio)
        nombre, rut = cli["nombre"].strip(), cli["rut"].strip()
        if not nombre or not rut:
            raise ValueError
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return _error("Datos incompletos o inválidos.")

    cliente, _ = Cliente.objects.update_or_create(
        rut=rut, defaults={"nombre": nombre, "email": cli.get("email", ""), "telefono": cli.get("telefono", "")}
    )
    try:
        cita = Cita(cliente=cliente, profesional=prof, servicio=servicio,
                    inicio=inicio, fin=inicio + timedelta(minutes=servicio.duracion_minutos))
        cita.save()  # save() ejecuta clean(): horario, solapamientos, bloqueos
    except ValidationError as e:
        return _error("No se pudo agendar.", 409, detalles=e.message_dict if hasattr(e, "error_dict") else e.messages)
    except Exception:  # p. ej. restricción de exclusión de PostgreSQL ante reservas simultáneas
        return _error("Esa hora acaba de ser tomada. Elige otra.", 409)
    return JsonResponse({"cita": _cita(cita)}, status=201)


def _solo_staff(vista):
    def envoltura(request, *a, **k):
        if not (request.user.is_authenticated and request.user.is_staff):
            return _error("Requiere iniciar sesión como administrador.", 403)
        return vista(request, *a, **k)
    return envoltura


@_solo_staff
@require_GET
def agenda(request):
    """GET /api/agenda/?fecha=AAAA-MM-DD  -> citas del día (vista de gestión)."""
    fecha = _fecha(request.GET.get("fecha")) or timezone.localdate()
    citas = (Cita.objects.select_related("cliente", "servicio", "profesional")
             .filter(inicio__date=fecha).order_by("inicio"))
    # inicio__date usa la zona horaria activa (America/Santiago)
    return JsonResponse({"fecha": fecha.isoformat(), "citas": [_cita(c) for c in citas]})


@_solo_staff
@require_POST
def cambiar_estado(request, cita_id):
    cita = get_object_or_404(Cita, pk=cita_id)
    try:
        estado = json.loads(request.body).get("estado")
    except json.JSONDecodeError:
        estado = None
    if estado not in Cita.Estado.values:
        return _error("Estado inválido.")
    cita.estado = estado
    cita.save()
    return JsonResponse({"cita": _cita(cita)})
