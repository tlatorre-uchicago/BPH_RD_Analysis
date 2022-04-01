#!/usr/bin/env python

import numpy as np
import pandas as pd
import scipy.stats as sps
from glob import glob
import pickle, re
import time
from array import array
from scipy.interpolate import interp1d
import multiprocessing
import matplotlib.pyplot as plt
import uproot as ur
import ROOT as rt
import root_numpy as rtnp
import ROOT.RooFit as rf
from scipy.special import erf
import sys, os
import itertools
sys.path.append('../lib')
if os.environ['CMSSW_VERSION'] != 'CMSSW_10_2_3':
    raise
from histo_utilities import create_TH1D, create_TH2D, std_color_list, SetMaxToMaxHist, make_ratio_plot
from cebefo_style import Set_2D_colz_graphics
from progressBar import ProgressBar

from analysis_utilities import drawOnCMSCanvas, extarct, extarct_multiple, createSel, load_data
from lumi_utilities import getLumiByTrigger
from pileup_utilities import pileupReweighter

import CMS_lumi, tdrstyle
tdrstyle.setTDRStyle()
CMS_lumi.writeExtraText = 1

donotdelete = []

import argparse
parser = argparse.ArgumentParser(description='Script used to run trigger efficiencies.',
                                 epilog='Test example: ./triggerEfficiencies.py',
                                 add_help=True
                                 )
parser.add_argument ('--HELP', '-H', default=False, action='store_true', help='Print help message.')
parser.add_argument ('--version', '-v', default='test', help='Version name.')

parser.add_argument ('--dataset', '-d', type=str, default='MC', choices=['RD', 'MC'], help='Dataset to use.')
parser.add_argument ('--trigger', '-t', type=str, default='Mu7_IP4', choices=['Mu7_IP4', 'Mu9_IP6', 'Mu12_IP6'], help='Trigger to probe.')
parser.add_argument ('--tagTrigger', type=str, default='', choices=['Mu7_IP4', 'Mu9_IP6', 'Mu12_IP6', ''], help='Trigger of the tag muon.')
parser.add_argument ('--method', '-M', type=str, default='count', choices=['count', 'fit'], help='Method used to estimate signal yield.')
parser.add_argument ('--refIP', type=str, default='BS', choices=['BS', 'PV'], help='Reference point for the impact parameter.')
parser.add_argument ('--muonID', type=str, default='medium', choices=['soft', 'medium'], help='Muon ID')

parser.add_argument ('--dR_TagProbe', type=float, default=0.2, help='Minimum delta R between tag and probe muon.')
parser.add_argument ('--mJpsiWindow', type=float, default=-1, help='Width around J/psi mass to be considered. Default 0.1 (count) or 0.25 (fit).')
parser.add_argument ('--parallel', '-p', type=int, default=15, help='Number of parallel CPU to use.')

parser.add_argument ('--test_bin', default=False, action='store_true', help='Run also test bin')
parser.add_argument ('--verbose', default=False, action='store_true', help='Verbose switch.')
# Example with loop: for t in "Mu7_IP4" "Mu9_IP6" "Mu12_IP6"; do ./triggerEfficiencies.py -v test_fit -t $t -M fit -d RD; done;


args = parser.parse_args()
if args.HELP:
    parser.print_help()
    exit()

rt.gROOT.SetBatch(True)
plt.ioff()
plt.switch_backend('Agg')



rt.gErrorIgnoreLevel = rt.kError
rt.RooMsgService.instance().setGlobalKillBelow(rf.ERROR)
webFolder = '/storage/af/user/alatorre/public_html/BPH_RDst/triggerScaleFactors/'+args.version
if not os.path.exists(webFolder):
    print 'Creating', webFolder
    os.makedirs(webFolder)
    os.system('cp '+webFolder+'/../index.php '+webFolder+'/')


if args.mJpsiWindow <= 0:
    if args.method == 'count':
        args.mJpsiWindow = 0.1
    elif args.method == 'fit':
        args.mJpsiWindow = 0.2

cl = rt.TLine()
cl.SetLineColor(6)
cl.SetLineStyle(9)
cl.SetLineWidth(2)



colors = [rt.kBlack, rt.kAzure+1, rt.kRed-4, rt.kGreen+1, rt.kViolet-7]



branchesToLoad = ['mTag_pt', 'mTag_eta', 'mTag_phi', 'mTag_sigdxy_BS', 'mTag_sigdxy_PV',
                  'mTag_softID', 'mTag_mediumID',
                  'mTag_HLT_Mu7_IP4', 'mTag_HLT_Mu9_IP6', 'mTag_HLT_Mu12_IP6',
                  'mProbe_pt', 'mProbe_eta', 'mProbe_phi', 'mProbe_sigdxy_BS', 'mProbe_sigdxy_PV',
                  'mProbe_L1_pt', 'mProbe_L1_eta', 'mProbe_L1_dR',
                  'mProbe_softID', 'mProbe_mediumID',
                  'mProbe_HLT_Mu7_IP4', 'mProbe_HLT_Mu9_IP6', 'mProbe_HLT_Mu12_IP6',
                  'deltaR_tagProbe', 'massMuMu', 'vtx_isGood', 'massMuMu_refit',
                  'prescaleMu7_IP4', 'prescaleMu9_IP6', 'prescaleMu12_IP6', 'nVtx',
                 ]


def loadDF(loc, branches):
    print 'Loading', args.dataset, 'from', len(loc), 'files'
    if len(loc) == 0:
        raise
    dfL = []
    pb = ProgressBar(len(loc))
    for il, l in enumerate(loc):
        dfL.append(load_data(l, branches=branches))
        pb.show(il)
    if len(dfL) == 1:
        return dfL[0]
    else:
        return pd.concat(dfL)


if args.dataset == 'RD':
    dataDir = '/storage/af/group/rdst_analysis/BPhysics/data/cmsRD'
    RDdsLoc = glob(dataDir + '/ParkingBPH*/Run2018D-05May2019promptD-v1_RDntuplizer_TagAndProbeTrigger_220217_CAND.root')
    df = loadDF(RDdsLoc, branchesToLoad)
    CMS_lumi.extraText = "     Internal"
elif args.dataset == 'MC':
    mcDir = '/storage/af/group/rdst_analysis/BPhysics/data/cmsMC/CP_General_BdToJpsiKstar_BMuonFilter_SoftQCDnonD_TuneCP5_13TeV-pythia8-evtgen'
    MCdsLoc = glob(mcDir + '/ntuples_TagAndProbeTrigger_220217/out_CAND_*.root')
    df = loadDF(MCdsLoc, branchesToLoad + ['sfMediumMuonID', 'sfSoftMuonID', 'nTrueIntMC', 'MC_mProbe_pt', 'MC_mProbe_eta', 'MC_mProbe_phi'])
    puRew = pileupReweighter(MCdsLoc[0], 'TnP/hAllNTrueIntMC', trg=args.trigger)
    df['wPileup'] = puRew.getPileupWeights(df['nTrueIntMC'])
    df['w'] = df['sf'+args.muonID.capitalize()+'MuonID']*df['wPileup']
    CMS_lumi.extraText = "     Simulation Internal"
print 'Applying quality selection'
df = df[ df['prescale'+args.trigger] > 0 ]
df = df[ df['mProbe_'+args.muonID+'ID'] > 0.5 ]
df = df[ df['deltaR_tagProbe'] > args.dR_TagProbe ]
# df = df[ np.abs(df['massMuMu'] - 3.09691) < args.mJpsiWindow ]
df = df[ df['vtx_isGood'] > 0.5 ]
df = df[ np.abs(df['massMuMu_refit'] - 3.09691) < args.mJpsiWindow ]
if args.tagTrigger:
    df = df[ df['mTag_HLT_' + args.tagTrigger] == 1 ]
print 'Total number of probe muons:', df.shape[0]

def fitJpsi(xMass, passSel, canvasTag='', weights=None, mJpsiWindow=0.25, mBins=100, verbose=False):
    mJpsi = 3.096916

    aux = np.array(xMass[passSel], dtype=np.float64)
    binContent, _ = np.histogram(aux, bins=mBins, range=(mJpsi-mJpsiWindow, mJpsi+mJpsiWindow))
    if np.min(binContent) == 0:
        mBins = int(mBins*0.5)

    hAll = create_TH1D(xMass, name='hAll',
                       axis_title=['mass(#mu#mu) [GeV]', 'Events'],
                       binning=[mBins, mJpsi-mJpsiWindow, mJpsi+mJpsiWindow],
                       weights=weights
                       )
    hAll.Sumw2()
    nAll = hAll.Integral()

    hPass = create_TH1D(xMass[passSel], name='hPass',
                        h2clone=hAll,
                        weights=weights[passSel] if not (weights is None) else None
                       )
    hPass.Sumw2()
    nPass = hPass.Integral()
    #Fitting variable
    mass = rt.RooRealVar('mass', 'Mass(#mu#mu)', mJpsi-mJpsiWindow, mJpsi+mJpsiWindow, 'GeV')
    # J/psi mass shape: shared between all and pass
    mean = rt.RooRealVar('mean', '#mu', mJpsi, mJpsi-0.01, mJpsi+0.01, 'GeV')
    sigmaN = rt.RooRealVar('sigmaN', '#sigma_{N}', 0.02, 0.01, 0.05, 'GeV')
    sigmaW = rt.RooRealVar('sigmaW', '#sigma_{W}', 0.06, 0.01, 0.07, 'GeV')
    gausN = rt.RooGaussian('gausN','gausN', mass, mean, sigmaN)
    gausW = rt.RooGaussian('gausW','gausW', mass, mean, sigmaW)
    fN = rt.RooRealVar('fN', 'f_{N}', 0.5, 0.0, 1.0)
    pdf_sig = rt.RooAddPdf('dGaus', 'sig pdf', rt.RooArgList(gausN, gausW), rt.RooArgList(fN))

    # Signal pdf: J/psi shape + extension for normalization
    nSigAll = rt.RooRealVar('nSigAll', 'N_{S}^{all}', 0.8*nAll, 0, 1.5*nAll)
    pdfSigAll_ext = rt.RooExtendPdf('eSigAll', 'eSigAll', pdf_sig, nSigAll)

    nSigPass = rt.RooRealVar('nSigPass', 'N_{S}^{pass}', 0.8*nPass, 0, 1.5*nPass)
    pdfSigPass_ext = rt.RooExtendPdf('eSigPass', 'eSigPass', pdf_sig, nSigPass)


    # Background model
    lam = rt.RooRealVar('lam', '#lambda', -5, -100, -0.1, 'GeV^{-1}')
    pdf_bkg = rt.RooExponential('expo', 'bkg pdf', mass, lam)

    nBkgAll = rt.RooRealVar('nBkgAll', 'N_{B}^{all}', 0.1*nAll, 0, 1.5*nAll)
    pdfBkgAll_ext = rt.RooExtendPdf('eBkgAll', 'eBkgAll', pdf_bkg, nBkgAll)

    nBkgPass = rt.RooRealVar('nBkgPass', 'N_{B}^{pass}', 0.1*nPass, 0, 1.5*nPass)
    pdfBkgPass_ext = rt.RooExtendPdf('eBkgPass', 'eBkgPass', pdf_bkg, nBkgPass)

    # Total models
    pdfTotAll = rt.RooAddPdf('pdfTotAll', 'pdfTotAll', rt.RooArgList(pdfSigAll_ext, pdfBkgAll_ext))
    pdfTotPass = rt.RooAddPdf('pdfTotPass', 'pdfTotPass', rt.RooArgList(pdfSigPass_ext, pdfBkgPass_ext))

    # Create RooFit data sets
    data = {}
    unbinned = {}
    for n, h in zip(['all', 'pass'], [hAll, hPass]):
        if True or (h.GetMinimum() == 0 or h.Integral() < 2*h.binning[0]):
            if verbose:
                print n + ': using unbinned likelihood ({:.0f} events)'.format(h.Integral())

            xAux = xMass if n=='all' else xMass[passSel]
            arr = pd.DataFrame(data=np.array(xAux), columns=['mass'])
            T = rtnp.array2tree(arr.to_records(index=False))
            data[n] = rt.RooDataSet('data'+n.capitalize(), 'data '+n, T, rt.RooArgSet(mass))
            unbinned[n] = True
        else:
            if verbose:
                print n+': using binned likeihood'
            data[n] = rt.RooDataHist('data'+n.capitalize(), 'data '+n, rt.RooArgList(mass), h)
            unbinned[n] = False

    # Create joint fit
    cat = rt.RooCategory('cat','cat')
    cat.defineType('all')
    cat.defineType('pass')

    jointModel = rt.RooSimultaneous('jointModel','',cat)
    jointModel.addPdf(pdfTotAll, 'all')
    jointModel.addPdf(pdfTotPass,'pass')

    jointData = rt.RooDataSet('data','joint data', rt.RooArgSet(mass),
                               rf.Index(cat),
                               rf.Import('all', data['all']),
                               rf.Import('pass', data['pass'])
                               )

    fr = jointModel.fitTo(jointData, rf.PrintLevel(-1), rf.Save(), rf.Extended(True))
    pvalJointModel = 1

    def plotOnFrame(data, pdf, tag='All'):
        frame = mass.frame(rf.Title(''), rf.Bins(hAll.binning[0]))
        dataPlot = data.plotOn(frame, rf.MarkerStyle(1), rf.DrawOption('E1'),
                               rf.MarkerColor(1), rf.LineColor(1), rf.MarkerStyle(15))

        pdf.plotOn(frame, rf.LineColor(rt.kBlack), rf.LineWidth(1))

        dof = fr.floatParsFinal().getSize()
        chi2 = frame.chiSquare(dof)*dof
        pval = rt.ROOT.Math.chisquared_cdf_c(chi2, dof)
        if verbose: print 'chi2: {:.1f}/{:.0f} {:.3f}'.format(chi2, dof, pval)

        pdf.plotOn(frame, rf.Components('eBkg'+tag), rf.LineColor(rt.kRed), rf.LineWidth(2), rf.LineStyle(7))
        pdf.plotOn(frame, rf.Components('eSig'+tag), rf.LineColor(rt.kBlue), rf.LineWidth(2), rf.LineStyle(7))

        x_min = mass.getMin() + (mass.getMax()-mass.getMin())*0.04
        x_max = mass.getMin() + (mass.getMax()-mass.getMin())*0.36
        pTxt = rt.TPaveText(x_min, 0.25*dataPlot.GetMaximum(), x_max, 0.9*dataPlot.GetMaximum())
        pTxt.SetBorderSize(0)
        pTxt.SetFillStyle(0)
        pTxt.SetTextAlign(11)
        pTxt.AddText('#chi^{{2}}: {:.1f}/{:.0f} ({:.2f})'.format(chi2, dof, pval))
        if tag == 'All':
            pTxt.AddText('N_{{sig}}^{{All}} = {:.0f} #pm {:.0f}'.format(nSigAll.getVal(), nSigAll.getError()))
        else:
            pTxt.AddText('N_{{sig}}^{{Pass}} = {:.0f} #pm {:.0f}'.format(nSigPass.getVal(), nSigPass.getError()))

        pTxt.AddText('#mu = {:.1f} #pm {:.1f} MeV'.format(1e3*mean.getVal(), 1e3*mean.getError()))
        pTxt.AddText('#sigma_{{N}} = {:.1f} #pm {:.1f} MeV'.format(1e3*sigmaN.getVal(), 1e3*sigmaN.getError()))
        pTxt.AddText('#sigma_{{W}} = {:.1f} #pm {:.1f} MeV'.format(1e3*sigmaW.getVal(), 1e3*sigmaW.getError()))
        pTxt.AddText('f_{{N}} = {:.2f} #pm {:.2f}'.format(fN.getVal(), fN.getError()))
        frame.addObject(pTxt)

        x_min = mass.getMin() + (mass.getMax()-mass.getMin())*0.65
        x_max = mass.getMin() + (mass.getMax()-mass.getMin())*0.95
        pTxtR = rt.TPaveText(x_min, 0.5*dataPlot.GetMaximum(), x_max, 0.7*dataPlot.GetMaximum())
        pTxtR.SetBorderSize(0)
        pTxtR.SetFillStyle(0)
        pTxtR.AddText(tag)
        frame.addObject(pTxtR)
        frame.dnd = [pTxt, pTxtR]
        return frame, [chi2, dof, pval]

    frameAll, chi2All = plotOnFrame(data['all'], pdfTotAll, tag='All')
    framePass, chi2Pass = plotOnFrame(data['pass'], pdfTotPass, tag='Pass')

    c = rt.TCanvas('c'+canvasTag, 'c'+canvasTag, 50, 50, 1200, 600)
    c.SetTickx(0)
    c.SetTicky(0)
    c.Divide(2)

    p = c.cd(1)
    frameAll.Draw()
    CMS_lumi.CMS_lumi(p, -1, 33)
    p = c.cd(2)
    framePass.Draw()
    CMS_lumi.CMS_lumi(p, -1, 33)
    c.dnd = [frameAll, framePass]

    return c, [nSigAll.getVal(), nSigAll.getError()], [nSigPass.getVal(), nSigPass.getError()], pvalJointModel

def analyzeBin(idx, verbose=False):
    lim = {}
    selTot = None
    st = time.time()
    for n, i in idx.iteritems():
        lim[n] = [binning[n][i], binning[n][i+1]]
        if n=='eta':
            aux = np.abs(df['mProbe_'+n])
            sel = np.logical_and(aux > lim[n][0], aux < lim[n][1])
        else:
            sel = np.logical_and(df['mProbe_'+n] > lim[n][0], df['mProbe_'+n] < lim[n][1])
        if selTot is None:
            selTot = sel
        else:
            selTot = np.logical_and(sel, selTot)

    ## Require L1 mathing
    # dptRel = np.abs(df['mProbe_L1_pt']/df['mProbe_pt']) - 1
    l1Matching = np.logical_and(df['mProbe_L1_pt'] > 0, df['mProbe_L1_dR'] < 0.5)
    selPass = np.logical_and(selTot, l1Matching)
    ptThr = float(re.search('Mu[0-9]+_', probeTrigger).group(0)[2:-1])
    selPass = np.logical_and(selPass, df['mProbe_L1_pt'] > ptThr)
    selPass = np.logical_and(selPass, np.abs(df['mProbe_L1_eta']) < 1.5)
    selPass = np.logical_and(selPass, df['mProbe_' + probeTrigger] == 1)

    # selPass = np.logical_and(selTot, df['mProbe_' + probeTrigger] == 1)


    if verbose:
        print ' --- Total ---'
    st = time.time()

    if args.method == 'count':
        if args.dataset == 'RD':
            nSigTot = [np.sum(selTot), np.sqrt(np.sum(selTot))]
        else:
            nSigTot = [np.sum(df['w'][selTot]), np.sqrt(np.sum(np.square(df['w'][selTot])))]
        if verbose:
            print 'Time: {:.1f} s'.format(time.time()-st)
            print ' --- Passed ---'

        if args.dataset == 'RD':
            nSigPass = [np.sum(selPass), np.sqrt(np.sum(selPass))]
        else:
            nSigPass = [np.sum(df['w'][selPass]), np.sqrt(np.sum(np.square(df['w'][selPass])))]
    elif args.method == 'fit':
        canvTag = ''
        for n, i in idx.iteritems(): canvTag += n+str(i)
        canvas, nSigTot, nSigPass, pval = fitJpsi(df['massMuMu_refit'][selTot],
                                              passSel=selPass[selTot],
                                              canvasTag=canvTag,
                                              weights=df['w'][selTot] if args.dataset == 'MC' else None,
                                              mJpsiWindow=args.mJpsiWindow,
                                              mBins=100, verbose=verbose)
        webFolderAux = webFolder + '/fitJpsi_' + args.trigger + '_' + args.dataset + '/'
        if not os.path.isdir(webFolderAux):
            os.system('mkdir -p '+webFolderAux)
            os.system('cp {}/index.php {}/'.format(webFolder, webFolderAux))
        canvas.SaveAs(webFolderAux+'bin_'+canvTag+'.png')

    if verbose:
        print 'Time: {:.1f} s'.format(time.time()-st)
    print idx, '{:.1f}/{:.1f}'.format(nSigPass[0], nSigTot[0]), 'done'
    return idx, nSigTot, nSigPass


# # Run the fit in each bin
probeTrigger = 'HLT_'+args.trigger

if args.trigger == 'Mu7_IP4':
    binning = {'pt': array('d', [5.5, 6.5, 7, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 8, 8.5, 9, 9.2, 10, 12, 14]),
               'eta': array('d', [0, 0.4, 0.8, 1.5]),
               'sigdxy_'+args.refIP: array('d', [4, 5, 5.5, 6, 10, 20, 200])
              }
elif args.trigger == 'Mu9_IP6':
    binning = {'pt': array('d', [8.5, 9, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 10.0, 10.5, 11, 11.5, 12, 12.2, 14]),
               'eta': array('d', [0, 0.4, 0.8, 1.5]),
               'sigdxy_'+args.refIP: array('d', [4, 6, 7, 7.5, 8, 10, 20, 200])
              }
elif args.trigger == 'Mu12_IP6':
    binning = {'pt': array('d', [11, 12, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9, 13, 13.5, 14, 14.5, 15, 16, 17, 18, 19, 20, 22, 25, 28, 35]),
               'eta': array('d', [0, 0.4, 0.8, 1.5]),
               'sigdxy_'+args.refIP: array('d', [4, 6, 7, 8, 10, 20, 200])
              }


h2 = {}
for var, cat in itertools.product(['N', 'Chi2'], ['tot', 'pass']):
    h2[var+cat] = rt.TH3D('h2'+var+cat, '',
                          len(binning['pt'])-1, binning['pt'],
                          len(binning['sigdxy_'+args.refIP])-1, binning['sigdxy_'+args.refIP],
                          len(binning['eta'])-1, binning['eta'],)

if args.test_bin or args.verbose:
    print 'Test bin'
    start = time.time()
    testOutput = analyzeBin({'pt': 2, 'sigdxy_'+args.refIP:2, 'eta':0}, verbose=True)
    print testOutput
    print 'Total time: {:.1f} sec'.format((time.time() - start))

inputs = []
for ipt in range(len(binning['pt'])-1):
    for iip in range(len(binning['sigdxy_'+args.refIP])-1):
        for ieta in range(len(binning['eta'])-1):
            idx = {'pt': ipt, 'sigdxy_'+args.refIP:iip, 'eta': ieta}
            inputs.append(idx)
print 'Total bins:', len(inputs)


if args.parallel:
    N_max = min(args.parallel, max(1, multiprocessing.cpu_count() - 10))
    N_request = min(len(inputs), N_max)
    print 'Parallelization factor:', N_request
    p = multiprocessing.Pool(N_request)
    output = p.map(analyzeBin, inputs)
else:
    output = []
    for counter, i in enumerate(inputs):
        if not args.verbose:
            print '{}/{}'.format(counter+1, len(inputs))
        output.append(analyzeBin(i, verbose=args.verbose))



for idx, nSigTot, nSigPass in output:
    ip = idx['pt']+1
    ii = idx['sigdxy_'+args.refIP]+1
    ie = idx['eta']+1
    h2['Ntot'].SetBinContent(ip, ii, ie, nSigTot[0])
    h2['Ntot'].SetBinError(h2['Ntot'].GetBin(ip, ii, ie), nSigTot[1])
    h2['Npass'].SetBinContent(ip, ii, ie, nSigPass[0])
    h2['Npass'].SetBinError(h2['Npass'].GetBin(ip, ii, ie), nSigPass[1])



if not rt.TEfficiency.CheckConsistency(h2['Npass'], h2['Ntot']): raise
pEff = rt.TEfficiency(h2['Npass'], h2['Ntot'])
pEff.SetStatisticOption(rt.TEfficiency.kFCP)
pEff.SetNameTitle('eff_'+probeTrigger, 'Efficience for '+probeTrigger)

loc = '/storage/af/group/rdst_analysis/BPhysics/data/calibration'
tf = rt.TFile(loc+'/triggerScaleFactors/{}_{}_{}.root'.format(probeTrigger, args.dataset, args.version), 'RECREATE')
pEff.Write()
for h in h2.values():
    h.Write()
tf.Close()


outCanvases = []
tdrstyle.setTDRStyle()
BRY_colors = [rt.kBlack, rt.kGray+1,
              rt.kBlue, rt.kAzure+1,
              rt.kViolet-7, rt.kMagenta-9, rt.kRed-4,
              rt.kOrange-3, rt.kYellow+7, rt.kGreen+1]
hRef = h2['Npass']
for iz in range(1, hRef.GetNbinsZ()+1):
    title = 'Efficiency {} {} ({:.1f} < |#eta| < {:.1f})'.format(probeTrigger, args.dataset, binning['eta'][iz-1], binning['eta'][iz])

    leg = rt.TLegend(0.7, 0.2, 0.98, 0.5)
    leg.SetLineWidth(0)
    leg.SetBorderSize(0)
    gr2draw = []

    for iy in range(1, hRef.GetNbinsY()+1):
        gr = rt.TGraphAsymmErrors()
        gr.SetName('gr_{}_{}'.format(iy,iz))
        for ix in range(1, hRef.GetNbinsX()+1):
            idx = pEff.GetGlobalBin(ix, iy, iz)
            x = binning['pt'][ix-1] + 0.5*(binning['pt'][ix] - binning['pt'][ix-1])
            gr.SetPoint(ix-1, x, pEff.GetEfficiency(idx))
            gr.SetPointError(ix-1, x-binning['pt'][ix-1], binning['pt'][ix]-x,
                             pEff.GetEfficiencyErrorLow(idx), pEff.GetEfficiencyErrorUp(idx)
                            )
        gr.SetLineColor(BRY_colors[iy-1])
        gr.SetMarkerColor(BRY_colors[iy-1])
        leg.AddEntry(gr, '{:.1f} < IP ({}) < {:.1f}'.format(binning['sigdxy_'+args.refIP][iy-1], args.refIP, binning['sigdxy_'+args.refIP][iy]), 'lep')
        gr2draw.append(gr)

    M = 1.2
    m = 0
    gr2draw[0].GetYaxis().SetRangeUser(m ,M)
    c = drawOnCMSCanvas(CMS_lumi, gr2draw, ['AP'] + (len(gr2draw)-1)*['P'], tag='_eff'+str(iz))
    gr2draw[0].GetYaxis().SetTitle('Efficiency')
    gr2draw[0].GetXaxis().SetTitle('Muon p_{T} [GeV]')
    leg.Draw()
    gr2draw[0].GetXaxis().SetTitleOffset(1.1)

    trgThr = float(re.search(r'_Mu[0-9]+_', probeTrigger).group(0)[3:-1])
    cl.DrawLine(trgThr, m, trgThr, 1)

    l = rt.TLine()
    l.SetLineWidth(1)
    l.SetLineColor(rt.kGray)
    l.SetLineStyle(7)
    l.DrawLine(binning['pt'][0], 1, binning['pt'][-1], 1)

    rt.TLatex()
    text = rt.TLatex()
    text.SetTextAlign(22)
    text.SetTextSize(0.04)
    text.SetTextFont(42)
    text.DrawLatexNDC(0.6, 0.9, title);

    c.SaveAs(webFolder+'/eff_'+probeTrigger+ '_' + args.dataset + '_eta{}.png'.format(iz-1))
    outCanvases.append([c, gr2draw, leg])
