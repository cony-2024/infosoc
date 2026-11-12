from django.db import migrations


_TABLAS = (
    "servicios_servicio",
    "servicios_cliente",
    "servicios_profesional",
    "servicios_profesional_servicios",
    "servicios_horariotrabajo",
    "servicios_bloqueohorario",
    "servicios_cita",
)


def activar_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    for tabla in _TABLAS:
        schema_editor.execute(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY')

    schema_editor.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon';
                EXECUTE 'GRANT SELECT ON servicios_servicio TO anon';
                EXECUTE 'CREATE POLICY servicios_publicos_lectura
                    ON servicios_servicio
                    FOR SELECT
                    TO anon
                    USING (activo = TRUE)';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated';
            END IF;
        END
        $$;
        """
    )


def desactivar_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute("DROP POLICY IF EXISTS servicios_publicos_lectura ON servicios_servicio")
    schema_editor.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                EXECUTE 'REVOKE SELECT ON servicios_servicio FROM anon';
            END IF;
        END
        $$;
        """
    )
    for tabla in reversed(_TABLAS):
        schema_editor.execute(f'ALTER TABLE "{tabla}" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [
        ("servicios", "0007_datos_cliente_y_privacidad"),
    ]

    operations = [
        migrations.RunPython(activar_rls, desactivar_rls),
    ]
