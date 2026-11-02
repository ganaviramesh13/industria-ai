import os
import shutil
import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from accounts.models import User
from machines.models import Machine
from manuals.models import Manual
from assistant.rag.pipeline import RAGPipeline


class Command(BaseCommand):
    help = "Seed initial users, machines from CSV, and index manual PDFs."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=== SEEDING INDUSTRIA AI DATASET ==="))

        # 1. Create Default Users
        users_data = [
            ("admin", "admin@industria.ai", "Admin@123456", User.Role.ADMIN, True, True),
            ("engineer", "engineer@industria.ai", "Engineer@123456", User.Role.ENGINEER, False, False),
            ("supervisor", "supervisor@industria.ai", "Supervisor@123456", User.Role.SUPERVISOR, False, False),
        ]

        admin_user = None
        for username, email, pwd, role, is_staff, is_super in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "role": role,
                    "is_staff": is_staff,
                    "is_superuser": is_super,
                }
            )
            user.set_password(pwd)
            user.role = role
            user.is_staff = is_staff
            user.is_superuser = is_super
            user.save()
            action = "Created" if created else "Updated"
            self.stdout.write(f"  [{action}] User: {username} (Role: {role})")
            if role == User.Role.ADMIN:
                admin_user = user

        # 2. Parse CSV and Register Machines
        csv_path = settings.PROJECT_ROOT / "machine_manual_index.csv"
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"CSV file not found at {csv_path}"))
            return

        rag = RAGPipeline()

        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                machine_id = row['machine_id'].strip()
                model = row['model'].strip()
                name = row['machine_name'].strip()
                doc_id = row['document_id'].strip()
                rev = row['revision'].strip()
                pdf_filename = row['pdf_filename'].strip()

                # Register machine
                machine, m_created = Machine.objects.get_or_create(
                    machine_id=machine_id,
                    defaults={
                        "model": model,
                        "name": name,
                        "description": f"Industrial {name} (Model {model})"
                    }
                )
                if m_created:
                    self.stdout.write(f"  [Registered Machine] {machine_id}: {name}")

                # Locate manual PDF
                source_pdf = settings.PROJECT_ROOT / "Manuals" / pdf_filename
                if not source_pdf.exists():
                    self.stderr.write(self.style.ERROR(f"Manual PDF not found: {source_pdf}"))
                    continue

                # Ensure destination directory in media
                media_dest_dir = Path(settings.MEDIA_ROOT) / "manuals"
                media_dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file_path = media_dest_dir / pdf_filename

                if not dest_file_path.exists():
                    shutil.copyfile(source_pdf, dest_file_path)

                # Register Manual record
                manual_title = f"{model} {'Operations' if 'OPS' in doc_id else ('Maintenance' if 'MNT' in doc_id else 'Operations and Maintenance')} Manual"

                manual, man_created = Manual.objects.get_or_create(
                    machine=machine,
                    document_id=doc_id,
                    revision=rev,
                    defaults={
                        "title": manual_title,
                        "uploaded_by": admin_user,
                        "indexing_status": Manual.IndexingStatus.PROCESSING
                    }
                )

                # Assign file relative to MEDIA_ROOT
                manual.pdf_file.name = f"manuals/{pdf_filename}"
                manual.save()

                # Trigger RAG Ingestion & ChromaDB Vector Indexing
                self.stdout.write(f"  Indexing manual: {doc_id} Rev {rev} ({machine_id})...")
                try:
                    result = rag.ingest_manual(
                        pdf_path=str(dest_file_path),
                        machine_id=machine_id,
                        document_id=doc_id,
                        title=manual_title,
                        revision=rev
                    )
                    manual.page_count = result["page_count"]
                    manual.chunk_count = result["chunk_count"]
                    manual.indexing_status = Manual.IndexingStatus.INDEXED
                    manual.error_message = ""
                    manual.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"    -> [SUCCESS] Indexed {result['chunk_count']} chunks across {result['page_count']} pages."
                    ))
                except Exception as e:
                    manual.indexing_status = Manual.IndexingStatus.FAILED
                    manual.error_message = str(e)
                    manual.save()
                    self.stderr.write(self.style.ERROR(f"    -> [FAILED] {e}"))

        self.stdout.write(self.style.SUCCESS("=== SEEDING & INGESTION COMPLETE ==="))

