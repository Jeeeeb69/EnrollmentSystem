from django.db import migrations, models


def add_email_verified_if_missing(apps, schema_editor):
    User = apps.get_model("core", "User")
    table_name = User._meta.db_table
    column_names = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            table_name,
        )
    }

    if "email_verified" not in column_names:
        field = models.BooleanField(default=False)
        field.set_attributes_from_name("email_verified")
        schema_editor.add_field(User, field)


def mark_existing_active_users_verified(apps, schema_editor):
    User = apps.get_model("core", "User")
    User.objects.filter(is_active=True).update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_user_activation_code_user_activation_code_expires_at"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_email_verified_if_missing,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="user",
                    name="email_verified",
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
        migrations.RunPython(
            mark_existing_active_users_verified,
            migrations.RunPython.noop,
        ),
    ]
