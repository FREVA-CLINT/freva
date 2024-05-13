"""
Created on 21.04.2015

@author: sebastian.illing@met.fu-berlin.de
"""

import warnings

from django.contrib.auth.models import User
from django.db import models

warnings.warn(
    (
        "The evaluation_system.model.solr_models module will be removed from "
        "v2304.0.0"
    ),
    category=PendingDeprecationWarning,
)


class UserCrawl(models.Model):
    """
    Simple model to track user solr-crawls
    """

    class Meta:
        db_table = "solr_usercrawl"
        app_label = "solr"

    STATUS = [
        ("waiting", "waiting"),
        ("crawling", "crawling"),
        ("ingesting", "ingesting"),
        ("success", "success"),
        ("failed", "failed"),
    ]

    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    path_to_crawl = models.CharField(max_length=1000)
    tar_file = models.CharField(max_length=255, blank=True)
    ingest_msg = models.TextField(blank=True)
