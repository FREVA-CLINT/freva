_solr_query() {
    local query 
    for elem in "$@"; do
        [[ "${elem:0:1}" == "-" ]] || grep -qv =<<<"$elem" && continue
        query="$query $elem"
    done    
    echo "$query"
}

_solr_search_show() {
    local cur opts query extra
    cur="${COMP_WORDS[COMP_CWORD]}"
    query="$(_solr_query "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
    case "$cur" in
    -*)
        opts="--all-facets --attributes --baseline --baseline0 --baseline1 --batch-size --cmip5 --count-facet-values -d --debug --facet -h --help --multiversion --observations --reanalysis"
        COMPREPLY=( $(compgen -W "${opts}" -- "$cur") )
        ;;
    *=)
        opts="$(solr_search --facet "${cur/=}" $query | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        COMPREPLY=( $(compgen -W "${opts}") )
        ;;
    *=*)
        opts="$(solr_search --facet "${cur/=*}" $query ${cur}* | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        COMPREPLY=( $(compgen -W "${opts}" -- "${cur#*=}") )
        ;;
    *)
        prev="${COMP_WORDS[COMP_CWORD-1]}"
        [[ -z "$cur" ]] && extra=--relevant-only
        
        if [[ "$prev" == "--facet" ]]; then
            opts="$(solr_search $extra --attributes $query | sed  -e 's/,//g')"
        elif [[ "$prev" == "--baseline" ]]; then
            opts="0 1"
        else
            opts="$(solr_search $extra --attributes $query | sed  -e 's/,/=/g')="
        fi
        COMPREPLY=( $(compgen -W "${opts}" -- "$cur") )
    esac
} 2>/dev/null
complete -o nospace -F _solr_search_show solr_search