from django.db import models

from evaluation_system.api.parameters import ParameterType

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


class Parameter(models.Model):
    """
    Model for the tool parameter
    
    The entries tool and version seem to be redundant,
    but it could be necessary for not versioned tools. 
    """
    #: name of the parameter
    parameter_name = model.CharField(max_length=50)
    #: type of the parameter
    parameter_type = model.CharField(max_length=50)
    #: Name of the tool
    tool = models.CharField(max_length=50)
    #: Version of the tool
    version = models.CharField(max_length=20)
    #: the (repository) version
    detailed_version = models.ForeignKey(Version, default=1)
    #: mandatory
    mandatory = models.BooleanField()
    #: default value
    default = models.CharField(max_length=255)
    #: how strong affects this parameter the output?
    IMPACT_CHOICES = ((ParameterType.Impact.affects_values, 'Parameter affects values'),
                      (ParameterType.Impact.affects_plots, 'Parameter affects plots'),
                      (ParameterType.Impact.no_effects, 'No effects on output'),)
    
    impact = models.IntegerField(max_length = 1,
                                 choices = IMPACT_CHOICES,
                                 default = ParameterType.Impact.affects_values)
    
class Configuration(models.Model):
    """
    Holds the configuration
    """
    #: history id
    history_id = model.ForeignKey(History)
    
    #: parameter number
    parameter_id = models.ForeignKey(Parameter)
    
    #: md5 checksum of value (not used, yet)
    md5 = models.CharField(max_length=32, default='')
    
    #: value
    value = models.TextField()
    
    #; is the default value used?
    is_default = models.BooleanField()