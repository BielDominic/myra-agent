# FASE 28.1 — Diagnostico Tailscale

## Estado

O diagnostico local foi implementado em `tasks/remote_access.py` e exposto em `GET /remote_access/status`. A instalacao, autenticacao e validacao com o iPhone continuam pendentes porque exigem a conta e a aprovacao interativa do usuario.

## Instalar e conectar

1. Instale o cliente oficial do Tailscale no Windows: https://tailscale.com/download/windows
2. Abra o cliente e entre na conta Tailscale desejada.
3. Instale o app oficial no iPhone: https://tailscale.com/download/ios
4. Entre na mesma conta e confirme que ambos os dispositivos aparecem no mesmo tailnet.
5. Consulte `http://127.0.0.1:8000/remote_access/status` no PC para verificar a conexao local.

O diagnostico retorna apenas o estado do proprio PC, nome do dispositivo e IPv4 Tailscale validado no intervalo `100.64.0.0/10`. Nao lista outros dispositivos do tailnet.

## Seguranca importante

- A integracao **nao instala Tailscale, nao faz login, nao altera firewall e nao publica portas**.
- O endpoint informa explicitamente `api_exposed: false`.
- O backend da MYRA continua vinculado a `127.0.0.1:8000`.
- Nao exponha o FastAPI inteiro ao tailnet antes de implementar autenticacao/autorizacao para as rotas de controle do computador.
- O Telegram pode controlar a MYRA por long polling sem Tailscale; Tailscale e a base opcional para futuros clientes diretos, incluindo um app iOS.

## Pendencias para fechar a fase

- [ ] Instalar e autenticar Tailscale no PC.
- [ ] Instalar e autenticar Tailscale no iPhone com a mesma conta.
- [ ] Confirmar estado `connected` no endpoint local.
- [ ] Antes de habilitar acesso direto remoto, implementar autenticacao de API e restringir rotas sensiveis.
