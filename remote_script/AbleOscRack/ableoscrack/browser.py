import Live
from typing import Tuple, Any
from .handler import AbletonOSCHandler


# Map category names used in OSC params to browser attribute names
_CATEGORIES = {
    "instruments":   "instruments",
    "audio_effects": "audio_effects",
    "midi_effects":  "midi_effects",
    "plugins":       "plugins",
    "sounds":        "sounds",
    "drums":         "drums",
    "user_library":  "user_library",
}

# Map category names to hotswap filter types that guide where the device lands
_FILTER_TYPES = {
    "instruments":   Live.Browser.FilterType.instrument_hotswap,
    "audio_effects": Live.Browser.FilterType.audio_effect_hotswap,
    "midi_effects":  Live.Browser.FilterType.midi_effect_hotswap,
    "drums":         Live.Browser.FilterType.drum_pad_hotswap,
}


class BrowserHandler(AbletonOSCHandler):
    """OSC handler for Ableton's Browser API.

    Enables searching for and loading devices (instruments, effects) onto
    tracks from within the Live browser.

    Key constraint: loading is performed by selecting the target track as
    the hotswap target and calling browser.load_item(). This is the only
    supported way to add devices to tracks via the Live Python API.
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "browser"

    def init_api(self):

        def _browser():
            return Live.Application.get_application().browser

        def _get_category(browser, category_name):
            attr = _CATEGORIES.get(category_name)
            if attr is None:
                return None
            return getattr(browser, attr, None)

        def _iter_children(item):
            """Safely iterate children of a BrowserItem."""
            try:
                return item.children
            except Exception:
                return []

        def _collect_loadable(item, max_depth=1, depth=0):
            """Collect loadable (non-folder) items up to max_depth levels deep."""
            results = []
            try:
                is_folder = item.is_folder
            except Exception:
                is_folder = False
            if item.is_loadable and not is_folder:
                results.append(item)
            if depth < max_depth:
                for child in _iter_children(item):
                    results.extend(_collect_loadable(child, max_depth, depth + 1))
            return results

        def _search_item(item, query, max_depth=4, depth=0):
            """Find a loadable item whose name matches query (case-insensitive).

            Prefers exact matches over partial (contains) matches.
            Returns the best match found, or None.
            """
            query_lower = query.lower()
            partial = None

            try:
                is_folder = item.is_folder
            except Exception:
                is_folder = False

            if item.is_loadable and not is_folder:
                name_lower = item.name.lower()
                if name_lower == query_lower:
                    return item  # exact match — return immediately
                elif query_lower in name_lower and partial is None:
                    partial = item

            if depth < max_depth:
                for child in _iter_children(item):
                    result = _search_item(child, query, max_depth, depth + 1)
                    if result is not None:
                        if result.name.lower() == query_lower:
                            return result  # exact match from subtree
                        elif partial is None:
                            partial = result

            return partial

        # ----------------------------------------------------------------
        # /live/browser/get/categories — list available category names
        # ----------------------------------------------------------------

        def browser_get_categories(params: Tuple[Any] = ()):
            return tuple(_CATEGORIES.keys())

        self.osc_server.add_handler(
            "/live/browser/get/categories", browser_get_categories
        )

        # ----------------------------------------------------------------
        # /live/browser/get/devices (category_name)
        # ----------------------------------------------------------------

        def browser_get_devices(params: Tuple[Any] = ()):
            """Return names of directly loadable items in a browser category."""
            category_name = str(params[0]) if params else "instruments"
            browser = _browser()
            # Set filter_type first — activates the category in Ableton's browser
            # and forces lazy children to be populated.
            filter_type = _FILTER_TYPES.get(category_name)
            if filter_type is not None:
                browser.filter_type = filter_type
            category = _get_category(browser, category_name)
            if category is None:
                return ()
            # max_depth=2 returns just the core native devices (e.g. "Auto Filter",
            # "Compressor") without drilling into preset subfolders.
            items = _collect_loadable(category, max_depth=2)
            return tuple(item.name for item in items)

        self.osc_server.add_handler(
            "/live/browser/get/devices", browser_get_devices
        )

        # ----------------------------------------------------------------
        # /live/browser/load (track_index, category_name, device_name)
        # ----------------------------------------------------------------

        def browser_load(params: Tuple[Any] = ()):
            """Search for a device by name and load it onto a track.

            Selects the target track as the hotswap target before loading.
            Returns (1, item_name) on success or (0,) if not found.
            """
            track_index = int(params[0])
            category_name = str(params[1])
            device_name = str(params[2])

            browser = _browser()
            song = self.song

            # Select the target track — this sets it as the hotswap target
            track = song.tracks[track_index]
            song.view.selected_track = track

            # Apply filter type to guide where the device will land
            filter_type = _FILTER_TYPES.get(category_name)
            if filter_type is not None:
                browser.filter_type = filter_type

            # Find the device in the browser
            category = _get_category(browser, category_name)
            if category is None:
                return (0,)

            item = _search_item(category, device_name)
            if item is None or not item.is_loadable:
                return (0,)

            browser.load_item(item)
            return (1, item.name)

        self.osc_server.add_handler("/live/browser/load", browser_load)

        # ----------------------------------------------------------------
        # /live/browser/get/presets (category_name, device_name)
        # Returns loadable preset names inside a named device's folder.
        # ----------------------------------------------------------------

        def browser_get_presets(params: Tuple[Any] = ()):
            """Collect presets that live inside a device's folder subtree."""
            category_name = str(params[0]) if len(params) > 0 else "instruments"
            device_name = str(params[1]) if len(params) > 1 else ""

            browser = _browser()
            filter_type = _FILTER_TYPES.get(category_name)
            if filter_type is not None:
                browser.filter_type = filter_type
            category = _get_category(browser, category_name)
            if category is None:
                return ()

            device_lower = device_name.lower()
            results = []

            def walk(item, in_device_subtree=False, depth=0):
                try:
                    is_folder = item.is_folder
                except Exception:
                    is_folder = False
                try:
                    loadable = item.is_loadable
                except Exception:
                    loadable = False

                # Does this item's name match the target device?
                # Ableton devices can be loadable non-folders that also have
                # preset children (e.g. "Analog" is loadable + has sub-folders).
                name_matches = device_lower and device_lower in item.name.lower()

                # Collect loadable non-folder items once inside the device's
                # subtree — but NOT the device itself (that's the default patch).
                if loadable and not is_folder and in_device_subtree:
                    results.append(item.name)

                # Pass True to children when the current item matched or we're
                # already inside the subtree.
                child_in_subtree = in_device_subtree or name_matches

                if depth < 5:
                    for child in _iter_children(item):
                        walk(child, child_in_subtree, depth + 1)

            walk(category)
            return tuple(results[:100])  # cap to keep response size reasonable

        self.osc_server.add_handler("/live/browser/get/presets", browser_get_presets)
