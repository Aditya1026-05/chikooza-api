from django.contrib import admin

from chatbot.models import (
    ChatLog,
    ChatMessage,
    ChatSession,
    KnowledgeChunk,
    KnowledgeDocument,
)
from chatbot.rag_assistant import KnowledgeIngestionService


class KnowledgeChunkInline(admin.TabularInline):
    model = KnowledgeChunk
    fields = ("chunk_index", "page", "token_count", "content")
    readonly_fields = ("chunk_index", "page", "token_count", "content")
    extra = 0
    can_delete = False
    max_num = 20

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "chunk_count",
        "processed_at",
        "updated_at",
    )
    list_filter = ("status", "category", "created_at", "processed_at")
    search_fields = ("title", "source_label", "content", "processing_error")
    readonly_fields = (
        "checksum",
        "status",
        "chunk_count",
        "processing_error",
        "processed_at",
        "created_at",
        "updated_at",
    )
    inlines = (KnowledgeChunkInline,)
    actions = ("process_selected_documents",)
    ordering = ("-updated_at",)

    @admin.action(description="Process selected documents into RAG chunks")
    def process_selected_documents(self, request, queryset):
        service = KnowledgeIngestionService()
        processed = 0
        failed = 0
        for document in queryset:
            try:
                service.process_document(document)
                processed += 1
            except Exception:
                failed += 1

        if processed:
            self.message_user(request, f"Processed {processed} document(s).")
        if failed:
            self.message_user(
                request,
                f"{failed} document(s) failed. Open the document to see the error.",
                level="ERROR",
            )


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "page", "token_count", "created_at")
    list_filter = ("document__category", "document__status", "created_at")
    search_fields = ("content", "document__title", "document__source_label")
    readonly_fields = (
        "document",
        "chunk_index",
        "page",
        "token_count",
        "content",
        "metadata",
        "created_at",
    )
    ordering = ("document", "chunk_index")


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    fields = ("created_at", "role", "content", "provider", "model", "fallback")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "session_id",
        "user",
        "title",
        "is_public",
        "updated_at",
        "created_at",
    )
    list_filter = ("is_public", "created_at", "updated_at")
    search_fields = (
        "session_id",
        "title",
        "user__username",
        "user__email",
        "messages__content",
    )
    readonly_fields = ("session_id", "created_at", "updated_at")
    inlines = (ChatMessageInline,)
    ordering = ("-updated_at",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "session", "role", "provider", "model", "fallback")
    list_filter = ("role", "provider", "fallback", "created_at")
    search_fields = ("content", "session__session_id", "session__title")
    readonly_fields = (
        "session",
        "role",
        "content",
        "sources",
        "provider",
        "model",
        "fallback",
        "created_at",
    )
    ordering = ("-created_at",)


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
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
