from collections import defaultdict
from django.contrib.auth.models import Permission

APP_LABEL_TO_GROUP = {
    "bookings":        "Booking Management",
    "cars":            "Booking Management",
    "flights":         "Booking Management",
    "stay":            "Booking Management",
    "tickets":         "Support & Tickets",
    "users":           "Customer Data",
    "policy":          "Content Management",
    # add more if needed
}


class PermissionGrouper:
    """
    Fetches all Permissions, filters to only APP_LABEL_TO_GROUP keys,
    groups them under the friendly names, and strips 'Can ' from each name.
    """

    def __init__(self, mapping: dict[str, str] = APP_LABEL_TO_GROUP):
        self.mapping = mapping
        self.permissions = Permission.objects.select_related("content_type")

    def get_grouped(self) -> list[dict]:
        grouped: dict[str, list[dict]] = defaultdict(list)

        for perm in self.permissions:
            app = perm.content_type.app_label
            if app not in self.mapping:
                continue

            group_name = self.mapping[app]
            human_name = perm.name
            if human_name.lower().startswith("can "):
                human_name = human_name[4:]

            grouped[group_name].append({
                "id": perm.id,
                "codename": perm.codename,
                "name": human_name,
            })

        return [
            {"group": group, "permissions": perms}
            for group, perms in grouped.items()
        ]
