from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("farm", "0002_auto_20220630_0526"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE farms ADD COLUMN district varchar(255) NOT NULL DEFAULT '';",
                    migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="farm",
                    name="district",
                    field=models.CharField(blank=True, default="", max_length=255),
                ),
            ],
        ),
    ]
