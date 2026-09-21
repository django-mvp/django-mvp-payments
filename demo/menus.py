"""Sidebar navigation for the demo project.

The tree is registered by :meth:`demo.apps.DemoConfig.ready` importing this
module, which has to happen there rather than at module import because the
entries name views.

Each component page adds its entry here as it lands.
"""

from flex_menu import MenuItem
from mvp.menus import AppMenu

AppMenu.extend(
    [
        MenuItem(
            name="home",
            view_name="home",
            extra_context={"label": "Home", "icon": "home"},
        ),
    ]
)
