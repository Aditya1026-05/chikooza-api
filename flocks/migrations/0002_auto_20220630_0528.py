from django.db import migrations, transaction

from common.base_models import PublicId


def create_admin(apps, schema_editor):
    Breed = apps.get_model("flocks", "Breed")
    args_list = ["Hubbard", 'BV300', 'BV415' "AP95", "COB400", "COB430", "COB500", "ROSS208"]
    for val in args_list:
        with transaction.atomic():
            breed = Breed()
            breed.public_id = PublicId.create_public_id()
            breed.name = val
            breed.code = val
            breed.line = val
            breed.save()


class Migration(migrations.Migration):

    dependencies = [
        ('flocks', '0001_initial'),
    ]

    operations = [migrations.RunPython(create_admin)
    ]
