# AP2 – Simulador de prova de inclinação (VLCC 320K)

```
pip install -r requirements.txt
streamlit run ap2_inclinacao_app.py
```
- `incl_core.py`: física (equilíbrio com curva GZ, transitório, pêndulos, erros, ajuste linear, diagnóstico, sensibilidade, Monte Carlo).
- `ap2_inclinacao_app.py`: interface (abas I a VII).
- `hydro_core.py`: hidrostática da AP1.2 (fornece Δ, KM e BM; opcional).
- `exemplos/`: JSON de entrada e CSV da curva GZ (substitua pelos da sua AP1; KG de referência e GZ padrão são provisórios).
