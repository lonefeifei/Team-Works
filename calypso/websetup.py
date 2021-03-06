"""Setup the Calypso application"""
import logging
import calypso.controllers.Visualization
import calypso.controllers.TileProperties
from calypso.controllers import Main

from calypso.config.environment import load_environment
from calypso.model import meta
import calypso.net.topology
log = logging.getLogger(__name__)


def setup_app(command, conf, vars):
    """Place any commands to setup calypso here"""
    load_environment(conf.global_conf, conf.local_conf)

    # Create the tables if they don't already exist
    print "CREATING..."
    meta.metadata.create_all(bind=meta.engine)

