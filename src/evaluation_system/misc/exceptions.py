"""Definitions of custom exections."""


class PluginNotFoundError(Exception):
    """Exeption Definition for missing Plugins."""
    pass

class ValidationError(Exception):
    """Thrown if some variable contains an improper value."""
    pass

class ParameterNotFoundError(Exception):
    """Thrown if some parameter is not in the database."""
    pass




