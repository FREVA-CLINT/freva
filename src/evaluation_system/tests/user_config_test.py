"""Test loading different configurations."""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import freva

from .conftest import get_config


def test_load_config(dummy_config) -> None:
    """Test loading a different config."""
    cfg, _ = get_config()
    with TemporaryDirectory() as temp_dir:
        eval_config = Path(temp_dir) / "evaluation_system.conf"
        cfg.set("evaluation_system", "solr.host", "foo.bar.com.au")
        with open(eval_config, "w") as f_obj:
            cfg.write(f_obj)
        assert dummy_config.get("solr.host") != "foo.bar.com.au"
        with freva.config(eval_config):
            assert dummy_config.get("solr.host") == "foo.bar.com.au"
        assert dummy_config.get("solr.host") != "foo.bar.com.au"
        with freva.config(eval_config):
            with pytest.raises(ValueError):
                freva.run_plugin("dummyplugin", the_number=1, batchmode=True)
            with pytest.warns(UserWarning):
                freva.run_plugin("dummyplugin", the_number=1)
