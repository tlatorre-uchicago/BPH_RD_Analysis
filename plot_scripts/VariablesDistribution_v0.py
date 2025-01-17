import ROOT as rt
import root_numpy as rtnp
import numpy as np
from histo_utilities import create_TH1D, create_TH2D, std_color_list, EstimateDispersion

import CMS_lumi, tdrstyle
tdrstyle.setTDRStyle()
CMS_lumi.writeExtraText = 1
CMS_lumi.extraText = "      Simulation Preliminary"

donotdelete = []


fpath = {}
tree = {}
process = {}
process_short = {}

fpath['mu'] = '../data/cmsMC_private/BPH_Tag-Bm_D0kpmunu_Probe-B0_MuNuDmst-pD0bar-kp-_NoPU_10-2-3_v1/BPH_Tag-Bm_D0kpmunu_Probe-B0_MuNuDmst-pD0bar-kp-_BPHRDntuplizer_merged_1-300.root'
process['mu'] = 'B_{0} #rightarrow D*^{-}(#bar{D}_{0}(K^{+}#pi^{-})#pi^{-})#mu^{+}#nu'
process_short['mu'] = 'B #rightarrow D*#mu#nu'

fpath['tau'] = '../data/cmsMC_private/BPH_Tag-Bm_D0kpmunu_Probe-B0_TauNuDmst-pD0bar-kp-tau2mununu_NoPU_10-2-3_v0/BPH_Tag-Bm_D0kpmunu_Probe-B0_TauNuDmst-pD0bar-kp-tau2mununu_BPHRDntuplizer_merged_1-300.root'
process['tau'] = 'B_{0} #rightarrow D*^{-}(#bar{D}_{0}(K^{+}#pi^{-})#pi^{-})#tau^{+}(#mu^{+}#nu#bar{#nu})#nu'
process_short['tau'] = 'B #rightarrow D*#tau#nu'

for k,v in fpath.iteritems():
    tree[k] = rtnp.root2array(v)

reco_eff_ratio = len(tree['tau'])/float(len(tree['mu']))
print reco_eff_ratio

DecayChannelBr = {}
DecayChannelBr['mu'] = 4.88e-2 * 67e-2 * 3.89e-2
DecayChannelBr['tau'] = 1.67e-2 * 17.39e-2 * 67e-2 * 3.89e-2

weights = {}

sumBr = np.sum(np.array(DecayChannelBr.values()))
for k,v in DecayChannelBr.iteritems():
    weights[k] = v/sumBr

print weights

binning_q2 = np.linspace(-0.4, 12.6, 5, True)
N_q2bins = binning_q2.shape[0]-1
print binning_q2

binning = {}
binning['M2_miss_RECO'] = [40/5, -2, 10]
binning['Est_mu_RECO'] = [30/5, 0.10, 3.500]
# binning['ip_mu_RECO'] = [50/5, 0, 0.4]
# binning['M2_miss_RECO'] = [40, -2, 10]
# binning['Est_mu_RECO'] = [30, 0.10, 2.500]
# binning['ip_mu_RECO'] = [50, 0, 1]

xAx_title = {}
xAx_title['M2_miss_RECO'] = 'm^{2}_{miss} [GeV^{2}]'
xAx_title['Est_mu_RECO'] = 'E*_{#mu} [GeV]'
xAx_title['ip_mu_RECO'] = 'IP #mu [mm]'

N_var = len(binning.keys())

def q2_sel(arr, q2_l, q2_h, vname='q2_RECO'):
    return np.logical_and(arr[vname] > q2_l, arr[vname] < q2_h)

canvas = rt.TCanvas('c_out', 'c_out', 50, 50, N_var*300, 400*N_q2bins)
canvas.Divide(N_var, N_q2bins)

overall_scale_factor = 740000./float(len(tree['mu']))

for i_q2 in range(N_q2bins):
    q2_l = binning_q2[i_q2]
    q2_h = binning_q2[i_q2+1]

    q2_txt = '{:.2f} <  q^{{2}}  < {:.2f} GeV^{{2}}'.format(q2_l, q2_h)

    for i_v, vark in enumerate(binning.keys()):
        h_bname = 'h_{}_{}'.format(i_q2, i_v)

        h_dic = {}
        for k, t in tree.iteritems():
            aux = t[vark][q2_sel(t, q2_l, q2_h)]
            h_dic[k] = create_TH1D(aux, h_bname+'_aux_'+k, binning=binning[vark])
            h_dic[k].Scale(overall_scale_factor)

        h_dic['tau'].Scale(0.3*0.17) #R(D*)*Br(tau->mu)


        h = rt.TH1D(h_bname+'_tau', h_bname+'_tau', binning[vark][0], binning[vark][1], binning[vark][2])
        h.Add(h_dic['tau'])#, h_dic['mu']) #Just because we want to show them separate
        h.SetLineColor(2)
        h.GetXaxis().SetTitle(xAx_title[vark])
        h.GetXaxis().SetTitleSize(0.07)
        h.GetXaxis().SetLabelSize(0.07)
        h.GetYaxis().SetTitleOffset(1.14)
        h.GetXaxis().SetTitleOffset(1.1)
        h.GetYaxis().SetTitleSize(0.07)
        h.GetYaxis().SetLabelSize(0.07)
        iunits = xAx_title[vark].find('[') + 1
        h.GetYaxis().SetTitle('Candidates / {:.2f} '.format(h.GetBinWidth(1)) + xAx_title[vark][iunits:-1])

        h2 = h_dic['mu'].Clone(h_bname+'_mu')
        h2.SetLineColor(4)

        i_pad = i_q2*N_var + i_v + 1
        pad = canvas.cd(i_pad)
        pad.SetBottomMargin(0.2)

        # Normalize them to unity....
        h.Scale(1./h.Integral())
        h2.Scale(1./h2.Integral())
        h.GetYaxis().SetRangeUser(0, 1.5*np.max([x.GetMaximum() for x in [h, h2]]))


        h.Draw()
        h2.Draw('SAME')

        l = rt.TLatex()
        l.SetTextAlign(11)
        l.SetTextSize(0.06)
        l.DrawLatexNDC(0.2, 0.85, q2_txt)

        CMS_lumi.CMS_lumi(pad, -1, 0, 0.75*1.3, 0.6*1.3)

        if 'ip' in vark:
            maxs = [x.GetMaximum() for x in [h, h2]]
            h.GetYaxis().SetRangeUser(1e-4, 1.5*np.max(maxs))
            pad.SetLogy()

        if i_pad == 1:
            leg = rt.TLegend(0.7, 0.5, 0.9, 0.9)
            leg.SetTextFont(42)
            leg.SetTextAlign(12)
            leg.SetLineWidth(0)
            leg.SetBorderSize(0)
            leg.AddEntry(h, 'B#rightarrow D*#tau#nu', 'le')
            leg.AddEntry(h2, 'B#rightarrow D*#mu#nu', 'le')
            leg.Draw()

        donotdelete.append([h, h2])

canvas.SaveAs('../fig/1902_1/RDst_tau2mu_VariablesDistribution.png')
