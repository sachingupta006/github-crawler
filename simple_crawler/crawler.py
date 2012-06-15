import sys
import urllib2
import re
import urlparse
from collections import deque

# This regex is not complete, so using Beautiful Soup to extract links from web page
linkregex = re.compile(r'<a.*?href=[\'|"]?(.*?)[\'|"]?\s*>', re.IGNORECASE)

# Goes to a depth 5 for the input url
search_depth = 1

from BeautifulSoup import BeautifulSoup

class Crawler(object):

    def __init__(self, root, depth):

        self.root = root
        self.depth = depth
        self.host = urlparse.urlparse(self.root).netloc
        self.crawled = []
        self.links = 1 #including the root url
        self.externalLinks = []
        self.uncrawled = []

    def crawl(self):

        page = GetLinks(self.root)
        page.get()
        parentQ = deque()
        childQ = deque()

        parentQ.append(self.root)
        level = 0

        while True:

            try:
                url = parentQ.popleft()
            except:
                level+=1
                print("\n")
                if level == self.depth:
                    break

                else:

                    # transfer all urls from the child queue to the parent queue
                    while childQ:
                        url = childQ.popleft()
                        parentQ.append(url)
                        
                    
                    # break if the queue is empty
                    if not parentQ:
                        print "No more links found"
                        print "Finishing...."
                        break
                    else:
                        continue

            if url not in self.crawled:

                try:
                    
                    # extract the host out of the new url
                    host = urlparse.urlparse(url).netloc
                    # if it matches with the current root .* includes any subdomains
                    if re.match(".*%s" % self.host, host):

                        print "crawling: " + url
                        self.links+=1
                        self.crawled.append(url)
                        page = GetLinks(url)
                        page.get()
                        for new_url in page.urls:
                            if new_url not in self.crawled:
                                childQ.append(new_url)
                    else:
                        self.externalLinks.append(url)

                except Exception, e:
                    print "ERROR: Can't process url '%s' (%s)" % (url, e)
        
        while childQ:
            link = childQ.popleft()
            self.uncrawled.append(link)
                    
class GetLinks(object):

    def __init__(self,url):
        self.url = url
        self.urls = []

    def get(self):
    
        # Fetch the page contents
        url = urlparse.urlparse(self.url)
        request = urllib2.Request(self.url)
        response = urllib2.urlopen(request)
        page = response.read()
        
        # Extract urls from the page
        # links = linkregex.findall(page)
        # can't use regex here, some problems with that using beautiful soup
        soup = BeautifulSoup(page)
        tags = soup('a')
        for tag in tags:
            link = tag.get("href")
            if link.startswith('/'):
                link = url.scheme + '://' + url.netloc + link
            elif link.startswith('#'):
                if link == '#':
                    tags.remove(tag)
                    continue
                else:
                    link = url.scheme + '://' + url.netloc + url.path
            elif not link.startswith('http'):
                link = 'http://' + url[1] + '/' + link
            
            # specific to mycareerstack.com
            # remove this
            if not "accounts" in link:    
                self.urls.append(link)

def main():

    if len(sys.argv) < 2:
        print 'No start url was given'
        sys.exit()

    url = sys.argv[1]
    print "Crawling %s (Max Depth: %d)" % (url, search_depth)
    crawler = Crawler(url,search_depth)
    crawler.crawl()
    print "Total internal links found " + str(crawler.links)
    print "Total links crawled " + str(len(crawler.crawled))

    print "\nUncrawled links "
    print "\n".join(crawler.uncrawled)

    print "\nExternal links:"
    print "\n".join(crawler.externalLinks)

if __name__ == "__main__":
    main()



