"""Apps de domínio do Findly.

Cada app será criado na próxima etapa (via ``python manage.py startapp``):

- ``authentication`` — login, logout, cadastro e recuperação de senha.
- ``users``          — perfil, dados cadastrais e papéis/permissões.
- ``items``          — achados, perdidos e máquina de estados.
- ``operations``     — custódia, entregas/retiradas e pontos de coleta.
- ``audit``          — histórico e logs de auditoria.

Lembre-se: o atributo ``name`` do ``AppConfig`` de cada app deve ser
``apps.<app>`` (ex.: ``apps.users``), pois todos vivem dentro deste pacote.
"""
