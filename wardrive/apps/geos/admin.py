from django.contrib.gis import admin

from apps.geos.models import City


@admin.register(City)
class CityAdmin(admin.GISModelAdmin):
    list_display = ("city", "country", "country_iso", "source", "source_id", "updated_at")
    list_filter = ("country_iso", "source", "country")
    search_fields = ("city", "country", "country_iso", "source_id")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
