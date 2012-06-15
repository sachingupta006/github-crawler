from __future__ import division
import sys
import logging
logging.basicConfig(filename='crawler.log', level=logging.DEBUG)
import urllib2
import urlparse
from collections import deque
from lxml.html import parse
from BeautifulSoup import BeautifulSoup
import iso8601

from locale import *
setlocale(LC_NUMERIC, '')

from weights import *
from utils import *
from classes import ownRepository, forkRepository 

# This will contain other objects that will be used to 
# calculate the statistics of a user
UserRepo = {}

# An object of this class is instantiated whenever a user is to be crawled
class Crawler(object):

    def __init__(self, username):

        self.username = username
        self.domain = "https://github.com/"
        self.root = urlparse.urljoin(self.domain, self.username)
        print self.root
        self.skills = set([])
        self.own_repo = []
        self.forked_repo = []
        self.followers = []
        self.stat = 0

    # Once a cralwer object is instantiated, this function is called from main
    def crawl(self):

        print "\nGetting the repositories"
        self.getRepositories()
        print "\nGetting the followers"
        self.getFollowers()
        print "\nGetting own repo info"
        self.getOwnRepoInfo()
        print "\nGetting forked repo info"
        self.getForkRepoInfo()
        print "\nPrinting follower stats"
        self.calculateFollowerStats()
        print "\nCalculating repo stats"
        self.calculateRepoStats()

    # makes a list of all the repositories in the user's profile   
    def getRepositories(self):

        url = self.root + '/repositories'
        soup = soup_from_url(url)

        try:

            own_repos = soup.findAll('li',{"class":"simple public source"})
            fork_repos = soup.findAll('li',{"class":"simple public fork"})
            
            for r in own_repos:
                
                repo_type = "own"
                lang = r.find('li').string
                a_link = r.find('h3').find('a')
                name = a_link.string
                link = urlparse.urljoin(self.domain, a_link['href'])
                repo = ownRepository(name,link,repo_type,lang)
                self.skills.add(lang)
                self.own_repo.append(repo)

            for r in fork_repos:
                
                repo_type = "fork"
                # language of the repository
                lang = r.find('li').string
                # link of he forked repository
                a_link = r.find('h3').find('a')
                name = a_link.string
                link = urlparse.urljoin(self.domain, a_link['href'])
                # link of the repository from where it is forked
                forked_from = r.find('p', {"class":"fork-flag"}).find('a')['href']
                forked_from = urlparse.urljoin(self.domain, forked_from)
                # create an object of the repository
                repo = forkRepository(name,link,repo_type,lang,forked_from)
                self.skills.add(lang)
                self.forked_repo.append(repo)

        except AttributeError:
            print "User does not have any repository"
   
    # Makes a list of followers
    def getFollowers(self):
       
        url = self.root + '/followers'
        soup = soup_from_url(url)

        try:
            followers = soup.find(id="watchers").findAll('li')
            for f in followers:
                link = f.findAll('a')[1]
                name = link.string
                url = urlparse.urljoin(self.domain,link['href'])
                follower = {'name':name, 'url':url}
                self.followers.append(follower)

        except AttributeError:
            print "User does not have any followers"

    # collect statistics of a repository that is user's own repository
    def getOwnRepoInfo(self):

        # collect stats from the users own repo
        # TODO do we have to give any weightage to the fact that other users have contributed 
        # to this repository
        for r in self.own_repo:

            doc = doc_from_url(r.link)

            # TODO  Do we need to see who all are watching or just the number would suffice
            watchers = doc.cssselect('li.watchers a')[0].text_content().strip()
            r.watchers = int(watchers)
            
            # have to get the name of all those who have forked this repository
            # link is of type <username>/<repo-name>/network/
            fork_link = doc.cssselect('li.forks a')[0].get('href')
            # members needs to be appended to get to the actual page that contains the forkers
            fork_link = fork_link +"/members"
            fork_link = urlparse.urljoin(self.domain,fork_link)
            fork_page = urllib2.urlopen(fork_link)
            fork_doc = parse(fork_page).getroot()
            
            # Get the name and link of each forker
            forkers = fork_doc.xpath(forker_xpath)
            for fork in forkers:
                name = fork.text_content()
                link = urlparse.urljoin(self.domain, name)
                # if a forker has also commited then higher weigthage needs to be given
                name_and_link = {'name':name, 'url':link, 'hasCommitted': False}
                r.forks.append(name_and_link) 
                
            clone_doc = doc_from_url(r.link + clone_link)
            clone_text = clone_doc.cssselect("div#path")[0].text_content().split()

            # The first number is the number of clones over the last 4 weeks
            # TODO save this count for the forked repository as well
            for string in clone_text:
                try:
                    a = atoi(string)
                    self.clones = a
                    break
                except Exception:
                    pass

            # word history is a bit misleading contains the link as /<repo-name>/commits/master/
            try:
                history = doc.cssselect('div.history a')[0].get('href')
            except IndexError:
                print "Repository ("+r.name+") is empty"

            # goes to the commit page, and extracts info about each commit
            history = urlparse.urljoin(self.root,history)

            page_value = 0

            while(True):

                page_value += 1
                page_number = '?page='+str(page_value)
                history_url = urlparse.urljoin(history,page_number)

                try:
                    history_doc = doc_from_url(history_url)                  
                    commits = history_doc.cssselect('li.commit-group-item')

                    for commit in commits:

                        # this link contains the user name as well
                        a = commit.cssselect('a.message')[0].get('href')
                        # just append the github domain in the beginning
                        a = urlparse.urljoin(self.domain,a)

                        # Calculate the number of lines of code
                        commit_doc = doc_from_url(a)

                        # Find out the number of parents of this commit, if there are 2, then this is a merge
                        # commit and we do not have to attribute to the repository author
                        parents = int(commit_doc.cssselect('span.sha-block')[1].text_content().split()[0])

                        # this commit has only parent and hence is not a merge commit
                        if parents <= 1:

                            time = commit_doc.cssselect('time')[0].get('datetime')
                            authors = commit_doc.cssselect('span.author-name')
                                                    
                            name = "" 

                            # can the length be greater than 2 in any case
                            if len(authors) > 1:

                                # This should not happend, a commit cannot have more than 1 author
                                if len(authors) > 2:
                                    logging.warning('Repository ' + r.name + ' has a commit with sha ' \
                                            + commit_doc.cssselect('span.sha').text_content() + ' which has more than 2 authors')

                                commiter = commit_doc.cssselect('span.committer span.author-name')

                                if len(commiter) == 1:
                                    commiter_name = commiter[0].text_content().strip()
                                
                                    for author in authors:
                                        author_name = author.text_content().strip()
                                        if not author_name == commiter_name:
                                            name = author_name 
                                else:
                                    logging.warning('Repository ' + r.name + ' has a commit with sha ' \
                                            + commit_doc.cssselect('span.sha').text_content() + ' which has more than 2 authors and no commiter')

                            else:
                                name = authors[0].text_content().strip()

                            data = {'link':a, 'time':time, 'author':name }
                                
                            # this p element contains the text where the info about the commit is written
                            commit_info = commit_doc.cssselect('p.explain')[0].text_content()
                            numbers = []
                            # it contains 3 numbers
                            # 1 - number of files changed
                            # 2 - number of lines added
                            # 3 - number of lines deleted
                            for string in commit_info.split():
                                try:
                                    a = atoi(string)
                                    numbers.append(a)
                                except Exception:
                                    pass

                            additions = numbers[1]
                            deletions = numbers[2]
                            data['additions'] = additions
                            data['deletions'] = deletions

                            # This is user's own commit
                            if name == self.username:

                                # Update the lines of code by the user for that repo
                                r.ownLinesOfCode += additions
                                r.ownLinesOfCode -= deletions
                              
                                # add this commit as own commit
                                r.own_commits.append(data)

                            # somebody else has committed
                            else:
                                
                                # TODO look for some better method of finding whether a user 
                                # TODO hasCommitted flag is set or not

                                # If this author has also forked the repository 
                                # then store this info, it will be used in assigning weight
                                # to the forker
                                for forker in r.forks:
                                    if forker['name'] == name:
                                        forker['hasCommitted'] = True
                                        break
                                
                                r.otherLinesOfCode += additions
                                r.otherLinesOfCode -= deletions
                                r.other_commits.append(data)

                 
                except Exception:
                    break
                     
            # TODO see why is this not working        
            try:

                start_date = iso8601.parse_date(r.own_commits[-1]['time'])
                end_date =  iso8601.parse_date(r.own_commits[0]['time'])
                diff = start_date - end_date
                self.activity = diff.days

            except Exception:
                pass

    # collect statistics of a repository that a user has forked from somehwher
    def getForkRepoInfo(self):
       
        for r in self.forked_repo:
            
            print "\n"
            # first we will collect information from the repository
            # which the user has forked, this info is useful only
            # if the pull requests have been accepted by the owner
            
            # set hasCommitted to True if the user does a commit 
            # to this repository
            contributor_doc = doc_from_url(r.forked_from + contributor_link)
            contributor_element = contributor_doc.cssselect('ul.members li')

            hasCommitted = False
            for contributor in contributor_element:
                name = contributor.cssselect('a')[1].text_content()
                r.contributors.append(name)
                if name == self.username:
                    hasCommitted = True

            #### If the user has committed then we need to find out those commits which the user
            #### has done and calcualte the number of lines of code and other statistics of the repo

            if hasCommitted:

                doc = doc_from_url(r.forked_from)

                # word history is a bit misleading contains the link as /<repo-name>/commits/master/
                history = doc.cssselect('div.history a')[0].get('href')

                # goes to the commit page, and extracts info about each commit
                history = urlparse.urljoin(self.root,history)

                page_value = 0

                while(True):

                    page_value += 1
                    page_number = '?page='+str(page_value)
                    history_url = urlparse.urljoin(history,page_number)

                    try:
                        history_doc = doc_from_url(history_url)                  
                        commits = history_doc.cssselect('li.commit-group-item')

                        for commit in commits:

                            authors = commit.cssselect('span.author-name')
                            name = "" 

                            # can the length be greater than 2 in any case
                            if len(authors) > 1:

                                # This should not happend, a commit cannot have more than 1 author
                                if len(authors) > 2:
                                    logging.warning('Repository ' + r.name + ' has a commit with sha ' \
                                            + commit.cssselect('span.sha').text_content() + ' which has more than 2 authors')

                                commiter = commit.cssselect('span.committer span.author-name')

                                if len(commiter) == 1:
                                    commiter_name = commiter[0].text_content().strip()
                                
                                    for author in authors:
                                        author_name = author.text_content().strip()
                                        if not author_name == commiter_name:
                                            name = author_name 
                                else:
                                    logging.warning('Repository ' + r.name + ' has a commit with sha ' \
                                            + commit.cssselect('span.sha').text_content() + ' which has more than 2 authors and no commiter')

                            else:
                                name = authors[0].text_content().strip()
                            
                            # The name of the committer is the same as that of the 
                            if name == self.username:

                                # this link contains the user name as well
                                a = commit.cssselect('a.message')[0].get('href')
                                # just append the github domain in the beginning
                                a = urlparse.urljoin(self.domain,a)

                                # Calculate the number of lines of code
                                commit_doc = doc_from_url(a)

                                time = commit_doc.cssselect('time')[0].get('datetime')
                                
                                data = {'link':a, 'time':time, 'author':name }
                                    
                                # this p element contains the text where the info about the commit is written
                                commit_info = commit_doc.cssselect('p.explain')[0].text_content()

                                numbers = []
                                # it contains 3 numbers
                                # 1 - number of files changed
                                # 2 - number of lines added
                                # 3 - number of lines deleted
                                for string in commit_info.split():
                                    try:
                                        a = atoi(string)
                                        numbers.append(a)
                                    except Exception:
                                        pass

                                additions = numbers[1]
                                deletions = numbers[2]
                                data['additions'] = additions
                                data['deletions'] = deletions

                                # Update the lines of code by the user for that repo
                                r.ownLinesOfCode += additions
                                r.ownLinesOfCode -= deletions

                                # add this commit as own commit
                                r.own_commits.append(data)

                    except Exception:
                        #print Exception
                        break
                
                # if the user has committed then other contents of the repository are
                # of use to us, need to decide if we need to maintain a list of all the forkers
               
                # find out the owner of the repository that has been forked
                owner = doc.cssselect('div.title-actions-bar span')[0].text_content().strip()
                r.owner = owner

                # TODO  Do we need to see who all are watching or just the number would suffice
                watchers = doc.cssselect('li.watchers a')[0].text_content().strip()
                r.watchers = int(watchers)
               
                # TODO do we need to get all the names or just the number would be sufficient
                # link is of type <username>/<repo-name>/network/
                fork_link = doc.cssselect('li.forks a')[0].get('href')
                # members needs to be appended to get to the actual page that contains the forkers
                fork_link = fork_link +"/members"
                fork_link = urlparse.urljoin(self.domain,fork_link)
                fork_page = urllib2.urlopen(fork_link)
                fork_doc = parse(fork_page).getroot()
                
                # Get the name and link of each forker
                forkers = fork_doc.xpath(forker_xpath)
                for fork in forkers:
                    name = fork.text_content()
                    link = urlparse.urljoin(self.domain, name)
                    # if a forker has also commited then higher weigthage needs to be given
                    name_and_link = {'name':name, 'url':link, 'hasCommitted': False}
                    r.forks.append(name_and_link) 

            else:
                print "User has not committed to the forked repository"

            ###############################################################################################

            # Now we will collect info from the repository that is in the users
            # a/c, it may contain some work that the user either did request to be pulled
            # or was not acceppted, but since some work has been done some weight should be attributed

            contributor_doc = doc_from_url(r.link + contributor_link)
            contributor_element = contributor_doc.cssselect('ul.members li')

            hasCommitted = False
            for contributor in contributor_element:
                name = contributor.csseselect('a')[1].text_content()
                r.contributors.append(name)
                if name == self.username:
                    hasCommitted = True

            # TODO How to take into account those commits which have been both pulled and are in the local repository 
            # TODO as well. Is it worth so much of trouble?
            ## If the user has committed and these commits have not been pulled in the other repository then 
            if hasCommitted:

                clone_doc = doc_from_url(r.link + clone_link)
                clone_text = clone_doc.cssselect("div#path")[0].text_content().split()

                # The first number is the number of clones over the last 4 weeks
                # TODO save this count for the forked repository as well
                for string in clone_text:
                    try:
                        a = atoi(string)
                        self.clones = a
                        break
                    except Exception:
                        pass

                doc = doc_from_url(r.link)

                # word history is a bit misleading contains the link as /<repo-name>/commits/master/
                history = doc.cssselect('div.history a')[0].get('href')

                # goes to the commit page, and extracts info about each commit
                history = urlparse.urljoin(self.root,history)

                page_value = 0

                while(True):

                    page_value += 1
                    page_number = '?page='+str(page_value)
                    history_url = urlparse.urljoin(history,page_number)

                    try:
                        history_doc = doc_from_url(history_url)                  
                        commits = history_doc.cssselect('li.commit-group-item')

                        for commit in commits:

                            authors = commit.cssselect('span.author-name')
                            name = "" 

                            # can the length be greater than 2 in any case
                            if len(authors) > 1:

                                # This should not happend, a commit cannot have more than 1 author
                                if len(authors) > 2:
                                    logging.warning('Repository ' + r.name + ' has a commit with sha ' \
                                            + commit_doc.cssselect('span.sha').text_content() + ' which has more than 2 authors')

                                commiter = commit.cssselect('span.committer span.author-name')
                                if len(commiter) == 1:
                                    commiter_name = commiter[0].text_content().strip()
                                
                                    for author in authors:
                                        author_name = author.text_content().strip()
                                        if not author_name == commiter_name:
                                            name = author_name 
                                else:
                                    logging.warning('Repository ' + r.name + ' has a commit with sha ' \
                                            + commit_doc.cssselect('span.sha').text_content() + ' which has more than 2 authors and no commiter')

                            else:
                                name = authors[0].text_content().strip()
                            
                            # The name of the committer is the same as that of the 
                            if name == self.username:

                                # this link contains the user name as well
                                a = commit.cssselect('a.message')[0].get('href')
                                # just append the github domain in the beginning
                                a = urlparse.urljoin(self.domain,a)

                                # Calculate the number of lines of code
                                commit_doc = doc_from_url(a)

                                time = commit_doc.cssselect('time')[0].get('datetime')
                                
                                data = {'link':a, 'time':time, 'author':name }
                                    
                                # this p element contains the text where the info about the commit is written
                                commit_info = commit_doc.cssselect('p.explain')[0].text_content()

                                numbers = []
                                # it contains 3 numbers
                                # 1 - number of files changed
                                # 2 - number of lines added
                                # 3 - number of lines deleted
                                for string in commit_info.split():
                                    try:
                                        a = atoi(string)
                                        numbers.append(a)
                                    except Exception:
                                        pass

                                additions = numbers[1]
                                deletions = numbers[2]
                                data['additions'] = additions
                                data['deletions'] = deletions

                                # Update the lines of code for the user, that has written in the
                                # forked repository but not sent for pull request 
                                r.selfLinesOfCode += additions
                                r.selfLinesOfCode -= deletions

                    except Exception:
                        break

            else:
                print "User has not committed locally to the fork"

    # Calculate the follower stats
    def calculateFollowerStats(self):

        for follower in self.followers:
            name = follower['name']
            old_value = self.stat
            if name in UserRepo:
                self.stat += follower_weight * UserRepo[name].impact_value
            else:
                self.stat += follower_weight * getUserStats(follower,UserRepo)
            print name + " following you, added points: " + str(self.stat - old_value)

    def calculateRepoStats(self):
        
        # points for own repositories
        for r in self.own_repo: 

            print r.name 
            old_value = self.stat
            # points from the people who have forked 
            for forker in r.forks:

                name = forker['name']

                if name in UserRepo:
                    impact = UserRepo[name].impact_value
                else:
                    impact =  getUserStats(forker,UserRepo)
                
                if forker['hasCommitted']:
                    self.stat += impact * forker_with_commit
                else:
                    self.stat += impact * forker_without_commit
            
            # points from the watchers
            self.stat += r.watchers * watcher_weight

            # points from clones
            self.stat += r.clones * clone_weight

            # points from the number of lines of code
            self.stat += r.ownLinesOfCode * weight_for_code
            self.stat += r.otherLinesOfCode * weight_for_others_code
            print "Points added from repository("+r.name+"): " + str(self.stat - old_value)

        # points for forked repositories
        for r in self.forked_repo: 
            
            old_value = self.stat
            # link of the repository from where it is forked
            forked_from = r.forked_from

            # it means the user has contributed to the repository
            # we do not need to calculate the repo stats because they 
            # are already available in the repository object
            # however we need to calculate the stats for the person who owns the repo
            if r.ownLinesOfCode > 0:

                owner = r.owner
                owner_link = urlparse.urljoin(self.domain,owner)

                if owner in UserRepo:
                    self.stat += fork_with_commit_owner * UserRepo[name].impact_value
                else:
                    name_and_link = {'name':owner, 'url':owner_link}
                    self.stat += fork_with_commit_owner * getUserStats(name_and_link,UserRepo)
                
                # points awarded for the lines of code commited in others repository
                linesOfCode = totalLinesOfCode(forked_from)

                # points awarded due to the quality of the forked repo
                repo_points = forked_repo_watcher_weight* r.watchers + forked_repo_forker_wight*len(r.forks) + forked_repo_lines_of_code*linesOfCode
                
                # points awarded due to contribution to the repo
                code_points = fork_with_commit_code * r.ownLinesOfCode/linesOfCode 

                self.stat += code_points + repo_points

            # points awarded for lines of code written in forked repository that have not been pulled
            if r.selfLinesOfCode > 0:
                self.stat +=  fork_without_commit_code * r.selfLinesOfCode

            print "Points added from forked repository("+r.name+"): " + str(self.stat - old_value)

def main():

    if len(sys.argv) < 2:
        print 'No start url was given'
        sys.exit()

    url = sys.argv[1]
    print "Crawling the github profile  %s " % url
    crawler = Crawler(url)
    crawler.crawl()
    
    print "\nOwn repositories: " + str(len(crawler.own_repo))
    print "Forked repositories: " + str(len(crawler.forked_repo))
    print "Followers: " + str(len(crawler.followers))
    print "Skills: " + "\t".join(crawler.skills)

    print "\nStats about own repository"
    for repo in crawler.own_repo:
        print "Name: " + repo.name
        print "Language: " + repo.lang

        if repo.watchers > 0:
            print "Watchers: %d " % repo.watchers

        if len(repo.forks) > 0:
            print "Forks: %d " %  len(repo.forks)
    
        print "Self commits: %d" % len(repo.own_commits)
        print "Lines of Code: %d" % repo.ownLinesOfCode
        print "Activity: %d" % repo.activity

        print "\n"

    print "\nStats about forked repository"
    for repo in crawler.forked_repo:
        print "Name: " + repo.name
        print "Language: " + repo.lang
        print "Forks: " + str(len(repo.forks))

        print "Own commits: " + str(len(repo.own_commits))
        print "\n"

    
if __name__ == "__main__":
    main()
