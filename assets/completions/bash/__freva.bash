__cmd_query() {
    local -a arr=( "$@" )
    local query i
    for (( i = 0 ; i < ${#arr[@]} ; i++ )) do
        [[ "${arr[i]}" == -* ]] && continue
        query="$query ${arr[i]}=${arr[i+2]}"
        ((i+=2))
    done
    echo "$query" |set 's/=//g'
}


__databrowser() {
    local options args facets extra
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    cur="${COMP_WORDS[COMP_CWORD],,}"
    let num=$1
    if [ $num -eq 1 ];then
        cmd_args="${COMP_WORDS[@]:$1:COMP_CWORD-1}"
        cmd_args_prev="${COMP_WORDS[@]:$1:COMP_CWORD}"
    else
        cmd_args="${COMP_WORDS[@]:$1:COMP_CWORD-2}"
        cmd_args_prev="${COMP_WORDS[@]:$1:COMP_CWORD-3}"
    fi
    [[ -z "$cur" ]] && extra=--relevant-only
    if [[ "$cur" == "=" ]]; then
        query="$(__cmd_query $cmd_args)"
        options="$(freva databrowser --facet $prev $query | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        #don't consider this for selection of possible auto-complete word
    elif [ "$prev" == "=" ]; then
        query="$(__cmd_query "${cmd_args_prev}")"
        facet="${COMP_WORDS[COMP_CWORD-2]}"
        options="$(freva databrowser --facet $facet $query $facet=${cur}* | sed -e 's/[^:]*: //' -e 's/,/ /g')"
    elif [ "$prev" == "--facet" ]; then
        options="$(freva databrowser $extra --attributes $query | sed  -e 's/,//g')"
    elif [ "$(echo $cur |cut -c1)" == "-" ]; then
        for arg in ${cmd_args[@]};do
            if [ "$(echo $arg|cut -c1)" = "-" ];then
                flags="$flags $arg"
            fi
        done
        options="$(python3 -m freva.cli --shell bash --flags-only freva databrowser $flags)"
    else
        options="$(freva databrowser --attributes $query | sed  -e 's/,/=/g')="
    fi
    echo $options
}

__plugin() {

    local -a plugins args flags
    local plugin
    let num=$1
    if [ $COMP_CWORD -lt 2 ];then
        cmd_args="${COMP_WORDS[@]:$1:COMP_CWORD-1}"
    else
        cmd_args="${COMP_WORDS[@]:$1:COMP_CWORD-1}"
    fi
    if [ $num -ge $COMP_CWORD ];then
        if [ "$(echo $cur |cut -c1)" == "-" ]; then
            options="$(python3 -m freva.cli --shell bash --flags-only freva plugin)"
        else
            options="$(python3 -m freva.cli --shell bash --strip freva plugin)"
        fi
    elif [ "$(echo $cur |cut -c1)" == "-" ]; then
        for arg in ${cmd_args[@]};do
            if [ "$(echo $arg|cut -c1)" = "-" ];then
                flags="$flags $arg"
            fi
        done
        options="$(python3 -m freva.cli --shell bash --flags-only freva plugin $flags)"
    else
        for comp in ${cmd_args[@]};do
            if [ ! "$(echo $comp|cut -c1)" == "-" ];then
                plugin=$comp
                break
            fi
        done
        if [ -z "$plugin" ];then
            cur=""
            options="$(python3 -m freva.cli --shell bash --strip freva plugin)"
        else
            # We do have a plugin
            opts="$(python3 -m freva.cli --shell bash --strip freva plugin $cmd_args)"
            options=''
            for opt in $opts;do
                if [ "${cmd_args##*${opt}*}" ];then
                    echo ${opt}=
                fi
            done
        fi
    fi
    echo $options
}

__freva_databrowser() {

    options="$(__databrowser 1)"
    cur="${COMP_WORDS[COMP_CWORD],,}"
    if [[ "$cur" == "=" ]]; then
        cur=
    fi
    COMPREPLY=( $(compgen -W "${options}" -- "$cur"  ) )
}

__freva_plugin() {

    options="$(__plugin 1)"
    cur="${COMP_WORDS[COMP_CWORD]}"
    if [ "$cur" == "=" ]; then
        cur=
    elif [ "$cur" == "-" ] && [ -z "$(echo $options|grep - '-')" ];then
        # Something is odd with compgen, I have no clue why this happens
       cur=
    fi
    COMPREPLY=( $(compgen -W "${options}" -- "$cur"  ) )
}


__freva_history() {

    options="$(python3 -m freva.cli --shell bash --flags-only freva history "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
    cur="$(echo "${COMP_WORDS[COMP_CWORD]}" | tr '[:upper:]' '[:lower:]')"
    COMPREPLY=( $(compgen -W "${options}" -- "$cur"  ) )
}


__freva_esgf() {
    options="$(python3 -m freva.cli --shell bash --flags-only freva esgf "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
    cur="$(echo "${COMP_WORDS[COMP_CWORD]}" | tr '[:upper:]' '[:lower:]')"
    COMPREPLY=( $(compgen -W "${options}" -- "$cur"  ) )
}


__freva_crawl_my_data() {
    options="$(python3 -m freva.cli --shell bash --flags-only freva crawl-my-data "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
    cur="$(echo "${COMP_WORDS[COMP_CWORD]}" | tr '[:upper:]' '[:lower:]')"
    COMPREPLY=( $(compgen -W "${options}" -- "$cur"  ) )
}


__freva() {

    local options args
    if [ "${COMP_WORDS[1]}" == "databrowser" ];then
        options="$(__databrowser 2)"
        cur="${COMP_WORDS[COMP_CWORD],,}"
        if [[ "$cur" == "=" ]]; then
            cur=
        fi
    elif [ "${COMP_WORDS[1]}" == "plugin" ];then
        options="$(__plugin 2)"
        cur="${COMP_WORDS[COMP_CWORD],,}"
        if [ "$cur" == "=" ]; then
            cur=
        elif [ "$cur" == "-" ] && [ -z "$(echo $options|grep - '-')" ];then
            # Something is odd with compgen, I have no clue why this happens
            cur=
        fi
    else
        options="$(python3 -m freva.cli --shell bash --flags-only freva "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
        cur="$(echo "${COMP_WORDS[COMP_CWORD]}" | tr '[:upper:]' '[:lower:]')"
    fi
    COMPREPLY=( $(compgen -W "${options}" -- "$cur"  ) )
}
complete -F __freva_plugin freva-plugin
complete -o nospace -o default -F __freva freva
complete -o nospace -o default -F __freva_history freva-history
complete -o nospace -o default -F __freva_esgf freva-esgf
complete -o nospace -o default -F __freva_crawl_my_data freva-crawl-my-data
complete -o nospace -o default -F __freva_databrowser freva-databrowser
