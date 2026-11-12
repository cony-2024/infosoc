import re

import django.db.models.functions.text
import django.utils.timezone
from django.db import migrations, models
from django.db.models import Q
from django.db.migrations.exceptions import IrreversibleError


_TELEFONO_CHILENO = re.compile(
    r"(?:\+?56|0056)?[ .-]?(?:[2-9]|\([2-9]\))(?:[ .-]?\d){8}"
)


def preparar_datos_cliente(apps, schema_editor):
    Cliente = apps.get_model("servicios", "Cliente")
    clientes = list(Cliente.objects.all())
    telefonos = {}
    emails = {}
    errores = []
    valores_normalizados = []

    for cliente in clientes:
        telefono = cliente.telefono or ""
        if not _TELEFONO_CHILENO.fullmatch(telefono.strip()):
            errores.append(f"teléfono inválido en cliente id={cliente.pk}")
            continue

        digitos = re.sub(r"\D", "", telefono)
        if digitos.startswith("0056"):
            digitos = digitos[4:]
        elif digitos.startswith("56") and len(digitos) == 11:
            digitos = digitos[2:]
        telefono_normalizado = f"+56{digitos}"
        telefonos.setdefault(telefono_normalizado, []).append(cliente.pk)

        email = (cliente.email or "").strip() or None
        if email:
            emails.setdefault(email.casefold(), []).append(cliente.pk)
        valores_normalizados.append((cliente, telefono_normalizado, email))

    for telefono, ids in telefonos.items():
        if len(ids) > 1:
            errores.append(f"teléfono duplicado {telefono} en clientes id={ids}")
    for email, ids in emails.items():
        if len(ids) > 1:
            errores.append(f"correo duplicado {email} en clientes id={ids}")

    if errores:
        detalle = "; ".join(errores)
        raise RuntimeError(
            "No se puede migrar servicios.Cliente. Corrige estos datos antes de "
            f"ejecutar migrate: {detalle}"
        )

    for cliente, telefono, email in valores_normalizados:
        cliente.telefono = telefono
        cliente.email = email
        cliente.save(update_fields=["telefono", "email"])


def no_revertir_eliminacion_de_rut(apps, schema_editor):
    raise IrreversibleError(
        "La migración elimina el RUT de las clientas y no conserva esos datos."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("servicios", "0006_profesional_usuario"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="creado_en",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                editable=False,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="cliente",
            name="acepta_politica_privacidad",
            field=models.BooleanField(db_default=False, default=False),
        ),
        migrations.AddField(
            model_name="cliente",
            name="acepta_politica_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.RunPython(preparar_datos_cliente, no_revertir_eliminacion_de_rut),
        migrations.RemoveField(
            model_name="cliente",
            name="rut",
        ),
        migrations.AlterField(
            model_name="cliente",
            name="telefono",
            field=models.CharField(max_length=20, unique=True),
        ),
        migrations.AddConstraint(
            model_name="cliente",
            constraint=models.CheckConstraint(
                condition=Q(telefono__regex=r"^\+?[0-9]{8,15}$"),
                name="cliente_telefono_formato",
            ),
        ),
        migrations.AddConstraint(
            model_name="cliente",
            constraint=models.CheckConstraint(
                condition=Q(acepta_politica_privacidad=False)
                | Q(acepta_politica_en__isnull=False),
                name="cliente_consentimiento_con_fecha",
            ),
        ),
        migrations.AddConstraint(
            model_name="cliente",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("email"),
                condition=Q(email__isnull=False),
                name="cliente_email_unico_idx",
            ),
        ),
    ]
