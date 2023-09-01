"""Future dataset definitions"""
from django.db import models


class FuturesDB(models.Model):
    """Database definition for the future table."""

    history_id: models.IntegerField = models.IntegerField(default=-1)
    code: models.JSONField = models.JSONField(null=False)
    file_name: models.TextField = models.TextField(null=False)
    code_hash: models.CharField = models.CharField(
        null=False, max_length=64, unique=True
    )

    class Meta:
        db_table = "futures"
        app_label = "futures"
