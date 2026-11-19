# Simulador de prova de inclinação

Aplicativo de Engenharia Naval em português para montar uma condição de carga, planejar pesos e pêndulos, movimentar pesos entre bordos e estimar GM e KG por regressão. A interface compartilha a mesma sessão entre dez telas. A execução depende somente dos arquivos deste repositório.

## Primeiro ensaio em poucos minutos

1. Na página **Início**, clique em **Carregar exemplo fictício**. A tela de movimentação abre com o pontão de 12 000 kg. Para testar o carregamento, clique em uma carga, arraste-a ou edite as coordenadas e aplique. **Desfazer** ou **Restaurar condição inicial** recupera o ponto de partida.
2. Em **Planejamento de pesos**, clique em **Comparar configurações** para ver as três alternativas do exemplo. Em **Pêndulos**, confira os fios de 2,0 e 2,5 m. O limite de projeto do exemplo já está definido em **Condições do ensaio**.
3. Em **Ensaio virtual**, clique em **Iniciar prova e congelar condição de carregamento**. Abra o roteiro do pontão. Registre o zero inicial. Siga os oito movimentos da tabela, sempre clicando primeiro em **Movimentar o peso** e depois em **Registrar condição experimental simulada**. O roteiro indica qual peso vai a +1,25 m, −1,25 m ou ao zero. No carregamento inicial todos os pesos estão na linha de centro.
4. Clique em **Encerrar prova (manter leituras)** e em **Calcular regressão**. No modelo quase estático ideal, sem erros, o resultado esperado é **GM = 1,000 m e KG = 0,750 m**. Estes valores valem para a condição fictícia do exemplo.
5. Em **Relatório**, baixe o PDF ou o ZIP com tabelas, dados, comparação e gráficos. Para estudar erros, exporte primeiro a série de referência. Ative um viés em **Condições do ensaio**, inicie nova prova e repita a sequência. Com viés de +5% na massa declarada e sem outros efeitos, o GM ajustado do pontão passa a 1,05 m.

## Executar e publicar

Use Python 3.12. No Windows, abra a pasta descompactada no terminal. Os comandos são os mesmos no Linux e macOS.

```sh
python -m venv .venv
```

Ative com `.venv\Scripts\activate` no Prompt de Comando do Windows ou `source .venv/bin/activate` em bash. Em seguida execute:

```sh
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

Para publicar, crie um repositório no GitHub e envie **o conteúdo descompactado**, com `app.py`, `requirements.txt` e as pastas na raiz. Inclua `components/cargo_drag/frontend/index.html`. No Streamlit Community Cloud, abra **Create app**, selecione o repositório e a branch utilizada, indique `app.py` em **Main file path**, selecione Python 3.12 em **Advanced settings** e clique em **Deploy**. Se o projeto estiver dentro de uma subpasta, o caminho precisa incluí-la. [Guia oficial](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

## Usar os dados da sua embarcação

Comece em uma sessão vazia para trabalhar com dados reais. Ao importar uma tabela, revise o tipo, a aba, a linha de cabeçalho e as unidades na prévia. Confirme a importação em cada tabela. CSV aceita ponto ou vírgula decimal e codificações UTF-8 e Windows-1252. Em XLSX, selecione cada aba pertinente. Quando uma coluna calculada do Excel aparece vazia, recalcule e salve a planilha no Excel ou exporte os valores como CSV. JSON aceita os campos canônicos descritos nos modelos de `data/`.

| O que você já tem | Onde inserir | O que conferir |
|---|---|---|
| Resultados hidrostáticos e geométricos da AP1.1 | Embarcação → Tabela hidrostática ou Contorno do casco | Deslocamento de massa, calado moldado, KM **transversal**. KB, LCB, LCF e MCT são opcionais. Geometria aceita como contorno XY em planta. |
| Lista individual da AP1.2 | Carregamento → Importar tabela de cargas | Massa, coordenadas do CG e origem dos eixos. A massa base exclui os itens cadastrados. |
| Condições globais da AP1.2 | Embarcação → importar arquivo → Condição global de carregamento | Selecione a linha desejada com Δ, LCG, TCG e KG. Importe antes os itens individuais que já integram essa condição. A base é recuperada por diferença de massas e momentos. |
| Curva GZ da AP1.3 | Embarcação → Curva GZ | Ângulo, unidade e braço GZ. Informe também Δ e KG de referência para ajustar a curva. Verifique igualdade de casco, deslocamento e trim. |
| Leituras experimentais | Processamento → Importar ou editar medições | Momento em kg·m, tangente adimensional e indicação de equilíbrio. Informe deslocamento, KM e FSM da própria prova. |

L, B e pontal isolados são insuficientes para calcular KM ou GZ do casco. Se faltar uma hidrostática correspondente a Δ, a interface continua mostrando o que o balanço de massas permite obter. Quando a única tabela disponível é a hidrostática, ainda faltam a massa e os centros da condição de prova. O FSM deve ser zero somente quando a ausência de superfície livre for conhecida.

## Modos e resultados

No **modo de carregamento**, salvar a condição inicial define o ponto de restauração das cargas. É possível adicionar, duplicar e retirar massas em Carregamento e editar X, Y, Z e massa na Movimentação. O arraste edita X e Y. As representações indicam o referencial e distinguem categorias. O limite de Z se aplica ao CG. Os limites nominais em X e Y para cargas dimensionadas pressupõem o CG no centro da projeção da carga. Contorno, obstáculos, interferência entre peças e resistência do convés exigem conferência do projetista.

No **modo de prova**, os pesos já estão a bordo. A condição inicial deve ser transversalmente centrada. Somente Y muda, o momento é acumulado em relação às posições iniciais e a regressão usa os patamares em equilíbrio. O modelo **quase estático** dispensa informações de dinâmica e etiqueta a leitura como equilíbrio teórico. No **dinâmico**, informe I efetivo, amortecimento e tolerâncias, mova um peso e avance o tempo. A tela mostra a curva de balanço e bloqueia leituras enquanto a velocidade ou o afastamento do equilíbrio exceder a tolerância.

O relatório técnico, a condição congelada, o cenário por leitura e as posições dos pesos permitem verificar a origem dos resultados. Os dados vivem na sessão do Streamlit. Exporte antes de fechar, recarregar, reiniciar a aplicação ou iniciar outra prova. O pacote JSON fornece dados por categoria para reimportação; os controles de desfazer e a sessão dinâmica em andamento ficam na memória da sessão.

## Arquivos, equações e como verificar cada etapa

A navegação declarada em `app.py` usa `telas/` para evitar que o Streamlit crie um segundo menu automaticamente. As equações completas, símbolos, unidades e fontes ficam em `REFERENCIAS.md` e no painel **Fundamentação dos cálculos** da página inicial.

| Etapa | Arquivos principais | Verificação a executar |
|---|---|---|
| 1. Arquitetura e estado | `app.py`, `inicio.py`, `utils/estado.py`, `utils/navegacao.py` | Abra as dez telas. Volte a uma etapa e confira os dados salvos. |
| 2. Hidrostática e importação | `modules/hidrostatica.py`, `modules/validacao.py`, `utils/importacao.py`, `utils/mapeamento.py`, `utils/dados.py`, `utils/ui_importacao.py`, `utils/condicao_global.py`, `telas/01_embarcacao.py` | Confira um ponto tabulado, outro interpolado e um fora da faixa. Verifique a conversão de t para kg. |
| 3. Distribuição de cargas | `modules/carregamento.py`, `telas/02_carregamento.py` | Some massas e momentos. Duplique, remova e restaure um item. |
| 4. Interatividade | `telas/03_simulacao_interativa.py`, `components/cargo_drag/` | Arraste um peso e confira TCG. Aumente Z e confira KG. Verifique desfazer e refazer. |
| 5. Representação | `visualization/casco.py`, `visualization/cargas.py`, `visualization/inclinacao.py`, `modules/estabilidade.py`, `modules/criterios.py` | Em uma banda positiva, boreste desce. Deslocar para vante altera LCG. |
| 6. Planejamento | `modules/movimentacao_pesos.py`, `telas/04_planejamento_pesos.py` | Compare três cursos. Um Y final fora do intervalo informado impede a recomendação. |
| 7. Pêndulos | `modules/pendulos.py`, `visualization/pendulos.py`, `telas/05_pendulos.py` | Com o mesmo ângulo, dobrar L dobra a deflexão. Compare três comprimentos e a altura disponível. |
| 8. Prova | `modules/prova_inclinacao.py`, `telas/06_prova_inclinacao.py` | Execute a sequência do pontão. No modo dinâmico, verifique o bloqueio logo após mover um peso. |
| 9. Erros | `modules/erros_experimentais.py`, `telas/07_simulacao_erros.py` | Aplique ruído de leitura, viés de massa, vento entre patamares ou FSM extra e inspecione os diagnósticos. |
| 10. Processamento | `modules/regressao.py`, `visualization/graficos.py`, `telas/08_processamento.py` | Compare reta, resíduos e GM/KG com o balanço da condição congelada. |
| 11. Validação | `tests/test_fisica.py`, `tests/test_ensaio_integrado.py`, `tests/test_fluxo_streamlit.py`, `tests/test_importacao_categorias.py`, `tests/test_importacao_planilhas_reais.py` | Execute `python -m pytest -q`. Inclui teste do ponto de entrada, importadores, exemplo de livro e série completa. |
| 12. Exportação e distribuição | `telas/09_relatorio.py`, `utils/relatorio_pdf.py`, `requirements.txt`, `.streamlit/config.toml`, `data/`, `utils/exemplo.py` | Abra PDF e ZIP. Compare os valores com a tela e consulte gráficos HTML offline extraindo o ZIP inteiro. |
