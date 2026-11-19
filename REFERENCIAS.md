# Fundamentação dos cálculos

## Referencial e grandezas

Use um único sistema de coordenadas em todas as importações. O aplicativo adota X da extremidade de ré (0) para a proa (L), Y positivo para boreste e Z a partir da linha base. Banda positiva submerge boreste. A seção gráfica mostra a flutuação direita e B e M de referência. O cálculo usa **massa deslocada Δ em kg**. Momentos de massa têm unidade kg·m. Um momento externo de força, em N·m, entra dividido pela gravidade padrão g₀ = 9,80665 m/s².

## Carregamento e hidrostática

| Resultado | Equação e variáveis | Hipóteses e limites | Fonte |
|---|---|---|---|
| Massa e centros | Δ = m₀ + Σmᵢ. Para qualquer coordenada q em m, qG = (m₀q₀ + Σmᵢqᵢ)/Δ. O numerador é o momento de massa no eixo. | Pesos fixos e centros conhecidos. A massa base exclui as cargas discriminadas. Um centro desconhecido permanece pendente. | [3], equilíbrio de momentos |
| Recuperação da base | m₀ = Δ − Σmᵢ. q₀ = (ΔqG − Σmᵢqᵢ)/m₀. | Todas as cargas descontadas já integram a condição global. Com base de massa zero, as cargas devem fechar os momentos nos três eixos. | Rearranjo do balanço anterior |
| Consulta hidrostática | Para dois deslocamentos vizinhos Δ₁ e Δ₂, H = H₁ + (H₂−H₁)(Δ−Δ₁)/(Δ₂−Δ₁). | Interpolação linear local, sem extrapolação. Exige a mesma água, geometria, referência de calado e trim compatível. Propriedades opcionais exigem ambos os valores vizinhos. Ponto isolado só serve à sua própria condição. | Interpolação linear entre dados de hidrostática [3] |
| Estabilidade inicial | GM sólido = KMₜ − KG. FSC = FSM/Δ. GM efetivo = GM sólido − FSC. Comprimentos em m, FSM total em kg·m. | FSM inclui densidades e se refere aos tanques da condição. Campo vazio significa desconhecido. O cenário pode acrescentar um FSM declarado. | [1], anexo 1 §2.1. [4], eq. 10.7 |
| Banda de carregamento | tan φ = TCG/GM efetivo. | Casco simétrico transversalmente, trim pequeno, ausência de momento externo e região metacêntrica inicial. O app suprime estimativa acima de 4° e para GM não positivo. GM positivo indica estabilidade local da condição direita. | Equilíbrio transversal de [3] e [4] |
| Variação de trim | M = Δ(LCG−LCB). Variação de trim = M/MCT, em m, positiva pela proa. | LCB da condição hidrostática de referência. MCT requerido em **kg·m por m de trim**. Conversão de t·m/cm para kg·m/m multiplica por 100 000. Modelo linear, sem iteração de equilíbrio longitudinal. | [3], capítulo de trim, exemplo da p. 150 |
| Curva GZ ajustada | GZ₂(φ) = GZ₁(φ) + (KG₁−KG₂) sen φ. Braços e alturas em m. | Mesmos casco, deslocamento, trim e curva direita simétrica. TCG=0 e FSM=0. O usuário deve confirmar que o trim da curva continua aplicável. Esta identidade altera apenas o braço associado ao deslocamento vertical de G. | Geometria da projeção vertical de GG′ no braço horizontal, [3], estabilidade a grandes ângulos |

## Planejamento e execução da prova

| Resultado | Equação e variáveis | Hipóteses e limites | Fonte |
|---|---|---|---|
| Momento dos pesos | M = Σmᵢ(yᵢ−yᵢ,₀), em kg·m. | Posições relativas ao zero inicial. Massas, X e Z congelados durante a prova. A condição virtual começa com TCG nulo. | [4], eq. 10.1 |
| Banda prevista | tan φ = (M + Nₑ/g₀)/(Δ GM efetivo). φ = arctan(tan φ). Nₑ é o momento externo imposto em N·m. | Pequena banda, pesos a bordo, flutuação livre e GM aproximadamente constante. O teto **didático** de 4° delimita este modelo e não comprova a validade para um casco particular. O limite de projeto informado pode ser menor. | [1], anexo 1 §2.4.2. [4], eq. 10.1 |
| Momento e massa alvo | M requerido = Δ GM efetivo tan φ. Massa a deslocar = M requerido/curso. | Módulo do curso em m, GM de planejamento conhecido, sem momento externo. Uma recomendação compara somente alternativas que atendem aos limites declarados. Maior sinal angular/divisão angular e, no empate, menos pesos. | [4], eq. 10.4 e exemplo 10.2. A regra de escolha é didática. |
| Pêndulo | x = L tan φ, φ = arctan(x/L), L mínimo = x desejado / tan φ. Divisão angular no zero = arctan(r/L). L, x e divisão r em m. | L é a distância vertical da suspensão à régua na condição direita. A distância até o prumo pode ser maior. A divisão é um indicador geométrico da legibilidade no zero. Durante o transitório, a linha é apenas a indicação geométrica instantânea. | [1], anexo 1 §2.4. [4], eq. 10.3 |
| Balanço transitório | I φ″ + c φ′ + Δg₀ GM efetivo φ = g₀M + Nₑ. φ em rad, I em kg·m², c em N·m·s/rad. | Um grau de liberdade, momento constante por patamar, I efetivo inclui inércia adicionada. I e c vêm do usuário. Equilíbrio linear φeq = (M+Nₑ/g₀)/(Δ GM). Exponencial da matriz de estado durante cada passo. Registro exige proximidade angular a φeq e velocidade dentro das tolerâncias informadas. | [6], eq. 2.1, especializada para GM constante e com momento externo imposto |
| Indicador gráfico | Rotação de ângulo −φ no plano Y–Z em torno do calado direito. | Seção nominal retangular. A planta pode utilizar um contorno real importado. B mostrado é o da condição direita. O desenho não determina o novo volume imerso, B inclinado ou a flutuação em trim. | Transformação geométrica da visualização |

## Leituras, regressão e incerteza

| Resultado | Equação e unidades | Hipóteses e limites | Fonte |
|---|---|---|---|
| Erros impostos | M indicado = M(1+eₘ)(1+e_d). L indicado = L(1+e_L). x lido = L tan φ + b₀ + ε. Os vieses e são frações; b₀ e o desvio-padrão de ε são em m. | Experimentos sintéticos. O ruído de leitura é normal, independente por instrumento e reprodutível. O momento de vento tem média e desvio em N·m e muda entre movimentos. A interferência é um momento adicional assinado. Não se estima vento usando velocidade ou área vélica. | Modelo de injeção definido neste projeto sobre as grandezas de [4]; distribuições e intensidades não são propriedades de embarcações. |
| Tangente e desacordo | Para cada instrumento tⱼ = x lido/L indicado. Cada registro usa a média aritmética dos tⱼ. Desacordo = maior − menor arctan(tⱼ), em graus. | Leituras referentes ao mesmo patamar e mesmo zero. Pêndulos têm peso estatístico igual. Sem quantização automática da régua. | [4], cap. 10 |
| Regressão | tᵢ = a + bMᵢ + εᵢ. GM observado = 1/(Δ b). KG sólido = KM − GM observado − FSM/Δ. | Ajuste OLS com intercepto, deslocamento constante, b positivo, ao menos três momentos distintos. Apenas leituras confirmadas em equilíbrio. O app aceita série curta como preliminar; oito registros sozinhos não comprovam oito movimentos ou aprovação do ensaio. | [4], eqs. 10.5–10.7. [2], documentação da prova |
| Resíduos e dispersão | eᵢ = tᵢ − (a+bMᵢ); s = √[Σeᵢ²/(n−2)]; R² = 1 − Σeᵢ²/Σ(tᵢ−t médio)². u(b) = s/√Σ(Mᵢ−M médio)². | Tangentes e resíduos adimensionais; b em (kg·m)⁻¹. Hipóteses de ruído independente, variância constante e momentos conhecidos para interpretar u(b). R² elevado pode coexistir com um erro sistemático de escala. | Mínimos quadrados com intercepto, [4], §10.4 |
| Incerteza do ajuste | u(GM) ≈ GM·u(b)/b, em m. | Somente a contribuição da inclinação da reta. Δ fixo e pequenas perturbações. Se KM, FSM e Δ forem exatos, a mesma contribuição absoluta se transmite a KG. | Propagação diferencial [5], aplicada à regressão |
| Sensibilidade individual | GM = m d L/(Δ abs(x)). Para entradas independentes positivas q = m,d,L,Δ,abs(x), u(GM) ≈ GM·√(Σ (u(q)/q)²). | Uma leitura não nula, sem viés residual. A incerteza deve estar nas unidades da entrada. Vieses comuns, correlações entre leituras e incertezas de KM/FSM não integram automaticamente a estimativa. | [4], eqs. 10.1 e 10.3. [5], eq. A-3 |

## Caso fictício e conferência independente

O exemplo representa um pontão **prismático retangular fictício** de 8 m × 3 m em água com densidade estipulada de 1 000 kg/m³. Só para esse corpo geométrico, Δ = ρLBT, KB = T/2, BMₜ = (LB³/12)/(LBT) e KMₜ = KB + BMₜ. A tabela foi calculada entre T = 0,40 e 0,60 m. O mesmo procedimento não é aplicado a um casco importado a partir de comprimento e boca.

Com 11 000 kg de massa base e 1 000 kg de cargas, Δ = 12 000 kg. Para T = 0,50 m, KB = 0,25 m, BMₜ = 1,50 m e KMₜ = 1,75 m. Todos os centros verticais do exemplo estão a 0,75 m. Com FSM = 0, GM = 1,00 m. Dois pesos de 250 kg movidos 1,25 m produzem 625 kg·m; a tangente é 625/12 000. No pêndulo de 2 m isso corresponde a 0,10417 m. O exemplo permite conferir cálculo, sinal e leitura sem conhecer o código.

O teste da p. 289 de [3] verifica o exemplo 2 no sentido inverso e recupera GM = 0,600 m. Os exemplos 10.1 e 10.2 de [4] verificam uma leitura de referência e o planejamento. A série de nove leituras do pontão passa pela interface, pela regressão e pela exportação.

## Referências consultadas

1. **IMO.** *International Code on Intact Stability, 2008*. Resolução MSC.267(85), adotada em 4 dez. 2008. Parte B, cap. 8 e anexo 1. Para instrumentação, consultar 8.2.2.9; para deslocamentos dos pesos, consultar 8.4. Texto de referência do projeto. A aplicação operacional depende da Administração e das regras aplicáveis à embarcação. [Texto oficial](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MSCResolutions/MSC.267%2885%29.pdf)
2. **US Coast Guard, Marine Safety Center.** *Submission of Stability Test Results*. Plan Review Guideline GEN-02, revisão de 28 maio 2020. Usada para o conteúdo documental do ensaio. [Documento oficial](https://www.dco.uscg.mil/Portals/9/MSC/PRG/PRG.GEN-02.2020.05.28.Submission%20of%20Stability%20Test%20Results.pdf)
3. **DERRETT, D. R.; BARRASS, C. B.** *Ship Stability for Masters and Mates*. 6ª ed. consolidada. Butterworth-Heinemann, 2006. Equilíbrio de momentos, estabilidade transversal, trim e experimento de inclinação. [Exemplar consultado, Western Norway University of Applied Sciences](https://home.hvl.no/ansatte/gste/ftp/mas124_intro_marinteknikk/Litteratur/Kompendier_Books/ShipStabMastersMates.pdf)
4. **OpenNAOE.** *Hydrostatics and Stability*, capítulo 10, “The inclining experiment”. Edição web consultada em 18 nov. 2026. Equações e exemplos trabalhados. [Capítulo](https://opennaoe.org/books/hydrostatics-stability/ch10/)
5. **NIST.** *Technical Note 1297*, apêndice A, “Law of propagation of uncertainty”. [Equação A-3](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-law-propagation-uncertainty)
6. **USCG, relatório sobre critérios de estabilidade intacta de segunda geração.** Seção 2.2.1, equação 2.1. A equação de balanço linear identifica inércia adicionada, amortecimento e restauração. A simulação aqui usa GM constante e momento imposto pelo usuário. [Relatório técnico](https://www.dco.uscg.mil/Portals/9/DCO%20Documents/5p/5ps/Design%20and%20Engineering%20Standards/Naval%20Architecture%20Division/dtmb-2ndgen-is-rpt2011.pdf)
