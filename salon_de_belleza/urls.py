from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from servicios import api, views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "ingresar/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("salir/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    # Páginas
    path("", views.index, name="index"),
    path("trabajos/", views.trabajos, name="trabajos"),
    path("reservar/", views.reservar, name="reservar"),
    path("privacidad/", views.politica_de_privacidad, name="politica_de_privacidad"),
    path("gestion/", views.gestion, name="gestion"),
    # API REST
    path("api/servicios/", api.servicios),
    path("api/profesionales/", api.profesionales),
    path("api/disponibilidad/", api.disponibilidad_api),
    path("api/citas/", api.crear_cita),
    path("api/citas/<int:cita_id>/estado/", api.cambiar_estado),
    path("api/agenda/", api.agenda),
]
