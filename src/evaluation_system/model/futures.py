"""Future dataset definitions"""
from django.db import models


class FutureFilesDB(models.Model):
    """Database definition for the future table."""

    code_hash: models.CharField = models.CharField(
        null=False, max_length=64, unique=True, primary_key=True
    )
    file_names: models.JSONField = models.JSONField(null=False)

    class Meta:
        db_table = "future_files"
        app_label = "futures"


class FutureCodeDB(models.Model):
    """Database definition for the future table."""

    code_hash: models.OneToOneField = models.OneToOneField(
        FutureFilesDB,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="code_hash",
    )
    history_id: models.IntegerField = models.IntegerField(default=-1)
    code: models.JSONField = models.JSONField(null=False)
    file_name: models.TextField = models.TextField(null=False)

    class Meta:
        db_table = "future_recipe"
        app_label = "futures"
