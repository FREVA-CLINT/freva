set -l freva_commands  "help plugin history databrowser crawl_my_data esgf"
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
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l debug -s d -d 'Turn on debugging info and show stack trace on exceptions.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l help -s h -d 'Display help message.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l full_text -d 'If present shows the complete configuration stored'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l return_command -d 'Show freva commands belonging to the history entries'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l limit= -d 'display n entries'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l plugin= -d 'isplay only entries from plugin "name"'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l since= -d 'Retrieve entries older than date (see DATE FORMAT)'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l unitl= -d 'Retrieve entries newer than date (see DATE FORMAT)'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l entry_id= -d 'Select entries whose ids are in "ids"'

# Add the help message for the crawl_my_data command
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l debug -s d -d 'Turn on debugging info and show stack trace on exceptions.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l help -s h -d 'Display help message.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l path -d 'crawl the given directory'

# Add the help message for esgf command
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l debug -s d -d 'Turn on debugging info and show stack trace on exceptions.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l help -s h -d 'Display help message.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l datasets -d 'List the name of the datasets instead of showing the urls.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l show-facet -d 'List all values for the given facet'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l opendap -d 'List the name of the datasets instead of showing the urls.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l gridftp -d 'Show Opendap endpoints instead of the http default'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l download-script= -d 'Download wget_script for getting the files'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l query= -d '<list> Display results from <list> queried fields'

# Add the help message for the databrowser command
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l debug -s d -d 'Turn on debugging info and show stack trace on exceptions.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l help -s h -d 'Display help message.'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l multiversion -d 'select not only the latest version but all of them'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l relevant-only -d 'how only facets that filter results'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l batch-size= -d 'Number of files to retrieve'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l count-facet-values -d 'Show the number of files for each values in each facet'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l attributes -d 'retrieve all possible attributes for the current search'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l all-facets -d 'retrieve all facets (attributes & values)'
complete -f -c freva -n "__fish_seen_subcommand_from --plugin" -l fracet= -d 'retrieve these facets (attributes & values)'

