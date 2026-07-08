"""v7 (owner) — curated identity for non-state actors: full official names and
flag/emblem images, so Hamas/Hezbollah/etc. render like first-class entities
(the way countries get flags). Keyed by the seeded NSA name. Flags via
Wikimedia Special:FilePath (same pattern as country flags, proxy-safe)."""

def _wm(f):
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{f}?width=320"


NSA_IDENTITY = {
    "Hamas": {
        "official_name": "Harakat al-Muqawama al-Islamiya "
                         "(Islamic Resistance Movement)",
        "flag_image_url": _wm("Flag of Hamas.svg"),
    },
    "Hezbollah": {
        "official_name": "Hizb Allah (The Party of God)",
        "flag_image_url": _wm("Flag of Hezbollah.svg"),
    },
    "Houthi Movement (Ansar Allah)": {
        "official_name": "Ansar Allah (Supporters of God)",
        "flag_image_url": _wm("Flag of the Houthi movement.svg"),
    },
    "Islamic State Sahel Province": {
        "official_name": "Islamic State - Sahel Province (Wilayat al-Sahil)",
        "flag_image_url": _wm("Flag of the Islamic State.svg"),
    },
    "JNIM (al-Qaeda in the Sahel)": {
        "official_name": "Jama'at Nusrat al-Islam wal-Muslimin "
                         "(Group for the Support of Islam and Muslims)",
        "flag_image_url": _wm("Flag of Jama'at Nasr al-Islam wal Muslimin.svg"),
    },
    "M23 Movement": {
        "official_name": "Mouvement du 23 mars (March 23 Movement)",
        "flag_image_url": _wm("Flag of the March 23 Movement.svg"),
    },
    "People's Defence Forces (Myanmar)": {
        "official_name": "People's Defence Force (PDF) - armed wing of the "
                         "National Unity Government of Myanmar",
        "flag_image_url": _wm("Flag of the People's Defence Force (Myanmar).svg"),
    },
    "Rapid Support Forces": {
        "official_name": "Quwwat al-Da'm al-Sari' (Rapid Support Forces, RSF)",
        "flag_image_url": _wm("Flag of the Rapid Support Forces.svg"),
    },
}
