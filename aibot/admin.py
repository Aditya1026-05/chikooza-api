from django.contrib import admin

from aibot.models import AIChatLog


@admin.register(AIChatLog)
class AIChatLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "query_preview",
        "response_preview",
        "query_id",
    )
    list_filter = ("created_at", "user")
    search_fields = ("query", "response", "query_id", "user__username", "user__email")
    readonly_fields = ("created_at", "query_id")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    @admin.display(description="Query")
    def query_preview(self, obj):
        return obj.query[:80]

    @admin.display(description="Response")
    def response_preview(self, obj):
        return obj.response[:80]
