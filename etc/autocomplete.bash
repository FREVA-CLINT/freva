#This file must be sourced from bash!
sh=$(echo $SHELL|sed 's#/# #g'|awk '{print $NF}')
if [ "$sh" = "bash" ] || [ "$sh" = "sh" ];then
    etc_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    let bash_major=${BASH_VERSION:0:1}
    if [[ $bash_major -le 3 ]]; then
        . $etc_dir/bash_3/freva.sh && . $etc_dir/bash_3/solr.sh && echo bash 3.x auto-completion script successfully loaded
    elif [ "$bash_major" ];then
        . $etc_dir/bash_4/freva.sh && . $etc_dir/bash_4/solr.sh && echo bash 4.x auto-completion script successfully loaded
    fi
elif [ "$sh" = "zsh" ];then
    etc_dir=$(dirname $(readlink -f $0))
    let zsh_major=${ZSH_VERSION:0:1}
    setopt COMPLETE_ALIASES
    zstyle ':completion::complete:*' gain-privileges 1
    autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
    zle -N up-line-or-beginning-search
    zle -N down-line-or-beginning-search
    [[ -n "${key[Up]}"   ]] && bindkey -- "${key[Up]}"   up-line-or-beginning-search
    [[ -n "${key[Down]}" ]] && bindkey -- "${key[Down]}" down-line-or-beginning-search
    fpath+=($etc_dir/zsh)
    source /usr/share/zsh/functions/Completion/compinit 1> /dev/null
fi
