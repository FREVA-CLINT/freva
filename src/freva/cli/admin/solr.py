"""Collection of admin commands for apache solr requests."""

__all__ = ["SolrIndex"]


from ..utils import BaseCompleter, BaseParser, parse_type

class SolrIndex(BaseParser):
    """Consturt a command line parser that indexes the apache solr server."""
    
    desc = "Re-Index apache solr server."
    
    def __init__(self,
                 command: str = "freva"
                 parser: Optional[parse_type] = None
                ):
        """Construct the reindex sub arg. parser."""
        subparser = parser or argparse.ArgumentParser(
                prog=f"{command}-reindex",
                description=self.desc,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

