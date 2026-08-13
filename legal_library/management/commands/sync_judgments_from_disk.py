import os
from django.core.management.base import BaseCommand
from django.conf import settings
from legal_library.models import Justice, Judgment


class Command(BaseCommand):
    help = 'Scans the media/legal_library/supreme_court folder and registers all PDFs into the database without re-copying files'

    def handle(self, *args, **options):
        base_path = os.path.join(settings.MEDIA_ROOT, 'legal_library', 'supreme_court')

        if not os.path.exists(base_path):
            self.stdout.write(self.style.ERROR(
                f"Folder not found: {base_path}\n"
                "Make sure your PDF folders are inside media/legal_library/supreme_court/"
            ))
            return

        total_imported = 0
        total_skipped = 0

        justice_folders = sorted(os.listdir(base_path))

        for justice_folder in justice_folders:
            justice_path = os.path.join(base_path, justice_folder)

            if not os.path.isdir(justice_path):
                continue

            justice_name = justice_folder.strip()

            # Create or get Justice record
            justice_obj, created = Justice.objects.get_or_create(name=justice_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"\n[+] Justice created: {justice_name}"))
            else:
                self.stdout.write(f"\n[~] Justice exists: {justice_name}")

            pdf_files = sorted([f for f in os.listdir(justice_path) if f.lower().endswith('.pdf')])

            for filename in pdf_files:
                # Build the relative path as stored in the FileField
                relative_path = os.path.join(
                    'legal_library', 'supreme_court', justice_name, filename
                ).replace('\\', '/')

                # Skip if already registered in DB
                if Judgment.objects.filter(justice=justice_obj, title=filename).exists():
                    self.stdout.write(self.style.WARNING(f"   SKIP (already in DB): {filename}"))
                    total_skipped += 1
                    continue

                # Register the file path directly without copying
                judgment = Judgment(
                    title=filename,
                    justice=justice_obj,
                    pdf_file=relative_path,   # Point directly at existing file on disk
                )
                judgment.save()

                self.stdout.write(f"   Imported: {filename}")
                total_imported += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n[DONE] Imported: {total_imported} | Skipped (already existed): {total_skipped}"
        ))
