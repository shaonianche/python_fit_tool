PROFILE validation now supports selectable scopes (``ProfileScope.CORE`` /
``DOMAIN`` / ``FULL``) under architecture decision O1. Default ``strict`` /
``DEFAULT_LEVELS`` remain **CORE** (developer fields + ambiguous subfields).
DOMAIN and FULL add data-driven native base-type and closed-enum checks from a
gen-exported field catalog (``fit_tool.profile.field_catalog``) derived from
bundled Profile.xlsx ``21.205.0``. FULL is opt-in only; use
``validate_fit_file(..., profile_scope=ProfileScope.FULL)`` or
``profile_rule_coverage(ProfileScope.FULL)`` for coverage metrics.
