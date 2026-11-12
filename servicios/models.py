from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from .validators import normalizar_rut, validar_telefono_chileno


DIA_SEMANA_CHOICES = [
    (0, "Lunes"),
    (1, "Martes"),
    (2, "Miércoles"),
    (3, "Jueves"),
    (4, "Viernes"),
    (5, "Sábado"),
    (6, "Domingo"),
]


class Servicio(models.Model):
    class Categoria(models.TextChoices):
        MANOS = "manos", "Manos"
        PIES = "pies", "Pies"
        OTROS = "otros", "Otros"

    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.OTROS)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_minutos = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, unique=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)

    def clean(self):
        super().clean()
        if self.rut:
            try:
                self.rut = normalizar_rut(self.rut)
            except ValidationError as e:
                raise ValidationError({"rut": e.messages}) from e
        if self.telefono:
            try:
                validar_telefono_chileno(self.telefono)
            except ValidationError as e:
                raise ValidationError({"telefono": e}) from e

    def __str__(self):
        return self.nombre


class Profesional(models.Model):
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, unique=True)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="profesional",
        null=True,
        blank=True,
    )
    servicios = models.ManyToManyField(
        Servicio,
        related_name="profesionales",
        blank=True,
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class HorarioTrabajo(models.Model):
    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.CASCADE,
        related_name="horarios",
    )
    dia = models.PositiveSmallIntegerField(choices=DIA_SEMANA_CHOICES)
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField()

    class Meta:
        ordering = ("dia", "hora_entrada")
        constraints = [
            models.CheckConstraint(
                condition=Q(hora_salida__gt=F("hora_entrada")),
                name="horario_salida_despues_entrada",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.profesional_id or self.dia is None or not self.hora_entrada or not self.hora_salida:
            return

        overlapping = HorarioTrabajo.objects.filter(
            profesional_id=self.profesional_id,
            dia=self.dia,
            hora_entrada__lt=self.hora_salida,
            hora_salida__gt=self.hora_entrada,
        )
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError(
                {"hora_entrada": "Este horario se superpone con otro turno del profesional."}
            )

    def __str__(self):
        return f"{self.profesional} - {self.get_dia_display()} {self.hora_entrada}-{self.hora_salida}"


class BloqueoHorario(models.Model):
    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.CASCADE,
        related_name="bloqueos",
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("inicio",)
        constraints = [
            models.CheckConstraint(
                condition=Q(fin__gt=F("inicio")),
                name="bloqueo_fin_despues_inicio",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.profesional_id or not self.inicio or not self.fin or self.fin <= self.inicio:
            return

        overlapping = Cita.objects.filter(
            profesional_id=self.profesional_id,
            estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
            inicio__lt=self.fin,
            fin__gt=self.inicio,
        )
        if overlapping.exists():
            raise ValidationError(
                {"inicio": "El bloqueo se superpone con una cita pendiente o confirmada."}
            )

    def __str__(self):
        return f"{self.profesional} - {self.inicio:%Y-%m-%d %H:%M}"


class Cita(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"
        CANCELADA = "cancelada", "Cancelada"

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="citas",
    )
    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.PROTECT,
        related_name="citas",
    )
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.PROTECT,
        related_name="citas",
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("inicio",)
        constraints = [
            models.CheckConstraint(
                condition=Q(fin__gt=F("inicio")),
                name="cita_fin_despues_inicio",
            ),
        ]

    def clean(self):
        super().clean()
        if not all((self.cliente_id, self.profesional_id, self.servicio_id, self.inicio, self.fin)):
            return
        if self.fin <= self.inicio:
            return

        errors = {}
        inicio_local = timezone.localtime(self.inicio)
        fin_local = timezone.localtime(self.fin)
        if fin_local.date() != inicio_local.date():
            errors["fin"] = "La cita debe comenzar y terminar el mismo día."
        if self.fin - self.inicio != timedelta(minutes=self.servicio.duracion_minutos):
            errors["fin"] = "La duración de la cita debe coincidir con la duración del servicio."

        if not self.profesional.activo:
            errors["profesional"] = "No se pueden agendar citas con un profesional inactivo."
        if not self.servicio.activo:
            errors["servicio"] = "No se pueden agendar citas para un servicio inactivo."
        if not self.profesional.servicios.filter(pk=self.servicio_id).exists():
            errors.setdefault("servicio", "Este profesional no ofrece el servicio seleccionado.")

        horario_disponible = HorarioTrabajo.objects.filter(
            profesional_id=self.profesional_id,
            dia=inicio_local.weekday(),
            hora_entrada__lte=inicio_local.time(),
            hora_salida__gte=fin_local.time(),
        ).exists()
        if not horario_disponible:
            errors.setdefault(
                "inicio",
                "La cita debe estar dentro del horario de trabajo del profesional.",
            )

        citas_superpuestas = Cita.objects.filter(
            profesional_id=self.profesional_id,
            estado__in=[self.Estado.PENDIENTE, self.Estado.CONFIRMADA],
            inicio__lt=self.fin,
            fin__gt=self.inicio,
        )
        if self.pk:
            citas_superpuestas = citas_superpuestas.exclude(pk=self.pk)
        if citas_superpuestas.exists():
            errors.setdefault("inicio", "El profesional ya tiene una cita en ese horario.")

        bloqueos_superpuestos = BloqueoHorario.objects.filter(
            profesional_id=self.profesional_id,
            inicio__lt=self.fin,
            fin__gt=self.inicio,
        )
        if bloqueos_superpuestos.exists():
            errors.setdefault("inicio", "El profesional no está disponible en ese horario.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Django NO llama a clean() solo al guardar: lo forzamos para que
        # las reglas (horario, duración, solapamiento) valgan también desde la API.
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.servicio} - {self.profesional} - {self.inicio:%Y-%m-%d %H:%M}"
