def exclusiveTrigger(j, ev, trgAcc, trgNegate = []):
    if not hasattr(ev, 'trgMu_'+trgAcc):
        return False
    if getattr(ev, 'trgMu_'+trgAcc)[j] == 0:
        return False
    for t in trgNegate:
        if hasattr(ev, t):
            if getattr(ev, 'trgMu_'+t)[j] == 1:
                return False
    return True

def trigger_selection(j, ev, evEx, cat):
    if not exclusiveTrigger(j, ev, 'HLT_' + cat.trg):
        return False
    if evEx.mu_pt < cat.min_pt or evEx.mu_pt > cat.max_pt:
        return False
    if not ev.trgMu_sigdxy[j] > cat.minIP:
        return False
    if not abs(ev.trgMu_eta[j]) < 1.5:
        return False
    return True

def candidate_selection(j, ev, e, skipCut=[]):
    if not (1 in skipCut):
        if not ev.pval_piK[j] > 0.1:
            return False
    if not (2 in skipCut):
        if not e.K_pt > 0.8:
            return False
    if not (3 in skipCut):
        if not abs(e.K_eta) < 2.4:
            return False
    if not (4 in skipCut):
        if not e.pi_pt > 0.8:
            return False
    if not (5 in skipCut):
        if not abs(e.pi_eta) < 2.4:
            return False
    if not (6 in skipCut):
        if not abs(e.mass_piK - 1.86483) < 0.05:
            # if not ev.mass_piK_hKK[j] > 1.91 and ev.mass_piK_hpipi[j] < 1.83:
            return False
    if not (7 in skipCut):
        if not ev.sigdxy_vtxD0_PV[j] > 2:
            return False
    if not (8 in skipCut):
        if not e.pis_pt > 0.4:
            return False
    if not (9 in skipCut):
        if not abs(e.pis_eta) < 2.4:
            return False
    if not (10 in skipCut):
        if not ev.pval_D0pis[j] > 0.1:
            return False
    if not (11 in skipCut):
        if not abs(e.mass_D0pis - 2.01026) < 0.03:
            return False
    if not (12 in skipCut):
        if not 1e3*abs(e.mass_D0pis - e.mass_piK - 0.14543) < 2.:
            return False
    if not (13 in skipCut):
        if not ev.pval_D0pismu[j] > 0.1:
            return False
    if not (14 in skipCut):
        if not ev.cos_D0pismu_PV[j] > 0.99:
            return False
    if not (15 in skipCut):
        if not (e.q2 > -2. and e.q2 < 12):
            return False
    if not (16 in skipCut):
        if not e.mass_D0pismu < 7.:
            return False
    if not (17 in skipCut):
        if not e.N_goodAddTks == 0:
            return False
    return True

candidateSelection_stringList = [
    'pval_piK > 0.1',
    'K_pt > 0.8',
    'abs(K_eta) < 2.4',
    'pi_pt > 0.8',
    'abs(pi_eta) < 2.4',
    'abs(mass_piK - 1.86483) < 0.05',
    'sigdxy_vtxD0_PV > 2',
    'pis_pt > 0.4',
    'abs(pis_eta) < 2.4',
    'pval_D0pis > 0.1',
    'abs(mass_D0pis - 2.01026) < 0.03',
    '1e3*abs(mass_D0pis - mass_piK - 0.14543) < 2.5',
    'pval_D0pismu > 0.1',
    'cos_D0pismu_PV > 0.99',
    '-2 < q2 && q2 < 12',
    'mass_D0pismu < 7.',
    'N_goodAddTks == 0',
]

candidateSelection_nameList = [
    'pval_piK',
    'K_pt',
    '|K_eta|',
    'pi_pt',
    '|pi_eta|',
    'mass_piK',
    'sigdxy_vtxD0_PV',
    'pis_pt',
    '|pis_eta|',
    'pval_D0pis',
    'mass_D0pis',
    '|m_D0pis - m_piK|',
    'pval_D0pismu',
    'cos_D0pismu_PV',
    '-2 < q2 < 12',
    'm D0pismu',
    'N goodAddTks',
]
