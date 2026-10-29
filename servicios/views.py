from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Servicio


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


@staff_member_required(login_url="/admin/login/")
@ensure_csrf_cookie
def gestion(request):
    """Vista de gestión diaria para el administrador."""
    return render(request, "servicios/gestion.html")
