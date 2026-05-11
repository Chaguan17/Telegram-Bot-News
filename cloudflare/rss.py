from xml.etree import ElementTree


def _text(element, path: str) -> str:
    found = element.find(path)
    return (found.text or "").strip() if found is not None else ""


def parse_rss_entries(xml_text: str) -> list[dict]:
    root = ElementTree.fromstring(xml_text)
    entries = []

    for item in root.findall(".//item"):
        entries.append({
            "title": _text(item, "title"),
            "link": _text(item, "link"),
        })

    if entries:
        return entries

    atom_ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f".//{atom_ns}entry"):
        link = ""
        link_element = entry.find(f"{atom_ns}link")
        if link_element is not None:
            link = link_element.attrib.get("href", "")
        entries.append({
            "title": _text(entry, f"{atom_ns}title"),
            "link": link,
        })

    return entries
