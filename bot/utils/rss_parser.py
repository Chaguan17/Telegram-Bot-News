import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class RSSEntry:
    title: str
    link: str
    published: str = ""

def parse_rss_custom(xml_text: str) -> list[RSSEntry]:
    """Simple RSS/Atom parser using standard library only."""
    entries = []
    try:
        root = ET.fromstring(xml_text)
        
        # Handle RSS 2.0
        for item in root.findall(".//item"):
            title = item.findtext("title", "Sin título")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            entries.append(RSSEntry(title=title, link=link, published=pub_date))
            
        # Handle Atom if no RSS items found
        if not entries:
            # Atom uses namespaces, but we can search by local name
            for entry in root.findall(".//*[local-name()='entry']"):
                title = entry.findtext(".//*[local-name()='title']", "Sin título")
                link_node = entry.find(".//*[local-name()='link']")
                link = link_node.get("href") if link_node is not None else ""
                published = entry.findtext(".//*[local-name()='published']", "") or entry.findtext(".//*[local-name()='updated']", "")
                entries.append(RSSEntry(title=title, link=link, published=published))
                
    except Exception as e:
        print(f"RSS Parsing Error: {e}")
        
    return entries
