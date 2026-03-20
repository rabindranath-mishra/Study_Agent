#!/usr/bin/env python3
"""Fetch a web page and return JSON with: url, title, publish_date (if found), description, text_snippet
Usage (Windows PowerShell):
  # Run from vault root:
  .\\"00 - System"\\.agent\\venv\\Scripts\\python.exe ".\\00 - System\\.agent\\tools\\web_fetch.py" "https://example.com/article"
"""
import sys
import json
import requests
from bs4 import BeautifulSoup
import re
import certifi

def extract_date(soup):
    selectors = [
        ('meta', {'property':'article:published_time'}),
        ('meta', {'name':'pubdate'}),
        ('meta', {'name':'publication_date'}),
        ('meta', {'name':'date'}),
        ('meta', {'property':'og:published_time'}),
        ('meta', {'name':'DC.date.issued'}),
    ]
    for tag, attrs in selectors:
        el = soup.find(tag, attrs=attrs)
        if el and el.get('content'):
            return el.get('content')
    t = soup.find('time')
    if t and t.get('datetime'):
        return t.get('datetime')
    return None

def get_text_snippet(soup, max_len=2000):
    article = soup.find('article')
    if article:
        text = article.get_text(separator=' ', strip=True)
    else:
        main = soup.find('main')
        if main:
            text = main.get_text(separator=' ', strip=True)
        else:
            body = soup.find('body')
            text = body.get_text(separator=' ', strip=True) if body else ''
    text = re.sub(r'\s+', ' ', text)
    return text[:max_len].strip()

def fetch(url):
    headers = {'User-Agent': 'StudyAgent/1.0 (+https://example.com)'}
    # Use certifi CA bundle with python-certifi-win32 for Windows certificate support
    resp = requests.get(url, headers=headers, timeout=15, verify=certifi.where())
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    publish_date = extract_date(soup)
    description = ''
    desc_tag = soup.find('meta', attrs={'name':'description'}) or soup.find('meta', attrs={'property':'og:description'})
    if desc_tag and desc_tag.get('content'):
        description = desc_tag.get('content').strip()
    snippet = get_text_snippet(soup)
    return {
        'url': url,
        'title': title,
        'publish_date': publish_date,
        'description': description,
        'text_snippet': snippet
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python web_fetch.py <url>')
        sys.exit(1)
    url = sys.argv[1]
    try:
        out = fetch(url)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e), 'url': url}))
        sys.exit(1)
