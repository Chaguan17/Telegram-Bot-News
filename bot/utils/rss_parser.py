import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class RSSEntry:
    title: str
    link: str
    published: str = ""

def parse_rss_custom(xml_text: str) -> list[RSSEntry]:
    """Simple RSS/Atom parser using standard library only.
    Handles namespaces manually for maximum compatibility."""
    entries = []
    try:
        # Some feeds have encoding issues, we try to fix common ones
        if isinstance(xml_text, bytes):
            xml_text = xml_text.decode('utf-8', errors='ignore')
            
        root = ET.fromstring(xml_text)
        
        # We iterate over all elements and check their local name
        # to avoid complex XPath predicates that might fail in some Python versions.
        for node in root.iter():
            tag_local = node.tag.split('}')[-1]
            
            # Handle RSS 'item' or Atom 'entry'
            if tag_local in ('item', 'entry'):
                title = ""
                link = ""
                published = ""
                
                for child in node:
                    child_local = child.tag.split('}')[-1]
                    if child_local == 'title':
                        title = child.text or "Sin título"
                    elif child_local == 'link':
                        # RSS uses text inside <link>, Atom uses href attribute
                        link = child.text or child.get('href', '')
                    elif child_local in ('pubDate', 'published', 'updated'):
                        published = child.text or ""
                
                if title or link:
                    entries.append(RSSEntry(title=title, link=link, published=published))
                
    except Exception as e:
        print(f"RSS Parsing Error: {e}")
        
    return entries
