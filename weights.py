# Different weights that are to be assigned
# These weights are to be used when calculating the statitics of 
# the user who is being crawled
follower_weight = 1
forker_with_commit = 1
forker_without_commit = 1
watcher_weight = 1
weight_for_code = 1/100
weight_for_others_code = 1/10

# weight assigned to the owner whose repository is forked and
# a pull request is accepted
fork_with_commit_owner = 1
fork_with_commit_code = 1/10

# weight to be assigned to the lines of code that a user has written to a repository
# that he has forked but editing for his/her own purpose
fork_without_commit_code = 1/10

forked_repo_watcher_weight = 1
forked_repo_forker_wight = 1
forked_repo_lines_of_code = 1/100

