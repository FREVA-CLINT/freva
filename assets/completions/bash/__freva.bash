_solr_query() {
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
    #all_opts="$(echo "${COMP_WORDS[@]:$1:COMP_CWORD-1}"|sed 's/ =/=/g'|sed 's/= /=/g')"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    cur="${COMP_WORDS[COMP_CWORD],,}"
    [[ -z "$cur" ]] && extra=--relevant-only
    if [[ "$cur" == "=" ]]; then
        query="$(_solr_query "${COMP_WORDS[@]:$1:COMP_CWORD-2}")"
        options="$(freva databrowser --facet $prev $query | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        #don't consider this for selection of possible auto-complete word
    elif [ "$prev" == "=" ]; then
        query="$(_solr_query "${COMP_WORDS[@]:$1:COMP_CWORD-3}")"
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

__freva() {

    local options args
    if [ "${COMP_WORDS[1]}" == "databrowser" ];then
        options="$(__databrowser 2)"
        cur="${COMP_WORDS[COMP_CWORD],,}"
        if [[ "$cur" == "=" ]]; then
            cur=
        fi
    else
        options="$(python3 -m freva.cli --shell bash freva "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
        cur="$(echo "${COMP_WORDS[COMP_CWORD]}" | tr '[:upper:]' '[:lower:]')"
    fi
    COMPREPLY=( $(compgen -W "${options}" -- "$cur"  ) )
}
complete -o nospace -o default -F __freva freva
