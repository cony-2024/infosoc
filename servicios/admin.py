from django.contrib import admin

from .models import BloqueoHorario, Cita, Cliente, HorarioTrabajo, Profesional, Servicio


class HorarioInline(admin.TabularInline):
    model = HorarioTrabajo
    extra = 1


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "duracion_minutos", "activo")
    list_filter = ("categoria", "activo")


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "usuario", "activo")
    list_select_related = ("usuario",)
    autocomplete_fields = ("usuario",)
    filter_horizontal = ("servicios",)
    inlines = [HorarioInline]


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "email", "acepta_politica_privacidad")
    list_filter = ("acepta_politica_privacidad",)
    search_fields = ("nombre", "telefono", "email")


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ("inicio", "cliente", "servicio", "profesional", "estado")
    list_filter = ("estado", "profesional")
    date_hierarchy = "inicio"


admin.site.register(BloqueoHorario)
