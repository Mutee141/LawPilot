import os
from django.core.management.base import BaseCommand
from django.core.files import File
from legal_library.models import Justice, Judgment

class Command(BaseCommand):
    help = 'Bulk imports extracted Supreme Court Judgments folder'

    def add_arguments(self, parser):
        parser.add_argument(
            'folder_path',
            nargs='+',
            type=str,
            help='Absolute path to the extracted Judgments folder (supports spaces in the path)'
        )

    def handle(self, *args, **options):
        base_path = os.path.abspath(' '.join(options['folder_path']))

        if not os.path.exists(base_path):
            self.stdout.write(self.style.ERROR(f"Path does not exist: {base_path}"))
            return

        # Iterate through Justice folders
        for justice_folder in os.listdir(base_path):
            justice_path = os.path.join(base_path, justice_folder)
            
            if os.path.isdir(justice_path):
                # 1. Create or get the Justice object
                justice_obj, created = Justice.objects.get_or_create(name=justice_folder.strip())
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created Justice: {justice_obj.name}"))

                # 2. Iterate through PDFs inside the Justice's folder
                for filename in os.listdir(justice_path):
                    if filename.lower().endswith('.pdf'):
                        file_path = os.path.join(justice_path, filename)
                        
                        # Check if already imported to prevent duplicates
                        if not Judgment.objects.filter(justice=justice_obj, title=filename).exists():
                            with open(file_path, 'rb') as f:
                                judgment = Judgment(
                                    title=filename,
                                    justice=justice_obj,
                                )
                                # Saves file automatically into your media/ directory setup
                                judgment.pdf_file.save(filename, File(f), save=True)
                            
                            self.stdout.write(f" Imported: {filename} for {justice_obj.name}")
                        else:
                            self.stdout.write(self.style.WARNING(f" Skipped (Exists): {filename}"))
                            
        self.stdout.write(self.style.SUCCESS("Bulk import completed successfully!"))