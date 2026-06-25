from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .vector_fields import PgVectorField


class KnowledgeDocument(models.Model):
    CATEGORY_PRODUCT = "product"
    CATEGORY_BROILER = "broiler"
    CATEGORY_FEED = "feed"
    CATEGORY_HEALTH = "health"
    CATEGORY_FARM_SETUP = "farm_setup"
    CATEGORY_REPORTS = "reports"
    CATEGORY_GENERAL = "general"

    CATEGORY_CHOICES = (
        (CATEGORY_PRODUCT, "Chikooza product"),
        (CATEGORY_BROILER, "Broiler management"),
        (CATEGORY_FEED, "Feed and nutrition"),
        (CATEGORY_HEALTH, "Health and disease"),
        (CATEGORY_FARM_SETUP, "Farm setup"),
        (CATEGORY_REPORTS, "Reports and records"),
        (CATEGORY_GENERAL, "General poultry"),
    )

    STATUS_DRAFT = "draft"
    STATUS_PROCESSING = "processing"
    STATUS_READY = "ready"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_READY, "Ready"),
        (STATUS_FAILED, "Failed"),
    )

    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=40,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GENERAL,
    )
    source_label = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="chatbot/knowledge/", blank=True, null=True)
    content = models.TextField(blank=True)
    checksum = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    chunk_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    processing_error = models.TextField(blank=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-created_at")
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["checksum"]),
        ]

    def __str__(self):
        return self.title

    @property
    def display_source(self):
        if self.source_label:
            return self.source_label
        if self.file:
            return self.file.name.rsplit("/", 1)[-1]
        return self.title

    def mark_processing(self):
        self.status = self.STATUS_PROCESSING
        self.processing_error = ""
        self.save(update_fields=["status", "processing_error", "updated_at"])

    def mark_ready(self, chunk_count):
        self.status = self.STATUS_READY
        self.chunk_count = chunk_count
        self.processing_error = ""
        self.processed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "chunk_count",
                "processing_error",
                "processed_at",
                "updated_at",
            ]
        )

    def mark_failed(self, error):
        self.status = self.STATUS_FAILED
        self.processing_error = str(error)[:4000]
        self.save(update_fields=["status", "processing_error", "updated_at"])


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(
        KnowledgeDocument,
        related_name="chunks",
        on_delete=models.CASCADE,
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    page = models.CharField(max_length=40, blank=True)
    token_count = models.PositiveIntegerField(default=0)
    embedding = PgVectorField(dimensions=384, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("document_id", "chunk_index")
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="chatbot_unique_document_chunk",
            )
        ]
        indexes = [
            models.Index(fields=["document", "chunk_index"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.document.title} chunk {self.chunk_index}"

    @property
    def source_label(self):
        source = self.document.display_source
        if self.page:
            return f"{source}, page {self.page}"
        return source


class ChatSession(models.Model):
    session_id = models.UUIDField(unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=160, blank=True)
    is_public = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=["user", "updated_at"]),
            models.Index(fields=["is_public", "updated_at"]),
        ]

    def __str__(self):
        return self.title or str(self.session_id)


class ChatMessage(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"

    ROLE_CHOICES = (
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
    )

    session = models.ForeignKey(
        ChatSession,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    provider = models.CharField(max_length=60, blank=True)
    model = models.CharField(max_length=120, blank=True)
    fallback = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["role", "created_at"]),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:80]}"


class ChatLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    query = models.TextField()
    response = models.TextField()
    query_id = models.CharField(max_length=36)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["query_id"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user"]),
        ]
