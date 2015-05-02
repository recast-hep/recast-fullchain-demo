import click

import adagetasks
import pkg_resources
import adage
from adage import mknode

import logging
logging.basicConfig(level = logging.INFO, format = '%(levelname)s %(name)s :: %(message)s')
log = None


def build_dag(workdir):
  rules = []
  dag = adage.mk_dag()

  def inwrk(path):
    return '{0}/{1}'.format(workdir,path)

  def rsrc(path):
    return pkg_resources.resource_filename('recastfullchain','resources/{}'.format(path))
  
  madgraph = mknode(dag,adagetasks.madgraph.s(rsrc('./mg5steering.tplt'), inwrk('what.lhe'), inwrk('feynmandiags'),
                                              param = inwrk('inputs/param.dat'),
                                              proc = inwrk('inputs/proc.dat'),
                                              workdir = inwrk('madwork')))
  
  pythia_nonshowered = mknode(dag,adagetasks.pythia.s(inwrk('what.lhe'),inwrk('what_unshowered.hepmc'), showered = False,
                                                    resourcedir = rsrc(''), workdir = inwrk('pythiawork')), depends_on = [madgraph])

  mcviz = mknode(dag,adagetasks.mcviz.s(inwrk('what_unshowered.hepmc'),inwrk('preshower.svg'),
                 inwrk('preshower.pdf'),inwrk('preshower.png')),depends_on = [pythia_nonshowered])


  pack = mknode(dag,adagetasks.pack_LHE_File.s(inwrk('what.lhe'),1,outputdir = workdir), depends_on = [madgraph])

  evgen = mknode(dag,adagetasks.evgen.s(inwrk('what._00001.tar.gz'), inwrk('evt.pool.root'),
                                        seed = 1234, jobopts = rsrc('evgenJO.py'), runnr = 123, ecm = 14000,
                                        workdir = inwrk('evgenwork'), maxevents = 1), depends_on=[pack])

  sim = mknode(dag,adagetasks.sim.s(inwrk('evt.pool.root'), inwrk('g4hits.pool.root'),
                                    seed = 1234, workdir = inwrk('simwork')), depends_on = [evgen])

  digi = mknode(dag,adagetasks.digi.s(inwrk('g4hits.pool.root'), inwrk('digi.pool.root'),
                                      workdir = inwrk('digiwork')), depends_on = [sim])

  reco = mknode(dag,adagetasks.reco.s(inwrk('digi.pool.root'), inwrk('esd.pool.root'), inwrk('aod.pool.root'),
                                      workdir = inwrk('recowork')), depends_on = [digi])


  evdisplay = mknode(dag,adagetasks.eventdisplay.s(inwrk('aod.pool.root'),inwrk('eventdisplay.png'), workdir = inwrk('evntwork')), depends_on = [reco])

  ntup = mknode(dag,adagetasks.ntup.s(inwrk('aod.pool.root'), inwrk('ntup.pool.root'),
                                      workdir = inwrk('ntupwork')), depends_on = [reco])

  plot = mknode(dag,adagetasks.plot.s(inwrk('ntup.pool.root'),workdir), depends_on = [ntup])

  return dag,rules

@click.command()
@click.argument('workdir')
@click.option('-l','--logger',default = __name__)
def fullchaincli(workdir,logger):
  global log
  log = logging.getLogger(logger)

  log.info('running fullchain from workdir {0}'.format(workdir))

  dag,rules = build_dag(workdir)
  
  adage.rundag(dag,rules,loggername = logger)

  log.info('done')
  
if __name__ == '__main__':
  fullchaincli()
