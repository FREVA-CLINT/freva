import os
import shutil
import tempfile
import time
from pathlib import Path
from subprocess import PIPE, run

import numpy as np
import pandas as pd
import xarray as xr
from netCDF4 import Dataset as nc
from PIL import Image

from evaluation_system.api.parameters import (
    Directory,
    Float,
    InputDirectory,
    Integer,
    ParameterDictionary,
    SolrField,
    String,
)
from evaluation_system.api.plugin import PluginAbstract
from evaluation_system.model.db import UserDB
from evaluation_system.model.user import User


class ClimdexCalc(PluginAbstract):
    """Stub class for implementing the abstract one"""

    __short_description__ = "Climate extreme index"
    __long_description__ = ""
    __tags__ = ["foo"]
    __version__ = ("foo", "bar")
    __category__ = "statistical"
    __name__ = "ClimdexCalc"
    __parameters__ = ParameterDictionary(
        SolrField(
            name="project",
            facet="project",
            help="Input project",
            mandatory=True,
        ),
        String(name="product", help="Input product", mandatory=True),
        String(name="institute", help="Input institute", mandatory=True),
        String(name="model", help="Input model", mandatory=True),
        String(name="experiment", help="Input experiment", mandatory=True),
        String(name="ensemble", help="Input ensemble", mandatory=True),
        String(name="timeperiod", help="The input years", default="1979,2010"),
        Integer(name="ntasks", help="The number of cores to be used", default=8),
        String(
            name="indices",
            help="Output indices",
            default="tx10p,tx90p,tn10p,tn90p",
        ),
        Directory(
            name="outputdir",
            default="$USER_OUTPUT_DIR/$SYSTEM_DATETIME",
            mandatory=False,
            help="The default output directory",
        ),
    )
    _template = "${number} - $something - $other"
    tool_developer = {"name": "DummyUser", "email": "data@dkrz.de"}

    def run_tool(self, config_dict):
        out_dir = Path(config_dict["outputdir"]).absolute().expanduser()
        out_dir.mkdir(exist_ok=True, parents=True)
        indices = [i.strip() for i in config_dict["indices"].split(",") if i.strip()]
        years = [
            int(i.strip()) for i in config_dict["timeperiod"].split(",") if i.strip()
        ]
        dates = xr.DataArray(
            data=pd.date_range(f"{years[0]}-01-01", f"{years[1]}-12-31", freq="m"),
            name="time",
            dims=("time",),
            attrs={"standard_name": "time", "axis": "T", "long_name": "time"},
        )
        out_dir = (
            out_dir
            / config_dict["project"]
            / config_dict["product"]
            / config_dict["institute"]
            / config_dict["model"]
            / config_dict["experiment"]
            / "mon"
            / "atmos"
        )
        for idx in indices:
            output_dir = out_dir / idx / config_dict["ensemble"]
            out_file = (
                f"{idx}_mon_{config_dict['model']}_"
                f"{config_dict['experiment']}_{config_dict['ensemble']}"
                f"_{years[0]}-{years[-1]}.nc"
            )
            data = np.random.random_sample(len(dates)) * 10

            dset = xr.Dataset(
                {
                    idx: xr.DataArray(
                        data=data,
                        name=idx,
                        dims=("time",),
                        coords={"time": dates},
                        attrs={"long_name": "Some extreme index"},
                    )
                }
            )
            output_dir.mkdir(exist_ok=True, parents=True)
            dset.to_netcdf(output_dir / out_file)
        return self.prepare_output(config_dict["outputdir"])
