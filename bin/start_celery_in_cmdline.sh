#!/bin/bash

# Run celery in a commandline window to monitor it
# Running in 'screen' might be an idea...
celery worker --app=openarticlegauge.slavedriver -B -l info -Q detect_provider,provider_licence,store_results

# (Of course there is the daemonised way to run it.)
