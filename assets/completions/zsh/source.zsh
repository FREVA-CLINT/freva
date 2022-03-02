comp_dir=$(dirname $(readlink -f $0))
setopt COMPLETE_ALIASES
zstyle ':completion::complete:*' gain-privileges 1
autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
[[ -n "${key[Up]}"   ]] && bindkey -- "${key[Up]}"   up-line-or-beginning-search
[[ -n "${key[Down]}" ]] && bindkey -- "${key[Down]}" down-line-or-beginning-search
fpath+=($comp_dir)
source ${comp_dir}/completions.zsh
source /usr/share/zsh/functions/Completion/compinit 1> /dev/null



