import subprocess
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('RECAST')

def recast(ctx):
  jobguid = ctx['jobguid']

  workdir = 'workdirs/{}'.format(jobguid)
  log.info(jobguid)
  log.info('running single function using dagger on workdir {}'.format(workdir))
  
  proc = subprocess.check_call(['recastworkflow-fullchain',workdir,'--logger','RECAST'], stdout = subprocess.PIPE)

  log.info('finished. thanks.')
  return jobguid

def resultlist():
  return ['preshower.png','preshower.pdf','feynmandiags','plot.pdf','plot.png','eventdisplay.png']
