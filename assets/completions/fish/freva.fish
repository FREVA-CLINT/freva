
function __fish_default_complete
    set -l cmd $argv[1]
    set -l keywords_only $argv[2]
    for sub_str in (python -m freva.cli --shell fish freva $cmd)
        set -l sub_cmd (echo $sub_str|cut -d ':' -f1)
        set -l sub_h (echo $sub_str|sed "s/$sub_cmd: //")
        if [ $keywords_only = 0 ] || [ (echo $sub_cmd|cut -c1) = "-" ]
            complete -f -c freva -n "__fish_seen_subcommand_from $cmd" -a $sub_cmd -d "$sub_h"
            complete -f -c freva-$cmd -n "not __fish_seen_subcommand_from freva-$cmd" -a $sub_cmd -d "$sub_h"
        end
    end
end

function __fish_facet_in_cmd -d "Check if facet name is already in command line"
    set -l tokens (commandline -opc) (commandline -ct)
    if [ (count $tokens) -lt 3 ]
        echo 1
        return
    end
    set -l c (count $tokens)
    for i in (seq 2 (math $c - 1))
        if [ ! (echo $tokens[$i]|cut -c1) = '-' ]
            set -l key (echo $tokens[$i]|cut -d = -f1)
            if [ $key = $argv[1] ]
                echo 0
                return
            end
        end
    end
    echo 1
end


function __fish_complete_databrowser -d "Completion for databrowser"

    set -l tokens (commandline -opc) (commandline -ct)
    set -l search_keys
    set -l keys
    for entry in $tokens
        if [ (__fish_string_in_list $entry freva databrowser freva-databrowser) = 0 ]
            if [ -z "$search_keys" ]
                set search_keys $entry
            else
                set -l num (count $search_keys)
                set search_keys[(math $num+1)] $entry
            end
        end
    end
    set -l facets (python -m freva.cli --shell fish --strip freva databrowser $search_keys)
    for line in $facets
        set -l facet (echo $line|cut -d : -f1)
        set -l entries (echo $line|cut -d : -f2 |awk '{print $NF}'|sed 's/,/\n/g')
        if [ (count $entries) -ge 1 ] && [ (__fish_facet_in_cmd $facet) = 1 ]
            for e in $entries
                if [ -z "$keys" ]
                    set keys "$facet=$e"
                else
                    set -l num (count $keys)
                    set keys[(math $num+1)] $facet=$e
                end
                echo "$facet=$e"
            end
        end
    end
end

function __fish_string_in_list -d "Check if a string is in a list"
    set -l target $argv[1]
    set -l list $argv[2..-1]
    for cmd in $list
        if [ $cmd = $target ]
            echo 1
            return
        end
    end
    echo 0
    return
end

function __fish_complete_plugin -d "Completion definition for the freva plugin command"

    set -l tokens (commandline -opc) (commandline -ct)
    set -l search_keys
    set -l keys cmd_args
    for entry in $tokens
        if [ (__fish_string_in_list $entry freva plugin freva-plugin) = 0 ]
            set -l num (count $search_keys)
            set search_keys[(math $num+1)] $entry
            if [ ! (echo $entry |cut -c1) = "-" ]
                set -l num (count $cmd_args)
                set cmd_args[(math $num+1)] $entry
            end
        end
    end
    set -l options (python -m freva.cli --strip freva plugin $search_keys)
    for option in $options
        if [ (__fish_facet_in_cmd $option) = 1 ]
            set -l num (count $keys)
            if [ -z "$cmd_args" ]
                set keys[(math $num+1)] $option
                echo "$option"
            else
                set keys[(math $num+1)] $option=
                echo "$option="
            end
        end
    end
end

set -l freva_str (python -m freva.cli --shell fish freva)
set -l cmds help
for i in (seq (count $freva_str))
    set -l cmd (echo $freva_str[$i]|cut -d ':' -f1)
    set -l h (echo $freva_str[$i]|sed "s/$cmd: //")
    set cmds[$i] $cmd
    set help[$i] $h
end
for i in (seq (count $freva_str))
    set -l cmd $cmds[$i]
    set -l h $help[$i]
    complete -f -c freva -n "not __fish_seen_subcommand_from $cmds" -a $cmd -d "$h"
    if [ $cmd = "databrowser" ]
        #__fish_default_complete $cmd 1
        complete -f -c freva -n "__fish_seen_subcommand_from $cmd" -a "(__fish_complete_databrowser)"
        complete -f -c freva-$cmd -n "not __fish_seen_subcommand_from freva-$cmd" -a "(__fish_complete_databrowser)"
    else if [ $cmd = "plugin" ]
        __fish_default_complete $cmd 1
        complete -f -c freva -n "__fish_seen_subcommand_from $cmd" -a "(__fish_complete_plugin)"
        complete -f -c freva-$cmd -n "not __fish_seen_subcommand_from freva-$cmd" -a "(__fish_complete_plugin)"
    else
        __fish_default_complete $cmd 0
    end
end


