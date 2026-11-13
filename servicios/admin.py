from django.contrib import admin
from django.utils.html import format_html

from .models import BloqueoHorario, Cita, Cliente, HorarioTrabajo, Profesional, Servicio, Trabajo


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

@admin.register(Trabajo)
class TrabajoAdmin(admin.ModelAdmin):
    list_display = ("vista_previa", "titulo", "categoria", "orden", "activo")
    list_display_links = ("vista_previa", "titulo")
    list_editable = ("orden", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("titulo", "descripcion")

    @admin.display(description="Foto")
    def vista_previa(self, obj):
        return format_html(
            '<img src="{}" alt="" style="height:56px;width:56px;object-fit:cover;border-radius:8px">',
            obj.imagen_url,
        )
    
admin.site.register(BloqueoHorario)

admin.site.site_header = "Beauty Corner · Administración"
admin.site.site_title = "Beauty Corner"
admin.site.index_title = "Panel de gestión"