# pipenv install

from curses import def_shell_mode
from token import EXACT_TOKEN_TYPES
import pandas as pd
import urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from anytree import Node, RenderTree, findall


def get_sitemap(url):
    """Scrapes an XML sitemap from the provided URL and returns XML source.

    Args:
        url (string): Fully qualified URL pointing to XML sitemap.

    Returns:
        xml (string): XML source of scraped sitemap.
    """

    response = urllib.request.urlopen(url)
    xml = BeautifulSoup(response, 
                         'lxml-xml', 
                         from_encoding=response.info().get_param('charset'))

    return xml

def get_sitemap_type(xml):
    """Parse XML source and returns the type of sitemap.

    Args:
        xml (string): Source code of XML sitemap.

    Returns:
        sitemap_type (string): Type of sitemap (sitemap, sitemapindex, or None).
    """

    sitemapindex = xml.find_all('sitemapindex')
    sitemap = xml.find_all('urlset')

    if sitemapindex:
        return 'sitemapindex'
    elif sitemap:
        return 'urlset'
    else:
        return

def get_child_sitemaps(xml):
    """Return a list of child sitemaps present in a XML sitemap file.

    Args:
        xml (string): XML source of sitemap. 

    Returns:
        sitemaps (list): Python list of XML sitemap URLs.
    """

    sitemaps = xml.find_all("sitemap")

    output = []

    for sitemap in sitemaps:
        #output.concat([output, sitemap.findNext("loc").text])
        output.append(sitemap.findNext("loc").text)
    return output

def sitemap_to_dataframe(xml, name=None, data=None, verbose=False):
    """Read an XML sitemap into a Pandas dataframe. 

    Args:
        xml (string): XML source of sitemap. 
        name (optional): Optional name for sitemap parsed.
        verbose (boolean, optional): Set to True to monitor progress.

    Returns:
        dataframe: Pandas dataframe of XML sitemap content. 
    """

    df = pd.DataFrame(columns=['loc', 'changefreq', 'priority', 'domain', 'sitemap_name'])

    urls = xml.find_all("url")
  
    for url in urls:

        if xml.find("loc"):
            loc = url.findNext("loc").text
            parsed_uri = urlparse(loc)
            domain = '{uri.netloc}'.format(uri=parsed_uri)
        else:
            loc = ''
            domain = ''

        if xml.find("changefreq"):
            changefreq = url.findNext("changefreq").text
        else:
            changefreq = ''

        if xml.find("priority"):
            priority = url.findNext("priority").text
        else:
            priority = ''

        if name:
            sitemap_name = name
        else:
            sitemap_name = ''
              
        row = {
            'domain': domain,
            'loc': loc,
            'changefreq': changefreq,
            'priority': priority,
            'sitemap_name': sitemap_name,
        }

        if verbose:
            print(row)

        df = df.append(row, ignore_index=True)
    return df


url = "https://www.wenvision.com/sitemap.xml"
xml = get_child_sitemaps(get_sitemap(url))

def get_all_urls(url):
    """Return a dataframe containing all of the URLs from a site's XML sitemaps.

    Args:
        url (string): URL of site's XML sitemap. Usually located at /sitemap.xml

    Returns:
        df (dataframe): Pandas dataframe containing all sitemap content. 

    """


    xml = get_sitemap(url)
    sitemap_type = get_sitemap_type(xml)

    if sitemap_type =='sitemapindex':
        sitemaps = get_child_sitemaps(xml)
    else:
        sitemaps = [url]

    df = pd.DataFrame(columns=['loc', 'changefreq', 'priority', 'domain', 'sitemap_name'])

    for sitemap in sitemaps:
        sitemap_xml = get_sitemap(sitemap)
        df_sitemap = sitemap_to_dataframe(sitemap_xml, name=sitemap)

        df = pd.concat([df, df_sitemap], ignore_index=True)

    return df

df = get_all_urls(url)

#print(df.to_string())
df.describe()
print (df.head())

def parse_page(url):
    response = urllib.request.urlopen(url)
    soup = BeautifulSoup(response, 
                         'html.parser', 
                         from_encoding=response.info().get_param('charset'))

    elements = soup.find_all('a')
    to_return = []

    for element in elements:
        element['href'] = element['href'].removeprefix('https://wenvision.com')
        element['href'] = element['href'].removeprefix('https://www.wenvision.com')          
       
        if (element['href'].startswith('/') and len(element['href']) > 1):
            if (element['href'].startswith('/author') | element['href'].startswith('/signup')):
                continue
            to_return.append(element)
    
    return to_return

def find_or_create_node(cocoon, name):
    co_elm = findall(cocoon, filter_=lambda node: node.name in (name))

    if (len(co_elm) == 0):
        co_elm = Node(name, parent=cocoon)
    else:
        co_elm = co_elm[0]

    return co_elm

# MAIN PROCESS
cocoon_parent = Node("WE ENVISION")
cocoon_sister = Node("WE ENVISION")

root_page = "https://www.wenvision.com"

for index, row in df.iterrows():
    current_page = row['loc']
    if (current_page == root_page + "/"):
        continue
    
    print("*** PROCESSING + " + current_page)
    current_node_parent = find_or_create_node(cocoon_parent, current_page)
    current_node_sister = Node(current_page, parent=cocoon_sister)
    elements = parse_page(current_page)
    print("     -- Links + " + str(len(elements)))
    
    for element in elements:
        co_elm = find_or_create_node(cocoon_parent, root_page + element['href'])
        
        if (element.get_text().startswith("< ")):
            current_node_parent.parent = co_elm

        if (element.get_text().endswith(" >")):
            Node(root_page + element['href'], parent=current_node_sister)

print("*** PARENTS" )
for pre, fill, node in RenderTree(cocoon_parent):
    print("%s%s" % (pre, node.name))

print("*** SISTERS")
for pre, fill, node in RenderTree(cocoon_sister):
    print("%s%s" % (pre, node.name))
