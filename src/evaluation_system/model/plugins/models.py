from django.db import models

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
