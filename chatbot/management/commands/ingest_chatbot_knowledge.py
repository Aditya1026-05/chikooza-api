import hashlib
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from chatbot.models import KnowledgeDocument
from chatbot.rag_assistant import KnowledgeIngestionService


class Command(BaseCommand):
    help = "Ingest Chikooza chatbot reference documents into the RAG knowledge base."

    def add_arguments(self, parser):
        parser.add_argument(
            "paths",
            nargs="*",
            help="Optional files or directories to ingest. Defaults to chatbot/data knowledge folders.",
        )
        parser.add_argument(
            "--category",
            default=KnowledgeDocument.CATEGORY_GENERAL,
            choices=[choice[0] for choice in KnowledgeDocument.CATEGORY_CHOICES],
            help="Category to use for explicitly supplied paths.",
        )
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Reprocess existing documents with matching checksums.",
        )

    def handle(self, *args, **options):
        paths = self._paths(options["paths"])
        if not paths:
            self.stdout.write(self.style.WARNING("No knowledge files found."))
            return

        service = KnowledgeIngestionService()
        created = 0
        processed = 0
        skipped = 0
        failed = 0

        for path in paths:
            checksum = self._checksum(path)
            document = KnowledgeDocument.objects.filter(checksum=checksum).first()
            if document and not options["reprocess"]:
                skipped += 1
                continue

            if document is None:
                document = KnowledgeDocument(
                    title=self._title(path),
                    category=self._category(path, options["category"]),
                    source_label=path.name,
                    checksum=checksum,
                )
                with path.open("rb") as file_obj:
                    document.file.save(path.name, File(file_obj), save=True)
                created += 1

            try:
                service.process_document(document)
                processed += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processed {document.title}: {document.chunk_count} chunk(s)"
                    )
                )
            except Exception as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f"Failed {path.name}: {exc}"))

        self.stdout.write(
            f"Created {created}, processed {processed}, skipped {skipped}, failed {failed}."
        )

    def _paths(self, requested_paths):
        if requested_paths:
            roots = [Path(item).expanduser().resolve() for item in requested_paths]
        else:
            roots = [
                settings.BASE_DIR / "chatbot" / "data" / "public_knowledge",
                settings.BASE_DIR / "chatbot" / "data" / "processed_documents",
            ]

        paths = []
        for root in roots:
            if root.is_file() and self._is_supported(root):
                paths.append(root)
            elif root.is_dir():
                paths.extend(
                    path
                    for path in sorted(root.rglob("*"))
                    if path.is_file() and self._is_supported(path)
                )
        return paths

    def _is_supported(self, path):
        return path.suffix.lower() in {".pdf", ".txt", ".md"}

    def _title(self, path):
        return path.stem.replace("_", " ").replace("-", " ").title()

    def _category(self, path, default_category):
        lower_name = path.name.lower()
        if "chikooza" in lower_name:
            return KnowledgeDocument.CATEGORY_PRODUCT
        if "feed" in lower_name:
            return KnowledgeDocument.CATEGORY_FEED
        if "disease" in lower_name or "health" in lower_name:
            return KnowledgeDocument.CATEGORY_HEALTH
        if "setup" in lower_name or "shed" in lower_name or "farm" in lower_name:
            return KnowledgeDocument.CATEGORY_FARM_SETUP
        if "broiler" in lower_name:
            return KnowledgeDocument.CATEGORY_BROILER
        return default_category

    def _checksum(self, path):
        digest = hashlib.sha256()
        with path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
