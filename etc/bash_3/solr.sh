_solr_query() {
    local query 
    for elem in "$@"; do
        [[ "$elem" == "-*" ]] && continue
        query="$query $elem"
    done    
    echo "$query"
}

_solr_search_show() {
    local cur opts query
    cur="${COMP_WORDS[COMP_CWORD]}"
    query="$(_solr_query "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
    case "$cur" in
    *=)
        opts="$(solr_search --facet "${cur/=}" $query | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        COMPREPLY=( $(compgen -W "${opts}") )
        ;;
    *=*)
        opts="$(solr_search --facet "${cur/=*}" $query ${cur}* | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        COMPREPLY=( $(compgen -W "${opts}" "${cur#*=}") )
        ;;
    *)
        opts="$(solr_search --attributes $query | sed  -e 's/,/=/g')"
        COMPREPLY=( $(compgen -W "${opts}" "$cur") )
    esac
}

