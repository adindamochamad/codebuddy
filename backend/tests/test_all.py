"""Suite uji komprehensif CodeBuddy.

Jalankan semua:
    pytest tests/ -v

Dengan laporan coverage:
    pytest tests/ --cov=. --cov-report=term-missing --cov-omit="tests/*,.venv/*"

Target: 80%+ code coverage.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import buat_mock_llm


# =========================================================================== #
# 1. OCR SERVICE                                                               #
# =========================================================================== #

class TestOCRFixCommonErrors:
    """Unit test fix_common_ocr_errors — tanpa OCR asli."""

    @pytest.fixture(autouse=True)
    def svc(self):
        from services.ocr_service import CodeOCRService
        self.svc = CodeOCRService()

    def test_prin_to_print(self):
        assert self.svc.fix_common_ocr_errors('prin("x")') == 'print("x")'

    def test_printt_to_print(self):
        assert self.svc.fix_common_ocr_errors('printt("x")') == 'print("x")'

    def test_semicolon_to_colon_if(self):
        result = self.svc.fix_common_ocr_errors("if x > 0;")
        assert result == "if x > 0:"

    def test_semicolon_to_colon_for(self):
        result = self.svc.fix_common_ocr_errors("for i in range(10);")
        assert result == "for i in range(10):"

    def test_semicolon_to_colon_while(self):
        result = self.svc.fix_common_ocr_errors("while True;")
        assert result == "while True:"

    def test_semicolon_to_colon_def(self):
        result = self.svc.fix_common_ocr_errors("def fungsi();")
        assert result == "def fungsi():"

    def test_de_f_keyword(self):
        result = self.svc.fix_common_ocr_errors("de f hitung():")
        assert result == "def hitung():"

    def test_zero_vs_o_in_expression(self):
        result = self.svc.fix_common_ocr_errors("x = O + 1")
        assert "0" in result

    def test_tab_to_spaces(self):
        result = self.svc.fix_common_ocr_errors("\tx = 1")
        assert result.startswith("    ")

    def test_smart_quotes_converted_to_straight(self):
        # U+2018 kiri, U+2019 kanan → diganti kutip lurus U+0027
        curly = "‘hello’"
        result = self.svc.fix_common_ocr_errors(curly)
        assert chr(0x27) in result  # U+0027 straight single quote

    def test_no_change_for_clean_code(self):
        kode = "print('halo')"
        assert self.svc.fix_common_ocr_errors(kode) == kode


class TestOCRCalculateConfidence:

    @pytest.fixture(autouse=True)
    def svc(self):
        from services.ocr_service import CodeOCRService
        self.svc = CodeOCRService()

    def test_empty_lines(self):
        assert self.svc.calculate_confidence([]) == 0.0

    def test_single_line_perfect(self):
        lines = [{"text": "print(x)", "confidence": 1.0}]
        assert self.svc.calculate_confidence(lines) == 1.0

    def test_weighted_average_long_line_dominates(self):
        lines = [
            {"text": "print('halo dunia')", "confidence": 0.95},
            {"text": "x", "confidence": 0.10},
        ]
        result = self.svc.calculate_confidence(lines)
        assert result > 0.5, "Baris panjang harus lebih berpengaruh"

    def test_multiple_lines(self):
        lines = [
            {"text": "for i in range(10):", "confidence": 0.9},
            {"text": "    print(i)", "confidence": 0.8},
        ]
        result = self.svc.calculate_confidence(lines)
        assert 0.0 < result < 1.0


class TestOCRReconstructCode:

    @pytest.fixture(autouse=True)
    def svc(self):
        from services.ocr_service import CodeOCRService
        self.svc = CodeOCRService()

    def _box(self, x, y):
        return [[x, y], [x+100, y], [x+100, y+20], [x, y+20]]

    def test_empty_lines(self):
        assert self.svc.reconstruct_code([]) == ""

    def test_single_line_no_indent(self):
        lines = [{"text": "print('halo')", "confidence": 0.9, "box": self._box(0, 0)}]
        result = self.svc.reconstruct_code(lines)
        assert "print('halo')" in result

    def test_sorted_by_y_position(self):
        lines = [
            {"text": "baris_dua", "confidence": 0.9, "box": self._box(0, 30)},
            {"text": "baris_satu", "confidence": 0.9, "box": self._box(0, 0)},
        ]
        result = self.svc.reconstruct_code(lines)
        assert result.index("baris_satu") < result.index("baris_dua")

    def test_indentation_from_x_position(self):
        lines = [
            {"text": "def f():", "confidence": 0.9, "box": self._box(0, 0)},
            {"text": "return 1", "confidence": 0.9, "box": self._box(80, 30)},
        ]
        result = self.svc.reconstruct_code(lines)
        baris = result.split("\n")
        assert baris[0].startswith("def f():")
        assert baris[1].startswith("    ")  # ada indentasi

    def test_applies_ocr_fixes(self):
        lines = [{"text": "prin('halo')", "confidence": 0.9, "box": self._box(0, 0)}]
        result = self.svc.reconstruct_code(lines)
        assert "print(" in result


class TestOCRExtractCode:

    def test_file_not_found(self):
        from services.ocr_service import CodeOCRService, LayananOCRError
        svc = CodeOCRService()
        with pytest.raises(LayananOCRError, match="tidak ditemukan"):
            svc.extract_code("/tmp/tidak_ada_sama_sekali_xyz.png")

    def test_extract_with_mock_ocr(self, tmp_path):
        """Extract dengan PaddleOCR di-mock langsung via _ocr attribute."""
        cv2 = pytest.importorskip("cv2", reason="opencv tidak terpasang (paket OCR opsional)")
        import numpy as np
        from services.ocr_service import CodeOCRService

        # Buat gambar putih sederhana
        img = np.ones((60, 300, 3), dtype=np.uint8) * 255
        img_path = str(tmp_path / "test_code.png")
        cv2.imwrite(img_path, img)

        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = [[
            [[[0, 0], [200, 0], [200, 20], [0, 20]], ("print('halo')", 0.95)],
            [[[0, 25], [200, 25], [200, 45], [0, 25]], ("x = 42", 0.90)],
        ]]

        svc = CodeOCRService()
        svc._ocr = mock_ocr  # inject mock langsung

        hasil = svc.extract_code(img_path)

        assert hasil["confidence"] > 0
        assert len(hasil["raw_lines"]) == 2
        assert "print" in hasil["code"]
        mock_ocr.ocr.assert_called_once()

    def test_extract_empty_ocr_result(self, tmp_path):
        """OCR tidak mendeteksi teks → kembalikan code kosong."""
        cv2 = pytest.importorskip("cv2", reason="opencv tidak terpasang (paket OCR opsional)")
        import numpy as np
        from services.ocr_service import CodeOCRService

        img = np.zeros((60, 300, 3), dtype=np.uint8)
        img_path = str(tmp_path / "blank.png")
        cv2.imwrite(img_path, img)

        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = [None]

        svc = CodeOCRService()
        svc._ocr = mock_ocr
        hasil = svc.extract_code(img_path)

        assert hasil["code"] == ""
        assert hasil["confidence"] == 0.0


# =========================================================================== #
# 2. CODE EXECUTOR                                                             #
# =========================================================================== #

class TestSafeCodeExecutorSuccess:

    @pytest.fixture(autouse=True)
    def ex(self):
        from services.code_executor import SafeCodeExecutor
        self.ex = SafeCodeExecutor()

    def test_print_string(self):
        h = self.ex.execute('print("halo dunia")')
        assert h["success"] is True
        assert "halo dunia" in h["output"]

    def test_math_operations(self):
        h = self.ex.execute("print(2 + 3 * 4)")
        assert h["success"] is True
        assert "14" in h["output"]

    def test_for_loop(self):
        h = self.ex.execute("for i in range(3):\n    print(i)")
        assert h["success"] is True
        assert "0" in h["output"] and "2" in h["output"]

    def test_list_operations(self):
        h = self.ex.execute("lst = [1,2,3]\nprint(sum(lst))")
        assert h["success"] is True
        assert "6" in h["output"]

    def test_function_definition_and_call(self):
        h = self.ex.execute("def tambah(a,b):\n    return a+b\nprint(tambah(3,4))")
        assert h["success"] is True
        assert "7" in h["output"]

    def test_string_methods(self):
        h = self.ex.execute("print('halo'.upper())")
        assert h["success"] is True
        assert "HALO" in h["output"]

    def test_execution_time_is_float(self):
        h = self.ex.execute("print(1+1)")
        assert isinstance(h["execution_time"], float)
        assert h["execution_time"] >= 0

    def test_inplace_operator(self):
        h = self.ex.execute("x = 5\nx += 3\nprint(x)")
        assert h["success"] is True
        assert "8" in h["output"]


class TestSafeCodeExecutorErrors:

    @pytest.fixture(autouse=True)
    def ex(self):
        from services.code_executor import SafeCodeExecutor
        self.ex = SafeCodeExecutor()

    def test_syntax_error(self):
        h = self.ex.execute("def f(")
        assert h["success"] is False
        assert h["error_type"] == "SyntaxError"
        assert h["error"] is not None

    def test_name_error_indonesian_message(self):
        h = self.ex.execute("print(variabel_xyz)")
        assert h["success"] is False
        assert h["error_type"] == "NameError"
        assert "variabel_xyz" in h["error"]

    def test_type_error(self):
        h = self.ex.execute('print("a" + 1)')
        assert h["success"] is False
        assert h["error_type"] == "TypeError"

    def test_zero_division_error(self):
        h = self.ex.execute("print(1/0)")
        assert h["success"] is False
        assert h["error_type"] == "ZeroDivisionError"
        assert "nol" in h["error"]

    def test_index_error(self):
        h = self.ex.execute("a=[1,2]\nprint(a[99])")
        assert h["success"] is False
        assert h["error_type"] == "IndexError"

    def test_key_error(self):
        h = self.ex.execute("d={}\nprint(d['kunci'])")
        assert h["success"] is False
        assert h["error_type"] == "KeyError"

    def test_too_long_code(self):
        from services.code_executor import SafeCodeExecutor
        ex = SafeCodeExecutor(max_code_length=5)
        h = ex.execute("print('halo')")
        assert h["success"] is False
        assert h["error_type"] == "ValidationError"

    def test_partial_output_on_runtime_error(self):
        kode = 'print("baris pertama")\nprint(1/0)'
        h = self.ex.execute(kode)
        assert h["success"] is False
        assert "baris pertama" in h["output"]


class TestSafeCodeExecutorSecurity:

    @pytest.fixture(autouse=True)
    def ex(self):
        from services.code_executor import SafeCodeExecutor
        self.ex = SafeCodeExecutor()

    def test_import_blocked(self):
        h = self.ex.execute("import os")
        assert h["success"] is False

    def test_open_blocked(self):
        h = self.ex.execute("open('/etc/passwd')")
        assert h["success"] is False

    def test_eval_blocked(self):
        h = self.ex.execute("eval('1+1')")
        assert h["success"] is False

    def test_exec_blocked(self):
        h = self.ex.execute("exec('x=1')")
        assert h["success"] is False

    def test_timeout(self):
        from services.code_executor import SafeCodeExecutor
        ex = SafeCodeExecutor(timeout=1)
        h = ex.execute("while True:\n    pass")
        assert h["success"] is False
        assert h["error_type"] == "TimeoutError"
        assert "timeout" in h["error"].lower()


class TestSafeCodeExecutorValidateSyntax:

    @pytest.fixture(autouse=True)
    def ex(self):
        from services.code_executor import SafeCodeExecutor
        self.ex = SafeCodeExecutor()

    def test_valid_code(self):
        result = self.ex.validate_syntax("x = 1 + 1")
        assert result["valid"] is True
        assert result["error"] is None
        assert result["line"] is None

    def test_invalid_syntax(self):
        result = self.ex.validate_syntax("def broken(")
        assert result["valid"] is False
        assert result["line"] is not None
        assert result["error"] is not None

    def test_complex_valid_code(self):
        kode = "def f(x):\n    return x * 2\nprint(f(5))"
        assert self.ex.validate_syntax(kode)["valid"] is True


# =========================================================================== #
# 3. LLM SERVICE                                                               #
# =========================================================================== #

class TestGemmaServicePrompts:

    @pytest.fixture(autouse=True)
    def svc(self):
        from services.llm_service import GemmaService
        self.svc = GemmaService()

    def test_analyze_prompt_beginner_contains_keywords(self):
        p = self.svc._build_analyze_prompt("print(x)", None, "beginner")
        assert "pemula" in p
        assert "JSON" in p
        assert "print(x)" in p

    def test_analyze_prompt_advanced(self):
        p = self.svc._build_analyze_prompt("x=1", None, "advanced")
        assert "lanjut" in p

    def test_analyze_prompt_includes_error(self):
        err = {"type": "NameError", "message": "x not defined"}
        p = self.svc._build_analyze_prompt("print(x)", err, "beginner")
        assert "NameError" in p

    def test_analyze_prompt_intermediate(self):
        p = self.svc._build_analyze_prompt("x=1", None, "intermediate")
        assert "menengah" in p

    def test_exercise_prompt_beginner(self):
        p = self.svc._build_exercise_prompt("loop", "beginner")
        assert "loop" in p
        assert "sangat mudah" in p

    def test_exercise_prompt_advanced(self):
        p = self.svc._build_exercise_prompt("rekursi", "advanced")
        assert "menantang" in p

    def test_exercise_prompt_contains_json_format(self):
        p = self.svc._build_exercise_prompt("variabel", "beginner")
        assert "title" in p
        assert "starter_code" in p


class TestGemmaServiceParseJSON:

    @pytest.fixture(autouse=True)
    def svc(self):
        from services.llm_service import GemmaService
        self.svc = GemmaService()

    def test_parse_direct_json(self):
        r = self.svc._parse_json_response('{"understanding": "test"}')
        assert r == {"understanding": "test"}

    def test_parse_markdown_json_block(self):
        resp = '```json\n{"understanding": "loop"}\n```'
        r = self.svc._parse_json_response(resp)
        assert r == {"understanding": "loop"}

    def test_parse_markdown_no_lang(self):
        resp = '```\n{"understanding": "fungsi"}\n```'
        r = self.svc._parse_json_response(resp)
        assert r == {"understanding": "fungsi"}

    def test_parse_json_inside_text(self):
        resp = 'Berikut hasilnya: {"understanding": "variabel"} selesai.'
        r = self.svc._parse_json_response(resp)
        assert r == {"understanding": "variabel"}

    def test_parse_fallback_on_invalid(self):
        r = self.svc._parse_json_response("bukan json sama sekali !!!")
        assert "error" in r
        assert "raw_response" in r

    def test_parse_empty_string(self):
        r = self.svc._parse_json_response("")
        assert "error" in r


class TestGemmaServiceCallOllama:

    @pytest.fixture(autouse=True)
    def svc(self):
        from services.llm_service import GemmaService
        self.svc = GemmaService()

    async def test_call_ollama_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": '{"understanding": "ok"}'},
            "done": True,
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await self.svc._call_ollama("prompt test")
            assert '{"understanding": "ok"}' in result

    async def test_call_ollama_retries_on_connection_error(self):
        import httpx
        from services.llm_service import LayananLLMError

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("no conn"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(LayananLLMError):
                await self.svc._call_ollama("prompt test")

            assert mock_client.post.call_count == 3  # retry 3 kali

    async def test_analyze_code_calls_ollama_and_parses(self, ai_feedback_sukses):
        # Mock kedua metode: structured (primary) dan fallback
        self.svc._call_ollama_structured = AsyncMock(return_value=ai_feedback_sukses)
        self.svc._call_ollama = AsyncMock(return_value=json.dumps(ai_feedback_sukses))
        result = await self.svc.analyze_code("print(x)", student_level="beginner")
        assert result["encouragement"] == ai_feedback_sukses["encouragement"]

    async def test_generate_exercise_calls_ollama(self):
        exercise = {"title": "Latihan", "instructions": "...", "starter_code": "", "solution": "", "test_cases": []}
        self.svc._call_ollama_structured = AsyncMock(return_value=exercise)
        self.svc._call_ollama = AsyncMock(return_value=json.dumps(exercise))
        result = await self.svc.generate_exercise("loop")
        assert result["title"] == "Latihan"


# =========================================================================== #
# 4. AGENT WORKFLOW                                                            #
# =========================================================================== #

class TestErrorDetector:

    @pytest.fixture(autouse=True)
    def det(self):
        from services.agent_service import ErrorDetector
        self.det = ErrorDetector()

    @pytest.mark.parametrize("error_type,expected_cat", [
        ("NameError", "runtime"),
        ("SyntaxError", "syntax"),
        ("IndentationError", "syntax"),
        ("TypeError", "runtime"),
        ("ZeroDivisionError", "runtime"),
        ("IndexError", "runtime"),
        ("KeyError", "runtime"),
        ("TimeoutError", "timeout"),
        ("SecurityError", "security"),
        (None, "runtime"),
        ("TidakAda", "runtime"),
    ])
    def test_detect_category(self, error_type, expected_cat):
        info = self.det.detect(error_type, "pesan test")
        assert info.category == expected_cat

    def test_detect_returns_error_info_dict(self):
        info = self.det.detect("NameError", "x not defined")
        d = info.to_dict()
        assert all(k in d for k in ["type", "message_raw", "category", "message_id", "suggestion"])

    def test_classify_success(self):
        from services.agent_service import _buat_attempt, _STAGE_EXEC, _STAGE_SUCCESS
        attempts = [
            _buat_attempt(_STAGE_EXEC, True),
            _buat_attempt(_STAGE_SUCCESS, True),
        ]
        assert self.det.classify_final_result(attempts) == "success"

    def test_classify_syntax_error(self):
        from services.agent_service import _buat_attempt, _STAGE_SYNTAX, _STAGE_ANALYSIS
        attempts = [
            _buat_attempt(_STAGE_SYNTAX, False, error={"type": "SyntaxError", "category": "syntax", "message_id": "", "message_raw": "", "suggestion": ""}),
            _buat_attempt(_STAGE_ANALYSIS, False, error={"type": "SyntaxError", "category": "syntax", "message_id": "", "message_raw": "", "suggestion": ""}),
        ]
        assert self.det.classify_final_result(attempts) == "syntax_error"

    def test_classify_timeout(self):
        from services.agent_service import _buat_attempt, _STAGE_EXEC
        attempts = [_buat_attempt(_STAGE_EXEC, False, error={"type": "TimeoutError", "category": "timeout", "message_id": "", "message_raw": "", "suggestion": ""})]
        assert self.det.classify_final_result(attempts) == "timeout"

    def test_classify_runtime_error(self):
        from services.agent_service import _buat_attempt, _STAGE_EXEC
        attempts = [_buat_attempt(_STAGE_EXEC, False, error={"type": "NameError", "category": "runtime", "message_id": "", "message_raw": "", "suggestion": ""})]
        assert self.det.classify_final_result(attempts) == "runtime_error"


class TestCodeBuddyAgentSession:

    async def test_success_path(self, ai_feedback_sukses):
        from services.agent_service import CodeBuddyAgent
        agent = CodeBuddyAgent(llm=buat_mock_llm(ai_feedback_sukses))
        sesi = await agent.tutor_session("print('halo')", student_id=1)

        assert sesi["final_result"] == "success"
        assert sesi["student_id"] == 1
        stages = [a["stage"] for a in sesi["attempts"]]
        assert "syntax_validation" in stages
        assert "execution" in stages
        assert "success_analysis" in stages

    async def test_syntax_error_path(self, ai_feedback_error):
        from services.agent_service import CodeBuddyAgent
        agent = CodeBuddyAgent(llm=buat_mock_llm(ai_feedback_error))
        sesi = await agent.tutor_session("def f(", student_id=2)

        assert sesi["final_result"] == "syntax_error"
        stages = [a["stage"] for a in sesi["attempts"]]
        assert "error_analysis" in stages

    async def test_runtime_error_path(self, ai_feedback_error):
        from services.agent_service import CodeBuddyAgent
        agent = CodeBuddyAgent(llm=buat_mock_llm(ai_feedback_error))
        sesi = await agent.tutor_session("print(variabel_xyz)", student_id=3)

        assert sesi["final_result"] == "runtime_error"

    async def test_llm_fallback_when_unavailable(self):
        from services.agent_service import CodeBuddyAgent
        from services.llm_service import LayananLLMError

        mock_llm = MagicMock()
        mock_llm.analyze_code = AsyncMock(side_effect=LayananLLMError("Ollama offline"))

        agent = CodeBuddyAgent(llm=mock_llm)
        sesi = await agent.tutor_session("print('halo')", student_id=4)

        # Harus tetap selesai, bukan crash
        assert "final_result" in sesi
        last = sesi["attempts"][-1]
        assert last["ai_feedback"]["encouragement"] != ""  # fallback punya encouragement

    async def test_exercise_id_preserved(self, ai_feedback_sukses):
        from services.agent_service import CodeBuddyAgent
        agent = CodeBuddyAgent(llm=buat_mock_llm(ai_feedback_sukses))
        sesi = await agent.tutor_session("print(1)", student_id=1, exercise_id="hello_print")
        assert sesi["exercise_id"] == "hello_print"

    async def test_student_level_preserved(self, ai_feedback_sukses):
        from services.agent_service import CodeBuddyAgent
        agent = CodeBuddyAgent(llm=buat_mock_llm(ai_feedback_sukses))
        sesi = await agent.tutor_session("print(1)", student_id=1, student_level="advanced")
        assert sesi["student_level"] == "advanced"


class TestCodeBuddyAgentHint:

    async def test_hint_level_1(self):
        from services.agent_service import CodeBuddyAgent

        with patch("services.agent_service.kirim_chat_tutor", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {"reply": "Apa yang seharusnya terjadi?"}
            agent = CodeBuddyAgent()
            hint = await agent.get_progressive_hint("print(x)", "NameError", hint_level=1)
            assert len(hint) > 0

    async def test_hint_level_clamp(self):
        from services.agent_service import CodeBuddyAgent
        from services.llm_service import LayananLLMError

        with patch("services.agent_service.kirim_chat_tutor", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = LayananLLMError("offline")
            agent = CodeBuddyAgent()
            hint = await agent.get_progressive_hint("x", "err", hint_level=99)
            assert len(hint) > 0  # Fallback aktif

    async def test_hint_fallback_when_llm_down(self):
        from services.agent_service import CodeBuddyAgent, _HINT_FALLBACK
        from services.llm_service import LayananLLMError

        with patch("services.agent_service.kirim_chat_tutor", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = LayananLLMError("down")
            agent = CodeBuddyAgent()
            hint = await agent.get_progressive_hint("x=1", "err", hint_level=2)
            assert hint == _HINT_FALLBACK[2]

    def test_prompt_level1_no_solution(self):
        from services.agent_service import CodeBuddyAgent
        prompt = CodeBuddyAgent._buat_prompt_hint("print(x)", "NameError", 1, "beginner")
        assert "pertanyaan" in prompt.lower() or "Jangan" in prompt

    def test_prompt_level3_has_solution(self):
        from services.agent_service import CodeBuddyAgent
        prompt = CodeBuddyAgent._buat_prompt_hint("print(x)", "NameError", 3, "beginner")
        assert "SOLUSI" in prompt or "solusi" in prompt.lower()


# =========================================================================== #
# 5. API ROUTES                                                                #
# =========================================================================== #

class TestHealthRoutes:

    def test_health_ok(self, klien_http: TestClient):
        r = klien_http.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_root_has_docs(self, klien_http: TestClient):
        r = klien_http.get("/")
        assert r.status_code == 200
        assert "docs" in r.json()


class TestOCRRoutes:

    def test_extract_invalid_content_type(self, klien_http: TestClient):
        r = klien_http.post(
            "/api/ocr/extract",
            files={"berkas": ("test.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400

    def test_extract_empty_file(self, klien_http: TestClient):
        r = klien_http.post(
            "/api/ocr/extract",
            files={"berkas": ("test.jpg", b"", "image/jpeg")},
        )
        assert r.status_code == 400

    def test_extract_too_large(self, klien_http: TestClient):
        big = b"x" * (5 * 1024 * 1024 + 1)
        r = klien_http.post(
            "/api/ocr/extract",
            files={"berkas": ("big.jpg", big, "image/jpeg")},
        )
        assert r.status_code == 413

    def test_extract_valid_image_mocked(self, klien_http: TestClient, tmp_path):
        """Kirim gambar asli dengan OCR di-mock."""
        cv2 = pytest.importorskip("cv2", reason="opencv tidak terpasang (paket OCR opsional)")
        import numpy as np

        img = np.ones((60, 300, 3), dtype=np.uint8) * 255
        img_path = tmp_path / "code.png"
        cv2.imwrite(str(img_path), img)
        img_bytes = img_path.read_bytes()

        mock_svc = MagicMock()
        mock_svc.extract_code.return_value = {
            "code": "print('halo')",
            "confidence": 0.95,
            "raw_lines": [],
        }

        with patch("api.routes.CodeOCRService", return_value=mock_svc):
            r = klien_http.post(
                "/api/ocr/extract",
                files={"berkas": ("code.png", img_bytes, "image/png")},
            )

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["confidence"] == 0.95


class TestCodeRoutes:

    def test_execute_valid_code(self, klien_http: TestClient):
        r = klien_http.post("/api/code/execute", json={"kode": "print('halo')"})
        assert r.status_code == 200
        assert r.json()["sukses"] is True
        assert "halo" in r.json()["stdout"]

    def test_execute_syntax_error(self, klien_http: TestClient):
        r = klien_http.post("/api/code/execute", json={"kode": "def f("})
        assert r.status_code == 200
        assert r.json()["sukses"] is False

    def test_execute_runtime_error(self, klien_http: TestClient):
        r = klien_http.post("/api/code/execute", json={"kode": "print(xyz_belum_ada)"})
        assert r.status_code == 200
        assert r.json()["sukses"] is False

    def test_execute_empty_code_rejected(self, klien_http: TestClient):
        r = klien_http.post("/api/code/execute", json={"kode": ""})
        assert r.status_code == 422  # Pydantic validation error

    def test_validate_valid_code(self, klien_http: TestClient):
        r = klien_http.post("/api/code/validate", json={"kode": "x = 1 + 1"})
        assert r.status_code == 200
        assert r.json()["valid"] is True
        assert r.json()["error"] is None

    def test_validate_invalid_code(self, klien_http: TestClient):
        r = klien_http.post("/api/code/validate", json={"kode": "def broken("})
        assert r.status_code == 200
        assert r.json()["valid"] is False
        assert r.json()["line"] is not None


class TestAgentRoutes:

    def test_agent_tutor_success_path(self, klien_http: TestClient, ai_feedback_sukses):
        with patch("api.routes.code_buddy_agent") as mock_agent:
            mock_agent.tutor_session = AsyncMock(return_value={
                "student_id": 1,
                "exercise_id": None,
                "original_code": "print(1)",
                "student_level": "beginner",
                "attempts": [
                    {"stage": "syntax_validation", "success": True, "output": "", "error": None, "ai_feedback": None},
                    {"stage": "execution", "success": True, "output": "1\n", "error": None, "ai_feedback": None},
                    {"stage": "success_analysis", "success": True, "output": "1\n", "error": None, "ai_feedback": ai_feedback_sukses},
                ],
                "final_result": "success",
            })

            r = klien_http.post("/api/agent/tutor", json={
                "code": "print(1)", "student_id": 1,
            })

        assert r.status_code == 200
        body = r.json()
        assert body["final_result"] == "success"
        assert len(body["attempts"]) == 3

    def test_agent_tutor_missing_student_id(self, klien_http: TestClient):
        r = klien_http.post("/api/agent/tutor", json={"code": "print(1)"})
        assert r.status_code == 422

    def test_hint_valid_request(self, klien_http: TestClient):
        with patch("api.routes.code_buddy_agent") as mock_agent:
            mock_agent.get_progressive_hint = AsyncMock(return_value="Coba pikirkan lagi!")
            r = klien_http.post("/api/agent/hint", json={
                "code": "print(x)", "error": "NameError", "hint_level": 1,
            })
        assert r.status_code == 200
        assert r.json()["hint"] == "Coba pikirkan lagi!"
        assert r.json()["hint_level"] == 1

    def test_hint_level_out_of_range(self, klien_http: TestClient):
        r = klien_http.post("/api/agent/hint", json={
            "code": "x", "error": "err", "hint_level": 0,
        })
        assert r.status_code == 422

    def test_hint_missing_error_field(self, klien_http: TestClient):
        r = klien_http.post("/api/agent/hint", json={
            "code": "x", "hint_level": 1,
        })
        assert r.status_code == 422


class TestStudentRoutes:

    def test_create_student_success(self, klien_http: TestClient):
        r = klien_http.post("/api/students/", json={"name": "Test Uji", "age": 15})
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Test Uji"
        assert body["id"] > 0

    def test_create_student_no_name(self, klien_http: TestClient):
        r = klien_http.post("/api/students/", json={"age": 15})
        assert r.status_code == 422

    def test_create_student_empty_name(self, klien_http: TestClient):
        r = klien_http.post("/api/students/", json={"name": ""})
        assert r.status_code == 422

    def test_get_progress_not_found(self, klien_http: TestClient):
        r = klien_http.get("/api/students/999999/progress")
        assert r.status_code == 404

    def test_get_progress_returns_structure(self, klien_http: TestClient):
        # Buat siswa dulu
        create_r = klien_http.post("/api/students/", json={"name": "Siswa Progress"})
        sid = create_r.json()["id"]

        r = klien_http.get(f"/api/students/{sid}/progress")
        assert r.status_code == 200
        body = r.json()
        assert body["student_id"] == sid
        assert "latihan" in body
        assert "total_selesai" in body


class TestExerciseRoutes:

    def test_list_all_exercises(self, klien_http: TestClient):
        r = klien_http.get("/api/exercises/")
        assert r.status_code == 200
        body = r.json()
        assert "total" in body
        assert "latihan" in body
        assert body["total"] >= 1

    def test_list_filter_beginner(self, klien_http: TestClient):
        r = klien_http.get("/api/exercises/?difficulty=beginner")
        assert r.status_code == 200
        for item in r.json()["latihan"]:
            assert item["difficulty"] == "beginner"

    def test_list_filter_no_results(self, klien_http: TestClient):
        r = klien_http.get("/api/exercises/?difficulty=unknown_level")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_generate_exercise_success(self, klien_http: TestClient):
        exercise_data = {
            "title": "Latihan Variabel",
            "instructions": "Buat variabel nama",
            "starter_code": "nama = ",
            "solution": 'nama = "Budi"',
            "test_cases": [],
        }
        with patch("api.routes.gemma_service") as mock_svc:
            mock_svc.generate_exercise = AsyncMock(return_value=exercise_data)
            r = klien_http.post("/api/exercises/generate", json={
                "topic": "variabel", "difficulty": "beginner",
            })

        assert r.status_code == 200
        assert r.json()["title"] == "Latihan Variabel"

    def test_generate_exercise_llm_unavailable(self, klien_http: TestClient):
        from services.llm_service import LayananLLMError
        with patch("api.routes.gemma_service") as mock_svc:
            mock_svc.generate_exercise = AsyncMock(side_effect=LayananLLMError("down"))
            r = klien_http.post("/api/exercises/generate", json={
                "topic": "loop", "difficulty": "beginner",
            })
        assert r.status_code == 502


# =========================================================================== #
# 6. DATABASE CRUD                                                             #
# =========================================================================== #

class TestCRUDStudent:

    async def test_create_and_get(self, mem_db: AsyncSession):
        from models.crud import create_student, get_student
        s = await create_student(mem_db, name="Budi", age=14)
        assert s.id is not None
        assert s.name == "Budi"
        assert s.level == "beginner"

        s2 = await get_student(mem_db, s.id)
        assert s2 is not None
        assert s2.name == "Budi"

    async def test_get_not_found(self, mem_db: AsyncSession):
        from models.crud import get_student
        assert await get_student(mem_db, 99999) is None

    async def test_list_students(self, mem_db: AsyncSession):
        from models.crud import create_student, list_students
        await create_student(mem_db, name="A")
        await create_student(mem_db, name="B")
        daftar = await list_students(mem_db)
        assert len(daftar) >= 2

    async def test_update_level(self, mem_db: AsyncSession):
        from models.crud import create_student, update_student_level
        s = await create_student(mem_db, name="Siti", level="beginner")
        s2 = await update_student_level(mem_db, s.id, "advanced")
        assert s2.level == "advanced"

    async def test_update_level_not_found(self, mem_db: AsyncSession):
        from models.crud import update_student_level
        assert await update_student_level(mem_db, 99999, "advanced") is None


class TestCRUDSubmission:

    async def test_create_submission_agent_format(self, mem_db: AsyncSession):
        from models.crud import create_student, create_submission
        s = await create_student(mem_db, name="X")
        sub = await create_submission(mem_db, s.id, "print(1)", {"final_result": "success"})
        assert sub.score == 100.0
        assert sub.id is not None

    async def test_create_submission_executor_format(self, mem_db: AsyncSession):
        from models.crud import create_student, create_submission
        s = await create_student(mem_db, name="Y")
        sub = await create_submission(mem_db, s.id, "print(x)", {"success": False})
        assert sub.score == 30.0

    async def test_create_submission_with_errors(self, mem_db: AsyncSession):
        from models.crud import create_student, create_submission
        s = await create_student(mem_db, name="Z")
        result = {
            "final_result": "runtime_error",
            "attempts": [
                {"stage": "error_analysis", "success": False,
                 "error": {"type": "NameError", "message_id": "...", "message_raw": "", "category": "runtime", "suggestion": ""},
                 "ai_feedback": {"errors": [{"line": 1, "explanation": "err", "fix": "x=1"}], "corrected_code": "x=1\nprint(x)"}}
            ],
        }
        sub = await create_submission(mem_db, s.id, "print(x)", result)
        assert sub.score == 40.0

    async def test_get_submissions_ordered(self, mem_db: AsyncSession):
        from models.crud import create_student, create_submission, get_student_submissions
        s = await create_student(mem_db, name="W")
        await create_submission(mem_db, s.id, "print(1)", {"success": True})
        await create_submission(mem_db, s.id, "print(2)", {"success": False})
        subs = await get_student_submissions(mem_db, s.id, limit=5)
        assert len(subs) == 2

    async def test_get_submissions_limit(self, mem_db: AsyncSession):
        from models.crud import create_student, create_submission, get_student_submissions
        s = await create_student(mem_db, name="V")
        for i in range(5):
            await create_submission(mem_db, s.id, f"print({i})", {"success": True})
        subs = await get_student_submissions(mem_db, s.id, limit=3)
        assert len(subs) == 3


class TestCRUDProgress:

    async def test_update_progress_insert(self, mem_db: AsyncSession):
        from models.crud import create_student, update_progress
        s = await create_student(mem_db, name="P1")
        p = await update_progress(mem_db, s.id, "hello_print", score=85.0)
        assert p.attempts == 1
        assert p.avg_score == 85.0
        assert p.completed is True  # >= 70

    async def test_update_progress_not_completed_below_threshold(self, mem_db: AsyncSession):
        from models.crud import create_student, update_progress
        s = await create_student(mem_db, name="P2")
        p = await update_progress(mem_db, s.id, "loop_bintang", score=60.0)
        assert p.completed is False

    async def test_update_progress_upsert_moving_average(self, mem_db: AsyncSession):
        from models.crud import create_student, update_progress
        s = await create_student(mem_db, name="P3")
        await update_progress(mem_db, s.id, "loop_sum", score=80.0)
        p2 = await update_progress(mem_db, s.id, "loop_sum", score=60.0)
        assert p2.attempts == 2
        expected = round((80.0 + 60.0) / 2, 2)
        assert abs(p2.avg_score - expected) < 0.01

    async def test_update_progress_becomes_completed_on_good_score(self, mem_db: AsyncSession):
        from models.crud import create_student, update_progress
        s = await create_student(mem_db, name="P4")
        p1 = await update_progress(mem_db, s.id, "variabel_nama", score=60.0)
        assert p1.completed is False
        p2 = await update_progress(mem_db, s.id, "variabel_nama", score=90.0)
        assert p2.completed is True

    async def test_get_progress_existing(self, mem_db: AsyncSession):
        from models.crud import create_student, update_progress, get_progress
        s = await create_student(mem_db, name="P5")
        await update_progress(mem_db, s.id, "ex01", score=75.0)
        p = await get_progress(mem_db, s.id, "ex01")
        assert p is not None and p.attempts == 1

    async def test_get_progress_not_existing(self, mem_db: AsyncSession):
        from models.crud import create_student, get_progress
        s = await create_student(mem_db, name="P6")
        assert await get_progress(mem_db, s.id, "tidak_ada") is None


class TestCRUDStats:

    async def test_stats_empty_student(self, mem_db: AsyncSession):
        from models.crud import create_student, get_student_stats
        s = await create_student(mem_db, name="Stats0")
        stats = await get_student_stats(mem_db, s.id)
        assert stats["total_submissions"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["exercises_attempted"] == 0

    async def test_stats_with_data(self, mem_db: AsyncSession):
        from models.crud import create_student, create_submission, update_progress, get_student_stats
        s = await create_student(mem_db, name="Stats1")
        await create_submission(mem_db, s.id, "print(1)", {"final_result": "success"})   # score 100
        await create_submission(mem_db, s.id, "print(x)", {"final_result": "runtime_error"})  # score 40
        await update_progress(mem_db, s.id, "hello_print", score=90.0)
        await update_progress(mem_db, s.id, "loop_bintang", score=65.0)

        stats = await get_student_stats(mem_db, s.id)
        assert stats["total_submissions"] == 2
        assert stats["success_rate"] == 50.0   # 1/2 submission score >= 70
        assert stats["exercises_completed"] == 1  # only hello_print >= 70
        assert stats["exercises_attempted"] == 2

    async def test_stats_not_found(self, mem_db: AsyncSession):
        from models.crud import get_student_stats
        stats = await get_student_stats(mem_db, 99999)
        assert stats == {}
