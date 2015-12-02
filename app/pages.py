from app.wiki import create_wiki_page, create_redirect_wiki_page
from app.__init__ import *
import re

CR = "\n"
LIST_ITEM = "* {} : {}\n"
ALEF_LINK = "http://aleph.nli.org.il/F?func=direct&local_base={}&doc_number={}"
WIKI_LINK = "[[{}|{}]]"  # first the link then the display text
AUTHORITY_ID_PATTERN = ".*\$\$E(.*)\$\$I(.*)\$\$P"  # e.g. "$$Dרכטר, יוני, 1951-$$Eרכטר, יוני, 1951-$$INNL10000110663$$PY M"

def str_to_list(str_or_list):
    if str_to_list is None:
        return None
    if type(str_or_list) is str:
        return [str_or_list]
    else:
        return str_or_list

def comma_and(line):
    """
    in a comma-separated list of terms, replace the last comma with וו החיבור.
    :param line: one or more comma-separated terms
    :return: last comma (if exists) replaced with "ו"
    """
    return ' ו'.join(line.rsplit(', ', maxsplit=1))

def entries_to_authority_id(browse_entries):
    """
    Create a dictionary from authority terms to their NNL record id. The input is a list of
    lines like this: "$$Dרכטר, יוני, 1951-$$Eרכטר, יוני, 1951-$$INNL10000110663$$PY M". Here the
    key is "רכטר, יוני, 1951-" and the value is "000110663"
    :param browse_entries: list of authority entries
    :return: a dictionary from authority name to NNL record id
    """
    authority_dictionary = {}
    for author in browse_entries:
        match = re.search(AUTHORITY_ID_PATTERN, author)
        if match:
            authority_dictionary[match.group(1)] = match.group(2)[5:]
    return authority_dictionary

def simple_person_name(primo_person_name):
    splitted = primo_person_name.split(", ", 2)
    return splitted[1] + " " + splitted[0]

def person_name(persons_to_id, primo_person_name):
    """
    Convert "last, first, year" to "first last" (year is optional)
    :param name: person name as "last, first, other"
    :return: first last
    """
    wiki_person_name = primo_person_name
    link = persons_to_id.get(primo_person_name)
    if not link:
        person_name_no_role = primo_person_name[:primo_person_name.rfind(" ")]
        link = persons_to_id.get(person_name_no_role)
        if link:
            wiki_person_name = person_name_no_role
    display_name = simple_person_name(wiki_person_name)
    if link:
        return WIKI_LINK.format(link, display_name)
    else:
        return display_name


def trim(line):
    """
    Trim non-alpha characters from the end of the line. Leave parentheses, quotes.
    For example trime("abc def..") returns "abc def"
    :param line: a string
    :return: the same string without trailing non-alpha characters
    """
    clean_line = line
    while clean_line and not clean_line[-1].isalnum() and not clean_line[-1] in '")':
        clean_line = clean_line[:-1]
    return clean_line


def create_page_from_dictionary(item_dict, debug=None):
    """
    create a wikipedia page from a dictionary that describes a primo item
    :param item_dict: primo item as a dictionary/json
    :param debug: if not debug then actually create the pages
    :return: page content in wiki markup
    """
    document_id = item_dict['control']['recordid']
    sourcerecordid = item_dict['control']['sourcerecordid']
    originalsourceid = item_dict['control']['originalsourceid']
    display = item_dict['display']
    try:
        title = trim(item_dict['sort']['title'])
    except:
        title = display['title']
    item_type = display['type']

    try:
        display_type = type_dict[item_type][1]  # hebrew type as a definite article, e.g. כתב העת
        display_type += " "
    except Exception as e:
        display_type = ""
        print("Unrecognized type '{}'".format(item_type))

    creation_verb = type_dict[item_type][2]
    creators_field = display.get('creator')
    creator = None
    if creators_field:
        authors_to_id = entries_to_authority_id(str_to_list(item_dict['browse']['author']))
        creators = creators_field.split(";")
        creator = ", ".join(set([person_name(authors_to_id, creator.strip()) for creator in creators]))
        creator = comma_and(creator)

    summary = display.get('lds20')

    comments = str_to_list(display.get('lds05'))
    comments_section = None
    if comments:
        comments_section = CR.join(["* " + comment for comment in comments])

    creationdate = display.get('creationdate')
    ispartof = display.get('ispartof')
    performed_by = display.get('lds35')  # list
    performed_by = str_to_list(performed_by)

    performed_by_str = None
    if performed_by:
        performed_by_str = ", ".join(person_name(authors_to_id, performer) for performer in performed_by)

    source = display['source']
    lib_link = display['lds21']

    content = "{{DISPLAYTITLE:%s}}\n" % title
    content += "{}'''{}''' {} על ידי {}".format(display_type, title, creation_verb, creator)

    if (creationdate):
        content += " בשנת {}".format(creationdate)
    content += CR
    if summary:
        content += CR + summary + CR

    content += "==פרטים כלליים==" + CR
    if (performed_by_str):
        content += LIST_ITEM.format("שם מבצע", performed_by_str)
    if (ispartof):
        content += LIST_ITEM.format("מתוך", ispartof)
    if comments_section:
        content += comments_section
    content += CR + "==מידע נוסף==" + CR
    content += LIST_ITEM.format("מקור", source)
    content += "* מספר מערכת: [{} {}]\n".format(lib_link, sourcerecordid)
    content += "== קישורים נוספים ==\n"
    alef_link = ALEF_LINK.format(originalsourceid, sourcerecordid)
    content += "* [{} הפריט בקטלוג הספריה]\n".format(alef_link)

    if not debug:
        create_redirect_wiki_page(page_name=title, redirect_to=document_id,
                                  summary="Creating redirect page for {}".format(document_id))
        create_wiki_page(page_name=document_id, summary="Created from primo", content=content)

    return content
