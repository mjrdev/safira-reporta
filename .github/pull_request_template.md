## O que muda

<!-- Descreva a mudança e o requisito atendido (ex.: RF01, RNF02). -->

## Como testar

- [ ] `pytest` passa localmente
- [ ] Testado no navegador do celular (largura 360 px)

## Checklist de auto-revisão

- [ ] O código segue a separação Model / View / Template
- [ ] Entradas validadas no servidor (Forms) e saída escapada nos templates
- [ ] Nenhum segredo, senha ou dado pessoal real no código ou nos testes
- [ ] Nome e telefone de moradores não aparecem em páginas públicas
- [ ] Rótulos visíveis, botões ≥ 48 px e mensagens de erro com ícone + texto (RNF04)
- [ ] Testes novos cobrem o comportamento alterado
- [ ] Migrations criadas quando o model mudou
