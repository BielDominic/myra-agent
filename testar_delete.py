import imaplib
import os

m = imaplib.IMAP4_SSL('imap.gmail.com', 993)
m.login(os.environ['GMAIL_USER'], os.environ['GMAIL_APP_PASSWORD'])
m.select('INBOX')

status, mensagens = m.search(None, 'ALL')
ids = mensagens[0].split()
print(f'Total antes: {len(ids)}')

eid = ids[-1]
print(f'Movendo email ID: {eid}')

# 1. Copia para Trash
r1 = m.copy(eid, '[Gmail]/Trash')
print(f'copy: {r1}')

# 2. Marca como deletado (1 backslash = \Deleted)
r2 = m.store(eid, '+FLAGS', '\\Deleted')
print(f'store: {r2}')

# 3. Expurga
r3 = m.expunge()
print(f'expunge: {r3}')

status, mensagens = m.search(None, 'ALL')
ids = mensagens[0].split()
print(f'Total depois: {len(ids)}')

m.logout()