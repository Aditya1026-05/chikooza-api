import os
import sys
import shutil
from django.apps import AppConfig
from django.conf import settings

class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'

    def ready(self):
        """
        This method is called once when Django starts.
        We'll add the logic to update the chatbot index here.
        """
        # This check ensures the update logic only runs in the main server process,
        # not the reloader process.
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            print("Checking for new documents to add to the chatbot...")
            self.update_chatbot_index()

    def update_chatbot_index(self):
        """
        Scans the 'data' folder for new documents, updates the FAISS index,
        and archives processed files to a 'processed_documents' subfolder.
        """
        # Imports are done here to avoid issues during Django's startup process.
        from .services import RAGService

        # The source directory is now the main 'data' folder
        source_dir = os.path.join(settings.BASE_DIR, 'data')
        processed_dir = os.path.join(source_dir, 'processed_documents')

        # Ensure the directory for processed files exists
        os.makedirs(processed_dir, exist_ok=True)

        # Get all files from the 'data' directory, but only include specific document types
        all_items_in_dir = os.listdir(source_dir)
        file_paths_to_add = []
        allowed_extensions = ['.pdf', '.txt', '.md'] # Add any other text-based extensions you use

        for item_name in all_items_in_dir:
            full_path = os.path.join(source_dir, item_name)
            # Check if it's a file and has an allowed extension
            if os.path.isfile(full_path) and os.path.splitext(item_name)[1].lower() in allowed_extensions:
                file_paths_to_add.append(full_path)

        if not file_paths_to_add:
            print("No new documents found in the 'data' folder.")
            return

        try:
            print(f"Found {len(file_paths_to_add)} new document(s) in 'data' folder. Processing...")
            rag_service = RAGService()
            rag_service.add_files_to_index(file_paths_to_add)

            # Move the processed files to the 'processed_documents' subfolder
            for path in file_paths_to_add:
                shutil.move(path, os.path.join(processed_dir, os.path.basename(path)))
            
            print(f"Successfully processed and archived {len(file_paths_to_add)} file(s).")

        except Exception as e:
            print(f"ERROR: Could not update chatbot index. {e}")