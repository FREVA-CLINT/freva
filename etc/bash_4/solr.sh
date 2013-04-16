_solr_query() {
    local -a arr=( "$@" )
    local query i
    for (( i = 0 ; i < ${#arr[@]} ; i++ )) do
        [[ "${arr[i]}" == -* ]] && continue
        query="$query ${arr[i]}=${arr[i+2]}"
        ((i+=2))
    done
    
    echo "$query"
}
_solr_search_show() {
    local cur opts query
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    if [[ "$cur" == "=" ]]; then
        query="$(_solr_query "${COMP_WORDS[@]:1:COMP_CWORD-2}")"
        opts="$(solr_search --facet $prev $query | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        opts="${opts#*: }"      #remove the ensemble name
        opts="${opts//,/ }"      #remove the commas
        COMPREPLY=( $(compgen -W "${opts}") )
    elif [[ "$prev" == "=" ]]; then
        query="$(_solr_query "${COMP_WORDS[@]:1:COMP_CWORD-3}")"
        facet="${COMP_WORDS[COMP_CWORD-2]}"
        opts="$(solr_search --facet $facet $query $facet=${cur}* | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        COMPREPLY=( $(compgen -W "${opts}" "$cur") )
    else
        opts="$(solr_search --attributes $query | sed  -e 's/,//g')"
        COMPREPLY=( $(compgen -W "${opts}" "$cur") )
    fi
}
complete -o nospace -F _solr_search_show solr_search