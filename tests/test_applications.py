from unittest import TestCase
from unittest.mock import patch

from computer import applications


class ApplicationWindowVerificationTests(TestCase):
    def test_windows_calculator_matches_localized_calculator_title(self):
        with patch.object(applications, "_janelas_visiveis", return_value=["Calculadora"]), \
             patch.object(applications.time, "monotonic", return_value=0.0):
            self.assertEqual(
                applications._verificar_janela_aplicativo("Windows Calculator"),
                "Calculadora",
            )

    def test_windows_notepad_matches_dynamic_document_title(self):
        with patch.object(applications, "_janelas_visiveis", return_value=["Untitled - Notepad"]), \
             patch.object(applications.time, "monotonic", return_value=0.0):
            self.assertEqual(
                applications._verificar_janela_aplicativo("Windows Notepad"),
                "Untitled - Notepad",
            )

    def test_task_manager_matches_accented_portuguese_title(self):
        title = "Gerenciador de Tarefas — Administrador"
        with patch.object(applications, "_janelas_visiveis", return_value=[title]), \
             patch.object(applications.time, "monotonic", return_value=0.0):
            self.assertEqual(
                applications._verificar_janela_aplicativo("Task Manager"), title
            )

    def test_command_prompt_alias_does_not_match_arbitrary_cmd_substring(self):
        with patch.object(applications, "_janelas_visiveis", return_value=["My cmd helper"]), \
             patch.object(applications.time, "monotonic", side_effect=[0.0, 3.0]), \
             patch.object(applications.time, "sleep"):
            self.assertIsNone(applications._verificar_janela_aplicativo("cmd"))

    def test_command_prompt_matches_explicit_executable_title(self):
        title = "C:\\Windows\\System32\\cmd.exe - Administrator"
        with patch.object(applications, "_janelas_visiveis", return_value=[title]), \
             patch.object(applications.time, "monotonic", return_value=0.0):
            self.assertEqual(
                applications._verificar_janela_aplicativo("Prompt de comando"), title
            )

    def test_invalid_app_name_is_not_verified(self):
        self.assertIsNone(applications._verificar_janela_aplicativo(None))
        self.assertIsNone(applications._verificar_janela_aplicativo("   "))

    def test_open_app_rejects_non_string_names_without_exception(self):
        for nome in (None, [], {}, 123):
            with self.subTest(nome=nome):
                self.assertEqual(applications.abrir_aplicativo(nome)["status"], "erro")

    def test_uninstall_rejects_non_string_names_without_exception(self):
        for nome in (None, [], {}, 123):
            with self.subTest(nome=nome):
                self.assertEqual(applications.desinstalar_aplicativo(nome)["status"], "erro")


def test_open_application_deduplicates_same_app_across_windows_shortcuts(monkeypatch):
    from computer import applications
    launched = []
    monkeypatch.setattr(applications, "listar_aplicativos", lambda: {
        "status": "ok", "total": 3, "result": [
            {"nome": "Google Chrome", "atalho": r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Google Chrome.lnk", "origem": "Start Menu"},
            {"nome": "Google Chrome", "atalho": r"C:\Users\Public\Desktop\Google Chrome.lnk", "origem": "Desktop"},
            {"nome": "Google Chrome", "atalho": r"shell:AppsFolder\Chrome", "origem": "Windows StartApps"},
        ]
    })
    monkeypatch.setattr(applications.os, "startfile", lambda target: launched.append(target), raising=False)
    monkeypatch.setattr(applications, "_verificar_janela_aplicativo", lambda nome: "Google Chrome")

    result = applications.abrir_aplicativo("google")

    assert result["status"] == "ok"
    assert result["verified"] is True
    assert launched == [r"shell:AppsFolder\Chrome"]


def test_open_application_keeps_ambiguity_for_different_matching_apps(monkeypatch):
    from computer import applications
    monkeypatch.setattr(applications, "listar_aplicativos", lambda: {
        "status": "ok", "total": 2, "result": [
            {"nome": "Google Chrome", "atalho": r"shell:AppsFolder\Chrome", "origem": "Windows StartApps"},
            {"nome": "Google Chrome Beta", "atalho": r"C:\Apps\Chrome Beta.lnk", "origem": "Start Menu"},
        ]
    })
    result = applications.abrir_aplicativo("google")
    assert result["status"] == "ambiguous"
    assert len(result["result"]) == 2
