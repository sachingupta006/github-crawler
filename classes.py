# Stores information about a User(other than the one being crawled)
class otherUser(object):

    def __init__(self,name=None,link=None):

        self.name = name
        self.link = link
        self.followers = 0
        self.own_repos = []
        self.forked_repos = []
        self.impact_value = 0

# Stores information about a repository
class ownRepository(object):
    
    def __init__(self,name=None,link=None,repo_type=None,lang=None):

        self.name = name 
        self.type = repo_type
        self.lang = lang 
        self.link = link
        self.forks = []
        self.watchers = 0
        self.own_commits = []
        self.other_commits = []
        self.activity = 0
        self.ownLinesOfCode = 0
        self.otherLinesOfCode = 0

# Stores information about a repository
class forkRepository(object):
    
    def __init__(self,name=None,link=None,repo_type=None,lang=None,forked_from=None):

        self.name = name 
        self.link = link

        # name of the person whose repository is forked
        self.owner = None
        # link of original repo
        self.forked_from = forked_from

        self.type = repo_type
        self.lang = lang 

        # if a forked repository is forked
        # the fork is attributed to the original repo
        # same is with watchers
        self.forks = []
        self.watchers = 0
    
        # the commits here refer to pull requests that have been acceppted
        # by the owner in his own repository
        self.own_commits = []
        self.other_commits = []
        self.activity = 0
        self.ownLinesOfCode = 0
        self.otherLinesOfCode = 0

        # the person may not give any pull requests and develope the 
        # repository natively
        self.selfLinesOfCode = 0

