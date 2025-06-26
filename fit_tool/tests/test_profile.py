from fit_tool.gen.profile import Profile


def test_profile():
    profile = Profile.get_default_profile()

    for type_name in profile.types_by_name:
        profile_type = profile.types_by_name[type_name]
        print(f"{type_name}", profile_type)
