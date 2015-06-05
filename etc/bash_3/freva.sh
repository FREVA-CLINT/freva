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
    # check for databrowser as first argument behind freva command to autocomplete or not
    if [[ "${COMP_WORDS[1]}" == "--databrowser" ]]; then
    # convert upper case letters to lower ones
	cur="$(echo "${COMP_WORDS[COMP_CWORD]}" | tr '[:upper:]' '[:lower:]')"
# this is the former version, pls uncomment if case problems occur
#    cur="${COMP_WORDS[COMP_CWORD]}"
	query="$(_solr_query "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
	case "$cur" in
	    -*)
		opts="--all-facets --attributes --batch-size --count-facet-values -d --debug --facet -h --help --multiversion"
		COMPREPLY=( $(compgen -W "${opts}" -- "$cur") )
		;;
	    *=)
		opts="$(freva --databrowser --facet "${cur/=}" $query | sed -e 's/[^:]*: //' -e 's/,/ /g')"
		COMPREPLY=( $(compgen -W "${opts}") )
		;;
	    *=*)
		opts="$(freva --databrowser --facet "${cur/=*}" $query ${cur}* | sed -e 's/[^:]*: //' -e 's/,/ /g')"
		COMPREPLY=( $(compgen -W "${opts}" -- "${cur#*=}") )
		;;
	    *)
		prev="${COMP_WORDS[COMP_CWORD-1]}"
		[[ -z "$cur" ]] && extra=--relevant-only
		
		if [[ "$prev" == "--facet" ]]; then
		    opts="$(freva --databrowser $extra --attributes $query | sed  -e 's/,//g')"
		elif [[ "$prev" == "--baseline" ]]; then
		    opts="0 1"
		else
		    opts="$(freva --databrowser $extra --attributes $query | sed  -e 's/,/=/g')="
		fi
		COMPREPLY=( $(compgen -W "${opts}" -- "$cur") )
	esac	
    fi
} 2>/dev/null
complete -o nospace -o default -F _solr_search_show "freva" 
