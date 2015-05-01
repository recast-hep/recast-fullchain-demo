# from adage import adagetask

import subprocess
import logging
import os
import subprocess
import os
import shutil

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
      subprocess.check_call('{0} {1}'.format(setupenv,what),cwd = workdir, shell = True)
    except subprocess.CalledProcessError:
      log.error('subprocess failed: called with {0} {1}'.format(setupenv,what))
      raise RuntimeError
  yield check_call


def render(template,outputfile,**kwargs):
  """render template"""
  with open(outputfile,'w') as out:
      out.write(open(template).read().format(**kwargs))

@adagetask
def madgraph(steeringtempl, outputLHE, param, proc, nevents = 1000, workdir = None):
  if not workdir:
    workdir = os.getcwd()
    
  if not os.path.exists(workdir):
    os.makedirs(workdir)


  madgraphwork = '{}/madgraphrun'.format(workdir)
  steeringfile = '{}/mg5.cmd'.format(workdir)
  render(steeringtempl,steeringfile, PARAM = param, PROC = proc, NEVENTS = nevents, WORKDIR =  madgraphwork)
  subprocess.check_call(['mg5','-f',steeringfile])
  try:
    subprocess.check_call(['gunzip','-c','{}/Events/output/events.lhe.gz'.format(madgraphwork)],
                          stdout = open(outputLHE,'w'))
  except CalledProcessError:
    os.remote(outputLHE)
    
@adagetask
def pythia(lhefilename,outhepmcfile,resourcedir = None, workdir = None):
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

  steeringtempl = '{}/pythiasteering.tplt'.format(resourcedir)
  steeringfname = '{}/{}.steering'.format(workdir,basestub)
  
  render(steeringtempl,steeringfname, INPUTLHEF = absinputfname)
  
  try:
    pythia_proc = subprocess.check_call(['{}/pythia/pythiarun'.format(resourcedir),steeringfname,outhepmcfile])
  except CalledProcessError:
    os.remove(outhepmcfile)
    
@adagetask
def mcviz(inputhepmc,outputsvg):
  try:
    subprocess.check_call(['mcviz','--demo',inputhepmc,'--output_file',outputsvg])
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

@adagetask
def evgen(inputtarball,outputpoolfile,jobopts,runnr,seed,firstevt = 0, ecm = 14000, maxevents = 2, workdir = None):
  open(outputpoolfile,'a').close()
  return
  with subprocess_in_env(envscript = 'evgenenv.sh', workdir = workdir) as check_call:
    check_call('Generate_tf.py --randomSeed {seed} --runNumber {runnr} --ecmEnergy {ecm} --maxEvents {maxevents} --jobConfig {jobopts} --firstEvent {firstevt} --inputGeneratorFile {inputtarball} --outputEVNTFile {outputpoolfile}'.format(
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
  open(outputhitsfile,'a').close()
  return 
  
  with subprocess_in_env(envscript = 'basicathenv.sh', workdir = workdir) as check_call:
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
  open(outputrdofile,'a').close()
  return 

  with subprocess_in_env(envscript = 'basicathenv.sh', workdir = workdir) as check_call:
    check_call('Digi_trf.py inputHitsFile={hitsfile} outputRDOFile={outputrdofile} maxEvents={maxevents} skipEvents=0 geometryVersion={geometry}  conditionsTag={conditions}'.format(
    hitsfile = os.path.abspath(hitsfile),
    outputrdofile = os.path.abspath(outputrdofile),
    geometry = 'ATLAS-GEO-16-00-00',
    conditions = 'OFLCOND-SDR-BS7T-04-00',
    maxevents = maxevents
  ))

@adagetask
def reco(rdofile, outputaodfile, maxevents = -1, workdir = None):
  open(outputaodfile,'a').close()
  return 
  
  with subprocess_in_env(envscript = 'basicathenv.sh', workdir = workdir) as check_call:
    check_call('Reco_trf.py inputRDOFile={rdofile} outputAODFile={outputaodfile} maxEvents={maxevents}'.format(
    rdofile = os.path.abspath(rdofile),
    outputaodfile = os.path.abspath(outputaodfile),
    maxevents = maxevents
  ))
  