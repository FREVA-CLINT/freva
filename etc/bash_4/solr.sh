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
    local cur opts query extra
    # in bash4 this line converts the entries to lower case, s.t. a completion
    # becomes case insensitive
    cur="${COMP_WORDS[COMP_CWORD],,}"
    # if the is some trouble with case insensitivity then uncomment the
    # following line of code
    # cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    #if we have no value we will concentrate on relevant ones, if applicable
    #(if not, we have to consider all of them)
    [[ -z "$cur" ]] && extra=--relevant-only

    if [[ "$cur" == "=" ]]; then
        query="$(_solr_query "${COMP_WORDS[@]:1:COMP_CWORD-2}")"
        opts="$(solr_search --facet $prev $query | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        #don't consider this for selection of possible auto-complete word
        cur=
        
    elif [[ "$prev" == "=" ]]; then
        query="$(_solr_query "${COMP_WORDS[@]:1:COMP_CWORD-3}")"
        facet="${COMP_WORDS[COMP_CWORD-2]}"
        opts="$(solr_search --facet $facet $query $facet=${cur}* | sed -e 's/[^:]*: //' -e 's/,/ /g')"
        
    elif [[ "${cur:0:1}" == "-" ]]; then
        opts="--all-facets --attributes --baseline --baseline0 --baseline1 --batch-size --cmip5 --count-facet-values -d --debug --facet -h --help --multiversion --observations --reanalysis"
        
    elif [[ "$prev" == "--facet" ]]; then
        opts="$(solr_search $extra --attributes $query | sed  -e 's/,//g')"
    else
        opts="$(solr_search $extra --attributes $query | sed  -e 's/,/=/g')="
    fi

    COMPREPLY=( $(compgen -W "${opts}" -- "$cur") )

#    cat >>/tmp/autocom.log <<EOF
#query: '$query'
#prev: '$prev'
#cur: '$cur'
#opts: '$opts'
#facet: '$facet'
#value: '$value'
#EOF
}
complete -o nospace -F _solr_search_show solr_search
