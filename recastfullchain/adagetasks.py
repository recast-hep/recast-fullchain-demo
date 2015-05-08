# from adage import adagetask

import subprocess
import logging
import os
import subprocess
import os
import shutil
import glob
from adage import adagetask
from contextlib import contextmanager

log = logging.getLogger(__name__)
@contextmanager
def subprocess_in_env(envscript = None,workdir = None):
  if not workdir:
    workdir = os.getcwd()
    
  if not os.path.exists(workdir):
    os.makedirs(workdir)
    
  setupenv = 'source {0} && '.format(os.path.abspath(envscript)) if envscript else ''
  
  #helpful SO lesson on scoping: 
  #http://stackoverflow.com/questions/4851463/python-closure-write-to-variable-in-parent-scope#comment5388645_4851555

  def check_call(what):
    try:
      subprocess.check_call('{0} {1}'.format(setupenv,what),cwd = workdir, shell = True, stdout = open(os.devnull,'w'))
    except subprocess.CalledProcessError:
      log.error('subprocess failed: called with {0} {1}'.format(setupenv,what))
      raise RuntimeError
  yield check_call


def render(template,outputfile,**kwargs):
  """render template"""
  with open(outputfile,'w') as out:
      out.write(open(template).read().format(**kwargs))

@adagetask
def madgraph(steeringtempl, outputLHE, outputdiagramdir, param, proc, nevents = 1000, workdir = None):
  if not workdir:
    workdir = os.getcwd()
    
  if not os.path.exists(workdir):
    os.makedirs(workdir)

  madgraphwork = '{}/madgraphrun'.format(workdir)
  steeringfile = '{}/mg5.cmd'.format(workdir)
  render(steeringtempl,steeringfile, PARAM = param, PROC = proc, NEVENTS = nevents, WORKDIR =  madgraphwork)
  try:
    with open('{}/mg5.log'.format(workdir),'w') as mg5log:
      subprocess.check_call(['mg5','-f',steeringfile], stdout = mg5log)
    subprocess.check_call(['gunzip','-c','{}/Events/output/unweighted_events.lhe.gz'.format(madgraphwork)],
                          stdout = open(outputLHE,'w'))
    log.info('..')
  except subprocess.CalledProcessError:
    os.remote(outputLHE)

  psfiles = glob.glob('{}/SubProcesses/*/matrix*.ps'.format(madgraphwork))

  print psfiles
  
  if not os.path.exists(outputdiagramdir):
      os.makedirs(outputdiagramdir)

  for file in psfiles:
      basename = file.replace(madgraphwork+'/','').replace('/','_').rstrip('.ps')
      pdffile = '{}/{}'.format(outputdiagramdir,basename+'.pdf')
      pngfile = '{}/{}'.format(outputdiagramdir,basename+'.png')

      subprocess.call(['ps2pdf',file,pdffile])
      subprocess.check_call(['convert','-trim','-density','92',pdffile,pngfile])
       
@adagetask
def pythia(lhefilename,outhepmcfile,resourcedir = None, workdir = None, showered = True):
  if not workdir:
    workdir = os.getcwd()
    
  if not os.path.exists(workdir):
    os.makedirs(workdir)

  log.info('running pythia on {}'.format(lhefilename))

  if not os.path.exists(resourcedir):
    log.error('resource directory does not exist')
    raise IOError
    
  absinputfname = os.path.abspath(lhefilename)
  basestub = os.path.basename(lhefilename).rsplit('.',1)[0]

  template_name = 'pythiasteering.tplt' if showered else 'pythiasteering_unshowered.tplt'
  steeringtempl = '{}/{}'.format(resourcedir,template_name)
  steeringfname = '{}/{}.steering'.format(workdir,basestub)

  render(steeringtempl,steeringfname, INPUTLHEF = absinputfname)
  
  try:
    env = os.environ
    #pick up local pythia installation
    xmldoc = subprocess.Popen(['pythia8-config','--xmldoc'],stdout = subprocess.PIPE).communicate()[0].strip()
    env['PYTHIA8DATA'] = xmldoc
    log.info('starting pythia')
    with open('{}/pythia.log'.format(workdir),'w') as logfile:
      log.info('now')
      pythia_proc = subprocess.check_call(['{}/pythia/pythiarun'.format(resourcedir),steeringfname,outhepmcfile], env = env, stdout = logfile)
  except subprocess.CalledProcessError:
    log.info('something went wrong in pythia')
    os.remove(outhepmcfile)
    
@adagetask
def mcviz(inputhepmc,outputsvg,outputpdf,outputpng):
  try:
    subprocess.check_call(['mcviz','--demo',inputhepmc,'--output_file',outputsvg])
    import svg2rlg
    import reportlab.graphics
    d = svg2rlg.svg2rlg(outputsvg);reportlab.graphics.renderPDF.drawToFile(d,outputpdf)
    subprocess.check_call(['convert','-trim','-density','3000',outputpdf,outputpng])
  except subprocess.CalledProcessError:
    log.error('mcviz failed!')
    raise RuntimeError

@adagetask
def pack_LHE_File(lhefile,counter,nameformat = None, outputdir = None):
  #nameformat could be e.g. 'basename._{0:05}.events'.format(3)'
  log.info('packaging LHE file {} using ATLAS conventions with counter {}'.format(lhefile,counter))

  if not os.path.exists(lhefile):
    log.error('file {} does not exist'.format(lhefile))
    raise IOError
    
  dirname, basename = os.path.dirname(lhefile), os.path.basename(lhefile)
  
  if not outputdir:
    outputdir = os.getcwd()
  else:
    outputdir = outputdir.rstrip('/')
  
  formattedlhe = None
  if not nameformat:
    formatbase = basename.rsplit('.',1)[0]+'._{}.events'.format('{}'.format(counter).zfill(5))
  else:
    formatbase = nameformat.format()

  formattedlhe = '{}{}'.format('' if not outputdir else (outputdir+'/'),formatbase)

  tarballname = formattedlhe.rsplit('.',1)[0]+'.tar.gz'

  try:
    os.link(lhefile,formattedlhe)
    subprocess.check_call(['tar','--directory',os.path.dirname(formattedlhe),
                           '-cvzf',tarballname,os.path.basename(formattedlhe)])
  except OSError:
    log.error('could not write to outputdir {}'.format(outputdir))
    raise OSError
  finally:
    os.unlink(formattedlhe)

  return tarballname

import pkg_resources
def rsrc(path):
  return pkg_resources.resource_filename('recastfullchain','resources/{}'.format(path))

@adagetask
def evgen(inputtarball,outputpoolfile,jobopts,runnr,seed,firstevt = 0, ecm = 14000, maxevents = 2, workdir = None):
  with subprocess_in_env(envscript = rsrc('evgenenv.sh'), workdir = workdir) as check_call:
    check_call('Generate_trf.py randomSeed={seed} runNumber={runnr} ecmEnergy={ecm} maxEvents={maxevents} jobConfig={jobopts} firstEvent={firstevt} inputGeneratorFile={inputtarball} outputEVNTFile={outputpoolfile}'.format(
    seed = seed,
    runnr = runnr,
    ecm = ecm,
    maxevents = maxevents,
    jobopts = os.path.abspath(jobopts),
    firstevt = firstevt,
    inputtarball = os.path.abspath(inputtarball),
    outputpoolfile = os.path.abspath(outputpoolfile)
    ))
  
@adagetask
def sim(evgenfile, outputhitsfile, seed, maxevents = -1, workdir = None):
  with subprocess_in_env(envscript = rsrc('asetup_tag.sh')+' s1581', workdir = workdir) as check_call:
    check_call('AtlasG4_trf.py inputEvgenFile={evgenfile} outputHitsFile={outputhitsfile} maxEvents={maxevents} skipEvents=0 randomSeed={seed} geometryVersion={geometry} conditionsTag={conditions}'.format(
    seed = seed,
    evgenfile = os.path.abspath(evgenfile),
    outputhitsfile = os.path.abspath(outputhitsfile),
    geometry = 'ATLAS-GEO-16-00-00',
    conditions = 'OFLCOND-SDR-BS7T-04-00',
    maxevents = maxevents
  ))
  

@adagetask
def digi(hitsfile, outputrdofile, maxevents = -1, workdir = None):
  with subprocess_in_env(envscript =  rsrc('asetup_tag.sh')+' r3658', workdir = workdir) as check_call:
    check_call('Digi_trf.py inputHitsFile={hitsfile} outputRDOFile={outputrdofile} maxEvents={maxevents} skipEvents=0 geometryVersion={geometry}  conditionsTag={conditions}'.format(
    hitsfile = os.path.abspath(hitsfile),
    outputrdofile = os.path.abspath(outputrdofile),
    geometry = 'ATLAS-GEO-16-00-00',
    conditions = 'OFLCOND-SDR-BS7T-04-00',
    maxevents = maxevents
    ))

@adagetask
def reco(rdofile, outputesdfile, outputaodfile, maxevents = -1, workdir = None):
  with subprocess_in_env(envscript =  rsrc('asetup_tag.sh')+' r3658', workdir = workdir) as check_call:
    check_call('Reco_trf.py inputRDOFile={rdofile} outputESDFile={outputesdfile} outputAODFile={outputaodfile} maxEvents={maxevents}'.format(
    rdofile = os.path.abspath(rdofile),
    outputesdfile = os.path.abspath(outputesdfile),
    outputaodfile = os.path.abspath(outputaodfile),
    maxevents = maxevents
  ))
  
@adagetask
def ntup(aodfile, outputntupfile, maxevents = -1, workdir = None):
  with subprocess_in_env(envscript =  rsrc('asetup_tag.sh')+' p1512', workdir = workdir) as check_call:
    check_call('Reco_trf.py inputAODFile={aodfile} outputNTUP_SUSYFile={outputntupfile} maxEvents={maxevents}'.format(
    aodfile = os.path.abspath(aodfile),
    outputntupfile = os.path.abspath(outputntupfile),
    maxevents = maxevents
  ))

@adagetask
def eventdisplay(aodfile,outputpngfile,workdir = None):
  with subprocess_in_env(envscript =  rsrc('asetup_tag.sh')+' r3658', workdir = workdir) as check_call:
    jobopttempl = rsrc('atlantisJO.tplt')
    joboptionsfile = '{}/atlantisJO.py'.format(workdir)
   
    render(jobopttempl,joboptionsfile, AODFILE = os.path.abspath(aodfile))
    check_call('athena.py {jobopts}'.format(jobopts = os.path.abspath(joboptionsfile)))

    import glob
    jivexmlfile = glob.glob('{}/JiveXML*.xml'.format(workdir))
    assert len(jivexmlfile) == 1
    jivexmlfile = jivexmlfile[0]
    log.info('running atlantis on {}'.format(jivexmlfile))
  with subprocess_in_env(workdir = '{}/runatlantis'.format(workdir) ) as check_call:
    shutil.copyfile(jivexmlfile,'{}/runatlantis/Jive.xml'.format(workdir))
    
    atlantiscmd = 'java -Djava.awt.headless=true -Xms128m -Xmx1024m -jar $ATLANTISHOME/atlantis.jar'
    check_call('{cmd} -o ./  700x700 1 eventdisplay.png -p 1 -s {source}'.format(
      cmd = atlantiscmd,
      source = os.path.abspath('{}/runatlantis/Jive.xml'.format(workdir))
    ))
    shutil.copyfile('{}/runatlantis/eventdisplay.png'.format(workdir),os.path.abspath(outputpngfile))

@adagetask
def plot(ntupfile,workdir):
  if not workdir:
    workdir = os.getcwd()

  if not os.path.exists(workdir):
    os.makedirs(workdir)

  import ROOT
  f = ROOT.TFile.Open(ntupfile)
  c = ROOT.TCanvas()
  f.susy.Draw('el_pt')
  c.SaveAs('{0}/plot.pdf'.format(workdir))
  c.SaveAs('{0}/plot.png'.format(workdir))

