from django.db import migrations, models


def mark_existing_active_users_verified(apps, schema_editor):
    User = apps.get_model("core", "User")
    User.objects.filter(is_active=True).update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_user_activation_code_user_activation_code_expires_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            mark_existing_active_users_verified,
            migrations.RunPython.noop,
        ),
    ]
