#This file must be sourced from bash!

etc_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [[ "${BASH_VERSION:0:1}" == "3" ]]; then
    . $etc_dir/bash_3/* && echo Successfully loaded scripts for bash 3.x
elif [[ "${BASH_VERSION:0:1}" == "4" ]]; then
    . $etc_dir/bash_3/* && echo Successfully sourced scripts for bash 4.x
fi
