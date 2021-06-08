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

function __fish_facet_search
    sh -c "freva --databrowser --all-facets --relevant-only $argv"
end

function __fish_complete_solr -d "Completion for the databrowser command"
    set -l tokens (commandline -opc) (commandline -ct)
    set -l search_keys
    set -l keys
    for entry in $tokens[2..-2]
        if [ ! (echo $entry|cut -c1) = '-' ]
            if [ -z $search_keys ]
                set search_keys $entry
            else
                set search_keys (string join " " $search_keys $entry)
            end
        end
    end
    set -l facets (__fish_facet_search $search_keys)
    for line in $facets
        set -l facet (echo $line|cut -d : -f1)
        set -l entries (echo $line|cut -d : -f2 |awk '{print $NF}'|sed 's/,/\n/g')
        if [ (count $entries) -ge 2 ] && [ (__fish_facet_in_cmd $facet) = 1 ]
            for e in $entries
                if [ -z $keys ]
                    set keys "$facet=$e"
                else
                    set search_keys (string join " " $keys "$facet=$e")
                end
                echo "$facet=$e"
            end
        end
    end
    #set l index (contains -i (commandline -opc))
    #set -l facets=(${(f)"$(freva --databrowser --all-facets ${search_keys[@]})"})
end

set -l freva_commands  "--help --plugin --history --databrowser --crawl_my_data --esgf -h"
# Add the basic freva commands with thier help messages
complete -f -c freva -n "not __fish_seen_subcommand_from $freva_commands" -s h -l help -d 'Display help message'
complete -f -c freva -n "not __fish_seen_subcommand_from $freva_commands" -l plugin -d 'Applies some analysis to the given data.'
complete -f -c freva -n "not __fish_seen_subcommand_from $freva_commands" -l history -d 'Provides access to the configuration history (use --help for more help).'
complete -f -c freva -n "not __fish_seen_subcommand_from $freva_commands" -l databrowser -d 'Find data in the system.'
complete -f -c freva -n "not __fish_seen_subcommand_from $freva_commands" -l crawl_my_data -d 'Use this command to update your projectdata.'
complete -f -c freva -n "not __fish_seen_subcommand_from $freva_commands" -l esgf -d 'Browse ESGF data and create wget scripts.'

# Add the help messages for the plugin command
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l debug -s d -d 'Turn on debugging info and show stack trace on exceptions.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l help -s h -d 'Display help message.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l repos-version -d 'show the version number from the repository'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l caption -d 'sets a caption for the results'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l save -d 'saves the configuration locally for this user.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l save-config= -d 'saves the configuration at the given file path'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l show-config -d 'shows the resulting configuration (implies dry-run).'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l scheduled-id= -d 'Runs a scheduled job from database'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l dry-run -d 'dry-run, perform no computation.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l batchmode -d 'creates a SLURM job'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l unique_output -d 'If true append the freva run id to every output folder'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l pull-request -d 'issue a new pull request for the tool'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l tag= -d 'The git tag to pull'
# complete -f -c aws-okta -n "__fish_seen_subcommand_from exec; and not __fish_seen_subcommand_from (__fish_okta_complete_profiles)" -a "(__fish_okta_complete_profiles)"

# Add the help message for the hitsory command
complete -f -c freva -n "__fish_seen_subcommand_from --history" -l debug -s d -d 'Turn on debugging info and show stack trace on exceptions.'
complete -f -c freva -n "__fish_seen_subcommand_from --hisotry" -l help -s h -d 'Display help message.'
complete -f -c freva -n "__fish_seen_subcommand_from --history" -l full_text -d 'If present shows the complete configuration stored'
complete -f -c freva -n "__fish_seen_subcommand_from --history" -l return_command -d 'Show freva commands belonging to the history entries'
complete -f -c freva -n "__fish_seen_subcommand_from --history" -l limit= -d 'display n entries'
complete -f -c freva -n "__fish_seen_subcommand_from --history" -l plugin= -d 'isplay only entries from plugin "name"'
complete -f -c freva -n "__fish_seen_subcommand_from --history" -l since= -d 'Retrieve entries older than date (see DATE FORMAT)'
complete -f -c freva -n "__fish_seen_subcommand_from --history" -l unitl= -d 'Retrieve entries newer than date (see DATE FORMAT)'
complete -f -c freva -n "__fish_seen_subcommand_from --history" -l entry_id= -d 'Select entries whose ids are in "ids"'

# Add the help message for the crawl_my_data command
complete -f -c freva -n "__fish_seen_subcommand_from --crawl_my_data" -l debug -s d -d 'Turn on debugging info and show stack trace on exceptions.'
complete -f -c freva -n "__fish_seen_subcommand_from --crawl_my_data" -l help -s h -d 'Display help message.'
complete -f -c freva -n "__fish_seen_subcommand_from --crawl_my_data" -l path= -d 'crawl the given directory'
#complete -f -c freva -n "__fish_seen_subcommand_from --crawl_my_data; and not __fish_seen_subcommand_from $freva_commands" -e


# Add the help message for esgf command
complete -f -c freva -n "__fish_seen_subcommand_from --esgf" -l debug -s d -d 'Turn on debugging info and show stack trace on exceptions.'
complete -f -c freva -n "__fish_seen_subcommand_from --esgf" -l help -s h -d 'Display help message.'
complete -f -c freva -n "__fish_seen_subcommand_from --esgf" -l datasets -d 'List the name of the datasets instead of showing the urls.'
complete -f -c freva -n "__fish_seen_subcommand_from --esgf" -l show-facet -d 'List all values for the given facet'
complete -f -c freva -n "__fish_seen_subcommand_from --esgf" -l opendap -d 'List the name of the datasets instead of showing the urls.'
complete -f -c freva -n "__fish_seen_subcommand_from --esgf" -l gridftp -d 'Show Opendap endpoints instead of the http default'
complete -f -c freva -n "__fish_seen_subcommand_from --esgf" -l download-script= -d 'Download wget_script for getting the files'
complete -f -c freva -n "__fish_seen_subcommand_from --esgf" -l query= -d '<list> Display results from <list> queried fields'

# Add the help message for the databrowser command
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -l debug -s d -d 'Turn on debugging info and show stack trace on exceptions.'
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -l help -s h -d 'Display help message.'
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -l multiversion -d 'select not only the latest version but all of them'
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -l relevant-only -d 'how only facets that filter results'
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -l batch-size= -d 'Number of files to retrieve'
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -l count-facet-values -d 'Show the number of files for each values in each facet'
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -l attributes -d 'retrieve all possible attributes for the current search'
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -l all-facets -d 'retrieve all facets (attributes & values)'
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -l fracet= -d 'retrieve these facets (attributes & values)'
complete -f -c freva -n "__fish_seen_subcommand_from --databrowser" -a "(__fish_complete_solr)"
