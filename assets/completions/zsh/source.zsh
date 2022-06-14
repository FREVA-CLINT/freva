comp_dir=$(dirname $(readlink -f $0))
setopt COMPLETE_ALIASES
fpath+=($comp_dir)
source ${comp_dir}/completions.zsh
compinit -u
