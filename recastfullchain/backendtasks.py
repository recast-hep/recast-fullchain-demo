import subprocess
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('RECAST')

def recast(ctx):
  jobguid = ctx['jobguid']
  log.info('running single function using dagger')

  workdir = 'workdirs/{}'.format(jobguid)

  proc = subprocess.check_call(['recastworkflow-fullchain',workdir,'--logger','RECAST'], stdout = subprocess.PIPE)

  log.info('finished. thanks.')
  return jobguid

def resultlist():
  return ['what.svg']