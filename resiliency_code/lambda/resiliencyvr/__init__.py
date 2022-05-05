# -*- coding: utf-8 -*-
from typing import List

from chaoslib.discovery.discover import (discover_actions, discover_probes,
                                         initialize_discovery_result)
from chaoslib.types import (DiscoveredActivities, Discovery)
from logzero import logger

__version__ = '0.3.0'
__all__ = ["__version__", "discover"]


def discover(discover_system: bool = True) -> Discovery:
    """
    Discover GPN capabilities from this extension as well, if a GPN
    configuration is available, some information about the environment.
    """
    logger.info("Discovering capabilities from resiliencyvr")

    discovery = initialize_discovery_result(
        "resiliencyvr", __version__, "resiliency")
    discovery["activities"].extend(load_exported_activities())

    return discovery


###############################################################################
# Private functions
###############################################################################
def load_exported_activities() -> List[DiscoveredActivities]:
    """
    Extract metadata from actions and probes exposed by this extension.
    """
    activities = []

    activities.extend(discover_actions("resiliencyvr.s3.actions"))
    activities.extend(discover_probes("resiliencyvr.s3.probes"))
    activities.extend(discover_actions("resiliencyvr.ssm.actions"))
    activities.extend(discover_probes("resiliencyvr.ssm.probes"))

    return activities
