import hashlib
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import KnowledgeDocument


class IngestChatbotKnowledgeCommandTests(TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def _file(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def _document(self, path, status):
        return KnowledgeDocument.objects.create(
            title=path.stem.title(),
            source_label=path.name,
            checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
            status=status,
        )

    @patch(
        "chatbot.management.commands.ingest_chatbot_knowledge.KnowledgeIngestionService"
    )
    def test_skips_ready_document_without_reprocess(self, service_class):
        path = self._file("ready.txt", "Already ingested knowledge.")
        self._document(path, KnowledgeDocument.STATUS_READY)
        stdout = StringIO()

        call_command("ingest_chatbot_knowledge", str(path), stdout=stdout)

        service_class.return_value.process_document.assert_not_called()
        self.assertIn("Created 0, processed 0, skipped 1, failed 0.", stdout.getvalue())

    @patch(
        "chatbot.management.commands.ingest_chatbot_knowledge.KnowledgeIngestionService"
    )
    def test_retries_existing_documents_that_are_not_ready(self, service_class):
        paths = [
            self._file("draft.txt", "Draft knowledge."),
            self._file("processing.txt", "Interrupted knowledge."),
            self._file("failed.txt", "Previously failed knowledge."),
        ]
        documents = [
            self._document(paths[0], KnowledgeDocument.STATUS_DRAFT),
            self._document(paths[1], KnowledgeDocument.STATUS_PROCESSING),
            self._document(paths[2], KnowledgeDocument.STATUS_FAILED),
        ]
        stdout = StringIO()

        call_command(
            "ingest_chatbot_knowledge",
            *(str(path) for path in paths),
            stdout=stdout,
        )

        processed_ids = [
            call.args[0].pk
            for call in service_class.return_value.process_document.call_args_list
        ]
        self.assertEqual(processed_ids, [document.pk for document in documents])
        self.assertIn("Created 0, processed 3, skipped 0, failed 0.", stdout.getvalue())

    @patch(
        "chatbot.management.commands.ingest_chatbot_knowledge.KnowledgeIngestionService"
    )
    def test_reprocesses_ready_document_when_requested(self, service_class):
        path = self._file("ready.txt", "Ready knowledge to refresh.")
        document = self._document(path, KnowledgeDocument.STATUS_READY)

        call_command(
            "ingest_chatbot_knowledge",
            str(path),
            reprocess=True,
            stdout=StringIO(),
        )

        service_class.return_value.process_document.assert_called_once()
        self.assertEqual(
            service_class.return_value.process_document.call_args.args[0].pk,
            document.pk,
        )

    @patch(
        "chatbot.management.commands.ingest_chatbot_knowledge.KnowledgeIngestionService"
    )
    def test_processes_remaining_files_then_fails_command(self, service_class):
        failed_path = self._file("failure.txt", "Knowledge that will fail.")
        success_path = self._file("success.txt", "Knowledge that will succeed.")
        self._document(failed_path, KnowledgeDocument.STATUS_FAILED)
        self._document(success_path, KnowledgeDocument.STATUS_DRAFT)
        service_class.return_value.process_document.side_effect = [
            RuntimeError("embedding unavailable"),
            None,
        ]
        stdout = StringIO()

        with self.assertRaisesMessage(
            CommandError, "1 knowledge file(s) failed to process."
        ):
            call_command(
                "ingest_chatbot_knowledge",
                str(failed_path),
                str(success_path),
                stdout=stdout,
            )

        self.assertEqual(service_class.return_value.process_document.call_count, 2)
        output = stdout.getvalue()
        self.assertIn("Failed failure.txt: embedding unavailable", output)
        self.assertIn("Processed Success: 0 chunk(s)", output)
        self.assertIn("Created 0, processed 1, skipped 0, failed 1.", output)
