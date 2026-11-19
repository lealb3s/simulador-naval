"""Equilíbrio estático em pequeno ângulo e dinâmica linear opcional.

I φ''+c φ'+(Δ g GMef)φ = (g M_massa), em radianos; g padrão 9.80665 m/s².
O modelo de dinâmica é fenomenológico e exige I efetivo e amortecimento medidos/fornecidos.
"""
from math import atan, degrees, radians, tan
import numpy as np
from .validacao import numero

G0=9.80665


def equilibrio_angulo(momento_kgm, deslocamento_kg, gm_efetivo_m):
    numero(deslocamento_kg,"deslocamento",positivo=True)
    numero(gm_efetivo_m,"GM",positivo=True)
    return degrees(atan(momento_kgm/(deslocamento_kg*gm_efetivo_m)))


def avancar_dinamica(estado, momento_kgm, deslocamento_kg, gm_efetivo_m, inercia_kgm2,
                      amortecimento_Nms, dt_s):
    """Integração dinâmica com equilíbrio linear φeq=M/(Δ GM), não atan.
    Não usar fora do regime angular linear; tolerâncias externas definem estabilização.
    """
    inicial={"tempo_s":0., "phi_rad":0., "omega_rad_s":0., **estado}
    return serie_transitoria(inicial,momento_kgm,deslocamento_kg,gm_efetivo_m,
                             {"I":inercia_kgm2,"c":amortecimento_Nms},dt_s,pontos=2)[-1]


def estabilizado(estado, momento_kgm, delta_kg, gm_m, tol_angulo_graus, tol_vel_graus_s):
    for k,v in (("tolerância angular",tol_angulo_graus),("tolerância velocidade",tol_vel_graus_s)):
        numero(v,k,positivo=True)
    # Apenas modelo LINEAR no caso dinâmico.
    phi_eq=momento_kgm/(delta_kg*gm_m)
    return abs(degrees(estado["phi_rad"]-phi_eq)) <= tol_angulo_graus and abs(degrees(estado["omega_rad_s"])) <= tol_vel_graus_s


def leitura_teorica(momento_kgm, deslocamento_kg, gm_efetivo_m, pendulos):
    theta=equilibrio_angulo(momento_kgm, deslocamento_kg, gm_efetivo_m)
    return {"angulo_graus":theta,"tangente":tan(radians(theta)),
            "deflexoes":{p["id"]:p["comprimento_m"]*tan(radians(theta)) for p in pendulos}}


def serie_transitoria(estado, momento, delta, gm, config, intervalo, pontos=61):
    """Solução da EDO no patamar constante por exponencial de matriz, em rad e s."""
    from scipy.linalg import expm
    m=numero(delta,"deslocamento",positivo=True)
    altura=numero(gm,"GM efetivo",positivo=True)
    inercia=numero(config["I"],"inércia efetiva",positivo=True)
    amort=numero(config["c"],"amortecimento",nao_negativo=True)
    duracao=numero(intervalo,"intervalo",positivo=True)
    eq=momento/(m*altura)
    a=np.array([[0.,1.],[-G0*m*altura/inercia,-amort/inercia]])
    transicao=expm(a*duracao/(pontos-1))
    vetor=np.array([estado["phi_rad"]-eq,estado["omega_rad_s"]])
    serie=[]
    for t in np.linspace(0,duracao,pontos):
        serie.append({"tempo_s":float(estado["tempo_s"]+t), "phi_rad":float(vetor[0]+eq),"omega_rad_s":float(vetor[1])})
        vetor=transicao@vetor
    return serie
