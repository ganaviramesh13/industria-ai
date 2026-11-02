import os
import csv
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from machines.models import Machine
from manuals.models import Manual
from assistant.rag.pipeline import RAGPipeline


class Command(BaseCommand):
    help = "Ingest PDF manuals from machine_manual_index.csv into the database and persistent vector store."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-ingestion and re-embedding even if already indexed.',
        )
        parser.add_argument(
            '--csv',
            type=str,
            default=None,
            help='Custom path to machine_manual_index.csv',
        )

    def handle(self, *args, **options):
        project_root = Path(settings.PROJECT_ROOT)
        force_reindex = options.get('force', False)

        # Locate CSV
        csv_candidates = []
        if options.get('csv'):
            csv_candidates.append(Path(options['csv']))
        csv_candidates.extend([
            project_root / "machine_manual_index.csv",
            project_root / "Manuals" / "machine_manual_index.csv",
            project_root / "manual" / "machine_manual_index.csv",
        ])

        csv_path = next((p for p in csv_candidates if p.exists()), None)
        if not csv_path:
            raise CommandError(f"Could not locate machine_manual_index.csv in {project_root}")

        # Locate Manuals Directory
        manuals_dir_candidates = [
            project_root / "Manuals",
            project_root / "manual",
            project_root / "media" / "manuals",
        ]
        manuals_dir = next((d for d in manuals_dir_candidates if d.exists()), None)
        if not manuals_dir:
            raise CommandError(f"Could not locate Manuals/ directory in {project_root}")

        media_manuals_dir = Path(settings.MEDIA_ROOT) / "manuals"
        media_manuals_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.MIGRATE_HEADING("\n" + "=" * 65))
        self.stdout.write(self.style.MIGRATE_HEADING("  INDUSTRIA AI — Technical Manual Ingestion Pipeline"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 65))
        self.stdout.write(f"  Source CSV : {csv_path}")
        self.stdout.write(f"  PDF Directory: {manuals_dir}")
        self.stdout.write(f"  Media Store  : {media_manuals_dir}\n")

        # Read CSV
        rows = []
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                rows.append(cleaned)

        if not rows:
            raise CommandError("CSV file is empty or contains no records.")

        rag = RAGPipeline()
        summary_results = []
        total_chunks = 0
        total_pages = 0

        for row in rows:
            machine_id = row.get("machine_id", "").strip()
            model = row.get("model", "").strip()
            machine_name = row.get("machine_name", "").strip()
            doc_id = row.get("document_id", "").strip()
            rev = row.get("revision", "1.0").strip()
            pdf_filename = row.get("pdf_filename", "").strip()

            # Determine Title
            doc_title = row.get("document_title", "").strip()
            if not doc_title:
                if "OPS" in doc_id and "MNT" not in doc_id:
                    doc_title = f"{model} Operations Manual"
                elif "MNT" in doc_id and "OPS" not in doc_id:
                    doc_title = f"{model} Maintenance Manual"
                else:
                    doc_title = f"{model} Operations and Maintenance Manual"

            self.stdout.write(f"\n[Processing] Machine: {machine_id} ({model}) | Doc: {doc_id} Rev {rev}")

            # 1. Ensure Machine Record Exists (exact 2 machines expected: M-HP200, M-AC90)
            machine, m_created = Machine.objects.get_or_create(
                machine_id=machine_id,
                defaults={
                    "model": model,
                    "name": machine_name,
                    "description": f"Industrial {machine_name} (Model {model})"
                }
            )
            if m_created:
                self.stdout.write(self.style.SUCCESS(f"  -> Created machine record: {machine_id} - {model}"))
            else:
                self.stdout.write(f"  -> Machine record verified: {machine_id} - {model}")

            # 2. Locate source PDF
            src_pdf = manuals_dir / pdf_filename
            if not src_pdf.exists():
                alt_pdf = project_root / "Manuals" / pdf_filename
                if alt_pdf.exists():
                    src_pdf = alt_pdf
                else:
                    self.stderr.write(self.style.ERROR(f"  -> ERROR: PDF file not found: {pdf_filename}"))
                    continue

            # 3. Ensure copy in media/manuals
            dest_pdf = media_manuals_dir / pdf_filename
            if not dest_pdf.exists() or dest_pdf.resolve() != src_pdf.resolve():
                shutil.copyfile(src_pdf, dest_pdf)
                self.stdout.write(f"  -> Stored copy at {dest_pdf.name}")

            # 4. Ensure Manual Record Exists
            manual, man_created = Manual.objects.get_or_create(
                machine=machine,
                document_id=doc_id,
                revision=rev,
                defaults={
                    "title": doc_title,
                    "indexing_status": Manual.IndexingStatus.PENDING
                }
            )
            manual.title = doc_title
            manual.pdf_file.name = f"manuals/{pdf_filename}"
            manual.save()

            # 5. Check if re-index needed
            if not force_reindex and manual.indexing_status == Manual.IndexingStatus.INDEXED and manual.chunk_count > 0:
                self.stdout.write(self.style.NOTICE(f"  -> Already indexed ({manual.chunk_count} chunks, {manual.page_count} pages). Use --force to re-index."))
                total_chunks += manual.chunk_count
                total_pages += manual.page_count
                summary_results.append({
                    "machine": machine_id,
                    "doc_id": doc_id,
                    "title": doc_title,
                    "status": "CACHED",
                    "pages": manual.page_count,
                    "chunks": manual.chunk_count
                })
                continue

            # 6. Run RAG Ingestion Pipeline
            manual.indexing_status = Manual.IndexingStatus.PROCESSING
            manual.save()

            try:
                result = rag.ingest_manual(
                    pdf_path=str(dest_pdf),
                    machine_id=machine_id,
                    document_id=doc_id,
                    title=doc_title,
                    revision=rev
                )
                pages = result.get("page_count", 0)
                chunks = result.get("chunk_count", 0)
                manual.page_count = pages
                manual.chunk_count = chunks
                manual.indexing_status = Manual.IndexingStatus.INDEXED
                manual.error_message = ""
                manual.save()

                total_chunks += chunks
                total_pages += pages
                self.stdout.write(self.style.SUCCESS(f"  -> [INDEXED] Extracted {pages} pages, created {chunks} vector chunks."))
                summary_results.append({
                    "machine": machine_id,
                    "doc_id": doc_id,
                    "title": doc_title,
                    "status": "INDEXED",
                    "pages": pages,
                    "chunks": chunks
                })
            except Exception as e:
                manual.indexing_status = Manual.IndexingStatus.FAILED
                manual.error_message = str(e)
                manual.save()
                self.stderr.write(self.style.ERROR(f"  -> [FAILED] Ingestion error: {e}"))
                summary_results.append({
                    "machine": machine_id,
                    "doc_id": doc_id,
                    "title": doc_title,
                    "status": "FAILED",
                    "pages": 0,
                    "chunks": 0
                })

        # Summary Table
        self.stdout.write("\n" + "=" * 65)
        self.stdout.write(self.style.MIGRATE_HEADING("  INGESTION SUMMARY REPORT"))
        self.stdout.write("=" * 65)
        self.stdout.write(f"  {'Machine ID':<12} {'Document ID':<14} {'Pages':<8} {'Chunks':<8} {'Status':<10}")
        self.stdout.write("  " + "-" * 55)
        for s in summary_results:
            self.stdout.write(f"  {s['machine']:<12} {s['doc_id']:<14} {s['pages']:<8} {s['chunks']:<8} {s['status']:<10}")
        self.stdout.write("  " + "-" * 55)
        self.stdout.write(f"  Total Machines : {Machine.objects.count()}")
        self.stdout.write(f"  Total Manuals  : {Manual.objects.count()}")
        self.stdout.write(f"  Total Pages    : {total_pages}")
        self.stdout.write(f"  Total Chunks   : {total_chunks}")
        self.stdout.write("=" * 65 + "\n")

