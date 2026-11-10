"""Serviços transversais do Findly (camada de serviços do Django).

Módulos utilitários desacoplados acionados pelas regras de negócio:

- ``qrcode_service``       — geração de etiquetas e vouchers de retirada.
- ``photo_service``        — validação, compressão e remoção de EXIF das fotos.
- ``notification_service`` — matching e disparo de e-mails/push.
"""
