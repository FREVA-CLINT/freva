#!bash
# This script is to be called by the tcsh 'complete' command.
# It should be called by setting up a 'complete' command in the tcsh shell like this:
#
root_path=$(cd `dirname $0` && pwd)
common_functions="${root_path}/common-functions.bash"

# Allow for debug printouts when running the script by hand
if [ "$1" == "-d" ] || [ "$1" == "--debug" ]; then
    debug=true
    shift
fi

completionScript="$(dirname $root_path)/bash/__freva.bash"
commandToComplete=${@:1:$#}

if [ "${debug}" == "true" ]; then
    echo =====================================
    echo $0 called towards $completionFunction from $completionScript
    echo with command to complete: $commandToComplete
fi
if [ -e ${completionScript} ]; then
	source ${completionScript}
fi

# Set the bash completion variables
#
export COMP_LINE=${commandToComplete}
#
# TODO: set the below in case the cursor is in the middle of the line
export COMP_POINT=${#COMP_LINE}
#
# TODO: Set to an integer value corresponding to the type of completion
# attempted that caused a completion function to be called:
#   9 (TAB) for normal completion,
#   63 ('?') for listing completions after successive tabs,
#   33 ('!') for listing alternatives on partial word completion,
#   64 ('@') to list completions if the word is not unmodified,
#   37 ('%') for menu completion.
export COMP_TYPE=9
#
# TODO: The key (or final key of a key sequence) used to invoke the current completion function.
# Could be 9 for TAB but could also be 27 for Esc or maybe something else I didn't think of.
export COMP_KEY=9
#
# Remove the colon as a completion separator because tcsh cannot handle it
export COMP_WORDBREAKS=${COMP_WORDBREAKS//:}
#
# Set COMP_WORDS in a way that can be handled by the bash script.
export COMP_WORDS=(${commandToComplete})

# The cursor is at the end of parameter #1.
# We must check for a space as the last character which will
# tell us that the previous word is complete and the cursor
# is on the next word.
if [ "${commandToComplete: -1}" == " " ]; then
	# The last character is a space, so our location is at the end
	# of the command-line array
	COMP_CWORD=${#COMP_WORDS[@]}
else
	# The last character is not a space, so our location is on the
	# last word of the command-line array, so we must decrement the
	# count by 1
	COMP_CWORD=$((${#COMP_WORDS[@]}-1))
fi
# Call the completion command in the real bash script
if [ "${1}" == "freva" ] && [ "${COMP_WORDS[1]}" == "databrowser" ];then
    COMPREPLY=$(__databrowser 2)
elif [ "${1}" == "freva-databrowser" ];then
    COMPREPLY=$(__databrowser 1)
elif [ "${1}" == "freva" ] && [ "${COMP_WORDS[1]}" == "plugin" ];then
    COMPREPLY=$(__plugin 2)
elif [ "${1}" == "freva-plugin" ];then
    COMPREPLY=$(__plugin 1)
else
    COMPREPLY=$(python -m freva.cli --shell bash --flags-only ${COMP_WORDS[@]})
fi

if [ "${debug}" == "true" ]; then
    echo =====================================
    echo $0 returned:
    echo "${COMPREPLY[@]}"
fi

IFS=$'\n'
if [ ${#COMPREPLY[*]} -eq 0 ]; then
	# No completions suggested.  In this case, we want tcsh to perform
	# standard file completion.  However, there does not seem to be way
	# to tell tcsh to do that.  To help the user, we try to simulate
	# file completion directly in this script.
	#
	# Known issues:
	#     - Possible completions are shown with their directory prefix.
	#     - Completions containing shell variables are not handled.
	#     - Completions with ~ as the first character are not handled.

	# No file completion should be done unless we are completing beyond
	# the first sub-command.
    # WARNING: This seems like a good idea for the commands I have been
    #          using, however, I may have not noticed issues with other
    #          commands.
	if [ ${COMP_CWORD} -gt 1 ]; then
		TO_COMPLETE="${COMP_WORDS[${COMP_CWORD}]}"

		# We don't support ~ expansion: too tricky.
		if [ "${TO_COMPLETE:0:1}" != "~" ]; then
			# Use ls so as to add the '/' at the end of directories.
			COMPREPLY=(`ls -dp ${TO_COMPLETE}* 2> /dev/null`)
		fi
	fi
fi

if [ "${debug}" == "true" ]; then
    echo =====================================
    echo Completions including tcsh additions:
    echo "${COMPREPLY[@]}"
    echo =====================================
    echo Final completions returned:
fi
# tcsh does not automatically remove duplicates, so we do it ourselves
echo "${COMPREPLY[*]}" | sort | uniq

# If there is a single completion and it is a directory, we output it
# a second time to trick tcsh into not adding a space after it.
if [ ${#COMPREPLY[*]} -eq 1 ] && [ "${COMPREPLY[0]: -1}" == "/" ]; then
    echo "${COMPREPLY[*]}"
fi
