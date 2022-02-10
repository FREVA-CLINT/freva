from django.db import models
from django.contrib.auth.models import User


class ToolPullRequest(models.Model):
    """
    Keep track of pull requests for tools
    """

    created = models.DateTimeField(auto_now_add=True)
    tool = models.CharField(max_length=50)
    tagged_version = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    STATUS = [
        ("waiting", "waiting"),
        ("processing", "processing"),
        ("success", "success"),
        ("failed", "failed"),
    ]
    status = models.CharField(max_length=10, choices=STATUS)

    class Meta:
        app_label = "plugins"


class Version(models.Model):
    """
    The class belongs to a table holding all software versions used
    """

    #: Date and time when the process were scheduled
    timestamp = models.DateTimeField()
    #: Name of the tool
    tool = models.CharField(max_length=50)
    #: Version of the tool
    version = models.CharField(max_length=20)
    #: The tools internal version of a code versioning system
    internal_version_tool = models.CharField(max_length=40)
    #: The evaluation system's internal version
    internal_version_api = models.CharField(max_length=40)
    #: the repository to checkout thing
    repository = models.TextField()

    class Meta:
        app_label = "plugins"


class Parameter(models.Model):
    """
    Model for the tool parameter

    The entries tool and version seem to be redundant,
    but it could be necessary for not versioned tools.
    """

    class Impact(object):
        affects_values = 0
        affects_plots = 5
        no_effects = 9

    class Meta:
        app_label = "plugins"

    #: name of the parameter
    parameter_name = models.CharField(max_length=50)
    #: type of the parameter
    parameter_type = models.CharField(max_length=50)
    #: Name of the tool
    tool = models.CharField(max_length=50)
    #: Version of the tool
    version = models.IntegerField()
    #: mandatory
    mandatory = models.BooleanField()
    #: default value
    default = models.CharField(max_length=255, null=True, blank=True)
    #: how strong affects this parameter the output?
    IMPACT_CHOICES = (
        (Impact.affects_values, "Parameter affects values"),
        (Impact.affects_plots, "Parameter affects plots"),
        (Impact.no_effects, "No effects on output"),
    )

    impact = models.IntegerField(choices=IMPACT_CHOICES, default=Impact.affects_values)

    def __str__(self):
        return self.parameter_name
