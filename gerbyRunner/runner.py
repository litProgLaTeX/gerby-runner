
import argparse
import logging
import sys
import yaml

from waitress import serve

from lpilGerbyConfig.config import ConfigManager

# The following import order is CRITICAL since we are monkey-patching the
# gerby.configuration module's constants.
#
from gerbyRunner.monkeyPatchConfig import monkeyPatchWebServerConfig
from gerbyRunner.databases import openCreateDatabases

import gerby.application

def cli() :
  logging.basicConfig(stream=sys.stdout)

  # Load the configuration values
  config = ConfigManager(chooseCollection=True)

  config.loadConfig()
  config.checkInterface({
    'gerby.collections.*.webserver.host' : {
      'msg' : "Gerby WebServers must have a host"
    },
    'gerby.collections.*.webserver.port' : {
      'msg' : "Gerby WebServers must have a port"
    },
    'gerby.collections.*.plastexDir' : {
      'msg' : "A Gerby collection must specify a PlasTeX directory "
    },
    'gerby.collections.*.webserver.unit' : {
      'default' : 'section'
    },
    'gerby.collections.*.webserver.depth' : {
      'default' : 1
    },
  })

  if not config.cmdArgs['collection'] :
    print("You MUST choose ONE collection for this web server to work!")
    sys.exit(1)

  collectionName = None
  for aCollectionName, aCollectionConfig in config['gerby.collections'].items() :
    if aCollectionName.lower() == config.cmdArgs['collection'] :
      collectionName = aCollectionName
      collectionConfig = aCollectionConfig
      break

  databaseName = None
  for aDatabaseName, aDatabaseConfig in config['tags.databases'].items() :
    if aDatabaseName.lower() == config.cmdArgs['collection'] :
      databaseName = aDatabaseName
      databaseConfig = aDatabaseConfig
      break

  if not collectionName :
    print(f"There is no configuration for the {collectionName} collection")
    sys.exit(1)

  if not databaseName :
    print(f"There is no configuration for the {databaseName} database")
    sys.exit(1)

  monkeyPatchWebServerConfig(
    collectionName, collectionConfig,
    databaseName, databaseConfig,
    config.cmdArgs['verbose']
  )

  # This MUST be called AFTER the config has been monkey patched!
  openCreateDatabases()

  webConfig = collectionConfig['webserver']

  # Adjust the Waitress logging levels....
  if 'waitressLogLevel' in webConfig :
    wLogger = logging.getLogger('waitress')
    wLogger.setLevel(webConfig['waitressLogLevel'])

  # Adjust the Flask logging levels....
  # actually I am not sure where/how the Flask logger is created
  #
  # see: https://flask.palletsprojects.com/en/3.0.x/quickstart/#logging
  #
  if 'flaskLogLevel' in webConfig :
    gLogger = gerby.application.app.logger
    gLogger.setLevel(webConfig['flaskLogLevel'])

  # If the user has specified their own templates directory then use it
  if 'templatesDir' in webConfig :
    gerby.application.app.template_folder = webConfig['templatesDir']

  # start the Gerby Flask App using Waitress
  if not config.cmdArgs['quiet'] :
    print("\nYour Waitress will serve you on:")
    print(f"  http://{webConfig['host']}:{webConfig['port']}")
    print("")

  serve(
    gerby.application.app.wsgi_app,
    host=webConfig['host'],
    port=webConfig['port'],
  )