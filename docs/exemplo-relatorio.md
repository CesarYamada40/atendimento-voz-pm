# Exemplo de relatório de log (dados fictícios)

> Exemplo **anônimo** para documentar o formato do relatório. Nenhum dado real
> é publicado neste repositório (ver seção LGPD no README).

```
OCORRÊNCIA 2026-000000  call_id=exemplo00000
  status=registrada  gravidade=G1  criada=2026-01-01T12:00:00
------------------------------------------------------------------------------
CHECKLIST
  [OK ] campos_obrigatorios_ok
  [OK ] local_resolvido
  [OK ] cep_identificado
  [OK ] gravidade_calculada
  [OK ] orgao_definido
  [OK ] numero_gerado
  [OK ] registrada

PASSO A PASSO (entendimento por pergunta)
  [OK ] nome        falou='meu nome é Fulano' -> caller_name='Fulano'
  [OK ] ocorrencia  falou='tem um homem armado agora' -> nature='Crime em andamento com risco'
  [OK ] tipo        falou='pessoa física' -> caller_type='PF'
  [OK ] endereco    falou='meu cep é 00000-000' -> location_address='Rua Exemplo'
  [OK ] numero      falou='número 100' -> location_number='100'
  [OK ] telefone    falou='telefone 00 90000-0000' -> caller_phone='00900000000'
  [OK ] referencia  falou='perto da praça' -> location_reference='perto da praça'
  [OK ] fatos       falou='um homem armado…' -> description='um homem armado…'
        -> GRAVIDADE G1
```

Gerar o relatório de uma ocorrência real:

```bash
.venv/bin/python scripts/relatorio.py <call_id>
.venv/bin/python scripts/exportar.py     # exporta tudo para docs/relatorios/ (local)
```
