from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Profesional, Servicio


def index(request):
    """Catálogo público, agrupado por categoría."""
    grupos = {}
    for s in Servicio.objects.filter(activo=True).order_by("categoria", "nombre"):
        grupos.setdefault(s.get_categoria_display(), []).append(s)
    return render(request, "servicios/index.html", {"grupos": grupos})


@ensure_csrf_cookie
def reservar(request):
    """Selector de servicio, profesional, fecha y hora (usa la API por fetch)."""
    return render(request, "servicios/reservar.html", {"servicio_id": request.GET.get("servicio", "")})


@login_required
@ensure_csrf_cookie
def gestion(request):
    """Vista de gestión diaria para el profesional autenticado."""
    profesional = Profesional.objects.filter(usuario=request.user, activo=True).first()
    if profesional is None:
        raise PermissionDenied
    return render(request, "servicios/gestion.html", {"profesional": profesional})
