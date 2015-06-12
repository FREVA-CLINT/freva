#This file must be sourced from bash!

etc_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [[ "${BASH_VERSION:0:1}" == "3" ]]; then
    . $etc_dir/bash_3/freva.sh && . $etc_dir/bash_3/solr.sh && echo bash 3.x auto-completion script successfully loaded
elif [[ "${BASH_VERSION:0:1}" == "4" ]]; then
    . $etc_dir/bash_4/freva.sh && . $etc_dir/bash_4/solr.sh && echo bash 4.x auto-completion script successfully loaded
fi
