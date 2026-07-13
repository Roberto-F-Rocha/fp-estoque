from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventory", "0002_full_system_upgrade_marker")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE inventory_movement "
                        "ADD COLUMN IF NOT EXISTS unit_sale_price numeric(12, 2) NOT NULL DEFAULT 0;"
                    ),
                    reverse_sql=(
                        "ALTER TABLE inventory_movement "
                        "DROP COLUMN IF EXISTS unit_sale_price;"
                    ),
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="movement",
                    name="unit_sale_price",
                    field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
                )
            ],
        )
    ]
