"""Run Hysteria model/export tests without real app startup, network or Xray."""
import os,sys,types,tempfile,logging,unittest
from pathlib import Path
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
with tempfile.TemporaryDirectory(prefix='marzban-unit-') as tmp:
 os.environ['SQLALCHEMY_DATABASE_URL']='sqlite:///'+tmp+'/unit.sqlite3'
 os.environ['XRAY_JSON']=str(root/'xray_config.json')
 exe=Path(tmp)/'xray';exe.write_text('#!/bin/sh\nprintf "Xray 26.3.27\\n"\n');exe.chmod(0o700)
 os.environ['XRAY_EXECUTABLE_PATH']=str(exe)
 app=types.ModuleType('app');app.__path__=[str(root/'app')];app.app=FastAPI();app.scheduler=BackgroundScheduler();app.logger=logging.getLogger('unit')
 sys.modules['app']=app
 from app.utils import system
 system.get_public_ip=lambda:'127.0.0.1';system.get_public_ipv6=lambda:'[::1]'
 from app import xray
 import importlib.util
 spec=importlib.util.spec_from_file_location('test_hysteria',root/'tests/test_hysteria.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
 sys.exit(not result.wasSuccessful())
