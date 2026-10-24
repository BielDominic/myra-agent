from unittest import TestCase
from unittest.mock import Mock, patch

from computer import ui_automation as uia


class UIAutomationTests(TestCase):
    def setUp(self):
        self.control = Mock()
        self.control.element_info.name = "Save"
        self.control.element_info.control_type = "Button"
        self.control.element_info.automation_id = "saveButton"
        self.control.is_visible.return_value = True
        self.control.is_enabled.return_value = True
        self.window = Mock()
        self.window.window_text.return_value = "Notepad"
        self.window.is_visible.return_value = True
        self.window.descendants.return_value = [self.control]
        self.desktop = Mock()
        self.desktop.windows.return_value = [self.window]
        self.backend = patch.object(uia, "_backend", return_value=self.desktop)
        self.backend.start()
        self.addCleanup(self.backend.stop)

    def test_lista_controles_com_nome_tipo_e_automation_id(self):
        result = uia.listar_controles("Notepad")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["result"][0]["nome"], "Save")
        self.assertEqual(result["result"][0]["control_type"], "Button")
        self.assertEqual(result["result"][0]["automation_id"], "saveButton")

    def test_rejeita_janela_ambigua(self):
        other = Mock()
        other.window_text.return_value = "Notepad - second"
        other.is_visible.return_value = True
        self.desktop.windows.return_value = [self.window, other]
        result = uia.listar_controles("Notepad")
        self.assertEqual(result["status"], "ambiguous")

    def test_acao_permitida_em_controle_unico(self):
        result = uia.acionar_controle("Notepad", "saveButton", "click")
        self.assertEqual(result["status"], "ok")
        self.control.click_input.assert_called_once_with()

    def test_set_text_so_retorna_ok_quando_valor_final_e_confirmado(self):
        self.control.get_value.return_value = "hello"
        result = uia.acionar_controle("Notepad", "saveButton", "set_text", "hello")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["verified"])

    def test_set_text_sem_leitura_final_retorna_unverified(self):
        self.control.get_value.side_effect = RuntimeError("provider unavailable")
        result = uia.acionar_controle("Notepad", "saveButton", "set_text", "hello")
        self.assertEqual(result["status"], "unverified")
        self.assertFalse(result["verified"])

    def test_acao_nao_permitida_e_bloqueada(self):
        result = uia.acionar_controle("Notepad", "saveButton", "delete")
        self.assertEqual(result["status"], "erro")
        self.control.click_input.assert_not_called()

    def test_controle_duplicado_nao_e_acionado(self):
        duplicate = Mock()
        duplicate.element_info.name = "Save"
        duplicate.element_info.automation_id = "saveButton"
        duplicate.element_info.control_type = "Button"
        self.window.descendants.return_value = [self.control, duplicate]
        result = uia.acionar_controle("Notepad", "Save", "click")
        self.assertEqual(result["status"], "ambiguous")
        self.control.click_input.assert_not_called()

    def test_controle_desabilitado_nao_e_acionado(self):
        self.control.is_enabled.return_value = False
        result = uia.acionar_controle("Notepad", "saveButton", "click")
        self.assertEqual(result["status"], "erro")
        self.control.click_input.assert_not_called()

    def test_limite_invalido_e_rejeitado(self):
        self.assertEqual(uia.listar_controles("Notepad", 201)["status"], "erro")


    def test_acao_de_janela_invalida_e_bloqueada(self):
        result = uia.gerenciar_janela("Notepad", "delete")
        self.assertEqual(result["status"], "erro")
        self.window.close.assert_not_called()

    def test_minimizar_janela_verifica_estado(self):
        self.window.is_minimized.return_value = True
        result = uia.gerenciar_janela("Notepad", "minimize")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["verified"])
        self.window.minimize.assert_called_once_with()

    def test_janela_ambigua_nao_e_acionada(self):
        other = Mock()
        other.window_text.return_value = "Notepad - second"
        other.is_visible.return_value = True
        self.desktop.windows.return_value = [self.window, other]
        result = uia.gerenciar_janela("Notepad", "maximize")
        self.assertEqual(result["status"], "ambiguous")
        self.window.maximize.assert_not_called()


    def test_acao_aceita_substring_quando_controle_unico(self):
        result = uia.acionar_controle("Notepad", "Sav", "click")
        self.assertEqual(result["status"], "ok")
        self.control.click_input.assert_called_once_with()

    def test_substring_ambiguo_nao_aciona_controles(self):
        duplicate = Mock()
        duplicate.element_info.name = "Save As"
        duplicate.element_info.automation_id = "saveAsButton"
        duplicate.element_info.control_type = "Button"
        duplicate.is_visible.return_value = True
        duplicate.is_enabled.return_value = True
        self.window.descendants.return_value = [self.control, duplicate]
        result = uia.acionar_controle("Notepad", "Sav", "click")
        self.assertEqual(result["status"], "ambiguous")
        self.control.click_input.assert_not_called()
        duplicate.click_input.assert_not_called()
