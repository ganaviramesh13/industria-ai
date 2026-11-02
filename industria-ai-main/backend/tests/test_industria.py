import os
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from machines.models import Machine
from manuals.models import Manual
from history.models import QuestionHistory
from assistant.rag.pipeline import RAGPipeline
from assistant.rag.vector_store import VectorStoreService


class IndustriaAITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create 3 users with respective roles
        self.admin = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='TestPassword123',
            role=User.Role.ADMIN
        )
        self.engineer1 = User.objects.create_user(
            username='engineer1_test',
            email='eng1@test.com',
            password='TestPassword123',
            role=User.Role.ENGINEER
        )
        self.engineer2 = User.objects.create_user(
            username='engineer2_test',
            email='eng2@test.com',
            password='TestPassword123',
            role=User.Role.ENGINEER
        )
        self.supervisor = User.objects.create_user(
            username='supervisor_test',
            email='sup@test.com',
            password='TestPassword123',
            role=User.Role.SUPERVISOR
        )

        # Create Machines
        self.hp200 = Machine.objects.create(
            machine_id='M-HP200',
            model='HP-200',
            name='Hydraulic forming press'
        )
        self.ac90 = Machine.objects.create(
            machine_id='M-AC90',
            model='AC-90',
            name='Air compressor'
        )

        # Create and Index Chunks for HP-200 and AC-90 in VectorStore
        self.vector_store = VectorStoreService()
        self.rag = RAGPipeline()

        # Insert HP-200 chunks
        hp_chunks = [
            {
                "chunk_id": "HP-OPS-01_rev1_0_p2_c1",
                "text": "Code: E17 | Meaning: Low hydraulic pressure | Response: Record pressure and cycle stage; place on HOLD and request the checks in HP-MNT-01 page 3.",
                "metadata": {
                    "machine_id": "M-HP200",
                    "document_id": "HP-OPS-01",
                    "document_title": "HP 200 Operations Manual",
                    "revision": "1.0",
                    "page_number": 2,
                    "chunk_identifier": "HP-OPS-01_rev1_0_p2_c1"
                }
            },
            {
                "chunk_id": "HP-OPS-01_rev1_0_p2_c2",
                "text": "E17 is generated when pressure stays below 110 bar for more than 5 seconds during forming. Normal forming range is 120 to 140 bar.",
                "metadata": {
                    "machine_id": "M-HP200",
                    "document_id": "HP-OPS-01",
                    "document_title": "HP 200 Operations Manual",
                    "revision": "1.0",
                    "page_number": 2,
                    "chunk_identifier": "HP-OPS-01_rev1_0_p2_c2"
                }
            },
            {
                "chunk_id": "HP-MNT-01_rev1_0_p3_c1",
                "text": "Low hydraulic pressure or E17: Collect these observations in order: (1) reservoir level relative to MIN and MAX; (2) visible external leakage reported by the operator; (3) RF-20 restriction-indicator state; (4) oil temperature and recorded pressure during forming.",
                "metadata": {
                    "machine_id": "M-HP200",
                    "document_id": "HP-MNT-01",
                    "document_title": "HP 200 Maintenance Manual",
                    "revision": "1.0",
                    "page_number": 3,
                    "chunk_identifier": "HP-MNT-01_rev1_0_p3_c1"
                }
            },
            {
                "chunk_id": "HP-OPS-01_rev1_0_p3_c1",
                "text": "Information not provided: This dataset does not specify the pump replacement price, supplier contacts, tightening torque, wiring diagrams, hydraulic circuit drawings, or internal repair procedures.",
                "metadata": {
                    "machine_id": "M-HP200",
                    "document_id": "HP-OPS-01",
                    "document_title": "HP 200 Operations Manual",
                    "revision": "1.0",
                    "page_number": 3,
                    "chunk_identifier": "HP-OPS-01_rev1_0_p3_c1"
                }
            }
        ]
        self.vector_store.index_chunks(hp_chunks)

        # Insert AC-90 chunks
        ac_chunks = [
            {
                "chunk_id": "AC-OM-01_rev1_0_p2_c1",
                "text": "Code: E17 | AC-90 meaning: High discharge temperature | Response: Record temperature; above 95 degrees C, hold and request cooling-path review. At 105 degrees C or higher, high-temperature stop applies.",
                "metadata": {
                    "machine_id": "M-AC90",
                    "document_id": "AC-OM-01",
                    "document_title": "AC 90 Operations and Maintenance Manual",
                    "revision": "1.0",
                    "page_number": 2,
                    "chunk_identifier": "AC-OM-01_rev1_0_p2_c1"
                }
            },
            {
                "chunk_id": "AC-OM-01_rev1_0_p3_c1",
                "text": "Every 100 operating hours: AF-10 inlet-filter restriction indicator check. Every 600 operating hours: Planned AF-10 replacement. A calendar interval for AF-10 is not supplied. The HP-200 RF-20 filter is not the AC-90 filter.",
                "metadata": {
                    "machine_id": "M-AC90",
                    "document_id": "AC-OM-01",
                    "document_title": "AC 90 Operations and Maintenance Manual",
                    "revision": "1.0",
                    "page_number": 3,
                    "chunk_identifier": "AC-OM-01_rev1_0_p3_c1"
                }
            }
        ]
        self.vector_store.index_chunks(ac_chunks)

    # =========================================================================
    # MANDATORY TEST 1: Engineer Upload Restriction (HTTP 403)
    # =========================================================================
    def test_mandatory_test1_engineer_upload_restriction(self):
        """
        Authenticate as Engineer.
        Attempt to upload a manual.
        Confirm HTTP 403 Forbidden.
        Confirm no manual is created in the database.
        """
        self.client.force_authenticate(user=self.engineer1)

        pdf_content = b"%PDF-1.4 simulated pdf manual"
        uploaded_file = SimpleUploadedFile("test_manual.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post('/api/manuals/upload/', {
            'machine_id': 'M-HP200',
            'document_id': 'UNAUTHORIZED-DOC',
            'title': 'Unauthorized Engineer Manual',
            'revision': '1.0',
            'pdf_file': uploaded_file
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Manual.objects.filter(document_id='UNAUTHORIZED-DOC').exists())

    # =========================================================================
    # MANDATORY TEST 2: Strict Machine Isolation at Vector Retrieval Time
    # =========================================================================
    def test_mandatory_test2_machine_isolation(self):
        """
        Query with HP-200 selected -> Verify no AC-90 chunk is returned.
        Query with AC-90 selected -> Verify no HP-200 chunk is returned.
        """
        # Query HP-200
        hp_passages = self.vector_store.query_machine(
            machine_id='M-HP200',
            query_text='What does E17 mean?'
        )
        self.assertTrue(len(hp_passages) > 0)
        for p in hp_passages:
            self.assertEqual(p['machine_id'], 'M-HP200')
            self.assertNotEqual(p['machine_id'], 'M-AC90')
            self.assertNotIn('High discharge temperature', p['text'])

        # Query AC-90
        ac_passages = self.vector_store.query_machine(
            machine_id='M-AC90',
            query_text='What does E17 mean?'
        )
        self.assertTrue(len(ac_passages) > 0)
        for p in ac_passages:
            self.assertEqual(p['machine_id'], 'M-AC90')
            self.assertNotEqual(p['machine_id'], 'M-HP200')
            self.assertNotIn('Low hydraulic pressure', p['text'])

    # =========================================================================
    # ROLE-BASED ACCESS CONTROL TESTS
    # =========================================================================
    def test_supervisor_cannot_upload_manual(self):
        """Supervisor must be denied upload privileges (HTTP 403)."""
        self.client.force_authenticate(user=self.supervisor)
        pdf_content = b"%PDF-1.4 simulated pdf"
        uploaded_file = SimpleUploadedFile("sup_test.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post('/api/manuals/upload/', {
            'machine_id': 'M-HP200',
            'document_id': 'SUP-DOC',
            'title': 'Supervisor Manual',
            'revision': '1.0',
            'pdf_file': uploaded_file
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_engineer_cannot_access_other_engineer_history(self):
        """Engineers can only access their own history, not another engineer's."""
        # Create history for engineer 1
        h1 = QuestionHistory.objects.create(
            user=self.engineer1,
            selected_machine=self.hp200,
            question="Engineer 1 Private Question",
            answer="Private Answer",
            status="answered"
        )

        # Authenticate as Engineer 2
        self.client.force_authenticate(user=self.engineer2)

        # Attempt to access engineer 1's history detail
        response = self.client.get(f'/api/assistant/history/{h1.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # List personal history: engineer 2 sees 0 entries
        list_resp = self.client.get('/api/assistant/history/')
        results = list_resp.data.get('results', list_resp.data)
        self.assertEqual(len(results), 0)

    def test_supervisor_can_access_question_audit(self):
        """Supervisor can read question history across all engineers."""
        QuestionHistory.objects.create(
            user=self.engineer1,
            selected_machine=self.hp200,
            question="Question by Eng 1",
            answer="Answer",
            status="answered"
        )
        QuestionHistory.objects.create(
            user=self.engineer2,
            selected_machine=self.ac90,
            question="Question by Eng 2",
            answer="Answer",
            status="answered"
        )

        self.client.force_authenticate(user=self.supervisor)
        response = self.client.get('/api/supervisor/questions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 2)

    # =========================================================================
    # DEMONSTRATION SCENARIOS GROUNDED TESTS
    # =========================================================================
    def test_scenario1_hp200_e17(self):
        """HP-200 E17 means Low hydraulic pressure, cited HP-OPS-01 page 2."""
        res = self.rag.answer_question('M-HP200', 'What does E17 mean?')
        self.assertEqual(res['status'], 'answered')
        self.assertIn('Low hydraulic pressure', res['answer'])
        self.assertTrue(any(c['document_id'] == 'HP-OPS-01' and c['page_number'] == 2 for c in res['citations']))

    def test_scenario2_ac90_e17(self):
        """AC-90 E17 means High discharge temperature, cited AC-OM-01 page 2."""
        res = self.rag.answer_question('M-AC90', 'What does E17 mean?')
        self.assertEqual(res['status'], 'answered')
        self.assertIn('High discharge temperature', res['answer'])
        self.assertTrue(any(c['document_id'] == 'AC-OM-01' and c['page_number'] == 2 for c in res['citations']))

    def test_scenario3_ac90_af10_filter(self):
        """AC-90 AF-10 filter: check every 100 hrs, replace every 600 hrs."""
        res = self.rag.answer_question(
            'M-AC90',
            'How often should the AF-10 filter indicator be checked, and when is planned replacement due?'
        )
        self.assertEqual(res['status'], 'answered')
        self.assertIn('100', res['answer'])
        self.assertIn('600', res['answer'])
        self.assertTrue(any(c['document_id'] == 'AC-OM-01' and c['page_number'] == 3 for c in res['citations']))

    def test_scenario4_hp200_multi_manual_answer(self):
        """HP-200 question needing trigger and observations cites both HP-OPS-01 and HP-MNT-01."""
        res = self.rag.answer_question(
            'M-HP200',
            'What triggers E17, and what observations should be collected?'
        )
        self.assertEqual(res['status'], 'answered')
        self.assertIn('110 bar', res['answer'])
        self.assertIn('reservoir level', res['answer'].lower())
        cited_docs = {c['document_id'] for c in res['citations']}
        self.assertIn('HP-OPS-01', cited_docs)
        self.assertIn('HP-MNT-01', cited_docs)

    def test_scenario5_missing_evidence_pump_price(self):
        """Asking for pump price produces insufficient_evidence."""
        res = self.rag.answer_question('M-HP200', 'What is the pump replacement price?')
        self.assertEqual(res['status'], 'insufficient_evidence')
        self.assertEqual(res['answer'], "The available manuals do not contain enough information to answer this question.")
        self.assertEqual(len(res['citations']), 0)

    def test_scenario6_cross_machine_leakage_blocked(self):
        """Asking AC-90 about HP-200 return filter produces insufficient evidence with no leakage."""
        res = self.rag.answer_question('M-AC90', 'What is the HP-200 return-filter replacement interval?')
        self.assertEqual(res['status'], 'insufficient_evidence')
        self.assertEqual(len(res['citations']), 0)

    # =========================================================================
    # DEDUPLICATION & RE-INDEXING TEST
    # =========================================================================
    def test_reindexing_prevents_duplicate_chunks(self):
        """Re-indexing must purge previous chunks and avoid vector duplication."""
        initial_count = self.vector_store.collection.count()

        # Re-index AC-90 chunks
        ac_chunks = [
            {
                "chunk_id": "AC-OM-01_rev1_0_p2_c1",
                "text": "Code: E17 | AC-90 meaning: High discharge temperature",
                "metadata": {
                    "machine_id": "M-AC90",
                    "document_id": "AC-OM-01",
                    "document_title": "AC 90 Operations and Maintenance Manual",
                    "revision": "1.0",
                    "page_number": 2,
                    "chunk_identifier": "AC-OM-01_rev1_0_p2_c1"
                }
            }
        ]
        self.vector_store.index_chunks(ac_chunks)

        # Confirm count did not blow up with duplicate vectors
        final_count = self.vector_store.collection.count()
        # Old AC-OM-01 chunks (2) were purged, replaced with 1 new chunk
        self.assertEqual(final_count, initial_count - 1)

    # =========================================================================
    # ADDITIONAL TEST 13: All three PDFs discoverable in Manuals/ folder
    # =========================================================================
    def test_all_three_pdfs_discoverable(self):
        """Verify that all 3 required PDF manuals exist in the Manuals/ directory."""
        import os
        from django.conf import settings
        manuals_dir = settings.PROJECT_ROOT / 'Manuals'

        expected_pdfs = [
            'HP200_Operations_Rev1_0.pdf',
            'HP200_Maintenance_Rev1_0.pdf',
            'AC90_Operations_Maintenance_Rev1_0.pdf',
        ]

        for pdf_name in expected_pdfs:
            pdf_path = manuals_dir / pdf_name
            self.assertTrue(
                pdf_path.exists(),
                f"Required PDF not found: {pdf_path}"
            )

    # =========================================================================
    # ADDITIONAL TEST 14: Official Groq API error handled gracefully
    # =========================================================================
    def test_groq_api_error_handled_gracefully(self):
        """
        When official Groq API call fails (e.g. invalid key, timeout, rate limit),
        the system must degrade gracefully — using grounded synthesizer fallback.
        Must never raise an uncaught exception to the user.
        """
        from unittest.mock import patch
        from assistant.rag.generator import RAGGenerator

        generator = RAGGenerator()
        generator.groq_api_key = 'gsk_mock_invalid_groq_key_for_testing'

        passages = [
            {
                "text": "Code: E17 | Meaning: Low hydraulic pressure",
                "machine_id": "M-HP200",
                "document_id": "HP-OPS-01",
                "document_title": "HP 200 Operations Manual",
                "revision": "1.0",
                "page_number": 2,
            }
        ]

        # Patch _call_groq to simulate network timeout / connection refused
        with patch.object(generator, '_call_groq', side_effect=Exception("Connection refused by api.groq.com")):
            result = generator.generate_response('What does E17 mean?', 'M-HP200', passages)

        # Must return a valid structured response
        self.assertIn('status', result)
        self.assertIn(result['status'], ('answered', 'insufficient_evidence'))
        self.assertIn('answer', result)
        self.assertIsInstance(result['citations'], list)

    def test_groq_api_mock_success(self):
        """
        Tests that when official Groq API returns a valid JSON response,
        it is correctly parsed, citations preserved, and provider logged.
        """
        from unittest.mock import patch
        from assistant.rag.generator import RAGGenerator

        generator = RAGGenerator()
        generator.groq_api_key = 'gsk_mock_valid_key'

        passages = [
            {
                "text": "Code: E17 | Meaning: Low hydraulic pressure",
                "machine_id": "M-HP200",
                "document_id": "HP-OPS-01",
                "document_title": "HP 200 Operations Manual",
                "revision": "1.0",
                "page_number": 2,
            }
        ]

        mock_groq_response = {
            "status": "answered",
            "answer": "E17 indicates Low hydraulic pressure on the HP-200 press.",
            "citations": [
                {
                    "document_id": "HP-OPS-01",
                    "title": "HP 200 Operations Manual",
                    "revision": "1.0",
                    "page_number": 2,
                    "passage": "Code: E17 | Meaning: Low hydraulic pressure"
                }
            ],
            "supporting_passages": ["Code: E17 | Meaning: Low hydraulic pressure"],
            "llm_provider": "Official Groq API (llama-3.3-70b-versatile)"
        }

        with patch.object(generator, '_call_groq', return_value=mock_groq_response):
            result = generator.generate_response('What does E17 mean?', 'M-HP200', passages)

        self.assertEqual(result['status'], 'answered')
        self.assertIn('Low hydraulic pressure', result['answer'])
        self.assertEqual(len(result['citations']), 1)
        self.assertEqual(result['citations'][0]['document_id'], 'HP-OPS-01')

    # =========================================================================
    # ADDITIONAL TEST 15: Machine selection required for /api/assistant/ask/
    # =========================================================================
    def test_machine_selection_required_for_ask(self):
        """
        POST to /api/assistant/ask/ with an invalid/nonexistent machine_id
        must return HTTP 400 or 404, not 200.
        """
        self.client.force_authenticate(user=self.engineer1)

        response = self.client.post('/api/assistant/ask/', {
            'machine_id': 'M-INVALID-XYZ',
            'question': 'What does E17 mean?'
        }, format='json')

        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ])

    # =========================================================================
    # ADDITIONAL TEST 16: Citation page numbers match actual extracted pages
    # =========================================================================
    def test_citations_page_numbers_are_positive_integers(self):
        """
        All citations returned by the RAG pipeline must have
        positive integer page_number values (1-based, matching PDF pages).
        """
        # Query HP-200 for E17 (known answer, page 2)
        result = self.rag.answer_question('M-HP200', 'What does E17 mean?')

        if result['status'] == 'answered':
            for citation in result['citations']:
                self.assertIn('page_number', citation)
                page_num = citation['page_number']
                self.assertIsInstance(page_num, int, f"page_number must be int, got {type(page_num)}: {page_num}")
                self.assertGreaterEqual(page_num, 1, f"page_number must be >= 1 (1-based), got {page_num}")

        # Query AC-90 for E17 (known answer, page 2)
        result2 = self.rag.answer_question('M-AC90', 'What does E17 mean?')

        if result2['status'] == 'answered':
            for citation in result2['citations']:
                self.assertIn('page_number', citation)
                page_num = citation['page_number']
                self.assertIsInstance(page_num, int)
                self.assertGreaterEqual(page_num, 1)

    # =========================================================================
    # ADDITIONAL TEST 17: Supervisor Can Mark Questions as Reviewed
    # =========================================================================
    def test_supervisor_can_mark_question_reviewed(self):
        """Supervisor can PATCH a question review status."""
        history_entry = QuestionHistory.objects.create(
            user=self.engineer1,
            selected_machine=self.hp200,
            question="What is the torque for pump bolts?",
            answer="The available manuals do not contain enough information to answer this question.",
            status="insufficient_evidence",
            reviewed=False
        )

        self.client.force_authenticate(user=self.supervisor)
        patch_resp = self.client.patch(
            f'/api/supervisor/questions/{history_entry.id}/review/',
            {'reviewed': True},
            format='json'
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        history_entry.refresh_from_db()
        self.assertTrue(history_entry.reviewed)

    # =========================================================================
    # ADDITIONAL TEST 18: Supervisor Knowledge Gaps Endpoint
    # =========================================================================
    def test_supervisor_knowledge_gaps_endpoint(self):
        """Knowledge gaps endpoint lists unanswered/insufficient evidence queries."""
        QuestionHistory.objects.create(
            user=self.engineer1,
            selected_machine=self.hp200,
            question="What is the pump replacement price?",
            answer="The available manuals do not contain enough information to answer this question.",
            status="insufficient_evidence"
        )
        QuestionHistory.objects.create(
            user=self.engineer2,
            selected_machine=self.hp200,
            question="What does E17 mean?",
            answer="Low hydraulic pressure.",
            status="answered"
        )

        self.client.force_authenticate(user=self.supervisor)
        resp = self.client.get('/api/supervisor/knowledge-gaps/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        # Exactly 1 gap
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'insufficient_evidence')

    # =========================================================================
    # ADDITIONAL TEST 19: Supervisor Can Ask Questions Via Assistant
    # =========================================================================
    def test_supervisor_can_ask_questions(self):
        """Supervisors can query the Assistant endpoint."""
        self.client.force_authenticate(user=self.supervisor)
        response = self.client.post('/api/assistant/ask/', {
            'machine_id': 'M-HP200',
            'question': 'What does E17 mean?'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'answered')

    # =========================================================================
    # ADDITIONAL TEST 20: Machines API Returns Unpaginated List of Exactly 2 Machines
    # =========================================================================
    def test_machines_api_returns_two_registered_machines(self):
        """GET /api/machines/ returns exactly 2 machines: AC-90 and HP-200."""
        self.client.force_authenticate(user=self.engineer1)
        response = self.client.get('/api/machines/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        machines = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(machines), 2)
        machine_ids = {m['machine_id'] for m in machines}
        self.assertIn('M-HP200', machine_ids)
        self.assertIn('M-AC90', machine_ids)
