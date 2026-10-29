from django.db import migrations

# Solo PostgreSQL (Supabase). Garantiza a nivel de BASE DE DATOS que un profesional
# no tenga dos citas activas que se pisen, incluso con dos reservas simultáneas.
SQL_UP = """
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE servicios_cita
  ADD CONSTRAINT cita_sin_solapamiento
  EXCLUDE USING gist (
    profesional_id WITH =,
    tstzrange(inicio, fin) WITH &&
  ) WHERE (estado IN ('pendiente', 'confirmada'));
"""
SQL_DOWN = "ALTER TABLE servicios_cita DROP CONSTRAINT IF EXISTS cita_sin_solapamiento;"


def aplicar(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SQL_UP)


def revertir(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SQL_DOWN)


class Migration(migrations.Migration):
    dependencies = [("servicios", "0004_servicio_categoria")]
    operations = [migrations.RunPython(aplicar, revertir)]
