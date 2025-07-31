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
        Scans the 'chatbot/data' folder for new documents, updates the FAISS index,
        and logs processed files to avoid re-indexing.
        """
        from .services import RAGService

        # 1. The data folder is now inside the chatbot app
        data_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'data')
        log_file_path = os.path.join(data_dir, 'processed_log.txt')

        # Ensure the data directory exists
        os.makedirs(data_dir, exist_ok=True)

        # 2. Get the set of already processed files from the log
        processed_files = set()
        try:
            with open(log_file_path, 'r') as f:
                processed_files = set(line.strip() for line in f)
        except FileNotFoundError:
            pass # Log file doesn't exist yet, which is fine

        # 3. Find all potential document files in the data directory
        all_items_in_dir = os.listdir(data_dir)
        file_paths_to_add = []
        allowed_extensions = ['.pdf', '.txt', '.md']

        for item_name in all_items_in_dir:
            # Check if it's a file, has an allowed extension, AND has not been processed yet
            if item_name not in processed_files and os.path.splitext(item_name)[1].lower() in allowed_extensions:
                full_path = os.path.join(data_dir, item_name)
                if os.path.isfile(full_path):
                    file_paths_to_add.append(full_path)

        if not file_paths_to_add:
            print("No new documents found to index.")
            return

        try:
            print(f"Found {len(file_paths_to_add)} new document(s). Processing...")
            rag_service = RAGService()
            successfully_processed_paths = rag_service.add_files_to_index(file_paths_to_add)

            # 4. Log the successfully processed files to prevent re-indexing
            if successfully_processed_paths:
                with open(log_file_path, 'a') as f:
                    for path in successfully_processed_paths:
                        f.write(os.path.basename(path) + '\n')
                print(f"Successfully logged {len(successfully_processed_paths)} processed file(s).")

        except Exception as e:
            print(f"ERROR: Could not update chatbot index. {e}")