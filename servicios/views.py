from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Profesional, Servicio, Trabajo


def index(request):
    """Catálogo público, agrupado por categoría."""
    grupos = {}
    for s in Servicio.objects.filter(activo=True).order_by("categoria", "nombre"):
        grupos.setdefault(s.get_categoria_display(), []).append(s)
    destacados = Trabajo.objects.filter(activo=True)[:6]
    return render(request, "servicios/index.html", {"grupos": grupos, "destacados": destacados})


def trabajos(request):
    """Galería pública de trabajos, con filtro opcional por categoría."""
    categorias = dict(Servicio.Categoria.choices)
    elegida = request.GET.get("categoria", "")
    lista = Trabajo.objects.filter(activo=True)
    if elegida in categorias:
        lista = lista.filter(categoria=elegida)
    else:
        elegida = ""
    usadas = Trabajo.objects.filter(activo=True).values_list("categoria", flat=True).distinct()
    filtros = [(valor, categorias[valor]) for valor in categorias if valor in set(usadas)]
    return render(
        request,
        "servicios/trabajos.html",
        {"trabajos": lista, "filtros": filtros, "elegida": elegida},
    )

@ensure_csrf_cookie
def reservar(request):
    """Selector de servicio, profesional, fecha y hora (usa la API por fetch)."""
    return render(request, "servicios/reservar.html", {"servicio_id": request.GET.get("servicio", "")})


def politica_de_privacidad(request):
    """Muestra la política de privacidad del servicio."""
    return render(request, "servicios/politica_de_privacidad.html")


@login_required
@ensure_csrf_cookie
def gestion(request):
    """Vista de gestión diaria para el profesional autenticado."""
    profesional = Profesional.objects.filter(usuario=request.user, activo=True).first()
    if profesional is None:
        raise PermissionDenied
    return render(request, "servicios/gestion.html", {"profesional": profesional})
