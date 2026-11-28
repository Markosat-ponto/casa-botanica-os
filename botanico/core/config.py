"""Configuração e limites de segurança do Botânico.

REGRA: o Botânico (IA ou motor) NUNCA altera este arquivo nem os valores
equivalentes no Home Assistant. Só o Theo altera, por decisão humana.
Valores marcados "VALIDAR" dependem de medição física na casa.
"""

# Modo de execução física do portão:
#   "simulado"  -> nenhum comando real; tudo é registrado (padrão atual)
#   "autonomo"  -> comandos reais, somente após aprovação do Theo (Fase 7)
MODO_EXECUCAO_PADRAO = "simulado"

PORTAO = {
    # Entidade real confirmada em 27/11/2026 (Tuya, módulo de pulso c/ sensor).
    "entidade_cover": "cover.portao_door_1",
    # Sensor só informa "fechado" (reed na posição fechada) ou "não fechado".
    # Precisa estar estável este tempo para ser considerado confiável
    # (histórico mostra oscilações de ~100 ms entre open/closed).
    "estavel_segundos": 5,
    # Mais que N trocas de estado em 60 s = sensor contraditório.
    "max_trocas_por_minuto": 4,
    # VALIDAR: tempo de curso completo do portão (abrir ou fechar).
    "tempo_curso_segundos": 25,
    # Após um pulso de abertura, o reed deve sair de "closed" em até:
    "resposta_abertura_segundos": 15,
    # Após um pulso de fechamento, deve chegar a "closed" em até:
    "resposta_fechamento_segundos": 45,
    # Repetições permitidas quando o pulso de ABERTURA não teve efeito.
    # Fechamento NUNCA é repetido automaticamente.
    "max_repeticoes_abertura": 1,
    # Limites anti-repetição.
    "max_pulsos_por_atendimento": 3,
    "max_pulsos_por_hora": 6,
    # Equipamentos físicos de segurança. Ficam False até instalação E
    # validação presencial pelo Theo. Sem fotocélula validada, o fechamento
    # autônomo fica BLOQUEADO.
    "fotocelula_instalada_e_validada": False,
    "botao_fisico_saida_instalado": False,
    # Câmera é complementar: pode BLOQUEAR, nunca autoriza sozinha.
    "camera_entidade": "camera.garagem_camera_entrada",
}

HOSPEDE = {
    # Janela de suporte após o fim das credenciais: o hóspede validado ainda
    # pode pedir ajuda para SAIR (nunca para entrar) durante este período.
    "suporte_horas_apos_expiracao": 5,
    # Mesmo que a credencial expire cedo, suporte de saída vale ao menos até:
    "suporte_minimo_ate_hora": 18,
    # Tempo para o hóspede confirmar que o veículo saiu antes de alertar o Theo.
    "aguardar_veiculo_minutos": 15,
    # Tentativas de validação de código antes de bloquear a sessão.
    "max_tentativas_codigo": 3,
}

# Regras pré-aprovadas (nível 2). Mudar = decisão do Theo.
REGRAS_NIVEL_2 = {
    # Alteração de horário de saída: até este limite, se não houver check-in
    # no mesmo dia no mesmo quarto.
    "late_checkout_max_hora": 13,
    "late_checkout_exige_quarto_livre_no_dia": True,
    # Extensão de estadia: Botânico só consulta disponibilidade e informa o
    # valor cadastrado; a reserva/pagamento acontece no Airbnb.
    "extensao_somente_informar": True,
}

EMERGENCIA = {
    "samu": "192",
    "bombeiros": "193",
    "policia": "190",
}
