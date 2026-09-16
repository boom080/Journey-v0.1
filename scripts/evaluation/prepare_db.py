"""Migrate only the two dedicated evaluation databases; no database creation/drop."""
import sys
from scripts.evaluation.runtime import configure
mode=sys.argv[1] if len(sys.argv)>1 else 'test'
assert mode in ('test','real')
settings=configure(mode=='real')
assert '@127.0.0.1:55439/' in settings.database_url
from alembic.config import Config
from alembic import command
c=Config('backend/alembic.ini');c.set_main_option('script_location','backend/alembic')
command.upgrade(c,'head')
