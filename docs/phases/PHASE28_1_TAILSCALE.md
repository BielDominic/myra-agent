# FASE 28.1 — Diagnostico Tailscale

## Estado

O diagnostico local foi implementado em `tasks/remote_access.py` e exposto em `GET /remote_access/status`. O cliente Tailscale 1.104.2 foi instalado no PC Windows em 2026-10-25 e agora informa `Running`, com IPv4 Tailscale atribuido. A consulta resumida encontrou zero peers no tailnet, incluindo zero peers iOS; portanto, o PC esta conectado, mas ainda nao ha iPhone visivel para validar. O login/adicao do iPhone e a validacao entre dispositivos continuam pendentes.

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
- A API remota Bearer ja existe, mas retorna HTTP 503 enquanto `MYRA_REMOTE_API_TOKEN` nao estiver carregado no backend. Nao exponha o FastAPI inteiro ao tailnet; publique somente `/remote/v1` depois de configurar o token e validar a regra de path.
- O Telegram pode controlar a MYRA por long polling sem Tailscale; Tailscale e a base opcional para futuros clientes diretos, incluindo um app iOS.

## Pendencias para fechar a fase

- [x] Instalar e autenticar Tailscale no PC; o endpoint local confirmou `connected`.
- [ ] Instalar e autenticar Tailscale no iPhone com a mesma conta.
- [x] Confirmar estado `connected` no endpoint local e `api_exposed: false`.
- [ ] Configurar e validar Serve restrito a `/remote/v1` somente depois de configurar `MYRA_REMOTE_API_TOKEN`; nao expor rotas locais antigas.
