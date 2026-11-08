"""Direct-to-merchant static BR Codes. No bank API or payment confirmation."""
import base64
import binascii
import io
import re
import unicodedata


def ascii_text(value, maximum):
    value = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Z0-9 .-]', '', value.upper()).strip()[:maximum]


def valid_document(value, size):
    if len(value) != size or len(set(value)) == 1:
        return False
    if size == 11:
        if not value.isascii() or not value.isdigit():
            return False
        nums = [int(v) for v in value]
        for end in (9, 10):
            check = (sum(n * w for n, w in zip(nums[:end], range(end + 1, 1, -1))) * 10) % 11
            if nums[end] != (0 if check == 10 else check):
                return False
        return True
    if not re.fullmatch(r'[A-Z0-9]{12}[0-9]{2}', value):
        return False
    # The same weights support numeric and alphanumeric CNPJ (ASCII minus 48).
    nums = [ord(v) - 48 for v in value]
    for end, weights in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
                         (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
        rem = sum(n * w for n, w in zip(nums[:end], weights)) % 11
        if nums[end] != (0 if rem < 2 else 11 - rem):
            return False
    return True


def normalize_key(raw, kind):
    raw = str(raw).strip()
    if kind in ('cpf', 'cnpj'):
        value = re.sub(r'[./\s-]', '', raw).upper()
        if not valid_document(value, 11 if kind == 'cpf' else 14):
            raise ValueError('Confira o CPF ou CNPJ da chave Pix.')
    elif kind == 'email':
        value = raw.lower()
        from email_validator import validate_email, EmailNotValidError
        try:
            value = validate_email(value, check_deliverability=False, allow_smtputf8=False).normalized.lower()
        except EmailNotValidError as exc:
            raise ValueError('Confira o e-mail da chave Pix.') from exc
    elif kind == 'phone':
        if not re.fullmatch(r'[+()0-9\s.-]+', raw):
            raise ValueError('Confira o telefone da chave Pix.')
        value = re.sub(r'\D', '', raw)
        if len(value) in (10, 11):
            value = '55' + value
        if not re.fullmatch(r'55[1-9][0-9][0-9]{8,9}', value):
            raise ValueError('Informe o telefone da chave Pix com DDD.')
        value = '+' + value
    elif kind == 'random':
        value = raw.lower()
        if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value):
            raise ValueError('Confira a chave aleatória Pix completa.')
    else:
        raise ValueError('Escolha o tipo da chave Pix para gerar o QR Code.')
    if not value.isascii() or not 1 <= len(value) <= 77:
        raise ValueError('A chave Pix deve ter até 77 caracteres para o QR Code.')
    return value


def settings(key, kind, receiver, city):
    key, kind, receiver, city = (str(v).strip() for v in (key, kind, receiver, city))
    if not key:
        return '', '', '', ''
    if not kind:
        # Preserve old key-only setups until the merchant deliberately enables QR.
        return key[:180], '', receiver[:120], city[:120]
    normalized = normalize_key(key, kind)
    if not ascii_text(receiver, 25) or not ascii_text(city, 15):
        raise ValueError('Informe o nome do recebedor e a cidade para ativar o QR Code Pix.')
    if len(receiver) > 120 or len(city) > 120:
        raise ValueError('Revise o nome do recebedor e a cidade do Pix.')
    return normalized, kind, receiver, city


def field(tag, value):
    value = str(value)
    if not value.isascii() or len(value) > 99:
        raise ValueError('Campo BR Code inválido.')
    return tag + f'{len(value):02d}' + value


def payload(key, receiver, city, cents, txid='***'):
    if type(cents) is not int or not 0 < cents <= 999999999999:
        raise ValueError('Valor Pix inválido.')
    if txid != '***' and not re.fullmatch(r'[A-Za-z0-9]{1,25}', txid):
        raise ValueError('Identificador Pix inválido.')
    account = field('00', 'br.gov.bcb.pix') + field('01', key)
    result = (field('00', '01') + field('26', account) + field('52', '0000') +
              field('53', '986') + field('54', f'{cents // 100}.{cents % 100:02d}') +
              field('58', 'BR') + field('59', ascii_text(receiver, 25)) +
              field('60', ascii_text(city, 15)) + field('62', field('05', txid)) + '6304')
    return result + f'{binascii.crc_hqx(result.encode("ascii"), 0xffff):04X}'


def payment(store, cents, txid='***'):
    store = dict(store)
    if not store.get('pix_key_type') or cents <= 0:
        return None
    try:
        key, kind, receiver, city = settings(store.get('pix_key', ''), store['pix_key_type'],
                                            store.get('pix_receiver_name', ''), store.get('pix_receiver_city', ''))
        if not kind:
            return None
        code = payload(key, receiver, city, cents, txid)
    except ValueError:
        return None
    import qrcode
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=4)
    qr.add_data(code); qr.make(fit=True)
    output = io.BytesIO(); qr.make_image(fill_color='black', back_color='white').save(output, format='PNG')
    return {'payload': code, 'qr_image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode(),
            'receiver': receiver, 'key': key, 'amount': 'R$ ' + f'{cents / 100:.2f}'.replace('.', ','),
            'confirmation': 'Confirmação do pagamento feita pela loja.'}
