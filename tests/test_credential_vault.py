import os
import pytest

from tasks import credential_vault as vault


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI test")
def test_dpapi_vault_encrypts_and_never_lists_secret(tmp_path, monkeypatch):
    monkeypatch.setattr(vault, "ROOT", tmp_path)
    monkeypatch.setattr(vault, "VAULT_FILE", tmp_path / "credentials.dpapi")

    saved = vault.credentials_save(vault.CredentialInput(
        service="gmail",
        label="Conta de teste",
        username="test@example.com",
        secret="DO_NOT_EXPOSE_THIS_SECRET",
    ))
    assert saved["saved"] is True
    assert vault.VAULT_FILE.exists()
    raw = vault.VAULT_FILE.read_bytes()
    assert b"DO_NOT_EXPOSE_THIS_SECRET" not in raw

    listed = vault.credentials_list()["credentials"]
    assert listed == [{
        "service": "gmail",
        "label": "Conta de teste",
        "username": "test@example.com",
        "updated_at": listed[0]["updated_at"],
        "has_secret": True,
    }]
    assert "secret" not in listed[0]
    assert vault.get_credential("gmail")["secret"] == "DO_NOT_EXPOSE_THIS_SECRET"

    deleted = vault.credentials_delete("gmail")
    assert deleted["deleted"] is True
    assert vault.list_credentials() == []
