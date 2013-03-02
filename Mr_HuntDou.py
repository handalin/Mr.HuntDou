# -*-coding:utf-8-*-
# (140, 193)
from bookxing_db.models import *
from htmlentitydefs import entitydefs
from HTMLParser import HTMLParser
import sys, re, urllib2, Image
import os
reload(sys)
sys.setdefaultencoding('utf-8')
# Declare a list of interesting tables.

def parseImgLink(url):
  fp = urllib2.urlopen(url)
  raw_html = fp.read()

class InfoParser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self.HTML = ''
    self.info = {'image_path':''}
    self.inside_mainpic = False
    self.inside_h1 = False
    self.inside_interest_sectl = False
    self.reading_title = False
    self.reading_rating = False
    self.reading_mainpic = False


  def handle_starttag(self, tag, attrs):
    if tag == 'div':
      for (k, v) in attrs:
        if k == 'id':
          if v == 'mainpic':
            # found @id=mainpic
            self.inside_mainpic = True
          elif v == 'interest_sectl':
            self.inside_interest_sectl = True

    elif tag == 'a' and self.inside_mainpic:
      self.inside_mainpic = False
      for (k, v) in attrs:
        if k == 'href':
          self.info.update({'image_urls': v})
    elif tag == 'h1':
      self.inside_h1 = True
    elif tag == 'span' and self.inside_h1:
      self.reading_title = True
    elif tag == 'strong' and self.inside_interest_sectl:
      self.reading_rating = True
   


  def handle_data(self, data):
    if self.reading_title:
      self.info.update({'title':data})
    elif self.reading_rating:
      self.info.update({'rating':data.strip()})

  def handle_endtag(self, tag):
    if tag == 'h1' and self.inside_h1:
      self.inside_h1 = False
    elif tag == 'span' and self.reading_title:
      self.reading_title = False
    elif tag == 'div' and self.reading_mainpic:
      self.inside_mainpic = False
    elif tag == 'strong' and self.reading_rating:
      self.reading_rating = False
  def parse_intro(self, intro_html):
    t = intro_html
    intro = t[t.find('<p>'):t.rfind('</p>')+4]  # drop head and foot
    p = intro.find('<p>')
    result = ''
    while p != -1 :
      q = intro.find('</p>')
      result += intro[p+3:q] + '\n'
      intro = intro[q+4:]
      p = intro.find('<p>')
    return result
        
  def regular_find(self):
    info = self.HTML
    # deal with the data
    try:
      author = re.findall( u'作者</span>:.+?>(.+?)</a>'.encode('utf-8'), info, re.S )[0]
      self.info.update({'author':author})
    except IndexError:
      pass
    try:
      publisher = re.findall(u'出版社:</span>(.+?)<br/.*>'.encode('utf-8'), info, re.S )[0][1:]
      self.info.update({'publisher':publisher})
    except IndexError:
      pass
    try:
      numOfPages = re.findall(u'页数:</span>(.+?)<br/.*>'.encode('utf-8'), info, re.S )[0][1:]
      self.info.update({'numOfPages':numOfPages})
    except IndexError:
      pass
    try:
      ISBN = re.findall(r'ISBN:</span>(.+?)<br/>', info )[0][1:]
      self.info.update({'ISBN':ISBN})
    except IndexError:
      self.info.update({'ISBN':''})
      pass

    def deal_with_intro(intro):
      intro = self.parse_intro(intro.strip())
      if len(intro) <= 1490:
        return intro
      else:
        return intro[:1490] + '...'
    try:
      intro = re.findall(u'<div class="intro">([\s\S]+?)</div>'.encode('utf-8'), info)
      if '<a href=' in intro[0]:
        self.info.update({'intro':deal_with_intro(intro[1])})
      else:
        self.info.update({'intro':deal_with_intro(intro[0])})
    except IndexError:
      pass


class UrlParser(HTMLParser):
  """get the books' url from a search_result. """
  def __init__(self):
    # Initialize base class.
    HTMLParser.__init__(self)
    self.hrefs = []
  
  def handle_starttag(self, tag, attrs):
    if tag == 'a':
      for (k,v) in attrs:
        if k == 'href' and re.match(r'http://book.douban.com/subject/\d+/*$', v):
          self.hrefs.append(v)
          #print v

def get_books_by_search(keyword):
  p = UrlParser()
  r = urllib2.Request('http://book.douban.com/subject_search?search_text=%s&cat=1001' % keyword)
  fd = urllib2.urlopen(r)
  f = fd.read()
  p.feed(f)
  if not p.hrefs:
    return []
  # p.hrefs -- the list of hrefs , got.
  p.hrefs = list(set(p.hrefs))
  q = InfoParser()
  book_list = []
  for href in p.hrefs:
    fd = urllib2.urlopen(href)
    f = fd.read()
    q.__init__()
    q.HTML = f
    q.feed(f)
    q.regular_find()
    book = q.info

    # get the infos from the book
    ISBN = book.get('ISBN', '')
    if not ISBN:
      continue
    title = book.get('title', '......')
    authors = book.get('author', '')
    publisher = book.get('publisher', '')
    numOfPages = book.get('numOfPages', '')
    intro = book.get('intro', '')
    rating = book.get('rating', '')
    img_name = 'bookxing/pic/thumbs/big/%s.jpg' % ISBN
    image_path = '%s.jpg' % ISBN
    book['image_path'] = image_path
    #try:
    new_book = Book(
      ISBN = ISBN,
      title = title[:min(len(title), 100)],
      authors = authors[:min(len(authors), 30)],
      publisher = publisher[:min(len(publisher), 100)],
      numOfPages = numOfPages,
      intro = intro,
      rating = rating,
      read_cnt = 0,
      image_path = image_path,
    )
    if book not in book_list and book.get('ISBN', ''):
      book_list.append(book)
    fd = urllib2.urlopen(q.info['image_urls'])
    img = fd.read()
    new_img = open(img_name, 'wb')
    new_img.write(img)
    new_img.close()
    try:
      # download fail -- maybe the picture is not exist.
      img = Image.open(img_name)
      out = img.resize((140, 193))
      out.save(img_name)
    except BaseException:
      pass
    try:
      new_book.save()
    except BaseException:
      try:
        new_book.intro = new_book.intro[:-4] + '...'
        new_book.save()
      except BaseException:
        try:
          new_book.intro = new_book.intro[:-5] + '...'
          new_book.save()
        except BaseException:
          try:
            new_book.intro = new_book.intro[:-6] + '...'
            new_book.save()
          except BaseException:
            pass

  return book_list
  """
  """
