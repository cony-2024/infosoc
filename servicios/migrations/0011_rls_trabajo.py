from django.db import migrations


def activar_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute('ALTER TABLE "servicios_trabajo" ENABLE ROW LEVEL SECURITY')
    schema_editor.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                EXECUTE 'REVOKE ALL ON servicios_trabajo FROM anon';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                EXECUTE 'REVOKE ALL ON servicios_trabajo FROM authenticated';
            END IF;
        END
        $$;
        """
    )


def desactivar_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute('ALTER TABLE "servicios_trabajo" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):

    dependencies = [
        ("servicios", "0010_trabajo"),
    ]

    operations = [
        migrations.RunPython(activar_rls, desactivar_rls),
    ]