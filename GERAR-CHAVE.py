# Execute na sua máquina ou no Shell do Render. Não envie o resultado no chat.
import base64,secrets
print(base64.b64encode(secrets.token_bytes(32)).decode())
