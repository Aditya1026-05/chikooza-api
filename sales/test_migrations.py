from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

from django.db import models
from django.test import SimpleTestCase

buyer_phone_migration = import_module(
    "sales.migrations.0009_alter_sales_buyer_phone_no"
)


class BuyerPhoneMigrationTests(SimpleTestCase):
    def test_sqlite_skips_table_rebuild(self):
        apps = Mock()
        schema_editor = Mock(
            connection=SimpleNamespace(vendor="sqlite"),
        )

        buyer_phone_migration.forwards(apps, schema_editor)

        apps.get_model.assert_not_called()
        schema_editor.alter_field.assert_not_called()

    def test_non_sqlite_forward_and_reverse_use_real_schema_alteration(self):
        sales_model = Mock()
        apps = Mock()
        apps.get_model.return_value = sales_model
        schema_editor = Mock(
            connection=SimpleNamespace(vendor="postgresql"),
        )

        buyer_phone_migration.forwards(apps, schema_editor)
        buyer_phone_migration.backwards(apps, schema_editor)

        forward_call, reverse_call = schema_editor.alter_field.call_args_list
        self.assertEqual(type(forward_call.args[1]), models.IntegerField)
        self.assertEqual(type(forward_call.args[2]), models.BigIntegerField)
        self.assertEqual(type(reverse_call.args[1]), models.BigIntegerField)
        self.assertEqual(type(reverse_call.args[2]), models.IntegerField)
        self.assertIs(forward_call.args[1].model, sales_model)
        self.assertIs(reverse_call.args[2].model, sales_model)
