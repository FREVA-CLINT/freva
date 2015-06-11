_freva_query() {
    local query 
    for elem in "$@"; do
        [[ "${elem:0:1}" == "-" ]] || grep -qv =<<<"$elem" && continue
        query="$query $elem"
    done    
    echo "$query"
}

_freva_containsElement() {
local e
  for e in "${@:2}"; do [[ "$e" == "$1" ]] && echo "True" ; done
}

_freva_show() {
    local cur opts query extra
    argarray=("--help" "--plugin" "--history" "--databrowser" "--crawl_my_data" "--esgf")
    # check for databrowser as first argument behind freva command to autocomplete or not
    if [[ "${COMP_WORDS[1]}" == "--databrowser" ]]; then    
	NOSPACE="-o nospace"
   # convert upper case letters to lower ones
	cur="$(echo "${COMP_WORDS[COMP_CWORD]}" | tr '[:upper:]' '[:lower:]')"
# this is the former version, pls uncomment if case problems occur
#    cur="${COMP_WORDS[COMP_CWORD]}"
	query="$(_freva_query "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
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
    elif [[ "$(_freva_containsElement ${COMP_WORDS[1]} ${argarray[@]})" != True ]]; then
	cur="$(echo "${COMP_WORDS[COMP_CWORD]}" | tr '[:upper:]' '[:lower:]')"                        
        query="$(_freva_query "${COMP_WORDS[@]:1:COMP_CWORD-1}")"
        case "$cur" in
	    *)
		prev="${COMP_WORDS[COMP_CWORD-1]}"
		opts=$(echo ${argarray[@]})
                COMPREPLY=( $(compgen -W "${opts}" -- "$cur"  ) )
		;;
	esac
    elif [[ "${COMP_WORDS[2]}" == "--help" ]]; then
	freva ${COMP_WORDS[1]} ${COMP_WORDS[2]}
    fi
} 2>/dev/null

complete -o nospace -o default -F _freva_show freva 
