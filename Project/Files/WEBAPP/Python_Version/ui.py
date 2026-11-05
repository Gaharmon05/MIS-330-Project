"""
ui.py -- display-only helpers for the templates (no database code here).
  TABS          the sections of the one page and who may see each one
  icon(name)    inline SVG icons
  swatch(color) turns a color name from the Category table into a hex color
"""
from markupsafe import Markup

# (tab id, menu label, page subtitle, icon, who can see it)
TABS = [
    ("shop",        "Shop",        "Clothing, shoes and accessories",            "shop",      "everyone"),
    ("cart",        "Cart",        "Review your items and check out",            "cart",      "customer"),
    ("orders",      "Orders",      "Your purchase history",                      "receipt",   "customer"),
    ("alterations", "Alterations", "Tailoring for any piece of clothing",        "scissors",  "everyone"),
    ("board",       "Work board",  "Assign tailors and move jobs along",         "board",     "employee"),
    ("products",    "Products",    "Add, edit and remove products",              "tag",       "manager"),
    ("inventory",   "Inventory",   "Stock levels, suppliers and deliveries",     "box",       "manager"),
    ("employees",   "Employees",   "Staff accounts and roles",                   "users",     "manager"),
    ("reports",     "Reports",     "Business reports for decision making",       "chart",     "manager"),
    ("account",     "Account",     "Sign in, register or edit your profile",     "user",      "everyone"),
]

ICONS = {
    "shop":     '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',
    "cart":     '<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2 2h2l2.7 12.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L22 7H5.1"/>',
    "receipt":  '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    "scissors": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/>',
    "board":    '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/>',
    "tag":      '<path d="M12.6 2.6A2 2 0 0 0 11.2 2H4a2 2 0 0 0-2 2v7.2a2 2 0 0 0 .6 1.4l8.7 8.7a2.4 2.4 0 0 0 3.4 0l6.6-6.6a2.4 2.4 0 0 0 0-3.4Z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    "box":      '<path d="M21 8 12 3 3 8v8l9 5 9-5Z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    "users":    '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2M16 3.1a4 4 0 0 1 0 7.8M22 21v-2a4 4 0 0 0-3-3.9"/>',
    "chart":    '<path d="M3 3v18h18"/><path d="M7 16v-4M12 16V8M17 16v-7"/>',
    "user":     '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "logout":   '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
    "search":   '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    "check":    '<path d="M20 6 9 17l-5-5"/>',
    "plus":     '<path d="M12 5v14M5 12h14"/>',
    "trash":    '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
    "edit":     '<path d="M17 3a2.8 2.8 0 0 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>',
    "truck":    '<path d="M10 17h4V5H2v12h3M14 9h4l4 4v4h-2"/><circle cx="7.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "alert":    '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
    "dollar":   '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    "info":     '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "sparkle":  '<path d="m12 3 1.9 5.8L20 10l-6.1 1.2L12 17l-1.9-5.8L4 10l6.1-1.2Z"/>',
}

COLOR_HEX = {
    "white": "#f8fafc", "black": "#1f2937", "blue": "#3b82f6", "navy": "#1e3a8a",
    "red": "#dc2626", "khaki": "#c3b091", "charcoal": "#374151", "gray": "#9ca3af",
    "grey": "#9ca3af", "green": "#16a34a", "brown": "#8b5a2b", "pink": "#f472b6",
    "beige": "#e8dcc4", "yellow": "#facc15", "purple": "#7c3aed", "teal": "#14b8a6",
}


def icon(name):
    """<svg> markup for an icon, safe to drop into a template."""
    return Markup(f'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">{ICONS.get(name, "")}</svg>')


def swatch(color_name):
    return COLOR_HEX.get((color_name or "").lower(), "#14b8a6")


def initials(name):
    return (name or "?")[:1].upper()
