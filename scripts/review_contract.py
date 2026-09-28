"""Mandatory inspection fields; completed records still require actual visual work."""
BASE_CHECKS = {"layout_matches_source", "openings_match_confirmed_map", "room_function_matches",
               "no_added_or_missing_spaces", "no_blocked_access", "must_not_change_preserved",
               "camera_matches_plan", "must_show_covered"}
PACKAGE_CHECKS = {"style_consistent","materials_consistent","furniture_consistent",
                  "opening_geometry_consistent","lighting_consistent"}


def required_checks(kind):
    checks = set(BASE_CHECKS)
    if kind in {"birdseye","room_view","furnished_colour_plan"}:
        checks |= {"furniture_matches_scheme", "materials_match_scheme", "bay_window_and_balcony_preserved"}
    if kind == "room_view":
        checks |= {"camera_and_visible_proportions_plausible"}
    return checks
