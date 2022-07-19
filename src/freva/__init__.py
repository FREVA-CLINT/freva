"""
freva -- Free University Evaluation System

@copyright:  2016 FU Berlin. All rights reserved.

@contact:    sebastian.illing@met.fu-berlin.de

@license:    BSD

Copyright (c) 2016, FU Berlin
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
 are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import importlib
from evaluation_system import __version__

__all__ = [
    "crawl_my_data",
    "databrowser",
    "run_plugin",
    "list_plugins",
    "plugin_doc",
    "read_plugin_cache" "esgf",
    "history",
]


def __getattr__(name):
    if name in ["crawl_my_data", "databrowser", "esgf", "history"]:
        return getattr(importlib.import_module(f"._{name}", __name__), name)
    elif name in [
        "run_plugin",
        "list_plugins",
        "plugin_doc",
        "get_tools_list",
        "read_plugin_cache",
    ]:
        return getattr(importlib.import_module(f"._plugin", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
