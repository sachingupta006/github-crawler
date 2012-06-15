import urllib2
import urlparse
from lxml.html import parse
from BeautifulSoup import BeautifulSoup
from locale import *
setlocale(LC_NUMERIC, '')

# Returns a lxml document from a url
def doc_from_url(url,shouldPrint=True):

    if shouldPrint:
        print "fetching: "+ url
    page = urllib2.urlopen(url)
    doc = parse(page).getroot()
    return doc

# Returns a beautifulSoup element from a url
def soup_from_url(url,shouldPrint=True):

    if shouldPrint:
        print "fetching: " + url
    response = urllib2.urlopen(url)
    page = response.read()
    soup = BeautifulSoup(page)
    return soup

# takes url of a reository and returns the total lines of code
def totalLinesOfCode(url):

    linesOfCode = 0

    doc = doc_from_url(url)
    history = doc.cssselect('div.history a')[0].get('href')
    # goes to the commit page, and extracts info about each commit
    history = urlparse.urljoin(domain,history)

    page_value = 0

    while(True):

        page_value += 1
        page_number = '?page='+str(page_value)
        history_url = urlparse.urljoin(history,page_number)

        try:
            history_doc = doc_from_url(history_url)                  
            commits = history_doc.cssselect('li.commit-group-item')

            for commit in commits:

                a = commit.cssselect('a.message')[0].get('href')
                # just append the github domain in the beginning
                a = urlparse.urljoin(domain,a)

                # Calculate the number of lines of code
                commit_doc = doc_from_url(a)

                # Find out the number of parents of this commit, if there are 2, then this is a merge
                # commit and we do not have to attribute to the repository author
                parents = int(commit_doc.cssselect('span.sha-block')[1].text_content().split()[0])
                
                # this commit has only parent and hence is not a merge commit
                if parents == 1:

                    authors = commit_doc.cssselect('span.author-name')
                    
                    # can the length be greater than 2 in any case
                    if len(authors) <= 2:

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

                        linesOfCode += numbers[1]
                        linesOfCode -= numbers[2]

        except Exception:
            break

