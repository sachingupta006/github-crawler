import sys
import urllib2
import re
import urlparse
from collections import deque
linkregex = re.compile(r'<a.*?href=[\'|"]?(.*?)[\'|"]?\s*>', re.IGNORECASE)
search_depth = 5

class Crawler(object):

    def __init__(self, root, depth):

        self.root = root
        self.depth = depth
        self.host = urlparse.urlparse(self.root).netloc
        self.crawled = [self.root,]
        self.links = 0

    def crawl(self):

        page = GetLinks(self.root)
        page.get()
        parentQ = deque()
        childQ = deque()
        print(self.root + "\n" )

        for url in page.urls:
            parentQ.append(url)
            self.links+=1

        level = 0

        while parentQ:

            try:
                url = parentQ.popleft()
            except:

                level+=1
                print("\n")
                if level == self.depth:
                    break
                else:
                    parentQ = childQ
                    del childQ[:] 
                    continue

            if url not in self.crawled:

                try:
                    # extract the host out of the new url
                    host = urlparse.urlparse(url).netloc
                    # if it matches with the current root .* includes any subdomains
                    if re.match(".*%s" % self.host, host):

                        self.links+=1
                        print(url) 
                        self.crawled.append(url)
                        page = GetLinks(url)
                        page.get()
                        for new_url in page.urls:
                            if new_url not in self.crawled:
                                childQ.append(url)

                except Exception, e:
                    print "ERROR: Can't process url '%s' (%s)" % (url, e)
                    
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
        links = linkregex.findall(page)
        for link in links:
            if link.startswith('/'):
                link = 'http://' + url.netloc + link
            elif link.startswith('#'):
                if link == '#':
                    links.remove(link)
                    continue
                else:
                    link = 'http://' + url.netloc + url.path
            elif not link.startswith('http'):
                link = 'http://' + url[1] + '/' + link

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
    print "\n Total links found " + crawler.links
    print "\n Total links crawled " + len(crawler.crawled)


if __name__ == "__main__":
    main()



