__plugin() {
    # Help menu for the plugin subcommand
    local -a plugins args options
    local line state _values ret=1
    options=(${(f)"$(python3 -m freva.cli --shell zsh freva plugin)"})
    for arg in ${options};do
        first_char=$(echo ${arg}|cut -c1)
        if [ "${first_char}" = '-' ];then
            args+=(${arg})
        else
            plugins+=(${arg})
        fi
    done
    _arguments \
        ${args[@]} \
        '1: :->plugins' \
        '*:plugin options:__plugin_options' && ret=0
     case "${state}" in
        plugins)
            _values "Available plugins" "${plugins[@]}"
            ret=0
        ;;
     esac

}

__plugin_options() {

    local -a options
    integer ret=1
    local -a args keys search_keys
    let n=$CURRENT-1
    # Get all facets and entries depending on what has alread been typed
    if [ $n -ge 2 ];then
        for i in {2..$n};do
            arg=$(echo ${words[$i]}|cut -c1)
            if [ ! "${arg}" = '-' ];then
                search_keys+=("${words[$i]}")
            fi
        done
    fi
    options=(${(f)"$(python3 -m freva.cli --shell zsh --strip freva plugin ${search_keys[@]})"})
    for line in ${options};do
        key=$(echo $line|cut -d '[' -f1)
        keys+=("${line}:Plugin option:(${key})")
    done
    _values -s \  'plugin options' ${keys[@]}

}

__process() {
    local -a args options positional_args
    options=(${(f)"$(python3 -m freva.cli --shell zsh freva ${1})"})
    for arg in ${options[@]};do
        first_char=$(echo ${arg}|cut -c1)
        if [ "${first_char}" = '-' ];then
            args+=(${arg})
        else
            positional_args+=(${arg})
        fi
    done
    _arguments ${args[@]} '1::->pos'
    case "${state}" in
        pos)
           _values "Positional args" "${positional_args[@]}"
           ret=0
        ;;
        *)
            ;;
    esac
}

__solr() {
    local -a facets
    integer ret=1
    local -a args keys search_keys
    let n=$CURRENT-1
    # Get all facets and entries depending on what has alread been typed
    if [ $n -ge 2 ];then
        for i in {2..$n};do
            arg=$(echo ${words[$i]}|cut -c1)
            if [ ! "${arg}" = '-' ];then
                search_keys+=("${words[$i]}")
            fi
        done
    fi
    facets=(${(f)"$(python3 -m freva.cli --shell zsh --strip freva databrowser ${search_keys[@]})"})
    for line in ${facets};do
        facet=$(echo $line|cut -d : -f1)
        entries=$(echo $line|cut -d : -f2 |awk '{print $NF}'|sed 's/,/ /g')
        if [ ${#entries[*]} -ge 2 ]; then
            keys+=("${facet}[select ${facet} facet]:${facet} facet:(${entries})")
        fi
    done
    _values -s \  'search facets' ${keys[@]}
}

__databrowser() {
    local -a options args facets
    options=(${(f)"$(python3 -m freva.cli --shell zsh freva databrowser)"})
    for arg in ${options};do
        first_char=$(echo ${arg}|cut -c1)
        if [ "${first_char}" = '-' ];then
            args+=(${arg})
        else
            facets+=(${args})
        fi
    done
    if [ ${#facets} -eq 0 ];then
        _arguments \
            ${args[@]}
    else
        _arguments \
            ${args[@]} \
            '*:search facets:__solr'
    fi
}
