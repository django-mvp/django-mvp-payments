"""Regions of a rendered Account Center, for tests that need one part of it.

Article XVI asks for assertions against rendered output rather than against the
presence of a class name. A whole page is often too coarse for that: the same
label appears in the navigation and on a card, so counting it across the page
answers a question nobody asked. These helpers narrow an assertion to the
region it is actually about.

django-mvp draws the Account Center's navigation twice — a collapsed copy above
the content and a persistent one beside it — so one registered entry
legitimately renders once per region.
"""

NAVIGATION_LABEL = 'aria-label="Account navigation"'
CARDS_MARKER = 'id="account-center-cards"'


def _enclosing_element(content: str, marker: int, tag: str) -> str:
    """The full `tag` element containing `marker`, nested copies and all."""
    start = content.rindex(f"<{tag}", 0, marker)
    opening, closing = f"<{tag}", f"</{tag}>"
    position, depth = start, 1
    while depth:
        next_open = content.find(opening, position + 1)
        next_close = content.index(closing, position + 1)
        if next_open != -1 and next_open < next_close:
            position, depth = next_open, depth + 1
        else:
            position, depth = next_close, depth - 1
    return content[start : position + len(closing)]


def account_navigation_regions(content: str) -> list[str]:
    """Every rendering of the Account Center's navigation, as markup."""
    regions, searched_to = [], 0
    while True:
        found = content.find(NAVIGATION_LABEL, searched_to)
        if found == -1:
            return regions
        region = _enclosing_element(content, found, "ul")
        regions.append(region)
        searched_to = found + len(NAVIGATION_LABEL)


def account_center_cards_region(content: str) -> str:
    """The cards region of the Account Center's overview, as markup."""
    return _enclosing_element(content, content.index(CARDS_MARKER), "div")
