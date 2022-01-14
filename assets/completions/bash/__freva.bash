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
    [[ -z "$cur" ]] && extra=--relevant-only
    if [[ "$cur" == "=" ]]; then
        query="$(__cmd_query "${COMP_WORDS[@]:$1:COMP_CWORD-2}")"
        options="$(freva databrowser --facet $prev $query | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        #don't consider this for selection of possible auto-complete word
    elif [ "$prev" == "=" ]; then
        query="$(__cmd_query "${COMP_WORDS[@]:$1:COMP_CWORD-3}")"
        facet="${COMP_WORDS[COMP_CWORD-2]}"
        options="$(freva databrowser --facet $facet $query $facet=${cur}* | sed -e 's/[^:]*: //' -e 's/,/ /g')"
    elif [ "$(echo $cur |cut -c1)" == "-" ]; then
        options="$(python3 -m freva.cli --shell bash freva databrowser --flags-only)"
    elif [ "$prev" == "--facet" ]; then
        options="$(freva databrowser $extra --attributes $query | sed  -e 's/,//g')"
    else
        options="$(freva databrowser --attributes $query | sed  -e 's/,/=/g')="
    fi
    echo $options
}

__plugin() {

    local -a plugins args flags
    local plugin
    let num=$1
    args="$(python3 -m freva.cli --shell bash freva plugin)"
    cmd_args="${COMP_WORDS[@]:$1:COMP_CWORD-2}"
    if [ $num -gt $COMP_CWORD ];then
        echo $args
        return
    fi
    for arg in ${args};do
        if [ "$(echo $arg|cut -c1)" = "-" ];then
            flags="$flags $arg"
        else
            plugins="$plugins $arg"
        fi
    done
    for comp in ${cmd_args};do
        if [ ! "$(echo $comp|cut -c1)" = "-" ];then
            plugin=$comp
            break
        fi
    done
    if [ -z "$plugin" ];then
        echo $args
        return
    fi
    # We do have a plugin
    options="$(python3 -m freva.cli --shell bash --strip freva plugin $cmd_args)"
    for opt in $options;do
        if [ "${cmd_args##*${opt}*}" ];then
            echo ${opt}=
        fi
    done
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
        if [[ "$cur" == "=" ]]; then
            cur=
        fi
    else
        options="$(python3 -m freva.cli --shell bash --flags-only freva "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
        cur="$(echo "${COMP_WORDS[COMP_CWORD]}" | tr '[:upper:]' '[:lower:]')"
    fi
    COMPREPLY=( $(compgen -W "${options}" -- "$cur"  ) )
}
complete -o nospace -o default -F __freva freva
