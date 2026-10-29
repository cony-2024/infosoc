from django.contrib import admin
from django.urls import path

from servicios import api, views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Páginas
    path("", views.index, name="index"),
    path("reservar/", views.reservar, name="reservar"),
    path("gestion/", views.gestion, name="gestion"),
    # API REST
    path("api/servicios/", api.servicios),
    path("api/profesionales/", api.profesionales),
    path("api/disponibilidad/", api.disponibilidad_api),
    path("api/citas/", api.crear_cita),
    path("api/citas/<int:cita_id>/estado/", api.cambiar_estado),
    path("api/agenda/", api.agenda),
]
