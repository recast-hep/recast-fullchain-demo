import subprocess
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('RECAST')

def recast(ctx):
  jobguid = ctx['jobguid']

  workdir = 'workdirs/{}'.format(jobguid)
  log.info(jobguid)
  log.info('running single function using dagger on workdir {}'.format(workdir))
  
  proc = subprocess.Popen(['recastworkflow-fullchain',workdir,'--logger','RECAST'], stderr = subprocess.PIPE)

  while proc.poll() is None:
    s = proc.stderr.readline()
    if 'RECAST' in s:
      lvl,msg = s.split(' RECAST :: ')
      log.info(msg)
    import time
    time.sleep(0.01)

  log.info('finished. thanks.')
  return jobguid

def resultlist():
  return ['preshower.png','preshower.pdf','feynmandiags','plot.pdf','plot.png','eventdisplay.png','workflow.gif']
